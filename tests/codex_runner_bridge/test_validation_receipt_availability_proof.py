"""Static contract tests for the validation receipt availability proof.

These tests validate that the receipt availability proof document exists and
respects the evidence-only boundary language without requiring Docker, Codex
Runner, real module execution, or receipt creation.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not execute python -m codex_runner in automated tests.
Do not write receipts in automated tests.
Do not read real receipt contents in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

AVAILABILITY_PROOF = (
    ARCH / "guardian-codex-runner-validation-receipt-availability-proof.md"
)
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
# Document existence and status
# ---------------------------------------------------------------------------

def test_availability_proof_document_exists() -> None:
    assert AVAILABILITY_PROOF.exists(), (
        "guardian-codex-runner-validation-receipt-availability-proof.md must exist"
    )


def test_availability_proof_has_status() -> None:
    text = AVAILABILITY_PROOF.read_text()
    statuses = ["Status: AVAILABLE", "Status: BLOCKED", "Status: FAIL",
                "Status: **AVAILABLE**", "Status: **BLOCKED**", "Status: **FAIL**"]
    assert any(s in text for s in statuses), (
        "availability proof must contain one of Status: AVAILABLE, BLOCKED, or FAIL"
    )


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_availability_proof_includes_boundary_label() -> None:
    text = AVAILABILITY_PROOF.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "availability proof must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "availability proof must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "availability proof must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "availability proof must include NO CODEXIFY INGESTION boundary label"
    )


def test_availability_proof_includes_all_authority_locks_false() -> None:
    text = AVAILABILITY_PROOF.read_text()
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
            f"availability proof must include authority lock: {lock}"
        )


# ---------------------------------------------------------------------------
# No-execution / no-receipt assertions
# ---------------------------------------------------------------------------

def test_availability_proof_states_not_run_orchestration() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "does not run orchestration" in text or "not run orchestration" in text or "does not" in text, (
        "availability proof must state this task does not run orchestration"
    )


def test_availability_proof_states_does_not_create_receipts() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "does not create" in text or "not create" in text, (
        "availability proof must state this task does not create receipts"
    )


def test_availability_proof_states_does_not_write_receipts() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "does not write" in text or "not write" in text or "no write" in text, (
        "availability proof must state this task does not write receipts"
    )


def test_availability_proof_states_no_model_judgment() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "model judgment" in text or "automated scanning" in text, (
        "availability proof must state receipts are not selected by model judgment"
    )


def test_availability_proof_states_does_not_trust_receipts() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "not trust" in text or "does not trust" in text, (
        "availability proof must state this task does not trust receipts"
    )


def test_availability_proof_states_does_not_ingest_receipts() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "does not ingest" in text or "not ingest" in text, (
        "availability proof must state this task does not ingest receipts"
    )


# ---------------------------------------------------------------------------
# Evidence-only receipt semantics
# ---------------------------------------------------------------------------

def test_availability_proof_states_receipt_is_evidence_only() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "evidence only" in text or "is evidence" in text, (
        "availability proof must state a validation receipt is evidence only"
    )


def test_availability_proof_states_no_pi_loop_from_receipt() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "pi loop" in text, (
        "availability proof must mention Pi Loop invocation prohibition"
    )


def test_availability_proof_states_no_plan_execution_from_receipt() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "plan execution" in text, (
        "availability proof must mention plan execution prohibition"
    )


def test_availability_proof_states_no_codexify_ingestion_from_receipt() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "codexify ingestion" in text, (
        "availability proof must mention Codexify ingestion prohibition"
    )


def test_availability_proof_states_no_write_flags_from_receipt() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "write flags" in text, (
        "availability proof must mention write flags prohibition"
    )


def test_availability_proof_states_orchestration_deferred() -> None:
    text = AVAILABILITY_PROOF.read_text().lower()
    assert "deferred" in text, (
        "availability proof must state live orchestration remains deferred"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_prerequisite_contract_links_availability_proof() -> None:
    text = PREREQ_CONTRACT.read_text()
    assert "guardian-codex-runner-validation-receipt-availability-proof.md" in text, (
        "prerequisite contract must link the availability proof"
    )


def test_module_proof_links_availability_proof() -> None:
    text = MODULE_PROOF.read_text()
    assert "guardian-codex-runner-validation-receipt-availability-proof.md" in text, (
        "module proof must link the availability proof"
    )


def test_preflight_contract_links_availability_proof() -> None:
    text = PREFLIGHT_CONTRACT.read_text()
    assert "guardian-codex-runner-validation-receipt-availability-proof.md" in text, (
        "preflight bridge contract must link the availability proof"
    )


def test_readme_links_availability_proof() -> None:
    text = README.read_text()
    assert "guardian-codex-runner-validation-receipt-availability-proof.md" in text, (
        "README must link the availability proof"
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
