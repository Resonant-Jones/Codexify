"""Bounded request-correlation identifiers for completion execution."""

from __future__ import annotations

import re
import uuid
from typing import Any


MAX_IDENTIFIER_LENGTH = 128
SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def is_safe_identifier(value: Any) -> bool:
    """Return whether *value* is safe for headers and structured metadata."""

    return isinstance(value, str) and bool(SAFE_IDENTIFIER_RE.fullmatch(value))


def generate_request_id() -> str:
    """Generate a non-content-bearing root correlation identifier."""

    return f"req_{uuid.uuid4().hex}"


def generate_attempt_id() -> str:
    """Generate a new identifier for one provider execution attempt."""

    return f"attempt_{uuid.uuid4().hex}"


def normalize_request_id(value: Any) -> tuple[str, bool]:
    """Accept a bounded inbound root ID or replace it with a safe one."""

    candidate = value.strip() if isinstance(value, str) else ""
    if is_safe_identifier(candidate):
        return candidate, True
    return generate_request_id(), False


def normalize_optional_identifier(value: Any) -> str | None:
    """Return a bounded optional task/attempt identifier, otherwise None."""

    candidate = value.strip() if isinstance(value, str) else ""
    return candidate if is_safe_identifier(candidate) else None


def correlation_metadata(
    *,
    request_id: Any,
    task_id: Any,
    attempt_id: Any = None,
    whooshd_request_id: Any = None,
) -> dict[str, str]:
    """Build bounded correlation metadata without accepting arbitrary values."""

    result: dict[str, str] = {}
    root = normalize_optional_identifier(request_id)
    task = normalize_optional_identifier(task_id)
    attempt = normalize_optional_identifier(attempt_id)
    whooshd = normalize_optional_identifier(whooshd_request_id)
    if root:
        result["request_id"] = root
    if task:
        result["task_id"] = task
    if attempt:
        result["attempt_id"] = attempt
    if whooshd:
        result["whooshd_request_id"] = whooshd
    return result
