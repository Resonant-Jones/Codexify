from __future__ import annotations

import builtins
import copy

import pytest

from guardian.providers.whooshd_control_plane import (
    parse_whooshd_runtime_provenance,
)
from guardian.providers.whooshd_qualification import (
    ATTESTATION_SCHEMA_VERSION,
    CANONICALIZATION_PROFILE,
    STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
    WhooshdQualificationCanonicalizationError,
    WhooshdQualificationOutcome,
    canonicalize_qualification_identity,
    compare_whooshd_qualification,
    digest_qualification_identity,
)


def _synthetic_identity() -> dict[str, object]:
    """The normative Stage 2F vector, intentionally not in key order."""

    return {
        "tool_template_parser": {
            "relationship": "distinct",
            "identity_fingerprint": "sha256:" + "c" * 64,
        },
        "tokenizer": {
            "identity_fingerprint": "sha256:" + "b" * 64,
            "implementation": "GemmaTokenizer",
        },
        "structured_transport": {
            "protocol_version": "model-turn.strict-json-schema.v1",
            "mode": "strict_json_schema",
        },
        "structured_decoder": {"version": "1.7.6", "package": "llguidance"},
        "serving_runtime": {"version": "0.6.2", "package": "mlx-vlm"},
        "runtime_kind": "mlx_vlm",
        "resolved_model_id": "example.org/Gemma-4-12B-IT-QAT-4bit",
        "quantization": "qat-4bit",
        "qualification_protocol_version": "model-turn.strict-json-schema.v1",
        "whooshd_build_identity": "whooshd-0.1.0rc1+synthetic",
        "invocation_model_id": "Gemma-4-12B-IT-QAT-4bit",
        "chat_template_fingerprint": "sha256:" + "a" * 64,
        "canonicalization_profile": CANONICALIZATION_PROFILE,
        "attestation_schema_version": ATTESTATION_SCHEMA_VERSION,
        "artifact_identity": {
            "value": "sha256:" + "d" * 64,
            "kind": "manifest_fingerprint",
        },
        "adapter": {"semantic_build": "MlxVlmAdapter-Café-v1", "name": "mlx-vlm"},
    }


def _matching_provenance(**overrides):
    record = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    material = record.material
    payload: dict[str, object] = {
        "schema_version": "whooshd.runtime.v1",
        "request_id": "req-stage2f",
        "requested_model_id": material.invocation_model_id,
        "advertised_model_id": material.invocation_model_id,
        "resolved_model_id": material.invocation_model_id,
        "backend_reported_model_id": material.resolved_model_id,
        "runtime_kind": material.runtime_kind,
        "adapter_name": material.adapter_name,
        "resolution_source": record.route_resolution_source,
        "execution_mode": record.route_execution_mode,
        "streaming": record.route_streaming,
        "queued": False,
        "batched": False,
        "model_lifecycle": "ready",
        "whooshd_version": "0.1.0rc1",
        "qualification_attestation": {
            "attestation_schema_version": material.attestation_schema_version,
            "canonicalization_profile": material.canonicalization_profile,
            "digest_algorithm": record.digest_algorithm,
            "attestation_digest": record.expected_attestation_digest,
            "invocation_model_id": material.invocation_model_id,
            "resolved_model_id": material.resolved_model_id,
            "runtime_kind": material.runtime_kind,
            "adapter_name": material.adapter_name,
        },
    }
    payload.update(overrides)
    provenance = parse_whooshd_runtime_provenance(payload)
    assert provenance is not None
    return provenance


def test_global_fixed_vector_is_exact_and_unicode_is_direct_utf8():
    identity = _synthetic_identity()

    canonical = canonicalize_qualification_identity(identity)

    assert b"MlxVlmAdapter-Caf\xc3\xa9-v1" in canonical
    assert digest_qualification_identity(identity) == (
        "sha256:5f1923d1afa0f3a804bd3c12f37486b9f6b692baf43a294c766610399d95725f"
    )


def test_canonicalizer_normalizes_nfc_and_ignores_object_insertion_order():
    identity = _synthetic_identity()
    reordered = dict(reversed(list(identity.items())))
    decomposed = copy.deepcopy(reordered)
    decomposed["adapter"]["semantic_build"] = "MlxVlmAdapter-Cafe\u0301-v1"  # type: ignore[index]

    assert canonicalize_qualification_identity(identity) == canonicalize_qualification_identity(reordered)
    assert canonicalize_qualification_identity(identity) == canonicalize_qualification_identity(decomposed)


def test_canonicalizer_preserves_case_and_rejects_unordered_or_unrecognized_values():
    identity = _synthetic_identity()
    case_changed = copy.deepcopy(identity)
    case_changed["invocation_model_id"] = "gemma-4-12b-it-qat-4bit"
    assert digest_qualification_identity(identity) != digest_qualification_identity(case_changed)

    unordered = copy.deepcopy(identity)
    unordered["quantization"] = {"qat-4bit"}
    with pytest.raises(WhooshdQualificationCanonicalizationError):
        canonicalize_qualification_identity(unordered)

    unsupported_array = copy.deepcopy(identity)
    unsupported_array["quantization"] = ["qat-4bit"]
    with pytest.raises(WhooshdQualificationCanonicalizationError):
        canonicalize_qualification_identity(unsupported_array)


