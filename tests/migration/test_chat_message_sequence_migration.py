"""PostgreSQL chat-message identity-sequence repair tests."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

PREVIOUS_REVISION = "8b02d5f3a7c9"
REPAIR_REVISION = "8c4d2e7f1a9b"


def _database_url(base_url: str, database_name: str) -> str:
    return (
        make_url(base_url)
        .set(database=database_name)
        .render_as_string(hide_password=False)
    )


def _admin_database_url(base_url: str) -> str:
    return (
        make_url(base_url)
        .set(drivername="postgresql", database="postgres")
        .render_as_string(hide_password=False)
    )


@pytest.fixture
def migration_database(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required")

    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        pytest.skip("alembic not installed")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_message_seq_{uuid.uuid4().hex[:12]}"
    database_url = _database_url(base_url, database_name)

    try:
        admin_connection = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:
        pytest.skip(f"Unable to connect to admin database: {exc}")

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{database_name}"')
    except psycopg.Error as exc:
        admin_connection.close()
        pytest.skip(f"Unable to create test database: {exc.sqlstate}")
    finally:
        if not admin_connection.closed:
            admin_connection.close()

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location",
        str(repo_root / "guardian" / "db" / "migrations"),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    command.upgrade(config, PREVIOUS_REVISION)
    engine = create_engine(database_url, future=True)
    yield database_url, config, command, engine

    engine.dispose()
    try:
        drop_connection = psycopg.connect(admin_url, autocommit=True)
        with drop_connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            cursor.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        drop_connection.close()
    except Exception:
        pass


def _seed_thread(engine) -> int:
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, username, password_hash, role, created_at) "
                "VALUES (:id, :username, :password_hash, :role, :created_at)"
            ),
            {
                "id": "sequence-test-user",
                "username": "sequence-test-user",
                "password_hash": "not-a-real-hash",
                "role": "guest",
                "created_at": now,
            },
        )
        thread_id = connection.execute(
            text(
                "INSERT INTO chat_threads "
                "(user_id, title, summary, created_at, updated_at) "
                "VALUES (:user_id, :title, :summary, :created_at, :updated_at) "
                "RETURNING id"
            ),
            {
                "user_id": "sequence-test-user",
                "title": "Sequence test thread",
                "summary": "",
                "created_at": now,
                "updated_at": now,
            },
        ).scalar_one()
    return int(thread_id)


def _insert_explicit_message(engine, *, thread_id: int, message_id: int) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO chat_messages "
                "(id, thread_id, user_id, role, content) "
                "VALUES (:id, :thread_id, :user_id, 'user', 'fixture row')"
            ),
            {
                "id": message_id,
                "thread_id": thread_id,
                "user_id": "sequence-test-user",
            },
        )


def _set_sequence(engine, value: int, is_called: bool = True) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "SELECT setval(" \
                "pg_get_serial_sequence('public.chat_messages', 'id'), "
                ":value, :is_called)"
            ),
            {"value": value, "is_called": is_called},
        )


def _sequence_state(engine) -> tuple[int, bool]:
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT last_value, is_called FROM chat_messages_id_seq")
        ).one()
    return int(row.last_value), bool(row.is_called)


def test_migration_repairs_stale_sequence_and_is_idempotent(
    migration_database,
):
    database_url, config, command, engine = migration_database
    thread_id = _seed_thread(engine)
    _insert_explicit_message(engine, thread_id=thread_id, message_id=900000)
    _set_sequence(engine, 1)

    command.upgrade(config, REPAIR_REVISION)
    assert _sequence_state(engine) == (900000, True)

    with engine.begin() as connection:
        generated_id = connection.execute(
            text(
                "INSERT INTO chat_messages "
                "(thread_id, user_id, role, content) "
                "VALUES (:thread_id, :user_id, 'assistant', 'generated row') "
                "RETURNING id"
            ),
            {
                "thread_id": thread_id,
                "user_id": "sequence-test-user",
            },
        ).scalar_one()
    assert int(generated_id) == 900001

    command.downgrade(config, PREVIOUS_REVISION)
    _insert_explicit_message(engine, thread_id=thread_id, message_id=900010)
    _set_sequence(engine, 900001)
    command.upgrade(config, REPAIR_REVISION)
    assert _sequence_state(engine) == (900010, True)


def test_restore_sequence_repair_never_lowers_sequence(migration_database):
    database_url, config, command, engine = migration_database
    command.upgrade(config, REPAIR_REVISION)
    thread_id = _seed_thread(engine)
    _insert_explicit_message(engine, thread_id=thread_id, message_id=910000)
    _set_sequence(engine, 990000)

    from guardian.core.pgdb import PgDB

    db = PgDB(database_url)
    with db._connect() as connection:
        with connection.cursor() as cursor:
            db._restore_account_export_sync_sequence(
                cursor,
                table_name="chat_messages",
                sequence_column="id",
            )

    assert _sequence_state(engine) == (990000, True)
