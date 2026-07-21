"""Codexify-side reader for the versioned Whoosh'd control-plane contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


WHOOSHD_CONTROL_PLANE_VERSION = "whooshd.control.v1"
WHOOSHD_CONTROL_VERSION_HEADER = "X-Whooshd-Contract-Version"

_ERROR_CODES = frozenset(
    {
        "invalid_request",
        "unsupported_field",
        "unsupported_capability",
        "contract_version_unsupported",
        "model_not_found",
        "model_unavailable",
        "model_warming",
        "model_load_failed",
        "runtime_unavailable",
        "runtime_degraded",
        "runner_overloaded",
        "queue_full",
        "timeout",
        "cancelled",
        "context_overflow",
        "upstream_unavailable",
        "upstream_timeout",
        "upstream_protocol_error",
        "stream_interrupted",
        "malformed_upstream_response",
        "internal_error",
    }
)


@dataclass(frozen=True)
class WhooshdErrorDiagnostic:
    """Content-free canonical error metadata consumed by Guardian."""

    contract_version: str
    code: str
    http_status: int
    retryable: bool
    retry_after_seconds: float | None
    request_id: str | None
    category: str | None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "contract_version": self.contract_version,
            "code": self.code,
            "http_status": self.http_status,
            "retryable": self.retryable,
        }
        if self.retry_after_seconds is not None:
            payload["retry_after_seconds"] = self.retry_after_seconds
        if self.request_id:
            payload["request_id"] = self.request_id
        if self.category:
            payload["category"] = self.category
        return payload


def _header(response: Any, name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    value = headers.get(name) or headers.get(name.lower())
    return str(value).strip()[:80] if value else None


def parse_whooshd_error(response: Any) -> WhooshdErrorDiagnostic | None:
    """Parse a v1 error only when the response explicitly declares v1.

    A missing or unknown version is intentionally treated as legacy rather
    than guessed to be v1.  The response body is never copied into the
    diagnostic; only bounded machine fields are retained.
    """

    if _header(response, WHOOSHD_CONTROL_VERSION_HEADER) != WHOOSHD_CONTROL_PLANE_VERSION:
        return None
    try:
        body = response.json()
    except Exception:
        return None
    if not isinstance(body, dict):
        return None
    envelope = body.get("error") if isinstance(body.get("error"), dict) else body
    if not isinstance(envelope, dict):
        return None
    code = str(envelope.get("code") or "").strip()
    if code not in _ERROR_CODES:
        return None
    try:
        http_status = int(envelope.get("http_status") or response.status_code)
    except (TypeError, ValueError):
        http_status = int(getattr(response, "status_code", 502) or 502)
    retry_after = envelope.get("retry_after_seconds")
    try:
        retry_after_value = (
            max(0.0, min(float(retry_after), 60.0))
            if retry_after is not None
            else None
        )
    except (TypeError, ValueError):
        retry_after_value = None
    request_id = envelope.get("request_id")
    category = envelope.get("category")
    return WhooshdErrorDiagnostic(
        contract_version=WHOOSHD_CONTROL_PLANE_VERSION,
        code=code,
        http_status=http_status,
        retryable=bool(envelope.get("retryable")),
        retry_after_seconds=retry_after_value,
        request_id=str(request_id)[:128] if request_id else None,
        category=str(category)[:80] if category else None,
    )


def provider_failure_kind(code: str) -> str:
    """Map v1 codes into Guardian's existing provider failure categories."""

    if code in {"timeout", "upstream_timeout"}:
        return "provider_timeout"
    if code in {"upstream_unavailable", "runtime_unavailable", "model_unavailable"}:
        return "transport_error"
    if code in {"invalid_request", "unsupported_field", "unsupported_capability"}:
        return "request_error"
    if code == "model_not_found":
        return "local_model_unavailable"
    return "provider_http_error"
