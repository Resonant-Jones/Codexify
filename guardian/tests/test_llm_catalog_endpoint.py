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
        "LOCAL_BASE_URL": settings.LOCAL_BASE_URL,
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai,anthropic,gemini,groq"
        settings.GROQ_API_KEY = None
        settings.OPENAI_API_KEY = None
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
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
        settings.GROQ_API_KEY = "test-groq-key"

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
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = False
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "groq"
        settings.GROQ_API_KEY = "test-groq-key"

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
    }
    try:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        settings.ALLOW_CLOUD_PROVIDERS = True
        settings.CODEXIFY_LOCAL_ONLY_MODE = False
        settings.CODEXIFY_EGRESS_ALLOWLIST = "openai,anthropic,gemini,groq"
        settings.GROQ_API_KEY = None
        settings.OPENAI_API_KEY = None

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
        }.issubset(provider_ids)

        groq = _provider_by_id(payload, "groq")
        openai = _provider_by_id(payload, "openai")
        anthropic = _provider_by_id(payload, "anthropic")
        gemini = _provider_by_id(payload, "gemini")
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
    finally:
        for field, value in snapshot.items():
            setattr(settings, field, value)
