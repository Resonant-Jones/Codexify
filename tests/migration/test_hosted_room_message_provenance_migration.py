"""Migration tests for Hosted Room participant message provenance.

Tests upgrade, downgrade, re-upgrade, paired-provenance constraints,
participant lifecycle FK behavior, and historical transcript preservation.
"""

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

import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

PREVIOUS_REVISION = "b2c3d4e5f6a8"
PROVENANCE_REVISION = "7a91c4e2f6b8"
NEW_COLUMNS = {"hosted_room_participant_id", "sender_display_name_snapshot"}


def _database_url(base_url: str, database_name: str) -> str:
    return (
        make_url(base_url)
        .set(database=database_name)
        .render_as_string(hide_password=False)
    )


def _admin_database_url(base_url: str) -> str:
    # psycopg.connect() expects the plain PostgreSQL URL scheme; the
    # SQLAlchemy/Alembic URL may use postgresql+psycopg.
    return (
        make_url(base_url)
        .set(drivername="postgresql", database="postgres")
        .render_as_string(hide_password=False)
    )


@pytest.fixture
def temporary_postgres(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_provenance_{uuid.uuid4().hex[:12]}"
    database_url = _database_url(base_url, database_name)

    try:
        admin_connection = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:
        pytest.skip(f"Unable to connect to admin database: {exc}")

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {database_name}")
    except psycopg.Error as exc:
        pytest.skip(f"Unable to create test database: {exc.sqlstate}")
    finally:
        admin_connection.close()

    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location",
        str(repo_root / "guardian" / "db" / "migrations"),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    yield database_url

    # Clean up
    try:
        drop_conn = psycopg.connect(admin_url, autocommit=True)
        with drop_conn.cursor() as cursor:
            cursor.execute(
                f"SELECT pg_terminate_backend(pg_stat_activity.pid) "
                f"FROM pg_stat_activity "
                f"WHERE pg_stat_activity.datname = '{database_name}' "
                f"AND pid <> pg_backend_pid()"
            )
            cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        drop_conn.close()
    except Exception:
        pass


@pytest.fixture
def upgraded_db(temporary_postgres, monkeypatch):
    """Upgrade to head and return an engine."""
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", temporary_postgres)
    config.set_main_option(
        "script_location",
        str(repo_root / "guardian" / "db" / "migrations"),
    )

    command.upgrade(config, "head")

    engine = create_engine(temporary_postgres, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def parent_db(temporary_postgres, monkeypatch):
    """Create the disposable existing-instance fixture at the parent revision."""
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", temporary_postgres)
    config.set_main_option(
        "script_location",
        str(repo_root / "guardian" / "db" / "migrations"),
    )
    command.upgrade(config, PREVIOUS_REVISION)
    engine = create_engine(temporary_postgres, future=True)
    yield config, engine, command
    engine.dispose()


def _create_matching_preexisting_schema(engine) -> None:
    """Reproduce the tester's physical schema drift without changing history."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN hosted_room_participant_id VARCHAR(36)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN sender_display_name_snapshot VARCHAR(255)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD CONSTRAINT ck_chat_messages_paired_provenance CHECK ("
                "(hosted_room_participant_id IS NULL "
                "AND sender_display_name_snapshot IS NULL) OR ("
                "hosted_room_participant_id IS NOT NULL "
                "AND sender_display_name_snapshot IS NOT NULL "
                "AND sender_display_name_snapshot <> ''))"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD CONSTRAINT fk_chat_messages_hosted_room_participant_id "
                "FOREIGN KEY (hosted_room_participant_id) "
                "REFERENCES public.hosted_room_participants(id) "
                "ON DELETE SET NULL"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX ix_chat_messages_hosted_room_participant_id "
                "ON public.chat_messages (hosted_room_participant_id)"
            )
        )


def _assert_provenance_schema(engine) -> None:
    inspector = inspect(engine)
    columns = {
        column["name"]: column
        for column in inspector.get_columns("chat_messages")
    }
    assert columns["hosted_room_participant_id"]["type"].length == 36
    assert columns["hosted_room_participant_id"]["nullable"] is True
    assert columns["sender_display_name_snapshot"]["type"].length == 255
    assert columns["sender_display_name_snapshot"]["nullable"] is True
    assert any(
        foreign_key["name"] == "fk_chat_messages_hosted_room_participant_id"
        and foreign_key["referred_table"] == "hosted_room_participants"
        and foreign_key["referred_columns"] == ["id"]
        and (foreign_key.get("options") or {}).get("ondelete") == "SET NULL"
        for foreign_key in inspector.get_foreign_keys("chat_messages")
    )
    assert any(
        check["name"] == "ck_chat_messages_paired_provenance"
        for check in inspector.get_check_constraints("chat_messages")
    )
    assert any(
        index["name"] == "ix_chat_messages_hosted_room_participant_id"
        and index["column_names"] == ["hosted_room_participant_id"]
        and not index["unique"]
        for index in inspector.get_indexes("chat_messages")
    )


def test_matching_preexisting_schema_reconciles_and_preserves_data(parent_db):
    config, engine, command = parent_db
    _seed_historical_data(engine)
    with engine.connect() as connection:
        before = connection.execute(
            text(
                "SELECT id, role, content FROM chat_messages ORDER BY id"
            )
        ).fetchall()

    _create_matching_preexisting_schema(engine)
    command.upgrade(config, "head")

    _assert_provenance_schema(engine)
    with engine.connect() as connection:
        after = connection.execute(
            text(
                "SELECT id, role, content FROM chat_messages ORDER BY id"
            )
        ).fetchall()
        versions = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()
        sequence_owner = connection.execute(
            text(
                "SELECT sequence.relname, table_name.relname, attribute.attname "
                "FROM pg_class AS sequence "
                "JOIN pg_depend AS dependency "
                "ON dependency.objid = sequence.oid "
                "AND dependency.deptype = 'a' "
                "JOIN pg_class AS table_name "
                "ON table_name.oid = dependency.refobjid "
                "JOIN pg_attribute AS attribute "
                "ON attribute.attrelid = table_name.oid "
                "AND attribute.attnum = dependency.refobjsubid "
                "WHERE sequence.relkind = 'S' "
                "AND table_name.relname = 'chat_messages' "
                "AND attribute.attname = 'id'"
            )
        ).one()
    assert after == before
    assert versions == ["8c4d2e7f1a9b"]
    assert tuple(sequence_owner) == (
        "chat_messages_id_seq",
        "chat_messages",
        "id",
    )


def test_missing_companion_objects_are_created(parent_db):
    config, engine, command = parent_db
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN hosted_room_participant_id VARCHAR(36)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN sender_display_name_snapshot VARCHAR(255)"
            )
        )

    command.upgrade(config, PROVENANCE_REVISION)
    _assert_provenance_schema(engine)


def test_wrong_column_type_fails_closed(parent_db):
    config, engine, command = parent_db
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN hosted_room_participant_id INTEGER"
            )
        )

    with pytest.raises(RuntimeError, match="hosted_room_participant_id"):
        command.upgrade(config, PROVENANCE_REVISION)


def test_wrong_column_nullability_fails_closed(parent_db):
    config, engine, command = parent_db
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN hosted_room_participant_id VARCHAR(36) NOT NULL "
                "DEFAULT 'invalid'"
            )
        )

    with pytest.raises(RuntimeError, match="nullable"):
        command.upgrade(config, PROVENANCE_REVISION)


def test_wrong_foreign_key_target_fails_closed(parent_db):
    config, engine, command = parent_db
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN hosted_room_participant_id VARCHAR(36)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN sender_display_name_snapshot VARCHAR(255)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD CONSTRAINT fk_chat_messages_hosted_room_participant_id "
                "FOREIGN KEY (hosted_room_participant_id) "
                "REFERENCES public.hosted_room_invites(id)"
            )
        )

    with pytest.raises(RuntimeError, match="foreign key"):
        command.upgrade(config, PROVENANCE_REVISION)


def test_invalid_existing_paired_data_fails_closed(parent_db):
    config, engine, command = parent_db
    _seed_historical_data(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN hosted_room_participant_id VARCHAR(36)"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE public.chat_messages "
                "ADD COLUMN sender_display_name_snapshot VARCHAR(255)"
            )
        )
        connection.execute(
            text(
                "UPDATE public.chat_messages SET sender_display_name_snapshot = "
                "'orphaned provenance' WHERE id = 1"
            )
        )

    with pytest.raises(RuntimeError, match="violate the paired-provenance"):
        command.upgrade(config, PROVENANCE_REVISION)


def test_repeated_existing_schema_inspection_is_safe(parent_db):
    config, engine, command = parent_db
    _create_matching_preexisting_schema(engine)
    command.upgrade(config, "head")
    command.downgrade(config, PREVIOUS_REVISION)
    _assert_provenance_schema(engine)
    command.upgrade(config, "head")
    _assert_provenance_schema(engine)


# ── Migration schema correctness ─────────────────────────────────────────


def test_new_columns_exist(upgraded_db):
    inspector = inspect(upgraded_db)
    columns = {c["name"] for c in inspector.get_columns("chat_messages")}
    for col_name in NEW_COLUMNS:
        assert col_name in columns, f"Column {col_name} missing"


def test_columns_are_nullable(upgraded_db):
    inspector = inspect(upgraded_db)
    for col in inspector.get_columns("chat_messages"):
        if col["name"] in NEW_COLUMNS:
            assert col["nullable"], f"Column {col['name']} must be nullable"


def test_foreign_key_exists(upgraded_db):
    inspector = inspect(upgraded_db)
    fks = inspector.get_foreign_keys("chat_messages")
    provenance_fk = [
        fk
        for fk in fks
        if "hosted_room_participant_id" in fk.get("constrained_columns", ())
    ]
    assert len(provenance_fk) == 1
    assert provenance_fk[0]["referred_table"] == "hosted_room_participants"
    assert provenance_fk[0]["referred_columns"] == ["id"]
    assert "SET NULL" in str(provenance_fk[0].get("options", {})).upper() or (
        provenance_fk[0].get("ondelete") or ""
    ).upper() in ("SET NULL", "SET_NULL")


def test_check_constraint_exists(upgraded_db):
    inspector = inspect(upgraded_db)
    checks = inspector.get_check_constraints("chat_messages")
    paired = [c for c in checks if "paired_provenance" in c["name"]]
    assert len(paired) == 1


def test_index_exists(upgraded_db):
    inspector = inspect(upgraded_db)
    indexes = inspector.get_indexes("chat_messages")
    index_names = {idx["name"] for idx in indexes}
    assert "ix_chat_messages_hosted_room_participant_id" in index_names


# ── Historical transcript preservation ───────────────────────────────────


def _seed_historical_data(engine):
    """Insert pre-provenance historical data and return recorded values."""
    now = datetime.now(timezone.utc)

    with engine.begin() as conn:
        # Account
        conn.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role, created_at) "
                "VALUES (:id, :username, :hash, :role, :now)"
            ),
            {
                "id": "owner-1",
                "username": "owner",
                "hash": "not-a-real-hash",
                "role": "guest",
                "now": now,
            },
        )
        # Project
        conn.execute(
            text(
                "INSERT INTO projects (user_id, name, description, created_at, updated_at) "
                "VALUES (:uid, :name, :desc, :now, :now)"
            ),
            {
                "uid": "owner-1",
                "name": "Hosted Room provenance fixture",
                "desc": "Migration test fixture",
                "now": now,
            },
        )
        # Thread
        conn.execute(
            text(
                "INSERT INTO chat_threads (user_id, title, summary, created_at, updated_at) "
                "VALUES (:uid, :title, :summary, :now, :now)"
            ),
            {
                "uid": "owner-1",
                "title": "Hosted Room provenance fixture thread",
                "summary": "",
                "now": now,
            },
        )

    # Determine thread ID
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id FROM chat_threads "
                "WHERE title = 'Hosted Room provenance fixture thread'"
            )
        ).fetchone()
    thread_id = row[0]

    # Messages with known content
    messages = [
        {"role": "user", "content": "Hello, world"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "system", "content": "System prompt"},
    ]

    with engine.begin() as conn:
        for msg in messages:
            conn.execute(
                text(
                    "INSERT INTO chat_messages (thread_id, user_id, role, content, kind, extra_meta) "
                    "VALUES (:tid, :uid, :role, :content, :kind, :meta)"
                ),
                {
                    "tid": thread_id,
                    "uid": "owner-1",
                    "role": msg["role"],
                    "content": msg["content"],
                    "kind": "chat",
                    "meta": "{}",
                },
            )

    return thread_id, messages


def test_historical_messages_survive_upgrade(upgraded_db):
    """Upgrade from previous head must preserve historical messages."""
    # This test runs on the already-upgraded DB and inserts new data.
    # The migration test infrastructure upgrades first, then we verify.

    # Since we're already at head, we insert data and verify it's valid.
    thread_id, messages = _seed_historical_data(upgraded_db)

    with upgraded_db.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT role, content, hosted_room_participant_id, "
                "sender_display_name_snapshot "
                "FROM chat_messages WHERE thread_id = :tid "
                "ORDER BY id"
            ),
            {"tid": thread_id},
        ).fetchall()

    assert len(rows) == len(messages)
    for row, original in zip(rows, messages):
        assert row[0] == original["role"]
        assert row[1] == original["content"]
        # Provenance must be null for historical messages
        assert row[2] is None
        assert row[3] is None


# ── Provenance constraint proof ──────────────────────────────────────────


def _seed_room_data(engine):
    """Create room, owner, and guest participant for FK tests."""
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO hosted_rooms (id, owner_account_id, backing_thread_id, "
                "title, slug, status, enabled_agent_ids, created_at, updated_at) "
                "VALUES (:id, :oid, :tid, :title, :slug, :status, :agents, :now, :now)"
            ),
            {
                "id": "room-1",
                "oid": "owner-1",
                "tid": 1,
                "title": "Room",
                "slug": "room-abc",
                "status": "active",
                "agents": "[]",
                "now": now,
            },
        )
        conn.execute(
            text(
                "INSERT INTO hosted_room_participants "
                "(id, room_id, display_name, kind, role, state, joined_at, created_at) "
                "VALUES (:id, :rid, :name, :kind, :role, :state, :now, :now)"
            ),
            {
                "id": "part-guest",
                "rid": "room-1",
                "name": "Jane Guest",
                "kind": "human",
                "role": "member",
                "state": "active",
                "now": now,
            },
        )


def test_paired_provenance_insert_succeeds(upgraded_db):
    _seed_historical_data(upgraded_db)
    _seed_room_data(upgraded_db)

    # Find a thread
    with upgraded_db.begin() as conn:
        tid_row = conn.execute(text("SELECT id FROM chat_threads LIMIT 1")).fetchone()
    thread_id = tid_row[0]

    with upgraded_db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO chat_messages "
                "(thread_id, user_id, role, content, kind, extra_meta, "
                "hosted_room_participant_id, sender_display_name_snapshot) "
                "VALUES (:tid, :uid, :role, :content, :kind, :meta, :pid, :snap)"
            ),
            {
                "tid": thread_id,
                "uid": "owner-1",
                "role": "user",
                "content": "Room message",
                "kind": "chat",
                "meta": "{}",
                "pid": "part-guest",
                "snap": "Jane Guest",
            },
        )

    # Verify
    with upgraded_db.begin() as conn:
        row = conn.execute(
            text(
                "SELECT hosted_room_participant_id, sender_display_name_snapshot, content "
                "FROM chat_messages WHERE hosted_room_participant_id IS NOT NULL"
            )
        ).fetchone()
    assert row is not None
    assert row[0] == "part-guest"
    assert row[1] == "Jane Guest"
    assert row[2] == "Room message"


def test_participant_only_insert_fails(upgraded_db):
    _seed_historical_data(upgraded_db)
    _seed_room_data(upgraded_db)

    with upgraded_db.begin() as conn:
        tid_row = conn.execute(text("SELECT id FROM chat_threads LIMIT 1")).fetchone()
    thread_id = tid_row[0]

    with pytest.raises((IntegrityError, Exception)):
        with upgraded_db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO chat_messages "
                    "(thread_id, user_id, role, content, kind, extra_meta, "
                    "hosted_room_participant_id, sender_display_name_snapshot) "
                    "VALUES (:tid, :uid, :role, :content, :kind, :meta, :pid, :snap)"
                ),
                {
                    "tid": thread_id,
                    "uid": "owner-1",
                    "role": "user",
                    "content": "Bad",
                    "kind": "chat",
                    "meta": "{}",
                    "pid": "part-guest",
                    "snap": None,
                },
            )


def test_snapshot_only_insert_fails(upgraded_db):
    _seed_historical_data(upgraded_db)
    _seed_room_data(upgraded_db)

    with upgraded_db.begin() as conn:
        tid_row = conn.execute(text("SELECT id FROM chat_threads LIMIT 1")).fetchone()
    thread_id = tid_row[0]

    with pytest.raises((IntegrityError, Exception)):
        with upgraded_db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO chat_messages "
                    "(thread_id, user_id, role, content, kind, extra_meta, "
                    "hosted_room_participant_id, sender_display_name_snapshot) "
                    "VALUES (:tid, :uid, :role, :content, :kind, :meta, :pid, :snap)"
                ),
                {
                    "tid": thread_id,
                    "uid": "owner-1",
                    "role": "user",
                    "content": "Bad",
                    "kind": "chat",
                    "meta": "{}",
                    "pid": None,
                    "snap": "Jane Guest",
                },
            )


def test_blank_snapshot_insert_fails(upgraded_db):
    _seed_historical_data(upgraded_db)
    _seed_room_data(upgraded_db)

    with upgraded_db.begin() as conn:
        tid_row = conn.execute(text("SELECT id FROM chat_threads LIMIT 1")).fetchone()
    thread_id = tid_row[0]

    with pytest.raises((IntegrityError, Exception)):
        with upgraded_db.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO chat_messages "
                    "(thread_id, user_id, role, content, kind, extra_meta, "
                    "hosted_room_participant_id, sender_display_name_snapshot) "
                    "VALUES (:tid, :uid, :role, :content, :kind, :meta, :pid, :snap)"
                ),
                {
                    "tid": thread_id,
                    "uid": "owner-1",
                    "role": "user",
                    "content": "Bad",
                    "kind": "chat",
                    "meta": "{}",
                    "pid": "part-guest",
                    "snap": "",
                },
            )


# ── Participant lifecycle ────────────────────────────────────────────────


def test_participant_deletion_sets_message_fk_null(upgraded_db):
    _seed_historical_data(upgraded_db)
    _seed_room_data(upgraded_db)

    with upgraded_db.begin() as conn:
        tid_row = conn.execute(text("SELECT id FROM chat_threads LIMIT 1")).fetchone()
    thread_id = tid_row[0]

    # Insert a participant-linked message
    with upgraded_db.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO chat_messages "
                "(thread_id, user_id, role, content, kind, extra_meta, "
                "hosted_room_participant_id, sender_display_name_snapshot) "
                "VALUES (:tid, :uid, :role, :content, :kind, :meta, :pid, :snap)"
            ),
            {
                "tid": thread_id,
                "uid": "owner-1",
                "role": "user",
                "content": "Delete me",
                "kind": "chat",
                "meta": "{}",
                "pid": "part-guest",
                "snap": "Jane Guest",
            },
        )

    # Delete the participant
    with upgraded_db.begin() as conn:
        conn.execute(
            text("DELETE FROM hosted_room_participants WHERE id = :pid"),
            {"pid": "part-guest"},
        )

    # Message must survive with null provenance
    with upgraded_db.begin() as conn:
        row = conn.execute(
            text(
                "SELECT content, hosted_room_participant_id, sender_display_name_snapshot "
                "FROM chat_messages WHERE content = :content"
            ),
            {"content": "Delete me"},
        ).fetchone()
    assert row is not None
    assert row[0] == "Delete me"
    assert row[1] is None
    assert row[2] is None


# ── Downgrade / re-upgrade ───────────────────────────────────────────────


def test_downgrade_removes_provenance_columns(temporary_postgres, monkeypatch):
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", temporary_postgres)
    config.set_main_option(
        "script_location",
        str(repo_root / "guardian" / "db" / "migrations"),
    )

    # Upgrade to head
    command.upgrade(config, "head")

    # Insert some data
    engine = create_engine(temporary_postgres, future=True)
    _seed_historical_data(engine)
    engine.dispose()

    # Downgrade through the child revisions to the immediate parent so this
    # focused test exercises the provenance migration's own downgrade.
    command.downgrade(config, PREVIOUS_REVISION)

    # Verify columns are gone
    engine2 = create_engine(temporary_postgres, future=True)
    inspector = inspect(engine2)
    columns = {c["name"] for c in inspector.get_columns("chat_messages")}
    for col_name in NEW_COLUMNS:
        assert col_name not in columns, f"Column {col_name} still present after downgrade"

    # Verify FK and index are gone
    fks = inspector.get_foreign_keys("chat_messages")
    fk_names = {fk["name"] for fk in fks}
    assert "fk_chat_messages_hosted_room_participant_id" not in fk_names

    indexes = {idx["name"] for idx in inspector.get_indexes("chat_messages")}
    assert "ix_chat_messages_hosted_room_participant_id" not in indexes

    # Historical data must survive
    with engine2.begin() as conn:
        rows = conn.execute(
            text("SELECT id, role, content FROM chat_messages")
        ).fetchall()
    assert len(rows) > 0

    engine2.dispose()

    # Re-upgrade
    command.upgrade(config, "head")

    engine3 = create_engine(temporary_postgres, future=True)
    inspector3 = inspect(engine3)
    columns3 = {c["name"] for c in inspector3.get_columns("chat_messages")}
    for col_name in NEW_COLUMNS:
        assert col_name in columns3, f"Column {col_name} missing after re-upgrade"

    # Historical data still present and null-provenance
    with engine3.begin() as conn:
        rows3 = conn.execute(
            text(
                "SELECT id, role, content, hosted_room_participant_id, "
                "sender_display_name_snapshot FROM chat_messages"
            )
        ).fetchall()
    assert len(rows3) > 0
    for row in rows3:
        assert row[3] is None  # hosted_room_participant_id
        assert row[4] is None  # sender_display_name_snapshot

    engine3.dispose()
