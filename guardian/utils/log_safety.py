"""Content- and credential-safe logging primitives.

Operational logs are a metadata surface.  This module is deliberately small
and dependency-free so it can be installed before application-specific loggers
are created.  It sanitizes records at creation time, which also protects test
handlers and third-party handlers that do not use Codexify's formatter.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit, urlunsplit

_REDACTED = "<redacted>"
_RECORD_SANITIZED_ATTR = "_codexify_log_sanitized"

_SAFE_FIELDS = {
    "attempt",
    "attempt_count",
    "audio_url_present",
    "acceptance_status",
    "acceptance_warnings",
    "assistant_text_length",
    "bytes",
    "chars",
    "concurrency",
    "content_part_counts",
    "content_present",
    "cause_class",
    "count",
    "depth",
    "duration_ms",
    "endpoint_kind",
    "error_code",
    "event_id",
    "event_type",
    "exception_type",
    "execution_continued",
    "failure_class",
    "failure_kind",
    "final_status",
    "finish_reason",
    "has_content",
    "has_images",
    "http_status",
    "item_count",
    "items",
    "message_count",
    "message_id",
    "model",
    "model_id",
    "name",
    "provider",
    "provider_name",
    "project_id",
    "queue",
    "queue_name",
    "request_id",
    "requestid",
    "retrieval_bundle",
    "retrieval_query_chars",
    "run_id",
    "status",
    "status_code",
    "task_event_error_code",
    "stream",
    "task_id",
    "task_type",
    "thread_id",
    "timeout",
    "timeout_seconds",
    "tool_turn_id",
    "transport",
    "transport_classification",
    "turn_id",
    "type",
    "depth_mode",
    "policy",
    "selection_source",
    "source",
    "user",
    "user_id",
    "visibility_scope",
    "worker",
}

_UNSAFE_FIELD_RE = re.compile(
    r"(?i)(?:prompt|content|output|response|body|payload|detail|error|err|"
    r"exception|exc|header|authorization|bearer|cookie|token|secret|key|"
    r"argument|args|kwargs|origin|candidate|result|trace|message)"
)
_PLACEHOLDER_RE = re.compile(
    r"%(?:\([^)]+\))?[#0\- +]?\d*(?:\.\d+)?[diouxXeEfFgGcrsa%]"
)
_FIELD_RE = re.compile(r"([A-Za-z][A-Za-z0-9_.-]*)\s*(?:=|:)\s*$")
_AUTH_RE = re.compile(
    r"(?i)(\b(?:authorization\s*:\s*(?:bearer|basic)|bearer)\s+)[^\s,;]+"
)
_COOKIE_RE = re.compile(r"(?i)(\bcookie\s*:\s*)[^\r\n]+")
_QUERY_RE = re.compile(
    r"([?&](?:api[_-]?key|token|secret|code|auth|signature)=[^\s&#]+)", re.I
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|session[_-]?secret|"
    r"password|client[_-]?secret)\s*[=:]\s*)[^\s,;]+"
)

_LOG_RECORD_STANDARD_FIELDS = set(
    logging.LogRecord("_", logging.INFO, __file__, 0, "", (), None).__dict__
)

_factory_installed = False
_original_factory = logging.getLogRecordFactory()
_make_record_installed = False
_original_make_record = logging.Logger.makeRecord


def _field_name(
    template: str, match_start: int, previous_end: int
) -> str | None:
    prefix = template[previous_end:match_start]
    match = _FIELD_RE.search(prefix)
    return match.group(1).lower() if match else None


def _placeholder_fields(template: str) -> list[str | None]:
    fields: list[str | None] = []
    previous_end = 0
    for match in _PLACEHOLDER_RE.finditer(template):
        if match.group(0) == "%%":
            previous_end = match.end()
            continue
        fields.append(_field_name(template, match.start(), previous_end))
        previous_end = match.end()
    return fields


def _safe_url(value: str) -> str:
    """Keep endpoint identity while dropping userinfo, query, and fragment."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return _REDACTED
    if not parsed.scheme or not parsed.netloc:
        return _REDACTED
    try:
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port is not None else ""
    except ValueError:
        return _REDACTED
    return urlunsplit((parsed.scheme, f"{host}{port}", parsed.path, "", ""))[
        :256
    ]


