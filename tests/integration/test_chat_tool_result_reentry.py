"""Same-task tool-result reentry against isolated PostgreSQL persistence."""

from __future__ import annotations

import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy.engine import make_url

from guardian.command_bus import invoke as command_invoke
from guardian.command_bus.store import CommandBusStore
from guardian.core import chat_completion_service
from guardian.core.db import (
    ChatToolCheckpointError,
    GuardianDB,
    get_chat_tool_checkpoint,
)
from guardian.core import dependencies
from guardian.core.chatlog_postgres import PostgresChatLogDB
from guardian.db.models import ChatCompletionAttempt, ChatMessage, ChatThread, User
from guardian.routes import command_bus as command_bus_routes
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from guardian.tasks.types import ChatCompletionTask, task_from_dict
from guardian.workers import chat_worker


@pytest.fixture
def disposable_database(monkeypatch: pytest.MonkeyPatch):
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")
    database_name = f"codexify_tool_reentry_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=database_name)
    admin_dsn = admin_url.render_as_string(hide_password=False)
    test_dsn = test_url.render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        connection.execute(f"CREATE DATABASE {database_name}")
    config = Config(
        str(Path(__file__).resolve().parents[2] / "backend" / "alembic.ini")
    )
    config.set_main_option("sqlalchemy.url", test_dsn.replace("%", "%%"))
    try:
        # Apply every current Alembic head so the disposable proof database has
        # the repository's complete migration schema before records are seeded.
        command.upgrade(config, "heads")
        monkeypatch.setenv("DATABASE_URL", test_dsn)
        yield test_dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (database_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {database_name}")


def _seed_attempt(db: GuardianDB) -> tuple[int, ChatCompletionTask]:
    request_id = "request-reentry-proof"
    task_id = "task-reentry-proof"
    turn_id = "turn-reentry-proof"
    with db.get_session() as session:
        session.add(
            User(
                id="reentry-account",
                username="reentry-account",
                password_hash="inert-test-hash",
                role="guest",
            )
        )
        thread = ChatThread(user_id="reentry-account", title="Reentry proof")
        session.add(thread)
        session.flush()
        thread_id = thread.id
        session.add(
            ChatCompletionAttempt(
                request_id=request_id,
                backend_task_id=task_id,
                thread_id=thread_id,
                turn_id=turn_id,
                accepted_at=sa.func.now(),
            )
        )
        session.commit()
    task = ChatCompletionTask(
        user_id="reentry-account",
        task_id=task_id,
        request_id=request_id,
        thread_id=thread_id,
        origin=f"api:chat.complete|turn_id={turn_id}",
        provider="groq",
        model="proof-model",
        tools=[{"command_id": "op::health_check"}],
    )
    for _name, _value in build_accepted_chat_task_deadline(
        datetime.now(timezone.utc)
    ).to_dict().items():
        setattr(task, _name, _value)
    task.turn_id = turn_id
    # Exercise the same JSON-safe serialize/deserialize boundary used by Redis.
    queued_task = task_from_dict(json.loads(json.dumps(task.to_dict())))
    assert isinstance(queued_task, ChatCompletionTask)
    assert queued_task.turn_id == turn_id
    return thread_id, queued_task


@pytest.mark.integration
def test_completed_command_reentry_after_interruption_uses_durable_records_once(
    disposable_database: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = disposable_database
    original_db = GuardianDB(database_url)
    chat_db = PostgresChatLogDB(database_url)
    thread_id, task = _seed_attempt(original_db)
    monkeypatch.setattr(dependencies, "chatlog_db", chat_db)
    monkeypatch.setattr(
        chat_completion_service, "get_settings", lambda: SimpleNamespace()
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_sanitized_payload_summary",
        lambda messages, _bundle, provider, model, **_kw: {
            "message_count": len(messages),
            "resolved_provider": provider,
            "resolved_model": model,
        },
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **_kw: (
            messages,
            {"image_routing_path": "none", "image_attachment_count": 0},
        ),
    )
    monkeypatch.setattr(chat_completion_service, "_task_routing_debug_metadata", lambda _task: {})
    async def build_messages(_task: Any, **_kwargs: Any):
        return (
            [{"role": "user", "content": "Check service health"}],
            "groq",
            "proof-model",
            {"_prompt_meta": {}},
            {"source_mode": "project", "effective_policy": None},
        )

    monkeypatch.setattr(chat_completion_service, "build_messages_for_llm", build_messages)
    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health(password: str = "") -> dict[str, bool]:
        return {"ok": True}

    monkeypatch.setattr(chat_completion_service, "_command_bus_app", lambda: app)
    monkeypatch.setattr(
        command_bus_routes, "_store", CommandBusStore(db=original_db)
    )
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999")
    executions = 0

    async def execute_loopback(**_kwargs: Any) -> dict[str, Any]:
        nonlocal executions
        executions += 1
        return {"status_code": 200, "body": {"ok": True}}

    monkeypatch.setattr(command_invoke, "execute_loopback_request", execute_loopback)

    decision = (
        '{"type":"tool_decision","command_id":"op::health_check",'
        '"arguments":{"password":"secret-canary-value"}}'
    )

    mismatched_task = task_from_dict(task.to_dict())
    assert isinstance(mismatched_task, ChatCompletionTask)
    mismatched_task.turn_id = "other-accepted-turn"
    monkeypatch.setattr(
        chat_completion_service, "chat_with_ai", lambda *_args, **_kwargs: decision
    )
    with pytest.raises(
        chat_completion_service.ToolLoopExecutionError,
        match="accepted_tool_attempt_unavailable",
    ):
        chat_completion_service.run_chat_completion_task(mismatched_task)
    assert executions == 0

    provider_calls = 0
    interrupt = True

    def interrupt_after_command(messages: list[dict[str, Any]], **_kwargs: Any) -> str:
        nonlocal provider_calls, interrupt
        provider_calls += 1
        if interrupt and provider_calls == 1:
            return decision
        if interrupt:
            raise RuntimeError("injected_after_completed_command_before_persistence")
        if any(
            str(message.get("content") or "").startswith("Tool result injection:\n")
            for message in messages
        ):
            return "Health check completed."
        return decision

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", interrupt_after_command)
    with pytest.raises(RuntimeError, match="injected_after_completed_command"):
        chat_completion_service.run_chat_completion_task(task)
    assert executions == 1

    # A distinct GuardianDB and store force both records to be read from fresh
    # PostgreSQL sessions rather than the first invocation's process objects.
    reentry_db = GuardianDB(database_url)
    reentry_chat_db = PostgresChatLogDB(database_url)
    checkpoint = get_chat_tool_checkpoint(
        reentry_chat_db,
        request_id=task.request_id,
        backend_task_id=task.task_id,
        thread_id=thread_id,
        turn_id=task.turn_id,
        account_id=task.user_id,
    )
    assert checkpoint is not None
    replay_store = CommandBusStore(db=reentry_db)
    command_key = f"{task.request_id}:{checkpoint['tool_turn_id']}:op::health_check"
    completed_run = replay_store.get_run_by_idempotency_key(
        "op::health_check", command_key
    )
    assert completed_run is not None
    assert completed_run["status"] == "completed"
    assert completed_run["args_hash"] == checkpoint["args_hash"]
    assert completed_run["result_json"] == {
        "status_code": 200,
        "body": {"ok": True},
    }
    run_id = completed_run["run_id"]
    assert "secret-canary-value" not in str(completed_run["args_redacted"])

    monkeypatch.setattr(dependencies, "chatlog_db", reentry_chat_db)
    monkeypatch.setattr(command_bus_routes, "_store", replay_store)
    interrupt = False
    replay_store.update_run(run_id=run_id, status="running")
    with pytest.raises(chat_completion_service.ToolLoopExecutionError, match="tool_command_incomplete"):
        chat_completion_service.run_chat_completion_task(task)
    assert executions == 1
    replay_store.update_run(
        run_id=run_id, status="failed", error_text="synthetic terminal failure"
    )
    with pytest.raises(chat_completion_service.ToolLoopExecutionError, match="tool_command_terminal_failure"):
        chat_completion_service.run_chat_completion_task(task)
    assert executions == 1
    replay_store.update_run(run_id=run_id, status="completed")
    result = chat_completion_service.run_chat_completion_task(task)

    assert result["assistant_text"] == "Health check completed."
    assert result["persistence_outcome"] == "persisted"
    assert result["toolTurnId"] == checkpoint["tool_turn_id"]
    assert result["commandRunId"] == run_id
    assert result["provider"] == "groq"
    assert result["model"] == "proof-model"
    assert result["terminal_evidence"]["status"] == "success"
    assert executions == 1

    with reentry_db.get_session() as session:
        messages = (
            session.query(ChatMessage)
            .filter_by(thread_id=thread_id, role="assistant")
            .all()
        )
        assert len(messages) == 1
        assert messages[0].content == "Health check completed."
        assert "secret-canary-value" not in str(messages[0].extra_meta)
        assert messages[0].extra_meta["turn_id"] == task.turn_id
        assert messages[0].extra_meta["requestId"] == task.request_id
        assert messages[0].extra_meta["turnId"] == task.turn_id
        assert messages[0].extra_meta["toolTurnId"] == checkpoint["tool_turn_id"]
        assert messages[0].extra_meta["toolTurnState"] == "completed"
        assert messages[0].extra_meta["loopStopReason"] == "tool_turn_completed"
        assert messages[0].extra_meta["commandRunId"] == run_id
        assert messages[0].extra_meta["commandStatus"] == "completed"
        assert messages[0].extra_meta["provider"] == "groq"
        assert messages[0].extra_meta["model"] == "proof-model"
        assert messages[0].extra_meta["terminalEvidence"]["status"] == "success"
        persisted_message_id = messages[0].id

    # A new handle can find the message immediately from the atomic snake-case
    # key; the worker-side metadata enrichment has not been called in this test.
    fresh_chat_db = PostgresChatLogDB(database_url)
    monkeypatch.setattr(dependencies, "chatlog_db", fresh_chat_db)
    monkeypatch.setattr(chat_worker, "get_redis_client", lambda: SimpleNamespace())
    assert (
        chat_worker._find_assistant_message_for_turn(
            thread_id=thread_id,
            turn_id=task.turn_id,
        )
        == persisted_message_id
    )

    provider_calls_after_persist = provider_calls
    monkeypatch.setattr(chat_worker, "_publish_task_state", lambda *_a, **_k: {})
    monkeypatch.setattr(chat_worker, "_safe_publish", lambda *_a, **_k: {})
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_a, **_k: pytest.fail("persisted turn must deduplicate before inference"),
    )
    chat_worker._run_chat_task(task)
    assert provider_calls == provider_calls_after_persist
    with reentry_db.get_session() as session:
        assert (
            session.query(ChatMessage)
            .filter_by(thread_id=thread_id, role="assistant")
            .count()
            == 1
        )

    binding = {
        "request_id": task.request_id,
        "backend_task_id": task.task_id,
        "thread_id": thread_id,
        "turn_id": task.turn_id,
        "account_id": task.user_id,
    }
    for changed in (
        {"account_id": "other-account"},
        {"thread_id": thread_id + 100},
        {"backend_task_id": "other-task"},
        {"request_id": "other-request"},
    ):
        with pytest.raises(
            ChatToolCheckpointError, match="accepted_tool_attempt_unavailable"
        ):
            get_chat_tool_checkpoint(
                reentry_chat_db,
                **(binding | changed),
            )

    chat_db._sa_engine.dispose()
    reentry_chat_db._sa_engine.dispose()
    fresh_chat_db._sa_engine.dispose()
    original_db.engine.dispose()
    reentry_db.engine.dispose()
