from __future__ import annotations

import re
from pathlib import Path

from guardian.core.ai_router import (
    LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND,
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


def test_explicit_request_model_is_exact_independently_of_configured_default() -> None:
    settings = Settings(
        _env_file=None,
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=True,
        ALLOW_CLOUD_PROVIDERS=False,
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_CHAT_MODEL=LOGICAL_ROUTE,
    )
    endpoint = {"state": "available", "inventory_source": "synthetic:/v1/models"}
    rejected = resolve_local_execution_model(
        settings=settings,
        requested_model="missing-local-model-A7K9",
        requested_model_is_authoritative=True,
        discovered_model_names=[LOGICAL_ROUTE],
        endpoint_resolution=endpoint,
    )
    assert not rejected.ok
    assert rejected.model == "missing-local-model-A7K9"
    assert rejected.failure_kind == LOCAL_MODEL_UNAVAILABLE_FAILURE_KIND
    assert rejected.source == "requested_model"

    advertised = resolve_local_execution_model(
        settings=settings,
        requested_model="exact-test-model",
        requested_model_is_authoritative=True,
        discovered_model_names=[LOGICAL_ROUTE, "exact-test-model"],
        endpoint_resolution=endpoint,
    )
    assert advertised.ok
    assert advertised.model == "exact-test-model"
    assert advertised.source == "requested_model"

    default = resolve_local_execution_model(
        settings=settings,
        requested_model="missing-local-model-A7K9",
        discovered_model_names=[LOGICAL_ROUTE],
        endpoint_resolution=endpoint,
    )
    assert default.ok
    assert default.model == LOGICAL_ROUTE
    assert default.source == "LOCAL_CHAT_MODEL"
