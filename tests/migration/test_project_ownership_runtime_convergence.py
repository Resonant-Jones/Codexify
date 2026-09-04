"""Proof for canonical Project ownership runtime convergence migration."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover - environment specific
    psycopg = None


PREVIOUS_REVISION = "b2c8d0e3f5a7"
PROJECT_OWNERSHIP_REVISION = "c3d9e4f6a8b1"
MIGRATION_MODULE = (
    "guardian.db.migrations.versions."
    "c3d9e4f6a8b1_remove_project_description_owner_authority"
)


def _envelope(owner_id: str, description: str) -> str:
    return json.dumps(
        {
            "__codexify_project_owner__": True,
            "owner_user_id": owner_id,
            "description": description,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


class _FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return _FakeMappings(self._rows)


class _FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.updates: list[dict[str, object]] = []

    def execute(self, statement, parameters=None):
        sql = str(statement)
        if sql.startswith("SELECT"):
            return _FakeResult(self.rows)
        if sql.startswith("UPDATE"):
            self.updates.append(dict(parameters or {}))
            return _FakeResult([])
        raise AssertionError(f"Unexpected migration SQL: {sql}")


def test_migration_classifies_all_rows_before_safe_normalization(monkeypatch):
    migration = importlib.import_module(MIGRATION_MODULE)
    exact = "  exact text\nwith unicode café  "
    connection = _FakeConnection(
        [
            {"id": 1, "user_id": "account-a", "description": "plain"},
            {
                "id": 2,
                "user_id": "account-a",
                "description": _envelope("account-a", exact),
            },
            {
                "id": 3,
                "user_id": "local",
                "description": _envelope("local", "local exact"),
            },
            {"id": 4, "user_id": "local", "description": "local plain"},
        ]
    )
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    migration.upgrade()

    assert connection.updates == [
        {"description": exact, "project_id": 2},
        {"description": "local exact", "project_id": 3},
    ]


def test_migration_conflict_aborts_before_any_update(monkeypatch):
    migration = importlib.import_module(MIGRATION_MODULE)
    connection = _FakeConnection(
        [
            {
                "id": 1,
                "user_id": "account-a",
                "description": _envelope("account-a", "safe but later"),
            },
            {
                "id": 2,
                "user_id": "account-b",
                "description": _envelope("account-a", "conflict"),
            },
        ]
    )
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    with pytest.raises(RuntimeError, match="project_ownership_authority_conflict"):
        migration.upgrade()

    assert connection.updates == []


def test_downgrade_is_explicit_non_fabricating_no_op(monkeypatch):
    migration = importlib.import_module(MIGRATION_MODULE)
    connection = _FakeConnection([])
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    assert migration.downgrade() is None
    assert connection.updates == []


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
def temporary_postgres(monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_project_owner_{uuid.uuid4().hex[:10]}"
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


def _seed_users(connection) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) VALUES "
            "('account-a', 'project-owner-a', 'not-a-real-hash', 'guest'), "
            "('account-b', 'project-owner-b', 'not-a-real-hash', 'guest'), "
            "('local', 'project-owner-local', 'not-a-real-hash', 'guest')"
        )
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@pytest.mark.integration
def test_postgres_upgrade_preserves_ids_owners_relationships_and_descriptions(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)
    exact = "  exact text\nwith unicode café  "
    local_exact = "\tlocal text with whitespace\n"

    _upgrade_to(config, PREVIOUS_REVISION)
    with engine.begin() as connection:
        _seed_users(connection)
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, user_id, name, description) VALUES "
                "(901, 'account-a', 'Canonical fixture', 'plain text'), "
                "(902, 'account-a', 'Matching fixture', :matching), "
                "(903, 'local', 'Local matching fixture', :local_matching), "
                "(904, 'local', 'Local canonical fixture', 'local plain')"
            ),
            {
                "matching": _envelope("account-a", exact),
                "local_matching": _envelope("local", local_exact),
            },
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_threads (id, user_id, project_id, title) "
                "VALUES (911, 'account-b', 902, 'Preserved thread')"
            )
        )

    _upgrade_to(config, PROJECT_OWNERSHIP_REVISION)
    _upgrade_to(config, PROJECT_OWNERSHIP_REVISION)

    with engine.connect() as connection:
        projects = (
            connection.execute(
                sa.text(
                    "SELECT id, user_id, description FROM projects "
                    "WHERE id BETWEEN 901 AND 904 ORDER BY id"
                )
            )
            .mappings()
            .all()
        )
        thread = (
            connection.execute(
                sa.text(
                    "SELECT id, user_id, project_id FROM chat_threads WHERE id = 911"
                )
            )
            .mappings()
            .one()
        )
        current_revision = connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert [row["id"] for row in projects] == [901, 902, 903, 904]
    assert [row["user_id"] for row in projects] == [
        "account-a",
        "account-a",
        "local",
        "local",
    ]
    assert projects[0]["description"] == "plain text"
    assert projects[1]["description"] == exact
    assert len(projects[1]["description"]) == len(exact)
    assert _digest(projects[1]["description"]) == _digest(exact)
    assert projects[2]["description"] == local_exact
    assert projects[3]["description"] == "local plain"
    assert dict(thread) == {
        "id": 911,
        "user_id": "account-b",
        "project_id": 902,
    }
    assert current_revision == PROJECT_OWNERSHIP_REVISION

    _downgrade_to(config, PREVIOUS_REVISION)
    with engine.connect() as connection:
        descriptions = (
            connection.execute(
                sa.text(
                    "SELECT description FROM projects WHERE id IN (902, 903) ORDER BY id"
                )
            )
            .scalars()
            .all()
        )
    assert descriptions == [exact, local_exact]
    assert all("__codexify_project_owner__" not in value for value in descriptions)
    engine.dispose()


@pytest.mark.integration
def test_postgres_conflict_aborts_without_partial_cleanup(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)
    matching = _envelope("account-a", "would be safe")
    conflicting = _envelope("account-a", "must block")

    _upgrade_to(config, PREVIOUS_REVISION)
    with engine.begin() as connection:
        _seed_users(connection)
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, user_id, name, description) VALUES "
                "(921, 'account-a', 'Safe before conflict', :matching), "
                "(922, 'account-b', 'Blocking conflict', :conflicting)"
            ),
            {"matching": matching, "conflicting": conflicting},
        )

    with pytest.raises(RuntimeError, match="project_ownership_authority_conflict"):
        _upgrade_to(config, PROJECT_OWNERSHIP_REVISION)

    with engine.connect() as connection:
        descriptions = (
            connection.execute(
                sa.text(
                    "SELECT description FROM projects WHERE id IN (921, 922) ORDER BY id"
                )
            )
            .scalars()
            .all()
        )
        current_revision = connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert descriptions == [matching, conflicting]
    assert current_revision == PREVIOUS_REVISION
    engine.dispose()
