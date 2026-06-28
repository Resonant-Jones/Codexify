"""
Luna n8n Mention Adapter
~~~~~~~~~~~~~~~~~~~~~~~~

Isolated outbound integration for the explicit ``@luna`` mention boundary on
the latest user message in a Codexify chat thread. When triggered, the
adapter:

1. Detects the leading ``@luna`` mention (case-insensitive, with
   word-boundary protection so ``@lunatic`` is not matched).
2. Strips only that leading token and adjacent separator characters; rejects
   empty commands (``@luna`` / ``@luna,``).
3. Builds a labeled user-visible transcript from the visible ``user`` and
   ``assistant`` messages in chronological order.
4. Sends the transcript plus an optional role-establishing preamble to the
   configured n8n webhook as ``chatInput``.
5. Extracts a non-empty text reply from the actual n8n response shape and
   returns it for the chat route to persist.

This module does NOT touch Atlas, retrieval, embeddings, providers, graph,
queues, workers, the WebUI, or mobile. The webhook URL is runtime
configuration (``LUNA_N8N_WEBHOOK_URL``) and is never logged or included in
error responses.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Iterable, Mapping

import httpx

logger = logging.getLogger(__name__)


# ---- Configuration --------------------------------------------------------

LUNA_N8N_WEBHOOK_URL = os.getenv("LUNA_N8N_WEBHOOK_URL", "").strip()
LUNA_N8N_TIMEOUT_SECONDS = float(
    os.getenv("LUNA_N8N_TIMEOUT_SECONDS", "120") or "120"
)
# Optional operator/owner display name used to label user messages in the
# transcript when the authenticated user's own display_name is unavailable.
# Never hardcode this value in committed source; it is local runtime config.
LUNA_OPERATOR_NAME = os.getenv("LUNA_OPERATOR_NAME", "").strip()

# Defensive ceiling for the assembled transcript payload. Documents over this
# size are rejected explicitly so we never silently truncate.
MAX_TRANSCRIPT_CHARS = 200_000

# Anchor regex for the leading mention. The full match is consumed; only the
# message portion (after the leading token and adjacent separators) is
# retained via ``strip_luna_mention``.
#
# The optional ``(?:\[[^]]+\]:\s*)?`` prefix matches the stored display-name
# shape used by webui-basic (e.g. ``[Zac]: @luna test``). The prefix is
# matched but NOT captured — only the ``message`` group after the mention
# token is returned.
#
# Accepts:
#   "@luna hello"
#   "@Luna, hello"
#   "  @LUNA: hello"
#   "@luna - hello"
#   "[Zac]: @luna test"
#   "[Any Future Display Name]: @luna test"
#   "[Name With Spaces]: @luna - test"
# Rejects:
#   "hello @luna"           (mid-message)
#   "[Zac]: hello @luna"    (mention not leading after prefix)
#   '"@luna hello"'         (quoted — leading '"' blocks the anchor)
#   "@lunatic hello"        (word boundary)
#   "@luna", "@luna,"       (empty remainder — handled by strip_luna_mention)
#   "[Zac]: @luna"          (empty remainder — handled by strip_luna_mention)
_LUNA_LEADING_MENTION_RE = re.compile(
    r"^\s*(?:\[[^]]+\]:\s*)?@luna(?![A-Za-z0-9_])(?:[\s,:;\-]+(?P<message>.*))?",
    re.IGNORECASE | re.DOTALL,
)

# Speaker labels and outbound header.
_ASSISTANT_LABEL = "Guardian"
_LUNA_LABEL = "Luna"
_DEFAULT_USER_LABEL = "User"
_TRANSCRIPT_HEADER = "## Chat Transcript"
_LUNA_PREAMBLE = "You are Luna."

# Order of fields checked when parsing an n8n JSON reply.
_REPLY_FIELD_KEYS = ("message", "output", "text", "response")


# ---- Typed exceptions ------------------------------------------------------


class LunaError(Exception):
    """Base class for Luna adapter errors."""


class LunaConfigError(LunaError):
    """Raised when the n8n webhook URL is not configured."""


class LunaTimeoutError(LunaError):
    """Raised when the n8n webhook call exceeds the configured timeout."""


class LunaUpstreamError(LunaError):
    """Raised on non-2xx status, empty reply, malformed reply, or transport failure."""


# ---- Pure helpers ---------------------------------------------------------


def is_luna_mention(text: Any) -> bool:
    """Return True iff ``text`` begins with a valid leading ``@luna`` mention.

    An optional ``[Display Name]:`` prefix (as stored by webui-basic) is
    accepted before the mention token. A bare ``@luna`` (no message
    portion) is matched; downstream callers should still validate that the
    mention is non-empty via ``strip_luna_mention``.
    """
    if not isinstance(text, str):
        return False
    return _LUNA_LEADING_MENTION_RE.match(text) is not None


def strip_luna_mention(text: Any) -> str | None:
    """Strip a leading ``@luna`` mention and adjacent separators.

    An optional ``[Display Name]:`` prefix (as stored by webui-basic) is
    consumed and discarded — only the message portion after the ``@luna``
    token is returned. Returns the remaining message text (stripped), or
    ``None`` when the mention is empty (e.g. ``@luna``, ``@luna,``, or
    ``[Zac]: @luna``) or the input is not a valid string.
    """
    if not isinstance(text, str):
        return None
    match = _LUNA_LEADING_MENTION_RE.match(text)
    if match is None:
        return None
    remainder = match.group("message") or ""
    remainder = remainder.strip()
    return remainder or None


def resolve_user_display_name(
    auth_display_name: str | None = None,
    *,
    operator_name: str | None = None,
) -> str:
    """Resolve the user-facing speaker label for transcript messages.

    Resolution order (highest priority first):

    1. ``auth_display_name`` — the authenticated user's own ``display_name``
       from their account profile, when available and non-empty.
    2. ``operator_name`` — typically ``LUNA_OPERATOR_NAME`` from the runtime
       environment; used when no authenticated display name is available.
    3. ``"User"`` — the final repo-standard fallback.

    Whitespace-only strings are treated as empty.
    """
    candidate = str(auth_display_name).strip() if auth_display_name else ""
    if candidate:
        return candidate
    candidate = (
        str(operator_name).strip()
        if operator_name is not None
        else LUNA_OPERATOR_NAME
    )
    if candidate:
        return candidate
    return _DEFAULT_USER_LABEL


def extract_latest_text(latest_turn: Any) -> str:
    """Flatten the latest turn's content to plain text.

    Handles both string and structured multimodal content (list of typed
    parts). Mirrors the existing extraction pattern used elsewhere in the
    chat route.
    """
    if not isinstance(latest_turn, dict):
        return ""
    content = latest_turn.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = str(part.get("text", "")).strip()
                if text:
                    parts.append(text)
        return " ".join(parts)
    if content is None:
        return ""
    return str(content)


def _label_for_role(
    role: Any,
    user_display_name: str,
    message_metadata: Mapping[str, Any] | None = None,
) -> str | None:
    role_norm = str(role or "").strip().lower()
    if role_norm == "user":
        return user_display_name.strip() or _DEFAULT_USER_LABEL
    if role_norm == "assistant":
        if isinstance(message_metadata, Mapping):
            meta_source = str(
                message_metadata.get("source", "")
            ).strip().lower()
            if meta_source == "luna_n8n":
                return _LUNA_LABEL
        return _ASSISTANT_LABEL
    return None


def _coerce_message_text(content: Any) -> str:
    if isinstance(content, list):
        text_parts: list[str] = []
        for part in content:
            if isinstance(part, Mapping) and part.get("type") == "text":
                text = str(part.get("text", "")).strip()
                if text:
                    text_parts.append(text)
        return " ".join(text_parts)
    if isinstance(content, str):
        return content
    return ""


def format_transcript(
    messages: Iterable[Mapping[str, Any]],
    *,
    user_display_name: str = _DEFAULT_USER_LABEL,
    preamble: str | None = _LUNA_PREAMBLE,
    max_chars: int = MAX_TRANSCRIPT_CHARS,
) -> str:
    """Build the ``chatInput`` body from the visible transcript.

    Each included message is rendered with a stable speaker label followed
    by the complete visible content. Non-user/non-assistant messages are
    skipped. The header is always emitted when at least one labeled
    message is present; a leading ``preamble`` is emitted when provided.

    Raises ``LunaUpstreamError`` when the assembled body exceeds
    ``max_chars``; the caller should map this to a 4xx response.
    """
    user_label = user_display_name.strip() or _DEFAULT_USER_LABEL
    blocks: list[str] = []
    if preamble:
        preamble_text = str(preamble).strip()
        if preamble_text:
            blocks.append(preamble_text)
    blocks.append(_TRANSCRIPT_HEADER)

    for message in messages:
        if not isinstance(message, Mapping):
            continue
        label = _label_for_role(
            message.get("role"),
            user_label,
            message.get("message_metadata"),
        )
        if label is None:
            continue
        content = _coerce_message_text(message.get("content"))
        content = content.strip()
        if not content or content.lower() == "null":
            continue
        blocks.append(f"{label}:\n{content}")

    body = "\n\n".join(blocks)
    if len(body) > max_chars:
        raise LunaUpstreamError(
            f"transcript exceeds {max_chars} characters; "
            "refusing to silently truncate"
        )
    return body


def build_payload(
    chat_input: str,
    *,
    session_id: str,
    thread_id: int | None = None,
    project_id: int | None = None,
) -> dict[str, Any]:
    """Build the allowlisted n8n payload.

    Only ``chatInput``, ``sessionId``, and ``metadata`` are forwarded.
    ``metadata`` is restricted to ``source`` (always ``"codexify"``),
    ``threadId`` (when present), and ``projectId`` (when present).
    """
    if not session_id:
        raise ValueError("session_id is required")
    if not isinstance(chat_input, str) or not chat_input.strip():
        raise ValueError("chat_input is required")

    metadata: dict[str, Any] = {"source": "codexify"}
    if thread_id is not None:
        metadata["threadId"] = int(thread_id)
    if project_id is not None:
        metadata["projectId"] = int(project_id)

    return {
        "chatInput": chat_input,
        "sessionId": str(session_id),
        "metadata": metadata,
    }


def extract_luna_reply(raw_text: Any) -> str:
    """Extract a non-empty reply from the actual n8n response shape.

    Supports direct string bodies, dicts with ``message``/``output``/
    ``text``/``response`` keys, and a one-item array of either. Raises
    ``LunaUpstreamError`` when no non-empty reply is found or the shape
    is unrecognized.
    """
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise LunaUpstreamError("n8n returned an empty response")

    candidate: Any = raw_text
    stripped = raw_text.strip()
    if stripped[:1] in ("{", "["):
        try:
            candidate = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            # Not JSON; treat the raw text as a plain string reply.
            return stripped

    if isinstance(candidate, str):
        return candidate.strip()

    if isinstance(candidate, list):
        if len(candidate) != 1:
            raise LunaUpstreamError(
                "n8n returned an unexpected response array length"
            )
        candidate = candidate[0]

    if isinstance(candidate, dict):
        for key in _REPLY_FIELD_KEYS:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        raise LunaUpstreamError("n8n returned no recognized reply field")

    if isinstance(candidate, (int, float, bool)):
        return str(candidate)

    raise LunaUpstreamError("n8n returned an unrecognized reply shape")


# ---- Async I/O ------------------------------------------------------------


def _resolve_call_params(
    url: str | None,
    timeout: float | None,
) -> tuple[str, float]:
    effective_url = (url or LUNA_N8N_WEBHOOK_URL or "").strip()
    if not effective_url:
        raise LunaConfigError("LUNA_N8N_WEBHOOK_URL is not configured")
    try:
        effective_timeout = (
            float(timeout) if timeout is not None else LUNA_N8N_TIMEOUT_SECONDS
        )
    except (TypeError, ValueError) as exc:
        raise LunaConfigError("invalid LUNA_N8N_TIMEOUT_SECONDS") from exc
    if effective_timeout <= 0:
        raise LunaConfigError("invalid LUNA_N8N_TIMEOUT_SECONDS")
    return effective_url, effective_timeout


async def call_luna_n8n(
    payload: Mapping[str, Any],
    *,
    url: str | None = None,
    timeout: float | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    """Send ``payload`` to the configured n8n webhook and return the reply.

    Raises:
        LunaConfigError: when ``LUNA_N8N_WEBHOOK_URL`` is not configured
            or ``timeout`` is non-positive.
        LunaTimeoutError: when the request exceeds the configured timeout.
        LunaUpstreamError: on connection failure, non-2xx status, empty
            reply, or malformed reply.
    """
    effective_url, effective_timeout = _resolve_call_params(url, timeout)

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=effective_timeout)
    try:
        try:
            response = await client.post(
                effective_url,
                json=dict(payload),
                headers={"Accept": "application/json, text/plain, */*"},
            )
        except httpx.TimeoutException as exc:
            raise LunaTimeoutError("n8n webhook timed out") from exc
        except httpx.HTTPError as exc:
            raise LunaUpstreamError(
                "n8n webhook transport failed"
            ) from exc
    finally:
        if owns_client:
            await client.aclose()

    if response.status_code < 200 or response.status_code >= 300:
        raise LunaUpstreamError(
            f"n8n webhook returned status {response.status_code}"
        )

    return extract_luna_reply(response.text)


__all__ = [
    "LUNA_N8N_TIMEOUT_SECONDS",
    "LUNA_N8N_WEBHOOK_URL",
    "LUNA_OPERATOR_NAME",
    "LUNA_PREAMBLE",
    "MAX_TRANSCRIPT_CHARS",
    "LunaConfigError",
    "LunaError",
    "LunaTimeoutError",
    "LunaUpstreamError",
    "build_payload",
    "call_luna_n8n",
    "extract_latest_text",
    "extract_luna_reply",
    "format_transcript",
    "is_luna_mention",
    "resolve_user_display_name",
    "strip_luna_mention",
]