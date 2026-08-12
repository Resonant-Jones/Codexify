"""Stage 2G pre-request tool-capability projection tests."""

from __future__ import annotations

import copy

import pytest

from guardian.providers.whooshd_control_plane import (
    parse_whooshd_runtime_inventory_entry,
)
from guardian.providers.whooshd_qualification import (
    STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
    WhooshdQualificationOutcome,
    canonicalize_qualification_identity,
    digest_qualification_identity,
)
from guardian.providers.whooshd_tool_capability import (
    project_whooshd_tool_capability,
)


def _full_inventory_attestation() -> dict[str, object]:
    """Mirror the exact Stage 2D material identity and its pinned digest."""

    material = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.material
    return {
        "attestation_schema_version": material.attestation_schema_version,
        "canonicalization_profile": material.canonicalization_profile,
        "invocation_model_id": material.invocation_model_id,
        "resolved_model_id": material.resolved_model_id,
        "artifact_identity": {
            "kind": material.artifact_identity_kind,
            "value": material.artifact_identity_value,
        },
        "quantization": material.quantization,
        "runtime_kind": material.runtime_kind,
        "adapter": {
            "name": material.adapter_name,
            "semantic_build": material.adapter_semantic_build,
        },
        "whooshd_build_identity": material.whooshd_build_identity,
        "serving_runtime": {
            "package": material.serving_runtime_package,
            "version": material.serving_runtime_version,
        },
        "structured_decoder": {
            "package": material.structured_decoder_package,
            "version": material.structured_decoder_version,
        },
        "tokenizer": {
            "implementation": material.tokenizer_implementation,
            "identity_fingerprint": material.tokenizer_identity_fingerprint,
        },
        "chat_template_fingerprint": material.chat_template_fingerprint,
        "tool_template_parser": {
            "relationship": material.tool_template_parser_relationship,
            "identity_fingerprint": material.tool_template_parser_identity_fingerprint,
        },
        "structured_transport": {
            "mode": material.structured_transport_mode,
            "protocol_version": material.structured_transport_protocol_version,
        },
        "qualification_protocol_version": material.qualification_protocol_version,
        "digest_algorithm": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.digest_algorithm,
        "attestation_digest": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.expected_attestation_digest,
    }


