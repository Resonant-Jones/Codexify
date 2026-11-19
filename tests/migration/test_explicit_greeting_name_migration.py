"""Bounded parent-profile upgrade/downgrade proof on disposable stores."""

import importlib
import os

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

REVISION = "d2e7a9b4c1f6"
migration = importlib.import_module(
    "guardian.db.migrations.versions.d2e7a9b4c1f6_add_explicit_account_greeting_name"
)


@pytest.fixture(params=["sqlite", "postgres"])
def connection(request):
    url = "sqlite+pysqlite://"
    if request.param == "postgres":
        url = os.environ.get("GREETING_PROFILE_TEST_DATABASE_URL")
        if not url:
            pytest.skip("Disposable GREETING_PROFILE_TEST_DATABASE_URL required")
        parsed = sa.engine.make_url(url)
        assert (
            parsed.host == "127.0.0.1" and parsed.database == "codexify_greeting_proof"
        )
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    profile = sa.Table(
        "user_profiles",
        metadata,
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column("display_name", sa.String(255)),
        sa.Column("username", sa.String(32)),
    )
    with engine.connect() as conn:
        metadata.create_all(conn)
        conn.execute(
            profile.insert(),
            {
                "user_id": "synthetic-owner",
                "display_name": " Existing display ",
                "username": "opaque-identifier",
            },
        )
        conn.commit()
        try:
            yield conn
        finally:
            conn.rollback()
            metadata.drop_all(conn)
            conn.commit()
    engine.dispose()


def apply(connection, action):
    with Operations.context(MigrationContext.configure(connection)):
        action()


def test_upgrade_adds_only_null_choice_and_preserves_existing_values(connection):
    before = sa.inspect(connection).get_columns("user_profiles")
    apply(connection, migration.upgrade)
    after = sa.inspect(connection).get_columns("user_profiles")
    assert {c["name"] for c in after} - {c["name"] for c in before} == {"greeting_name"}
    column = next(c for c in after if c["name"] == "greeting_name")
    assert column["nullable"] and column["default"] is None
    assert connection.execute(
        sa.text("SELECT display_name, username, greeting_name FROM user_profiles")
    ).one() == (" Existing display ", "opaque-identifier", None)
    connection.execute(
        sa.text("UPDATE user_profiles SET greeting_name = :name"), {"name": "星"}
    )
    assert connection.scalar(sa.text("SELECT greeting_name FROM user_profiles")) == "星"


def test_downgrade_removes_only_choice_and_reupgrade_does_not_infer(connection):
    apply(connection, migration.upgrade)
    connection.execute(sa.text("UPDATE user_profiles SET greeting_name = 'Chosen'"))
    apply(connection, migration.downgrade)
    assert {c["name"] for c in sa.inspect(connection).get_columns("user_profiles")} == {
        "user_id",
        "display_name",
        "username",
    }
    assert connection.execute(
        sa.text("SELECT display_name, username FROM user_profiles")
    ).one() == (" Existing display ", "opaque-identifier")
    apply(connection, migration.upgrade)
    assert connection.scalar(sa.text("SELECT greeting_name FROM user_profiles")) is None


def test_new_revision_descends_from_serving_schema_without_extra_head():
    config = Config("backend/alembic.ini")
    config.set_main_option("script_location", "guardian/db/migrations")
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["a3f8c2d6e901"]
    assert scripts.get_revision(REVISION).down_revision == "ab71d5ce9604"