def test_record_is_one_complete_stage_2d_target_with_pinned_digest():
    record = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    material = record.material

    assert record.provider_vendor == "whooshd"
    assert record.record_id == "whooshd.stage2d.gemma-4-12b-it-qat-4bit.v1"
    assert len(record.audit_evidence_references) == 2
    assert material.tokenizer_identity_fingerprint == (
        "sha256:d9b98aa21582c4a1dcf598a17ffbede72feabe6a46b1a6bb8cf1ed5ab44eb264"
    )
    assert material.artifact_identity_value == (
        "sha256:49bad978b020bdfc70730aaf1516bbed811e8e4122e7e01c7b687ab6e595a72b"
    )
    assert material.tool_template_parser_relationship == "shared_chat_template"
    assert material.tool_template_parser_identity_fingerprint == material.chat_template_fingerprint
    assert digest_qualification_identity(material.as_identity_document()) == record.expected_attestation_digest


def test_runtime_qualification_never_reads_a_proof_document(monkeypatch):
    def _forbidden_open(*_args, **_kwargs):
        raise AssertionError("runtime qualification must not open files")

    monkeypatch.setattr(builtins, "open", _forbidden_open)
    record = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    assert digest_qualification_identity(record.material.as_identity_document()) == record.expected_attestation_digest
    assert compare_whooshd_qualification(record, _matching_provenance()).outcome is WhooshdQualificationOutcome.MATCH


def test_exact_stage_2f_1a_reference_parses_and_matches():
    provenance = _matching_provenance()

    assert provenance.qualification_attestation is not None
    assert provenance.qualification_attestation.attestation_digest == (
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.expected_attestation_digest
    )
    comparison = compare_whooshd_qualification(
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD, provenance
    )
    assert comparison.outcome is WhooshdQualificationOutcome.MATCH
    assert comparison.reason == "qualified_identity_match"


def test_legacy_runtime_provenance_stays_parseable_but_is_insufficient():
    payload = _matching_provenance().as_dict()
    payload.pop("qualification_attestation")
    provenance = parse_whooshd_runtime_provenance(payload)
    assert provenance is not None

    assert provenance.qualification_attestation is None
    assert provenance.qualification_attestation_malformed is False
    assert compare_whooshd_qualification(
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD, provenance
    ).outcome is WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize(
    "attestation",
    [
        {"attestation_digest": "not-a-digest"},
        {"attestation_digest": "sha256:" + "A" * 64},
        {"attestation_digest": "sha256:" + "a" * 63},
        {"attestation_digest": 42},
        {"attestation_digest": "sha256:" + "a" * 64, "resolved_model_id": "/private/model"},
    ],
)
def test_malformed_attestation_reference_is_discarded_to_insufficient(attestation):
    base = _matching_provenance().as_dict()
    reference = dict(base["qualification_attestation"])
    reference.update(attestation)
    base["qualification_attestation"] = reference
    provenance = parse_whooshd_runtime_provenance(base)

    assert provenance is not None
    assert provenance.qualification_attestation is None
    assert provenance.qualification_attestation_malformed is True
    comparison = compare_whooshd_qualification(
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD, provenance
    )
    assert comparison.outcome is WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    assert comparison.reason == "attestation_malformed"


def test_incomplete_attestation_reference_is_discarded_to_insufficient():
    base = _matching_provenance().as_dict()
    reference = dict(base["qualification_attestation"])
    reference.pop("adapter_name")
    base["qualification_attestation"] = reference
    provenance = parse_whooshd_runtime_provenance(base)

    assert provenance is not None
    assert provenance.qualification_attestation is None
    assert provenance.qualification_attestation_malformed is True
    assert compare_whooshd_qualification(
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD, provenance
    ).outcome is WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("attestation_schema_version", "whooshd.qualification-attestation.v2", "schema_unrecognized"),
        ("canonicalization_profile", "whooshd.qualification-attestation.canonical-json.v2", "canonicalization_profile_unrecognized"),
        ("digest_algorithm", "sha512", "digest_algorithm_unrecognized"),
    ],
)
def test_unknown_reference_versions_are_insufficient(field, value, reason):
    base = _matching_provenance().as_dict()
    reference = dict(base["qualification_attestation"])
    reference[field] = value
    base["qualification_attestation"] = reference
    provenance = parse_whooshd_runtime_provenance(base)
    assert provenance is not None

    comparison = compare_whooshd_qualification(
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD, provenance
    )
    assert comparison.outcome is WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    assert comparison.reason == reason


def test_recognized_digest_or_target_binding_difference_is_mismatch():
    base = _matching_provenance().as_dict()
    digest_reference = dict(base["qualification_attestation"])
    digest_reference["attestation_digest"] = "sha256:" + "0" * 64
    base["qualification_attestation"] = digest_reference
    digest_mismatch = parse_whooshd_runtime_provenance(base)
    assert digest_mismatch is not None
    assert compare_whooshd_qualification(
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD, digest_mismatch
    ).outcome is WhooshdQualificationOutcome.MISMATCH

    for field, value in (
        ("resolved_model_id", "another-target"),
        ("runtime_kind", "llama_cpp"),
        ("adapter_name", "llama-cpp"),
    ):
        base = _matching_provenance().as_dict()
        if field == "resolved_model_id":
            base[field] = value
        else:
            reference = dict(base["qualification_attestation"])
            reference[field] = value
            base["qualification_attestation"] = reference
        provenance = parse_whooshd_runtime_provenance(base)
        assert provenance is not None
        comparison = compare_whooshd_qualification(
            STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD, provenance
        )
        assert comparison.outcome is WhooshdQualificationOutcome.MISMATCH
        assert comparison.reason == "target_identity_mismatch"
