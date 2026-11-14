"""DDL capture and SQLite column roundtrip, not live PostgreSQL trigger proof."""

import importlib
from unittest.mock import Mock

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text

from guardian.db.models import ChatCompletionAttempt

MODULE = "guardian.db.migrations.versions.c7e4a1b9d602_preserve_accepted_chat_account_custody"


def test_postgres_trigger_ddl_preserves_original_custody(monkeypatch):
    migration = importlib.import_module(MODULE)
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()
    assert migration.down_revision == "ab71d5ce9604"
    table, column = operations.add_column.call_args.args
    assert table == "chat_completion_attempts"
    assert column.name == "accepted_account_id" and column.nullable
    assert column.type.length == 255
    assert column.default is None and column.server_default is None
    ddl = "\n".join(call.args[0] for call in operations.execute.call_args_list)
    assert "NEW.accepted_account_id IS DISTINCT FROM OLD.accepted_account_id" in ddl
    assert "OLD.accepted_account_id IS NOT NULL" in ddl
    for field in ("request_id", "backend_task_id", "thread_id", "turn_id"):
        assert f"NEW.{field} IS DISTINCT FROM OLD.{field}" in ddl
    for field in (
        "accepted_at",
        "terminal_event_type",
        "completed_message_id",
        "tool_args_hash",
    ):
        assert f"NEW.{field}" not in ddl
    assert "BEFORE UPDATE ON chat_completion_attempts" in ddl
    assert "UPDATE chat_completion_attempts SET" not in ddl
    operations.reset_mock()
    migration.downgrade()
    operations.drop_column.assert_called_once_with(
        "chat_completion_attempts", "accepted_account_id"
    )
    assert len(operations.execute.call_args_list) == 2


def test_column_roundtrip_preserves_legacy_null_without_backfill(monkeypatch):
    migration = importlib.import_module(MODULE)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE chat_completion_attempts (request_id TEXT PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO chat_completion_attempts VALUES ('legacy')")
        )
        operations = Operations(MigrationContext.configure(connection))
        # Only column evolution is portable. PostgreSQL trigger SQL is captured
        # in the separate test and deliberately not presented as executed here.
        proxy = Mock()
        proxy.add_column.side_effect = operations.add_column
        proxy.drop_column.side_effect = operations.drop_column
        monkeypatch.setattr(migration, "op", proxy)
        migration.upgrade()
        assert (
            connection.execute(
                text("SELECT accepted_account_id FROM chat_completion_attempts")
            ).scalar()
            is None
        )
        migration.downgrade()
        assert [
            column["name"]
            for column in inspect(connection).get_columns("chat_completion_attempts")
        ] == ["request_id"]
        assert (
            connection.execute(
                text("SELECT request_id FROM chat_completion_attempts")
            ).scalar()
            == "legacy"
        )
    engine.dispose()


def test_orm_column_matches_nullable_migration():
    column = ChatCompletionAttempt.__table__.c.accepted_account_id
    assert column.nullable and column.type.length == 255
    assert column.default is None and column.server_default is None
