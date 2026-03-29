from __future__ import annotations

import requests
from fastapi.testclient import TestClient

from guardian.core.config import get_settings
from guardian.guardian_api import app


class _MockResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


def _mock_local_catalog_request(url: str, *args, **kwargs) -> _MockResponse:
    if url.endswith("/api/tags"):
        return _MockResponse(
            {
                "models": [
                    {"name": "llama3.1:8b"},
                    {"name": "qwen2.5:7b"},
                ]
            }
        )
    return _MockResponse({"data": []}, status_code=404)


def _mock_alibaba_model_index(url: str, *args, **kwargs) -> _MockResponse:
    assert url == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/models"
    return _MockResponse({"data": [{"id": "qwen-plus"}]})


def _mock_alibaba_model_index_timeout(
    url: str, *args, **kwargs
) -> _MockResponse:
    _ = (args, kwargs)
    assert url == "https://dashscope-us.aliyuncs.com/compatible-mode/v1/models"
    raise requests.exceptions.Timeout("timed out")


def _mock_minimax_model_index_transport_error(
    url: str, *args, **kwargs
) -> _MockResponse:
    _ = (args, kwargs)
    assert url == "https://api.minimax.chat/v1/models"
    raise requests.exceptions.ConnectionError("connection refused")


def _mock_minimax_model_index_empty(url: str, *args, **kwargs) -> _MockResponse:
    _ = (args, kwargs)
    assert url == "https://api.minimax.chat/v1/models"
    return _MockResponse(
        {"data": [{"id": "text-embedding-3-small", "type": "embedding"}]}
    )


def _mock_groq_model_index(url: str, *args, **kwargs) -> _MockResponse:
    assert url == "https://api.groq.com/openai/v1/models"
    headers = kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer test-groq-key"
    return _MockResponse(
        {
            "data": [
                {
                    "id": "llama-3.3-70b-versatile",
                    "name": "Llama 3.3 70B",
                    "type": "chat",
                },
                {
                    "id": "moonshotai/kimi-k2-instruct-0905",
                    "name": "Kimi K2 Instruct",
                    "type": "chat",
                },
                {
                    "id": "llama-3.3-70b-versatile",
                    "name": "Llama 3.3 70B Duplicate",
                    "type": "chat",
                },
                {
                    "id": "text-embedding-3-small",
                    "name": "Embeddings",
                    "type": "embedding",
                },
            ]
        }
    )


def _mock_groq_model_index_classifier_miss(
    url: str, *args, **kwargs
) -> _MockResponse:
    assert url == "https://api.groq.com/openai/v1/models"
    headers = kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer test-groq-key"
    return _MockResponse(
        {
            "data": [
                {
                    "id": "llama-3.3-70b-versatile",
                    "name": "Llama 3.3 70B",
                    "supports_chat": False,
                },
                {
                    "id": "moonshotai/kimi-k2-instruct-0905",
                    "name": "Kimi K2 Instruct",
                    "supportsChat": False,
                },
            ]
        }
    )


def _mock_bridge_fallback_catalog_request(calls: list[str]):
    def _handler(url: str, *args, **kwargs) -> _MockResponse:
        _ = (args, kwargs)
        calls.append(url)
        if "127.0.0.1:11434" in url:
            raise requests.exceptions.ConnectionError("connection refused")
        if url.endswith("/api/tags") and "host.docker.internal:11434" in url:
            return _MockResponse({"models": [{"name": "llama3.2:3b"}]})
        return _MockResponse({"data": []}, status_code=404)

    return _handler


def _mock_supported_local_catalog_request(
    url: str, *args, **kwargs
) -> _MockResponse:
    _ = (args, kwargs)
    if url.endswith("/api/tags"):
        return _MockResponse(
            {
                "models": [
                    {"name": "qwen3.5:0.8b"},
                    {"name": "qwen2.5:7b"},
                ]
            }
        )
    return _MockResponse({"data": []}, status_code=404)


