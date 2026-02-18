from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.db import models
from guardian.routes import documents as documents_routes

_API_KEY = "test-api-key"


def _auth_headers(monkeypatch) -> dict[str, str]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    return {"X-API-Key": _API_KEY}


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(documents_routes.router)
    return TestClient(app)


@dataclass
class _Thread:
    id: int
    project_id: int | None
    user_id: str | None
    title: str


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return self._result


def _make_db(thread: _Thread):
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    mock_db.get_session.return_value.__exit__.return_value = False

    def query_side_effect(model):
        if model is models.ChatThread:
            return _FakeQuery(thread)
        return _FakeQuery(None)

    mock_session.query.side_effect = query_side_effect
    return mock_db


def test_document_generate_happy_path(monkeypatch) -> None:
    thread = _Thread(id=5, project_id=2, user_id="user-1", title="Seed")
    mock_db = _make_db(thread)
    calls: dict[str, object] = {}

    def fake_chat_with_ai(messages, model=None, provider=None, settings=None):
        calls["messages"] = messages
        calls["model"] = model
        calls["provider"] = provider
        return "Drafted content"

    monkeypatch.setattr(documents_routes, "_get_db", lambda: mock_db)
    monkeypatch.setattr(documents_routes, "chat_with_ai", fake_chat_with_ai)
    monkeypatch.setattr(
        documents_routes.uuid,
        "uuid4",
        lambda: uuid.UUID("33333333-3333-3333-3333-333333333333"),
    )

    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        headers=_auth_headers(monkeypatch),
        json={
            "thread_id": 5,
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
    assert payload["document_id"] == "33333333-3333-3333-3333-333333333333"
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


def test_document_generate_accepts_minimax_provider(monkeypatch) -> None:
    thread = _Thread(id=6, project_id=3, user_id="user-2", title="MiniMax")
    mock_db = _make_db(thread)
    calls: dict[str, object] = {}

    def fake_chat_with_ai(messages, model=None, provider=None, settings=None):
        calls["messages"] = messages
        calls["model"] = model
        calls["provider"] = provider
        return "MiniMax drafted content"

    monkeypatch.setattr(documents_routes, "_get_db", lambda: mock_db)
    monkeypatch.setattr(documents_routes, "chat_with_ai", fake_chat_with_ai)

    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        headers=_auth_headers(monkeypatch),
        json={
            "thread_id": 6,
            "title": "MiniMax Brief",
            "prompt": "Draft a short summary.",
            "type": "markdown",
            "provider": "minimax",
            "model": "minimax-chat",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "minimax"
    assert payload["model"] == "minimax-chat"
    assert calls["provider"] == "minimax"
    assert calls["model"] == "minimax-chat"


def test_document_generate_requires_prompt(monkeypatch) -> None:
    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        headers=_auth_headers(monkeypatch),
        json={
            "thread_id": 5,
            "title": "Launch Brief",
            "prompt": "   ",
            "type": "markdown",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "prompt is required and cannot be empty"


def test_document_generate_requires_thread_id(monkeypatch) -> None:
    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        headers=_auth_headers(monkeypatch),
        json={
            "title": "Launch Brief",
            "prompt": "Summarize the launch goals.",
            "type": "markdown",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "thread_id is required"
