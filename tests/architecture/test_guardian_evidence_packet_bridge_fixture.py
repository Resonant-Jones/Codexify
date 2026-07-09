"""Static contract tests for the Guardian Evidence Packet bridge fixture.

These tests validate that the fixture exists, parses as JSON, and preserves
boundary language — all without requiring Docker or runtime execution.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not invoke validation or orchestration in automated tests.
Do not write receipts in automated tests.
Do not call live command bus in automated tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

FIXTURE = (
    ARCH / "fixtures"
    / "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json"
)
EVIDENCE_CONTRACT = (
    ARCH / "guardian-evidence-packet-reducer-contract.md"
)
PROOF_CHAIN_INDEX = (
    ARCH / "guardian-codex-runner-bridge-proof-chain-index.md"
)
README = ARCH / "README.md"

ALLOWED_CLAIM_STATUSES = {"supported", "unsupported", "blocked", "inferred", "not_evaluated"}

REQUIRED_COMMANDS = [
    "internal::guardian.codex_runner.validate_plan_pack",
    "internal::guardian.codex_runner.orchestrate_dry_run_preflight",
]


# ---------------------------------------------------------------------------
# Fixture existence and validity
# ---------------------------------------------------------------------------

def test_fixture_exists() -> None:
    assert FIXTURE.exists(), "Fixture file must exist"


def test_fixture_is_valid_json() -> None:
    data = json.loads(FIXTURE.read_text())
    assert isinstance(data, dict), "Fixture must parse to a JSON object"


# ---------------------------------------------------------------------------
# Top-level fields
# ---------------------------------------------------------------------------

@pytest.fixture
def packet():
    return json.loads(FIXTURE.read_text())


def test_schema_version(packet):
    assert packet["schema_version"] == "guardian_evidence_packet.v1"


def test_source_domain(packet):
    assert packet["source_domain"] == "codex_runner_bridge"


def test_evidence_class(packet):
    assert packet["evidence_class"] == "preflight_proof_chain"


def test_review_depth(packet):
    assert packet["review_depth"] == "high"


def test_has_reducer_profile_ref(packet):
    assert "reducer_profile_ref" in packet
    assert len(packet["reducer_profile_ref"]) > 0


def test_has_raw_evidence_refs(packet):
    assert "raw_evidence_refs" in packet
    assert len(packet["raw_evidence_refs"]) >= 10


def test_has_reduced_summary(packet):
    assert "reduced_summary" in packet
    assert len(packet["reduced_summary"]) > 0


def test_has_claim_ledger(packet):
    assert "claim_ledger" in packet
    assert len(packet["claim_ledger"]) >= 12


def test_has_authority_state(packet):
    assert "authority_state" in packet


def test_has_invariant_checks(packet):
    assert "invariant_checks" in packet


def test_has_uncertainty(packet):
    assert "uncertainty" in packet


def test_has_forbidden_interpretations(packet):
    assert "forbidden_interpretations" in packet


def test_has_next_gate_options(packet):
    assert "next_gate_options" in packet


def test_has_recommended_next_gate(packet):
    assert "recommended_next_gate" in packet
    assert len(packet["recommended_next_gate"]) > 0


def test_has_loop_policy(packet):
    assert "loop_policy" in packet


def test_has_provenance(packet):
    assert "provenance" in packet


def test_has_limits(packet):
    assert "limits" in packet


# ---------------------------------------------------------------------------
# Boundary label
# ---------------------------------------------------------------------------

def test_fixture_includes_boundary_label(packet):
    bl = packet.get("boundary_label", "")
    assert "PREFLIGHT ONLY" in bl
    assert "NO PI LOOP INVOCATION" in bl
    assert "NO SOURCE MUTATION" in bl
    assert "NO CODEXIFY INGESTION" in bl


# ---------------------------------------------------------------------------
# Authority locks
# ---------------------------------------------------------------------------

def test_authority_state_all_false(packet):
    auth = packet["authority_state"]
    locks = [
        "guardian_operational", "plan_execution_allowed",
        "pi_loop_invocation_allowed", "codexify_ingestion_allowed",
        "durable_mutation_allowed", "provider_execution_allowed",
        "patch_application_allowed", "dispatch_allowed", "merge_allowed",
    ]
    for lock in locks:
        assert lock in auth, f"Missing authority lock: {lock}"
        assert auth[lock] is False, f"Authority lock must be false: {lock}"


# ---------------------------------------------------------------------------
# Command identity
# ---------------------------------------------------------------------------

def test_fixture_names_validate_command(packet):
    text = json.dumps(packet)
    assert "internal::guardian.codex_runner.validate_plan_pack" in text


def test_fixture_names_orchestrate_command(packet):
    text = json.dumps(packet)
    assert "internal::guardian.codex_runner.orchestrate_dry_run_preflight" in text


def test_fixture_states_both_proven(packet):
    text = json.dumps(packet).lower()
    assert "proven" in text


# ---------------------------------------------------------------------------
# Preflight-only assertions
# ---------------------------------------------------------------------------

def test_fixture_states_preflight_only(packet):
    text = json.dumps(packet).lower()
    assert "preflight" in text


def test_fixture_states_no_pi_loop(packet):
    text = json.dumps(packet).lower()
    assert "pi loop" in text


def test_fixture_states_no_plan_execution(packet):
    text = json.dumps(packet).lower()
    assert "plan execution" in text


def test_fixture_states_no_source_mutation(packet):
    text = json.dumps(packet).lower()
    assert "source mutation" in text


def test_fixture_states_no_provider_execution(packet):
    text = json.dumps(packet).lower()
    assert "provider execution" in text


def test_fixture_states_no_codexify_ingestion(packet):
    text = json.dumps(packet).lower()
    assert "codexify ingestion" in text


def test_fixture_states_command_bus_not_ingestion(packet):
    text = json.dumps(packet).lower()
    assert "not codexify ingestion" in text or "operational records" in text


def test_fixture_states_not_runtime_generated(packet):
    text = json.dumps(packet).lower()
    assert "static" in text or "not generated" in text


def test_fixture_states_not_execution_ledger(packet):
    text = json.dumps(packet).lower()
    assert "execution ledger" in text


def test_fixture_states_not_workorder(packet):
    text = json.dumps(packet).lower()
    assert "workorder" in text or "work order" in text


# ---------------------------------------------------------------------------
# Next gate options
# ---------------------------------------------------------------------------

def test_recommended_next_gate(packet):
    assert packet["recommended_next_gate"] == "guardian_evidence_packet_static_validator_contract"


def test_next_gate_has_park(packet):
    gate_ids = [g["gate_id"] for g in packet["next_gate_options"]]
    assert "park_as_proven_substrate" in gate_ids


def test_next_gate_has_dev_build(packet):
    gate_ids = [g["gate_id"] for g in packet["next_gate_options"]]
    assert "dev_build_bridge_test_affordance_contract" in gate_ids


# ---------------------------------------------------------------------------
# Claim ledger validation
# ---------------------------------------------------------------------------

def test_claim_ledger_entries_valid(packet):
    for entry in packet["claim_ledger"]:
        assert "claim_id" in entry
        assert "claim" in entry
        assert "status" in entry
        assert entry["status"] in ALLOWED_CLAIM_STATUSES
        assert "evidence_refs" in entry
        assert "confidence" in entry
        assert "limits" in entry
        assert "counterclaims" in entry
        assert "missing_evidence" in entry
        assert "forbidden_interpretations" in entry


# ---------------------------------------------------------------------------
# Evidence refs validation
# ---------------------------------------------------------------------------

def test_evidence_refs_valid(packet):
    for ref in packet["raw_evidence_refs"]:
        assert "ref_id" in ref
        assert "ref_type" in ref
        assert "uri_or_path" in ref
        assert "source_system" in ref
        assert "status" in ref
        assert "trust_posture" in ref


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_evidence_contract_links_fixture():
    text = EVIDENCE_CONTRACT.read_text()
    assert "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json" in text


def test_proof_chain_index_links_fixture():
    text = PROOF_CHAIN_INDEX.read_text()
    assert "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json" in text


def test_readme_links_fixture():
    text = README.read_text()
    assert "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json" in text


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def test_no_frontend_files_changed() -> None:
    frontend_dir = ROOT / "frontend"
    assert frontend_dir.exists()


def test_no_new_route_file() -> None:
    routes_dir = ROOT / "guardian" / "routes"
    existing = set(p.name for p in routes_dir.glob("*.py"))
    forbidden = {
        "bridge.py", "codex_runner.py", "evidence_reducer.py", "evidence_packet.py",
    }
    assert existing.isdisjoint(forbidden)
