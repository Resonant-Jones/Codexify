# guardian/tests/core/test_pgdb_account_export_owner_columns.py
"""
Real PostgreSQL regression proving the production PgDB account-export seam
preserves canonical ``user_id`` ownership through Project and chat-message
export/restore round trips.

This test exercises the actual PgDB account-export readers and restore
helpers against a dedicated PostgreSQL 17.6 authority. It does not
duplicate any production SQL in test code.

Required environment:
    PostgreSQL 17.6 Homebrew
    /tmp/.s.PGSQL.55432
    codexify_test_runner / postgres
    CREATEDB=true

Use:

    export TEST_DATABASE_URL='postgresql://codexify_test_runner@/postgres?host=/tmp&port=55432'
    pytest -v guardian/tests/core/test_pgdb_account_export_owner_columns.py
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import psycopg
import pytest

from guardian.core.pgdb import PgDB

SOURCE_ACCOUNT = "ums04dr2-account"
TARGET_ACCOUNT = SOURCE_ACCOUNT
OTHER_ACCOUNT = "ums04dr2-other-account"
PROJECT_ID = 91001
THREAD_ID = 92001
MESSAGE_ID = 93001


def _admin_url() -> str:
    base = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if not base:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")
    return base


def _create_disposable_database(admin_url: str, name: str) -> str:
    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{name}"')
    # Build a per-database URL preserving query/host/port/user semantics.
    parts = admin_url.split("?", 1)
    base = parts[0].rsplit("/", 1)[0]
    suffix = ("?" + parts[1]) if len(parts) == 2 else ""
    return f"{base}/{name}{suffix}"


def _drop_database(admin_url: str, name: str) -> None:
    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid <> pg_backend_pid()",
                    (name,),
                )
                cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
    except Exception:
        pass


def _migrate_to_head(database_url: str) -> None:
    from alembic.command import upgrade
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[3]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    os.environ["DATABASE_URL"] = database_url
    os.environ["GUARDIAN_DATABASE_URL"] = database_url
    upgrade(config, "head")


def _seed_source(database_url: str) -> None:
    """Seed source DB with a Project, chat_thread, and chat_message owned by SOURCE_ACCOUNT."""
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES (%s, %s, 'not-a-real-hash', 'guest') "
                "ON CONFLICT (id) DO NOTHING",
                (SOURCE_ACCOUNT, SOURCE_ACCOUNT),
            )
            cur.execute(
                "INSERT INTO projects (id, user_id, name) VALUES (%s, %s, %s)",
                (PROJECT_ID, SOURCE_ACCOUNT, "R2 Owner Project"),
            )
            cur.execute(
                "INSERT INTO chat_threads (id, user_id, title, project_id) "
                "VALUES (%s, %s, %s, %s)",
                (THREAD_ID, SOURCE_ACCOUNT, "R2 Owner Thread", PROJECT_ID),
            )
            cur.execute(
                "INSERT INTO chat_messages "
                "(id, thread_id, user_id, role, content) "
                "VALUES (%s, %s, %s, 'user', %s)",
                (
                    MESSAGE_ID,
                    THREAD_ID,
                    SOURCE_ACCOUNT,
                    "remember this exactly",
                ),
            )
        conn.commit()


def _seed_target_account(database_url: str, account: str) -> None:
    """Bootstrap the target account row so FKs can resolve."""
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES (%s, %s, 'not-a-real-hash', 'guest') "
                "ON CONFLICT (id) DO NOTHING",
                (account, account),
            )
        conn.commit()


def _read_owner(
    database_url: str, table: str, pk_column: str, pk_value: int
) -> str | None:
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT user_id FROM {table} WHERE {pk_column} = %s",
                (pk_value,),
            )
            row = cur.fetchone()
    return row[0] if row else None


@pytest.fixture
def source_target_databases():
    admin_url = _admin_url()
    suffix = uuid.uuid4().hex[:10]
    source_name = f"ums04dr2_src_{suffix}"
    target_name = f"ums04dr2_tgt_{suffix}"
    source_url = _create_disposable_database(admin_url, source_name)
    target_url = _create_disposable_database(admin_url, target_name)
    try:
        _migrate_to_head(source_url)
        _migrate_to_head(target_url)
        _seed_source(source_url)
        _seed_target_account(target_url, TARGET_ACCOUNT)
        yield source_url, target_url
    finally:
        _drop_database(admin_url, source_name)
        _drop_database(admin_url, target_name)


def test_production_projects_export_carries_source_user_id(source_target_databases):
    source_url, _ = source_target_databases
    pgdb = PgDB(source_url)
    rows = pgdb.fetch_account_export_projects_for_user(SOURCE_ACCOUNT)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == PROJECT_ID
    assert row.get("user_id") == SOURCE_ACCOUNT


def test_production_chat_messages_export_carries_source_user_id(
    source_target_databases,
):
    source_url, _ = source_target_databases
    pgdb = PgDB(source_url)
    rows = pgdb.fetch_account_export_chat_messages_for_user(SOURCE_ACCOUNT)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == MESSAGE_ID
    assert row.get("user_id") == SOURCE_ACCOUNT


def test_production_bundle_chat_messages_carries_source_user_id(
    source_target_databases,
):
    source_url, _ = source_target_databases
    pgdb = PgDB(source_url)
    bundle = pgdb.fetch_account_export_bundle_for_user(SOURCE_ACCOUNT)
    messages = bundle.get("chat_messages") or []
    assert len(messages) == 1
    row = messages[0]
    assert row["id"] == MESSAGE_ID
    assert row.get("user_id") == SOURCE_ACCOUNT


def test_production_restore_persists_explicit_user_id(source_target_databases):
    source_url, target_url = source_target_databases
    pgdb_source = PgDB(source_url)
    pgdb_target = PgDB(target_url)

    project_rows = pgdb_source.fetch_account_export_projects_for_user(SOURCE_ACCOUNT)
    thread_rows = pgdb_source.fetch_account_export_chat_threads_for_user(SOURCE_ACCOUNT)
    message_rows = pgdb_source.fetch_account_export_chat_messages_for_user(
        SOURCE_ACCOUNT
    )

    assert project_rows and thread_rows and message_rows
    assert project_rows[0]["user_id"] == SOURCE_ACCOUNT
    assert thread_rows[0]["user_id"] == SOURCE_ACCOUNT
    assert message_rows[0]["user_id"] == SOURCE_ACCOUNT

    pgdb_target.restore_account_export_projects(
        project_rows, target_user_id=TARGET_ACCOUNT
    )
    pgdb_target.restore_account_export_chat_threads(thread_rows)
    pgdb_target.restore_account_export_chat_messages(
        message_rows, target_user_id=TARGET_ACCOUNT
    )

    target_project_owner = _read_owner(target_url, "projects", "id", PROJECT_ID)
    target_message_owner = _read_owner(target_url, "chat_messages", "id", MESSAGE_ID)

    assert target_project_owner is not None
    assert target_message_owner is not None
    assert target_project_owner == TARGET_ACCOUNT
    assert target_message_owner == TARGET_ACCOUNT


def test_restore_fails_closed_for_mismatched_project_owner(source_target_databases):
    source_url, target_url = source_target_databases
    pgdb_source = PgDB(source_url)
    pgdb_target = PgDB(target_url)

    project_rows = pgdb_source.fetch_account_export_projects_for_user(SOURCE_ACCOUNT)
    assert project_rows, "source must have a project row"
    # Inject a row whose owner is not admitted by the restore target mapping.
    tampered = [{**project_rows[0], "user_id": OTHER_ACCOUNT}]

    with pytest.raises(ValueError) as excinfo:
        pgdb_target.restore_account_export_projects(
            tampered, target_user_id=TARGET_ACCOUNT
        )

    msg = str(excinfo.value).lower()
    assert (
        "user_id" in msg or "mismatch" in msg or "ownership" in msg
    ), f"unexpected exception: {excinfo.value!r}"

    # And nothing must have been committed.
    owner = _read_owner(target_url, "projects", "id", PROJECT_ID)
    assert owner is None, f"tampered project row leaked into target: {owner!r}"


def test_restore_fails_closed_for_mismatched_chat_message_owner(
    source_target_databases,
):
    source_url, target_url = source_target_databases
    pgdb_source = PgDB(source_url)
    pgdb_target = PgDB(target_url)

    message_rows = pgdb_source.fetch_account_export_chat_messages_for_user(
        SOURCE_ACCOUNT
    )
    assert message_rows, "source must have a chat_message row"
    tampered = [{**message_rows[0], "user_id": OTHER_ACCOUNT}]

    with pytest.raises(ValueError) as excinfo:
        pgdb_target.restore_account_export_chat_messages(
            tampered, target_user_id=TARGET_ACCOUNT
        )

    msg = str(excinfo.value).lower()
    assert (
        "user_id" in msg or "mismatch" in msg or "ownership" in msg
    ), f"unexpected exception: {excinfo.value!r}"

    owner = _read_owner(target_url, "chat_messages", "id", MESSAGE_ID)
    assert owner is None, f"tampered chat_message row leaked into target: {owner!r}"
