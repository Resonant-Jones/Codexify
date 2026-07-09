"""Static contract tests for the live orchestration proof document.

These tests validate that the live orchestration proof document exists and
respects the dry-run-only boundary language without requiring Docker, Codex
Runner, real module execution, or receipt creation.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not execute python -m codex_runner in automated tests.
Do not write receipts in automated tests.
Do not invoke orchestration in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

ORCHESTRATION_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-orchestration-proof.md"
)
SELECTED_PROOF = (
    ARCH / "guardian-codex-runner-selected-validation-receipt-proof.md"
)
PREREQ_CONTRACT = (
    ARCH / "guardian-codex-runner-orchestration-receipt-prerequisite-contract.md"
)
PREFLIGHT_CONTRACT = (
    ARCH / "guardian-codex-runner-preflight-bridge-contract.md"
)
README = ARCH / "README.md"

SELECTED_RECEIPT_PATH = (
    "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/"
    "20260706T171742Z-plan-pack-validation-sample-dry-run-plan-pack.json"
)
PLAN_PACK_PATH = (
    "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack"
)


# ---------------------------------------------------------------------------
# Document existence and status
# ---------------------------------------------------------------------------

def test_orchestration_proof_document_exists() -> None:
    assert ORCHESTRATION_PROOF.exists(), (
        "guardian-codex-runner-command-bus-live-orchestration-proof.md must exist"
    )


def test_orchestration_proof_has_status() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    statuses = ["Status: PASS", "Status: FAIL", "Status: BLOCKED",
                "Status: **PASS**", "Status: **FAIL**", "Status: **BLOCKED**"]
    assert any(s in text for s in statuses), (
        "orchestration proof must contain one of Status: PASS, FAIL, or BLOCKED"
    )


def test_orchestration_proof_names_orchestrate_command() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    assert "internal::guardian.codex_runner.orchestrate_dry_run_preflight" in text, (
        "orchestration proof must name the orchestrate command"
    )


def test_orchestration_proof_includes_receipt_path() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    assert SELECTED_RECEIPT_PATH in text, (
        "orchestration proof must include the selected receipt path"
    )


def test_orchestration_proof_includes_plan_pack_path() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    assert PLAN_PACK_PATH in text, (
        "orchestration proof must include the sample Plan Pack path"
    )


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_orchestration_proof_includes_boundary_label() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "orchestration proof must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "orchestration proof must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "orchestration proof must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "orchestration proof must include NO CODEXIFY INGESTION boundary label"
    )


def test_orchestration_proof_includes_all_authority_locks_false() -> None:
    text = ORCHESTRATION_PROOF.read_text()
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
            f"orchestration proof must include authority lock: {lock}"
        )


# ---------------------------------------------------------------------------
# Module invocation awareness
# ---------------------------------------------------------------------------

def test_orchestration_proof_mentions_module_invocation() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    assert "CODEXRUN_INVOCATION_MODE" in text, (
        "orchestration proof must mention CODEXRUN_INVOCATION_MODE"
    )


# ---------------------------------------------------------------------------
# Write-flag / no-execution assertions
# ---------------------------------------------------------------------------

def test_orchestration_proof_states_no_write_flags() -> None:
    text = ORCHESTRATION_PROOF.read_text().lower()
    assert "no write flags" in text, (
        "orchestration proof must state no write flags were used"
    )


def test_orchestration_proof_states_no_receipt_written() -> None:
    text = ORCHESTRATION_PROOF.read_text().lower()
    assert "null" in text and "validation_receipt_path" in text, (
        "orchestration proof must state no receipt is written"
    )


def test_orchestration_proof_states_no_orchestration_receipt_written() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    assert "orchestration_receipt_path" in text and "null" in text, (
        "orchestration proof must state no orchestration receipt is written"
    )


def test_orchestration_proof_states_no_pi_loop() -> None:
    text = ORCHESTRATION_PROOF.read_text().lower()
    assert "no pi loop" in text or "pi_loop_invoked: false" in text.lower(), (
        "orchestration proof must state no Pi Loop invocation"
    )


def test_orchestration_proof_states_no_plan_execution() -> None:
    text = ORCHESTRATION_PROOF.read_text().lower()
    assert "no plan execution" in text or "execution_performed: false" in text.lower(), (
        "orchestration proof must state no plan execution"
    )


def test_orchestration_proof_states_no_source_mutation() -> None:
    text = ORCHESTRATION_PROOF.read_text().lower()
    assert "no source mutation" in text or "source_mutation_performed: false" in text.lower(), (
        "orchestration proof must state no source mutation"
    )


def test_orchestration_proof_states_no_ui_support() -> None:
    text = ORCHESTRATION_PROOF.read_text().lower()
    assert "no ui support" in text or "no ui" in text, (
        "orchestration proof must state no UI support"
    )


def test_orchestration_proof_states_no_codexify_ingestion() -> None:
    text = ORCHESTRATION_PROOF.read_text().lower()
    assert "no codexify ingestion" in text or "codexify_ingestion_performed: false" in text.lower(), (
        "orchestration proof must state no Codexify ingestion"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_selected_proof_links_orchestration_proof() -> None:
    text = SELECTED_PROOF.read_text()
    assert "guardian-codex-runner-command-bus-live-orchestration-proof.md" in text, (
        "selected receipt proof must link the orchestration proof"
    )


def test_prerequisite_contract_links_orchestration_proof() -> None:
    text = PREREQ_CONTRACT.read_text()
    assert "guardian-codex-runner-command-bus-live-orchestration-proof.md" in text, (
        "prerequisite contract must link the orchestration proof"
    )


def test_preflight_contract_links_orchestration_proof() -> None:
    text = PREFLIGHT_CONTRACT.read_text()
    assert "guardian-codex-runner-command-bus-live-orchestration-proof.md" in text, (
        "preflight bridge contract must link the orchestration proof"
    )


def test_readme_links_orchestration_proof() -> None:
    text = README.read_text()
    assert "guardian-codex-runner-command-bus-live-orchestration-proof.md" in text, (
        "README must link the orchestration proof"
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
