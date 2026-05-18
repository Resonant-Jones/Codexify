"""Tests for the codex entry draft and save routes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from guardian.codex import service as codex_service
from guardian.codex.lineage import (
    _set_session_factory as _set_lineage_session_factory,
)
from guardian.codex.lineage import (
    reset_session_factory as reset_lineage_session_factory,
)
from guardian.routes import codex as codex_routes

API_HEADERS = {"X-API-Key": "test"}


@pytest.fixture(autouse=True)
def _reset_lineage_state():
    reset_lineage_session_factory()
    yield
    reset_lineage_session_factory()


def _seed_chatlog(
    monkeypatch, tmp_path, *, thread_id: int, messages: list[dict]
) -> None:
    """Seed a SQLite-backed chatlog with thread and messages for testing."""
    db_path = str(tmp_path / "chatlog.db")
    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    with Session() as session:
        session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS chat_threads (id INTEGER PRIMARY KEY)"
            )
        )
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY,
                    thread_id INTEGER NOT NULL,
                    role TEXT,
                    content TEXT
                )
                """
            )
        )
        session.execute(
            text("INSERT INTO chat_threads (id) VALUES (:thread_id)"),
            {"thread_id": thread_id},
        )
        for msg in messages:
            session.execute(
                text(
                    "INSERT INTO chat_messages (id, thread_id, role, content) "
                    "VALUES (:id, :thread_id, :role, :content)"
                ),
                {
                    "id": msg["id"],
                    "thread_id": thread_id,
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                },
            )
        session.commit()

    # Wire the chatlog db dependency
    from guardian.codex import lineage as lineage_mod

    _set_lineage_session_factory(Session)

    # Create a simple mock chatlog_db
    class MockChatlogDB:
        def get_chat_thread(self, tid):
            return {"id": tid, "user_id": "local"}

        def list_messages(self, tid, limit=50, offset=0, **kwargs):
            with Session() as s:
                rows = s.execute(
                    text(
                        "SELECT id, thread_id, role, content "
                        "FROM chat_messages WHERE thread_id = :tid "
                        "ORDER BY id ASC LIMIT :limit OFFSET :offset"
                    ),
                    {"tid": tid, "limit": limit, "offset": offset},
                ).fetchall()
            return [
                {
                    "id": row[0],
                    "thread_id": row[1],
                    "role": row[2],
                    "content": row[3],
                }
                for row in rows
            ]

    monkeypatch.setattr(codex_routes, "chatlog_db", MockChatlogDB())


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(codex_routes.router)
    return app


# ---------------------------------------------------------------------------
# Draft endpoint tests
# ---------------------------------------------------------------------------


