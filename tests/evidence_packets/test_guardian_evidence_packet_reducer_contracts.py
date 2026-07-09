"""Tests for pure Guardian Evidence Packet reducer interface contracts."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

from guardian.evidence_packets import (
    ALLOWED_REDUCER_INPUT_CLASSES,
    ALLOWED_REDUCER_OUTPUT_CLASSES,
    REDUCER_CONTRACT_VERSION,
    REDUCER_LIFECYCLE_STEPS,
    REDUCER_STOP_STEP,
    ReducerDiagnosticsSummary,
    ReducerInputBundle,
    ReducerInputRef,
    ReducerResult,
    is_allowed_reducer_input_class,
    is_allowed_reducer_output_class,
    lifecycle_is_prefix,
    reducer_default_authority_state,
    reducer_limits,
    reducer_lifecycle_index,
)
from guardian.evidence_packets.contracts import REQUIRED_AUTHORITY_LOCKS

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "guardian" / "evidence_packets" / "reducer_contracts.py"
FIXTURES = ROOT / "docs" / "architecture" / "fixtures"

EXPECTED_INPUTS = {
    "static_docs", "static_fixtures", "validation_result", "command_run_snapshot",
    "command_run_event_snapshot", "receipt_metadata", "proof_index",
    "test_result_summary", "operator_supplied_context",
}
EXPECTED_OUTPUTS = {
    "GuardianEvidencePacket", "GuardianEvidencePacketStaticValidationResult",
    "reducer_diagnostics_summary",
}
EXPECTED_STEPS = (
    "receive_bounded_evidence_input_set", "classify_input_classes", "assign_evidence_refs",
    "extract_candidate_claims", "bind_candidate_claims_to_evidence_refs",
    "mark_unsupported_blocked_inferred_or_not_evaluated_claims", "preserve_uncertainty",
    "preserve_forbidden_interpretations", "set_authority_locks", "select_next_gate_options",
    "produce_guardian_evidence_packet", "run_static_validation",
    "return_packet_plus_validation_result_for_human_review", "stop",
)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_module_exists_and_uses_only_allowed_imports() -> None:
    assert MODULE.exists()
    source = MODULE.read_text().lower()
    assert "from guardian.evidence_packets.contracts" in source
    for token in ("fastapi", "sqlalchemy", "psycopg", "command_bus", "codex_runner_bridge", "scripts.guardian", "subprocess", "requests", "httpx", "docker"):
        assert token not in source


def test_constants_match_design_contract() -> None:
    assert REDUCER_CONTRACT_VERSION == "guardian_evidence_packet_reducer_contract.v1"
    assert ALLOWED_REDUCER_INPUT_CLASSES == EXPECTED_INPUTS
    assert ALLOWED_REDUCER_OUTPUT_CLASSES == EXPECTED_OUTPUTS
    assert REDUCER_LIFECYCLE_STEPS == EXPECTED_STEPS
    assert REDUCER_STOP_STEP == "stop"


def test_literal_helpers_and_lifecycle_indexes() -> None:
    assert is_allowed_reducer_input_class("static_docs")
    assert not is_allowed_reducer_input_class("runtime_service")
    assert is_allowed_reducer_output_class("GuardianEvidencePacket")
    assert not is_allowed_reducer_output_class("database_write")
    assert reducer_lifecycle_index("receive_bounded_evidence_input_set") == 0
    assert reducer_lifecycle_index("stop") == 13
    with pytest.raises(ValueError):
        reducer_lifecycle_index("execute")
    assert lifecycle_is_prefix(())
    assert lifecycle_is_prefix(EXPECTED_STEPS[:4])
    assert lifecycle_is_prefix(EXPECTED_STEPS)
    assert not lifecycle_is_prefix(("classify_input_classes",))
    assert not lifecycle_is_prefix(("receive_bounded_evidence_input_set", "execute"))


def test_default_authority_state_and_limits_are_pure() -> None:
    first = reducer_default_authority_state()
    second = reducer_default_authority_state()
    assert first == {lock: False for lock in REQUIRED_AUTHORITY_LOCKS}
    assert first is not second
    first["merge_allowed"] = True
    assert second["merge_allowed"] is False
    limits = reducer_limits()
    for boundary in ("does not execute", "does not ingest", "does not write receipts", "does not mutate WorkOrders", "does not write Execution Ledger entries", "does not call command bus", "does not call Codex Runner", "does not invoke Pi Loop", "does not mutate source", "does not execute providers"):
        assert boundary in limits


def test_dataclasses_are_frozen_and_reject_disallowed_literals() -> None:
    ref = ReducerInputRef("input-1", "static_docs", "docs/example.md", "evidence")
    assert is_dataclass(ref)
    with pytest.raises(FrozenInstanceError):
        ref.input_id = "changed"
    with pytest.raises(ValueError):
        ReducerInputRef("input-1", "runtime_service", "x", "evidence")
    bundle = ReducerInputBundle("bundle-1", "high", [ref], ["bounded context"])
    assert bundle.inputs == (ref,)
    assert bundle.operator_context == ("bounded context",)
    with pytest.raises(ValueError):
        ReducerInputBundle("bundle-1", "extreme", (ref,))
    diagnostics = ReducerDiagnosticsSummary(REDUCER_CONTRACT_VERSION, EXPECTED_STEPS[:2])
    assert diagnostics.lifecycle_steps_completed == EXPECTED_STEPS[:2]
    with pytest.raises(ValueError):
        ReducerDiagnosticsSummary(REDUCER_CONTRACT_VERSION, ("stop", "classify_input_classes"))


def test_result_carries_empty_handoffs_without_validation() -> None:
    diagnostics = ReducerDiagnosticsSummary(REDUCER_CONTRACT_VERSION, ())
    result = ReducerResult(packet=None, validation_result=None, diagnostics=diagnostics)
    assert result.packet is None
    assert result.validation_result is None


def test_init_exports_reducer_contract_names_and_existing_fixtures_remain_readable() -> None:
    from guardian.evidence_packets import contracts

    assert contracts.GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION == "guardian_evidence_packet.v1"
    for name in ("ReducerInputRef", "ReducerInputBundle", "ReducerDiagnosticsSummary", "ReducerResult"):
        assert name in __import__("guardian.evidence_packets", fromlist=[name]).__all__
    for fixture_name in (
        "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json",
        "guardian-evidence-packet.local-validator-toolchain.v1.json",
    ):
        assert _fixture(fixture_name)["schema_version"] == contracts.GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION


def test_existing_backend_contract_tests_and_local_batch_surface_remain_available() -> None:
    assert (ROOT / "tests/evidence_packets/test_guardian_evidence_packet_contracts.py").exists()
