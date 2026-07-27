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
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

PREVIOUS_REVISION = "a1c2d3e4f5b6"
HOSTED_ROOM_REVISION = "b2c3d4e5f6a7"
HOSTED_ROOM_TABLES = {
    "hosted_rooms",
    "hosted_room_invites",
    "hosted_room_participants",
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
    database_name = f"codexify_hosted_rooms_{uuid.uuid4().hex[:12]}"
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


def _seed_existing_chat_state(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                """
                INSERT INTO users (id, username, password_hash, role)
                VALUES (
                    'owner-account',
                    'room-owner',
                    'not-a-real-password-hash',
                    'guest'
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO projects (id, user_id, name, description)
                VALUES (901, 'owner-account', 'Existing project', 'Preserve me')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO chat_threads (id, user_id, project_id, title)
                VALUES (902, 'owner-account', 901, 'Existing thread')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO chat_threads (id, user_id, project_id, title)
                VALUES (904, 'owner-account', 901, 'Second existing thread')
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO chat_messages (
                    id,
                    thread_id,
                    user_id,
                    role,
                    content
                )
                VALUES (
                    903,
                    902,
                    'owner-account',
                    'user',
                    'Existing canonical message'
                )
                """
            )
        )


def _assert_existing_chat_state(engine) -> None:
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT name FROM projects WHERE id = 901")
            ).scalar_one()
            == "Existing project"
        )
        assert (
            connection.execute(
                sa.text("SELECT title FROM chat_threads WHERE id = 902")
            ).scalar_one()
            == "Existing thread"
        )
        assert (
            connection.execute(
                sa.text("SELECT content FROM chat_messages WHERE id = 903")
            ).scalar_one()
            == "Existing canonical message"
        )


def _reflect_hosted_room_tables(engine) -> dict[str, sa.Table]:
    metadata = sa.MetaData()
    return {
        table_name: sa.Table(table_name, metadata, autoload_with=engine)
        for table_name in HOSTED_ROOM_TABLES
    }


def _insert_valid_hosted_room_state(engine) -> None:
    tables = _reflect_hosted_room_tables(engine)
    with engine.begin() as connection:
        connection.execute(
            tables["hosted_rooms"].insert(),
            {
                "id": "room-1",
                "owner_account_id": "owner-account",
                "backing_thread_id": 902,
                "title": "Existing thread room",
                "slug": "existing-thread-room",
                "status": "active",
                "enabled_agent_ids": ["guardian", "luna"],
            },
        )
        connection.execute(
            tables["hosted_room_invites"].insert(),
            {
                "id": "invite-1",
                "room_id": "room-1",
                "intended_display_name": "Invited guest",
                "token_hash": "a" * 64,
                "status": "pending",
            },
        )
        connection.execute(
            tables["hosted_room_participants"].insert(),
            [
                {
                    "id": "participant-owner",
                    "room_id": "room-1",
                    "invitation_id": None,
                    "bound_account_id": "owner-account",
                    "display_name": "Owner",
                    "kind": "human",
                    "role": "owner",
                    "state": "active",
                },
                {
                    "id": "participant-member",
                    "room_id": "room-1",
                    "invitation_id": "invite-1",
                    "bound_account_id": None,
                    "display_name": "Guest",
                    "kind": "human",
                    "role": "member",
                    "state": "active",
                },
                {
                    "id": "participant-agent",
                    "room_id": "room-1",
                    "invitation_id": None,
                    "bound_account_id": None,
                    "display_name": "Guardian",
                    "kind": "agent",
                    "role": "agent",
                    "state": "active",
                },
            ],
        )


def _assert_insert_fails(engine, table: sa.Table, values: dict) -> None:
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(table.insert(), values)


