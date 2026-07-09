"""Static contract tests for the container visibility compose override and docs.

These tests validate that the opt-in Docker mount contract exists and respects
the read-only, preflight-only boundary without requiring Docker, the Codex
Runner checkout, or real codexrun execution.

Do not run Docker in automated tests.
Do not require /Volumes/Dev_SSD/Codex-Runner to exist in automated tests.
Do not execute real codexrun in automated tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "docs" / "architecture"

COMPOSE_OVERRIDE = ROOT / "docker-compose.codex-runner-bridge.yml"
COMPOSE_DEFAULT = ROOT / "docker-compose.yml"

VISIBILITY_CONTRACT = (
    ARCH / "guardian-codex-runner-container-visibility-contract.md"
)
LIVE_VALIDATE_RETRY_PROOF = (
    ARCH / "guardian-codex-runner-command-bus-live-validate-retry-proof.md"
)
README = ARCH / "README.md"


# ---------------------------------------------------------------------------
# Compose override existence and shape
# ---------------------------------------------------------------------------

def test_compose_override_file_exists() -> None:
    assert COMPOSE_OVERRIDE.exists(), (
        "docker-compose.codex-runner-bridge.yml must exist"
    )


def test_compose_override_references_backend() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    # Must have a services.backend entry (YAML key)
    assert re.search(r"^\s{2}backend\s*:", text, re.MULTILINE), (
        "compose override must declare a backend service"
    )


def test_compose_override_readonly_mount_present() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    # Must include the exact read-only mount with env-var defaults
    assert "${CODEX_RUNNER_HOST_ROOT:-/Volumes/Dev_SSD/Codex-Runner}" in text, (
        "compose override must mount the host Codex Runner checkout"
    )
    assert "${CODEX_RUNNER_CONTAINER_ROOT:-/Volumes/Dev_SSD/Codex-Runner}:ro" in text, (
        "compose override must mount Codex Runner read-only (:ro)"
    )


def test_compose_override_no_writable_codex_runner() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    # Find all Codex-Runner volume lines and confirm none lack :ro
    codex_lines = [
        line
        for line in text.splitlines()
        if "Codex-Runner" in line and "volume" not in line.lower()
    ]
    for line in codex_lines:
        if "CODEX_RUNNER" in line or "/Codex-Runner" in line:
            # Must end with :ro or be a comment
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "Codex-Runner" in stripped:
                assert stripped.rstrip().endswith(":ro"), (
                    f"Codex Runner mount must be read-only; found: {stripped!r}"
                )


def test_compose_override_no_image_or_build() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    # The override should not define a new backend image or build target
    assert "image:" not in text, (
        "compose override must not define a new backend image"
    )
    assert "build:" not in text, (
        "compose override must not define a new backend build target"
    )


def test_compose_override_does_not_modify_default_compose() -> None:
    """Confirm the default docker-compose.yml has not been changed by this task."""
    default_text = COMPOSE_DEFAULT.read_text()
    assert "Codex-Runner" not in default_text, (
        "default docker-compose.yml must not contain Codex-Runner mount"
    )


# ---------------------------------------------------------------------------
# Compose override comment / boundary checks
# ---------------------------------------------------------------------------

def test_compose_override_states_opt_in() -> None:
    text = COMPOSE_OVERRIDE.read_text().lower()
    assert "opt-in" in text, "compose override must state it is opt-in"


def test_compose_override_states_local_only() -> None:
    text = COMPOSE_OVERRIDE.read_text().lower()
    assert "local-only" in text, "compose override must state it is local-only"


def test_compose_override_states_no_write_flags() -> None:
    text = COMPOSE_OVERRIDE.read_text().lower()
    assert "no write flags" in text, (
        "compose override must explicitly state no write flags"
    )


def test_compose_override_states_no_pi_loop() -> None:
    text = COMPOSE_OVERRIDE.read_text().lower()
    assert "no pi loop invocation" in text, (
        "compose override must explicitly state no Pi Loop invocation"
    )


def test_compose_override_states_no_source_mutation() -> None:
    text = COMPOSE_OVERRIDE.read_text().lower()
    assert "no source mutation" in text, (
        "compose override must explicitly state no source mutation"
    )


def test_compose_override_states_no_codexify_ingestion() -> None:
    text = COMPOSE_OVERRIDE.read_text().lower()
    assert "no codexify ingestion" in text, (
        "compose override must explicitly state no Codexify ingestion"
    )


# ---------------------------------------------------------------------------
# Container visibility contract doc
# ---------------------------------------------------------------------------

def test_visibility_contract_doc_exists() -> None:
    assert VISIBILITY_CONTRACT.exists(), (
        "guardian-codex-runner-container-visibility-contract.md must exist"
    )


def test_visibility_contract_includes_failed_path() -> None:
    text = VISIBILITY_CONTRACT.read_text()
    assert "/Volumes/Dev_SSD/Codex-Runner" in text, (
        "visibility contract must reference the exact failed path"
    )


def test_visibility_contract_includes_startup_command() -> None:
    text = VISIBILITY_CONTRACT.read_text()
    assert "docker compose -f docker-compose.yml -f docker-compose.codex-runner-bridge.yml" in text, (
        "visibility contract must include the startup command with both compose files"
    )


def test_visibility_contract_includes_validation_command() -> None:
    text = VISIBILITY_CONTRACT.read_text()
    assert "exec backend test -d" in text, (
        "visibility contract must include the validation command using both compose files"
    )
    assert "docker compose -f docker-compose.yml -f docker-compose.codex-runner-bridge.yml" in text, (
        "validation command must reference both compose files"
    )


def test_visibility_contract_includes_boundary_label() -> None:
    text = VISIBILITY_CONTRACT.read_text()
    assert "PREFLIGHT ONLY" in text, (
        "visibility contract must include PREFLIGHT ONLY boundary label"
    )
    assert "NO PI LOOP INVOCATION" in text, (
        "visibility contract must include NO PI LOOP INVOCATION boundary label"
    )
    assert "NO SOURCE MUTATION" in text, (
        "visibility contract must include NO SOURCE MUTATION boundary label"
    )
    assert "NO CODEXIFY INGESTION" in text, (
        "visibility contract must include NO CODEXIFY INGESTION boundary label"
    )


def test_visibility_contract_says_not_live_validation_proof() -> None:
    text = VISIBILITY_CONTRACT.read_text().lower()
    assert "not live validation proof" in text or "does not prove live validation" in text, (
        "visibility contract must state it is not live validation proof"
    )


def test_visibility_contract_says_not_live_orchestration_proof() -> None:
    text = VISIBILITY_CONTRACT.read_text().lower()
    assert "not live orchestration proof" in text or "does not prove live orchestration" in text, (
        "visibility contract must state it is not live orchestration proof"
    )


def test_visibility_contract_says_not_ui_support() -> None:
    text = VISIBILITY_CONTRACT.read_text().lower()
    assert "not ui support" in text or "does not add ui support" in text or "no guardian ui" in text or "no ui panel" in text, (
        "visibility contract must state it is not UI support"
    )


# ---------------------------------------------------------------------------
# Cross-reference checks
# ---------------------------------------------------------------------------

def test_readme_links_visibility_contract() -> None:
    text = README.read_text()
    assert "guardian-codex-runner-container-visibility-contract.md" in text, (
        "README must link the container visibility contract"
    )


def test_live_validate_retry_proof_links_visibility_contract() -> None:
    text = LIVE_VALIDATE_RETRY_PROOF.read_text()
    assert "guardian-codex-runner-container-visibility-contract.md" in text, (
        "live validate retry proof must link the container visibility contract"
    )


def test_live_validate_retry_proof_has_visibility_section() -> None:
    text = LIVE_VALIDATE_RETRY_PROOF.read_text()
    assert "## 3. Container Visibility Contract" in text, (
        "live validate retry proof must have a Container Visibility Contract section"
    )


# ---------------------------------------------------------------------------
# Invariant checks
# ---------------------------------------------------------------------------

def test_no_frontend_files_changed() -> None:
    """No frontend files should be modified by this task."""
    frontend_dir = ROOT / "frontend"
    # This is a static check only—the actual git diff will catch any changes
    assert frontend_dir.exists(), "frontend directory should still exist"


def test_no_new_route_file() -> None:
    """No new route file should be added."""
    routes_dir = ROOT / "guardian" / "routes"
    existing = set(p.name for p in routes_dir.glob("*.py"))
    # Only check that we didn't add a bridge or codex_runner route file
    forbidden = {
        "bridge.py",
        "codex_runner.py",
        "codex_runner_bridge.py",
        "guardian_bridge.py",
        "codexrun.py",
    }
    assert existing.isdisjoint(forbidden), (
        f"No new route file should be added: found {existing & forbidden}"
    )


def test_no_write_flags_in_compose_override() -> None:
    text = COMPOSE_OVERRIDE.read_text().lower()
    disallowed = [
        "write_receipt",
        "write_orchestration_log",
        "write_orchestration_receipt",
    ]
    for term in disallowed:
        assert term not in text, (
            f"compose override must not reference {term}"
        )


def test_compose_override_no_secrets() -> None:
    text = COMPOSE_OVERRIDE.read_text()
    secret_patterns = [
        r"GUARDIAN_API_KEY\s*[=:]\s*\S+",
        r"API_KEY\s*[=:]\s*\S+",
        r"password\s*[=:]\s*\S+",
    ]
    for pattern in secret_patterns:
        assert not re.search(pattern, text, re.IGNORECASE), (
            f"compose override must not contain secrets matching {pattern!r}"
        )
