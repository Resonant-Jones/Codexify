from __future__ import annotations

from guardian.core import llm_catalog
from guardian.core.config import Settings
from guardian.core.llm_catalog import build_llm_catalog


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
        "DEEPSEEK_CHAT_MODEL": "deepseek-v4-pro",
        "ALIBABA_API_KEY": None,
        "MINIMAX_API_KEY": None,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _local_provider(payload: dict) -> dict:
    return next(
        provider
        for provider in payload["providers"]
        if provider.get("id") == "local"
    )


def test_whooshd_catalog_surfaces_live_inventory_when_configured_model_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    payload = build_llm_catalog(settings=_settings(), include_all=True)

    local = _local_provider(payload)
    model_ids = [model["id"] for model in local["models"]]
    assert model_ids == [_LLAMA, _QWEN_VL, _QWEN_GGUF]
    assert _GEMMA not in model_ids
    assert local["configured_model"] == _GEMMA
    assert local["configured_model_available"] is False
    assert local["availability_reason"] == _MISMATCH
    assert local["inventory_source"] == "whooshd:/v1/models"
    assert local["advertised_models"] == [_LLAMA, _QWEN_VL, _QWEN_GGUF]
    assert local["enabled"] is False
    assert local["truth"]["selectable"] is False


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

    payload = build_llm_catalog(settings=_settings(), include_all=False)

    assert [provider["id"] for provider in payload["providers"]] == ["local"]
    local = _local_provider(payload)
    assert local["truth"]["cloud_capable_configuration_present"] is False
    assert local["truth"]["egress_allowed"] is True


def test_deepseek_catalog_exposes_static_model_when_cloud_policy_allows(
    monkeypatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_SUPPORTED_PROFILE", raising=False)
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
        "deepseek-v4-pro"
    ]
    assert deepseek["models"][0]["displayName"] == "DeepSeek V4 Pro"
    assert deepseek["truth"]["selectable"] is True
    assert deepseek["truth"]["egress_allowed"] is True


def test_deepseek_catalog_stays_hidden_under_supported_local_only_posture(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    monkeypatch.setattr(llm_catalog.requests, "get", _whooshd_inventory)

    settings = _settings(
        ALLOW_CLOUD_PROVIDERS=False,
        CODEXIFY_LOCAL_ONLY_MODE=True,
        CODEXIFY_EGRESS_ALLOWLIST="",
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
