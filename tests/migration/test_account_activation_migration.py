"""Postgres round-trip proof for Guardian account activation persistence."""

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
PARENT_REVISION = "7e5a5fccf253"
ACTIVATION_REVISION = "a8d4c2f6b1e9"
TABLE_NAME = "account_activation_capabilities"


def _database_url(base_url: str, database_name: str, *, sqlalchemy: bool) -> str:
    driver = "postgresql+psycopg" if sqlalchemy else "postgresql"
    return (
        make_url(base_url)
        .set(drivername=driver, database=database_name)
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
    container_name = f"codexify_account_activation_{uuid.uuid4().hex[:12]}"
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
    database_name = f"account_activation_{uuid.uuid4().hex[:12]}"
    admin_url = _database_url(postgres_server, "postgres", sqlalchemy=False)
    sqlalchemy_url = _database_url(
        postgres_server, database_name, sqlalchemy=True
    )
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


def _user_rows(engine: Engine) -> list[tuple[str, str, str | None, str]]:
    with engine.connect() as connection:
        return [
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT id, username, email, role FROM users ORDER BY id"
                )
            )
        ]


def _revision(engine: Engine) -> str:
    with engine.connect() as connection:
        return str(
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        )


@pytest.mark.integration
def test_account_activation_migration_round_trip_preserves_users(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, username, email, password_hash, role) VALUES "
                "('operator@example.com', 'operator@example.com', "
                "'operator@example.com', 'hash-a', 'admin'), "
                "('existing@example.com', 'existing@example.com', "
                "'existing@example.com', 'hash-b', 'guest')"
            )
        )
    users_before = _user_rows(engine)
    assert TABLE_NAME not in inspect(engine).get_table_names(schema="public")

    command.upgrade(config, ACTIVATION_REVISION)
    inspector = inspect(engine)
    assert TABLE_NAME in inspector.get_table_names(schema="public")
    assert _revision(engine) == ACTIVATION_REVISION
    assert _user_rows(engine) == users_before

    columns = {column["name"]: column for column in inspector.get_columns(TABLE_NAME)}
    assert set(columns) == {
        "activation_id",
        "token_digest",
        "recipient_email",
        "intended_role",
        "created_by_user_id",
        "created_at",
        "expires_at",
        "consumed_at",
        "revoked_at",
        "resulting_user_id",
    }
    assert columns["token_digest"]["nullable"] is False
    assert columns["resulting_user_id"]["nullable"] is True

    unique_constraints = {
        constraint["name"]: tuple(constraint.get("column_names") or ())
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    assert unique_constraints[
        "uq_account_activation_capabilities_token_digest"
    ] == ("token_digest",)
    indexes = {
        index["name"]: tuple(index.get("column_names") or ())
        for index in inspector.get_indexes(TABLE_NAME)
    }
    assert indexes[
        "ix_account_activation_capabilities_recipient_lifecycle"
    ] == ("recipient_email", "consumed_at", "revoked_at", "expires_at")
    checks = {
        check["name"] for check in inspector.get_check_constraints(TABLE_NAME)
    }
    assert {
        "account_activation_capabilities_role_check",
        "account_activation_capabilities_expiry_check",
        "account_activation_capabilities_consumption_check",
        "account_activation_capabilities_terminal_state_check",
    } <= checks

    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO account_activation_capabilities "
                "(activation_id, token_digest, recipient_email, intended_role, "
                "created_by_user_id, created_at, expires_at) VALUES "
                "('activation-1', :digest, 'new@example.com', 'guest', "
                "'operator@example.com', now(), now() + interval '1 hour')"
            ),
            {"digest": "a" * 64},
        )

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO account_activation_capabilities "
                        "(activation_id, token_digest, recipient_email, "
                        "intended_role, created_by_user_id, created_at, expires_at) "
                        "VALUES ('activation-2', :digest, 'other@example.com', "
                        "'owner', 'operator@example.com', now(), "
                        "now() + interval '1 hour')"
                    ),
                    {"digest": "b" * 64},
                )
        finally:
            transaction.rollback()

    command.downgrade(config, PARENT_REVISION)
    assert TABLE_NAME not in inspect(engine).get_table_names(schema="public")
    assert _revision(engine) == PARENT_REVISION
    assert _user_rows(engine) == users_before

    command.upgrade(config, ACTIVATION_REVISION)
    assert TABLE_NAME in inspect(engine).get_table_names(schema="public")
    assert _revision(engine) == ACTIVATION_REVISION
    assert _user_rows(engine) == users_before
