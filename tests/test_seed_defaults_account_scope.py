"""PostgreSQL proof for account-scoped default Project seeding."""

from __future__ import annotations

import importlib.util
import os
import socket
import subprocess
import time
import uuid
from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from sqlalchemy.engine import make_url


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_seed_defaults_module():
    script_path = REPO_ROOT / "backend" / "scripts" / "seed_defaults.py"
    spec = importlib.util.spec_from_file_location(
        "seed_defaults_account_scope_module",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load seed_defaults module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed_defaults = _load_seed_defaults_module()


def _database_url(base_url: str, database_name: str) -> str:
    return (
        make_url(base_url)
        .set(drivername="postgresql", database=database_name)
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
    container_name = f"codexify_seed_scope_{uuid.uuid4().hex[:12]}"
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
def seed_database(postgres_server: str) -> Generator[str, None, None]:
    database_name = f"codexify_seed_scope_{uuid.uuid4().hex[:12]}"
    admin_url = _database_url(postgres_server, "postgres")
    database_url = _database_url(postgres_server, database_name)

    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{database_name}"')

    try:
        with psycopg.connect(database_url) as connection:
            connection.execute(
                """
                CREATE TABLE users (
                    id VARCHAR(255) PRIMARY KEY,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(16) NOT NULL DEFAULT 'guest'
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE projects (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    icon VARCHAR(16),
                    identity_depth VARCHAR(16) NOT NULL DEFAULT 'light',
                    system_role VARCHAR(32),
                    archived_at TIMESTAMPTZ,
                    UNIQUE (user_id, name)
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX uq_projects_user_id_system_role
                ON projects (user_id, system_role)
                WHERE system_role IS NOT NULL
                """
            )
            connection.execute(
                """
                CREATE TABLE seed_project_refs (
                    id VARCHAR(64) PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES projects(id)
                )
                """
            )
            connection.commit()
        yield database_url
    finally:
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')


def _add_user(connection: psycopg.Connection, user_id: str) -> None:
    connection.execute(
        "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, %s)",
        (user_id, user_id, "not-a-real-hash"),
    )


def _add_project(
    connection: psycopg.Connection,
    *,
    user_id: str,
    name: str,
    description: str = "preserve this description",
    system_role: str | None = None,
) -> int:
    return int(
        connection.execute(
            """
            INSERT INTO projects (user_id, name, description, system_role)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, name, description, system_role),
        ).fetchone()[0]
    )


def _run_seed(monkeypatch: pytest.MonkeyPatch, database_url: str) -> int:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    return int(seed_defaults.main())


def _project_rows(database_url: str) -> list[tuple[object, ...]]:
    with psycopg.connect(database_url) as connection:
        return list(
            connection.execute(
                """
                SELECT id, user_id, name, description, system_role
                FROM projects
                ORDER BY id
                """
            ).fetchall()
        )


@pytest.mark.integration
def test_zero_users_creates_zero_projects(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _run_seed(monkeypatch, seed_database) == 0
    assert _project_rows(seed_database) == []


@pytest.mark.integration
def test_one_canonical_account_receives_owned_general(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    rows = _project_rows(seed_database)
    assert len(rows) == 1
    assert rows[0][1:] == (
        "account-a",
        "General",
        seed_defaults.DEFAULT_PROJECT_DESCRIPTION,
        "general",
    )


@pytest.mark.integration
def test_multiple_accounts_receive_distinct_owned_generals(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        _add_user(connection, "account-b")
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    rows = _project_rows(seed_database)
    assert len(rows) == 2
    assert rows[0][0] != rows[1][0]
    assert {(row[1], row[2], row[4]) for row in rows} == {
        ("account-a", "General", "general"),
        ("account-b", "General", "general"),
    }


@pytest.mark.integration
def test_legacy_local_user_never_receives_general(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "local")
        _add_user(connection, "account-a")
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    rows = _project_rows(seed_database)
    assert [row[1] for row in rows] == ["account-a"]


@pytest.mark.integration
def test_same_name_in_one_account_does_not_suppress_another(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        _add_user(connection, "account-b")
        existing_id = _add_project(
            connection,
            user_id="account-a",
            name="General",
            description="keep A",
            system_role="general",
        )
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    rows = _project_rows(seed_database)
    assert len(rows) == 2
    assert rows[0] == (
        existing_id,
        "account-a",
        "General",
        "keep A",
        "general",
    )
    assert rows[1][1:] == (
        "account-b",
        "General",
        seed_defaults.DEFAULT_PROJECT_DESCRIPTION,
        "general",
    )


@pytest.mark.integration
def test_seed_is_project_id_and_owner_idempotent(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        _add_user(connection, "account-b")
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    first = _project_rows(seed_database)
    assert _run_seed(monkeypatch, seed_database) == 0
    assert _project_rows(seed_database) == first


@pytest.mark.integration
def test_alias_promotion_is_account_scoped_and_reference_stable(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        _add_user(connection, "account-b")
        alias_id = _add_project(
            connection,
            user_id="account-a",
            name="Loose Threads",
            description="keep alias description",
        )
        unrelated_id = _add_project(
            connection,
            user_id="account-b",
            name="Workspace",
            description="keep unrelated description",
        )
        connection.execute(
            "INSERT INTO seed_project_refs (id, project_id) VALUES (%s, %s), (%s, %s)",
            ("account-a-ref", alias_id, "account-b-ref", unrelated_id),
        )
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    rows = _project_rows(seed_database)
    assert (
        alias_id,
        "account-a",
        "General",
        "keep alias description",
        "general",
    ) in rows
    assert (
        unrelated_id,
        "account-b",
        "Workspace",
        "keep unrelated description",
        None,
    ) in rows
    with psycopg.connect(seed_database) as connection:
        refs = connection.execute(
            "SELECT id, project_id FROM seed_project_refs ORDER BY id"
        ).fetchall()
    assert refs == [("account-a-ref", alias_id), ("account-b-ref", unrelated_id)]


@pytest.mark.integration
def test_every_creation_and_promotion_path_has_an_owner(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        _add_user(connection, "account-b")
        _add_project(connection, user_id="account-b", name="Loose Threads")
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    with psycopg.connect(seed_database) as connection:
        ownerless = connection.execute(
            "SELECT count(*) FROM projects WHERE user_id IS NULL"
        ).fetchone()[0]
    assert ownerless == 0
    assert {(row[1], row[4]) for row in _project_rows(seed_database)} == {
        ("account-a", "general"),
        ("account-b", "general"),
    }


@pytest.mark.integration
def test_existing_structural_general_is_stable_and_unique(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        existing_id = _add_project(
            connection,
            user_id="account-a",
            name="Home Base",
            description="do not overwrite",
            system_role="general",
        )
        connection.commit()

    assert _run_seed(monkeypatch, seed_database) == 0
    assert _run_seed(monkeypatch, seed_database) == 0
    assert _project_rows(seed_database) == [
        (
            existing_id,
            "account-a",
            "Home Base",
            "do not overwrite",
            "general",
        )
    ]


@pytest.mark.integration
def test_multiple_same_account_aliases_fail_closed_without_partial_seed(
    seed_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with psycopg.connect(seed_database) as connection:
        _add_user(connection, "account-a")
        _add_user(connection, "account-b")
        first_id = _add_project(
            connection,
            user_id="account-a",
            name="General",
        )
        second_id = _add_project(
            connection,
            user_id="account-a",
            name="Loose Threads",
        )
        connection.commit()

    before = _project_rows(seed_database)
    assert _run_seed(monkeypatch, seed_database) == 1
    assert _project_rows(seed_database) == before
    assert {row[0] for row in before} == {first_id, second_id}
