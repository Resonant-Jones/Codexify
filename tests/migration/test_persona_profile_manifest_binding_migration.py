"""Alembic proof for account-owned Persona Profile manifest persistence.

The tests upgrade real PostgreSQL databases from the parent revision so the
legacy backfill, fail-closed ownership rule, and schema constraints are proven
against repository lineage rather than Base.metadata.create_all().
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover
    psycopg = None


PREVIOUS_REVISION = "b2c8d0e3f5a7"
PERSONA_MANIFEST_REVISION = "c3d9e1f4a6b8"
NEW_TABLES = {
    "persona_profile_revisions",
    "persona_profile_bindings",
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
def temporary_postgres(monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_persona_{uuid.uuid4().hex[:12]}"
    database_url = _database_url(base_url, database_name)

    try:
        admin_connection = psycopg.connect(admin_url, autocommit=True)
    except psycopg.Error as exc:  # pragma: no cover - environment specific
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


def _upgrade(config, revision: str) -> None:
    from alembic import command

    command.upgrade(config, revision)


def _insert_user(connection, account_id: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES (:id, :username, 'not-a-real-hash', 'guest')"
        ),
        {"id": account_id, "username": account_id},
    )


def _insert_legacy_profile(connection, profile_id: str) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO persona_profiles "
            "(id, name, system_prompt, model_provider, model_id, temperature) "
            "VALUES (:id, 'Legacy Persona', 'Legacy prompt.', 'openai', "
            "'gpt-4o', 0.35)"
        ),
        {"id": profile_id},
    )


@pytest.mark.integration
def test_single_account_backfill_creates_truthful_revision_and_binding(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            user_ids = list(
                connection.execute(
                    sa.text("SELECT id FROM users ORDER BY id")
                ).scalars()
            )
            assert len(user_ids) == 1
            sole_account_id = user_ids[0]
            _insert_legacy_profile(connection, "legacy-single")

        _upgrade(config, PERSONA_MANIFEST_REVISION)

        with engine.connect() as connection:
            profile = connection.execute(
                sa.text(
                    "SELECT id, current_revision FROM persona_profiles "
                    "WHERE id = 'legacy-single'"
                )
            ).one()
            assert profile.id == "legacy-single"
            assert profile.current_revision == 1

            revision = connection.execute(
                sa.text(
                    "SELECT revision, api_version, manifest_json "
                    "FROM persona_profile_revisions "
                    "WHERE profile_id = 'legacy-single'"
                )
            ).one()
            assert revision.revision == 1
            assert revision.api_version == "codexify.persona/v1"
            assert revision.manifest_json == {
                "apiVersion": "codexify.persona/v1",
                "profileIdentity": "legacy-single",
                "revision": 1,
                "identity": {"name": "Legacy Persona"},
                "prompt": {"systemPrompt": "Legacy prompt."},
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o",
                    "temperature": 0.35,
                },
            }

            owner = connection.execute(
                sa.text(
                    "SELECT owner_account_id FROM persona_profile_bindings "
                    "WHERE profile_id = 'legacy-single'"
                )
            ).scalar_one()
            assert owner == sole_account_id

            profile_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profiles")
            ).scalar_one()
            revision_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profile_revisions")
            ).scalar_one()
            binding_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profile_bindings")
            ).scalar_one()
            assert revision_count == profile_count
            assert binding_count == profile_count
    finally:
        engine.dispose()


@pytest.mark.integration
def test_multi_account_backfill_preserves_profiles_without_guessing_owner(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            _insert_user(connection, "account-b")
            user_count = connection.execute(
                sa.text("SELECT count(*) FROM users")
            ).scalar_one()
            assert user_count == 2
            _insert_legacy_profile(connection, "legacy-ambiguous")

        _upgrade(config, PERSONA_MANIFEST_REVISION)

        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text(
                        "SELECT current_revision FROM persona_profiles "
                        "WHERE id = 'legacy-ambiguous'"
                    )
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM persona_profile_revisions "
                        "WHERE profile_id = 'legacy-ambiguous'"
                    )
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM persona_profile_bindings "
                        "WHERE profile_id = 'legacy-ambiguous'"
                    )
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    sa.text("SELECT count(*) FROM persona_profile_bindings")
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_clean_upgrade_creates_one_valid_manifest_schema(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PERSONA_MANIFEST_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        inspector = sa.inspect(engine)
        assert NEW_TABLES <= set(inspector.get_table_names())
        profile_columns = {
            column["name"] for column in inspector.get_columns("persona_profiles")
        }
        assert "current_revision" in profile_columns
        revision_columns = {
            column["name"]
            for column in inspector.get_columns("persona_profile_revisions")
        }
        assert revision_columns == {
            "profile_id",
            "revision",
            "api_version",
            "manifest_json",
            "created_at",
        }
        binding_columns = {
            column["name"]
            for column in inspector.get_columns("persona_profile_bindings")
        }
        assert binding_columns == {
            "profile_id",
            "owner_account_id",
            "created_at",
            "updated_at",
        }

        profile_checks = {
            check["name"]
            for check in inspector.get_check_constraints("persona_profiles")
        }
        revision_checks = {
            check["name"]
            for check in inspector.get_check_constraints("persona_profile_revisions")
        }
        assert "persona_profiles_current_revision_check" in profile_checks
        assert "persona_profile_revisions_revision_check" in revision_checks

        revision_primary_key = inspector.get_pk_constraint("persona_profile_revisions")
        assert revision_primary_key["constrained_columns"] == [
            "profile_id",
            "revision",
        ]
        binding_primary_key = inspector.get_pk_constraint("persona_profile_bindings")
        assert binding_primary_key["constrained_columns"] == ["profile_id"]

        revision_foreign_keys = {
            (
                constraint["constrained_columns"][0],
                constraint["referred_table"],
                constraint["referred_columns"][0],
                constraint["options"].get("ondelete"),
            )
            for constraint in inspector.get_foreign_keys("persona_profile_revisions")
        }
        assert revision_foreign_keys == {
            ("profile_id", "persona_profiles", "id", "CASCADE")
        }
        binding_foreign_keys = {
            (
                constraint["constrained_columns"][0],
                constraint["referred_table"],
                constraint["referred_columns"][0],
                constraint["options"].get("ondelete"),
            )
            for constraint in inspector.get_foreign_keys("persona_profile_bindings")
        }
        assert binding_foreign_keys == {
            ("profile_id", "persona_profiles", "id", "CASCADE"),
            ("owner_account_id", "users", "id", "CASCADE"),
        }

        revision_indexes = {
            index["name"]
            for index in inspector.get_indexes("persona_profile_revisions")
        }
        binding_indexes = {
            index["name"] for index in inspector.get_indexes("persona_profile_bindings")
        }
        assert "ix_persona_profile_revisions_profile_created_at" in (revision_indexes)
        assert "ix_persona_profile_bindings_owner_account_id" in (binding_indexes)

        with engine.connect() as connection:
            assert (
                connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).scalar_one()
                == PERSONA_MANIFEST_REVISION
            )
            profile_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profiles")
            ).scalar_one()
            revision_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profile_revisions")
            ).scalar_one()
            binding_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profile_bindings")
            ).scalar_one()
            assert revision_count == profile_count
            assert binding_count == profile_count

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                sa.text(
                    "UPDATE persona_profiles SET current_revision = 0 "
                    "WHERE id = 'profile-1'"
                )
            )

        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO persona_profile_revisions "
                    "(profile_id, revision, api_version, manifest_json) "
                    "SELECT profile_id, revision, api_version, manifest_json "
                    "FROM persona_profile_revisions "
                    "WHERE profile_id = 'profile-1' AND revision = 1"
                )
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_zero_user_backfill_preserves_profiles_without_inventing_owner(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    _upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(database_url, future=True)
    try:
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM users"))
            assert (
                connection.execute(sa.text("SELECT count(*) FROM users")).scalar_one()
                == 0
            )

        _upgrade(config, PERSONA_MANIFEST_REVISION)

        with engine.connect() as connection:
            profile_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profiles")
            ).scalar_one()
            revision_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profile_revisions")
            ).scalar_one()
            binding_count = connection.execute(
                sa.text("SELECT count(*) FROM persona_profile_bindings")
            ).scalar_one()
            assert profile_count > 0
            assert revision_count == profile_count
            assert binding_count == 0
    finally:
        engine.dispose()
