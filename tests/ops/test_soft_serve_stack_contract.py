from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.soft-serve.yml"
DEFAULT_COMPOSE_PATH = ROOT / "docker-compose.yml"
ENV_TEMPLATE_PATH = ROOT / "config/soft-serve.env.example"
SCRIPT_PATH = ROOT / "scripts/ops/soft_serve.sh"
MAKEFILE_PATH = ROOT / "Makefile"
ADR_PATH = ROOT / "docs/architecture/adr/053-vaultnode-soft-serve-local-forge-and-github-publication-remote.md"


def test_soft_serve_compose_isolated_and_pinned() -> None:
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert COMPOSE_PATH.is_file()
    assert re.findall(r"^  [a-zA-Z0-9_-]+:$", text, re.MULTILINE) == ["  soft-serve:"]
    assert "image: charmcli/soft-serve:v0.11.6" in text
    assert "latest" not in text
    assert "restart: unless-stopped" in text
    assert ":/soft-serve" in text
    assert "SOFT_SERVE_INITIAL_ADMIN_KEYS:-" in text
    assert "SOFT_SERVE_INITIAL_ADMIN_KEYS is required for Soft Serve startup" in text


def test_soft_serve_access_and_exposure_defaults_are_private() -> None:
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert "CODEXIFY_SOFT_SERVE_BIND_HOST:-127.0.0.1" in text
    assert "settings allow-keyless false" in text
    assert "settings anon-access no-access" in text
    assert "9418" not in text
    assert "${CODEXIFY_SOFT_SERVE_SSH_PORT:-23231}:23231" in text


def test_soft_serve_env_template_contains_operator_placeholders_only() -> None:
    text = ENV_TEMPLATE_PATH.read_text(encoding="utf-8")

    for name in (
        "SOFT_SERVE_INITIAL_ADMIN_KEYS",
        "CODEXIFY_SOFT_SERVE_DATA_DIR",
        "CODEXIFY_SOFT_SERVE_BIND_HOST",
        "CODEXIFY_SOFT_SERVE_SSH_PORT",
        "CODEXIFY_SOFT_SERVE_HTTP_PORT",
        "CODEXIFY_SOFT_SERVE_STATS_PORT",
        "SOFT_SERVE_NAME",
        "SOFT_SERVE_SSH_PUBLIC_URL",
        "SOFT_SERVE_HTTP_PUBLIC_URL",
    ):
        assert name in text
    assert "REPLACE_WITH_YOUR_ED25519_PUBLIC_KEY" in text
    assert "REPLACE_WITH_FORGE_HOST" in text
    assert "ssh-ed25519 AAAA" not in text


def test_soft_serve_operator_script_exposes_exact_commands_and_is_executable() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert SCRIPT_PATH.stat().st_mode & 0o111
    assert "set -euo pipefail" in text
    for command in ("config", "up", "down", "status", "logs"):
        assert f"{command})" in text
    assert "COMPOSE_FILE=\"$REPO_ROOT/docker-compose.soft-serve.yml\"" in text
    assert "git remote" not in text


def test_soft_serve_make_targets_delegate_to_operator_script() -> None:
    text = MAKEFILE_PATH.read_text(encoding="utf-8")

    for command in ("config", "up", "down", "status", "logs"):
        target = f"soft-serve-{command}:"
        assert target in text
        start = text.index(target)
        end = text.find("\n\n", start)
        block = text[start:] if end == -1 else text[start:end]
        assert f"scripts/ops/soft_serve.sh {command}" in block


def test_default_codexify_compose_does_not_reference_soft_serve() -> None:
    text = DEFAULT_COMPOSE_PATH.read_text(encoding="utf-8").lower()
    assert "soft-serve" not in text


def test_adr_preserves_optional_runtime_boundary() -> None:
    text = ADR_PATH.read_text(encoding="utf-8").lower()
    normalized = " ".join(text.split())
    assert "optional" in text
    assert "operator substrate" in text
    assert "does not widen the supported codexify runtime" in normalized
