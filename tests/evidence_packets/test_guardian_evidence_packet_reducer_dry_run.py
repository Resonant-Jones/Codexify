"""Tests for the pure Guardian Evidence Packet reducer dry-run skeleton."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardian.evidence_packets import (
    DRY_RUN_STOP_REASON,
    DRY_RUN_WARNING,
    ReducerDiagnosticsSummary,
    ReducerInputBundle,
    ReducerInputRef,
    ReducerResult,
    dry_run_reducer,
    reducer_limits,
)
from guardian.evidence_packets.reducer_contracts import REDUCER_CONTRACT_VERSION

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "guardian" / "evidence_packets" / "reducer.py"
FIXTURES = ROOT / "docs" / "architecture" / "fixtures"


def _bundle(source_ref: str = "does-not-exist.json") -> ReducerInputBundle:
    return ReducerInputBundle(
        bundle_id="dry-run-test",
        review_depth="high",
        inputs=(ReducerInputRef("input-1", "static_docs", source_ref, "evidence"),),
    )


def test_reducer_module_exists_and_has_only_allowed_imports() -> None:
    assert MODULE.exists()
    source = MODULE.read_text().lower()
    assert "guardian.evidence_packets.reducer_contracts" in source
    for token in (
        "fastapi", "sqlalchemy", "psycopg", "command_bus", "codex_runner_bridge",
        "scripts.guardian", "subprocess", "requests", "httpx", "docker",
    ):
        assert token not in source


def test_dry_run_constants_and_exports() -> None:
    assert DRY_RUN_STOP_REASON == "dry_run_no_reduction"
    assert "does not produce GuardianEvidencePacket output" in DRY_RUN_WARNING
    from guardian import evidence_packets

    assert evidence_packets.dry_run_reducer is dry_run_reducer
    assert "dry_run_reducer" in evidence_packets.__all__


def test_dry_run_returns_diagnostics_only() -> None:
    result = dry_run_reducer(_bundle())
    assert isinstance(result, ReducerResult)
    assert result.packet is None
    assert result.validation_result is None
    assert isinstance(result.diagnostics, ReducerDiagnosticsSummary)
    assert result.diagnostics.reducer_contract_version == REDUCER_CONTRACT_VERSION
    assert result.diagnostics.lifecycle_steps_completed == (
        "receive_bounded_evidence_input_set", "classify_input_classes", "stop"
    )
    assert DRY_RUN_WARNING in result.diagnostics.warnings
    for limit in reducer_limits():
        assert limit in result.diagnostics.limits
    assert f"stop reason: {DRY_RUN_STOP_REASON}" in result.diagnostics.limits


def test_dry_run_does_not_mutate_or_inspect_input_source() -> None:
    bundle = _bundle("/path/that/does/not/exist.json")
    before = bundle
    result = dry_run_reducer(bundle)
    assert bundle == before
    assert result.packet is None
    assert result.validation_result is None
    with pytest.raises(TypeError):
        dry_run_reducer(object())  # type: ignore[arg-type]


def test_dry_run_does_not_produce_authority_or_packet_data() -> None:
    result = dry_run_reducer(_bundle())
    assert "authority_state" not in result.diagnostics.__dict__
    assert result.packet is None
    assert result.validation_result is None


def test_existing_fixture_and_batch_surfaces_remain_available() -> None:
    for name in (
        "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json",
        "guardian-evidence-packet.local-validator-toolchain.v1.json",
    ):
        packet = json.loads((FIXTURES / name).read_text())
        assert packet["schema_version"] == "guardian_evidence_packet.v1"
