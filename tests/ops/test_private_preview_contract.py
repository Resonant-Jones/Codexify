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
    "LOCAL_CHAT_MODEL": "local-chat",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "DEEPSEEK_MODEL_DISCOVERY_URL": "",
    "DEEPSEEK_MODEL_DISCOVERY_TIMEOUT_SECONDS": "3",
    "DEEPSEEK_CHAT_MODEL": "deepseek-v4-flash",
}
CHROMA_CONSUMERS = (
    "backend",
    "worker-chat",
    "worker-document-embed",
    "worker-chat-embed",
    "obsidian-ingest",
    "embedding-backfill",
)
EXPECTED_CHROMA_ENV = {
    "CODEXIFY_VECTOR_STORE": "chroma",
    "CODEXIFY_CHROMA_PATH": "/app/.chroma",
    "CODEXIFY_COLLECTION": "codexify_vault_supported",
}
REDIRECTED_CHROMA_ENV = {
    "CODEXIFY_VECTOR_STORE": "inert-alternate-store",
    "CODEXIFY_CHROMA_PATH": "/inert/alternate-chroma",
    "CODEXIFY_COLLECTION": "inert_alternate_collection",
}

SENTINEL_ENV_CONTENT = """\
DEEPSEEK_API_KEY=inert-deepseek-key
GUARDIAN_API_KEY=inert-guardian-key
GUARDIAN_SESSION_SECRET=inert-session-secret
GUARDIAN_JWT_SECRET=inert-jwt-secret
"""


