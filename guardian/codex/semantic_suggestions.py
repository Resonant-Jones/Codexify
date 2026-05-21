from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from guardian.protocol_tokens import CodexEntrySuggestionReason

_CAPTURE_LANGUAGE_RE = re.compile(
    r"\b("
    r"save this|"
    r"turn this into a codex entry|"
    r"this should be an entry|"
    r"capture this|"
    r"make this reusable|"
    r"this is a pattern|"
    r"add this to the codex"
    r")\b",
    re.IGNORECASE,
)
_SLASH_ONLY_RE = re.compile(r"^/\S+(?:\s*)?$")
_MIN_INLINE_SOURCE_CHARS = 40
_MIN_SIGNAL_SOURCE_CHARS = 80
_MAX_SOURCE_MESSAGES = 4


@dataclass(frozen=True)
class CodexEntrySuggestion:
    should_suggest: bool
    confidence: float = 0.0
    reason: str | None = None
    source_message_ids: list[str | int] = field(default_factory=list)
    source_summary: str = ""
    suppression_key: str = ""
    thread_id: str | int | None = None
    project_id: str | int | None = None
    persona_id: str | int | None = None


def _message_id(message: dict[str, Any]) -> str | int | None:
    value = message.get("id") or message.get("message_id")
    if value in (None, ""):
        return None
    return value


def _message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    return content.strip() if isinstance(content, str) else ""


def _is_usable_source_message(message: dict[str, Any]) -> bool:
    content = _message_content(message)
    if not content:
        return False
    if _SLASH_ONLY_RE.match(content):
        return False
    return _message_id(message) is not None


def _source_summary(messages: list[dict[str, Any]]) -> str:
    roles = [
        str(message.get("role") or "unknown").strip().lower() or "unknown"
        for message in messages
    ]
    user_count = roles.count("user")
    assistant_count = roles.count("assistant")
    return (
        f"{len(messages)} messages "
        f"({user_count} user, {assistant_count} assistant)"
    )


def _suppression_key(
    *, thread_id: str | int, reason: str, source_message_ids: list[str | int]
) -> str:
    raw = "|".join([str(thread_id), reason, *map(str, source_message_ids)])
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"codex:{digest}"


def _build_no_suggestion(
    *,
    thread_id: str | int,
    project_id: str | int | None,
    persona_id: str | int | None,
) -> CodexEntrySuggestion:
    return CodexEntrySuggestion(
        should_suggest=False,
        thread_id=thread_id,
        project_id=project_id,
        persona_id=persona_id,
    )


def evaluate_codex_entry_suggestion(
    *,
    thread_id: str | int,
    recent_messages: list[dict],
    project_id: str | int | None = None,
    persona_id: str | int | None = None,
) -> CodexEntrySuggestion:
    """Evaluate whether recent chat context merits an advisory Codex Entry prompt.

    This is intentionally deterministic and conservative. It only recognizes
    explicit capture language and returns a transient suggestion contract; it
    does not persist artifacts, write memory, or mutate retrieval settings.
    """
    normalized_messages = [
        message for message in recent_messages if isinstance(message, dict)
    ]
    if not normalized_messages:
        return _build_no_suggestion(
            thread_id=thread_id, project_id=project_id, persona_id=persona_id
        )

    signal_index: int | None = None
    for index in range(len(normalized_messages) - 1, -1, -1):
        content = _message_content(normalized_messages[index])
        if not content or _SLASH_ONLY_RE.match(content):
            continue
        if _CAPTURE_LANGUAGE_RE.search(content):
            signal_index = index
            break

    if signal_index is None:
        return _build_no_suggestion(
            thread_id=thread_id, project_id=project_id, persona_id=persona_id
        )

    signal_message = normalized_messages[signal_index]
    signal_content = _message_content(signal_message)
    source_messages: list[dict[str, Any]] = []

    if (
        len(signal_content) >= _MIN_SIGNAL_SOURCE_CHARS
        or (
            len(signal_content) >= _MIN_INLINE_SOURCE_CHARS
            and ":" in signal_content
        )
    ) and _is_usable_source_message(signal_message):
        source_messages.append(signal_message)
    else:
        prior_candidates = [
            message
            for message in normalized_messages[:signal_index]
            if _is_usable_source_message(message)
        ]
        source_messages.extend(prior_candidates[-_MAX_SOURCE_MESSAGES:])

    if not source_messages:
        return _build_no_suggestion(
            thread_id=thread_id, project_id=project_id, persona_id=persona_id
        )

    source_message_ids = [
        message_id
        for message in source_messages
        if (message_id := _message_id(message)) is not None
    ]
    if not source_message_ids:
        return _build_no_suggestion(
            thread_id=thread_id, project_id=project_id, persona_id=persona_id
        )

    reason = CodexEntrySuggestionReason.CAPTURE_LANGUAGE.value
    return CodexEntrySuggestion(
        should_suggest=True,
        confidence=0.82,
        reason=reason,
        source_message_ids=source_message_ids,
        source_summary=_source_summary(source_messages),
        suppression_key=_suppression_key(
            thread_id=thread_id,
            reason=reason,
            source_message_ids=source_message_ids,
        ),
        thread_id=thread_id,
        project_id=project_id,
        persona_id=persona_id,
    )