def _failure_class(exception: BaseException) -> str:
    name = exception.__class__.__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "connection" in name or "connect" in name:
        return "connection"
    if "http" in name or "response" in name or "status" in name:
        return "http"
    if "json" in name or "parse" in name or "decode" in name:
        return "parse"
    if "permission" in name or "auth" in name:
        return "authorization"
    if "validation" in name or "value" in name or "key" in name:
        return "validation"
    return "runtime"


def exception_metadata(exception: BaseException | None) -> str:
    """Return exception type/classification without interpolating its message."""
    if exception is None:
        return "exception_type=unknown failure_class=unknown"
    return (
        f"exception_type={exception.__class__.__name__[:80]} "
        f"failure_class={_failure_class(exception)}"
    )


def _redacted_summary(value: Any) -> str:
    if isinstance(value, (bytes, bytearray, memoryview)):
        size = len(value)
        return f"{_REDACTED} bytes={size}"
    if isinstance(value, str):
        size = len(value)
    elif isinstance(value, Mapping):
        size = len(value)
    elif isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        size = len(value)
    else:
        size = None
    if size is None:
        return _REDACTED
    return (
        f"{_REDACTED} chars={size}"
        if isinstance(value, str)
        else f"{_REDACTED} items={size}"
    )


def _is_unsafe_field(field: str | None) -> bool:
    return bool(field and _UNSAFE_FIELD_RE.search(field))


