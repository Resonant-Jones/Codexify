"""Saved Widget storage: migration proof against disposable PostgreSQL.

Proves the canonical Saved Widget schema is created, is internally
consistent, agrees with the ORM metadata, and can be created, upgraded,
downgraded, and re-upgraded without disturbing existing chat data.

Every test here runs against a uniquely named disposable database built from
the repository's own Alembic migrations. No production data is used, no
existing database is reused, and the database is dropped afterwards.

Contract: docs/architecture/saved-widget-contract.md
Storage authority: docs/architecture/data-and-storage.md
ADR: docs/architecture/adr/102-saved-widget-identity-and-revision-boundary.md
"""

from __future__ import annotations

import os
import pathlib
import uuid
from typing import Any, Iterator

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from guardian.db.models import Base

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

WIDGETS_TABLE = "saved_widgets"
REVISIONS_TABLE = "saved_widget_revisions"

#: The revision that introduced the Saved Widget schema.
SAVED_WIDGET_REVISION = "a6b9d2e4f701"

#: The revision immediately before it, which the migration must declare as
#: its parent.
PARENT_REVISION = "f0d7c4b2a198"


class _DisposablePostgres:
    """A disposable PostgreSQL database plus its Alembic configuration."""

    def __init__(
        self,
        config: Config,
        engine: sa.Engine,
        session_factory: Any,
        db_name: str,
    ) -> None:
        self.config = config
        self.engine = engine
        self.session_factory = session_factory
        self.db_name = db_name

    def upgrade(self, revision: str = "head") -> None:
        command.upgrade(self.config, revision)

    def downgrade(self, revision: str) -> None:
        command.downgrade(self.config, revision)

    def session(self):
        return self.session_factory()

    def scalar(self, statement: str, **params: Any) -> Any:
        with self.engine.connect() as connection:
            return connection.execute(sa.text(statement), params).scalar()


@pytest.fixture
def disposable_postgres(monkeypatch):
    """A disposable PostgreSQL database at no particular revision.

    The fixture creates the database and points Alembic at it; the test
    decides which revision to upgrade to.
    """
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_saved_widget_migration_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=db_name)

    with psycopg.connect(
        admin_url.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute(f"CREATE DATABASE {db_name}")

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        test_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    monkeypatch.setenv(
        "GUARDIAN_DATABASE_URL", test_url.render_as_string(hide_password=False)
    )

    engine = sa.create_engine(test_url)
    try:
        yield _DisposablePostgres(
            config, engine, sessionmaker(bind=engine), db_name
        )
        engine.dispose()
    finally:
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (db_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {db_name}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_existing_chat_rows(db: _DisposablePostgres) -> dict[str, Any]:
    """Insert ordinary chat rows on the pre-Saved-Widget schema.

    Raw SQL is used deliberately: the point of this test is that the
    migration leaves rows it never knew about exactly as they were.
    """
    with db.engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES (:id, :id, 'inert-test-hash', 'guest')"
            ),
            {"id": "migration-probe-account"},
        )
        thread_id = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title, summary) "
                "VALUES (:user_id, :title, '') RETURNING id"
            ),
            {"user_id": "migration-probe-account", "title": "Pre-existing thread"},
        ).scalar_one()
        message_id = connection.execute(
            sa.text(
                "INSERT INTO chat_messages (thread_id, user_id, role, content, kind) "
                "VALUES (:thread_id, :user_id, 'assistant', :content, 'chat') "
                "RETURNING id"
            ),
            {
                "thread_id": thread_id,
                "user_id": "migration-probe-account",
                "content": "pre-existing assistant content",
            },
        ).scalar_one()
        connection.execute(
            sa.text(
                "INSERT INTO chat_completion_attempts "
                "(request_id, backend_task_id, thread_id, turn_id, "
                " completed_message_id, accepted_at) "
                "VALUES (:request_id, :backend_task_id, :thread_id, :turn_id, "
                "        :message_id, now())"
            ),
            {
                "request_id": "req-migration-probe",
                "backend_task_id": "task-migration-probe",
                "thread_id": thread_id,
                "turn_id": "turn-migration-probe",
                "message_id": message_id,
            },
        )
    return {"thread_id": thread_id, "message_id": message_id}


