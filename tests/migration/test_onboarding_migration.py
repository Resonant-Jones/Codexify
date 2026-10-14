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
    database_name = f"codexify_onboarding_{uuid.uuid4().hex[:12]}"
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


def test_onboarding_upgrade_constraints_durable_state_and_downgrade(temporary_postgres):
    from alembic import command
    from sqlalchemy.orm import sessionmaker
    from guardian.db.models import User, UserOnboardingState, UserSettings
    from guardian.services import onboarding_service as service

    config, url = temporary_postgres
    command.upgrade(config, "c9f3e2a7b601")
    engine = sa.create_engine(url)
    before = set(sa.inspect(engine).get_table_names())
    command.upgrade(config, "8d41a0c2b7ef")
    assert set(sa.inspect(engine).get_table_names()) - before == {
        "user_onboarding_state"
    }
    factory = sessionmaker(engine)
    with factory() as session:
        session.add_all(
            [
                User(id=u, username=u, password_hash="unused")
                for u in ("onboarding-a", "onboarding-b")
            ]
        )
        session.commit()
        assert service.read_state(session, "onboarding-a") == service.DEFAULT_STATE
        assert session.get(UserOnboardingState, "onboarding-a") is None
        service.patch_state(
            session,
            "onboarding-a",
            {"status": "in_progress", "last_step_key": "identity"},
        )
    with factory() as session:
        result = service.patch_state(
            session, "onboarding-a", {"contextual_tips_enabled": False}
        )
        assert (
            result["status"] == "in_progress" and result["last_step_key"] == "identity"
        )
        assert service.read_state(session, "onboarding-b") == service.DEFAULT_STATE
        assert session.get(UserOnboardingState, "onboarding-b") is None
        assert session.get(UserSettings, "onboarding-a") is None
    with factory() as session:
        assert (
            service.read_state(session, "onboarding-a")["contextual_tips_enabled"]
            is False
        )
        with pytest.raises(IntegrityError):
            session.execute(
                sa.text(
                    "UPDATE user_onboarding_state SET status='done' WHERE user_id='onboarding-a'"
                )
            )
            session.commit()
        session.rollback()
    command.downgrade(config, "c9f3e2a7b601")
    assert set(sa.inspect(engine).get_table_names()) == before
    engine.dispose()
