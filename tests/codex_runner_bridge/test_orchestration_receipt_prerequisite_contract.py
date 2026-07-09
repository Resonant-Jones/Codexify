"""Static contract tests for the orchestration receipt prerequisite contract.

These tests validate that the prerequisite contract document exists and
respects the evidence-only boundary language without requiring Docker, Codex
Runner, real module execution, or receipt creation.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not execute python -m codex_runner in automated tests.
Do not write receipts in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

PREREQ_CONTRACT = (
    ARCH / "guardian-codex-runner-orchestration-receipt-prerequisite-contract.md"
)
MODULE_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-validate-module-proof.md"
)
PREFLIGHT_CONTRACT = (
    ARCH / "guardian-codex-runner-preflight-bridge-contract.md"
)
README = ARCH / "README.md"


# ---------------------------------------------------------------------------
# Document existence
# ---------------------------------------------------------------------------

def test_prerequisite_contract_document_exists() -> None:
    assert PREREQ_CONTRACT.exists(), (
        "guardian-codex-runner-orchestration-receipt-prerequisite-contract.md must exist"
    )


# ---------------------------------------------------------------------------
# Command identity checks
# ---------------------------------------------------------------------------

def test_prerequisite_contract_mentions_orchestrate_command() -> None:
    text = PREREQ_CONTRACT.read_text()
    assert "internal::guardian.codex_runner.orchestrate_dry_run_preflight" in text, (
        "prerequisite contract must mention the orchestrate command"
    )


def test_prerequisite_contract_mentions_validate_command() -> None:
    text = PREREQ_CONTRACT.read_text()
    assert "internal::guardian.codex_runner.validate_plan_pack" in text, (
        "prerequisite contract must mention the validate command"
    )


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_prerequisite_contract_includes_boundary_label() -> None:
    text = PREREQ_CONTRACT.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "prerequisite contract must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "prerequisite contract must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "prerequisite contract must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "prerequisite contract must include NO CODEXIFY INGESTION boundary label"
    )


def test_prerequisite_contract_includes_all_authority_locks_false() -> None:
    text = PREREQ_CONTRACT.read_text()
    required_locks = [
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
    for lock in required_locks:
        assert lock in text, (
            f"prerequisite contract must include authority lock: {lock}"
        )


# ---------------------------------------------------------------------------
# Validate proof status awareness
# ---------------------------------------------------------------------------

def test_prerequisite_contract_states_validate_proof_passed() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "passed" in text or "pass" in text, (
        "prerequisite contract must state validate-only live proof passed"
    )


def test_prerequisite_contract_states_orchestration_deferred() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "deferred" in text, (
        "prerequisite contract must state orchestration remains deferred"
    )


# ---------------------------------------------------------------------------
# No-execution / no-receipt assertions
# ---------------------------------------------------------------------------

def test_prerequisite_contract_states_not_run_orchestration() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "not run in this task" in text, (
        "prerequisite contract must state orchestration is not run in this task"
    )


def test_prerequisite_contract_states_does_not_create_receipts() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "does not create" in text or "not create" in text, (
        "prerequisite contract must state this task does not create receipts"
    )


def test_prerequisite_contract_states_does_not_write_receipts() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "does not write" in text or "not write" in text or "is not a valid proof path" in text, (
        "prerequisite contract must state this task does not write receipts"
    )


def test_prerequisite_contract_states_does_not_ingest_receipts() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "does not ingest" in text or "not ingest" in text, (
        "prerequisite contract must state this task does not ingest receipts"
    )


# ---------------------------------------------------------------------------
# Evidence-only receipt semantics
# ---------------------------------------------------------------------------

def test_prerequisite_contract_states_receipt_is_evidence_only() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "evidence only" in text or "is evidence" in text, (
        "prerequisite contract must state a validation receipt is evidence only"
    )


def test_prerequisite_contract_states_receipt_no_pi_loop() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "receipt" in text and "pi loop" in text, (
        "prerequisite contract must relate receipt to Pi Loop prohibition"
    )


def test_prerequisite_contract_states_receipt_no_plan_execution() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "receipt" in text and "plan execution" in text, (
        "prerequisite contract must relate receipt to plan execution prohibition"
    )


def test_prerequisite_contract_states_receipt_no_codexify_ingestion() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "receipt" in text and "codexify ingestion" in text, (
        "prerequisite contract must relate receipt to Codexify ingestion prohibition"
    )


def test_prerequisite_contract_states_receipt_no_write_flags() -> None:
    text = PREREQ_CONTRACT.read_text().lower()
    assert "receipt" in text and "write flags" in text, (
        "prerequisite contract must relate receipt to write flags prohibition"
    )


# ---------------------------------------------------------------------------
# Future orchestration payload
# ---------------------------------------------------------------------------

def test_prerequisite_contract_includes_future_payload() -> None:
    text = PREREQ_CONTRACT.read_text()
    assert "NOT RUN IN THIS TASK" in text, (
        "prerequisite contract must include a future orchestration payload marked NOT RUN IN THIS TASK"
    )


def test_prerequisite_contract_includes_receipt_path_placeholder() -> None:
    text = PREREQ_CONTRACT.read_text()
    assert "validation_receipt_path" in text, (
        "prerequisite contract must include validation_receipt_path placeholder"
    )
    assert "operator-selected-validation-receipt" in text, (
        "prerequisite contract must include operator-selected receipt placeholder"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_module_proof_links_prerequisite_contract() -> None:
    text = MODULE_PROOF.read_text()
    assert "guardian-codex-runner-orchestration-receipt-prerequisite-contract.md" in text, (
        "module proof must link the prerequisite contract"
    )


def test_preflight_contract_links_prerequisite_contract() -> None:
    text = PREFLIGHT_CONTRACT.read_text()
    assert "guardian-codex-runner-orchestration-receipt-prerequisite-contract.md" in text, (
        "preflight bridge contract must link the prerequisite contract"
    )


def test_readme_links_prerequisite_contract() -> None:
    text = README.read_text()
    assert "guardian-codex-runner-orchestration-receipt-prerequisite-contract.md" in text, (
        "README must link the prerequisite contract"
    )


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def test_no_frontend_files_changed() -> None:
    """No frontend files should be modified by this task."""
    frontend_dir = ROOT / "frontend"
    assert frontend_dir.exists(), "frontend directory should still exist"


def test_no_new_route_file() -> None:
    """No new route file should be added by this task."""
    routes_dir = ROOT / "guardian" / "routes"
    existing = set(p.name for p in routes_dir.glob("*.py"))
    forbidden = {
        "bridge.py",
        "codex_runner.py",
        "codex_runner_bridge.py",
        "guardian_bridge.py",
    }
    assert existing.isdisjoint(forbidden), (
        f"No new route file should be added: found {existing & forbidden}"
    )