@pytest.mark.integration
def test_hosted_room_migration_applies_to_a_clean_database(
    temporary_postgres,
) -> None:
    from alembic import command

    config, database_url = temporary_postgres
    command.upgrade(config, "head")

    engine = create_engine(database_url, future=True)
    try:
        inspector = inspect(engine)
        assert HOSTED_ROOM_TABLES <= set(inspector.get_table_names())
        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == HOSTED_ROOM_REVISION
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_hosted_room_migration_round_trip_preserves_existing_chat_state(
    temporary_postgres,
) -> None:
    from alembic import command

    config, database_url = temporary_postgres
    command.upgrade(config, PREVIOUS_REVISION)

    engine = create_engine(database_url, future=True)
    try:
        _seed_existing_chat_state(engine)
        _assert_existing_chat_state(engine)

        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert HOSTED_ROOM_TABLES <= set(inspector.get_table_names())

        room_columns = {
            column["name"] for column in inspector.get_columns("hosted_rooms")
        }
        assert {
            "id",
            "owner_account_id",
            "backing_thread_id",
            "title",
            "slug",
            "status",
            "enabled_agent_ids",
            "created_at",
            "updated_at",
            "closed_at",
        } == room_columns

        invite_columns = {
            column["name"] for column in inspector.get_columns("hosted_room_invites")
        }
        assert {
            "id",
            "room_id",
            "intended_display_name",
            "token_hash",
            "status",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "expired_at",
            "created_at",
            "updated_at",
        } == invite_columns
        assert {
            "token",
            "invite_token",
            "raw_token",
            "access_token",
            "bearer",
        }.isdisjoint(invite_columns)

        participant_columns = {
            column["name"]
            for column in inspector.get_columns("hosted_room_participants")
        }
        assert {
            "id",
            "room_id",
            "invitation_id",
            "bound_account_id",
            "display_name",
            "kind",
            "role",
            "state",
            "joined_at",
            "removed_at",
            "created_at",
        } == participant_columns

        expected_foreign_keys = {
            "hosted_rooms": {
                ("owner_account_id", "users", "id", "CASCADE"),
                ("backing_thread_id", "chat_threads", "id", "CASCADE"),
            },
            "hosted_room_invites": {
                ("room_id", "hosted_rooms", "id", "CASCADE"),
            },
            "hosted_room_participants": {
                ("room_id", "hosted_rooms", "id", "CASCADE"),
                (
                    "invitation_id",
                    "hosted_room_invites",
                    "id",
                    "SET NULL",
                ),
                ("bound_account_id", "users", "id", "SET NULL"),
            },
        }
        for table_name, expected in expected_foreign_keys.items():
            observed = {
                (
                    constraint["constrained_columns"][0],
                    constraint["referred_table"],
                    constraint["referred_columns"][0],
                    constraint["options"].get("ondelete"),
                )
                for constraint in inspector.get_foreign_keys(table_name)
            }
            assert observed == expected

        expected_uniques = {
            "hosted_rooms": {
                "uq_hosted_rooms_slug",
                "uq_hosted_rooms_backing_thread_id",
            },
            "hosted_room_invites": {
                "uq_hosted_room_invites_token_hash",
            },
            "hosted_room_participants": {
                "uq_hosted_room_participants_invitation_id",
            },
        }
        for table_name, expected in expected_uniques.items():
            observed = {
                constraint["name"]
                for constraint in inspector.get_unique_constraints(table_name)
            }
            assert expected <= observed

        expected_checks = {
            "hosted_rooms": {
                "hosted_rooms_status_check",
                "hosted_rooms_lifecycle_check",
                "hosted_rooms_slug_check",
                "hosted_rooms_enabled_agent_ids_size_check",
            },
            "hosted_room_invites": {
                "hosted_room_invites_status_check",
                "hosted_room_invites_lifecycle_check",
            },
            "hosted_room_participants": {
                "hosted_room_participants_kind_check",
                "hosted_room_participants_role_check",
                "hosted_room_participants_state_check",
                "hosted_room_participants_kind_role_check",
                "hosted_room_participants_lifecycle_check",
            },
        }
        for table_name, expected in expected_checks.items():
            observed = {
                constraint["name"]
                for constraint in inspector.get_check_constraints(table_name)
            }
            assert expected <= observed

        expected_indexes = {
            "hosted_rooms": {"ix_hosted_rooms_owner_account_id"},
            "hosted_room_invites": {"ix_hosted_room_invites_room_id"},
            "hosted_room_participants": {
                "ix_hosted_room_participants_room_id",
                "ix_hosted_room_participants_room_state",
            },
        }
        for table_name, expected in expected_indexes.items():
            observed = {index["name"] for index in inspector.get_indexes(table_name)}
            assert expected <= observed

        _insert_valid_hosted_room_state(engine)
        _assert_existing_chat_state(engine)
        tables = _reflect_hosted_room_tables(engine)

        _assert_insert_fails(
            engine,
            tables["hosted_rooms"],
            {
                "id": "room-duplicate-slug",
                "owner_account_id": "owner-account",
                "backing_thread_id": 904,
                "title": "Duplicate",
                "slug": "existing-thread-room",
                "status": "active",
                "enabled_agent_ids": [],
            },
        )
        _assert_insert_fails(
            engine,
            tables["hosted_rooms"],
            {
                "id": "room-duplicate-thread",
                "owner_account_id": "owner-account",
                "backing_thread_id": 902,
                "title": "Duplicate thread",
                "slug": "duplicate-thread",
                "status": "active",
                "enabled_agent_ids": [],
            },
        )
        _assert_insert_fails(
            engine,
            tables["hosted_rooms"],
            {
                "id": "room-invalid-status",
                "owner_account_id": "owner-account",
                "backing_thread_id": 904,
                "title": "Invalid",
                "slug": "invalid-status",
                "status": "paused",
                "enabled_agent_ids": [],
            },
        )
        _assert_insert_fails(
            engine,
            tables["hosted_room_invites"],
            {
                "id": "invite-duplicate-hash",
                "room_id": "room-1",
                "intended_display_name": "Other guest",
                "token_hash": "a" * 64,
                "status": "pending",
            },
        )
        _assert_insert_fails(
            engine,
            tables["hosted_room_participants"],
            {
                "id": "participant-duplicate-invite",
                "room_id": "room-1",
                "invitation_id": "invite-1",
                "display_name": "Duplicate guest",
                "kind": "human",
                "role": "member",
                "state": "active",
            },
        )
        _assert_insert_fails(
            engine,
            tables["hosted_room_participants"],
            {
                "id": "participant-invalid-role",
                "room_id": "room-1",
                "display_name": "Invalid agent",
                "kind": "agent",
                "role": "member",
                "state": "active",
            },
        )

        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT content FROM chat_messages WHERE id = 903")
                ).scalar_one()
                == "Existing canonical message"
            )

        engine.dispose()
        command.downgrade(config, PREVIOUS_REVISION)
        engine = create_engine(database_url, future=True)
        assert HOSTED_ROOM_TABLES.isdisjoint(set(inspect(engine).get_table_names()))
        _assert_existing_chat_state(engine)

        engine.dispose()
        command.upgrade(config, "head")
        engine = create_engine(database_url, future=True)
        assert HOSTED_ROOM_TABLES <= set(inspect(engine).get_table_names())
        _assert_existing_chat_state(engine)

        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == HOSTED_ROOM_REVISION
            )
    finally:
        engine.dispose()