def _provider_by_id(payload: dict, provider_id: str) -> dict:
    return next(
        provider
        for provider in payload["providers"]
        if provider.get("id") == provider_id
    )


def _clear_extra_cloud_keys(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GENAI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("ALIBABA_API_KEY", raising=False)
    monkeypatch.delenv("ALIBABA_API_BASE", raising=False)
    monkeypatch.delenv("ALIBABA_MODEL", raising=False)
    monkeypatch.delenv("MINIMAX_API_FLAVOR", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_BASE", raising=False)
    monkeypatch.delenv("MINIMAX_MODEL", raising=False)


def test_llm_catalog_hides_unauthorized_providers_by_default(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai,anthropic,gemini,groq"
        settings.OPENAI_API_KEY = None
        settings.GROQ_API_KEY = None
        settings.ALIBABA_API_KEY = None
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        response = client.get("/api/llm/catalog")
        assert response.status_code == 200
        payload = response.json()
        assert [provider["id"] for provider in payload["providers"]] == [
            "local"
        ]
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_uses_host_bridge_fallback_when_loopback_unreachable(
    monkeypatch,
):
    calls: list[str] = []
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_bridge_fallback_catalog_request(calls),
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "LOCAL_BASE_URL": settings.LOCAL_BASE_URL,
        "LOCAL_DOCKER_FALLBACK_BASE_URL": settings.LOCAL_DOCKER_FALLBACK_BASE_URL,
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
    }
    try:
        settings.LOCAL_BASE_URL = "http://127.0.0.1:11434"
        settings.LOCAL_DOCKER_FALLBACK_BASE_URL = (
            "http://host.docker.internal:11434"
        )
        settings.ALLOW_CLOUD_PROVIDERS = False
        settings.CODEXIFY_LOCAL_ONLY_MODE = True
        settings.CODEXIFY_EGRESS_ALLOWLIST = ""

        client = TestClient(app)
        response = client.get("/api/llm/catalog")
        assert response.status_code == 200
        payload = response.json()

        local = _provider_by_id(payload, "local")
        assert [model["id"] for model in local["models"]] == ["llama3.2:3b"]
        assert local["models"][0]["source"] == "host.docker.internal:11434"
        assert any("127.0.0.1:11434" in url for url in calls)
        assert any("host.docker.internal:11434" in url for url in calls)
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_local_only_exposes_effective_local_chat_model(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_supported_local_catalog_request,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "LOCAL_BASE_URL": settings.LOCAL_BASE_URL,
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "LOCAL_LLM_MODEL": settings.LOCAL_LLM_MODEL,
        "LOCAL_CHAT_MODEL": settings.LOCAL_CHAT_MODEL,
        "DEFAULT_LOCAL_MODEL": settings.DEFAULT_LOCAL_MODEL,
        "LLM_MODEL": settings.LLM_MODEL,
    }
    try:
        settings.LOCAL_BASE_URL = "http://host.docker.internal:11434/v1"
        settings.ALLOW_CLOUD_PROVIDERS = False
        settings.CODEXIFY_LOCAL_ONLY_MODE = True
        settings.CODEXIFY_EGRESS_ALLOWLIST = ""
        settings.LOCAL_LLM_MODEL = "library2/ministral-3:8b"
        settings.LOCAL_CHAT_MODEL = "qwen3.5:0.8b"
        settings.DEFAULT_LOCAL_MODEL = "library2/ministral-3:8b"
        settings.LLM_MODEL = "library2/ministral-3:8b"

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()

        local = _provider_by_id(payload, "local")
        assert local["default_model"] == "qwen3.5:0.8b"
        assert local["model_resolution"]["source"] == "LOCAL_CHAT_MODEL"
        assert local["enabled"] is True
        assert local["truth"]["selectable"] is True
        assert local["models"][0]["id"] == "qwen3.5:0.8b"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_provider_appears_when_key_exists(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai"
        settings.OPENAI_API_KEY = "test-openai-key"
        settings.ALIBABA_API_KEY = None
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        openai = _provider_by_id(payload, "openai")
        assert openai["enabled"] is True
        assert openai["available"] is True
        assert openai["authorized"] is True
        assert openai["models"][0]["supports_chat"] is True
        assert openai["models"][0]["supports_vision"] is True
        assert openai["models"][0]["supports_text_input"] is True
        assert openai["models"][0]["model_kind"] == "vision_chat"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_alibaba_provider_appears_when_configured(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _mock_alibaba_model_index,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "alibaba"
        settings.ALIBABA_API_KEY = "test-alibaba-key"
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = "qwen-plus"
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        alibaba = _provider_by_id(payload, "alibaba")
        assert alibaba["enabled"] is True
        assert alibaba["available"] is True
        assert alibaba["authorized"] is True
        assert alibaba["models"][0]["id"] == "qwen-plus"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_groq_discovery_surfaces_multiple_models(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _mock_groq_model_index,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "GROQ_BASE_URL": settings.GROQ_BASE_URL,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
        settings.OPENAI_API_KEY = None
        settings.GROQ_API_KEY = "test-groq-key"
        settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
        settings.ALIBABA_API_KEY = None
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        groq = _provider_by_id(payload, "groq")
        assert groq["enabled"] is True
        assert groq["available"] is True
        assert groq["authorized"] is True
        assert groq["model_index"]["state"] == "available"
        assert groq["model_index"]["model_count"] == 2
        assert groq["model_index"]["utility_model_count"] == 1
        assert groq["model_index"]["total_model_count"] == 3
        assert [model["id"] for model in groq["models"]] == [
            "llama-3.3-70b-versatile",
            "moonshotai/kimi-k2-instruct-0905",
        ]
        assert [model["displayName"] for model in groq["models"]] == [
            "Llama 3.3 70B",
            "Kimi K2 Instruct",
        ]
        assert groq["models"][0]["_capability"] == "confirmed"
        assert groq["models"][0]["supports_chat"] is True
        assert groq["models"][0]["supports_vision"] is False
        assert groq["models"][0]["supports_text_input"] is True
        assert groq["models"][0]["model_kind"] == "chat"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_soft_fallback_surfaces_inferred_groq_models(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _mock_groq_model_index_classifier_miss,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "GROQ_BASE_URL": settings.GROQ_BASE_URL,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
        settings.OPENAI_API_KEY = None
        settings.GROQ_API_KEY = "test-groq-key"
        settings.GROQ_BASE_URL = "https://api.groq.com/openai/v1"
        settings.ALIBABA_API_KEY = None
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        groq = _provider_by_id(payload, "groq")

        assert groq["enabled"] is True
        assert groq["available"] is True
        assert groq["authorized"] is True
        assert groq["model_index"]["state"] == "degraded"
        assert groq["model_index"]["failure_kind"] == "empty_model_result"
        assert groq["model_index"]["model_count"] == 2
        assert [model["id"] for model in groq["models"]] == [
            "llama-3.3-70b-versatile",
            "moonshotai/kimi-k2-instruct-0905",
        ]
        assert all(
            model["_capability"] == "inferred" for model in groq["models"]
        )
        assert all(model["supports_chat"] is True for model in groq["models"])
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_disabled_cloud_provider_has_reason(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = False
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai"
        settings.OPENAI_API_KEY = "test-openai-key"
        settings.ALIBABA_API_KEY = None
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        openai = _provider_by_id(payload, "openai")
        assert openai["enabled"] is False
        assert openai["available"] is False
        assert openai["disabled_reason"] == "Cloud providers disabled by config"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_alibaba_discovery_timeout_reports_failure_kind(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _mock_alibaba_model_index_timeout,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "alibaba"
        settings.ALIBABA_API_KEY = "test-alibaba-key"
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        alibaba = _provider_by_id(payload, "alibaba")
        assert alibaba["available"] is False
        assert alibaba["enabled"] is False
        assert alibaba["model_index"]["state"] == "degraded"
        assert alibaba["model_index"]["failure_kind"] == "provider_timeout"
        assert (
            alibaba["disabled_reason"]
            == "Provider model index request timed out"
        )
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_minimax_discovery_transport_failure_reports_failure_kind(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _mock_minimax_model_index_transport_error,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
        "MINIMAX_API_FLAVOR": settings.MINIMAX_API_FLAVOR,
        "MINIMAX_MODEL": settings.MINIMAX_MODEL,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "minimax"
        settings.MINIMAX_API_KEY = "test-minimax-key"
        settings.MINIMAX_API_BASE = "https://api.minimax.chat/v1"
        settings.MINIMAX_API_FLAVOR = "openai"
        settings.MINIMAX_MODEL = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        minimax = _provider_by_id(payload, "minimax")
        assert minimax["available"] is True
        assert minimax["enabled"] is True
        assert minimax["models"]
        assert minimax["models"][0]["id"] == "MiniMax-M2.7"
        assert minimax["model_index"]["state"] == "degraded"
        assert minimax["model_index"]["source"] == "fallback"
        assert minimax["model_index"]["failure_kind"] == "transport_error"
        assert minimax.get("disabled_reason") is None
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_minimax_empty_catalog_reports_failure_kind(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    monkeypatch.setattr(
        "guardian.core.provider_registry.requests.get",
        _mock_minimax_model_index_empty,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
        "MINIMAX_API_FLAVOR": settings.MINIMAX_API_FLAVOR,
        "MINIMAX_MODEL": settings.MINIMAX_MODEL,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "minimax"
        settings.MINIMAX_API_KEY = "test-minimax-key"
        settings.MINIMAX_API_BASE = "https://api.minimax.chat/v1"
        settings.MINIMAX_API_FLAVOR = "openai"
        settings.MINIMAX_MODEL = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog").json()
        minimax = _provider_by_id(payload, "minimax")
        assert minimax["available"] is True
        assert minimax["enabled"] is True
        assert minimax["models"]
        assert minimax["models"][0]["id"] == "MiniMax-M2.7"
        assert minimax["model_index"]["state"] == "degraded"
        assert minimax["model_index"]["failure_kind"] == "empty_model_result"
        assert minimax["model_index"]["source"] == "fallback"
        assert minimax.get("disabled_reason") is None
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_include_all_shows_unauthorized_providers(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )
    _clear_extra_cloud_keys(monkeypatch)

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "ALIBABA_API_KEY": settings.ALIBABA_API_KEY,
        "ALIBABA_API_BASE": settings.ALIBABA_API_BASE,
        "ALIBABA_MODEL": settings.ALIBABA_MODEL,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai,anthropic,gemini,groq"
        settings.OPENAI_API_KEY = None
        settings.GROQ_API_KEY = None
        settings.ALIBABA_API_KEY = None
        settings.ALIBABA_API_BASE = (
            "https://dashscope-us.aliyuncs.com/compatible-mode/v1"
        )
        settings.ALIBABA_MODEL = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        payload = client.get("/api/llm/catalog?include=all").json()
        provider_ids = {provider["id"] for provider in payload["providers"]}
        assert {
            "local",
            "openai",
            "anthropic",
            "gemini",
            "groq",
            "alibaba",
            "minimax",
        } <= provider_ids
        for provider_id in (
            "openai",
            "anthropic",
            "gemini",
            "groq",
            "alibaba",
            "minimax",
        ):
            provider = _provider_by_id(payload, provider_id)
            assert provider["enabled"] is False
            assert provider["authorized"] is False
            assert provider["disabled_reason"] == "Missing provider credentials"
        assert (
            _provider_by_id(payload, "alibaba")["model_index"]["failure_kind"]
            == "auth_config_error"
        )
        assert (
            _provider_by_id(payload, "minimax")["model_index"]["failure_kind"]
            == "auth_config_error"
        )
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