def test_draft_returns_candidate(monkeypatch, tmp_path):
    """POST /api/codex/entries/draft returns a draft from prior context."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    _seed_chatlog(
        monkeypatch,
        tmp_path,
        thread_id=10,
        messages=[
            {"id": 1, "role": "user", "content": "What is decentralized AI?"},
            {
                "id": 2,
                "role": "assistant",
                "content": "It's AI that runs on edge devices...",
            },
            {"id": 3, "role": "user", "content": "/codex_entry"},
        ],
    )

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/draft",
        json={
            "thread_id": 10,
            "trigger_message_id": 3,
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["draft"] is not None
    assert payload["draft"]["title"]
    assert payload["draft"]["body"]
    # The draft body should come from prior context, not the command
    assert "What is decentralized AI?" in payload["draft"]["body"]
    assert "/codex_entry" not in payload["draft"]["body"]
    # Lineage should include source message ids
    assert payload["draft"]["lineage"]["thread_id"] == 10
    assert payload["draft"]["lineage"]["trigger_message_id"] == 3
    assert 1 in payload["draft"]["lineage"]["source_message_ids"]
    assert 2 in payload["draft"]["lineage"]["source_message_ids"]
    assert 3 not in payload["draft"]["lineage"]["source_message_ids"]


def test_draft_does_not_persist_entry(monkeypatch, tmp_path):
    """The draft endpoint must NOT persist a Codex Entry."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    _seed_chatlog(
        monkeypatch,
        tmp_path,
        thread_id=20,
        messages=[
            {"id": 10, "role": "user", "content": "Hello"},
            {"id": 11, "role": "user", "content": "/codex_entry"},
        ],
    )

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/draft",
        json={
            "thread_id": 20,
            "trigger_message_id": 11,
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["draft"] is not None

    # No .cdx files should have been created
    cdx_files = list(codex_root.glob("**/*.cdx"))
    assert len(cdx_files) == 0, f"Expected 0 .cdx files, found {cdx_files}"


def test_draft_no_context_returns_empty(monkeypatch, tmp_path):
    """When there's no prior context, draft returns null."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    _seed_chatlog(
        monkeypatch,
        tmp_path,
        thread_id=30,
        messages=[
            {"id": 50, "role": "user", "content": "/codex_entry"},
        ],
    )

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/draft",
        json={
            "thread_id": 30,
            "trigger_message_id": 50,
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["draft"] is None
    assert payload["reason"] == "empty_source"


def test_draft_empty_thread_returns_no_context(monkeypatch, tmp_path):
    """When thread has no messages at all, returns no_context."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    _seed_chatlog(
        monkeypatch,
        tmp_path,
        thread_id=40,
        messages=[],
    )

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries/draft",
        json={
            "thread_id": 40,
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["draft"] is None
    assert payload["reason"] == "no_context"


# ---------------------------------------------------------------------------
# Save endpoint tests
# ---------------------------------------------------------------------------


def test_save_persists_markdown(monkeypatch, tmp_path):
    """POST /api/codex/entries persists a Codex Entry with frontmatter."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries",
        json={
            "title": "Test Entry",
            "body": "# Hello\n\nThis is a test.",
            "thread_id": 10,
            "source_thread_id": 10,
            "source_message_id": 2,
            "trigger_message_id": 3,
            "message_ids": [1, 2],
            "created_from": "slash_command",
            "retrieval_enabled": False,
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["entry"]["title"] == "Test Entry"
    assert payload["entry"]["created_from"] == "slash_command"
    assert payload["entry"]["retrieval_enabled"] is False
    assert payload["entry"]["source_message_id"] == "2"
    assert payload["entry"]["trigger_message_id"] == "3"

    # Verify file exists on disk
    cdx_files = list(codex_root.glob("**/*.cdx"))
    assert len(cdx_files) == 1
    content = cdx_files[0].read_text(encoding="utf-8")
    assert "created_from: slash_command" in content
    assert "retrieval_enabled: false" in content
    assert (
        "source_message_id: '2'" in content or "source_message_id: 2" in content
    )
    assert (
        "trigger_message_id: '3'" in content
        or "trigger_message_id: 3" in content
    )


def test_save_persists_created_from(monkeypatch, tmp_path):
    """Save payload carries createdFrom: slash_command in frontmatter."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries",
        json={
            "title": "From Slash",
            "body": "Content",
            "created_from": "slash_command",
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["entry"]["created_from"] == "slash_command"

    cdx_files = list(codex_root.glob("**/*.cdx"))
    content = cdx_files[0].read_text(encoding="utf-8")
    assert "created_from: slash_command" in content


def test_save_persists_retrieval_enabled_false(monkeypatch, tmp_path):
    """Save payload carries retrievalEnabled: false in frontmatter by default."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries",
        json={
            "title": "Retrieval Off",
            "body": "Content",
            "retrieval_enabled": False,
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["entry"]["retrieval_enabled"] is False

    cdx_files = list(codex_root.glob("**/*.cdx"))
    content = cdx_files[0].read_text(encoding="utf-8")
    assert "retrieval_enabled: false" in content


def test_save_trigger_separate_from_source(monkeypatch, tmp_path):
    """Trigger message ID is stored separately from source message ID."""
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    client = TestClient(_make_app())
    response = client.post(
        "/api/codex/entries",
        json={
            "title": "Trigger vs Source",
            "body": "Body",
            "source_message_id": 10,
            "trigger_message_id": 11,
        },
        headers=API_HEADERS,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["entry"]["source_message_id"] == "10"
    assert payload["entry"]["trigger_message_id"] == "11"

    cdx_files = list(codex_root.glob("**/*.cdx"))
    content = cdx_files[0].read_text(encoding="utf-8")
    assert "source_message_id" in content
    assert "trigger_message_id" in content
