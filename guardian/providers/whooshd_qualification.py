"""Static qualification evidence and comparison for one Whoosh'd target.

This module deliberately owns policy evidence, not live runtime discovery.  It
never reads proof documents, probes Whoosh'd, or inspects local packages or
model files during a completion.  Whoosh'd remains the producer of current
runtime evidence; Codexify only compares its bounded reference to this one
historical Stage 2D qualification record.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from guardian.providers.whooshd_control_plane import WhooshdRuntimeProvenance

ATTESTATION_SCHEMA_VERSION = "whooshd.qualification-attestation.v1"
CANONICALIZATION_PROFILE = "whooshd.qualification-attestation.canonical-json.v1"
DIGEST_ALGORITHM = "sha256"
QUALIFICATION_PROTOCOL_VERSION = "model-turn.strict-json-schema.v1"

_PLACEHOLDERS = frozenset({"unknown", "unavailable", "n/a"})
_V1_DOCUMENT_SPEC: dict[str, object] = {
    "attestation_schema_version": str,
    "canonicalization_profile": str,
    "invocation_model_id": str,
    "resolved_model_id": str,
    "artifact_identity": {"kind": str, "value": str},
    "quantization": str,
    "runtime_kind": str,
    "adapter": {"name": str, "semantic_build": str},
    "whooshd_build_identity": str,
    "serving_runtime": {"package": str, "version": str},
    "structured_decoder": {"package": str, "version": str},
    "tokenizer": {"implementation": str, "identity_fingerprint": str},
    "chat_template_fingerprint": str,
    "tool_template_parser": {"relationship": str, "identity_fingerprint": str},
    "structured_transport": {"mode": str, "protocol_version": str},
    "qualification_protocol_version": str,
}


class WhooshdQualificationCanonicalizationError(ValueError):
    """Raised when a v1 material identity cannot be canonically represented."""


class WhooshdQualificationOutcome(str, Enum):
    """Internal comparison classifications; these are not protocol tokens."""

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class WhooshdQualificationMaterial:
    """Complete Stage 2F identity material for one historical target."""

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
    attestation_schema_version: str = ATTESTATION_SCHEMA_VERSION
    canonicalization_profile: str = CANONICALIZATION_PROFILE

    def as_identity_document(self) -> dict[str, object]:
        """Return a fresh exact v1 material document for canonicalization."""

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
                "identity_fingerprint": self.tool_template_parser_identity_fingerprint,
            },
            "structured_transport": {
                "mode": self.structured_transport_mode,
                "protocol_version": self.structured_transport_protocol_version,
            },
            "qualification_protocol_version": self.qualification_protocol_version,
        }


@dataclass(frozen=True)
class WhooshdQualificationRecord:
    """Immutable Codexify policy record for exactly one Stage 2D target."""

    record_id: str
    provider_vendor: str
    material: WhooshdQualificationMaterial
    digest_algorithm: str
    expected_attestation_digest: str
    route_resolution_source: str
    route_execution_mode: str
    route_streaming: bool
    audit_evidence_references: tuple[str, str]


@dataclass(frozen=True)
class WhooshdQualificationComparison:
    """Pure internal qualification outcome with a bounded diagnostic reason."""

    outcome: WhooshdQualificationOutcome
    reason: str


def _normalize_value(value: object, spec: object, path: str) -> object:
    if isinstance(value, (set, frozenset)):
        raise WhooshdQualificationCanonicalizationError(
            f"unordered identity value at {path}"
        )
    if isinstance(spec, type):
        if (
            spec is str
            and isinstance(value, str)
            and value
            and value.casefold() not in _PLACEHOLDERS
        ):
            return unicodedata.normalize("NFC", value)
        raise WhooshdQualificationCanonicalizationError(
            f"invalid required evidence at {path}"
        )
    if not isinstance(spec, dict) or not isinstance(value, Mapping):
        raise WhooshdQualificationCanonicalizationError(
            f"invalid identity object at {path}"
        )

    normalized: dict[str, object] = {}
    normalized_keys: set[str] = set()
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str):
            raise WhooshdQualificationCanonicalizationError(
                f"non-string identity key at {path}"
            )
        key = unicodedata.normalize("NFC", raw_key)
        if key in normalized_keys:
            raise WhooshdQualificationCanonicalizationError(
                f"duplicate normalized identity key at {path}"
            )
        normalized_keys.add(key)
        if key not in spec:
            raise WhooshdQualificationCanonicalizationError(
                f"unknown identity field at {path}.{key}"
            )
        normalized[key] = _normalize_value(raw_value, spec[key], f"{path}.{key}")
    if set(normalized) != set(spec):
        raise WhooshdQualificationCanonicalizationError(
            f"incomplete identity object at {path}"
        )
    return normalized


def canonicalize_qualification_identity(identity: Mapping[str, object]) -> bytes:
    """Return exact UTF-8 canonical-json.v1 bytes for a complete identity."""

    normalized = _normalize_value(identity, _V1_DOCUMENT_SPEC, "identity")
    assert isinstance(normalized, dict)
    if normalized["attestation_schema_version"] != ATTESTATION_SCHEMA_VERSION:
        raise WhooshdQualificationCanonicalizationError(
            "unexpected attestation schema version"
        )
    if normalized["canonicalization_profile"] != CANONICALIZATION_PROFILE:
        raise WhooshdQualificationCanonicalizationError(
            "unexpected canonicalization profile"
        )
    try:
        serialized = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise WhooshdQualificationCanonicalizationError(
            "identity is not JSON-compatible"
        ) from exc
    return serialized.encode("utf-8")


def digest_qualification_identity(identity: Mapping[str, object]) -> str:
    """Return the canonical Stage 2F SHA-256 identity digest."""

    digest = hashlib.sha256(canonicalize_qualification_identity(identity)).hexdigest()
    return f"{DIGEST_ALGORITHM}:{digest}"


STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD = WhooshdQualificationRecord(
    record_id="whooshd.stage2d.gemma-4-12b-it-qat-4bit.v1",
    provider_vendor="whooshd",
    material=WhooshdQualificationMaterial(
        invocation_model_id="gemma-4-12b-it-qat-4bit",
        resolved_model_id="mlx-community/gemma-4-12B-it-qat-4bit",
        artifact_identity_kind="manifest_fingerprint",
        artifact_identity_value=(
            "sha256:49bad978b020bdfc70730aaf1516bbed811e8e4122e7e01c7b687ab6e595a72b"
        ),
        quantization="bits-4-group-64-affine",
        runtime_kind="mlx_vlm",
        adapter_name="mlx-vlm",
        adapter_semantic_build="MlxVlmAdapter-0.1.0rc1",
        whooshd_build_identity="whooshd-0.1.0rc1",
        serving_runtime_package="mlx-vlm",
        serving_runtime_version="0.6.2",
        structured_decoder_package="llguidance",
        structured_decoder_version="1.7.6",
        tokenizer_implementation="GemmaTokenizer",
        tokenizer_identity_fingerprint=(
            "sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264"
        ),
        chat_template_fingerprint=(
            "sha256:36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0"
        ),
        tool_template_parser_relationship="shared_chat_template",
        tool_template_parser_identity_fingerprint=(
            "sha256:36e3a42e5cf14cd0020e72d92e1fdd9970f59b82170e421f0cbe1bb42bead3f0"
        ),
        structured_transport_mode="strict_json_schema",
        structured_transport_protocol_version=QUALIFICATION_PROTOCOL_VERSION,
        qualification_protocol_version=QUALIFICATION_PROTOCOL_VERSION,
    ),
    digest_algorithm=DIGEST_ALGORITHM,
    expected_attestation_digest=(
        "sha256:9dd3b803259e5e6e65a6ba08a50dbf387c3907d987d35b327531bf5bf5cc4780"
    ),
    route_resolution_source="authoritative_registry",
    route_execution_mode="managed_sidecar",
    route_streaming=False,
    audit_evidence_references=(
        "docs/architecture/proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-strict-structured-tool-qualification-proof.md",
        "docs/architecture/proofs/2026-08-09-whooshd-gemma-4-12b-it-qat-4bit-tokenizer-identity-reconciliation-proof.md",
    ),
)


def compare_whooshd_qualification(
    record: WhooshdQualificationRecord,
    provenance: WhooshdRuntimeProvenance | None,
) -> WhooshdQualificationComparison:
    """Compare bounded live evidence with one frozen qualification record."""

    if provenance is None:
        return WhooshdQualificationComparison(
            WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE,
            "provenance_missing",
        )
    if provenance.qualification_attestation_malformed:
        return WhooshdQualificationComparison(
            WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE,
            "attestation_malformed",
        )
    reference = provenance.qualification_attestation
    if reference is None:
        return WhooshdQualificationComparison(
            WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE,
            "attestation_missing",
        )
    if reference.attestation_schema_version != record.material.attestation_schema_version:
        return WhooshdQualificationComparison(
            WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE,
            "schema_unrecognized",
        )
    if reference.canonicalization_profile != record.material.canonicalization_profile:
        return WhooshdQualificationComparison(
            WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE,
            "canonicalization_profile_unrecognized",
        )
    if reference.digest_algorithm != record.digest_algorithm:
        return WhooshdQualificationComparison(
            WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE,
            "digest_algorithm_unrecognized",
        )

    expected_provenance = (
        ("requested_model_id", record.material.invocation_model_id),
        ("advertised_model_id", record.material.invocation_model_id),
        ("resolved_model_id", record.material.invocation_model_id),
        ("runtime_kind", record.material.runtime_kind),
        ("adapter_name", record.material.adapter_name),
        ("resolution_source", record.route_resolution_source),
        ("execution_mode", record.route_execution_mode),
        ("streaming", record.route_streaming),
    )
    for field, expected in expected_provenance:
        observed = getattr(provenance, field)
        if observed is None:
            return WhooshdQualificationComparison(
                WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE,
                "provenance_binding_missing",
            )
        if observed != expected:
            return WhooshdQualificationComparison(
                WhooshdQualificationOutcome.MISMATCH,
                "target_identity_mismatch",
            )

    expected_reference = (
        ("invocation_model_id", record.material.invocation_model_id),
        ("resolved_model_id", record.material.resolved_model_id),
        ("runtime_kind", record.material.runtime_kind),
        ("adapter_name", record.material.adapter_name),
    )
    for field, expected in expected_reference:
        observed = getattr(reference, field)
        if observed != expected:
            return WhooshdQualificationComparison(
                WhooshdQualificationOutcome.MISMATCH,
                "target_identity_mismatch",
            )
    if reference.attestation_digest != record.expected_attestation_digest:
        return WhooshdQualificationComparison(
            WhooshdQualificationOutcome.MISMATCH,
            "digest_mismatch",
        )
    return WhooshdQualificationComparison(
        WhooshdQualificationOutcome.MATCH,
        "qualified_identity_match",
    )
