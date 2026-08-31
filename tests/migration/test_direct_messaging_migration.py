"""Migration proof for the direct-messaging and social-identity revision.

Upgrades ``f41493d13761`` → ``a1b7c9d2e4f6`` on a temporary Postgres
database, verifies the social identity backfill and the durable DM schema,
exercises the database-side uniqueness constraints, and verifies the
downgrade removes exactly this revision's structures.

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

PREVIOUS_REVISION = "f41493d13761"
DIRECT_MESSAGING_REVISION = "a1b7c9d2e4f6"
DM_TABLES = {
    "direct_message_conversations",
    "direct_message_conversation_participants",
    "direct_messages",
}


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
    database_name = f"codexify_dm_{uuid.uuid4().hex[:12]}"
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


def _seed_existing_profiles(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES ('user-a', 'user-a', 'not-a-real-hash', 'guest'), "
                "('user-b', 'user-b', 'not-a-real-hash', 'guest'), "
                "('user-b-2', 'user-b-2', 'not-a-real-hash', 'guest'), "
                "('user-c', 'user-c', 'not-a-real-hash', 'guest')"
            )
        )
        # Pre-migration shape: no social identity columns exist yet.
        connection.execute(
            sa.text(
                "INSERT INTO user_profiles (user_id, accent_color) "
                "VALUES ('user-a', 'default')"
            )
        )


def test_direct_messaging_migration_round_trip(temporary_postgres):
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, PREVIOUS_REVISION)
    _seed_existing_profiles(engine)
    _upgrade_to(config, DIRECT_MESSAGING_REVISION)

    inspector = sa.inspect(engine)
    profile_columns = {
        column["name"] for column in inspector.get_columns("user_profiles")
    }
    assert {"profile_id", "node_id", "username", "username_state"} <= (profile_columns)

    # Existing users remain valid without a username; profile_id is
    # backfilled with a durable token and never derived from email.
    with engine.connect() as connection:
        row = connection.execute(
            sa.text(
                "SELECT profile_id, node_id, username, username_state "
                "FROM user_profiles WHERE user_id = 'user-a'"
            )
        ).one()
        assert row.profile_id and len(row.profile_id) == 32
        assert row.username is None
        assert row.username_state == "unset"

    # ── Node-scoped username uniqueness (database-side) ───────────────────
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO threadspace_nodes (node_id, name, status) "
                "VALUES ('node-local', 'Local Node', 'active'), "
                "('node-remote', 'Remote Node', 'active')"
            )
        )
        connection.execute(
            sa.text(
                "UPDATE user_profiles SET node_id = 'node-local', "
                "username = 'zac', username_state = 'active' "
                "WHERE user_id = 'user-a'"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO user_profiles "
                "(user_id, profile_id, node_id, username, username_state, "
                "accent_color) "
                "VALUES ('user-b', :profile_b, 'node-local', NULL, 'unset', "
                "'default')"
            ),
            {"profile_b": uuid.uuid4().hex},
        )

        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    sa.text(
                        "UPDATE user_profiles SET username = 'zac', "
                        "username_state = 'active' WHERE user_id = 'user-b'"
                    )
                )
        # The same username on a different node is legal (Node-scoped).
        connection.execute(
            sa.text(
                "INSERT INTO user_profiles "
                "(user_id, profile_id, node_id, username, username_state, "
                "accent_color) "
                "VALUES ('user-b-2', :profile_b2, 'node-remote', 'zac', "
                "'active', 'default')"
            ),
            {"profile_b2": uuid.uuid4().hex},
        )
        # Grammar and state checks reject invalid rows database-side.
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    sa.text(
                        "INSERT INTO user_profiles "
                        "(user_id, profile_id, node_id, username, username_state, "
                        "accent_color) "
                        "VALUES ('user-c', :profile_c, 'node-local', 'Bad Name', "
                        "'active', 'default')"
                    ),
                    {"profile_c": uuid.uuid4().hex},
                )

    # ── Durable DM domain ─────────────────────────────────────────────────
    with engine.begin() as connection:
        row_a = connection.execute(
            sa.text("SELECT profile_id FROM user_profiles WHERE user_id = 'user-a'")
        ).one()
        profile_a = row_a.profile_id

        conversation_id = uuid.uuid4().hex
        pair_key = f"node-local:{profile_a}|node-local:{uuid.uuid4().hex}"
        connection.execute(
            sa.text(
                "INSERT INTO direct_message_conversations "
                "(id, kind, participant_pair_key) VALUES "
                "(:id, 'direct', :pair_key)"
            ),
            {"id": conversation_id, "pair_key": pair_key},
        )
        # The canonical one-conversation-per-pair constraint is enforced.
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(
                    sa.text(
                        "INSERT INTO direct_message_conversations "
                        "(id, kind, participant_pair_key) VALUES "
                        "(:id, 'direct', :pair_key)"
                    ),
                    {"id": uuid.uuid4().hex, "pair_key": pair_key},
                )

    # ── Downgrade removes exactly this revision's structures ──────────────
    _downgrade_to(config, PREVIOUS_REVISION)

    inspector = sa.inspect(engine)
    profile_columns = {
        column["name"] for column in inspector.get_columns("user_profiles")
    }
    assert {"profile_id", "node_id", "username", "username_state"}.isdisjoint(
        profile_columns
    )
    assert DM_TABLES.isdisjoint(inspector.get_table_names())

    # Pre-existing rows survive the downgrade intact.
    with engine.connect() as connection:
        kept = connection.execute(
            sa.text("SELECT user_id FROM user_profiles WHERE user_id = 'user-a'")
        ).scalar_one()
        assert kept == "user-a"

    engine.dispose()
