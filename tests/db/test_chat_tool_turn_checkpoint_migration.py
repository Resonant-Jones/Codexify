"""Disposable PostgreSQL proof for bounded chat tool decision checkpoints."""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from guardian.command_bus.redaction_policy import compute_args_hash
from guardian.core.db import (
    ChatToolCheckpointError,
    freeze_chat_tool_decision,
    get_chat_tool_checkpoint,
)
from guardian.core.pgdb import PgDB


PREVIOUS_REVISION = "17b23052da6a"
CHECKPOINT_REVISION = "f0d7c4b2a198"


@pytest.fixture
def disposable_database(monkeypatch):
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")
    database_name = f"codexify_tool_checkpoint_{uuid.uuid4().hex[:12]}"
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
    try:
        yield config, test_url
    finally:
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {database_name}")


def _seed_attempt(engine: sa.Engine, *, accepted: bool = True) -> int:
    with engine.begin() as connection:
        for user_id in ("account-a", "account-b"):
            connection.execute(
                sa.text(
                    "INSERT INTO users (id, username, password_hash, role) "
                    "VALUES (:id, :id, 'inert-test-hash', 'guest')"
                ),
                {"id": user_id},
            )
        thread_id = connection.execute(
            sa.text(
                "INSERT INTO chat_threads (user_id, title) "
                "VALUES ('account-a', 'Checkpoint test') RETURNING id"
            )
        ).scalar_one()
        connection.execute(
            sa.text(
                "INSERT INTO chat_completion_attempts "
                "(request_id, backend_task_id, thread_id, turn_id, accepted_at) "
                "VALUES ('request-a', 'task-a', :thread_id, 'turn-a', "
                + ("now()" if accepted else "NULL")
                + ")"
            ),
            {"thread_id": thread_id},
        )
    return thread_id


def _binding(thread_id: int) -> dict[str, object]:
    return {
        "request_id": "request-a",
        "backend_task_id": "task-a",
        "thread_id": thread_id,
        "turn_id": "turn-a",
        "account_id": "account-a",
    }


@pytest.mark.integration
def test_fresh_upgrade_freezes_one_decision_and_reads_it_independently(
    disposable_database,
) -> None:
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    thread_id = _seed_attempt(engine)
    repo = PgDB(test_url.render_as_string(hide_password=False))
    binding = _binding(thread_id)
    first_hash = compute_args_hash({"body": {"password": "private-value"}})
    second_hash = compute_args_hash({"body": {"password": "changed"}})

    first = freeze_chat_tool_decision(
        repo, **binding, command_id="op::health", args_hash=first_hash
    )
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE chat_completion_attempts SET accepted_at=NULL "
                "WHERE request_id='request-a'"
            )
        )
    independent_repo = PgDB(test_url.render_as_string(hide_password=False))
    assert get_chat_tool_checkpoint(independent_repo, **binding) == first
    assert freeze_chat_tool_decision(
        independent_repo, **binding, command_id="op::health", args_hash=first_hash
    ) == first
    with pytest.raises(ChatToolCheckpointError, match="tool_decision_conflict"):
        freeze_chat_tool_decision(
            repo, **binding, command_id="op::other", args_hash=first_hash
        )
    with pytest.raises(ChatToolCheckpointError, match="tool_decision_conflict"):
        freeze_chat_tool_decision(
            repo, **binding, command_id="op::health", args_hash=second_hash
        )
    for changed in (
        {"account_id": "account-b"},
        {"thread_id": thread_id + 1},
        {"backend_task_id": "other-task"},
        {"request_id": "missing-request"},
    ):
        with pytest.raises(ChatToolCheckpointError, match="accepted_tool_attempt_unavailable"):
            freeze_chat_tool_decision(
                repo,
                **(binding | changed),
                command_id="op::health",
                args_hash=first_hash,
            )
    with engine.connect() as connection:
        row = connection.execute(
            sa.text("SELECT * FROM chat_completion_attempts WHERE request_id='request-a'")
        ).mappings().one()
        assert row["tool_turn_id"] == first["tool_turn_id"]
        assert row["tool_args_hash"] == first_hash
        assert row["tool_checkpoint_at"] is not None
        assert "private-value" not in str(dict(row))
        assert "changed" not in str(dict(row))
    engine.dispose()


@pytest.mark.integration
def test_concurrent_decisions_cannot_replace_first_checkpoint(disposable_database) -> None:
    config, test_url = disposable_database
    command.upgrade(config, "head")
    engine = sa.create_engine(test_url)
    thread_id = _seed_attempt(engine)
    repo = PgDB(test_url.render_as_string(hide_password=False))
    binding = _binding(thread_id)

    def propose(command_id: str):
        try:
            return freeze_chat_tool_decision(
                repo,
                **binding,
                command_id=command_id,
                args_hash=compute_args_hash({"body": {"value": command_id}}),
            )
        except ChatToolCheckpointError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(propose, ("op::first", "op::second")))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count("tool_decision_conflict") == 1
    assert get_chat_tool_checkpoint(repo, **binding) in results
    engine.dispose()


@pytest.mark.integration
def test_existing_attempt_upgrade_and_compatible_downgrade(disposable_database) -> None:
    config, test_url = disposable_database
    command.upgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(test_url)
    thread_id = _seed_attempt(engine)
    command.upgrade(config, CHECKPOINT_REVISION)
    with engine.connect() as connection:
        row = connection.execute(
            sa.text(
                "SELECT tool_turn_id, tool_command_id, tool_args_hash, "
                "tool_checkpoint_at FROM chat_completion_attempts "
                "WHERE request_id='request-a'"
            )
        ).one()
        assert row == (None, None, None, None)
    repo = PgDB(test_url.render_as_string(hide_password=False))
    assert get_chat_tool_checkpoint(repo, **_binding(thread_id)) is None
    engine.dispose()
    command.downgrade(config, PREVIOUS_REVISION)
    engine = sa.create_engine(test_url)
    assert "tool_turn_id" not in {
        column["name"]
        for column in sa.inspect(engine).get_columns("chat_completion_attempts")
    }
    with engine.connect() as connection:
        assert connection.execute(
            sa.text("SELECT count(*) FROM chat_completion_attempts")
        ).scalar_one() == 1
    engine.dispose()
