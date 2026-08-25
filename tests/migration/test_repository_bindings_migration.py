"""Postgres round-trip proof for the Stage 2K.1 RepositoryBinding migration."""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover - environment specific
    psycopg = None

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError


BASELINE_REVISION = "c1a2b3c4d5e6"
REPOSITORY_BINDING_REVISION = "6e2b9c4a7d1f"


def _database_url(base_url: str, database_name: str) -> str:
    return make_url(base_url).set(
        drivername="postgresql+psycopg", database=database_name
    ).render_as_string(hide_password=False)


def _admin_database_url(base_url: str) -> str:
    return make_url(base_url).set(
        drivername="postgresql", database="postgres"
    ).render_as_string(hide_password=False)


@pytest.fixture
def migration_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[Config, Engine], None, None]:
    """Create and destroy one uniquely named Postgres database for this test."""
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required")

    database_name = f"codexify_repository_bindings_{uuid.uuid4().hex[:12]}"
    admin_url = _admin_database_url(base_url)
    database_url = _database_url(base_url, database_name)

    try:
        with psycopg.connect(admin_url, autocommit=True) as admin_connection:
            with admin_connection.cursor() as cursor:
                cursor.execute(f'CREATE DATABASE "{database_name}"')
    except Exception as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Unable to create temporary Postgres database: {exc}")

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repo_root / "guardian" / "db" / "migrations")
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    engine: Engine | None = None
    try:
        command.upgrade(config, BASELINE_REVISION)
        engine = create_engine(database_url, future=True)
        yield config, engine
    finally:
        if engine is not None:
            engine.dispose()
        try:
            with psycopg.connect(admin_url, autocommit=True) as admin_connection:
                with admin_connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = %s AND pid <> pg_backend_pid()",
                        (database_name,),
                    )
                    cursor.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        except Exception:
            # Do not hide a migration assertion behind cleanup failure; the
            # generated database name remains uniquely scoped to this test.
            pass


def _seed_preexisting_project(engine: Engine) -> tuple[int, dict[str, object]]:
    """Create a User/Project that existed before the new migration."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, username, password_hash, role) "
                "VALUES (:id, :username, :password_hash, :role)"
            ),
            {
                "id": "repository-binding-test-user",
                "username": "repository-binding-test-user",
                "password_hash": "not-a-real-password-hash",
                "role": "guest",
            },
        )
        project_id = connection.execute(
            text(
                "INSERT INTO projects "
                "(user_id, name, description, icon, identity_depth) "
                "VALUES (:user_id, :name, :description, :icon, :identity_depth) "
                "RETURNING id"
            ),
            {
                "user_id": "repository-binding-test-user",
                "name": "Repository binding migration fixture",
                "description": "must survive migration unchanged",
                "icon": "folder",
                "identity_depth": "light",
            },
        ).scalar_one()
        snapshot = connection.execute(
            text(
                "SELECT id, user_id, name, description, icon, identity_depth "
                "FROM projects WHERE id = :project_id"
            ),
            {"project_id": project_id},
        ).mappings().one()
    return int(project_id), dict(snapshot)


def _project_snapshot(engine: Engine, project_id: int) -> dict[str, object]:
    with engine.connect() as connection:
        snapshot = connection.execute(
            text(
                "SELECT id, user_id, name, description, icon, identity_depth "
                "FROM projects WHERE id = :project_id"
            ),
            {"project_id": project_id},
        ).mappings().one()
    return dict(snapshot)


@pytest.mark.integration
def test_repository_bindings_migration_round_trip(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    inspector = inspect(engine)

    assert "repository_bindings" not in inspector.get_table_names(schema="public")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == BASELINE_REVISION

    project_id, project_before = _seed_preexisting_project(engine)

    command.upgrade(config, REPOSITORY_BINDING_REVISION)
    inspector.clear_cache()
    assert "repository_bindings" in inspector.get_table_names(schema="public")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == REPOSITORY_BINDING_REVISION

    columns = {
        column["name"]
        for column in inspector.get_columns("repository_bindings", schema="public")
    }
    assert {
        "id",
        "project_id",
        "source_class",
        "canonical_root",
        "is_active",
        "provenance",
        "created_at",
        "updated_at",
    } <= columns

    foreign_keys = inspector.get_foreign_keys(
        "repository_bindings", schema="public"
    )
    project_fk = next(
        fk for fk in foreign_keys if fk["name"] == "fk_repository_bindings_project_id"
    )
    assert project_fk["constrained_columns"] == ["project_id"]
    assert project_fk["referred_table"] == "projects"
    assert project_fk["referred_columns"] == ["id"]
    assert str(project_fk.get("options", {}).get("ondelete", "")).upper() == "CASCADE"

    checks = {
        check["name"]: check.get("sqltext", "")
        for check in inspector.get_check_constraints(
            "repository_bindings", schema="public"
        )
    }
    assert "ck_repository_bindings_source_class" in checks
    assert "guardian_managed" in checks["ck_repository_bindings_source_class"]
    assert "external_linked" in checks["ck_repository_bindings_source_class"]

    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("repository_bindings", schema="public")
    }
    active_index = indexes["uq_repository_bindings_one_active_per_project"]
    assert active_index["unique"] is True
    predicate = active_index.get("dialect_options", {}).get("postgresql_where")
    assert predicate is not None
    assert "is_active" in str(predicate)
    assert "true" in str(predicate).lower()
    assert indexes["ix_repository_bindings_project_id"]["column_names"] == ["project_id"]

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM repository_bindings WHERE project_id = :project_id"),
            {"project_id": project_id},
        ).scalar_one() == 0
    assert _project_snapshot(engine, project_id) == project_before

    active_values = {
        "id": "binding-active",
        "project_id": project_id,
        "source_class": "external_linked",
        "canonical_root": "/authority-side/example",
        "is_active": True,
        "provenance": "{}",
    }
    insert_binding = text(
        "INSERT INTO repository_bindings "
        "(id, project_id, source_class, canonical_root, is_active, provenance) "
        "VALUES "
        "(:id, :project_id, :source_class, :canonical_root, :is_active, "
        "CAST(:provenance AS jsonb))"
    )
    with engine.begin() as connection:
        connection.execute(insert_binding, active_values)

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    insert_binding,
                    {**active_values, "id": "binding-second-active"},
                )
        finally:
            transaction.rollback()

    with engine.begin() as connection:
        connection.execute(
            insert_binding,
            {
                **active_values,
                "id": "binding-inactive-history",
                "is_active": False,
            },
        )

    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT count(*) FROM repository_bindings "
                "WHERE project_id = :project_id"
            ),
            {"project_id": project_id},
        ).scalar_one() == 2

    command.downgrade(config, BASELINE_REVISION)
    inspector.clear_cache()
    assert "repository_bindings" not in inspector.get_table_names(schema="public")
    assert _project_snapshot(engine, project_id) == project_before

    command.upgrade(config, REPOSITORY_BINDING_REVISION)
    inspector.clear_cache()
    assert "repository_bindings" in inspector.get_table_names(schema="public")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == REPOSITORY_BINDING_REVISION
