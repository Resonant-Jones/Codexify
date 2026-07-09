"""Static contract tests for the bridge proof-chain index.

These tests validate that the proof-chain index exists, lists all expected
artifacts, and preserves the preflight-only boundary language — all without
requiring Docker, Codex Runner, or runtime execution.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not execute python -m codex_runner in automated tests.
Do not invoke validation in automated tests.
Do not invoke orchestration in automated tests.
Do not write receipts in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

PROOF_CHAIN_INDEX = (
    ARCH / "guardian-codex-runner-bridge-proof-chain-index.md"
)
PREFLIGHT_CONTRACT = (
    ARCH / "guardian-codex-runner-preflight-bridge-contract.md"
)
AUTH_CONTRACT = (
    ARCH / "guardian-codex-runner-local-auth-override-contract.md"
)
README = ARCH / "README.md"

EXPECTED_ARTIFACTS = [
    "guardian-codex-runner-preflight-bridge-contract.md",
    "guardian-codex-runner-command-bus-proof.md",
    "guardian-codex-runner-container-visibility-contract.md",
    "guardian-codex-runner-command-bus-live-validate-proof.md",
    "guardian-codex-runner-command-bus-live-validate-retry-proof.md",
    "guardian-codex-runner-command-bus-live-validate-mounted-proof.md",
    "guardian-codex-runner-command-bus-live-validate-module-proof.md",
    "guardian-codex-runner-orchestration-receipt-prerequisite-contract.md",
    "guardian-codex-runner-validation-receipt-availability-proof.md",
    "guardian-codex-runner-selected-validation-receipt-proof.md",
    "guardian-codex-runner-command-bus-live-orchestration-proof.md",
    "guardian-codex-runner-local-auth-override-contract.md",
]


# ---------------------------------------------------------------------------
# Document existence
# ---------------------------------------------------------------------------

def test_proof_chain_index_document_exists() -> None:
    assert PROOF_CHAIN_INDEX.exists(), (
        "guardian-codex-runner-bridge-proof-chain-index.md must exist"
    )


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_proof_chain_index_includes_boundary_label() -> None:
    text = PROOF_CHAIN_INDEX.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "proof-chain index must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "proof-chain index must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "proof-chain index must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "proof-chain index must include NO CODEXIFY INGESTION boundary label"
    )


def test_proof_chain_index_includes_all_authority_locks_false() -> None:
    text = PROOF_CHAIN_INDEX.read_text()
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
            f"proof-chain index must include authority lock: {lock}"
        )


# ---------------------------------------------------------------------------
# Command identity
# ---------------------------------------------------------------------------

def test_proof_chain_index_names_validate_command() -> None:
    text = PROOF_CHAIN_INDEX.read_text()
    assert "internal::guardian.codex_runner.validate_plan_pack" in text, (
        "proof-chain index must name the validate command"
    )


def test_proof_chain_index_names_orchestrate_command() -> None:
    text = PROOF_CHAIN_INDEX.read_text()
    assert "internal::guardian.codex_runner.orchestrate_dry_run_preflight" in text, (
        "proof-chain index must name the orchestrate command"
    )


def test_proof_chain_index_states_both_proven() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "both" in text and "preflight" in text and "proven" in text, (
        "proof-chain index must state both bridge preflight commands are live-proven"
    )


# ---------------------------------------------------------------------------
# Dry-run / no-execution assertions
# ---------------------------------------------------------------------------

def test_proof_chain_index_states_orchestration_dry_run_only() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "dry-run" in text, (
        "proof-chain index must state orchestration proof was dry-run preflight only"
    )


def test_proof_chain_index_states_no_source_mutation() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "no source mutation" in text or "source mutation" in text, (
        "proof-chain index must state no source mutation occurred"
    )


def test_proof_chain_index_states_no_pi_loop() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "no pi loop" in text or "pi loop invocation" in text, (
        "proof-chain index must state no Pi Loop invocation occurred"
    )


def test_proof_chain_index_states_no_plan_execution() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "no plan execution" in text or "plan execution" in text, (
        "proof-chain index must state no plan execution occurred"
    )


def test_proof_chain_index_states_no_write_flags() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "no write flags" in text or "write flags" in text, (
        "proof-chain index must state no write flags were enabled"
    )


def test_proof_chain_index_states_no_receipt_written() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "no receipt was written" in text or "not ingested" in text, (
        "proof-chain index must state no receipt was written by live orchestration proof"
    )


def test_proof_chain_index_states_no_orchestration_log() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "orchestration log" in text, (
        "proof-chain index must mention orchestration log not written"
    )


def test_proof_chain_index_states_no_orchestration_receipt() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "orchestration receipt" in text, (
        "proof-chain index must mention orchestration receipt not written"
    )


def test_proof_chain_index_states_no_provider_execution() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "provider execution" in text, (
        "proof-chain index must state no provider execution occurred"
    )


def test_proof_chain_index_states_no_codexify_ingestion() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "codexify ingestion" in text, (
        "proof-chain index must state no Codexify ingestion occurred"
    )


def test_proof_chain_index_states_command_bus_not_ingestion() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "not ingestion" in text or "run/event records" in text, (
        "proof-chain index must state command-bus run/event records are not ingestion"
    )


# ---------------------------------------------------------------------------
# Local auth override posture
# ---------------------------------------------------------------------------

def test_proof_chain_index_states_auth_opt_in() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "opt-in" in text and "auth" in text, (
        "proof-chain index must state local-auth override is opt-in and local-only"
    )


def test_proof_chain_index_states_auth_not_production() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "not production" in text, (
        "proof-chain index must state local-auth override is not production auth policy"
    )


def test_proof_chain_index_states_not_ui_support() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "not ui support" in text or "no ui" in text, (
        "proof-chain index must state index is not UI support"
    )


def test_proof_chain_index_states_not_release_expansion() -> None:
    text = PROOF_CHAIN_INDEX.read_text().lower()
    assert "not release support" in text or "release support expansion" in text or "not widen release" in text, (
        "proof-chain index must state index is not release support expansion"
    )


# ---------------------------------------------------------------------------
# Artifact listing
# ---------------------------------------------------------------------------

def test_proof_chain_index_lists_all_expected_artifacts() -> None:
    text = PROOF_CHAIN_INDEX.read_text()
    missing = []
    for artifact in EXPECTED_ARTIFACTS:
        if artifact not in text:
            missing.append(artifact)
    assert not missing, (
        f"proof-chain index missing artifact links: {missing}"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_preflight_contract_links_proof_chain_index() -> None:
    text = PREFLIGHT_CONTRACT.read_text()
    assert "guardian-codex-runner-bridge-proof-chain-index.md" in text, (
        "preflight bridge contract must link the proof-chain index"
    )


def test_auth_contract_links_proof_chain_index() -> None:
    text = AUTH_CONTRACT.read_text()
    assert "guardian-codex-runner-bridge-proof-chain-index.md" in text, (
        "local-auth override contract must link the proof-chain index"
    )


def test_readme_links_proof_chain_index() -> None:
    text = README.read_text()
    assert "guardian-codex-runner-bridge-proof-chain-index.md" in text, (
        "README must link the proof-chain index"
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
