"""Migration proof for the recipient-local read-cursor revision.

Upgrades ``f0d7c4b2a198`` → ``b3c8d1e5f7a2`` on a temporary Postgres
database, verifies that the recipient-local read-cursor table is created with
its exact shape, that a cursor row round-trips and is unique per
(reading profile, conversation), that a second participant may hold its own
cursor for the same conversation, and that the downgrade removes exactly this
revision's structures without touching existing messaging data.

Requires ``TEST_DATABASE_URL`` (or ``DATABASE_URL``) and psycopg; skips
otherwise.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None

import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

PREVIOUS_REVISION = "f0d7c4b2a198"
READ_CURSOR_REVISION = "b3c8d1e5f7a2"
CURSOR_TABLE = "direct_message_read_cursors"


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
def temporary_postgres(tmp_path, monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_readcursor_{uuid.uuid4().hex[:12]}"
    database_url = _database_url(base_url, database_name)

    try:
        admin_connection = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Unable to connect to admin database: {exc}")

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {database_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment specific
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

    try:
        yield config, database_url
    finally:
        cleanup_connection = psycopg.connect(admin_url, autocommit=True)
        try:
            with cleanup_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE datname = %s",
                    (database_name,),
                )
                cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        finally:
            cleanup_connection.close()


def _upgrade_to(config, revision: str) -> None:
    from alembic import command

    command.upgrade(config, revision)


def _downgrade_to(config, revision: str) -> None:
    from alembic import command

    command.downgrade(config, revision)


def _seed_messaging_state(engine):
    """Seed two profiles, one relationship, one conversation and one message."""
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO users (id, username, password_hash, role) VALUES "
                "('user-a', 'user-a', 'not-a-real-hash', 'guest'), "
                "('user-b', 'user-b', 'not-a-real-hash', 'guest')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO threadspace_nodes (node_id, name, status) "
                "VALUES ('node-local', 'Local Node', 'active')"
            )
        )
        profile_a = uuid.uuid4().hex
        profile_b = uuid.uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO user_profiles "
                "(user_id, profile_id, node_id, username, username_state, "
                "accent_color) VALUES "
                "('user-a', :profile_a, 'node-local', 'alice', 'active', "
                "'default'), "
                "('user-b', :profile_b, 'node-local', 'bob', 'active', "
                "'default')"
            ),
            {"profile_a": profile_a, "profile_b": profile_b},
        )
        pair_key = f"node-local:{profile_a}|node-local:{profile_b}"
        relationship_id = uuid.uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO direct_message_relationships "
                "(id, participant_pair_key) VALUES (:id, :pair_key)"
            ),
            {"id": relationship_id, "pair_key": pair_key},
        )
        for profile_id in (profile_a, profile_b):
            connection.execute(
                sa.text(
                    "INSERT INTO direct_message_relationship_participants "
                    "(id, relationship_id, node_id, profile_id) "
                    "VALUES (:id, :relationship_id, 'node-local', :profile_id)"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "relationship_id": relationship_id,
                    "profile_id": profile_id,
                },
            )
        conversation_id = uuid.uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO direct_message_conversations "
                "(id, kind, relationship_id) "
                "VALUES (:id, 'direct', :relationship_id)"
            ),
            {"id": conversation_id, "relationship_id": relationship_id},
        )
        message_id = uuid.uuid4().hex
        connection.execute(
            sa.text(
                "INSERT INTO direct_messages "
                "(id, conversation_id, sender_node_id, sender_profile_id, "
                "content_type, body, client_message_key) "
                "VALUES (:id, :conversation_id, 'node-local', :profile_id, "
                "'text/plain', 'body', 'key')"
            ),
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "profile_id": profile_a,
            },
        )
    return conversation_id, profile_a, profile_b, message_id


def test_read_cursor_migration_round_trip(temporary_postgres):
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    # ── Before the revision the table does not exist ───────────────────────
    _upgrade_to(config, PREVIOUS_REVISION)
    inspector = sa.inspect(engine)
    assert CURSOR_TABLE not in inspector.get_table_names()

    conversation_id, profile_a, profile_b, message_id = _seed_messaging_state(engine)

    # ── The revision creates exactly the participant-local cursor table ────
    _upgrade_to(config, READ_CURSOR_REVISION)

    inspector = sa.inspect(engine)
    assert CURSOR_TABLE in inspector.get_table_names()
    columns = {c["name"]: c for c in inspector.get_columns(CURSOR_TABLE)}
    assert set(columns) == {
        "conversation_id",
        "profile_id",
        "last_read_message_id",
        "updated_at",
    }
    assert columns["last_read_message_id"]["nullable"] is True
    primary_key = set(inspector.get_pk_constraint(CURSOR_TABLE)["constrained_columns"])
    assert primary_key == {"conversation_id", "profile_id"}
    assert any(
        index["name"] == "ix_direct_message_read_cursors_profile"
        for index in inspector.get_indexes(CURSOR_TABLE)
    )

    # ── A cursor row round-trips and is unique per (profile, conversation) ─
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO direct_message_read_cursors "
                "(conversation_id, profile_id, last_read_message_id) "
                "VALUES (:conversation_id, :profile_id, :message_id)"
            ),
            {
                "conversation_id": conversation_id,
                "profile_id": profile_b,
                "message_id": message_id,
            },
        )
        # The same reading profile cannot hold two cursors for one conversation.
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    sa.text(
                        "INSERT INTO direct_message_read_cursors "
                        "(conversation_id, profile_id, last_read_message_id) "
                        "VALUES (:conversation_id, :profile_id, :message_id)"
                    ),
                    {
                        "conversation_id": conversation_id,
                        "profile_id": profile_b,
                        "message_id": message_id,
                    },
                )
        # The other participant may hold its OWN cursor for the same
        # conversation: read state is per profile, not per pair.
        connection.execute(
            sa.text(
                "INSERT INTO direct_message_read_cursors "
                "(conversation_id, profile_id, last_read_message_id) "
                "VALUES (:conversation_id, :profile_id, NULL)"
            ),
            {
                "conversation_id": conversation_id,
                "profile_id": profile_a,
            },
        )

    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT profile_id, last_read_message_id "
                "FROM direct_message_read_cursors WHERE conversation_id = :cid"
            ),
            {"cid": conversation_id},
        ).fetchall()
        assert {row.profile_id for row in rows} == {profile_a, profile_b}
        by_profile = {row.profile_id: row.last_read_message_id for row in rows}
        assert by_profile[profile_b] == message_id
        assert by_profile[profile_a] is None

    # ── Downgrade removes exactly this revision's structures ──────────────
    _downgrade_to(config, PREVIOUS_REVISION)

    inspector = sa.inspect(engine)
    assert CURSOR_TABLE not in inspector.get_table_names()

    # Pre-existing messaging rows survive the downgrade intact.
    with engine.connect() as connection:
        kept = connection.execute(
            sa.text("SELECT body FROM direct_messages WHERE id = :id"),
            {"id": message_id},
        ).scalar_one()
        assert kept == "body"

    engine.dispose()
