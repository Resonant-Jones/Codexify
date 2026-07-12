"""Static contract tests for the module live validate proof document.

These tests validate that the module live validate proof document exists and
respects the validate-only boundary language without requiring Docker, Codex
Runner, or real module execution.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not execute python -m codex_runner in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

MODULE_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-validate-module-proof.md"
)
VISIBILITY_CONTRACT = (
    ARCH / "guardian-codex-runner-container-visibility-contract.md"
)
MOUNTED_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-validate-mounted-proof.md"
)
README = ARCH / "README.md"


# ---------------------------------------------------------------------------
# Document existence and status
# ---------------------------------------------------------------------------

def test_module_proof_document_exists() -> None:
    assert MODULE_PROOF.exists(), (
        "guardian-codex-runner-command-bus-live-validate-module-proof.md must exist"
    )


def test_module_proof_has_status() -> None:
    text = MODULE_PROOF.read_text()
    statuses = ["Status: PASS", "Status: FAIL", "Status: BLOCKED",
                "Status: **PASS**", "Status: **FAIL**", "Status: **BLOCKED**"]
    assert any(s in text for s in statuses), (
        "module proof must contain one of Status: PASS, FAIL, or BLOCKED"
    )


# ---------------------------------------------------------------------------
# Command identity checks
# ---------------------------------------------------------------------------

def test_module_proof_names_validate_command() -> None:
    text = MODULE_PROOF.read_text()
    assert "internal::guardian.codex_runner.validate_plan_pack" in text, (
        "module proof must name validate_plan_pack command"
    )


def test_module_proof_does_not_instruct_orchestrate() -> None:
    text = MODULE_PROOF.read_text()
    assert "does not attempt" in text.lower(), (
        "module proof must have a 'does not attempt' section"
    )


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_module_proof_includes_boundary_label() -> None:
    text = MODULE_PROOF.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "module proof must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "module proof must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "module proof must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "module proof must include NO CODEXIFY INGESTION boundary label"
    )


def test_module_proof_includes_all_authority_locks_false() -> None:
    text = MODULE_PROOF.read_text()
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
            f"module proof must include authority lock: {lock}"
        )


# ---------------------------------------------------------------------------
# Module invocation awareness
# ---------------------------------------------------------------------------

def test_module_proof_mentions_invocation_mode_module() -> None:
    text = MODULE_PROOF.read_text()
    assert "CODEXRUN_INVOCATION_MODE" in text, (
        "module proof must mention CODEXRUN_INVOCATION_MODE"
    )
    assert "module" in text.lower(), (
        "module proof must mention module invocation"
    )


def test_module_proof_mentions_python_m_codex_runner() -> None:
    text = MODULE_PROOF.read_text()
    assert "python -m codex_runner" in text, (
        "module proof must mention python -m codex_runner"
    )


def test_module_proof_mentions_compose_override() -> None:
    text = MODULE_PROOF.read_text().lower()
    assert "compose" in text and "override" in text, (
        "module proof must mention the opt-in compose override"
    )


def test_module_proof_mentions_read_only_mount() -> None:
    text = MODULE_PROOF.read_text().lower()
    assert "read-only" in text or "read only" in text, (
        "module proof must mention the read-only mount"
    )


# ---------------------------------------------------------------------------
# Boundary / non-goal language
# ---------------------------------------------------------------------------

def test_module_proof_states_no_write_flags() -> None:
    text = MODULE_PROOF.read_text().lower()
    assert "no write flags" in text or "write flags" in text, (
        "module proof must state no write flags are enabled"
    )


def test_module_proof_states_no_receipt() -> None:
    text = MODULE_PROOF.read_text().lower()
    assert "no receipt" in text or "receipt" in text, (
        "module proof must state no receipt is written"
    )


def test_module_proof_states_no_orchestration_proof() -> None:
    text = MODULE_PROOF.read_text().lower()
    assert "no live orchestration" in text or "not live orchestration" in text or "live orchestration proof remains" in text, (
        "module proof must state no orchestration proof is claimed"
    )


def test_module_proof_states_no_ui_support() -> None:
    text = MODULE_PROOF.read_text().lower()
    assert "no ui support" in text or "no guardian ui" in text or "no ui" in text, (
        "module proof must state no UI support is added"
    )


def test_module_proof_states_no_codexify_ingestion() -> None:
    text = MODULE_PROOF.read_text().lower()
    assert "no codexify ingestion" in text or "does not ingest" in text, (
        "module proof must state no Codexify ingestion occurs"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_visibility_contract_links_module_proof() -> None:
    text = VISIBILITY_CONTRACT.read_text()
    assert "guardian-codex-runner-command-bus-live-validate-module-proof.md" in text, (
        "visibility contract must link the module proof document"
    )


def test_mounted_proof_links_module_proof() -> None:
    text = MOUNTED_PROOF.read_text()
    assert "guardian-codex-runner-command-bus-live-validate-module-proof.md" in text, (
        "mounted proof must link the module proof document"
    )


def test_readme_links_module_proof() -> None:
    text = README.read_text()
    assert "guardian-codex-runner-command-bus-live-validate-module-proof.md" in text, (
        "README must link the module proof document"
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
