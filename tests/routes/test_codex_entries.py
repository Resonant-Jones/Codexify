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


@pytest.fixture(autouse=True)
def _reset_lineage_state():
    reset_lineage_session_factory()
    yield
    reset_lineage_session_factory()


def _seed_lineage_db(
    db_path: str,
    *,
    thread_id: int,
    message_id: int | None = None,
) -> None:
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
            text("CREATE TABLE chat_threads (id INTEGER PRIMARY KEY)")
        )
        session.execute(
            text(
                """
                CREATE TABLE chat_messages (
                    id INTEGER PRIMARY KEY,
                    thread_id INTEGER NOT NULL
                )
                """
            )
        )
        session.execute(
            text("INSERT INTO chat_threads (id) VALUES (:thread_id)"),
            {"thread_id": thread_id},
        )
        if message_id is not None:
            session.execute(
                text(
                    "INSERT INTO chat_messages (id, thread_id) VALUES (:message_id, :thread_id)"
                ),
                {"message_id": message_id, "thread_id": thread_id},
            )
        session.commit()
    _set_lineage_session_factory(Session)


def _make_client(monkeypatch, tmp_path) -> TestClient:
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)
    monkeypatch.setattr(codex_routes, "chatlog_db", None)
    monkeypatch.setattr(codex_routes, "get_single_user_id", lambda: "local")

    app = FastAPI()
    app.include_router(codex_routes.router)
    app.dependency_overrides[
        codex_routes.require_api_key
    ] = lambda: "test-api-key"
    return TestClient(app)


def test_create_codex_entry_round_trips_thread_only_lineage(
    monkeypatch, tmp_path
):
    _seed_lineage_db(str(tmp_path / "lineage.db"), thread_id=11)
    client = _make_client(monkeypatch, tmp_path)

    metadata = {
        "artifactKind": "retrieval_posture_diff_note",
        "comparison_mode": "pinned_vs_current",
        "changed_fields": ["source_mode", "widen_reason"],
        "pinned_posture": {
            "source_mode": "conversation",
            "boundary_label": "active_conversation_only",
            "retrieval_override_mode": "conversation",
            "widen_reason": "none",
            "conversation_only": True,
        },
        "current_posture": {
            "source_mode": "project",
            "boundary_label": "same_user_same_project",
            "retrieval_override_mode": "none",
            "widen_reason": "insufficient_thread_hits",
            "conversation_only": False,
        },
    }
    content = (
        "Retrieval posture comparison\n\n"
        "Pinned posture differs from current."
    )

    response = client.post(
        "/api/codex/entries",
        json={
            "type": "note",
            "content": content,
            "threadId": 11,
            "sourceMessageId": None,
            "projectId": 17,
            "metadata": metadata,
        },
    )

    assert response.status_code == 201
    created = response.json()["entry"]
    entry_id = created["id"]
    assert int(created["source_thread_id"]) == 11
    assert created["source_message_id"] is None
    assert created["lineage_missing"] is False

    readback = client.get(f"/api/codex/entries/{entry_id}")
    assert readback.status_code == 200
    payload = readback.json()
    assert payload["body"] == content
    assert payload["frontmatter"]["project_id"] == 17
    assert payload["frontmatter"]["metadata"] == metadata
    assert (
        payload["frontmatter"]["metadata"]["pinned_posture"]["source_mode"]
        == "conversation"
    )
    assert (
        payload["frontmatter"]["metadata"]["current_posture"]["widen_reason"]
        == "insufficient_thread_hits"
    )

    source = client.get(f"/api/codex/{entry_id}/source")
    assert source.status_code == 200
    source_payload = source.json()
    assert source_payload["codex_entry_id"] == entry_id
    assert source_payload["source_thread_id"] == 11
    assert source_payload["source_message_id"] is None
    assert "message_index" not in source_payload


def test_create_codex_entry_accepts_message_linked_lineage(
    monkeypatch, tmp_path
):
    _seed_lineage_db(str(tmp_path / "lineage.db"), thread_id=11, message_id=22)
    client = _make_client(monkeypatch, tmp_path)

    response = client.post(
        "/api/codex/entries",
        json={
            "type": "note",
            "content": "Pinned vs current diff note",
            "threadId": 11,
            "sourceMessageId": 22,
            "metadata": {
                "artifactKind": "retrieval_posture_diff_note",
                "comparison_mode": "pinned_vs_current",
            },
        },
    )

    assert response.status_code == 201
    entry_id = response.json()["entry"]["id"]

    source = client.get(f"/api/codex/{entry_id}/source")
    assert source.status_code == 200
    source_payload = source.json()
    assert source_payload["source_thread_id"] == 11
    assert source_payload["source_message_id"] == 22
    assert source_payload["message_index"] == 0

    readback = client.get(f"/api/codex/entries/{entry_id}")
    assert readback.status_code == 200
    assert readback.json()["frontmatter"]["message_ids"] == [22]


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "memo", "content": "x", "threadId": 11},
        {"type": "note", "content": "x"},
        {
            "type": "note",
            "content": "x",
            "threadId": 11,
            "metadata": "not-an-object",
        },
    ],
)
def test_create_codex_entry_rejects_invalid_payloads(
    monkeypatch, tmp_path, payload
):
    client = _make_client(monkeypatch, tmp_path)

    response = client.post("/api/codex/entries", json=payload)

    assert response.status_code == 422
