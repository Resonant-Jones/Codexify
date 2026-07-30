from __future__ import annotations

import json
import os
import subprocess
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
    "LOCAL_CHAT_MODEL": "gemma-4-12b-it-qat-4bit",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "DEEPSEEK_CHAT_MODEL": "deepseek-v4-flash",
}


def _render_compose() -> dict[str, Any]:
    environment = {
        **os.environ,
        "GUARDIAN_API_KEY": "inert-guardian-key",
        "GUARDIAN_SESSION_SECRET": "inert-session-secret",
        "GUARDIAN_JWT_SECRET": "inert-jwt-secret",
        "CODEXIFY_PREVIEW_APPROVED_EMAILS": "guest@example.com",
        "CODEXIFY_PREVIEW_ADMIN_EMAILS": "admin@example.com",
        "DEEPSEEK_API_KEY": "inert-deepseek-key",
        "LOCAL_CHAT_MODEL": "gemma-4-12b-it-qat-4bit",
        "NEO4J_PASS": "inert-neo4j-password",
    }
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


def test_private_preview_tracked_files_contain_no_secret_literals() -> None:
    compose_text = COMPOSE_FILES[1].read_text(encoding="utf-8")
    template_text = TEMPLATE.read_text(encoding="utf-8")

    assert "DEEPSEEK_API_KEY: \"${DEEPSEEK_API_KEY:?" in compose_text
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

    assert "location /health/" in nginx
    assert "proxy_pass http://backend:8888;" in nginx
    assert "service: http://127.0.0.1:8081" in cloudflared
    assert "host.docker.internal:8000" not in nginx

