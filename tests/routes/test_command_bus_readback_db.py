"""Readback account-isolation proof using a disposable Unix-socket PostgreSQL.

Set READBACK_TEST_DATABASE_URL explicitly; never consult application DB config.
These tests prove route/store ownership with persisted canonical ORM records,
not production adapter wiring or deployed HTTP authentication.
"""

from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from guardian.command_bus.store import CommandBusStore
from guardian.db.models import Base, ChatMessage, ChatThread, CommandRun, User
from guardian.routes import command_bus as routes


@pytest.fixture
def persisted(monkeypatch):
    raw_url = os.getenv("READBACK_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("READBACK_TEST_DATABASE_URL required for isolated PostgreSQL proof")
    url = make_url(raw_url)
    assert url.drivername == "postgresql+psycopg"
    assert url.host is None
    assert url.database == "readback_proof"
    assert str(url.query.get("host", "")).startswith("/tmp/cfy-readback-")
    schema = "readback_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    tables = {
        User.__table__,
        ChatThread.__table__,
        ChatMessage.__table__,
        CommandRun.__table__,
    }
    while True:
        expanded = tables | {
            fk.column.table for table in tables for fk in table.foreign_keys
        }
        if expanded == tables:
            break
        tables = expanded
    try:
        Base.metadata.create_all(engine, tables=list(tables))
        with sessions.begin() as session:
            session.add_all(
                [
                    User(id=x, username=x, password_hash="inert-fixture")
                    for x in ("owner-a", "owner-b")
                ]
            )
            session.flush()
            thread = ChatThread(user_id="owner-a", title="synthetic readback proof")
            session.add(thread)
            session.flush()
            message = ChatMessage(
                thread_id=thread.id,
                user_id="owner-b",
                role="assistant",
                content="inert fixture",
                extra_meta={"toolTurnId": "proof-turn"},
            )
            session.add(message)
            session.flush()
            mid, tid = message.id, thread.id

        def get_message(message_id):
            with sessions() as session:
                return session.get(ChatMessage, message_id)

        def get_thread(thread_id):
            with sessions() as session:
                thread = session.get(ChatThread, thread_id)
                return {"id": thread.id, "user_id": thread.user_id} if thread else None

        db = SimpleNamespace(
            get_session=sessions, get_message=get_message, get_chat_thread=get_thread
        )
        store = CommandBusStore(db=db)
        monkeypatch.setattr(routes, "_store", store)
        monkeypatch.setattr(routes, "_chat_db", db)
        runs = {}
        for owner in ("owner-a", "owner-b"):
            runs[owner] = store.create_run(
                command_id="test::read",
                status="completed",
                actor_kind="user",
                actor_id=owner,
                actor_session_id=None,
                delegated_by=None,
                auth_subject=owner,
                invoke_version="1",
                idempotency_key=None,
                args_hash="0" * 64,
                args_redacted={},
            )["run_id"]
        yield SimpleNamespace(sessions=sessions, mid=mid, tid=tid, runs=runs)
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_persisted_run_owner_readback(persisted):
    result = asyncio.run(routes.get_run(persisted.runs["owner-a"], "owner-a"))
    assert result["auth_subject"] == "owner-a"
    with pytest.raises(HTTPException) as denied:
        asyncio.run(routes.get_run(persisted.runs["owner-a"], "owner-b"))
    assert denied.value.status_code == 403


def test_persisted_message_uses_thread_not_message_user(persisted):
    result = asyncio.run(
        routes.get_tool_turn_observability(str(persisted.mid), "owner-a")
    )
    assert result["tool_turn_id"] == "proof-turn"
    with pytest.raises(HTTPException) as denied:
        asyncio.run(routes.get_tool_turn_observability(str(persisted.mid), "owner-b"))
    assert denied.value.status_code == 403


@pytest.mark.parametrize("run_owner,allowed", [("owner-a", True), ("owner-b", False)])
def test_persisted_linked_run_ownership(persisted, run_owner, allowed):
    with persisted.sessions.begin() as session:
        message = session.get(ChatMessage, persisted.mid)
        message.extra_meta = {
            "toolTurnId": "proof-turn",
            "commandRunId": persisted.runs[run_owner],
        }
    if allowed:
        result = asyncio.run(
            routes.get_tool_turn_observability(str(persisted.mid), "owner-a")
        )
        assert result["command_run_id"] == persisted.runs[run_owner]
    else:
        with pytest.raises(HTTPException) as denied:
            asyncio.run(
                routes.get_tool_turn_observability(str(persisted.mid), "owner-a")
            )
        assert denied.value.status_code == 403


def test_persisted_owner_change_is_revalidated(persisted):
    assert asyncio.run(
        routes.get_tool_turn_observability(str(persisted.mid), "owner-a")
    )
    with persisted.sessions.begin() as session:
        session.get(ChatThread, persisted.tid).user_id = "owner-b"
    with pytest.raises(HTTPException) as denied:
        asyncio.run(routes.get_tool_turn_observability(str(persisted.mid), "owner-a"))
    assert denied.value.status_code == 403
    assert asyncio.run(
        routes.get_tool_turn_observability(str(persisted.mid), "owner-b")
    )
