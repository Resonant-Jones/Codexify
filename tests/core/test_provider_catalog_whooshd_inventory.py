from __future__ import annotations

import requests
import pytest

from guardian.core import llm_catalog
from guardian.core.config import Settings
from guardian.core.llm_catalog import build_llm_catalog
from guardian.core.provider_registry import (
    resolve_local_runtime_identity,
    validate_provider_model_selection,
)

_GEMMA = "mlx-community/gemma-4-e2b-it-4bit"
_LLAMA = "llama-3.2-3b-mlx"
_QWEN_VL = "qwen2-vl-2b-mlx"
_QWEN_GGUF = "qwen2.5-0.5b-gguf"
_MISMATCH = "configured_model_not_advertised_by_whooshd"


class _Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _whooshd_inventory(url: str, *args, **kwargs) -> _Response:
    _ = (args, kwargs)
    if url == "http://host.docker.internal:8000/api/tags":
        return _Response({"models": []}, status_code=404)
    if url == "http://host.docker.internal:8000/v1/models":
        return _Response(
            {
                "data": [
                    {"id": _LLAMA},
                    {"id": _QWEN_VL},
                    {"id": _QWEN_GGUF},
                ]
            }
        )
    return _Response({}, status_code=404)


def _deepseek_model_index(url: str, *args, **kwargs) -> _Response:
    _ = args
    assert url == "https://api.deepseek.com/v1/models"
    assert (kwargs.get("headers") or {}).get("Authorization") == (
        "Bearer test-deepseek-key"
    )
    assert kwargs.get("timeout") == 3.0
    return _Response(
        {
            "object": "list",
            "data": [
                {"id": "deepseek-flash", "owned_by": "deepseek"},
                {"id": "deepseek-v4-pro", "owned_by": "deepseek"},
                {"id": "deepseek-chat", "owned_by": "deepseek"},
            ],
        }
    )


def _deepseek_model_index_timeout(url: str, *args, **kwargs) -> _Response:
    _ = (url, args, kwargs)
    raise requests.exceptions.Timeout("timed out")


