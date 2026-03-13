import pytest
from fastapi import HTTPException

from guardian.core.ai_router import _resolve_local_base
from guardian.core.config import LLMConfigError, Settings, validate_llm_config


def _supported_profile_settings(**overrides) -> Settings:
    defaults = {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
        "LOCAL_BASE_URL": "http://host.docker.internal:11434/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_LLM_MODEL": "library2/ministral-3:8b",
        "LOCAL_CHAT_MODEL": "library2/ministral-3:8b",
        "LLM_MODEL": "library2/ministral-3:8b",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_validate_llm_config_accepts_supported_profile_local_contract(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    settings = _supported_profile_settings()

    validate_llm_config(settings)


def test_validate_llm_config_rejects_supported_profile_provider_drift(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    settings = _supported_profile_settings(
        LLM_PROVIDER="groq",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="groq",
    )

    with pytest.raises(LLMConfigError, match="blessed local gateway contract"):
        validate_llm_config(settings, provider_override="local")


def test_resolve_local_base_rejects_supported_profile_gateway_drift(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    settings = _supported_profile_settings(
        LOCAL_BASE_URL="http://127.0.0.1:11434/v1"
    )

    with pytest.raises(HTTPException) as exc:
        _resolve_local_base(settings)

    assert exc.value.status_code == 400
    assert "host.docker.internal:11434/v1" in str(exc.value.detail)
