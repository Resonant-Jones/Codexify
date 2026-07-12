"""Tests for the pure Guardian Evidence Packet backend contract package."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "guardian" / "evidence_packets"
CONTRACTS = PACKAGE / "contracts.py"
SINGLE_VALIDATOR = ROOT / "scripts" / "guardian" / "validate_evidence_packet.py"
BATCH_VALIDATOR = ROOT / "scripts" / "guardian" / "validate_evidence_packets.py"
PROTOCOL_TOKENS = ROOT / "guardian" / "protocol_tokens.py"
FIXTURES = ROOT / "docs" / "architecture" / "fixtures"

EXPECTED_PACKET_FIELDS = (
    "schema_version", "packet_id", "created_at", "source_domain", "evidence_class",
    "review_depth", "subject", "reducer_profile_ref", "raw_evidence_refs",
    "reduced_summary", "claim_ledger", "authority_state", "invariant_checks",
    "uncertainty", "forbidden_interpretations", "next_gate_options",
    "recommended_next_gate", "loop_policy", "provenance", "limits",
)
EXPECTED_EVIDENCE_FIELDS = (
    "ref_id", "ref_type", "uri_or_path", "source_system", "content_hash",
    "timestamp", "status", "trust_posture", "notes",
)
EXPECTED_CLAIM_FIELDS = (
    "claim_id", "claim", "status", "evidence_refs", "confidence", "limits",
    "counterclaims", "missing_evidence", "forbidden_interpretations",
)
EXPECTED_LOCKS = (
    "guardian_operational", "plan_execution_allowed", "pi_loop_invocation_allowed",
    "codexify_ingestion_allowed", "durable_mutation_allowed", "provider_execution_allowed",
    "patch_application_allowed", "dispatch_allowed", "merge_allowed",
)
EXPECTED_INVARIANT_FIELDS = ("invariant_id", "status", "evidence_refs", "notes")
EXPECTED_LOOP_FIELDS = (
    "bounded", "review_depth", "self_check_passes",
    "recursive_autonomous_loop_allowed", "adversarial_review_required",
    "missing_proof_ledger_required",
)
BOUNDARY = "PREFLIGHT ONLY\nNO PI LOOP INVOCATION\nNO SOURCE MUTATION\nNO CODEXIFY INGESTION"


def _module():
    return importlib.import_module("guardian.evidence_packets.contracts")


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_package_and_contract_module_exist() -> None:
    assert (PACKAGE / "__init__.py").exists()
    assert CONTRACTS.exists()
    assert _module()


def test_contract_module_is_stdlib_only_and_has_no_forbidden_imports() -> None:
    source = CONTRACTS.read_text()
    forbidden = (
        "fastapi", "sqlalchemy", "psycopg", "command_bus", "codex_runner_bridge",
        "scripts.guardian", "subprocess", "requests", "httpx", "docker",
    )
    for token in forbidden:
        assert token not in source.lower()
    assert "import json" in source
    assert "from collections.abc import Mapping" in source


def test_validators_consume_backend_contracts_without_import_side_effects() -> None:
    single_source = SINGLE_VALIDATOR.read_text()
    batch_source = BATCH_VALIDATOR.read_text()
    assert "guardian.evidence_packets.contracts" in single_source
    assert "guardian.evidence_packets.contracts" not in batch_source
    assert "packet_json_invalid" not in CONTRACTS.read_text()
    assert "packet_json_invalid" not in PROTOCOL_TOKENS.read_text()


def test_contract_constants_match_schema() -> None:
    contracts = _module()
    assert contracts.GUARDIAN_EVIDENCE_PACKET_SCHEMA_VERSION == "guardian_evidence_packet.v1"
    assert contracts.STATIC_VALIDATION_RESULT_SCHEMA_VERSION == "guardian_evidence_packet_static_validation_result.v1"
    assert contracts.BATCH_VALIDATION_RESULT_SCHEMA_VERSION == "guardian_evidence_packet_batch_validation_result.v1"
    assert contracts.BOUNDARY_LABEL == BOUNDARY
    assert contracts.ALLOWED_REVIEW_DEPTHS == {"light", "medium", "high", "xhigh"}
    assert contracts.ALLOWED_CLAIM_STATUSES == {"supported", "unsupported", "blocked", "inferred", "not_evaluated"}
    assert contracts.REQUIRED_PACKET_FIELDS == EXPECTED_PACKET_FIELDS
    assert contracts.REQUIRED_EVIDENCE_REF_FIELDS == EXPECTED_EVIDENCE_FIELDS
    assert contracts.REQUIRED_CLAIM_FIELDS == EXPECTED_CLAIM_FIELDS
    assert contracts.REQUIRED_AUTHORITY_LOCKS == EXPECTED_LOCKS
    assert contracts.REQUIRED_INVARIANT_CHECK_FIELDS == EXPECTED_INVARIANT_FIELDS
    assert contracts.REQUIRED_LOOP_POLICY_FIELDS == EXPECTED_LOOP_FIELDS


def test_false_authority_state_is_false_and_fresh() -> None:
    contracts = _module()
    first = contracts.false_authority_state()
    second = contracts.false_authority_state()
    assert first == {lock: False for lock in EXPECTED_LOCKS}
    assert all(value is False for value in first.values())
    assert first is not second
    first["merge_allowed"] = True
    assert second["merge_allowed"] is False


@pytest.mark.parametrize("helper, fields", [
    ("missing_packet_fields", EXPECTED_PACKET_FIELDS),
    ("missing_evidence_ref_fields", EXPECTED_EVIDENCE_FIELDS),
    ("missing_claim_fields", EXPECTED_CLAIM_FIELDS),
    ("missing_authority_locks", EXPECTED_LOCKS),
    ("missing_invariant_check_fields", EXPECTED_INVARIANT_FIELDS),
    ("missing_loop_policy_fields", EXPECTED_LOOP_FIELDS),
])
def test_missing_field_helpers_preserve_order(helper: str, fields: tuple[str, ...]) -> None:
    assert getattr(_module(), helper)({}) == fields


def test_authority_locks_true_returns_only_true_locks() -> None:
    contracts = _module()
    state = {"guardian_operational": True, "merge_allowed": True, "dispatch_allowed": False}
    assert contracts.authority_locks_true(state) == ("guardian_operational", "merge_allowed")


def test_allowed_value_helpers() -> None:
    contracts = _module()
    assert all(contracts.is_allowed_review_depth(value) for value in ("light", "medium", "high", "xhigh"))
    assert not contracts.is_allowed_review_depth("extreme")
    assert not contracts.is_allowed_review_depth(None)
    assert all(contracts.is_allowed_claim_status(value) for value in ("supported", "unsupported", "blocked", "inferred", "not_evaluated"))
    assert not contracts.is_allowed_claim_status("verified")
    assert not contracts.is_allowed_claim_status(None)


def test_boundary_and_preflight_helpers() -> None:
    contracts = _module()
    bridge = _load_fixture("guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json")
    local = _load_fixture("guardian-evidence-packet.local-validator-toolchain.v1.json")
    assert contracts.packet_declares_boundary_label(bridge)
    assert contracts.packet_declares_boundary_label(local)
    broken = {"boundary_label": "PREFLIGHT ONLY\nNO SOURCE MUTATION"}
    assert not contracts.packet_declares_boundary_label(broken)
    assert not contracts.packet_declares_boundary_label({"bad": object()})
    assert contracts.is_preflight_evidence_class("preflight_proof_chain")
    assert contracts.is_preflight_evidence_class("bridge-proof-chain")
    assert contracts.is_preflight_evidence_class("guardian_bridge_preflight")
    assert not contracts.is_preflight_evidence_class("local_static_validation_toolchain")
    assert not contracts.is_preflight_evidence_class(None)


def test_existing_fixtures_use_contract_values() -> None:
    contracts = _module()
    for name in (
        "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json",
        "guardian-evidence-packet.local-validator-toolchain.v1.json",
        "guardian-evidence-packet.generated-local-tooling.v1.json",
    ):
        packet = _load_fixture(name)
        assert set(packet["authority_state"]) == set(contracts.REQUIRED_AUTHORITY_LOCKS)
        assert contracts.is_allowed_review_depth(packet["review_depth"])
        assert all(contracts.is_allowed_claim_status(claim["status"]) for claim in packet["claim_ledger"])
