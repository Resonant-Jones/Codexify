from __future__ import annotations

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


def _provider_by_id(payload: dict, provider_id: str) -> dict:
    return next(
        provider
        for provider in payload["providers"]
        if provider.get("id") == provider_id
    )


def test_llm_catalog_hides_unauthorized_cloud_providers_by_default(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
        "MINIMAX_MODEL": settings.MINIMAX_MODEL,
        "LOCAL_BASE_URL": settings.LOCAL_BASE_URL,
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_BASE", raising=False)
        monkeypatch.delenv("MINIMAX_MODEL", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai,anthropic,gemini,groq"
        settings.GROQ_API_KEY = None
        settings.OPENAI_API_KEY = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None
        settings.MINIMAX_MODEL = None
        settings.LOCAL_BASE_URL = "http://127.0.0.1:11434/v1"

        client = TestClient(app)
        response = client.get("/api/llm/catalog")
        assert response.status_code == 200

        payload = response.json()
        provider_ids = [provider["id"] for provider in payload["providers"]]
        assert provider_ids == ["local"]
        local = _provider_by_id(payload, "local")
        assert local["displayName"] == "Local"
        assert local["enabled"] is True
        assert local["source"]["kind"] == "local"
        assert local["source"]["baseUrl"] == "http://127.0.0.1:11434/v1"
        assert local["source"]["label"] == "127.0.0.1:11434"
        assert [m["id"] for m in local["models"]] == [
            "llama3.1:8b",
            "qwen2.5:7b",
        ]
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_includes_authorized_provider(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_BASE", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
        settings.GROQ_API_KEY = "test-groq-key"
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        response = client.get("/api/llm/catalog")
        assert response.status_code == 200
        payload = response.json()
        groq = _provider_by_id(payload, "groq")
        assert groq["authorized"] is True
        assert groq["available"] is True
        assert groq["enabled"] is True
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_marks_qwen3_local_models_as_no_think_by_default(
    monkeypatch,
):
    def _mock_qwen_catalog_request(url: str, *args, **kwargs) -> _MockResponse:
        if url.endswith("/api/tags"):
            return _MockResponse(
                {"models": [{"name": "qwen3:4b"}, {"name": "qwen3.5:4b"}]}
            )
        return _MockResponse({"data": []}, status_code=404)

    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_qwen_catalog_request,
    )

    settings = get_settings()
    snapshot = {
        "LOCAL_BASE_URL": settings.LOCAL_BASE_URL,
        "LOCAL_DEFAULT_NO_THINK_ENABLED": settings.LOCAL_DEFAULT_NO_THINK_ENABLED,
    }
    try:
        settings.LOCAL_BASE_URL = "http://127.0.0.1:11434/v1"
        settings.LOCAL_DEFAULT_NO_THINK_ENABLED = True

        client = TestClient(app)
        response = client.get("/api/llm/catalog")
        assert response.status_code == 200

        payload = response.json()
        local = _provider_by_id(payload, "local")
        qwen = next(
            model for model in local["models"] if model.get("id") == "qwen3:4b"
        )
        assert qwen["runtime"]["reasoning"]["mode"] == "no_think"
        assert qwen["runtime"]["reasoning"]["instruction"] == "/no_think"
        qwen_3_5 = next(
            model
            for model in local["models"]
            if model.get("id") == "qwen3.5:4b"
        )
        assert qwen_3_5["runtime"]["reasoning"]["mode"] == "no_think"
        assert qwen_3_5["runtime"]["reasoning"]["instruction"] == "/no_think"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_marks_cloud_disabled_when_allow_cloud_is_false(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_BASE", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = False
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
        settings.GROQ_API_KEY = "test-groq-key"
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        response = client.get("/api/llm/catalog")
        assert response.status_code == 200
        payload = response.json()
        groq = _provider_by_id(payload, "groq")
        assert groq["authorized"] is True
        assert groq["available"] is False
        assert groq["enabled"] is False
        assert groq["disabled_reason"] == "Cloud providers disabled by config"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_include_all_returns_unauthorized_cloud_providers(
    monkeypatch,
):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.delenv("MINIMAX_API_BASE", raising=False)
        monkeypatch.delenv("MINIMAX_MODEL", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai,anthropic,gemini,groq"
        settings.GROQ_API_KEY = None
        settings.OPENAI_API_KEY = None
        settings.MINIMAX_API_KEY = None
        settings.MINIMAX_API_BASE = None

        client = TestClient(app)
        response = client.get("/api/llm/catalog?include=all")
        assert response.status_code == 200
        payload = response.json()

        provider_ids = {provider["id"] for provider in payload["providers"]}
        assert {
            "local",
            "openai",
            "anthropic",
            "gemini",
            "groq",
            "minimax",
        }.issubset(provider_ids)

        groq = _provider_by_id(payload, "groq")
        openai = _provider_by_id(payload, "openai")
        anthropic = _provider_by_id(payload, "anthropic")
        gemini = _provider_by_id(payload, "gemini")
        minimax = _provider_by_id(payload, "minimax")
        assert groq["authorized"] is False
        assert groq["available"] is False
        assert groq["enabled"] is False
        assert groq["disabled_reason"] == "Missing provider credentials"
        assert openai["authorized"] is False
        assert openai["available"] is False
        assert openai["enabled"] is False
        assert openai["disabled_reason"] == "Missing provider credentials"
        assert anthropic["authorized"] is False
        assert anthropic["available"] is False
        assert anthropic["enabled"] is False
        assert anthropic["disabled_reason"] == "Missing provider credentials"
        assert gemini["authorized"] is False
        assert gemini["available"] is False
        assert gemini["enabled"] is False
        assert gemini["disabled_reason"] == "Missing provider credentials"
        assert minimax["authorized"] is False
        assert minimax["available"] is False
        assert minimax["enabled"] is False
        assert minimax["disabled_reason"] == "Missing provider credentials"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_minimax_enabled_with_key_base_and_egress(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
        "MINIMAX_MODEL": settings.MINIMAX_MODEL,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "minimax"
        settings.MINIMAX_API_KEY = "test-minimax-key"
        settings.MINIMAX_API_BASE = "https://api.minimax.local/v1"
        settings.MINIMAX_MODEL = "minimax-chat"

        client = TestClient(app)
        response = client.get("/api/llm/catalog")
        assert response.status_code == 200
        payload = response.json()

        minimax = _provider_by_id(payload, "minimax")
        assert minimax["authorized"] is True
        assert minimax["available"] is True
        assert minimax["enabled"] is True
        assert minimax["models"][0]["id"] == "minimax-chat"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)


def test_llm_catalog_minimax_blocked_when_egress_missing(monkeypatch):
    monkeypatch.setattr(
        "guardian.core.llm_catalog.requests.get",
        _mock_local_catalog_request,
    )

    settings = get_settings()
    snapshot = {
        "ALLOW_CLOUD_PROVIDERS": settings.ALLOW_CLOUD_PROVIDERS,
        "CODEXIFY_LOCAL_ONLY_MODE": settings.CODEXIFY_LOCAL_ONLY_MODE,
        "CODEXIFY_EGRESS_ALLOWLIST": settings.CODEXIFY_EGRESS_ALLOWLIST,
        "MINIMAX_API_KEY": settings.MINIMAX_API_KEY,
        "MINIMAX_API_BASE": settings.MINIMAX_API_BASE,
    }
    try:
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
        settings.MINIMAX_API_KEY = "test-minimax-key"
        settings.MINIMAX_API_BASE = "https://api.minimax.local/v1"

        client = TestClient(app)
        response = client.get("/api/llm/catalog?include=all")
        assert response.status_code == 200
        payload = response.json()

        minimax = _provider_by_id(payload, "minimax")
        assert minimax["authorized"] is True
        assert minimax["available"] is False
        assert minimax["enabled"] is False
        assert minimax["disabled_reason"] == "Provider blocked by egress policy"
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
