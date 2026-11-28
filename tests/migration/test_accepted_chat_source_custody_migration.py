"""Structural guard for the PostgreSQL accepted source migration."""

import importlib
from unittest.mock import Mock

import sqlalchemy as sa

from guardian.db.models import ChatCompletionAttempt, ChatMessage

MIGRATION = "guardian.db.migrations.versions.e4b7c2d9a601_accepted_chat_source_custody"


def test_source_column_and_checks_match_migration(monkeypatch):
    migration = importlib.import_module(MIGRATION)
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()

    assert migration.revision == "e4b7c2d9a601"
    assert migration.down_revision == "a64c358e2241"
    table, column = operations.add_column.call_args.args
    model = ChatCompletionAttempt.__table__
    assert table == model.name and column.name == "accepted_user_message_id"
    for source in (column, model.c.accepted_user_message_id):
        assert isinstance(source.type, type(ChatMessage.__table__.c.id.type))
        assert (
            source.nullable and source.default is None and source.server_default is None
        )
        assert not source.foreign_keys

    name, table, sql = operations.create_check_constraint.call_args.args
    assert table == model.name
    model_check = next(c for c in model.constraints if c.name == name)
    assert isinstance(model_check, sa.CheckConstraint)
    assert str(model_check.sqltext) == sql

    trigger_sql = "\n".join(call.args[0] for call in operations.execute.call_args_list)
    assert (
        "NEW.accepted_user_message_id IS DISTINCT FROM OLD.accepted_user_message_id"
        in trigger_sql
    )
    assert "BEFORE UPDATE ON chat_completion_attempts" in trigger_sql
    assert "UPDATE chat_completion_attempts SET" not in trigger_sql

    migration.downgrade()
    operations.drop_constraint.assert_called_once_with(name, table, type_="check")
    operations.drop_column.assert_called_once_with(table, column.name)