def _sanitize_value(value: Any, field: str | None = None) -> Any:
    normalized_field = field.lower() if field else None
    if isinstance(value, BaseException):
        return exception_metadata(value)
    if normalized_field in {"endpoint", "url", "base_url", "health_base"}:
        return _safe_url(str(value))
    if normalized_field in _SAFE_FIELDS:
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value.replace("\n", " ").replace("\r", " ")[:256]
        if isinstance(value, Mapping):
            if normalized_field == "retrieval_bundle":
                return {
                    str(key): _sanitize_value(item, str(key))
                    for key, item in value.items()
                    if str(key).lower()
                    in {
                        "present",
                        "semantic",
                        "memory",
                        "graph",
                        "personal_facts",
                        "verified_personal_facts",
                        "retrieval_query_chars",
                    }
                }
            return {"items": len(value)}
        if isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            if normalized_field == "content_part_counts":
                return [int(item) for item in value if isinstance(item, int)][
                    :32
                ]
            return {"items": len(value)}
        return str(value)[:128]
    if _is_unsafe_field(normalized_field):
        return _redacted_summary(value)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return _redacted_summary(value)
    if isinstance(value, Mapping):
        return _redacted_summary(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return _redacted_summary(value)
    if isinstance(value, Sequence):
        return _redacted_summary(value)
    return _REDACTED


def _sanitize_args(template: Any, args: Any) -> Any:
    if isinstance(args, Mapping):
        return {
            str(key): _sanitize_value(value, str(key))
            for key, value in args.items()
        }
    if not isinstance(args, tuple):
        return _sanitize_value(args)
    fields = _placeholder_fields(str(template))
    sanitized: list[Any] = []
    field_index = 0
    for value in args:
        if field_index < len(fields):
            field = fields[field_index]
            field_index += 1
        else:
            field = None
        sanitized.append(_sanitize_value(value, field))
    return tuple(sanitized)


def sanitize_log_text(text: str) -> str:
    """Apply last-mile secret scrubbing to already-rendered log text."""
    output = _AUTH_RE.sub(r"\1<redacted>", text)
    output = _COOKIE_RE.sub(r"\1<redacted>", output)
    output = _QUERY_RE.sub("<redacted-query>", output)
    output = _SECRET_ASSIGNMENT_RE.sub(r"\1<redacted>", output)
    return output


def _sanitize_freeform_message(message: Any) -> str:
    if not isinstance(message, str):
        return _redacted_summary(message)
    scrubbed = sanitize_log_text(message)
    lowered = scrubbed.lower()
    content_markers = (
        "raw_output",
        "prompt=",
        "content=",
        "payload=",
        "response_body",
        "request_body",
        "tool_args",
        "tool_output",
        "authorization:",
        "bearer ",
        "cookie:",
    )
    if len(scrubbed) > 200 or any(
        marker in lowered for marker in content_markers
    ):
        return f"log_event={_REDACTED} chars={len(message)}"
    # A free-form message can itself be a prompt/result.  Preserve only the
    # conventional static event forms; dynamic callers must use arguments.
    if not (
        re.fullmatch(
            r"\[[A-Za-z0-9_.:-]+\]\s+(?:started|stopped|failed|ready|"
            r"available|disabled|enabled|cancelled)",
            scrubbed,
            re.I,
        )
        or re.fullmatch(r"[A-Za-z0-9_.:-]+", scrubbed)
        or re.fullmatch(
            r"[A-Za-z0-9_.:-]+\s+(?:started|stopped|failed|ready|available|disabled|enabled|cancelled)",
            scrubbed,
            re.I,
        )
    ):
        return f"log_event={_REDACTED} chars={len(message)}"
    return scrubbed


def sanitize_record(
    record: logging.LogRecord, *, force: bool = False
) -> logging.LogRecord:
    if getattr(record, _RECORD_SANITIZED_ATTR, False) and not force:
        return record
    original_message = record.msg
    if record.args:
        record.args = _sanitize_args(record.msg, record.args)
    else:
        record.msg = _sanitize_freeform_message(record.msg)

    if record.exc_info:
        exception = record.exc_info[1] if len(record.exc_info) > 1 else None
        suffix = exception_metadata(exception)
        if record.args:
            record.msg = f"{record.msg} {suffix}"
        else:
            record.msg = f"{record.msg} {suffix}"
        record.args = _sanitize_args(original_message, record.args)
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None

    for key, value in list(record.__dict__.items()):
        if key in _LOG_RECORD_STANDARD_FIELDS or key.startswith("_"):
            continue
        setattr(record, key, _sanitize_value(value, key))

    setattr(record, _RECORD_SANITIZED_ATTR, True)
    return record


class SafeLogFilter(logging.Filter):
    """Handler filter for integrations that bypass the installed factory."""

    def filter(self, record: logging.LogRecord) -> bool:
        sanitize_record(record, force=True)
        return True


def _safe_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    return sanitize_record(_original_factory(*args, **kwargs))


def _safe_make_record(
    logger: logging.Logger, *args: Any, **kwargs: Any
) -> logging.LogRecord:
    # Logger.makeRecord applies extra fields after invoking the record factory.
    # Sanitize again here so content or credential fields cannot bypass it.
    return sanitize_record(
        _original_make_record(logger, *args, **kwargs), force=True
    )


def install_safe_logging() -> None:
    """Install the process-wide record boundary once and protect current handlers."""
    global _factory_installed, _make_record_installed
    if not _factory_installed:
        logging.setLogRecordFactory(_safe_record_factory)
        _factory_installed = True
    if not _make_record_installed:
        logging.Logger.makeRecord = _safe_make_record
        _make_record_installed = True
    safe_filter = SafeLogFilter()
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(item, SafeLogFilter) for item in handler.filters):
            handler.addFilter(safe_filter)


def bounded_hash(value: Any) -> str:
    """Return a short correlation hash when a caller explicitly needs one."""
    encoded = str(value).encode("utf-8", errors="replace")
    return hashlib.sha256(encoded).hexdigest()[:16]
