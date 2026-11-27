"""Execute the actual Alembic lineage against an opt-in disposable local cluster."""

import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.core.chat_account_custody import (
    ChatAccountAcceptancePending,
    ChatAccountCustodyUnavailable,
    resolve_accepted_chat_work_identity,
)
from guardian.core.db import (
    build_native_origin_assertion,
    create_chat_completion_attempt,
    freeze_chat_tool_decision,
    mark_chat_completion_attempt_accepted,
)
from guardian.db.models import ChatCompletionAttempt, ChatMessage, ChatThread, User
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline

PARENT = "a64c358e2241"
REVISION = "e4b7c2d9a601"
ACCOUNT = "source-proof@example.invalid"


@pytest.fixture
def disposable_database(monkeypatch):
    socket_value = os.environ.get("CODEXIFY_RECALL_SOURCE_TEST_PG_SOCKET")
    if not socket_value:
        pytest.skip("requires an explicit disposable Recall-source PostgreSQL socket")
    socket = Path(socket_value).resolve()
    assert socket.parent.parent == Path("/tmp").resolve()
    assert socket.parent.name.startswith("codexify-recall-01a.")
    assert socket.name == "socket" and socket.is_dir()
    port = int(os.environ["CODEXIFY_RECALL_SOURCE_TEST_PG_PORT"])
    assert (socket / f".s.PGSQL.{port}").is_socket()
    database = f"recall_source_{uuid4().hex}"

    with psycopg.connect(
        dbname="postgres",
        host=str(socket),
        port=port,
        autocommit=True,
        client_encoding="UTF8",
    ) as root:
        assert root.execute("SHOW listen_addresses").fetchone() == ("",)
        root.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(
                sql.Identifier(database)
            )
        )
        url = f"postgresql+psycopg:///{database}?host={socket}&port={port}"
        monkeypatch.setenv("DATABASE_URL", url)
        engine = create_engine(url)
        try:
            config = Config("backend/alembic.ini")
            command.upgrade(config, PARENT)
            yield config, engine
        finally:
            engine.dispose()
            root.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))


def _make_source(sessions):
    with sessions.begin() as session:
        thread = ChatThread(user_id=ACCOUNT, title="Isolated accepted source")
        session.add(thread)
        session.flush()
        message = ChatMessage(
            thread_id=thread.id,
            user_id=ACCOUNT,
            role="user",
            kind="chat",
            content="isolated fixture only",
            extra_meta=build_native_origin_assertion().as_metadata(),
        )
        session.add(message)
        session.flush()
        return thread.id, message.id


def _bound_attempt(sessions, *, suffix, thread_id, source_id):
    deadline = build_accepted_chat_task_deadline(datetime.now(timezone.utc))
    task = SimpleNamespace(
        request_id=f"request-{suffix}",
        task_id=f"task-{suffix}",
        turn_id=f"turn-{suffix}",
        thread_id=thread_id,
        user_id=ACCOUNT,
        latest_turn_message_id=source_id,
        origin="api:chat.complete",
        **deadline.to_dict(),
    )
    store = SimpleNamespace(_sa_session=sessions.begin)
    create_chat_completion_attempt(
        store,
        request_id=task.request_id,
        backend_task_id=task.task_id,
        turn_id=task.turn_id,
        thread_id=thread_id,
        deadline_snapshot=deadline,
        turn_lock_token="isolated-lock",
        accepted_account_id=ACCOUNT,
        accepted_user_message_id=source_id,
    )
    return store, task


def _assert_write_refused(engine, statement, **params):
    with pytest.raises(IntegrityError) as failure, engine.begin() as connection:
        connection.execute(text(statement), params)
    assert failure.value.orig.sqlstate == "23514"


