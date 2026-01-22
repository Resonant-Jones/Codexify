from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.db import models
from guardian.routes import documents as documents_routes


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


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(documents_routes.router)
    return TestClient(app)


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
    return mock_db, mock_session


def test_document_generate_persists_and_links(monkeypatch) -> None:
    thread = _Thread(id=42, project_id=7, user_id="user-1", title="Seed")
    mock_db, mock_session = _make_db(thread)

    monkeypatch.setattr(documents_routes, "_get_db", lambda: mock_db)
    monkeypatch.setattr(
        documents_routes,
        "chat_with_ai",
        lambda *args, **kwargs: "Drafted content",
    )
    monkeypatch.setattr(
        documents_routes.uuid,
        "uuid4",
        lambda: uuid.UUID("11111111-1111-1111-1111-111111111111"),
    )

    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        json={
            "thread_id": 42,
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
    assert payload["document_id"] == "11111111-1111-1111-1111-111111111111"
    assert payload["content"] == "Drafted content"
    assert payload["format"] == "markdown"

    added_objects = [call.args[0] for call in mock_session.add.call_args_list]
    generated_doc = next(
        obj
        for obj in added_objects
        if isinstance(obj, models.GeneratedDocument)
    )
    link = next(
        obj for obj in added_objects if isinstance(obj, models.ThreadDocument)
    )

    assert generated_doc.id == payload["document_id"]
    assert generated_doc.thread_id == thread.id
    assert generated_doc.project_id == thread.project_id
    assert generated_doc.user_id == thread.user_id
    assert generated_doc.title == "Launch Brief"
    assert generated_doc.content == "Drafted content"
    assert generated_doc.format == "md"
    assert generated_doc.model == "moonshotai-kimi-k2-instruct-9050"

    assert link.thread_id == thread.id
    assert link.document_id == payload["document_id"]
    assert link.relation == "attached"


def test_document_generate_persist_failure(monkeypatch) -> None:
    thread = _Thread(id=7, project_id=1, user_id="user-1", title="Seed")
    mock_db, mock_session = _make_db(thread)
    mock_session.commit.side_effect = RuntimeError("db down")

    monkeypatch.setattr(documents_routes, "_get_db", lambda: mock_db)
    monkeypatch.setattr(
        documents_routes,
        "chat_with_ai",
        lambda *args, **kwargs: "Drafted content",
    )

    client = _make_client()
    response = client.post(
        "/api/documents/generate",
        json={
            "thread_id": 7,
            "title": "Launch Brief",
            "prompt": "Summarize the launch goals.",
            "type": "markdown",
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to persist generated document."
