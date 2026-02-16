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


def _seed_lineage_db(db_path: str, *, thread_id: int, message_id: int) -> None:
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
        session.execute(
            text(
                "INSERT INTO chat_messages (id, thread_id) VALUES (:message_id, :thread_id)"
            ),
            {"message_id": message_id, "thread_id": thread_id},
        )
        session.commit()
    _set_lineage_session_factory(Session)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(codex_routes.router)
    return app


def test_codex_source_returns_thread_and_message(monkeypatch, tmp_path):
    _seed_lineage_db(str(tmp_path / "lineage.db"), thread_id=11, message_id=22)
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    entry_path = codex_root / "entry-1.cdx"
    entry_path.write_text(
        "---\n"
        "id: entry-1\n"
        "title: Lineage Entry\n"
        "source_thread_id: 11\n"
        "source_message_id: 22\n"
        "message_ids:\n"
        "  - 21\n"
        "  - 22\n"
        "---\n\n"
        "Body\n",
        encoding="utf-8",
    )

    client = TestClient(_make_app())
    response = client.get("/api/codex/entry-1/source")
    assert response.status_code == 200
    payload = response.json()
    assert payload["codex_entry_id"] == "entry-1"
    assert payload["source_thread_id"] == 11
    assert payload["source_message_id"] == 22
    assert payload["message_index"] == 1


def test_codex_source_requires_lineage(monkeypatch, tmp_path):
    codex_root = tmp_path / "codex"
    codex_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(codex_service, "CODEX_ROOT", codex_root)

    entry_path = codex_root / "entry-2.cdx"
    entry_path.write_text(
        "---\n" "id: entry-2\n" "title: Missing Lineage\n" "---\n\n" "Body\n",
        encoding="utf-8",
    )

    client = TestClient(_make_app())
    response = client.get("/api/codex/entry-2/source")
    assert response.status_code == 422
    assert "source_thread_id and source_message_id are required" in str(
        response.json().get("detail")
    )
