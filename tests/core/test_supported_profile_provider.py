import pytest
from fastapi import HTTPException

from guardian.core import config as config_module
from guardian.core.ai_router import (
    _local_chat_model_is_authoritative,
    _resolve_local_base,
    resolve_local_execution_model,
)
from guardian.core.config import Settings

_WHOOSHD_MODEL = "gemma-4-12b-it-qat-4bit"
# ADR-074 restores the historical tracked Tester default and one-authority
# contract. It is intentionally not a claim about current Whoosh'd inventory.
_HISTORICAL_TRACKED_DEFAULT_MODEL = "qwen3.8-27b-4bit"


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
    settings = Settings(**defaults)
    # LOCAL_RUNTIME_PRESET is supplied by the runtime preset seam but is not
    # a declared Settings field on this branch. Bind it explicitly so this
    # contract test exercises the supported-profile comparison.
    object.__setattr__(
        settings, "LOCAL_RUNTIME_PRESET", defaults["LOCAL_RUNTIME_PRESET"]
    )
    return settings


def test_validate_llm_config_accepts_supported_profile_local_contract(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    settings = _supported_profile_settings()

    config_module.validate_llm_config(settings)


def test_validate_llm_config_accepts_whooshd_deepseek_contract(monkeypatch):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    settings = _supported_profile_settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        LOCAL_BASE_URL="http://host.docker.internal:8000/v1",
        LOCAL_PROVIDER_VENDOR="whooshd",
        LOCAL_CHAT_MODEL=_HISTORICAL_TRACKED_DEFAULT_MODEL,
        LOCAL_LLM_MODEL=_HISTORICAL_TRACKED_DEFAULT_MODEL,
        LLM_MODEL=_HISTORICAL_TRACKED_DEFAULT_MODEL,
        DEEPSEEK_API_KEY="test-deepseek-key",
        DEEPSEEK_CHAT_MODEL="deepseek-v4-flash",
    )

    config_module.validate_llm_config(settings)


def test_validate_llm_config_accepts_tester_operator_selected_local_model(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    monkeypatch.setenv("LOCAL_CHAT_MODEL", _WHOOSHD_MODEL)
    settings = _supported_profile_settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        LOCAL_CHAT_MODEL=_WHOOSHD_MODEL,
        LOCAL_LLM_MODEL=_WHOOSHD_MODEL,
        LLM_MODEL=_WHOOSHD_MODEL,
        DEEPSEEK_API_KEY="test-deepseek-key",
        DEEPSEEK_CHAT_MODEL="deepseek-v4-flash",
    )

    config_module.validate_llm_config(settings)


def test_whooshd_deepseek_profile_keeps_local_model_authoritative(monkeypatch):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    settings = _supported_profile_settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        LOCAL_CHAT_MODEL=_HISTORICAL_TRACKED_DEFAULT_MODEL,
        DEEPSEEK_API_KEY="test-deepseek-key",
        DEEPSEEK_CHAT_MODEL="deepseek-v4-flash",
    )

    assert _local_chat_model_is_authoritative(settings) is True
    resolution = resolve_local_execution_model(
        settings=settings,
        requested_model="stale-local-model",
    )
    assert resolution.ok
    assert resolution.strict is True
    assert resolution.model == _HISTORICAL_TRACKED_DEFAULT_MODEL


def test_supported_profile_keeps_model_inventory_as_runtime_discovery() -> None:
    settings = _supported_profile_settings(
        LOCAL_CHAT_MODEL="runtime-discovered-chat-model",
        LOCAL_LLM_MODEL="runtime-discovered-llm-model",
        LLM_MODEL="runtime-discovered-llm-model",
    )

    config_module.validate_llm_config(settings)


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
        config_module.LLMConfigError, match="blessed local gateway contract"
    ):
        config_module.validate_llm_config(settings, provider_override="local")


def test_resolve_local_base_rejects_supported_profile_runtime_base_drift(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    settings = _supported_profile_settings(
        LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
    )

    with pytest.raises(HTTPException, match="requires LOCAL_BASE_URL"):
        _resolve_local_base(settings)


def test_supported_profile_keeps_deepseek_posture_under_restored_authority(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-whooshd-deepseek-web")
    settings = _supported_profile_settings(
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        LOCAL_CHAT_MODEL=_HISTORICAL_TRACKED_DEFAULT_MODEL,
        DEEPSEEK_API_KEY="test-deepseek-key",
        DEEPSEEK_CHAT_MODEL="deepseek-v4-flash",
    )

    assert _local_chat_model_is_authoritative(settings) is True
    resolution = resolve_local_execution_model(
        settings=settings,
        requested_model="stale-local-model",
    )
    assert resolution.ok
    assert resolution.strict is True
    assert resolution.model == _HISTORICAL_TRACKED_DEFAULT_MODEL


def test_non_strict_alias_fallback_keeps_one_operator_selected_model(monkeypatch):
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    settings = _supported_profile_settings(
        LLM_PROVIDER="local",
        CODEXIFY_LOCAL_ONLY_MODE=False,
        LOCAL_LLM_MODEL=_HISTORICAL_TRACKED_DEFAULT_MODEL,
    )
    object.__setattr__(settings, "LOCAL_CHAT_MODEL", "")
    object.__setattr__(settings, "DEFAULT_LOCAL_MODEL", "")
    object.__setattr__(settings, "LLM_MODEL", "")
    object.__setattr__(settings, "LOCAL_LLM_MODEL", _HISTORICAL_TRACKED_DEFAULT_MODEL)

    assert _local_chat_model_is_authoritative(settings) is False
    resolution = resolve_local_execution_model(settings=settings)
    assert resolution.ok
    assert resolution.model == _HISTORICAL_TRACKED_DEFAULT_MODEL
