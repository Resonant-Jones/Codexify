"""Disposable Postgres upgrade and durable completion authority proof."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from guardian.core.db import (
    create_chat_completion_attempt,
    get_chat_completion_attempt_by_task_id,
    mark_chat_completion_attempt_accepted,
)
from guardian.core.pgdb import PgDB


PREVIOUS_REVISION = "a8d4c2f6b1e9"
ATTEMPT_REVISION = "c9f3e2a7b601"


@pytest.fixture
def disposable_database(monkeypatch):
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")
    db_name = f"codexify_attempt_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=db_name)
    with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as connection:
        connection.execute(f"CREATE DATABASE {db_name}")
    config = Config(str(Path(__file__).resolve().parents[2] / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", test_url.render_as_string(hide_password=False).replace("%", "%%"))
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    try:
        yield config, test_url
    finally:
        with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (db_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {db_name}")


@pytest.mark.integration
def test_upgrade_preserves_chat_data_and_adds_authority(disposable_database):
    config, test_url = disposable_database
    command.upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(test_url)
    with engine.begin() as connection:
        for account in ("account-a", "account-b"):
            connection.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (:id, :id, 'inert-test-hash', 'guest')"
                ),
                {"id": account},
            )
        thread_a = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title) "
                "VALUES ('account-a', 'Existing A') RETURNING id"
            )
        ).scalar_one()
        thread_b = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title) "
                "VALUES ('account-b', 'Existing B') RETURNING id"
            )
        ).scalar_one()
        message_id = connection.execute(
            sa.text(
                "INSERT INTO chat_messages (thread_id, user_id, role, content) "
                "VALUES (:thread, 'account-a', 'user', 'pre-migration text') RETURNING id"
            ),
            {"thread": thread_a},
        ).scalar_one()

    command.upgrade(config, ATTEMPT_REVISION)
    inspector = sa.inspect(engine)
    assert "chat_completion_attempts" in inspector.get_table_names()
    assert {"request_id", "backend_task_id", "thread_id", "turn_id", "created_at", "accepted_at"} <= {
        column["name"] for column in inspector.get_columns("chat_completion_attempts")
    }
    assert ("backend_task_id",) in {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("chat_completion_attempts")
    }
    assert any(
        item["referred_table"] == "chat_threads" and item["constrained_columns"] == ["thread_id"]
        for item in inspector.get_foreign_keys("chat_completion_attempts")
    )
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT count(*) FROM chat_completion_attempts")).scalar_one() == 0
        assert connection.execute(
            sa.text("SELECT content FROM chat_messages WHERE id = :id"), {"id": message_id}
        ).scalar_one() == "pre-migration text"
        assert connection.execute(sa.text("SELECT count(*) FROM users WHERE id IN ('account-a', 'account-b')")).scalar_one() == 2

    repo = PgDB(test_url.render_as_string(hide_password=False))
    create_chat_completion_attempt(repo, request_id="req-a", backend_task_id="task-a", thread_id=thread_a, turn_id="turn-a")
    create_chat_completion_attempt(repo, request_id="req-b", backend_task_id="task-b", thread_id=thread_b, turn_id="turn-b")
    fresh_repo = PgDB(test_url.render_as_string(hide_password=False))
    attempt_a = get_chat_completion_attempt_by_task_id(fresh_repo, "task-a")
    attempt_b = get_chat_completion_attempt_by_task_id(fresh_repo, "task-b")
    assert attempt_a["request_id"] == "req-a"
    assert attempt_a["thread_id"] == thread_a
    assert attempt_a["accepted_at"] is None
    assert attempt_b["thread_id"] == thread_b
    assert get_chat_completion_attempt_by_task_id(fresh_repo, "missing") is None
    mark_chat_completion_attempt_accepted(fresh_repo, backend_task_id="task-a")
    assert get_chat_completion_attempt_by_task_id(repo, "task-a")["accepted_at"] is not None
    assert get_chat_completion_attempt_by_task_id(repo, "task-b")["accepted_at"] is None
    engine.dispose()


@pytest.mark.integration
def test_assistant_and_attempt_success_link_commit_atomically(disposable_database):
    psycopg = pytest.importorskip("psycopg")
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES ('atomic-account', 'atomic-account', 'inert-test-hash', 'guest')"
            )
        )
        thread_id = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title) "
                "VALUES ('atomic-account', 'Atomic completion') RETURNING id"
            )
        ).scalar_one()

    repo = PgDB(test_url.render_as_string(hide_password=False))
    create_chat_completion_attempt(
        repo,
        request_id="atomic-request",
        backend_task_id="atomic-task",
        thread_id=thread_id,
        turn_id="atomic-turn",
    )
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                """CREATE FUNCTION reject_completion_link() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                    IF NEW.completed_message_id IS NOT NULL THEN
                        RAISE EXCEPTION 'injected link failure';
                    END IF;
                    RETURN NEW;
                END; $$"""
            )
        )
        connection.execute(
            sa.text(
                "CREATE TRIGGER reject_completion_link BEFORE UPDATE "
                "ON chat_completion_attempts FOR EACH ROW "
                "EXECUTE FUNCTION reject_completion_link()"
            )
        )

    with pytest.raises(psycopg.errors.RaiseException, match="injected link failure"):
        repo.create_assistant_message_for_completion_attempt(
            thread_id=thread_id,
            content="must roll back",
            request_id="atomic-request",
            backend_task_id="atomic-task",
            turn_id="atomic-turn",
        )

    with engine.begin() as connection:
        connection.execute(sa.text("DROP TRIGGER reject_completion_link ON chat_completion_attempts"))
        connection.execute(sa.text("DROP FUNCTION reject_completion_link()"))
    with engine.connect() as connection:
        assert connection.execute(
            sa.text(
                "SELECT count(*) FROM chat_messages "
                "WHERE thread_id = :thread_id AND content = 'must roll back'"
            ),
            {"thread_id": thread_id},
        ).scalar_one() == 0
        assert connection.execute(
            sa.text(
                "SELECT completed_message_id FROM chat_completion_attempts "
                "WHERE backend_task_id = 'atomic-task'"
            )
        ).scalar_one() is None

    message_id, linked = repo.create_assistant_message_for_completion_attempt(
        thread_id=thread_id,
        content="committed together",
        request_id="atomic-request",
        backend_task_id="atomic-task",
        turn_id="atomic-turn",
    )
    assert linked is True
    repeated_message_id, repeated_linked = (
        repo.create_assistant_message_for_completion_attempt(
            thread_id=thread_id,
            content="must not create another assistant",
            request_id="atomic-request",
            backend_task_id="atomic-task",
            turn_id="atomic-turn",
        )
    )
    assert repeated_linked is True
    assert repeated_message_id == message_id
    with engine.connect() as connection:
        message = connection.execute(
            sa.text(
                "SELECT thread_id, role, content FROM chat_messages WHERE id = :message_id"
            ),
            {"message_id": message_id},
        ).one()
        linked_message_id = connection.execute(
            sa.text(
                "SELECT completed_message_id FROM chat_completion_attempts "
                "WHERE backend_task_id = 'atomic-task'"
            )
        ).scalar_one()
    assert tuple(message) == (thread_id, "assistant", "committed together")
    assert linked_message_id == message_id
    with engine.connect() as connection:
        assert connection.execute(
            sa.text(
                "SELECT count(*) FROM chat_messages "
                "WHERE thread_id = :thread_id AND role = 'assistant'"
            ),
            {"thread_id": thread_id},
        ).scalar_one() == 1
    engine.dispose()