def _chat_row_snapshot(db: _DisposablePostgres) -> dict[str, Any]:
    """Read back the pre-existing chat rows exactly as stored."""
    return {
        "users": db.scalar("SELECT count(*) FROM users"),
        "threads": db.scalar("SELECT count(*) FROM chat_threads"),
        "messages": db.scalar("SELECT count(*) FROM chat_messages"),
        "attempts": db.scalar("SELECT count(*) FROM chat_completion_attempts"),
        "message_content": db.scalar(
            "SELECT content FROM chat_messages ORDER BY id LIMIT 1"
        ),
        "attempt_request_id": db.scalar(
            "SELECT request_id FROM chat_completion_attempts ORDER BY request_id LIMIT 1"
        ),
    }


def _assert_column_parity(inspector) -> None:
    """The migrated schema and the ORM metadata must describe the same tables."""
    dialect = postgresql.dialect()
    for table_name in (WIDGETS_TABLE, REVISIONS_TABLE):
        db_columns = {c["name"]: c for c in inspector.get_columns(table_name)}
        meta_table = Base.metadata.tables[table_name]
        assert set(db_columns) == set(meta_table.columns.keys())
        for name, meta_column in meta_table.columns.items():
            # Both sides are rendered through the same dialect, so the
            # comparison reflects the stored DDL type rather than each
            # library's own repr.
            db_type = db_columns[name]["type"].compile(dialect=dialect)
            meta_type = meta_column.type.dialect_impl(dialect).compile(dialect=dialect)
            assert db_type == meta_type, f"{table_name}.{name}: {db_type} != {meta_type}"
            assert db_columns[name]["nullable"] == meta_column.nullable, (
                f"{table_name}.{name}: nullability differs"
            )


def _assert_constraint_parity(inspector) -> None:
    """Constraint and index names must match the ORM metadata."""
    for table_name in (WIDGETS_TABLE, REVISIONS_TABLE):
        meta_table = Base.metadata.tables[table_name]

        db_checks = {c["name"] for c in inspector.get_check_constraints(table_name)}
        meta_checks = {
            c.name
            for c in meta_table.constraints
            if isinstance(c, sa.CheckConstraint) and c.name
        }
        assert meta_checks <= db_checks, f"{table_name}: missing check constraints"

        db_fks = {c["name"] for c in inspector.get_foreign_keys(table_name)}
        meta_fks = {c.name for c in meta_table.foreign_key_constraints if c.name}
        assert meta_fks <= db_fks, f"{table_name}: missing foreign keys"

        db_indexes = {i["name"] for i in inspector.get_indexes(table_name)}
        meta_indexes = {i.name for i in meta_table.indexes}
        assert meta_indexes <= db_indexes, f"{table_name}: missing indexes"


# ---------------------------------------------------------------------------
# Migration identity
# ---------------------------------------------------------------------------


def test_the_migration_declares_the_verified_parent(disposable_postgres) -> None:
    """The new revision extends the previously verified head."""
    module = __import__(
        "guardian.db.migrations.versions."
        "a6b9d2e4f701_add_saved_widget_identity_and_revisions",
        fromlist=["revision", "down_revision"],
    )
    assert module.revision == SAVED_WIDGET_REVISION
    assert module.down_revision == PARENT_REVISION


def test_the_migration_is_the_single_head(disposable_postgres) -> None:
    """There is exactly one head, and it is the Saved Widget revision."""
    script = ScriptDirectory.from_config(disposable_postgres.config)
    assert tuple(script.get_heads()) == (SAVED_WIDGET_REVISION,)


# ---------------------------------------------------------------------------
# Fresh database
# ---------------------------------------------------------------------------


