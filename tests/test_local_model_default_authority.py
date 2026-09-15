from __future__ import annotations

import re
from pathlib import Path

from guardian.core.ai_router import (
    WHOOSHD_CONFIGURED_MODEL_NOT_ADVERTISED_REASON,
    resolve_local_execution_model,
)
from guardian.core.config import Settings


ROOT = Path(__file__).resolve().parents[1]
LOGICAL_ROUTE = "local-chat"
PHYSICAL_MODEL_DEFAULT = re.compile(
    r"(?im)(?<![A-Z_])"
    r"(?:LOCAL_CHAT_MODEL|LOCAL_LLM_MODEL|DEFAULT_LOCAL_MODEL|LLM_MODEL|"
    r"EXPECTED_MODEL|PRIVATE_PREVIEW_LOCAL_MODEL)"
    r"[^\n]*(?<![A-Za-z])"
    r"(?:qwen|gemma|llama(?:[-.:/]|\d)|mistral|ministral|mlx-community)"
)

RUNTIME_AUTHORITY_SURFACES = (
    ".env.example",
    ".env.template",
    ".env.private-preview.example",
    ".env.tester.example",
    "docker-compose.private-preview.yml",
    "docker-compose.whooshd-smoke.yml",
    "config/supported_profiles/v1-whooshd-deepseek-web.yaml",
    "guardian/config/core.py",
    "guardian/core/config.py",
    "guardian/core/local_runtime_presets.py",
    "scripts/private_preview_validate.sh",
    "scripts/whooshd_deepseek_profile_up.sh",
    "scripts/whooshd_docker_smoke_up.sh",
    "scripts/ops/private_preview_provider_proof.py",
    "scripts/release/export_public_directory.sh",
    "src-tauri/src/commands.rs",
    "Codexify-Beta/.env.example",
    "Codexify-Beta/docker-compose.yml",
)


def test_default_settings_use_provider_owned_local_chat_route(monkeypatch) -> None:
    for key in (
        "LOCAL_CHAT_MODEL",
        "LOCAL_LLM_MODEL",
        "DEFAULT_LOCAL_MODEL",
        "LLM_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None)

    assert settings.LOCAL_CHAT_MODEL == LOGICAL_ROUTE
    assert settings.LOCAL_LLM_MODEL == LOGICAL_ROUTE
    assert settings.DEFAULT_LOCAL_MODEL == LOGICAL_ROUTE
    assert settings.LLM_MODEL == LOGICAL_ROUTE


def test_runtime_authority_surfaces_have_no_physical_local_model_default() -> None:
    violations: list[str] = []
    for relative_path in RUNTIME_AUTHORITY_SURFACES:
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        if match := PHYSICAL_MODEL_DEFAULT.search(content):
            violations.append(f"{relative_path}: {match.group(0).strip()}")

    assert not violations, "\n".join(violations)


def test_logical_route_resolves_but_unavailable_exact_override_fails_closed() -> None:
    common = {
        "_env_file": None,
        "LLM_PROVIDER": "local",
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "ALLOW_CLOUD_PROVIDERS": False,
        "LOCAL_PROVIDER_VENDOR": "whooshd",
    }
    endpoint = {"state": "available", "inventory_source": "whooshd:/v1/models"}

    logical = resolve_local_execution_model(
        settings=Settings(**common, LOCAL_CHAT_MODEL=LOGICAL_ROUTE),
        validate_availability=True,
        discovered_model_names=[LOGICAL_ROUTE],
        endpoint_resolution=endpoint,
    )
    assert logical.ok
    assert logical.model == LOGICAL_ROUTE

    exact = resolve_local_execution_model(
        settings=Settings(**common, LOCAL_CHAT_MODEL="operator-exact-model"),
        validate_availability=True,
        discovered_model_names=[LOGICAL_ROUTE],
        endpoint_resolution=endpoint,
    )
    assert not exact.ok
    assert exact.failure_kind == WHOOSHD_CONFIGURED_MODEL_NOT_ADVERTISED_REASON