def _inventory_entry(
    *,
    invocation_alias: str = "gemma-4-12b-it-qat-4bit",
    runtime_kind: str = "mlx_vlm",
    adapter_name: str = "mlx-vlm",
    loaded: bool = True,
    model_lifecycle: str | None = "ready",
    capabilities: list[str] | None = None,
    attestation: dict[str, object] | None = None,
    resolution_source: str = "loaded_model_match",
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build one ModelInfo-shaped payload for the Stage 2G parser."""

    payload: dict[str, object] = {
        "id": invocation_alias,
        "loaded": loaded,
        "runtime_provenance": {
            "schema_version": "whooshd.runtime.v1",
            "runtime_kind": runtime_kind,
            "adapter_name": adapter_name,
            "resolution_source": resolution_source,
            "execution_mode": "managed_sidecar",
            "model_lifecycle": model_lifecycle,
        },
        "model_lifecycle": model_lifecycle,
        "capabilities": list(
            capabilities
            if capabilities is not None
            else ["chat", "streaming", "json", "vision"]
        ),
    }
    if attestation is not None:
        payload["qualification_attestation"] = attestation
    if extra:
        payload.update(extra)
    return payload


# ── A. Exact inventory parser ───────────────────────────────────────────────


def test_exact_inventory_entry_parses_with_full_attestation():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=_full_inventory_attestation())
    )

    assert parsed is not None
    assert parsed.invocation_model_id == "gemma-4-12b-it-qat-4bit"
    assert parsed.runtime_kind == "mlx_vlm"
    assert parsed.adapter_name == "mlx-vlm"
    assert parsed.loaded is True
    assert parsed.model_lifecycle == "ready"
    assert parsed.qualification_attestation is not None
    assert parsed.qualification_attestation_malformed is False


# ── B. Inventory privacy ────────────────────────────────────────────────────


def test_parsed_evidence_does_not_expose_raw_paths_or_endpoints():
    sentinel_path = "/Volumes/Dev_SSD/secret/private/model-weights/target"
    sentinel_endpoint = "http://127.0.0.1:8082/health"
    payload = _inventory_entry(
        attestation=_full_inventory_attestation(),
        extra={
            "path": sentinel_path,
            "model_path": sentinel_path,
            "endpoint": sentinel_endpoint,
            "host": "127.0.0.1:8082",
            "pid": 4242,
            "env": {"WHOOSHD_VERSION": "0.1.0rc1"},
        },
    )

    parsed = parse_whooshd_runtime_inventory_entry(payload)

    assert parsed is not None
    blob = repr(parsed) + " " + str(parsed.qualification_attestation)
    assert sentinel_path not in blob
    assert sentinel_endpoint not in blob
    assert "127.0.0.1:8082" not in blob
    assert "WHOOSHD_VERSION" not in blob


# ── C. Full attestation self-consistency ────────────────────────────────────


def test_full_attestation_self_consistency_matches_pinned_digest():
    record = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    material = record.material.as_identity_document()

    canonical = canonicalize_qualification_identity(material)
    digest = digest_qualification_identity(material)

    assert digest == "sha256:9dd3b803259e5e6e65a6ba08a50dbf387c3907d987d35b327531bf5bf5cc4780"
    assert b'"adapter":{"name":"mlx-vlm"' in canonical
    assert b'"runtime_kind":"mlx_vlm"' in canonical


# ── D. Tampered material ────────────────────────────────────────────────────


def test_tampered_material_never_projects_eligible():
    tampered = copy.deepcopy(_full_inventory_attestation())
    tampered["quantization"] = "bits-8"
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=tampered)
    )

    assert parsed is not None
    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── E. Tampered digest ──────────────────────────────────────────────────────


def test_tampered_digest_never_projects_eligible():
    tampered = copy.deepcopy(_full_inventory_attestation())
    tampered["attestation_digest"] = "sha256:" + "0" * 64
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=tampered)
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── F. Exact MATCH + ready + exposure allowed ──────────────────────────────


def test_match_ready_and_exposure_allowed_projects_eligible():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=_full_inventory_attestation())
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "eligible"
    assert projection.invocation_model_id == "gemma-4-12b-it-qat-4bit"
    assert projection.runtime_kind == "mlx_vlm"
    assert projection.adapter_name == "mlx-vlm"
    assert projection.runtime_ready is True
    assert projection.exposure_allowed is True
    assert projection.qualification_outcome is WhooshdQualificationOutcome.MATCH
    assert projection.reason == "qualified_identity_match"


# ── G. MATCH + exposure denied ─────────────────────────────────────────────


def test_match_ready_but_exposure_denied_is_ineligible():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=_full_inventory_attestation())
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=False
    )

    assert projection.outcome == "ineligible"
    assert projection.exposure_allowed is False
    assert projection.reason == "exposure_denied"


# ── H. MATCH + unloaded ────────────────────────────────────────────────────


def test_unloaded_target_is_ineligible():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            attestation=_full_inventory_attestation(),
            loaded=False,
            model_lifecycle="unloaded",
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.runtime_ready is False
    assert projection.reason == "runtime_not_ready"


# ── I. MATCH + warming ─────────────────────────────────────────────────────


def test_warming_target_is_ineligible():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            attestation=_full_inventory_attestation(),
            model_lifecycle="warming",
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.reason == "runtime_not_ready"


# ── J. MATCH + generating ──────────────────────────────────────────────────


def test_generating_target_is_ineligible_for_a_new_request():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            attestation=_full_inventory_attestation(),
            model_lifecycle="generating",
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.reason == "runtime_not_ready"


# ── K. MATCH + degraded/failed/offline ─────────────────────────────────────


@pytest.mark.parametrize("lifecycle", ["degraded", "failed", "offline"])
def test_non_ready_lifecycle_states_are_ineligible(lifecycle):
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            attestation=_full_inventory_attestation(),
            model_lifecycle=lifecycle,
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.reason == "runtime_not_ready"


# ── L. MISMATCH + ready ────────────────────────────────────────────────────


def test_self_consistent_attestation_with_different_identity_is_mismatch():
    """A complete self-consistent attestation whose digest does not match
    the qualification record's expected digest identifies a different
    execution identity and must classify as MISMATCH."""

    from guardian.providers.whooshd_qualification import (
        digest_qualification_identity,
    )

    material = (
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.material
    )
    document = material.as_identity_document()
    document["adapter"] = {
        "name": material.adapter_name,
        "semantic_build": "MlxVlmAdapter-0.2.0-different",
    }
    self_consistent_digest = digest_qualification_identity(document)

    attestation_payload = _full_inventory_attestation()
    attestation_payload["adapter"] = document["adapter"]
    attestation_payload["attestation_digest"] = self_consistent_digest

    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=attestation_payload)
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.MISMATCH
    )
    assert projection.qualification_reason == "digest_mismatch"


def test_mismatch_with_ready_and_exposure_still_ineligible():
    tampered = copy.deepcopy(_full_inventory_attestation())
    tampered["attestation_digest"] = "sha256:" + "1" * 64
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=tampered)
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── M. INSUFFICIENT_EVIDENCE + ready ───────────────────────────────────────


def test_inconsistent_attestation_with_ready_is_insufficient():
    tampered = copy.deepcopy(_full_inventory_attestation())
    tampered["canonicalization_profile"] = (
        "whooshd.qualification-attestation.canonical-json.v9"
    )
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=tampered)
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── N. No attestation + ready ──────────────────────────────────────────────


def test_no_attestation_with_ready_is_insufficient():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=None)
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── O. Unknown schema/profile/algorithm ────────────────────────────────────


@pytest.mark.parametrize(
    "mutator",
    [
        pytest.param(
            lambda a: a.__setitem__(
                "attestation_schema_version",
                "whooshd.qualification-attestation.v9",
            ),
            id="unknown_schema",
        ),
        pytest.param(
            lambda a: a.__setitem__(
                "canonicalization_profile",
                "whooshd.qualification-attestation.canonical-json.v9",
            ),
            id="unknown_profile",
        ),
        pytest.param(
            lambda a: a.__setitem__("digest_algorithm", "sha512"),
            id="unknown_algorithm",
        ),
    ],
)
def test_unknown_attestation_metadata_is_insufficient(mutator):
    tampered = copy.deepcopy(_full_inventory_attestation())
    mutator(tampered)
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=tampered)
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── P. Wrong model ─────────────────────────────────────────────────────────


def test_different_gemma_alias_is_ineligible():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            invocation_alias="gemma-4-e4b-it-4bit",
            attestation=_full_inventory_attestation(),
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.MISMATCH
    )


# ── Q. Wrong runtime ───────────────────────────────────────────────────────


@pytest.mark.parametrize("runtime_kind", ["llama_cpp", "mlx_lm", "stub"])
def test_non_mlx_vlm_runtime_is_ineligible(runtime_kind):
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            runtime_kind=runtime_kind,
            adapter_name="other-adapter",
            attestation=_full_inventory_attestation(),
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.MISMATCH
    )


# ── R. Wrong adapter ───────────────────────────────────────────────────────


def test_other_adapter_for_same_target_is_ineligible():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            adapter_name="other-adapter",
            attestation=_full_inventory_attestation(),
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.MISMATCH
    )


# ── S. supports_tools=False distinction ────────────────────────────────────


def test_qualified_target_remains_eligible_even_when_native_supports_tools_is_false():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            capabilities=["chat", "streaming", "json", "vision"],
            attestation=_full_inventory_attestation(),
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "eligible"
    assert parsed is not None
    assert "tools" not in parsed.capabilities


def test_unqualified_target_with_supports_tools_true_is_ineligible():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(
            capabilities=["chat", "tools"],
            attestation=None,
        )
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── T. Profile is not runtime truth ────────────────────────────────────────


def test_profile_without_live_inventory_is_not_consulted():
    """The projection must not read the Codexify file-backed profile registry.

    The projection denies eligibility purely on the ``inventory_missing`` path
    when no live inventory evidence is supplied.  The file-backed
    ``guardian.core.whooshd_model_profiles`` registry is a configuration
    surface, not runtime truth, so it must never be consulted by the
    pre-request projection function.
    """

    import guardian.providers.whooshd_tool_capability as capability_module

    # The qualification record reference is the module's default; confirm
    # it remains bound to the same record even after other tests.
    assert capability_module.STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD is (
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    )

    projection = project_whooshd_tool_capability(
        inventory=None, exposure_allowed=True
    )

    assert projection.outcome == "ineligible"
    assert projection.reason == "inventory_missing"


# ── U. Stale snapshot safety ───────────────────────────────────────────────


def test_two_independent_snapshots_do_not_share_state():
    snapshot_a = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=_full_inventory_attestation())
    )
    snapshot_b_attestation = copy.deepcopy(_full_inventory_attestation())
    snapshot_b_attestation["quantization"] = "bits-8"
    snapshot_b = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=snapshot_b_attestation)
    )

    projection_a = project_whooshd_tool_capability(
        inventory=snapshot_a, exposure_allowed=True
    )
    projection_b = project_whooshd_tool_capability(
        inventory=snapshot_b, exposure_allowed=True
    )

    assert projection_a.outcome == "eligible"
    assert projection_b.outcome == "ineligible"
    assert projection_a.qualification_outcome is (
        WhooshdQualificationOutcome.MATCH
    )
    assert projection_b.qualification_outcome is (
        WhooshdQualificationOutcome.INSUFFICIENT_EVIDENCE
    )


# ── V. Projection contains bounded explanation ────────────────────────────


def test_projection_does_not_copy_full_attestation_material():
    parsed = parse_whooshd_runtime_inventory_entry(
        _inventory_entry(attestation=_full_inventory_attestation())
    )

    projection = project_whooshd_tool_capability(
        inventory=parsed, exposure_allowed=True
    )

    blob = repr(projection)
    assert (
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.expected_attestation_digest
        not in blob
    )
    assert (
        STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.material.tokenizer_identity_fingerprint
        not in blob
    )
    assert "manifest_fingerprint" not in blob


# ── X. Stage 1 regression is exercised by Stage 2F.1b tests ────────────────
# The Stage 2F.1b post-response guard remains in whooshd_tool_adapter; the
# Stage 1 authority gate remains in chat_completion_service.  Stage 2G
# deliberately does not touch either seam.  The re-runs of those suites in
# the focused pytest command prove the regression posture.
