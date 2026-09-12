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
    temporary_env_file: str | None = None
    try:
        if runtime_env_file is None:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".env", prefix="codexify_test_runtime_", delete=False
            ) as tmp:
                temporary_env_file = tmp.name
                os.chmod(temporary_env_file, 0o600)
                tmp.write(SENTINEL_ENV_CONTENT)
            runtime_env_file = temporary_env_file
        environment["CODEXIFY_RUNTIME_ENV_FILE"] = runtime_env_file
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
    finally:
        if temporary_env_file is not None:
            os.unlink(temporary_env_file)


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

    assert config["services"]["worker-chat"]["environment"][
        "CHAT_WORKER_CONCURRENCY"
    ] == "1"


def test_private_preview_compose_publishes_only_loopback_8081() -> None:
    config = _render_compose()

    assert _published_ports(config) == [("127.0.0.1", 8081, 8080)]


def test_private_preview_compose_mounts_only_the_canonical_atlas_artifact() -> None:
    config = _render_compose()
    services = config["services"]
    origin_mounts = services["private-preview-origin"].get("volumes") or []
    atlas_source = ROOT / "projection-ui-map/rc-atlas-prototype.html"
    compose_text = COMPOSE_FILES[1].read_text(encoding="utf-8")

    assert (
        "./projection-ui-map/rc-atlas-prototype.html:"
        "/usr/share/nginx/html/codexify-atlas.html:ro" in compose_text
    )
    atlas_mounts = [
        mount
        for mount in origin_mounts
        if Path(mount["source"]).resolve() == atlas_source.resolve()
    ]
    assert atlas_source.is_file()
    assert len(atlas_mounts) == 1
    atlas_mount = atlas_mounts[0]
    assert atlas_mount["target"] == "/usr/share/nginx/html/codexify-atlas.html"
    assert atlas_mount["read_only"] is True
    assert Path(atlas_mount["source"]).resolve().is_file()
    assert Path(atlas_mount["source"]).resolve().parent == ROOT / "projection-ui-map"
    assert all(
        Path(mount["source"]).resolve()
        not in {
            ROOT.resolve(),
            (ROOT / "docs").resolve(),
            (ROOT / "projection-ui-map").resolve(),
        }
        for mount in origin_mounts
    )
    assert not any("atlas" in service_name for service_name in services)


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

    import_root_location = re.search(
        r"location\s+=\s+/api/imports/openai-account\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert import_root_location is not None, (
        "private-preview origin must preserve the slashless account-import create URI"
    )
    import_root_body = import_root_location.group("body")
    assert "proxy_pass http://guardian_backend;" in import_root_body
    assert "proxy_pass http://guardian_backend/;" not in import_root_body
    assert "proxy_set_header Host $host;" in import_root_body
    assert "proxy_set_header X-Real-IP $remote_addr;" in import_root_body
    assert (
        "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
        in import_root_body
    )
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in import_root_body
    assert "client_max_body_size 0;" not in import_root_body
    assert "rewrite" not in import_root_body
    assert "return" not in import_root_body
    assert "frontend:5173" not in import_root_body

    import_child_location = re.search(
        r"location\s+/api/imports/openai-account/\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert import_child_location is not None
    import_child_body = import_child_location.group("body")
    assert "client_max_body_size 0;" in import_child_body
    assert "proxy_pass http://guardian_backend;" in import_child_body
    assert "proxy_set_header Host $host;" in import_child_body
    assert "proxy_set_header X-Real-IP $remote_addr;" in import_child_body
    assert (
        "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
        in import_child_body
    )
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in import_child_body
    assert "frontend:5173" not in import_child_body

    assert nginx.count("client_max_body_size 25m;") == 1
    assert nginx.count("client_max_body_size 0;") == 1

    atlas_redirect = re.search(
        r"location\s+=\s+/atlas\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert atlas_redirect is not None
    assert "return 308 /atlas/;" in atlas_redirect.group("body")
    assert "proxy_pass" not in atlas_redirect.group("body")

    atlas_location = re.search(
        r"location\s+=\s+/atlas/\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert atlas_location is not None
    atlas_body = atlas_location.group("body")
    assert "default_type text/html;" in atlas_body
    assert "alias /usr/share/nginx/html/codexify-atlas.html;" in atlas_body
    assert 'add_header Cache-Control "no-store" always;' in atlas_body
    assert 'add_header X-Robots-Tag "noindex, nofollow" always;' in atlas_body
    assert "proxy_pass" not in atlas_body
    assert "proxy_set_header" not in atlas_body
    assert "guardian_backend" not in atlas_body
    assert "frontend:5173" not in atlas_body
    assert not re.search(r"location\s+/atlas/\s*\{", nginx)
    assert not re.search(r"location\s+(?:=\s+)?/docs(?:/|\s|\{)", nginx)

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
    health_children_location = re.search(
        r"location\s+/health/\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert health_children_location is not None
    assert "proxy_pass http://guardian_backend;" in health_children_location.group(
        "body"
    )
    websocket_location = re.search(
        r"location\s+/ws/\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert websocket_location is not None
    assert "proxy_pass http://guardian_backend/api/ws/;" in websocket_location.group(
        "body"
    )
    root_location = re.search(
        r"location\s+/\s*\{(?P<body>.*?)\n\s*\}",
        nginx,
        flags=re.DOTALL,
    )
    assert root_location is not None
    assert "proxy_pass http://frontend:5173;" in root_location.group("body")
    assert "service: http://127.0.0.1:8081" in cloudflared
    assert "host.docker.internal:8000" not in nginx
