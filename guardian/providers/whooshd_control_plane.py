"""Codexify-side reader for the versioned Whoosh'd control-plane contract."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

WHOOSHD_CONTROL_PLANE_VERSION = "whooshd.control.v1"
WHOOSHD_CONTROL_VERSION_HEADER = "X-Whooshd-Contract-Version"
WHOOSHD_RUNTIME_PROVENANCE_SCHEMA = "whooshd.runtime.v1"
WHOOSHD_RUNTIME_PROVENANCE_HEADER = "X-Whooshd-Runtime-Provenance"
WHOOSHD_REQUEST_ID_HEADER = "X-Whooshd-Request-ID"
CODEXIFY_TASK_ID_HEADER = "X-Codexify-Task-ID"
CODEXIFY_ATTEMPT_ID_HEADER = "X-Codexify-Attempt-ID"

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
_SAFE_MODEL_CAPABILITIES = frozenset(
    {"chat", "streaming", "json", "tools", "embeddings", "reasoning", "vision"}
)
_RUNTIME_FIELD_NAMES = (
    "request_id",
    "correlation_id",
    "codexify_task_id",
    "codexify_attempt_id",
    "whooshd_request_id",
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
_SAFE_CORRELATION_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SAFE_ATTESTATION_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ATTESTATION_REFERENCE_FIELDS = (
    "attestation_schema_version",
    "canonicalization_profile",
    "digest_algorithm",
    "attestation_digest",
    "invocation_model_id",
    "resolved_model_id",
    "runtime_kind",
    "adapter_name",
)


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
    correlation_id: str | None = None
    codexify_task_id: str | None = None
    codexify_attempt_id: str | None = None
    whooshd_request_id: str | None = None

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
        for key, value in {
            "correlation_id": self.correlation_id,
            "codexify_task_id": self.codexify_task_id,
            "codexify_attempt_id": self.codexify_attempt_id,
            "whooshd_request_id": self.whooshd_request_id,
        }.items():
            if value:
                payload[key] = value
        return payload


@dataclass(frozen=True)
class WhooshdQualificationAttestationReference:
    """Bounded target-attestation reference carried by runtime provenance."""

    attestation_schema_version: str
    canonicalization_profile: str
    digest_algorithm: str
    attestation_digest: str
    invocation_model_id: str
    resolved_model_id: str
    runtime_kind: str
    adapter_name: str

    def as_dict(self) -> dict[str, str]:
        return {
            "attestation_schema_version": self.attestation_schema_version,
            "canonicalization_profile": self.canonicalization_profile,
            "digest_algorithm": self.digest_algorithm,
            "attestation_digest": self.attestation_digest,
            "invocation_model_id": self.invocation_model_id,
            "resolved_model_id": self.resolved_model_id,
            "runtime_kind": self.runtime_kind,
            "adapter_name": self.adapter_name,
        }


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
    correlation_id: str | None = None
    codexify_task_id: str | None = None
    codexify_attempt_id: str | None = None
    whooshd_request_id: str | None = None
    qualification_attestation: WhooshdQualificationAttestationReference | None = None
    qualification_attestation_malformed: bool = False

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
                "correlation_id": self.correlation_id,
                "codexify_task_id": self.codexify_task_id,
                "codexify_attempt_id": self.codexify_attempt_id,
                "whooshd_request_id": self.whooshd_request_id,
                "qualification_attestation": (
                    self.qualification_attestation.as_dict()
                    if self.qualification_attestation is not None
                    else None
                ),
            }.items()
            if value is not None
        }


def _parse_qualification_attestation_reference(
    raw: Any,
) -> WhooshdQualificationAttestationReference | None:
    """Accept one complete, content-free attestation reference shape only."""

    if not isinstance(raw, dict) or set(raw) != set(_ATTESTATION_REFERENCE_FIELDS):
        return None
    values: dict[str, str] = {}
    for field in _ATTESTATION_REFERENCE_FIELDS:
        value = raw.get(field)
        if not isinstance(value, str):
            return None
        if not value or len(value) > 256 or not _SAFE_RUNTIME_TEXT_RE.fullmatch(value):
            return None
        if _PRIVATE_OR_URL_RE.search(value):
            return None
        values[field] = value
    if not _SAFE_ATTESTATION_DIGEST_RE.fullmatch(values["attestation_digest"]):
        return None
    return WhooshdQualificationAttestationReference(**values)


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
        if name in {
            "correlation_id",
            "codexify_task_id",
            "codexify_attempt_id",
            "whooshd_request_id",
        } and not _SAFE_CORRELATION_ID_RE.fullmatch(value):
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
    raw_attestation = raw.get("qualification_attestation")
    attestation_present = "qualification_attestation" in raw
    qualification_attestation = _parse_qualification_attestation_reference(
        raw_attestation
    )
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
        correlation_id=text_values["correlation_id"],
        codexify_task_id=text_values["codexify_task_id"],
        codexify_attempt_id=text_values["codexify_attempt_id"],
        whooshd_request_id=text_values["whooshd_request_id"],
        qualification_attestation=qualification_attestation,
        qualification_attestation_malformed=(
            attestation_present and qualification_attestation is None
        ),
    )


def _safe_correlation_id(value: Any) -> str | None:
    candidate = value.strip() if isinstance(value, str) else ""
    return candidate if _SAFE_CORRELATION_ID_RE.fullmatch(candidate) else None


def _response_header(response: Any, name: str) -> str | None:
    headers = getattr(response, "headers", None) or {}
    value = headers.get(name) or headers.get(name.lower())
    return _safe_correlation_id(str(value).strip()) if value is not None else None


def parse_whooshd_response_correlation(response: Any) -> dict[str, str]:
    """Read only bounded correlation headers from a Whoosh'd response."""

    values = {
        "correlation_id": _response_header(response, "X-Request-ID"),
        "whooshd_request_id": _response_header(response, WHOOSHD_REQUEST_ID_HEADER),
        "codexify_task_id": _response_header(response, CODEXIFY_TASK_ID_HEADER),
        "codexify_attempt_id": _response_header(
            response, CODEXIFY_ATTEMPT_ID_HEADER
        ),
    }
    return {key: value for key, value in values.items() if value}


