from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILES = (
    ROOT / "docker-compose.yml",
    ROOT / "docker-compose.private-preview.yml",
)
TEMPLATE = ROOT / ".env.private-preview.example"
EXPECTED_ENV = {
    "CODEXIFY_SUPPORTED_PROFILE": "v1-whooshd-deepseek-web",
    "LLM_PROVIDER": "local",
    "ALLOW_CLOUD_PROVIDERS": "true",
    "CODEXIFY_LOCAL_ONLY_MODE": "false",
    "CODEXIFY_EGRESS_ALLOWLIST": "deepseek",
    "LOCAL_BASE_URL": "http://host.docker.internal:8000/v1",
    "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
    "LOCAL_PROVIDER_VENDOR": "whooshd",
    "LOCAL_CHAT_MODEL": "qwen3.8-27b-4bit",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "DEEPSEEK_CHAT_MODEL": "deepseek-v4-flash",
}

SENTINEL_ENV_CONTENT = """\
DEEPSEEK_API_KEY=inert-deepseek-key
GUARDIAN_API_KEY=inert-guardian-key
GUARDIAN_SESSION_SECRET=inert-session-secret
GUARDIAN_JWT_SECRET=inert-jwt-secret
"""


def _render_compose(
    runtime_env_file: str | None = None,
) -> dict[str, Any]:
    environment: dict[str, str] = {
        **os.environ,
        "GUARDIAN_API_KEY": "inert-guardian-key",
        "GUARDIAN_SESSION_SECRET": "inert-session-secret",
        "GUARDIAN_JWT_SECRET": "inert-jwt-secret",
        "CODEXIFY_PREVIEW_APPROVED_EMAILS": "guest@example.com",
        "CODEXIFY_PREVIEW_ADMIN_EMAILS": "admin@example.com",
        "DEEPSEEK_API_KEY": "inert-deepseek-key",
        "LOCAL_CHAT_MODEL": "qwen3.8-27b-4bit",
        "NEO4J_PASS": "inert-neo4j-password",
    }
    if runtime_env_file is not None:
        environment["CODEXIFY_RUNTIME_ENV_FILE"] = runtime_env_file
    command = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILES[0]),
        "-f",
        str(COMPOSE_FILES[1]),
        "config",
        "--format",
        "json",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        pytest.skip("docker compose is unavailable")
    return json.loads(completed.stdout)


def _published_ports(config: dict[str, Any]) -> list[tuple[str, int, int]]:
    publications: list[tuple[str, int, int]] = []
    for service in config.get("services", {}).values():
        for port in service.get("ports") or []:
            publications.append(
                (
                    str(port.get("host_ip") or ""),
                    int(port["published"]),
                    int(port["target"]),
                )
            )
    return publications


def test_private_preview_compose_selects_dual_provider_contract() -> None:
    config = _render_compose()

    for service_name in ("backend", "worker-chat"):
        environment = config["services"][service_name]["environment"]
        for key, expected in EXPECTED_ENV.items():
            assert str(environment[key]).lower() == expected.lower()
        assert environment["DEEPSEEK_API_KEY"] == "inert-deepseek-key"


def test_private_preview_compose_publishes_only_loopback_8081() -> None:
    config = _render_compose()

    assert _published_ports(config) == [("127.0.0.1", 8081, 8080)]


def test_private_preview_compose_keeps_browser_secrets_empty() -> None:
    config = _render_compose()
    frontend = config["services"]["frontend"]["environment"]

    assert frontend["VITE_GUARDIAN_API_KEY"] == ""
    assert frontend["VITE_GUARDIAN_DEV_API_KEY"] == ""
    assert "DEEPSEEK_API_KEY" not in frontend
    assert "GUARDIAN_API_KEY" not in frontend
    assert "GUARDIAN_SESSION_SECRET" not in frontend
    assert "GUARDIAN_JWT_SECRET" not in frontend


