"""Codexify-side reader for the versioned Whoosh'd control-plane contract."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


WHOOSHD_CONTROL_PLANE_VERSION = "whooshd.control.v1"
WHOOSHD_CONTROL_VERSION_HEADER = "X-Whooshd-Contract-Version"
WHOOSHD_RUNTIME_PROVENANCE_SCHEMA = "whooshd.runtime.v1"
WHOOSHD_RUNTIME_PROVENANCE_HEADER = "X-Whooshd-Runtime-Provenance"

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
_VERSION_RE = re.compile(r"^whooshd\.control\.v[0-9]+$")
_SAFE_RUNTIME_KINDS = frozenset(
    {"stub", "mlx_lm", "mlx_lm_server", "mlx_vlm", "llama_cpp"}
)
_SAFE_RESOLUTION_SOURCES = frozenset(
    {
        "authoritative_registry",
        "external_route",
        "format_heuristic",
        "loaded_model_match",
        "configured_stub",
        "single_runtime_compatibility",
        "stub_only_compatibility",
    }
)
_SAFE_EXECUTION_MODES = frozenset(
    {"in_process", "managed_sidecar", "external_sidecar", "stub"}
)
_SAFE_LIFECYCLE_STATES = frozenset(
    {"unloaded", "warming", "ready", "generating", "degraded", "failed"}
)
_RUNTIME_FIELD_NAMES = (
    "request_id",
    "requested_model_id",
    "advertised_model_id",
    "resolved_model_id",
    "backend_reported_model_id",
    "runtime_kind",
    "adapter_name",
    "resolution_source",
    "execution_mode",
    "streaming",
    "queued",
    "batched",
    "model_lifecycle",
    "whooshd_version",
)
_PRIVATE_OR_URL_RE = re.compile(r"(?:^[/~]|^[A-Za-z]:[\\/]|://|[?&#])")
_SAFE_RUNTIME_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


class WhooshdContractVersionError(ValueError):
    """An explicitly declared, unsupported Whoosh'd response version."""

    code = "contract_version_unsupported"

    def __init__(self, received_version: str):
        self.received_version = received_version
        super().__init__(self.code)


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


@dataclass(frozen=True)
class WhooshdRuntimeProvenance:
    """Content-free runtime evidence accepted from Whoosh'd v1 responses."""

    schema_version: str
    request_id: str | None
    requested_model_id: str | None
    advertised_model_id: str | None
    resolved_model_id: str | None
    backend_reported_model_id: str | None
    runtime_kind: str
    adapter_name: str
    resolution_source: str
    execution_mode: str
    streaming: bool
    queued: bool
    batched: bool
    model_lifecycle: str | None
    whooshd_version: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "schema_version": self.schema_version,
                "request_id": self.request_id,
                "requested_model_id": self.requested_model_id,
                "advertised_model_id": self.advertised_model_id,
                "resolved_model_id": self.resolved_model_id,
                "backend_reported_model_id": self.backend_reported_model_id,
                "runtime_kind": self.runtime_kind,
                "adapter_name": self.adapter_name,
                "resolution_source": self.resolution_source,
                "execution_mode": self.execution_mode,
                "streaming": self.streaming,
                "queued": self.queued,
                "batched": self.batched,
                "model_lifecycle": self.model_lifecycle,
                "whooshd_version": self.whooshd_version,
            }.items()
            if value is not None
        }


def parse_whooshd_runtime_provenance(raw: Any) -> WhooshdRuntimeProvenance | None:
    """Accept only the bounded, recognized runtime provenance schema."""
    if not isinstance(raw, dict):
        return None
    if raw.get("schema_version") != WHOOSHD_RUNTIME_PROVENANCE_SCHEMA:
        return None

    def _text(name: str, *, required: bool = False) -> str | None:
        value = raw.get(name)
        if value is None and not required:
            return None
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or len(value) > 256 or not _SAFE_RUNTIME_TEXT_RE.fullmatch(value):
            return None
        if _PRIVATE_OR_URL_RE.search(value):
            return None
        return value

    runtime_kind = _text("runtime_kind", required=True)
    adapter_name = _text("adapter_name", required=True)
    resolution_source = _text("resolution_source", required=True)
    execution_mode = _text("execution_mode", required=True)
    if (
        runtime_kind not in _SAFE_RUNTIME_KINDS
        or resolution_source not in _SAFE_RESOLUTION_SOURCES
        or execution_mode not in _SAFE_EXECUTION_MODES
    ):
        return None

    text_values = {
        name: _text(name)
        for name in _RUNTIME_FIELD_NAMES
        if name
        not in {
            "runtime_kind",
            "adapter_name",
            "resolution_source",
            "execution_mode",
            "streaming",
            "queued",
            "batched",
            "model_lifecycle",
        }
    }
    lifecycle = _text("model_lifecycle")
    if lifecycle is not None and lifecycle not in _SAFE_LIFECYCLE_STATES:
        return None
    bool_values: dict[str, bool] = {}
    for name in ("streaming", "queued", "batched"):
        value = raw.get(name, False)
        if not isinstance(value, bool):
            return None
        bool_values[name] = value
    if raw.get("model_lifecycle") is not None and lifecycle is None:
        return None
    for name, value in text_values.items():
        if raw.get(name) is not None and value is None:
            return None
    return WhooshdRuntimeProvenance(
        schema_version=WHOOSHD_RUNTIME_PROVENANCE_SCHEMA,
        request_id=text_values["request_id"],
        requested_model_id=text_values["requested_model_id"],
        advertised_model_id=text_values["advertised_model_id"],
        resolved_model_id=text_values["resolved_model_id"],
        backend_reported_model_id=text_values["backend_reported_model_id"],
        runtime_kind=runtime_kind,
        adapter_name=adapter_name,
        resolution_source=resolution_source,
        execution_mode=execution_mode,
        streaming=bool_values["streaming"],
        queued=bool_values["queued"],
        batched=bool_values["batched"],
        model_lifecycle=lifecycle,
        whooshd_version=text_values["whooshd_version"],
    )


def _header(response: Any, name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    if name in headers:
        value = headers.get(name)
    else:
        value = headers.get(name.lower())
    if value is None:
        return None
    candidate = str(value).strip()
    if len(candidate) > 80 or not _VERSION_RE.fullmatch(candidate):
        return "invalid"
    return candidate


def parse_whooshd_error(response: Any) -> WhooshdErrorDiagnostic | None:
    """Parse a v1 error only when the response explicitly declares v1.

    A missing version is intentionally treated as legacy rather than guessed
    to be v1. An explicit non-v1 version raises a bounded contract error so it
    cannot enter legacy fallback. The response body is never copied into the
    diagnostic; only bounded machine fields are retained.
    """

    response_version = _header(response, WHOOSHD_CONTROL_VERSION_HEADER)
    if response_version is None:
        return None
    if response_version != WHOOSHD_CONTROL_PLANE_VERSION:
        raise WhooshdContractVersionError(response_version)
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
    if code in {
        "invalid_request",
        "unsupported_field",
        "unsupported_capability",
        "contract_version_unsupported",
    }:
        return "request_error"
    if code == "model_not_found":
        return "local_model_unavailable"
    return "provider_http_error"
