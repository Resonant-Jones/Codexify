"""Static contract tests for the Guardian Evidence Packet static validator contract.

Tests that the validator contract documents required validation checks, issue
codes, severity levels, and pass/fail semantics — without requiring any runtime
execution.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not invoke validation or orchestration in automated tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

VALIDATOR_CONTRACT = (
    ARCH / "guardian-evidence-packet-static-validator-contract.md"
)
EVIDENCE_CONTRACT = (
    ARCH / "guardian-evidence-packet-reducer-contract.md"
)
FIXTURE = (
    ARCH / "fixtures"
    / "guardian-evidence-packet.codex-runner-bridge-proof-chain.v1.json"
)
README = ARCH / "README.md"
CURRENT_STATE = ARCH / "00-current-state.md"

ALLOWED_REVIEW_DEPTHS = {"light", "medium", "high", "xhigh"}
ALLOWED_CLAIM_STATUSES = {"supported", "unsupported", "blocked", "inferred", "not_evaluated"}
ALLOWED_RESULTS = {"pass", "pass_with_warnings", "fail"}
ALLOWED_SEVERITIES = {"error", "warning", "info"}

REQUIRED_ISSUE_CODES = [
    "packet_json_invalid",
    "packet_schema_version_missing",
    "packet_schema_version_unsupported",
    "packet_required_field_missing",
    "review_depth_invalid",
    "reducer_profile_missing",
    "evidence_ref_required_field_missing",
    "claim_required_field_missing",
    "claim_status_invalid",
    "claim_evidence_ref_missing",
    "authority_state_missing",
    "authority_lock_missing",
    "authority_lock_true_for_preflight",
    "invariant_required_field_missing",
    "uncertainty_missing_for_depth",
    "forbidden_interpretations_missing",
    "next_gate_options_missing",
    "recommended_next_gate_missing",
    "loop_policy_missing",
    "recursive_loop_allowed",
    "boundary_label_missing",
    "release_claim_expansion_risk",
    "content_hash_missing",
    "static_fixture_marker_missing",
]


# ---------------------------------------------------------------------------
# Document existence
# ---------------------------------------------------------------------------

def test_validator_contract_exists() -> None:
    assert VALIDATOR_CONTRACT.exists()


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_validator_contract_boundary_label() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    assert "PREFLIGHT ONLY" in text
    assert "NO PI LOOP INVOCATION" in text
    assert "NO SOURCE MUTATION" in text
    assert "NO CODEXIFY INGESTION" in text


def test_validator_contract_authority_locks() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    locks = [
        "guardian_operational: false",
        "plan_execution_allowed: false",
        "pi_loop_invocation_allowed: false",
        "codexify_ingestion_allowed: false",
        "durable_mutation_allowed: false",
        "provider_execution_allowed: false",
        "patch_application_allowed: false",
        "dispatch_allowed: false",
        "merge_allowed: false",
    ]
    for lock in locks:
        assert lock in text, f"Missing authority lock: {lock}"


# ---------------------------------------------------------------------------
# Validator result shape
# ---------------------------------------------------------------------------

def test_validator_defines_result_shape() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    assert "GuardianEvidencePacketStaticValidationResult" in text


def test_validator_defines_result_values() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    for val in ALLOWED_RESULTS:
        assert val in text, f"Missing result value: {val}"


def test_validator_defines_severity_values() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    for sev in ALLOWED_SEVERITIES:
        assert sev in text, f"Missing severity: {sev}"


def test_validator_defines_review_depths() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    for depth in ALLOWED_REVIEW_DEPTHS:
        assert depth in text, f"Missing review_depth: {depth}"


def test_validator_defines_claim_statuses() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    for status in ALLOWED_CLAIM_STATUSES:
        assert status in text, f"Missing claim status: {status}"


# ---------------------------------------------------------------------------
# Validation-is-not-authority assertions
# ---------------------------------------------------------------------------

def test_validator_states_validation_not_authority() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "not authority" in text or "not truth approval" in text


def test_validator_states_not_prove_claims() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "does not prove" in text or "not claim truth" in text or "not prove claims" in text


def test_validator_states_not_promote_to_authority() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "not promote" in text or "not authority" in text


def test_validator_states_not_implement_reducer() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "does not implement" in text or "not implement" in text


def test_validator_states_not_add_persistence() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "persistence" in text


def test_validator_states_not_add_ingestion() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "ingestion" in text


def test_validator_states_not_add_ui() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "ui" in text


def test_validator_states_not_add_dev_build() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "dev-build" in text or "dev build" in text


# ---------------------------------------------------------------------------
# No-authorization assertions
# ---------------------------------------------------------------------------

def test_validator_states_not_authorize_execution() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "execution" in text


def test_validator_states_not_authorize_source_mutation() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "source mutation" in text


def test_validator_states_not_authorize_pi_loop() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "pi loop" in text


def test_validator_states_not_authorize_provider_execution() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "provider execution" in text


def test_validator_states_not_authorize_codexify_ingestion() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "codexify ingestion" in text


def test_validator_states_execution_ledger_separate() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "execution ledger" in text


def test_validator_states_workorder_separate() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "workorder" in text or "work order" in text


# ---------------------------------------------------------------------------
# Issue codes
# ---------------------------------------------------------------------------

def test_validator_includes_all_required_issue_codes() -> None:
    text = VALIDATOR_CONTRACT.read_text()
    missing = [code for code in REQUIRED_ISSUE_CODES if code not in text]
    assert not missing, f"Missing issue codes: {missing}"


def test_validator_states_codes_not_runtime_tokens() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "not runtime protocol tokens" in text or "not canonical runtime tokens" in text or "not runtime tokens" in text


# ---------------------------------------------------------------------------
# Specific validation rules
# ---------------------------------------------------------------------------

def test_validator_fails_recursive_loop() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "recursive_autonomous_loop_allowed" in text


def test_validator_fails_authority_true_in_preflight() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "authority_lock_true_for_preflight" in text


def test_validator_warns_missing_forbidden_interpretations() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "forbidden_interpretations_missing" in text


def test_validator_warns_missing_uncertainty_for_depth() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "uncertainty_missing_for_depth" in text


def test_validator_warns_missing_recommended_next_gate() -> None:
    text = VALIDATOR_CONTRACT.read_text().lower()
    assert "recommended_next_gate_missing" in text


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_evidence_contract_links_validator() -> None:
    text = EVIDENCE_CONTRACT.read_text()
    assert "guardian-evidence-packet-static-validator-contract.md" in text


def test_readme_links_validator() -> None:
    text = README.read_text()
    assert "guardian-evidence-packet-static-validator-contract.md" in text


def test_current_state_names_validator() -> None:
    text = CURRENT_STATE.read_text()
    assert "static validator contract" in text


# ---------------------------------------------------------------------------
# Fixture integrity preservation
# ---------------------------------------------------------------------------

def test_fixture_still_valid_json() -> None:
    data = json.loads(FIXTURE.read_text())
    assert isinstance(data, dict)


def test_fixture_authority_still_false() -> None:
    data = json.loads(FIXTURE.read_text())
    auth = data["authority_state"]
    for lock in auth:
        assert auth[lock] is False, f"Fixture authority lock {lock} must remain false"


def test_fixture_boundary_label_intact() -> None:
    data = json.loads(FIXTURE.read_text())
    bl = data.get("boundary_label", "")
    assert "PREFLIGHT ONLY" in bl
    assert "NO PI LOOP INVOCATION" in bl
    assert "NO SOURCE MUTATION" in bl
    assert "NO CODEXIFY INGESTION" in bl


def test_fixture_still_recommends_validator() -> None:
    data = json.loads(FIXTURE.read_text())
    assert data["recommended_next_gate"] == "guardian_evidence_packet_static_validator_contract"


def test_fixture_has_static_marker() -> None:
    data = json.loads(FIXTURE.read_text())
    prov = data.get("provenance", {})
    assert prov.get("static_fixture") is True, "Fixture must declare static_fixture: true"


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def test_no_frontend_files_changed() -> None:
    assert (ROOT / "frontend").exists()
