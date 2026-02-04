from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import documents as documents_routes

_API_KEY = "test-api-key"


def _auth_headers(monkeypatch) -> dict[str, str]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    return {"X-API-Key": _API_KEY}


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(documents_routes.router)
    return TestClient(app)


def test_document_generate_happy_path(monkeypatch) -> None:
    calls: dict[str, object] = {}

    def fake_chat_with_ai(messages, model=None, provider=None, settings=None):
        calls["messages"] = messages
        calls["model"] = model
        calls["provider"] = provider
        return "Drafted content"

    monkeypatch.setattr(documents_routes, "chat_with_ai", fake_chat_with_ai)

    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        headers=_auth_headers(monkeypatch),
        json={
            "title": "Launch Brief",
            "prompt": "Summarize the launch goals.",
            "type": "markdown",
            "context": "Use the Q1 planning notes.",
            "provider": "groq",
            "model": "moonshotai-kimi-k2-instruct-9050",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == "Drafted content"
    assert payload["format"] == "markdown"
    assert payload["title"] == "Launch Brief"
    assert payload["provider"] == "groq"
    assert payload["model"] == "moonshotai-kimi-k2-instruct-9050"

    assert calls["provider"] == "groq"
    assert calls["model"] == "moonshotai-kimi-k2-instruct-9050"
    user_content = calls["messages"][1]["content"]
    assert "Title: Launch Brief" in user_content
    assert "Context: Use the Q1 planning notes." in user_content
    assert "Prompt: Summarize the launch goals." in user_content


def test_document_generate_requires_prompt(monkeypatch) -> None:
    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        headers=_auth_headers(monkeypatch),
        json={
            "title": "Launch Brief",
            "prompt": "   ",
            "type": "markdown",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "prompt is required and cannot be empty"
