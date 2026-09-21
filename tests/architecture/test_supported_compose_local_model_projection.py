"""Supported Compose contract for the Whoosh'd logical local-model route."""

from __future__ import annotations

from pathlib import Path

import yaml


BASE_COMPOSE_PATH = Path("docker-compose.yml")
SMOKE_OVERLAY_PATH = Path("docker-compose.whooshd-smoke.yml")
SUPPORTED_PROFILE_PATH = Path(
    "config/supported_profiles/v1-local-core-web-mcp.yaml"
)

SUPPORTED_PROFILE = "v1-local-core-web-mcp"
SUPPORTED_LOGICAL_MODEL = "local-chat"
OBSOLETE_PHYSICAL_MODEL = "qwen3.8-27b-4bit"
CHAT_MODEL_KEYS = (
    "LOCAL_CHAT_MODEL",
    "LOCAL_LLM_MODEL",
    "DEFAULT_LOCAL_MODEL",
    "LLM_MODEL",
)
REQUIRED_RUNTIME_SERVICES = (
    "backend",
    "worker-chat",
    "worker-document-embed",
)
CLOUD_API_KEY_FIELDS = (
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "DEEPSEEK_API_KEY",
    "ALIBABA_API_KEY",
    "MINIMAX_API_KEY",
)


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _service_environment(config: dict, service: str) -> dict:
    return config["services"][service]["environment"]


def test_supported_chat_executors_own_the_logical_route() -> None:
    overlay = _load_yaml(SMOKE_OVERLAY_PATH)

    for service in ("backend", "worker-chat"):
        environment = _service_environment(overlay, service)
        for key in CHAT_MODEL_KEYS:
            assert environment[key] == SUPPORTED_LOGICAL_MODEL


def test_required_services_share_the_supported_local_only_posture() -> None:
    overlay = _load_yaml(SMOKE_OVERLAY_PATH)

    for service in REQUIRED_RUNTIME_SERVICES:
        environment = _service_environment(overlay, service)
        assert environment["CODEXIFY_SUPPORTED_PROFILE"] == SUPPORTED_PROFILE
        assert environment["LLM_PROVIDER"] == "local"
        assert environment["CODEXIFY_LOCAL_ONLY_MODE"] == "true"
        assert environment["ALLOW_CLOUD_PROVIDERS"] == "false"
        assert environment["CODEXIFY_EGRESS_ALLOWLIST"] == ""
        for key in CLOUD_API_KEY_FIELDS:
            assert environment[key] == ""

    document_environment = _service_environment(
        overlay, "worker-document-embed"
    )
    assert "deepseek" not in document_environment["CODEXIFY_EGRESS_ALLOWLIST"]


def test_supported_projection_contains_no_physical_model_authority() -> None:
    overlay = _load_yaml(SMOKE_OVERLAY_PATH)
    profile = _load_yaml(SUPPORTED_PROFILE_PATH)

    for service in REQUIRED_RUNTIME_SERVICES:
        environment = _service_environment(overlay, service)
        assert OBSOLETE_PHYSICAL_MODEL not in yaml.safe_dump(environment)

    provider_contract = profile["provider_contract"]
    assert not set(CHAT_MODEL_KEYS).intersection(provider_contract)
    assert OBSOLETE_PHYSICAL_MODEL not in yaml.safe_dump(provider_contract)


def test_base_compose_keeps_explicit_exact_model_transport() -> None:
    base = _load_yaml(BASE_COMPOSE_PATH)

    for service in ("backend", "worker-chat"):
        environment = _service_environment(base, service)
        assert environment["LOCAL_CHAT_MODEL"] == "${LOCAL_CHAT_MODEL}"