def test_migration_source_custody_roundtrip(disposable_database, monkeypatch):
    config, engine = disposable_database
    sessions = sessionmaker(engine)
    with sessions.begin() as session:
        session.add(User(id=ACCOUNT, username="source-proof", password_hash="inert"))
    thread_id, source_id = _make_source(sessions)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO chat_completion_attempts "
                "(request_id, backend_task_id, thread_id, turn_id, accepted_account_id) "
                "VALUES ('legacy', 'legacy-task', :thread, 'legacy-turn', :owner)"
            ),
            {"thread": thread_id, "owner": ACCOUNT},
        )

    command.upgrade(config, REVISION)
    with sessions.begin() as session:
        legacy = session.get(ChatCompletionAttempt, "legacy")
        assert legacy.accepted_account_id == ACCOUNT
        assert legacy.accepted_user_message_id is None
        assert legacy.backend_task_id == "legacy-task"
        assert (
            session.scalar(text("SELECT version_num FROM alembic_version")) == REVISION
        )

    store, task = _bound_attempt(
        sessions, suffix="bound", thread_id=thread_id, source_id=source_id
    )
    monkeypatch.setattr("guardian.queue.redis_queue.is_cancelled", lambda _: False)
    with pytest.raises(ChatAccountAcceptancePending):
        resolve_accepted_chat_work_identity(store, task)
    mark_chat_completion_attempt_accepted(store, backend_task_id=task.task_id)
    binding = resolve_accepted_chat_work_identity(store, task)
    assert (binding.account_id, binding.accepted_user_message_id) == (
        ACCOUNT,
        source_id,
    )
    with sessions.begin() as session:
        row = session.get(ChatCompletionAttempt, task.request_id)
        assert row.accepted_at is not None and row.tool_turn_id is None
        assert row.accepted_user_message_id == source_id

    _assert_write_refused(
        engine,
        "INSERT INTO chat_completion_attempts "
        "(request_id, backend_task_id, thread_id, turn_id, accepted_user_message_id) "
        "VALUES ('unowned', 'unowned-task', :thread, 'unowned-turn', :source)",
        thread=thread_id,
        source=source_id,
    )
    for req, value in [
        (task.request_id, source_id + 1),
        (task.request_id, None),
        ("legacy", source_id),
    ]:
        _assert_write_refused(
            engine,
            "UPDATE chat_completion_attempts SET accepted_user_message_id=:source "
            "WHERE request_id=:req",
            source=value,
            req=req,
        )
    _assert_write_refused(
        engine,
        "UPDATE chat_completion_attempts SET accepted_account_id='other' WHERE request_id=:req",
        req=task.request_id,
    )

    with sessions.begin() as session:
        session.delete(session.get(ChatMessage, source_id))
    with sessions.begin() as session:
        assert (
            session.get(ChatCompletionAttempt, task.request_id).accepted_user_message_id
            == source_id
        )
    with pytest.raises(ChatAccountCustodyUnavailable):
        resolve_accepted_chat_work_identity(store, task)

    # Ordinary checkpoint and terminal writes remain valid after source deletion.
    freeze_chat_tool_decision(
        store,
        request_id=task.request_id,
        backend_task_id=task.task_id,
        thread_id=thread_id,
        turn_id=task.turn_id,
        account_id=ACCOUNT,
        command_id="op::notion_content_search",
        args_hash="a" * 64,
    )
    with sessions.begin() as session:
        session.get(
            ChatCompletionAttempt, task.request_id
        ).terminal_event_type = "task.failed"
    with engine.connect() as connection:
        before = connection.execute(
            text(
                "SELECT request_id, backend_task_id, accepted_account_id, "
                "accepted_at, terminal_event_type, tool_args_hash "
                "FROM chat_completion_attempts ORDER BY request_id"
            )
        ).all()

    # Separate bound rows prove the existing thread and account cascades can run.
    delete_thread, delete_source = _make_source(sessions)
    _, deleted_work = _bound_attempt(
        sessions,
        suffix="thread-delete",
        thread_id=delete_thread,
        source_id=delete_source,
    )
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM chat_threads WHERE id=:id"), {"id": delete_thread}
        )
    with sessions.begin() as session:
        assert session.get(ChatCompletionAttempt, deleted_work.request_id) is None
        assert session.get(ChatMessage, delete_source) is None

    command.downgrade(config, PARENT)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT request_id, backend_task_id, accepted_account_id, "
                    "accepted_at, terminal_event_type, tool_args_hash "
                    "FROM chat_completion_attempts ORDER BY request_id"
                )
            ).all()
            == before
        )
        assert not any(
            column["name"] == "accepted_user_message_id"
            for column in inspect(connection).get_columns("chat_completion_attempts")
        )

    # Re-upgrade creates no retroactive custody. A live account cascade still
    # succeeds on a newly bound row with the trigger installed.
    command.upgrade(config, REVISION)
    with sessions.begin() as session:
        assert (
            session.get(ChatCompletionAttempt, task.request_id).accepted_user_message_id
            is None
        )
    erase_thread, erase_source = _make_source(sessions)
    _, erased_work = _bound_attempt(
        sessions,
        suffix="account-delete",
        thread_id=erase_thread,
        source_id=erase_source,
    )
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM users WHERE id=:id"), {"id": ACCOUNT})
    with sessions.begin() as session:
        assert session.get(ChatMessage, erase_source) is None
        assert session.get(ChatCompletionAttempt, erased_work.request_id) is None
        assert session.scalar(select(User.id).where(User.id == ACCOUNT)) is None
