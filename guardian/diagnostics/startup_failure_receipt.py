"""Bounded, secret-safe evidence for unhandled application startup failures.

This module writes a single diagnostic receipt to stderr.  It is deliberately
not routed through the process-wide logging record sanitizer: that sanitizer
correctly suppresses arbitrary dynamic content, whereas this module first
constructs a separately bounded and secret-redacted JSON object.  The receipt
is log evidence only; it has no database, queue, or file persistence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import traceback
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import datetime, timezone
from typing import Any, TextIO

SCHEMA_VERSION = "codexify.backend-startup-failure.v1"
EVENT = "backend_startup_failure"
STARTUP_PHASE_APPLICATION_LIFESPAN = "application_lifespan"
RECEIPT_PREFIX = "CODEXIFY_STARTUP_FAILURE_RECEIPT "
FALLBACK_LINE = "CODEXIFY_STARTUP_FAILURE_RECEIPT_EMISSION_FAILED"

MAX_RECEIPT_BYTES = 16 * 1024
MAX_MESSAGE_BYTES = 1024
MAX_CHAIN_ENTRIES = 8
MAX_FRAMES = 16
MAX_EXCEPTION_IDENTITY_BYTES = 160
MAX_CHAIN_MESSAGE_BYTES = 512
MAX_FRAME_PATH_BYTES = 256
MAX_FRAME_FUNCTION_BYTES = 160
MAX_STARTUP_PHASE_BYTES = 128

_REDACTED = "<redacted>"
_AUTH_BEARER_RE = re.compile(
    r"(?i)(\bauthorization\s*:\s*bearer\s+)[^\s,;]+"
)
_BEARER_RE = re.compile(r"(?i)(\bbearer\s+)[^\s,;]+")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:password|passwd|secret|token|api[_-]?key|apikey)\s*[=:]\s*)"
    r"[^\s,;]+"
)
_ENV_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:OPENAI_API_KEY|DEEPSEEK_API_KEY|DATABASE_URL)\s*=\s*)"
    r"[^\s,;]+"
)
_URI_USERINFO_RE = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s/@]+@"
)
_JWT_RE = re.compile(
    r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b"
)
_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")


def _bound_text(value: Any, limit: int) -> tuple[str, bool]:
    """Return UTF-8 byte-bounded text and whether it was truncated."""
    text = str(value)
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text, False

    marker = "…"
    marker_bytes = marker.encode("utf-8")
    clipped = encoded[: max(0, limit - len(marker_bytes))].decode(
        "utf-8", errors="ignore"
    )
    return f"{clipped}{marker}", True


def _exception_message(exception: BaseException) -> str:
    """Read a message defensively without allowing a bad ``__str__`` to win."""
    try:
        return str(exception)
    except BaseException:
        return "<exception-message-unavailable>"


def _message_sha256(message: str) -> str:
    return hashlib.sha256(
        message.encode("utf-8", errors="replace")
    ).hexdigest()


def redact_exception_message(message: str, *, limit: int = MAX_MESSAGE_BYTES) -> tuple[str, bool]:
    """Return a human-readable but conservative, byte-bounded message.

    The input is used only to derive the redacted output and correlation hash;
    it is never logged or retained by this module as a raw value.
    """
    redacted = _AUTH_BEARER_RE.sub(r"\1" + _REDACTED, message)
    redacted = _BEARER_RE.sub(r"\1" + _REDACTED, redacted)
    redacted = _ENV_SECRET_ASSIGNMENT_RE.sub(r"\1" + _REDACTED, redacted)
    redacted = _SECRET_ASSIGNMENT_RE.sub(r"\1" + _REDACTED, redacted)
    redacted = _URI_USERINFO_RE.sub(r"\1" + _REDACTED + "@", redacted)
    redacted = _JWT_RE.sub(_REDACTED, redacted)
    redacted = _OPENAI_KEY_RE.sub(_REDACTED, redacted)
    redacted = redacted.replace("\r", " ").replace("\n", " ")
    return _bound_text(redacted, limit)


def _exception_identity(exception: BaseException) -> tuple[str, str, bool]:
    module, module_truncated = _bound_text(
        type(exception).__module__ or "unknown", MAX_EXCEPTION_IDENTITY_BYTES
    )
    class_name, class_truncated = _bound_text(
        type(exception).__qualname__ or "unknown", MAX_EXCEPTION_IDENTITY_BYTES
    )
    qualified, qualified_truncated = _bound_text(
        f"{module}.{class_name}", MAX_EXCEPTION_IDENTITY_BYTES
    )
    return qualified, module, (
        module_truncated or class_truncated or qualified_truncated
    )


def _exception_entry(exception: BaseException) -> tuple[dict[str, str], bool]:
    raw_message = _exception_message(exception)
    message_redacted, message_truncated = redact_exception_message(
        raw_message, limit=MAX_CHAIN_MESSAGE_BYTES
    )
    exception_type, exception_module, identity_truncated = _exception_identity(
        exception
    )
    return (
        {
            "exception_type": exception_type,
            "exception_module": exception_module,
            "message_redacted": message_redacted,
            "message_sha256": _message_sha256(raw_message),
        },
        message_truncated or identity_truncated,
    )


def _exception_chain(exception: BaseException) -> tuple[list[dict[str, str]], bool]:
    """Capture explicit cause first, otherwise implicit context, without cycles."""
    entries: list[dict[str, str]] = []
    truncated = False
    seen = {id(exception)}
    current = exception.__cause__ or exception.__context__
    while current is not None and id(current) not in seen:
        if len(entries) >= MAX_CHAIN_ENTRIES:
            truncated = True
            break
        seen.add(id(current))
        entry, entry_truncated = _exception_entry(current)
        entries.append(entry)
        truncated = truncated or entry_truncated
        current = current.__cause__ or current.__context__
    if current is not None:
        truncated = True
    return entries, truncated


def _normalized_frame_path(filename: str) -> tuple[str, bool]:
    normalized = filename.replace("\\", "/")
    try:
        relative = os.path.relpath(filename, os.getcwd()).replace("\\", "/")
    except ValueError:
        relative = normalized
    if relative and not relative.startswith("../"):
        normalized = f"<workspace>/{relative.lstrip('./')}"
    return _bound_text(normalized, MAX_FRAME_PATH_BYTES)


def _frames(exception: BaseException) -> tuple[list[dict[str, Any]], bool]:
    extracted = traceback.extract_tb(exception.__traceback__)
    retained = extracted[-MAX_FRAMES:]
    truncated = len(extracted) > len(retained)
    frames: list[dict[str, Any]] = []
    for frame in retained:
        filename, path_truncated = _normalized_frame_path(frame.filename)
        function, function_truncated = _bound_text(
            frame.name, MAX_FRAME_FUNCTION_BYTES
        )
        frames.append(
            {
                "path": filename,
                "function": function,
                "line": int(frame.lineno),
            }
        )
        truncated = truncated or path_truncated or function_truncated
    return frames, truncated


def _timestamp_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def build_startup_failure_receipt(
    exception: BaseException,
    *,
    startup_phase: str = STARTUP_PHASE_APPLICATION_LIFESPAN,
) -> dict[str, Any]:
    """Build one schema-stable startup receipt without emitting it."""
    raw_message = _exception_message(exception)
    message_redacted, message_truncated = redact_exception_message(raw_message)
    exception_type, exception_module, identity_truncated = _exception_identity(
        exception
    )
    chain, chain_truncated = _exception_chain(exception)
    frames, frames_truncated = _frames(exception)
    phase, phase_truncated = _bound_text(startup_phase, MAX_STARTUP_PHASE_BYTES)
    return {
        "schema_version": SCHEMA_VERSION,
        "event": EVENT,
        "timestamp_utc": _timestamp_utc(),
        "startup_phase": phase,
        "exception_type": exception_type,
        "exception_module": exception_module,
        "message_redacted": message_redacted,
        "message_sha256": _message_sha256(raw_message),
        "exception_chain": chain,
        "frames": frames,
        "truncated": bool(
            message_truncated
            or identity_truncated
            or chain_truncated
            or frames_truncated
            or phase_truncated
        ),
    }


def serialize_startup_failure_receipt(receipt: dict[str, Any]) -> str:
    """Serialize a receipt as one bounded JSON line.

    Field-level limits normally keep the receipt under the global ceiling. The
    defensive reduction path maintains required schema fields if future callers
    provide unusually large but valid exception structures.
    """
    payload = dict(receipt)
    payload["exception_chain"] = list(payload.get("exception_chain", []))[  # type: ignore[arg-type]
        :MAX_CHAIN_ENTRIES
    ]
    payload["frames"] = list(payload.get("frames", []))[:MAX_FRAMES]  # type: ignore[arg-type]

    def encode() -> str:
        return json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )

    serialized = encode()
    if len(serialized.encode("utf-8")) <= MAX_RECEIPT_BYTES:
        return serialized

    payload["truncated"] = True
    payload["frames"] = payload["frames"][:8]
    payload["exception_chain"] = payload["exception_chain"][:4]
    for entry in payload["exception_chain"]:
        entry["message_redacted"], _ = _bound_text(
            entry.get("message_redacted", ""), 128
        )
    payload["message_redacted"], _ = _bound_text(
        payload.get("message_redacted", ""), 256
    )
    serialized = encode()
    if len(serialized.encode("utf-8")) <= MAX_RECEIPT_BYTES:
        return serialized

    payload["frames"] = []
    payload["exception_chain"] = payload["exception_chain"][:1]
    payload["message_redacted"], _ = _bound_text(
        payload.get("message_redacted", ""), 64
    )
    serialized = encode()
    if len(serialized.encode("utf-8")) > MAX_RECEIPT_BYTES:
        raise ValueError("startup failure receipt exceeds the bounded schema")
    return serialized


def _write_line(line: str, *, stream: TextIO | None = None) -> None:
    output = stream if stream is not None else sys.stderr
    output.write(f"{line}\n")
    output.flush()


def emit_startup_failure_receipt(
    exception: BaseException,
    *,
    startup_phase: str = STARTUP_PHASE_APPLICATION_LIFESPAN,
    stream: TextIO | None = None,
) -> dict[str, Any]:
    """Emit one secret-safe JSON receipt to the ordinary stderr log surface."""
    receipt = build_startup_failure_receipt(
        exception, startup_phase=startup_phase
    )
    _write_line(
        f"{RECEIPT_PREFIX}{serialize_startup_failure_receipt(receipt)}",
        stream=stream,
    )
    return receipt


def emit_startup_failure_receipt_fallback(
    *, stream: TextIO | None = None
) -> None:
    """Best-effort fixed fallback that cannot carry exception or secret data."""
    try:
        _write_line(FALLBACK_LINE, stream=stream)
    except BaseException:
        pass


ReceiptEmitter = Callable[..., dict[str, Any]]


@asynccontextmanager
async def startup_failure_receipt_boundary(
    lifespan: AbstractAsyncContextManager[Any],
    *,
    startup_phase: str = STARTUP_PHASE_APPLICATION_LIFESPAN,
    stream: TextIO | None = None,
    emitter: ReceiptEmitter = emit_startup_failure_receipt,
) -> AsyncIterator[None]:
    """Instrument only ``lifespan.__aenter__`` and preserve all semantics.

    The explicit ``__aenter__`` boundary is what separates application startup
    from application runtime and shutdown. It emits once for an unhandled
    startup exception, re-raises that exact exception, and delegates normal
    shutdown semantics to the wrapped context manager unchanged.
    """
    try:
        await lifespan.__aenter__()
    except BaseException as exception:
        try:
            emitter(exception, startup_phase=startup_phase, stream=stream)
        except BaseException:
            emit_startup_failure_receipt_fallback(stream=stream)
        raise

    try:
        yield
    except BaseException as exception:
        suppress = await lifespan.__aexit__(
            type(exception), exception, exception.__traceback__
        )
        if not suppress:
            raise
    else:
        await lifespan.__aexit__(None, None, None)