def test_private_preview_frontend_env_file_isolation_prevents_server_credential_leak() -> None:
    """Reproduce the actual env-file inheritance seam.

    When CODEXIFY_RUNTIME_ENV_FILE points at a server-bearing env file,
    the frontend must not receive server-only credentials even when
    backend and worker-chat need them.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".env", prefix="codexify_test_runtime_", delete=False
    ) as tmp:
        tmp.write(SENTINEL_ENV_CONTENT)
        tmp_path = tmp.name

    try:
        os.chmod(tmp_path, 0o600)
        config = _render_compose(runtime_env_file=tmp_path)

        services = config["services"]
        backend_env = services["backend"]["environment"]
        worker_env = services["worker-chat"]["environment"]
        frontend_env = services["frontend"]["environment"]

        # Backend and worker-chat must receive the credential.
        assert backend_env.get("DEEPSEEK_API_KEY") == "inert-deepseek-key", (
            "backend must receive DEEPSEEK_API_KEY from runtime env file"
        )
        assert worker_env.get("DEEPSEEK_API_KEY") == "inert-deepseek-key", (
            "worker-chat must receive DEEPSEEK_API_KEY from runtime env file"
        )

        # Frontend must not receive any server-only credential.
        assert "DEEPSEEK_API_KEY" not in frontend_env, (
            "frontend must not receive DEEPSEEK_API_KEY"
        )
        assert "GUARDIAN_API_KEY" not in frontend_env, (
            "frontend must not receive GUARDIAN_API_KEY"
        )
        assert "GUARDIAN_SESSION_SECRET" not in frontend_env, (
            "frontend must not receive GUARDIAN_SESSION_SECRET"
        )
        assert "GUARDIAN_JWT_SECRET" not in frontend_env, (
            "frontend must not receive GUARDIAN_JWT_SECRET"
        )

        # Vite Guardian-key isolation.
        assert frontend_env.get("VITE_GUARDIAN_API_KEY") == "", (
            "frontend VITE_GUARDIAN_API_KEY must be empty"
        )
        assert frontend_env.get("VITE_GUARDIAN_DEV_API_KEY") == "", (
            "frontend VITE_GUARDIAN_DEV_API_KEY must be empty"
        )

        # Port isolation unchanged.
        assert _published_ports(config) == [("127.0.0.1", 8081, 8080)]
    finally:
        os.unlink(tmp_path)


def test_private_preview_tracked_files_contain_no_secret_literals() -> None:
    compose_text = COMPOSE_FILES[1].read_text(encoding="utf-8")
    template_text = TEMPLATE.read_text(encoding="utf-8")

    assert "DEEPSEEK_API_KEY: \"${DEEPSEEK_API_KEY:-}\"" in compose_text
    assert "GUARDIAN_SESSION_SECRET: \"${GUARDIAN_SESSION_SECRET:?" in compose_text
    assert "GUARDIAN_JWT_SECRET: \"${GUARDIAN_JWT_SECRET:?" in compose_text
    assert "DEEPSEEK_API_KEY=<set-in-untracked-private-preview-env>" in template_text
    assert "CODEXIFY_EGRESS_ALLOWLIST=deepseek" in template_text
    assert "CODEXIFY_EGRESS_ALLOWLIST=*" not in template_text


def test_private_preview_single_origin_proxy_contract() -> None:
    nginx = (ROOT / "docker/private-preview/nginx.conf").read_text(
        encoding="utf-8"
    )
    cloudflared = (
        ROOT / "config/cloudflared/private-preview.yml.example"
    ).read_text(encoding="utf-8")

    module_location = re.search(
        r"location\s+~\s+\^/api/\.\*\\\.\(\?:ts\|tsx\|js\|jsx\)\$\s*\{"
        r"(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert module_location is not None, (
        "private-preview origin must classify Vite source modules under /api/"
    )
    module_body = module_location.group("body")
    assert "proxy_pass http://frontend:5173;" in module_body
    assert "proxy_set_header Host localhost:5173;" in module_body
    assert "rewrite" not in module_body
    assert "proxy_pass http://frontend:5173/;" not in module_body

    guardian_location = re.search(
        r"location\s+(?P<modifier>\^~\s+)?/api/\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert guardian_location is not None
    assert guardian_location.group("modifier") is None, (
        "Guardian /api/ must not suppress the bounded Vite module classifier"
    )
    guardian_body = guardian_location.group("body")
    assert "proxy_pass http://guardian_backend;" in guardian_body
    assert "frontend:5173" not in guardian_body
    assert "error_page" not in guardian_body

    health_location = re.search(
        r"location\s+=\s+/health\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert health_location is not None
    assert "proxy_pass http://guardian_backend/health;" in health_location.group(
        "body"
    )
    assert "location /health/" in nginx
    assert "proxy_pass http://backend:8888;" in nginx
    assert "service: http://127.0.0.1:8081" in cloudflared
    assert "host.docker.internal:8000" not in nginx
