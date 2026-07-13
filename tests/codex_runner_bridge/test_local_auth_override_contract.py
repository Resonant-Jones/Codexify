"""Static contract tests for the local-auth override contract.

These tests validate that the local-auth override contract exists, preserves
boundary language, and that the compose override contains the required auth
values — all without requiring Docker or runtime execution.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
Do not execute python -m codex_runner in automated tests.
Do not invoke orchestration in automated tests.
Do not write receipts in automated tests.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

AUTH_CONTRACT = (
    ARCH / "guardian-codex-runner-local-auth-override-contract.md"
)
ORCHESTRATION_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-orchestration-proof.md"
)
PREFLIGHT_CONTRACT = (
    ARCH / "guardian-codex-runner-preflight-bridge-contract.md"
)
CONFIG_OPS = ARCH / "config-and-ops.md"
README = ARCH / "README.md"

COMPOSE_OVERRIDE = ROOT / "docker-compose.codex-runner-bridge.yml"


# ---------------------------------------------------------------------------
# Document existence
# ---------------------------------------------------------------------------

def test_auth_contract_document_exists() -> None:
    assert AUTH_CONTRACT.exists(), (
        "guardian-codex-runner-local-auth-override-contract.md must exist"
    )


# ---------------------------------------------------------------------------
# Boundary label and authority locks
# ---------------------------------------------------------------------------

def test_auth_contract_includes_boundary_label() -> None:
    text = AUTH_CONTRACT.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "auth contract must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "auth contract must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "auth contract must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "auth contract must include NO CODEXIFY INGESTION boundary label"
    )


def test_auth_contract_includes_all_authority_locks_false() -> None:
    text = AUTH_CONTRACT.read_text()
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
            f"auth contract must include authority lock: {lock}"
        )


# ---------------------------------------------------------------------------
# Opt-in / local-only assertions
# ---------------------------------------------------------------------------

def test_auth_contract_states_opt_in() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "opt-in" in text, (
        "auth contract must state the override is opt-in"
    )


def test_auth_contract_states_local_only() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "local-only" in text or "local only" in text, (
        "auth contract must state the override is local-only"
    )


def test_auth_contract_states_default_compose_untouched() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "default" in text and "untouched" in text or "not modified" in text, (
        "auth contract must state default docker-compose.yml remains untouched"
    )


def test_auth_contract_states_not_production_auth() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "not production auth" in text or "not set production auth" in text or "production auth policy" in text, (
        "auth contract must state this is not production auth guidance"
    )


def test_auth_contract_states_not_ui_support() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "no ui support" in text or "not ui support" in text or "does not add ui" in text, (
        "auth contract must state this is not UI support"
    )


def test_auth_contract_states_not_release_expansion() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "not release support" in text or "release support expansion" in text or "not widen release" in text, (
        "auth contract must state this is not release support expansion"
    )


def test_auth_contract_states_not_plan_execution() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "plan execution" in text, (
        "auth contract must mention plan execution prohibition"
    )


def test_auth_contract_states_not_pi_loop() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "pi loop" in text, (
        "auth contract must mention Pi Loop prohibition"
    )


def test_auth_contract_states_not_codexify_ingestion() -> None:
    text = AUTH_CONTRACT.read_text().lower()
    assert "codexify ingestion" in text, (
        "auth contract must mention Codexify ingestion prohibition"
    )


# ---------------------------------------------------------------------------
# Compose override posture checks
# ---------------------------------------------------------------------------

def test_compose_override_has_local_auth_mode() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    assert 'GUARDIAN_AUTH_MODE: "local"' in text, (
        "compose override must set GUARDIAN_AUTH_MODE to local"
    )


def test_compose_override_has_multi_user_disabled() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    assert 'CODEXIFY_MULTI_USER_ENABLED: "false"' in text, (
        "compose override must set CODEXIFY_MULTI_USER_ENABLED to false"
    )


def test_compose_override_has_oauth_disabled() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    oauth_envs = [
        "GOOGLE_OAUTH_REDIRECT",
        "GOOGLE_OAUTH_CLIENT_ID",
        "GOOGLE_OAUTH_CLIENT_SECRET",
        "GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY",
    ]
    for env_name in oauth_envs:
        assert env_name in text, (
            f"compose override must contain OAuth env: {env_name}"
        )
        # Must be empty or "false"
        assert f"{env_name}: \"\"" in text or f"{env_name}: \"false\"" in text, (
            f"compose override must clear {env_name}"
        )


def test_compose_override_still_has_module_mode() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    assert 'CODEXRUN_INVOCATION_MODE:' in text, (
        "compose override must still have CODEXRUN_INVOCATION_MODE"
    )
    assert "module" in text, (
        "compose override must still have module mode"
    )


def test_compose_override_still_has_pythonpath() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    assert "PYTHONPATH" in text and "Codex-Runner" in text and "src" in text, (
        "compose override must still include Codex Runner src in PYTHONPATH"
    )


def test_compose_override_still_readonly() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    assert ":ro" in text, (
        "compose override must still mount Codex Runner read-only"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_orchestration_proof_links_auth_contract() -> None:
    text = ORCHESTRATION_PROOF.read_text()
    assert "guardian-codex-runner-local-auth-override-contract.md" in text, (
        "orchestration proof must link the local-auth override contract"
    )


def test_preflight_contract_links_auth_contract() -> None:
    text = PREFLIGHT_CONTRACT.read_text()
    assert "guardian-codex-runner-local-auth-override-contract.md" in text, (
        "preflight bridge contract must link the local-auth override contract"
    )


def test_config_ops_links_or_names_auth_override() -> None:
    text = CONFIG_OPS.read_text()
    assert "codex-runner-bridge.yml" in text, (
        "config-and-ops must name or link the bridge compose override"
    )


def test_readme_links_auth_contract() -> None:
    text = README.read_text()
    assert "guardian-codex-runner-local-auth-override-contract.md" in text, (
        "README must link the local-auth override contract"
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