def _render_compose(
    runtime_env_file: str | None = None,
    *,
    compose_files: tuple[Path, ...] = COMPOSE_FILES,
    profiles: tuple[str, ...] = (),
    environment_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    environment: dict[str, str] = {
        # Keep Docker CLI discovery, but exclude ambient application/Compose
        # settings and credentials from this static, inert configuration.
        **{
            key: os.environ[key]
            for key in ("PATH", "HOME", "DOCKER_CONFIG")
            if key in os.environ
        },
        "GUARDIAN_API_KEY": "inert-guardian-key",
        "GUARDIAN_SESSION_SECRET": "inert-session-secret",
        "GUARDIAN_JWT_SECRET": "inert-jwt-secret",
        "CODEXIFY_PREVIEW_APPROVED_EMAILS": "guest@example.com",
        "CODEXIFY_PREVIEW_ADMIN_EMAILS": "admin@example.com",
        "DEEPSEEK_API_KEY": "inert-deepseek-key",
        "LOCAL_CHAT_MODEL": "local-chat",
        "NEO4J_PASS": "inert-neo4j-password",
    }
    environment.update(environment_overrides or {})
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
        # Use the inert file for interpolation as well as service env_file;
        # never implicitly load the operator's project .env during rendering.
        command = [
            "docker",
            "compose",
            "--project-directory",
            str(ROOT),
            "--env-file",
            runtime_env_file,
        ]
        for profile in profiles:
            command.extend(("--profile", profile))
        for compose_file in compose_files:
            command.extend(("-f", str(compose_file)))
        command.extend(("config", "--format", "json"))
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


@pytest.mark.parametrize("redirection_source", ("none", "environment", "env_file"))
def test_private_preview_chroma_topology_resists_redirection(
    redirection_source: str, tmp_path: Path
) -> None:
    runtime_env_file = None
    environment_overrides = None
    if redirection_source == "environment":
        environment_overrides = REDIRECTED_CHROMA_ENV
    elif redirection_source == "env_file":
        env_file = tmp_path / "inert-runtime.env"
        env_file.write_text(
            SENTINEL_ENV_CONTENT
            + "".join(
                f"{key}={value}\n" for key, value in REDIRECTED_CHROMA_ENV.items()
            ),
            encoding="utf-8",
        )
        runtime_env_file = str(env_file)

    config = _render_compose(
        runtime_env_file=runtime_env_file,
        profiles=("cli", "backfill"),
        environment_overrides=environment_overrides,
    )
    assert config["volumes"]["private_preview_chroma"] == {
        "name": "codexify_private_preview_chroma",
        "external": True,
    }
    assert [
        key
        for key, volume in config["volumes"].items()
        if volume["name"] == "codexify_private_preview_chroma"
    ] == ["private_preview_chroma"]
    assert {
        name
        for name, service in config["services"].items()
        if any(
            mount["target"] == "/app/.chroma"
            for mount in service.get("volumes", [])
        )
    } == set(CHROMA_CONSUMERS)

    for service_name in CHROMA_CONSUMERS:
        service = config["services"][service_name]
        mounts = [
            mount for mount in service["volumes"] if mount["target"] == "/app/.chroma"
        ]
        # Exact equality rejects duplicate, host-bind, anonymous, subpath,
        # read-only, or image-seeded alternatives at the canonical target.
        assert mounts == [
            {
                "type": "volume",
                "source": "private_preview_chroma",
                "target": "/app/.chroma",
                "volume": {"nocopy": True},
            }
        ], service_name
        assert {
            key: service["environment"][key] for key in EXPECTED_CHROMA_ENV
        } == EXPECTED_CHROMA_ENV, service_name

    # Prove the redirection inputs really reached Compose, rather than a
    # renderer accidentally dropping them and yielding a false-positive test.
    if redirection_source != "none":
        base = _render_compose(
            runtime_env_file=runtime_env_file,
            compose_files=COMPOSE_FILES[:1],
            environment_overrides=environment_overrides,
        )
        assert {
            key: base["services"]["backend"]["environment"][key]
            for key in EXPECTED_CHROMA_ENV
        } == REDIRECTED_CHROMA_ENV


@pytest.mark.parametrize("profiles", ((), ("cli",), ("backfill",), ("cli", "backfill")))
def test_private_preview_chroma_keeps_optional_profile_activation(
    profiles: tuple[str, ...],
) -> None:
    base = _render_compose(compose_files=COMPOSE_FILES[:1], profiles=profiles)
    preview = _render_compose(profiles=profiles)

    assert set(preview["services"]) == set(base["services"]) | {
        "private-preview-origin"
    }
    for service_name, profile in (
        ("obsidian-ingest", "cli"),
        ("embedding-backfill", "backfill"),
    ):
        assert (service_name in preview["services"]) == (profile in profiles)
        if profile in profiles:
            assert preview["services"][service_name]["profiles"] == [profile]


def test_private_preview_chroma_preserves_other_mounts_and_volumes() -> None:
    base = _render_compose(compose_files=COMPOSE_FILES[:1], profiles=("*",))
    preview = _render_compose(profiles=("*",))

    assert preview["name"] == base["name"]
    assert {
        key: volume
        for key, volume in preview["volumes"].items()
        if key != "private_preview_chroma"
    } == base["volumes"]
    for service_name, service in base["services"].items():
        preview_service = preview["services"][service_name]
        assert preview_service.get("profiles", []) == service.get("profiles", [])
        assert [
            mount
            for mount in preview_service.get("volumes", [])
            if service_name not in CHROMA_CONSUMERS
            or mount["target"] != "/app/.chroma"
        ] == [
            mount
            for mount in service.get("volumes", [])
            if service_name not in CHROMA_CONSUMERS
            or mount["target"] != "/app/.chroma"
        ], service_name


@pytest.mark.parametrize("include_local_override", (False, True))
def test_private_preview_chroma_does_not_change_default_local_topology(
    include_local_override: bool,
) -> None:
    compose_files = COMPOSE_FILES[:1]
    if include_local_override:
        compose_files += (ROOT / "docker-compose.override.yml",)
    config = _render_compose(compose_files=compose_files, profiles=("cli", "backfill"))

    assert "private_preview_chroma" not in config["volumes"]
    assert all(
        volume["name"] != "codexify_private_preview_chroma"
        for volume in config["volumes"].values()
    )
    for service_name in CHROMA_CONSUMERS:
        mounts = [
            mount
            for mount in config["services"][service_name]["volumes"]
            if mount["target"] == "/app/.chroma"
        ]
        if service_name == "worker-chat" and not include_local_override:
            assert mounts == []
        else:
            assert len(mounts) == 1
            assert mounts[0]["type"] == "bind"
            assert mounts[0]["source"] == str(ROOT / ".chroma")


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
