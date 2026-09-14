"""Postgres proof for account-scoped Project display-name uniqueness."""

from __future__ import annotations

import os
import socket
import subprocess
import time
import uuid
from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError


REPO_ROOT = Path(__file__).resolve().parents[2]
PARENT_REVISION = "f6b0d3e8c5a2"
PROJECT_NAME_SCOPE_REVISION = "7e5a5fccf253"
ACCOUNT_PROJECT_NAME_UNIQUE = "uq_projects_user_id_name"
ROLE_UNIQUE_INDEX = "uq_projects_user_id_system_role"
DOWNGRADE_DUPLICATE_ERROR = "project_name_scope_downgrade_cross_account_duplicates"


def _database_url(base_url: str, database_name: str, *, sqlalchemy: bool) -> str:
    driver = "postgresql+psycopg" if sqlalchemy else "postgresql"
    return (
        make_url(base_url)
        .set(
            drivername=driver,
            database=database_name,
        )
        .render_as_string(hide_password=False)
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def postgres_server() -> Generator[str, None, None]:
    configured_url = os.getenv("TEST_DATABASE_URL")
    if configured_url:
        yield configured_url
        return

    port = _free_port()
    container_name = f"codexify_project_name_scope_{uuid.uuid4().hex[:12]}"
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                container_name,
                "--env",
                "POSTGRES_USER=postgres",
                "--env",
                "POSTGRES_PASSWORD=postgres",
                "--env",
                "POSTGRES_DB=postgres",
                "--publish",
                f"127.0.0.1:{port}:5432",
                "postgres:15",
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ) as exc:
        pytest.fail(f"unable to start disposable Postgres: {exc}")

    base_url = f"postgresql://postgres:postgres@127.0.0.1:{port}/postgres"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(base_url):
                break
        except psycopg.Error:
            time.sleep(0.5)
    else:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            timeout=30,
        )
        pytest.fail("disposable Postgres did not become ready")

    try:
        yield base_url
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            timeout=30,
        )


@pytest.fixture
def migration_database(
    postgres_server: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[Config, Engine], None, None]:
    database_name = f"codexify_project_name_scope_{uuid.uuid4().hex[:12]}"
    admin_url = _database_url(postgres_server, "postgres", sqlalchemy=False)
    sqlalchemy_url = _database_url(postgres_server, database_name, sqlalchemy=True)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)

    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{database_name}"')

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)
    config.set_main_option(
        "script_location",
        str(REPO_ROOT / "guardian" / "db" / "migrations"),
    )
    monkeypatch.setenv("DATABASE_URL", sqlalchemy_url)

    engine: Engine | None = None
    try:
        command.upgrade(config, PARENT_REVISION)
        engine = create_engine(sqlalchemy_url, future=True)
        yield config, engine
    finally:
        if engine is not None:
            engine.dispose()
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')


def _unique_constraints(engine: Engine) -> dict[str, tuple[str, ...]]:
    return {
        str(constraint["name"]): tuple(constraint.get("column_names") or ())
        for constraint in inspect(engine).get_unique_constraints(
            "projects", schema="public"
        )
    }


def _project_snapshot(engine: Engine) -> list[dict[str, object]]:
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT id, user_id, name, description, system_role "
                    "FROM projects ORDER BY id"
                )
            ).mappings()
        ]


def _revision(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        )


def _seed_accounts(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role) VALUES "
                "('account-a', 'account-a', 'not-a-real-hash', 'guest'), "
                "('account-b', 'account-b', 'not-a-real-hash', 'guest')"
            )
        )


def _insert_project(
    engine: Engine,
    *,
    user_id: str,
    name: str,
    system_role: str | None = None,
) -> int:
    with engine.begin() as connection:
        return int(
            connection.execute(
                text(
                    "INSERT INTO projects "
                    "(user_id, name, description, icon, identity_depth, system_role) "
                    "VALUES (:user_id, :name, :description, 'folder', 'light', "
                    ":system_role) RETURNING id"
                ),
                {
                    "user_id": user_id,
                    "name": name,
                    "description": f"preserve:{user_id}:{name}",
                    "system_role": system_role,
                },
            ).scalar_one()
        )


