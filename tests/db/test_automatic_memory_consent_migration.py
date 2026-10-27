"""Disposable PostgreSQL proof for the automatic collection consent migration.

Runs against a real PostgreSQL database migrated to the canonical Alembic
head, so the migration itself, the database constraint, and the durable
consent read/write seam are proven together rather than simulated.

Requires ``TEST_DATABASE_URL``; the disposable database is created and
dropped again.  Synthetic account principals only.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from guardian.core.pgdb import PgDB
from guardian.services import iddb_settings_service

PREVIOUS_REVISION = "f0d7c4b2a198"
CONSENT_REVISION = "c59e4d1a28f0"

ACCOUNT_A = "pfp03b-pg-account-a"
ACCOUNT_B = "pfp03b-pg-account-b"


@pytest.fixture
def disposable_database(monkeypatch):
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")
    database_name = f"codexify_consent_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=database_name)
    with psycopg.connect(
        admin_url.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute(f"CREATE DATABASE {database_name}")
    config = Config(
        str(Path(__file__).resolve().parents[2] / "backend" / "alembic.ini")
    )
    config.set_main_option(
        "sqlalchemy.url",
        test_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    previous_factory = iddb_settings_service._SessionFactory
    try:
        yield config, test_url
    finally:
        iddb_settings_service._set_session_factory(previous_factory)
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {database_name}")


def _bind_service(engine) -> None:
    iddb_settings_service._set_session_factory(
        sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    )


def test_migration_preserves_existing_settings_and_defaults_to_unset(
    disposable_database,
):
    config, test_url = disposable_database
    command.upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(test_url)

    # A historical settings row written before the consent migration existed.
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO user_settings "
                "(user_id, memory_mode, diary_requires_unlock, "
                "allow_sensitive_modeling) "
                "VALUES (:uid, 'light', true, false)"
            ),
            {"uid": ACCOUNT_A},
        )

    command.upgrade(config, CONSENT_REVISION)

    with engine.connect() as connection:
        row = connection.execute(
            sa.text(
                "SELECT memory_mode, diary_requires_unlock, "
                "allow_sensitive_modeling, automatic_memory_suggestions, "
                "consent_policy_version, consent_recorded_by_user_id, "
                "consent_recorded_at, consent_updated_at "
                "FROM user_settings WHERE user_id = :uid"
            ),
            {"uid": ACCOUNT_A},
        ).mappings().one()

    # The historical identity settings are untouched.
    assert row["memory_mode"] == "light"
    assert row["diary_requires_unlock"] is True
    assert row["allow_sensitive_modeling"] is False
    # The consent columns default to the denying state.
    assert row["automatic_memory_suggestions"] == "unset"
    assert row["consent_policy_version"] == "1"
    assert row["consent_recorded_by_user_id"] is None
    assert row["consent_recorded_at"] is None
    assert row["consent_updated_at"] is None
    engine.dispose()


def test_migrated_accounts_default_to_unset_and_are_not_effective(
    disposable_database,
):
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    _bind_service(engine)

    record = iddb_settings_service.read_automatic_memory_suggestions_consent(
        ACCOUNT_A
    )
    assert record["state"] == "unset"
    assert record["effective"] is False
    assert (
        iddb_settings_service.is_automatic_memory_collection_enabled(ACCOUNT_A)
        is False
    )
    engine.dispose()


def test_database_constraint_rejects_an_invalid_consent_state(
    disposable_database,
):
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO user_settings "
                "(user_id, automatic_memory_suggestions, consent_policy_version) "
                "VALUES (:uid, 'unset', '1')"
            ),
            {"uid": ACCOUNT_A},
        )

    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO user_settings "
                    "(user_id, automatic_memory_suggestions, "
                    "consent_policy_version) "
                    "VALUES (:uid, 'bogus', '1')"
                ),
                {"uid": ACCOUNT_B},
            )
    engine.dispose()


def test_consent_is_durable_across_service_reinitialization(
    disposable_database,
):
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    _bind_service(engine)

    granted = iddb_settings_service.set_automatic_memory_suggestions_consent(
        ACCOUNT_A, "enabled", actor_user_id=ACCOUNT_A
    )
    assert granted["state"] == "enabled"
    assert granted["effective"] is True

    # A fresh engine and session factory models a service/session restart.
    restarted_engine = sa.create_engine(test_url)
    _bind_service(restarted_engine)
    reread = iddb_settings_service.read_automatic_memory_suggestions_consent(
        ACCOUNT_A
    )
    assert reread["state"] == "enabled"
    assert reread["effective"] is True
    assert reread["recorded_by_user_id"] == ACCOUNT_A
    assert reread["recorded_at"] is not None
    assert reread["updated_at"] is not None

    with restarted_engine.connect() as connection:
        row = connection.execute(
            sa.text(
                "SELECT automatic_memory_suggestions, consent_policy_version, "
                "consent_recorded_by_user_id FROM user_settings WHERE user_id = :uid"
            ),
            {"uid": ACCOUNT_A},
        ).mappings().one()
    assert row["automatic_memory_suggestions"] == "enabled"
    assert row["consent_policy_version"] == "1"
    assert row["consent_recorded_by_user_id"] == ACCOUNT_A
    restarted_engine.dispose()
    engine.dispose()


def test_no_cross_account_consent_inheritance(disposable_database):
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    _bind_service(engine)

    iddb_settings_service.set_automatic_memory_suggestions_consent(
        ACCOUNT_A, "enabled", actor_user_id=ACCOUNT_A
    )

    other = iddb_settings_service.read_automatic_memory_suggestions_consent(
        ACCOUNT_B
    )
    assert other["state"] == "unset"
    assert other["effective"] is False
    assert (
        iddb_settings_service.is_automatic_memory_collection_enabled(ACCOUNT_B)
        is False
    )
    engine.dispose()


def test_pausing_does_not_remove_historical_facts(disposable_database):
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    _bind_service(engine)

    iddb_settings_service.set_automatic_memory_suggestions_consent(
        ACCOUNT_A, "enabled", actor_user_id=ACCOUNT_A
    )
    repo = PgDB(test_url.render_as_string(hide_password=False))
    fact_id = repo.create_fact(
        ACCOUNT_A, "name", "Sam", status="candidate", confidence=0.5
    )
    assert fact_id

    iddb_settings_service.set_automatic_memory_suggestions_consent(
        ACCOUNT_A, "paused", actor_user_id=ACCOUNT_A
    )

    with engine.connect() as connection:
        remaining = connection.execute(
            sa.text(
                "SELECT count(*) FROM personal_facts "
                "WHERE user_id = :uid AND id = :fid"
            ),
            {"uid": ACCOUNT_A, "fid": fact_id},
        ).scalar_one()
    assert remaining == 1
    engine.dispose()


def test_downgrade_removes_the_consent_columns_and_keeps_settings(
    disposable_database,
):
    config, test_url = disposable_database
    command.upgrade(config, CONSENT_REVISION)
    engine = sa.create_engine(test_url)
    _bind_service(engine)

    iddb_settings_service.upsert_user_settings(
        ACCOUNT_A, {"memory_mode": "light"}
    )
    iddb_settings_service.set_automatic_memory_suggestions_consent(
        ACCOUNT_A, "enabled", actor_user_id=ACCOUNT_A
    )

    command.downgrade(config, PREVIOUS_REVISION)

    engine = sa.create_engine(test_url)
    columns = {
        column["name"]
        for column in sa.inspect(engine).get_columns("user_settings")
    }
    assert "automatic_memory_suggestions" not in columns
    assert "consent_policy_version" not in columns
    assert "consent_recorded_by_user_id" not in columns
    assert "consent_recorded_at" not in columns
    assert "consent_updated_at" not in columns

    with engine.connect() as connection:
        row = connection.execute(
            sa.text("SELECT memory_mode FROM user_settings WHERE user_id = :uid"),
            {"uid": ACCOUNT_A},
        ).scalar_one()
    assert row == "light"
    engine.dispose()
