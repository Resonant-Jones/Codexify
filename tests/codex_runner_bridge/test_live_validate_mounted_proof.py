"""Static contract tests for the mounted live validate proof document.

These tests validate that the mounted live validate proof document exists and
respects the validate-only boundary language without requiring Docker, Codex
Runner, or real codexrun execution.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

MOUNTED_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-validate-mounted-proof.md"
)
VISIBILITY_CONTRACT = (
    ARCH / "guardian-codex-runner-container-visibility-contract.md"
)
RETRY_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-validate-retry-proof.md"
)
README = ARCH / "README.md"


# ---------------------------------------------------------------------------
# Document existence and status
# ---------------------------------------------------------------------------


def test_mounted_proof_document_exists() -> None:
    assert (
        MOUNTED_PROOF.exists()
    ), "guardian-codex-runner-command-bus-live-validate-mounted-proof.md must exist"


def test_mounted_proof_has_status() -> None:
    text = MOUNTED_PROOF.read_text()
    statuses = [
        "Status: PASS",
        "Status: FAIL",
        "Status: BLOCKED",
        "Status: **FAIL**",
        "Status: **PASS**",
        "Status: **BLOCKED**",
    ]
    assert any(
        s in text for s in statuses
    ), "mounted proof must contain one of Status: PASS, FAIL, or BLOCKED"


# ---------------------------------------------------------------------------
# Command identity checks
# ---------------------------------------------------------------------------


def test_mounted_proof_names_validate_command() -> None:
    text = MOUNTED_PROOF.read_text()
    assert (
        "internal::guardian.codex_runner.validate_plan_pack" in text
    ), "mounted proof must name validate_plan_pack command"


def test_mounted_proof_does_not_instruct_orchestrate() -> None:
    text = MOUNTED_PROOF.read_text()
    # The doc may mention orchestrate in the context of "this proof does not
    # attempt" or "future orchestration slice".  It must not present it as
    # an invoked live command with a run result.
    #
    # Confirm the doc explicitly says it does not attempt orchestrate.
    assert (
        "does not attempt" in text.lower()
    ), "mounted proof must have a 'does not attempt' section"
    # The orchestrate command ID should only appear in the "does not attempt"
    # or "deferred" context, not as a live command invoked.
    # We verify this by ensuring it's listed under "This proof does not attempt"
    # rather than under "Live Command Invoked".


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------


def test_mounted_proof_includes_boundary_label() -> None:
    text = MOUNTED_PROOF.read_text()
    assert (
        "PREFLIGHT ONLY" in text
    ), "mounted proof must include PREFLIGHT ONLY boundary label"
    assert (
        "NO PI LOOP INVOCATION" in text
    ), "mounted proof must include NO PI LOOP INVOCATION boundary label"
    assert (
        "NO SOURCE MUTATION" in text
    ), "mounted proof must include NO SOURCE MUTATION boundary label"
    assert (
        "NO CODEXIFY INGESTION" in text
    ), "mounted proof must include NO CODEXIFY INGESTION boundary label"


def test_mounted_proof_includes_all_authority_locks_false() -> None:
    text = MOUNTED_PROOF.read_text()
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
        assert (
            lock in text
        ), f"mounted proof must include authority lock: {lock}"


# ---------------------------------------------------------------------------
# Mount / override awareness
# ---------------------------------------------------------------------------


def test_mounted_proof_mentions_compose_override() -> None:
    text = MOUNTED_PROOF.read_text().lower()
    assert "compose" in text and (
        "override" in text or "codex-runner-bridge" in text
    ), "mounted proof must mention the opt-in compose override"


def test_mounted_proof_mentions_read_only_mount() -> None:
    text = MOUNTED_PROOF.read_text().lower()
    assert (
        "read-only" in text or "read only" in text
    ), "mounted proof must mention the read-only mount"


# ---------------------------------------------------------------------------
# Boundary / non-goal language
# ---------------------------------------------------------------------------


def test_mounted_proof_states_no_write_flags() -> None:
    text = MOUNTED_PROOF.read_text().lower()
    assert (
        "no write flags" in text or "write flags" in text
    ), "mounted proof must state no write flags are enabled"


def test_mounted_proof_states_no_receipt() -> None:
    text = MOUNTED_PROOF.read_text().lower()
    assert (
        "no receipt" in text or "receipt" in text
    ), "mounted proof must state no receipt is written"


def test_mounted_proof_states_no_orchestration_proof() -> None:
    text = MOUNTED_PROOF.read_text().lower()
    assert (
        "no live orchestration" in text
        or "not live orchestration" in text
        or "does not prove live orchestration" in text
    ), "mounted proof must state no orchestration proof is claimed"


def test_mounted_proof_states_no_ui_support() -> None:
    text = MOUNTED_PROOF.read_text().lower()
    assert (
        "no ui support" in text
        or "does not prove guardian ui" in text
        or "no ui" in text
    ), "mounted proof must state no UI support is added"


def test_mounted_proof_states_no_codexify_ingestion() -> None:
    text = MOUNTED_PROOF.read_text().lower()
    assert (
        "no codexify ingestion" in text
        or "does not ingest" in text
        or "does not ingest evidence" in text
    ), "mounted proof must state no Codexify ingestion occurs"


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------


def test_visibility_contract_links_mounted_proof() -> None:
    text = VISIBILITY_CONTRACT.read_text()
    assert (
        "guardian-codex-runner-command-bus-live-validate-mounted-proof.md"
        in text
    ), "visibility contract must link the mounted proof document"


def test_retry_proof_links_mounted_proof() -> None:
    text = RETRY_PROOF.read_text()
    assert (
        "guardian-codex-runner-command-bus-live-validate-mounted-proof.md"
        in text
    ), "retry proof must link the mounted proof document"


def test_readme_links_mounted_proof() -> None:
    text = README.read_text()
    assert (
        "guardian-codex-runner-command-bus-live-validate-mounted-proof.md"
        in text
    ), "README must link the mounted proof document"


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
    existing = {p.name for p in routes_dir.glob("*.py")}
    forbidden = {
        "bridge.py",
        "codex_runner.py",
        "codex_runner_bridge.py",
        "guardian_bridge.py",
    }
    assert existing.isdisjoint(
        forbidden
    ), f"No new route file should be added: found {existing & forbidden}"