def test_fresh_upgrade_creates_the_saved_widget_schema(
    disposable_postgres,
) -> None:
    """Upgrading an empty database to head creates both tables and nothing else."""
    disposable_postgres.upgrade("head")

    inspector = sa.inspect(disposable_postgres.engine)
    tables = set(inspector.get_table_names())
    assert WIDGETS_TABLE in tables
    assert REVISIONS_TABLE in tables

    # The new tables start empty.
    assert disposable_postgres.scalar(f"SELECT count(*) FROM {WIDGETS_TABLE}") == 0
    assert disposable_postgres.scalar(f"SELECT count(*) FROM {REVISIONS_TABLE}") == 0

    # The widget's identity is its own opaque key.
    widget_pk = inspector.get_pk_constraint(WIDGETS_TABLE)
    assert widget_pk["constrained_columns"] == ["widget_id"]

    # Revision identity is (widget_id, revision).
    revision_pk = inspector.get_pk_constraint(REVISIONS_TABLE)
    assert revision_pk["constrained_columns"] == ["widget_id", "revision"]

    # The snapshots are JSONB.
    jsonb_columns = {
        column["name"]: str(column["type"])
        for column in inspector.get_columns(REVISIONS_TABLE)
    }
    for name in ("artifact_snapshot", "provenance_snapshot", "creation_context"):
        assert jsonb_columns[name] == "JSONB"


def test_the_migrated_schema_enforces_the_expected_constraints(
    disposable_postgres,
) -> None:
    """Keys, constraints, indexes, and foreign keys are all present."""
    disposable_postgres.upgrade("head")
    inspector = sa.inspect(disposable_postgres.engine)

    checks = {
        c["name"]: c["sqltext"]
        for c in inspector.get_check_constraints(WIDGETS_TABLE)
    }
    assert "saved_widgets_lifecycle_state_check" in checks
    assert "saved_widgets_current_revision_check" in checks

    revision_checks = {
        c["name"]: c["sqltext"]
        for c in inspector.get_check_constraints(REVISIONS_TABLE)
    }
    assert "saved_widget_revisions_revision_check" in revision_checks
    assert "saved_widget_revisions_edit_base_check" in revision_checks

    indexes = {i["name"] for i in inspector.get_indexes(WIDGETS_TABLE)}
    assert "ix_saved_widgets_owner_user_id" in indexes
    revision_indexes = {i["name"] for i in inspector.get_indexes(REVISIONS_TABLE)}
    assert "ix_saved_widget_revisions_widget_created_at" in revision_indexes

    widget_fks = {
        c["name"]: c for c in inspector.get_foreign_keys(WIDGETS_TABLE)
    }
    assert "fk_saved_widgets_owner_user_id" in widget_fks
    owner_fk = widget_fks["fk_saved_widgets_owner_user_id"]
    assert owner_fk["referred_table"] == "users"
    assert owner_fk["options"].get("ondelete") == "CASCADE"

    # The current-revision pointer is a deferrable composite foreign key, so
    # the widget and its first revision can be written in one transaction.
    pointer_fk = widget_fks["fk_saved_widgets_current_revision"]
    assert pointer_fk["referred_table"] == REVISIONS_TABLE
    assert pointer_fk["constrained_columns"] == ["widget_id", "current_revision"]
    assert pointer_fk["referred_columns"] == ["widget_id", "revision"]
    assert pointer_fk["options"].get("deferrable") is True
    assert pointer_fk["options"].get("initially") == "DEFERRED"

    revision_fks = {
        c["name"]: c for c in inspector.get_foreign_keys(REVISIONS_TABLE)
    }
    widget_fk = revision_fks["fk_saved_widget_revisions_widget"]
    assert widget_fk["referred_table"] == WIDGETS_TABLE
    assert widget_fk["options"].get("ondelete") == "CASCADE"

    edit_base_fk = revision_fks["fk_saved_widget_revisions_edit_base"]
    assert edit_base_fk["referred_table"] == REVISIONS_TABLE
    assert edit_base_fk["options"].get("deferrable") is True

    # There is deliberately no foreign key from a revision to its source
    # thread or message: the source is provenance, not storage authority.
    referred = {
        c["referred_table"]
        for c in inspector.get_foreign_keys(REVISIONS_TABLE)
    }
    assert "chat_threads" not in referred
    assert "chat_messages" not in referred
    assert "chat_completion_attempts" not in referred


