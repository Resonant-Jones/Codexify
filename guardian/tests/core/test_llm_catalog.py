from __future__ import annotations

import json

from guardian.core.config import Settings
from guardian.core.llm_catalog import build_llm_catalog


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
        "OPENAI_API_KEY": None,
        "OPENAI_BASE_URL": None,
        "GROQ_API_KEY": None,
        "GROQ_BASE_URL": None,
        "ANTHROPIC_API_KEY": None,
        "GEMINI_API_KEY": None,
        "GENAI_API_KEY": None,
        "GOOGLE_API_KEY": None,
        "ALIBABA_API_KEY": None,
        "ALIBABA_API_BASE": None,
        "MINIMAX_API_KEY": None,
        "MINIMAX_API_BASE": None,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _supported_profile_settings_with_default_cloud_bases(
    **overrides,
) -> Settings:
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
        "OPENAI_API_KEY": None,
        "OPENAI_BASE_URL": None,
        "GROQ_API_KEY": None,
        "GROQ_BASE_URL": None,
        "ANTHROPIC_API_KEY": None,
        "GEMINI_API_KEY": None,
        "GENAI_API_KEY": None,
        "GOOGLE_API_KEY": None,
        "ALIBABA_API_KEY": None,
        "MINIMAX_API_KEY": None,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def _mock_local_catalog_request(url: str, *args, **kwargs):
    _ = (args, kwargs)
    if url.endswith("/api/tags"):
        return type(
            "Resp",
            (),
            {
                "status_code": 200,
                "json": lambda self=None: {
                    "models": [
                        {"name": "qwen3.5:0.8b"},
                        {"name": "library2/ministral-3:8b"},
                    ]
                },
            },
        )()
    return type(
        "Resp",
        (),
        {
            "status_code": 404,
            "json": lambda self=None: {"data": []},
        },
    )()


def _provider_by_id(payload: dict, provider_id: str) -> dict:
    return next(
        provider
        for provider in payload["providers"]
        if provider.get("id") == provider_id
    )


def test_default_catalog_under_supported_profile_only_shows_local_provider(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    for env_key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "GROQ_API_KEY",
        "GROQ_BASE_URL",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ALIBABA_API_KEY",
        "ALIBABA_API_BASE",
        "MINIMAX_API_KEY",
        "MINIMAX_API_BASE",
    ):
        monkeypatch.delenv(env_key, raising=False)
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = _supported_profile_settings(
        GROQ_API_KEY="test-groq-key",
        GROQ_BASE_URL="https://api.groq.com/openai/v1",
    )

    payload = build_llm_catalog(settings=settings)
    provider_ids = [provider["id"] for provider in payload["providers"]]

    assert provider_ids == ["local"]
    local = _provider_by_id(payload, "local")
    assert local["truth"]["supported_profile_name"] == "v1-local-core-web-mcp"
    assert local["truth"]["supported_profile_approved"] is True
    assert local["truth"]["discovered_inventory"] is True
    assert local["truth"]["executable"] is True
    assert local["truth"]["cloud_capable_configuration_present"] is True

    payload_text = json.dumps(payload, sort_keys=True)
    assert "test-groq-key" not in payload_text
    assert "api_key" not in payload_text.lower()


def test_include_all_catalog_exposes_unsupported_cloud_provider_context(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    for env_key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "GROQ_API_KEY",
        "GROQ_BASE_URL",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ALIBABA_API_KEY",
        "ALIBABA_API_BASE",
        "MINIMAX_API_KEY",
        "MINIMAX_API_BASE",
    ):
        monkeypatch.delenv(env_key, raising=False)
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = _supported_profile_settings(
        GROQ_API_KEY="test-groq-key",
        GROQ_BASE_URL="https://api.groq.com/openai/v1",
    )

    payload = build_llm_catalog(settings=settings, include_all=True)
    groq = _provider_by_id(payload, "groq")

    assert groq["authorized"] is True
    assert groq["available"] is False
    assert groq["enabled"] is False
    assert groq["disabled_reason"] == "Cloud providers disabled by config"
    assert groq["truth"]["supported_profile_name"] == "v1-local-core-web-mcp"
    assert groq["truth"]["supported_profile_approved"] is False
    assert groq["truth"]["discovered_inventory"] is False
    assert groq["truth"]["egress_allowed"] is False
    assert groq["truth"]["cloud_capable_configuration_present"] is True

    payload_text = json.dumps(payload, sort_keys=True)
    assert "test-groq-key" not in payload_text
    assert "api_key" not in payload_text.lower()


def test_default_cloud_base_defaults_do_not_make_catalog_cloud_capable(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "v1-local-core-web-mcp")
    for env_key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "GROQ_API_KEY",
        "GROQ_BASE_URL",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GENAI_API_KEY",
        "GOOGLE_API_KEY",
        "ALIBABA_API_KEY",
        "MINIMAX_API_KEY",
    ):
        monkeypatch.delenv(env_key, raising=False)
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = _supported_profile_settings_with_default_cloud_bases()

    payload = build_llm_catalog(settings=settings)
    local = _provider_by_id(payload, "local")

    assert settings.ALIBABA_API_BASE or settings.MINIMAX_API_BASE
    assert local["truth"]["cloud_capable_configuration_present"] is False
    assert local["truth"]["supported_profile_approved"] is True