def _settings(**overrides) -> Settings:
    defaults = {
        "LLM_PROVIDER": "local",
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
        "LOCAL_RUNTIME_PRESET": "whooshd-mlx",
        "LOCAL_BASE_URL": "http://host.docker.internal:8000/v1",
        "LOCAL_API_KEY": "local",
        "LOCAL_PROVIDER_DISPLAY_NAME": "Whoosh'd",
        "LOCAL_PROVIDER_VENDOR": "whooshd",
        "LOCAL_LLM_MODEL": _LLAMA,
        "LOCAL_CHAT_MODEL": _GEMMA,
        "DEFAULT_LOCAL_MODEL": _LLAMA,
        "LLM_MODEL": _LLAMA,
        "OPENAI_API_KEY": None,
        "GROQ_API_KEY": None,
        "DEEPSEEK_API_KEY": None,
        "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        "DEEPSEEK_CHAT_MODEL": "deepseek-v4-flash",
        "ALIBABA_API_KEY": None,
        "MINIMAX_API_KEY": None,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _local_provider(payload: dict) -> dict:
    return next(
        provider
        for provider in payload["providers"]
        if provider.get("id") == "local"
    )


@pytest.mark.parametrize(
    ("configured_identity", "expected_id", "expected_display_name"),
    [
        ("whooshd-mlx", "whooshd", "Whoosh'd"),
        ("ollama", "ollama", "Ollama"),
        ("lmstudio", "lm_studio", "LM Studio"),
        ("lm_studio", "lm_studio", "LM Studio"),
    ],
)
def test_local_runtime_identity_normalizes_known_configured_values(
    configured_identity: str,
    expected_id: str,
    expected_display_name: str,
) -> None:
    runtime = resolve_local_runtime_identity(vendor=configured_identity)

    assert runtime["id"] == expected_id
    assert runtime["displayName"] == expected_display_name
    assert runtime["identitySource"] == "vendor"
    assert runtime["recognized"] is True


def test_unknown_local_runtime_identity_stays_generic() -> None:
    runtime = resolve_local_runtime_identity(
        vendor="acme-runtime",
        runtime_preset="whooshd-mlx",
    )

    assert runtime == {
        "id": "custom",
        "displayName": "Custom Local",
        "identitySource": "vendor",
        "recognized": False,
        "vendor": "acme-runtime",
        "runtimePreset": "whooshd-mlx",
    }


def test_whooshd_catalog_surfaces_live_inventory_when_configured_model_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    payload = build_llm_catalog(settings=_settings(), include_all=True)

    local = _local_provider(payload)
    model_ids = [model["id"] for model in local["models"]]
    assert local["id"] == "local"
    assert local["displayName"] == "Whoosh'd"
    assert local["runtime"] == {
        "id": "whooshd",
        "displayName": "Whoosh'd",
        "identitySource": "vendor",
        "recognized": True,
        "vendor": "whooshd",
        "runtimePreset": "whooshd-mlx",
    }
    assert local["source"]["label"] == "host.docker.internal:8000"
    assert model_ids == [_LLAMA, _QWEN_VL, _QWEN_GGUF]
    assert _GEMMA not in model_ids
    assert local["configured_model"] == _GEMMA
    assert local["configured_model_available"] is False
    assert local["availability_reason"] == _MISMATCH
    assert local["inventory_source"] == "whooshd:/v1/models"
    assert local["advertised_models"] == [_LLAMA, _QWEN_VL, _QWEN_GGUF]
    assert local["enabled"] is False
    assert local["truth"]["selectable"] is False


def test_local_runtime_display_override_remains_authoritative(monkeypatch) -> None:
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    payload = build_llm_catalog(
        settings=_settings(LOCAL_PROVIDER_DISPLAY_NAME="Jones Runtime"),
        include_all=True,
    )

    local = _local_provider(payload)
    assert local["id"] == "local"
    assert local["displayName"] == "Jones Runtime"
    assert local["runtime"]["id"] == "whooshd"
    assert local["runtime"]["displayName"] == "Jones Runtime"


def test_known_runtime_vendor_supplies_display_without_override(monkeypatch) -> None:
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    payload = build_llm_catalog(
        settings=_settings(LOCAL_PROVIDER_DISPLAY_NAME=None),
        include_all=True,
    )

    local = _local_provider(payload)
    assert local["id"] == "local"
    assert local["displayName"] == "Whoosh'd"
    assert local["runtime"]["displayName"] == "Whoosh'd"


def test_unknown_runtime_is_not_inferred_from_endpoint_or_models(monkeypatch) -> None:
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    payload = build_llm_catalog(
        settings=_settings(
            LOCAL_PROVIDER_DISPLAY_NAME=None,
            LOCAL_PROVIDER_VENDOR="acme-runtime",
        ),
        include_all=True,
    )

    local = _local_provider(payload)
    assert local["id"] == "local"
    assert local["displayName"] == "Custom Local"
    assert local["runtime"]["id"] == "custom"
    assert local["runtime"]["recognized"] is False
    assert local["source"]["label"] == "host.docker.internal:8000"
    assert [model["id"] for model in local["models"]] == [
        _LLAMA,
        _QWEN_VL,
        _QWEN_GGUF,
    ]


def test_local_chat_model_wins_over_legacy_local_model_env(monkeypatch) -> None:
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    payload = build_llm_catalog(
        settings=_settings(LOCAL_LLM_MODEL=_LLAMA, LLM_MODEL=_LLAMA),
        include_all=True,
    )

    local = _local_provider(payload)
    assert local["default_model"] == _GEMMA
    assert local["model_resolution"]["source"] == "LOCAL_CHAT_MODEL"
    assert local["model_resolution"]["failure_kind"] == _MISMATCH


def test_local_only_whooshd_mismatch_does_not_enable_cloud_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    payload = build_llm_catalog(settings=_settings(), include_all=True)

    local = _local_provider(payload)
    assert local["enabled"] is False
    assert not any(
        provider["enabled"]
        for provider in payload["providers"]
        if provider["id"] != "local"
    )
    assert local["truth"]["cloud_capable_configuration_present"] is False
    assert local["truth"]["egress_allowed"] is True


def test_deepseek_catalog_discovers_full_model_roster_when_cloud_policy_allows(
    monkeypatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get", _deepseek_model_index
    )
    settings = _settings(
        LLM_PROVIDER="deepseek",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        DEEPSEEK_API_KEY="test-deepseek-key",
    )

    payload = build_llm_catalog(settings=settings, include_all=False)
    deepseek = next(
        provider
        for provider in payload["providers"]
        if provider["id"] == "deepseek"
    )

    assert deepseek["enabled"] is True
    assert deepseek["available"] is True
    assert deepseek["authorized"] is True
    assert [model["id"] for model in deepseek["models"]] == [
        "deepseek-flash",
        "deepseek-v4-pro",
        "deepseek-chat",
    ]
    assert deepseek["model_index"] == {
        "source": "live",
        "state": "available",
        "endpoint": "https://api.deepseek.com/v1/models",
        "model_count": 3,
        "utility_model_count": 0,
        "total_model_count": 3,
    }
    assert deepseek["truth"]["selectable"] is True
    assert deepseek["truth"]["egress_allowed"] is True


def test_deepseek_catalog_rejects_model_outside_live_roster(monkeypatch) -> None:
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get", _deepseek_model_index
    )
    settings = _settings(
        LLM_PROVIDER="deepseek",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        DEEPSEEK_API_KEY="test-deepseek-key",
    )

    allowed, reason = validate_provider_model_selection(
        provider_id="deepseek",
        model_id="deepseek-v4-unknown",
        settings=settings,
    )

    assert allowed is False
    assert reason == (
        "Requested model 'deepseek-v4-unknown' is not available for provider 'deepseek'"
    )