def test_revision_rows_are_guarded_against_in_place_update(
    disposable_postgres,
) -> None:
    """A narrow database guard makes a stored revision immutable."""
    disposable_postgres.upgrade("head")

    triggers = disposable_postgres.scalar(
        "SELECT tgname FROM pg_trigger "
        "WHERE tgrelid = to_regclass(:table) AND NOT tgisinternal",
        table=REVISIONS_TABLE,
    )
    assert triggers == "trg_saved_widget_revisions_immutable"


def test_the_orm_metadata_agrees_with_the_migrated_schema(
    disposable_postgres,
) -> None:
    """The ORM models and the migration describe the same schema."""
    disposable_postgres.upgrade("head")
    inspector = sa.inspect(disposable_postgres.engine)
    _assert_column_parity(inspector)
    _assert_constraint_parity(inspector)


# ---------------------------------------------------------------------------
# Existing-instance upgrade
# ---------------------------------------------------------------------------


def test_upgrade_from_the_previous_head_preserves_existing_rows(
    disposable_postgres,
) -> None:
    """An existing instance upgrades without rewriting any source row."""
    disposable_postgres.upgrade(PARENT_REVISION)

    inspector_before = sa.inspect(disposable_postgres.engine)
    assert WIDGETS_TABLE not in inspector_before.get_table_names()
    assert REVISIONS_TABLE not in inspector_before.get_table_names()

    seeded = _seed_existing_chat_rows(disposable_postgres)
    before = _chat_row_snapshot(disposable_postgres)

    disposable_postgres.upgrade("head")

    after = _chat_row_snapshot(disposable_postgres)
    assert after == before
    assert after["threads"] == 1
    assert after["messages"] == 1
    assert after["attempts"] == 1
    assert after["message_content"] == "pre-existing assistant content"
    assert after["attempt_request_id"] == "req-migration-probe"

    # The new tables are created empty.
    assert disposable_postgres.scalar(f"SELECT count(*) FROM {WIDGETS_TABLE}") == 0
    assert disposable_postgres.scalar(f"SELECT count(*) FROM {REVISIONS_TABLE}") == 0

    # The seeded account is still the same row.
    assert (
        disposable_postgres.scalar(
            "SELECT count(*) FROM users WHERE id = :id",
            id="migration-probe-account",
        )
        == 1
    )

    # The seeded message is still the same row.
    assert (
        disposable_postgres.scalar(
            "SELECT count(*) FROM chat_messages WHERE id = :id",
            id=seeded["message_id"],
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Downgrade and re-upgrade
# ---------------------------------------------------------------------------


def test_downgrade_removes_the_new_tables_and_preserves_chat_data(
    disposable_postgres,
) -> None:
    """The downgrade is clean and reversible, and touches nothing else."""
    disposable_postgres.upgrade("head")
    _seed_existing_chat_rows(disposable_postgres)
    before = _chat_row_snapshot(disposable_postgres)

    disposable_postgres.downgrade(PARENT_REVISION)

    inspector = sa.inspect(disposable_postgres.engine)
    tables = set(inspector.get_table_names())
    assert WIDGETS_TABLE not in tables
    assert REVISIONS_TABLE not in tables

    # Pre-existing chat data is intact.
    assert _chat_row_snapshot(disposable_postgres) == before

    # The narrow guard went with the table.
    assert (
        disposable_postgres.scalar(
            "SELECT count(*) FROM pg_proc WHERE proname = "
            "'codexify_saved_widget_revisions_immutable'"
        )
        == 0
    )


def test_re_upgrade_restores_the_saved_widget_schema(
    disposable_postgres,
) -> None:
    """Re-upgrading recreates the schema, empty."""
    disposable_postgres.upgrade("head")
    _seed_existing_chat_rows(disposable_postgres)
    before = _chat_row_snapshot(disposable_postgres)

    disposable_postgres.downgrade(PARENT_REVISION)
    disposable_postgres.upgrade("head")

    inspector = sa.inspect(disposable_postgres.engine)
    assert WIDGETS_TABLE in inspector.get_table_names()
    assert REVISIONS_TABLE in inspector.get_table_names()
    assert disposable_postgres.scalar(f"SELECT count(*) FROM {WIDGETS_TABLE}") == 0
    assert disposable_postgres.scalar(f"SELECT count(*) FROM {REVISIONS_TABLE}") == 0
    assert _chat_row_snapshot(disposable_postgres) == before
