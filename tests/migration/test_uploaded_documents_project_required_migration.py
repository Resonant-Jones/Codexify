"""Real PostgreSQL/Alembic proof that empty migration replay does not
manufacture a default Project.

The historical ``d1a6b9f2c4e7_make_uploaded_documents_project_required``
revision unconditionally resolved or created the canonical ``General`` Project
even when no ``uploaded_documents.project_id IS NULL`` row existed. That side
effect on an empty migration-only database later forced
``d4e8f1a2b6c9_reconcile_legacy_local_project_owners`` into a
``project_ownership_reconciliation_unresolved`` abort because the manufactured
row became ``projects.user_id='local'`` with zero referencing threads.

This test proves the narrowed conditional behavior:

- on an empty migration replay with no NULL Project references, the
  revision must not invoke the default-Project resolution path;
- on a replay where legacy rows still need Project backfill, the
  revision must preserve its original resolution and backfill behavior;
- the ``uploaded_documents.project_id`` ``NOT NULL`` schema transition
  must still occur on both branches;
- the revision identity and downgrade behavior are unchanged.
"""

from __future__ import annotations

import importlib
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


REVISION_ID = "d1a6b9f2c4e7"
PREVIOUS_REVISION = "b7c1d9e0f2a3"
MIGRATION_MODULE = (
    "guardian.db.migrations.versions."
    "d1a6b9f2c4e7_make_uploaded_documents_project_required"
)


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
    database_name = f"codexify_uploads_required_{uuid.uuid4().hex[:10]}"
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


def _general_rows(connection) -> list[dict[str, object]]:
    return list(
        connection.execute(
            sa.text(
                "SELECT id, name FROM projects "
                "WHERE lower(trim(name)) = 'general' ORDER BY id"
            )
        )
        .mappings()
        .all()
    )


def _column_is_not_null(engine, table: str, column: str) -> bool:
    inspector = sa.inspect(engine)
    columns = inspector.get_columns(table)
    for entry in columns:
        if entry["name"] == column:
            return not bool(entry.get("nullable", True))
    raise AssertionError(f"Column {table}.{column} not present")


@pytest.mark.integration
def test_revision_identity_is_preserved() -> None:
    migration = importlib.import_module(MIGRATION_MODULE)
    assert migration.revision == REVISION_ID
    assert migration.down_revision == "b7c1d9e0f2a3"
    assert migration.branch_labels in (None, "")
    assert migration.branch_labels is None or migration.branch_labels == ""
    assert migration.depends_on is None


@pytest.mark.integration
def test_empty_replay_does_not_manufacture_general_project(temporary_postgres):
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, PREVIOUS_REVISION)

    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM uploaded_documents "
                    "WHERE project_id IS NULL"
                )
            ).scalar_one()
            == 0
        )
        assert _general_rows(connection) == []

    _upgrade_to(config, REVISION_ID)

    with engine.connect() as connection:
        assert _general_rows(connection) == []

    assert _column_is_not_null(engine, "uploaded_documents", "project_id")
    engine.dispose()


@pytest.mark.integration
def test_empty_replay_keeps_alter_column_invocation(temporary_postgres, monkeypatch):
    """The NOT NULL schema transition must still occur on the empty branch."""

    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, PREVIOUS_REVISION)

    migration = importlib.import_module(MIGRATION_MODULE)
    invocation_state: dict[str, int] = {
        "alter_column": 0,
        "resolve_default_project_id": 0,
    }
    original_alter_column = migration.op.alter_column
    original_resolve = migration._resolve_default_project_id

    def spy_alter_column(*args, **kwargs):
        invocation_state["alter_column"] += 1
        return original_alter_column(*args, **kwargs)

    def spy_resolve(bind):
        invocation_state["resolve_default_project_id"] += 1
        return original_resolve(bind)

    monkeypatch.setattr(migration.op, "alter_column", spy_alter_column)
    monkeypatch.setattr(migration, "_resolve_default_project_id", spy_resolve)

    _upgrade_to(config, REVISION_ID)

    assert invocation_state["resolve_default_project_id"] == 0
    assert invocation_state["alter_column"] >= 1
    assert _column_is_not_null(engine, "uploaded_documents", "project_id")
    engine.dispose()


@pytest.mark.integration
def test_legacy_backfill_still_creates_general_and_backfills_nulls(
    temporary_postgres,
):
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, PREVIOUS_REVISION)

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO uploaded_documents "
                "(id, filename, filesize, mime_type, src_url, project_id) "
                "VALUES "
                "('legacy-orphan-1', 'legacy-orphan-1.txt', 1024, 'text/plain', "
                "'mem://legacy-orphan-1', NULL), "
                "('legacy-orphan-2', 'legacy-orphan-2.txt', 2048, 'text/plain', "
                "'mem://legacy-orphan-2', NULL)"
            )
        )

    _upgrade_to(config, REVISION_ID)

    with engine.connect() as connection:
        general = _general_rows(connection)
        assert len(general) == 1
        general_id = int(general[0]["id"])

        project_ids = list(
            connection.execute(
                sa.text(
                    "SELECT DISTINCT project_id FROM uploaded_documents "
                    "WHERE id IN ('legacy-orphan-1', 'legacy-orphan-2')"
                )
            ).scalars()
        )
        assert project_ids == [general_id]
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM uploaded_documents "
                    "WHERE project_id IS NULL"
                )
            ).scalar_one()
            == 0
        )

    assert _column_is_not_null(engine, "uploaded_documents", "project_id")
    engine.dispose()


@pytest.mark.integration
def test_downgrade_relaxes_not_null_without_resurrecting_general(
    temporary_postgres,
):
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, PREVIOUS_REVISION)
    _upgrade_to(config, REVISION_ID)
    _downgrade_to(config, PREVIOUS_REVISION)

    with engine.connect() as connection:
        assert _general_rows(connection) == []
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM uploaded_documents "
                    "WHERE project_id IS NULL"
                )
            ).scalar_one()
            == 0
        )

    engine.dispose()