_RESPONSE_CORRELATION_FIELDS = (
    "correlation_id",
    "whooshd_request_id",
    "codexify_task_id",
    "codexify_attempt_id",
)


def bounded_response_correlation(values: Any) -> dict[str, str]:
    """Re-apply the bounded correlation filter to a pre-built mapping.

    Used when correlation metadata crosses a persistence or retry boundary:
    a stored dict is not trusted merely because it was previously shaped
    like ``parse_whooshd_response_correlation`` output.
    """

    if not isinstance(values, dict):
        return {}
    bounded: dict[str, str] = {}
    for field in _RESPONSE_CORRELATION_FIELDS:
        validated = _safe_correlation_id(values.get(field))
        if validated:
            bounded[field] = validated
    return bounded


def merge_whooshd_response_correlation(
    provenance: WhooshdRuntimeProvenance | None,
    response: Any,
) -> WhooshdRuntimeProvenance | None:
    """Merge safe response headers without trusting arbitrary upstream data."""

    if provenance is None:
        return None
    return replace(provenance, **parse_whooshd_response_correlation(response))


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


def parse_whooshd_error(
    response: Any,
    *,
    include_body: bool = True,
) -> WhooshdErrorDiagnostic | None:
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
    if not include_body:
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
    correlation = {
        name: _safe_correlation_id(envelope.get(name))
        for name in (
            "correlation_id",
            "codexify_task_id",
            "codexify_attempt_id",
            "whooshd_request_id",
        )
    }
    return WhooshdErrorDiagnostic(
        contract_version=WHOOSHD_CONTROL_PLANE_VERSION,
        code=code,
        http_status=http_status,
        retryable=bool(envelope.get("retryable")),
        retry_after_seconds=retry_after_value,
        request_id=_safe_correlation_id(request_id),
        category=str(category)[:80] if category else None,
        **{key: value for key, value in correlation.items() if value},
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


# ── Runtime inventory evidence (Stage 2G pre-request surface) ──────────────


@dataclass(frozen=True)
class WhooshdQualificationInventoryAttestation:
    """Bounded full attestation carried by one runtime inventory entry.

    Codexify only consumes the inventory copy of the material identity and the
    producer-emitted digest.  It re-canonicalizes the material with the existing
    Stage 2F.1b canonicalizer and recomputes the digest; an inventory copy that
    fails either check is rejected as ``attestation_inconsistent``.
    """

    attestation_schema_version: str
    canonicalization_profile: str
    digest_algorithm: str
    attestation_digest: str
    invocation_model_id: str
    resolved_model_id: str
    artifact_identity_kind: str
    artifact_identity_value: str
    quantization: str
    runtime_kind: str
    adapter_name: str
    adapter_semantic_build: str
    whooshd_build_identity: str
    serving_runtime_package: str
    serving_runtime_version: str
    structured_decoder_package: str
    structured_decoder_version: str
    tokenizer_implementation: str
    tokenizer_identity_fingerprint: str
    chat_template_fingerprint: str
    tool_template_parser_relationship: str
    tool_template_parser_identity_fingerprint: str
    structured_transport_mode: str
    structured_transport_protocol_version: str
    qualification_protocol_version: str

    def as_identity_document(self) -> dict[str, object]:
        """Return a fresh v1 material document for canonicalization."""

        return {
            "attestation_schema_version": self.attestation_schema_version,
            "canonicalization_profile": self.canonicalization_profile,
            "invocation_model_id": self.invocation_model_id,
            "resolved_model_id": self.resolved_model_id,
            "artifact_identity": {
                "kind": self.artifact_identity_kind,
                "value": self.artifact_identity_value,
            },
            "quantization": self.quantization,
            "runtime_kind": self.runtime_kind,
            "adapter": {
                "name": self.adapter_name,
                "semantic_build": self.adapter_semantic_build,
            },
            "whooshd_build_identity": self.whooshd_build_identity,
            "serving_runtime": {
                "package": self.serving_runtime_package,
                "version": self.serving_runtime_version,
            },
            "structured_decoder": {
                "package": self.structured_decoder_package,
                "version": self.structured_decoder_version,
            },
            "tokenizer": {
                "implementation": self.tokenizer_implementation,
                "identity_fingerprint": self.tokenizer_identity_fingerprint,
            },
            "chat_template_fingerprint": self.chat_template_fingerprint,
            "tool_template_parser": {
                "relationship": self.tool_template_parser_relationship,
                "identity_fingerprint": (
                    self.tool_template_parser_identity_fingerprint
                ),
            },
            "structured_transport": {
                "mode": self.structured_transport_mode,
                "protocol_version": self.structured_transport_protocol_version,
            },
            "qualification_protocol_version": (
                self.qualification_protocol_version
            ),
        }


@dataclass(frozen=True)
class WhooshdRuntimeInventoryEvidence:
    """Bounded one-row snapshot of the current Whoosh'd runtime inventory.

    This is a pre-request evidence carrier for Stage 2G capability projection.
    It carries enough identity, readiness, and attestation fields for the
    Stage 2F.1b comparator and the Stage 2G projection; raw paths, endpoints,
    PIDs, and arbitrary metadata are deliberately discarded during parsing.
    """

    invocation_model_id: str
    runtime_kind: str
    adapter_name: str
    loaded: bool
    model_lifecycle: str | None
    capabilities: tuple[str, ...]
    qualification_attestation: WhooshdQualificationInventoryAttestation | None
    qualification_attestation_malformed: bool = False
    resolution_source: str | None = None

    def is_ready(self) -> bool:
        """Return whether current inventory evidence proves admission-ready state.

        Ready means the current inventory entry reports both ``loaded=True``
        and ``model_lifecycle="ready"``.  Other lifecycle values — including
        ``generating``, ``warming``, ``degraded``, ``failed``, ``unloaded`` —
        are not eligible for a new structured-tool request.
        """

        return self.loaded and self.model_lifecycle == "ready"


_INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS = {
    "artifact_identity": ("kind", "value"),
    "adapter": ("name", "semantic_build"),
    "serving_runtime": ("package", "version"),
    "structured_decoder": ("package", "version"),
    "tokenizer": ("implementation", "identity_fingerprint"),
    "tool_template_parser": ("relationship", "identity_fingerprint"),
    "structured_transport": ("mode", "protocol_version"),
}


def _parse_inventory_text(raw: Any, *, name: str) -> str | None:
    """Apply the same bounded-text rules the runtime parser uses."""

    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value or len(value) > 256 or not _SAFE_RUNTIME_TEXT_RE.fullmatch(value):
        return None
    if _PRIVATE_OR_URL_RE.search(value):
        return None
    return value


def _parse_inventory_sub_object(
    raw: Any,
    expected_keys: tuple[str, ...],
    *,
    path: str,
) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    if set(raw) != set(expected_keys):
        return None
    bounded: dict[str, str] = {}
    for key in expected_keys:
        text = _parse_inventory_text(raw.get(key), name=f"{path}.{key}")
        if text is None:
            return None
        bounded[key] = text
    return bounded


def _parse_inventory_full_attestation(
    raw: Any,
) -> WhooshdQualificationInventoryAttestation | None:
    if not isinstance(raw, dict):
        return None
    bounded_text_fields = (
        "attestation_schema_version",
        "canonicalization_profile",
        "invocation_model_id",
        "resolved_model_id",
        "quantization",
        "runtime_kind",
        "whooshd_build_identity",
        "chat_template_fingerprint",
        "qualification_protocol_version",
    )
    expected_keys = set(bounded_text_fields).union(
        {"digest_algorithm", "attestation_digest"},
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS.keys(),
    )
    if set(raw) != expected_keys:
        return None
    values: dict[str, str] = {}
    for field in bounded_text_fields:
        text = _parse_inventory_text(raw.get(field), name=field)
        if text is None:
            return None
        values[field] = text
    digest_algorithm = _parse_inventory_text(
        raw.get("digest_algorithm"), name="digest_algorithm"
    )
    if digest_algorithm is None:
        return None
    attestation_digest = _parse_inventory_text(
        raw.get("attestation_digest"), name="attestation_digest"
    )
    if attestation_digest is None:
        return None
    if not _SAFE_ATTESTATION_DIGEST_RE.fullmatch(attestation_digest):
        return None
    artifact = _parse_inventory_sub_object(
        raw.get("artifact_identity"),
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS["artifact_identity"],
        path="artifact_identity",
    )
    adapter = _parse_inventory_sub_object(
        raw.get("adapter"),
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS["adapter"],
        path="adapter",
    )
    serving = _parse_inventory_sub_object(
        raw.get("serving_runtime"),
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS["serving_runtime"],
        path="serving_runtime",
    )
    decoder = _parse_inventory_sub_object(
        raw.get("structured_decoder"),
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS["structured_decoder"],
        path="structured_decoder",
    )
    tokenizer = _parse_inventory_sub_object(
        raw.get("tokenizer"),
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS["tokenizer"],
        path="tokenizer",
    )
    parser = _parse_inventory_sub_object(
        raw.get("tool_template_parser"),
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS["tool_template_parser"],
        path="tool_template_parser",
    )
    transport = _parse_inventory_sub_object(
        raw.get("structured_transport"),
        _INVENTORY_ATTESTATION_SUB_OBJECT_FIELDS["structured_transport"],
        path="structured_transport",
    )
    if not all(
        (artifact, adapter, serving, decoder, tokenizer, parser, transport)
    ):
        return None
    assert (
        artifact and adapter and serving and decoder and tokenizer and parser and transport
    )
    return WhooshdQualificationInventoryAttestation(
        attestation_schema_version=values["attestation_schema_version"],
        canonicalization_profile=values["canonicalization_profile"],
        digest_algorithm=digest_algorithm,
        attestation_digest=attestation_digest,
        invocation_model_id=values["invocation_model_id"],
        resolved_model_id=values["resolved_model_id"],
        artifact_identity_kind=artifact["kind"],
        artifact_identity_value=artifact["value"],
        quantization=values["quantization"],
        runtime_kind=values["runtime_kind"],
        adapter_name=adapter["name"],
        adapter_semantic_build=adapter["semantic_build"],
        whooshd_build_identity=values["whooshd_build_identity"],
        serving_runtime_package=serving["package"],
        serving_runtime_version=serving["version"],
        structured_decoder_package=decoder["package"],
        structured_decoder_version=decoder["version"],
        tokenizer_implementation=tokenizer["implementation"],
        tokenizer_identity_fingerprint=tokenizer["identity_fingerprint"],
        chat_template_fingerprint=values["chat_template_fingerprint"],
        tool_template_parser_relationship=parser["relationship"],
        tool_template_parser_identity_fingerprint=parser["identity_fingerprint"],
        structured_transport_mode=transport["mode"],
        structured_transport_protocol_version=transport["protocol_version"],
        qualification_protocol_version=values["qualification_protocol_version"],
    )


def parse_whooshd_runtime_inventory_entry(
    raw: Any,
) -> WhooshdRuntimeInventoryEvidence | None:
    """Parse one bounded entry from the current Whoosh'd runtime inventory.

    The parser accepts the ``ModelInfo`` payload shape emitted by Whoosh'd
    ``d08e3261`` from either the adapter-loaded inventory path or any
    future equivalent that exposes the bounded qualification attestation.
    Raw paths, endpoints, PIDs, and arbitrary unrelated metadata are not
    part of the contract and are intentionally dropped.
    """

    if not isinstance(raw, dict):
        return None
    invocation_model_id = _parse_inventory_text(
        raw.get("id"), name="id"
    )
    if invocation_model_id is None:
        return None
    loaded = raw.get("loaded")
    if not isinstance(loaded, bool):
        return None
    runtime_provenance_raw = raw.get("runtime_provenance")
    runtime_kind: str | None = None
    adapter_name: str | None = None
    resolution_source: str | None = None
    if isinstance(runtime_provenance_raw, dict):
        runtime_kind = _parse_inventory_text(
            runtime_provenance_raw.get("runtime_kind"),
            name="runtime_provenance.runtime_kind",
        )
        adapter_name = _parse_inventory_text(
            runtime_provenance_raw.get("adapter_name"),
            name="runtime_provenance.adapter_name",
        )
        resolution_source = _parse_inventory_text(
            runtime_provenance_raw.get("resolution_source"),
            name="runtime_provenance.resolution_source",
        )
    if runtime_kind is None:
        runtime_kind = _parse_inventory_text(raw.get("runtime_kind"), name="runtime_kind")
    if adapter_name is None:
        adapter_name = _parse_inventory_text(raw.get("adapter_name"), name="adapter_name")
    if runtime_kind is None or runtime_kind not in _SAFE_RUNTIME_KINDS:
        return None
    if adapter_name is None or not adapter_name:
        return None
    if (
        resolution_source is not None
        and resolution_source not in _SAFE_RESOLUTION_SOURCES
    ):
        return None
    lifecycle = _parse_inventory_text(raw.get("model_lifecycle"), name="model_lifecycle")
    if lifecycle is not None and lifecycle not in _SAFE_LIFECYCLE_STATES:
        lifecycle = None
    capabilities_raw = raw.get("capabilities")
    bounded_capabilities: list[str] = []
    if isinstance(capabilities_raw, list):
        for entry in capabilities_raw:
            text = _parse_inventory_text(entry, name="capabilities")
            if text is None or text not in _SAFE_MODEL_CAPABILITIES:
                return None
            if text not in bounded_capabilities:
                bounded_capabilities.append(text)
    raw_attestation = raw.get("qualification_attestation")
    attestation_present = "qualification_attestation" in raw
    attestation = _parse_inventory_full_attestation(raw_attestation)
    return WhooshdRuntimeInventoryEvidence(
        invocation_model_id=invocation_model_id,
        runtime_kind=runtime_kind,
        adapter_name=adapter_name,
        loaded=loaded,
        model_lifecycle=lifecycle,
        capabilities=tuple(bounded_capabilities),
        qualification_attestation=attestation,
        qualification_attestation_malformed=(
            attestation_present and attestation is None
        ),
        resolution_source=resolution_source,
    )
