"""Opt-in actual PostgreSQL custody-trigger and combined migration proof.

Uses minimal baseline tables, not a claim to replay the full Alembic history.
Only a private /tmp/codexify-oauth-pg.*/socket cluster is accepted.
"""

import importlib.util
import os
from pathlib import Path
import uuid

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import IntegrityError


@pytest.fixture
def database():
    socket = os.getenv("CODEXIFY_OAUTH_TEST_PG_SOCKET")
    if not socket:
        pytest.skip("requires explicitly supplied disposable PostgreSQL socket")
    path = Path(socket).resolve()
    assert str(path).startswith(
        ("/private/tmp/codexify-oauth-pg.", "/tmp/codexify-oauth-pg.")
    )
    assert path.name == "socket"
    url = URL.create(
        "postgresql+psycopg",
        database="postgres",
        query={
            "host": str(path),
            "port": os.getenv("CODEXIFY_OAUTH_TEST_PG_PORT", "55474"),
        },
    )
    root = create_engine(url)
    schema = "custody_test_" + uuid.uuid4().hex
    with root.begin() as connection:
        assert connection.execute(text("SHOW listen_addresses")).scalar() == ""
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    modules = []
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""CREATE TABLE chat_completion_attempts (
                request_id TEXT PRIMARY KEY, backend_task_id TEXT NOT NULL,
                thread_id INTEGER NOT NULL, turn_id TEXT NOT NULL,
                accepted_at TIMESTAMPTZ, terminal_event_type TEXT,
                completed_message_id INTEGER, tool_args_hash TEXT,
                tool_command_id TEXT, tool_decision_at TIMESTAMPTZ
            )""")
            )
            connection.execute(
                text(
                    "INSERT INTO chat_completion_attempts (request_id, backend_task_id, thread_id, turn_id) VALUES ('legacy', 'old-task', 1, 'old-turn')"
                )
            )
            expected_parent = "ab71d5ce9604"
            for revision in ("c7e4a1b9d602", "c13f0713a901", "d8a90bf32107"):
                paths = list(
                    Path("guardian/db/migrations/versions").glob(revision + "_*.py")
                )
                assert len(paths) == 1
                spec = importlib.util.spec_from_file_location(
                    "custody_pg_" + revision, paths[0]
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                assert module.down_revision == expected_parent
                expected_parent = revision
                module.op = Operations(MigrationContext.configure(connection))
                module.upgrade()
                modules.append(module)
            connection.execute(
                text(
                    "INSERT INTO chat_completion_attempts (request_id, backend_task_id, thread_id, turn_id, accepted_account_id) VALUES ('bound', 'task', 2, 'turn', 'account-a')"
                )
            )
        yield engine, modules
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


@pytest.mark.parametrize(
    "column,value",
    [
        ("accepted_account_id", "account-b"),
        ("accepted_account_id", None),
        ("request_id", "other-request"),
        ("backend_task_id", "other-task"),
        ("thread_id", 3),
        ("turn_id", "other-turn"),
    ],
)
def test_bound_custody_tuple_immutable(database, column, value):
    engine, _ = database
    with pytest.raises(IntegrityError) as failure:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE chat_completion_attempts SET {column}=:value WHERE request_id='bound'"
                ),
                {"value": value},
            )
    assert failure.value.orig.sqlstate == "23514"
    assert "Accepted chat account custody is immutable" in str(failure.value.orig)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT request_id, backend_task_id, thread_id, turn_id, accepted_account_id FROM chat_completion_attempts WHERE request_id='bound'"
            )
        ).one()
        assert tuple(row) == ("bound", "task", 2, "turn", "account-a")


def test_legacy_null_not_backfilled(database):
    engine, _ = database
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT accepted_account_id FROM chat_completion_attempts WHERE request_id='legacy'"
                )
            ).scalar()
            is None
        )
    with pytest.raises(IntegrityError) as failure:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE chat_completion_attempts SET accepted_account_id='account-a' WHERE request_id='legacy'"
                )
            )
    assert failure.value.orig.sqlstate == "23514"


def test_terminal_checkpoint_updates_allowed(database):
    engine, _ = database
    with engine.begin() as connection:
        connection.execute(
            text("""UPDATE chat_completion_attempts SET
            accepted_at=now(), terminal_event_type='completed', completed_message_id=17,
            tool_command_id='op::notion_content_read', tool_args_hash='hash',
            tool_decision_at=now() WHERE request_id='bound'""")
        )
        row = connection.execute(
            text(
                "SELECT accepted_account_id, terminal_event_type, completed_message_id, tool_args_hash FROM chat_completion_attempts WHERE request_id='bound'"
            )
        ).one()
        assert tuple(row) == ("account-a", "completed", 17, "hash")
        # An unchanged tuple is legal, including NULL -> NULL legacy custody.
        connection.execute(
            text(
                "UPDATE chat_completion_attempts SET accepted_account_id=accepted_account_id"
            )
        )


def test_combined_migrations_upgrade_and_downgrade(database):
    engine, modules = database
    with engine.begin() as connection:
        assert {
            "chat_completion_attempts",
            "github_knowledge_credentials",
            "knowledge_oauth_credentials",
            "knowledge_oauth_flows",
        } <= set(inspect(connection).get_table_names())
        for module in reversed(modules):
            module.op = Operations(MigrationContext.configure(connection))
            module.downgrade()
        assert inspect(connection).get_table_names() == ["chat_completion_attempts"]
        assert "accepted_account_id" not in {
            column["name"]
            for column in inspect(connection).get_columns("chat_completion_attempts")
        }
        assert (
            connection.execute(
                text("SELECT count(*) FROM chat_completion_attempts")
            ).scalar()
            == 2
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgname='chat_attempt_account_custody_immutable' AND tgrelid='chat_completion_attempts'::regclass"
                )
            ).scalar()
            == 0
        )
