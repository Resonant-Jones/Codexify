import pytest

from guardian.core.ai_router import _resolve_local_base
from guardian.core.config import LLMConfigError, Settings, validate_llm_config


_WHOOSHD_MODEL = "mlx-community/Llama-3.2-3B-Instruct-4bit"


def _supported_profile_settings(**overrides) -> Settings:
    defaults = {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
        "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
        "LOCAL_BASE_URL": "http://host.docker.internal:8000/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_COMPAT_FIRST": True,
        "LOCAL_PROVIDER_DISPLAY_NAME": "Whoosh'd",
        "LOCAL_PROVIDER_VENDOR": "whooshd",
        "LOCAL_LLM_MODEL": _WHOOSHD_MODEL,
        "LOCAL_CHAT_MODEL": _WHOOSHD_MODEL,
        "LLM_MODEL": _WHOOSHD_MODEL,
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

    with pytest.raises(
        LLMConfigError, match="local provider safety contract"
    ):
        validate_llm_config(settings, provider_override="local")


def test_resolve_local_base_accepts_supported_profile_runtime_preset_drift(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    settings = _supported_profile_settings(
        LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
    )

    assert _resolve_local_base(settings) == "http://127.0.0.1:8000/v1"