def test_deepseek_catalog_accepts_every_provider_advertised_model(monkeypatch) -> None:
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get", _deepseek_model_index
    )
    settings = _settings(
        LLM_PROVIDER="deepseek",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        DEEPSEEK_API_KEY="test-deepseek-key",
    )

    allowed, reason = validate_provider_model_selection(
        provider_id="deepseek",
        model_id="deepseek-chat",
        settings=settings,
    )

    assert reason is None
    assert allowed is True


def test_deepseek_catalog_keeps_configured_default_on_discovery_failure(
    monkeypatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _deepseek_model_index_timeout,
    )
    settings = _settings(
        LLM_PROVIDER="deepseek",
        ALLOW_CLOUD_PROVIDERS=True,
        CODEXIFY_LOCAL_ONLY_MODE=False,
        CODEXIFY_EGRESS_ALLOWLIST="deepseek",
        DEEPSEEK_API_KEY="test-deepseek-key",
    )

    payload = build_llm_catalog(settings=settings, include_all=False)
    deepseek = next(
        provider
        for provider in payload["providers"]
        if provider["id"] == "deepseek"
    )

    assert deepseek["enabled"] is True
    assert deepseek["models"][0]["id"] == "deepseek-v4-flash"
    assert deepseek["model_index"]["source"] == "fallback"
    assert deepseek["model_index"]["state"] == "degraded"


def test_deepseek_catalog_stays_hidden_under_supported_local_only_posture(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    settings = _settings(
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_LOCAL_ONLY_MODE=True,
        CODEXIFY_EGRESS_ALLOWLIST="",
        LOCAL_COMPAT_FIRST=True,
        LOCAL_CHAT_MODEL=_LLAMA,
        DEEPSEEK_API_KEY="test-deepseek-key",
    )

    payload = build_llm_catalog(settings=settings, include_all=False)
    provider_ids = [provider["id"] for provider in payload["providers"]]
    assert provider_ids == ["local"]

    payload_all = build_llm_catalog(settings=settings, include_all=True)
    deepseek = next(
        provider
        for provider in payload_all["providers"]
        if provider["id"] == "deepseek"
    )

    assert deepseek["enabled"] is False
    assert deepseek["available"] is False
    assert deepseek["disabled_reason"] == "Cloud providers disabled by config"
    assert deepseek["truth"]["supported_profile_approved"] is False