def _assert_insert_rejected(
    engine: Engine,
    *,
    user_id: str,
    name: str,
    system_role: str | None = None,
) -> None:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO projects "
                        "(user_id, name, description, icon, identity_depth, "
                        "system_role) VALUES "
                        "(:user_id, :name, 'must not persist', 'folder', "
                        "'light', :system_role)"
                    ),
                    {
                        "user_id": user_id,
                        "name": name,
                        "system_role": system_role,
                    },
                )
        finally:
            transaction.rollback()


@pytest.mark.integration
def test_project_names_are_scoped_to_account_after_upgrade(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    _seed_accounts(engine)

    parent_constraints = _unique_constraints(engine)
    assert parent_constraints["projects_name_key"] == ("name",)
    _insert_project(engine, user_id="account-a", name="Shared Name")
    _assert_insert_rejected(engine, user_id="account-b", name="Shared Name")
    _insert_project(engine, user_id="account-a", name="Preserved Project")
    project_rows_before = _project_snapshot(engine)

    command.upgrade(config, PROJECT_NAME_SCOPE_REVISION)

    upgraded_constraints = _unique_constraints(engine)
    assert ("name",) not in upgraded_constraints.values()
    assert upgraded_constraints[ACCOUNT_PROJECT_NAME_UNIQUE] == (
        "user_id",
        "name",
    )
    indexes = {
        str(index["name"]): index
        for index in inspect(engine).get_indexes("projects", schema="public")
    }
    assert indexes[ROLE_UNIQUE_INDEX]["unique"] is True
    assert tuple(indexes[ROLE_UNIQUE_INDEX]["column_names"]) == (
        "user_id",
        "system_role",
    )
    assert _project_snapshot(engine) == project_rows_before
    assert _revision(engine) == PROJECT_NAME_SCOPE_REVISION

    _insert_project(engine, user_id="account-b", name="Shared Name")
    _insert_project(engine, user_id="account-a", name="Duplicate")
    _assert_insert_rejected(engine, user_id="account-a", name="Duplicate")

    _insert_project(
        engine,
        user_id="account-a",
        name="General",
        system_role="general",
    )
    _insert_project(
        engine,
        user_id="account-b",
        name="General",
        system_role="general",
    )
    _assert_insert_rejected(
        engine,
        user_id="account-a",
        name="Renamed General",
        system_role="general",
    )

    rows_before_failed_downgrade = _project_snapshot(engine)
    with pytest.raises(RuntimeError, match=DOWNGRADE_DUPLICATE_ERROR):
        command.downgrade(config, PARENT_REVISION)

    assert _revision(engine) == PROJECT_NAME_SCOPE_REVISION
    assert _project_snapshot(engine) == rows_before_failed_downgrade
    assert _unique_constraints(engine)[ACCOUNT_PROJECT_NAME_UNIQUE] == (
        "user_id",
        "name",
    )


@pytest.mark.integration
def test_downgrade_restores_global_uniqueness_without_mutating_projects(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    _seed_accounts(engine)
    _insert_project(
        engine,
        user_id="account-a",
        name="General",
        system_role="general",
    )
    _insert_project(engine, user_id="account-b", name="Unique B")

    command.upgrade(config, PROJECT_NAME_SCOPE_REVISION)
    project_rows_before = _project_snapshot(engine)
    command.downgrade(config, PARENT_REVISION)

    assert _revision(engine) == PARENT_REVISION
    assert _project_snapshot(engine) == project_rows_before
    downgraded_constraints = _unique_constraints(engine)
    assert downgraded_constraints["uq_projects_name"] == ("name",)
    assert ("user_id", "name") not in downgraded_constraints.values()
    indexes = {
        str(index["name"]): index
        for index in inspect(engine).get_indexes("projects", schema="public")
    }
    assert indexes[ROLE_UNIQUE_INDEX]["unique"] is True
