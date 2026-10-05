"""Real PostgreSQL query-envelope regressions and worker phase controls."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import time
from types import SimpleNamespace
from unittest.mock import Mock

from alembic import command
import psycopg
import pytest
from sqlalchemy import text

from guardian.core import chat_postgres_deadline as bounds
from guardian.core.chatlog_postgres import PostgresChatLogDB
from guardian.core.db import (
    create_chat_completion_attempt,
    get_chat_completion_attempt_by_task_id,
    record_chat_completion_attempt_terminal_event,
)
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    build_accepted_chat_task_deadline,
)
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker
from tests.db.test_chat_completion_attempt_migration import (
    disposable_database as _disposable_database_fixture,
)

disposable_database = _disposable_database_fixture


@pytest.fixture
def database(disposable_database):
    config, url = disposable_database
    command.upgrade(config, "head")
    plain = url.set(drivername="postgresql").render_as_string(hide_password=False)
    label = "accepted_query_deadline_proof"
    repo = PostgresChatLogDB(
        url.update_query_dict({"application_name": label}).render_as_string(
            hide_password=False
        )
    )
    with psycopg.connect(plain, autocommit=True) as observer:
        observer.execute(
            "INSERT INTO users (id, username, password_hash, role) "
            "VALUES ('deadline-proof', 'deadline-proof', 'inert-test-hash', 'guest')"
        )
        thread = observer.execute(
            "INSERT INTO chat_threads (user_id, title) "
            "VALUES ('deadline-proof', 'Query deadline proof') RETURNING id"
        ).fetchone()[0]
        create_chat_completion_attempt(
            repo,
            request_id="proof-request",
            backend_task_id="proof-task",
            thread_id=thread,
            turn_id="proof-turn",
        )
        # Warm the ORM pool outside any task; the same connection must later
        # inherit a deadline, then retain ordinary limits outside that scope.
        with repo._sa_session() as session:
            assert session.execute(text("SHOW statement_timeout")).scalar_one() == "0"
        yield repo, observer, thread, label, plain
    repo._sa_engine.dispose()


def _terminal_snapshot(seconds=0.5):
    return build_accepted_chat_task_deadline(
        datetime.now(timezone.utc) - timedelta(seconds=780 - seconds)
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "surface", ["atomic_assistant", "orm_terminal", "expired_worker"]
)
def test_real_row_lock_cannot_write_after_terminal_deadline(
    database, monkeypatch, surface
):
    repo, observer, thread, label, plain = database
    events = []
    work = Mock(side_effect=AssertionError("Expired task reached generation"))
    released = Mock(return_value=True)
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", repo)
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda _: False)
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda tid, kind, data: events.append((kind, dict(data))),
    )
    monkeypatch.setattr(chat_worker, "_safe_emit_live_event", lambda *a, **k: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", released)
    monkeypatch.setattr(chat_worker, "run_chat_completion_task", work)
    with psycopg.connect(plain) as locker:
        locker.execute(
            "SELECT request_id FROM chat_completion_attempts "
            "WHERE backend_task_id='proof-task' FOR UPDATE"
        )
        deadline = _terminal_snapshot()
        task = ChatCompletionTask(
            user_id="deadline-proof",
            thread_id=thread,
            request_id="proof-request",
            task_id="proof-task",
            **deadline.to_dict(),
        )
        task.turn_id = "proof-turn"
        task.turn_lock_owner = "proof-task"

        def operation():
            if surface == "expired_worker":
                return chat_worker._run_chat_task(task)
            with bounds.accepted_postgres_query_scope(deadline):
                with pytest.raises(AcceptedChatTaskDeadlineExceeded):
                    if surface == "atomic_assistant":
                        repo.create_assistant_message_for_completion_attempt(
                            thread_id=thread,
                            content="must not persist after deadline",
                            request_id="proof-request",
                            backend_task_id="proof-task",
                            turn_id="proof-turn",
                        )
                    else:
                        record_chat_completion_attempt_terminal_event(
                            repo,
                            request_id="proof-request",
                            backend_task_id="proof-task",
                            thread_id=thread,
                            turn_id="proof-turn",
                            event_type="task.failed",
                        )

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(operation)
            wait = None
            while time.monotonic() - start < 0.35:
                wait = observer.execute(
                    "SELECT pid, wait_event FROM pg_stat_activity "
                    "WHERE application_name=%s AND wait_event_type='Lock'",
                    (label,),
                ).fetchone()
                if wait:
                    break
                assert not future.done(), "No actual PostgreSQL lock wait observed"
                time.sleep(0.005)
            assert wait is not None
            # Keep the row locked until the operation has independently ended.
            future.result(timeout=1.0)
            duration = time.monotonic() - start
            assert duration < 0.75
            # Observe server quiescence while the original row remains locked.
            # Unlocking must not be what ends the database operation.
            until = time.monotonic() + 0.2
            while observer.execute(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE application_name=%s AND state='active'",
                (label,),
            ).fetchone()[0]:
                assert time.monotonic() < until
                time.sleep(0.005)
            locker.rollback()

    assert {
        name: getattr(task, name) for name in deadline.to_dict()
    } == deadline.to_dict()
    row = get_chat_completion_attempt_by_task_id(repo, "proof-task")
    assert row["completed_message_id"] is None
    assert row["terminal_event_type"] is None
    assert (
        observer.execute(
            "SELECT count(*) FROM chat_messages WHERE thread_id=%s",
            (thread,),
        ).fetchone()[0]
        == 0
    )
    assert (
        observer.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE application_name=%s AND state='active'",
            (label,),
        ).fetchone()[0]
        == 0
    )
    if surface == "expired_worker":
        work.assert_not_called()
        released.assert_called_once_with(thread, "proof-task")
        failed = [payload for kind, payload in events if kind == "task.failed"]
        # No durable terminal write was acknowledged. Preserve uncertainty
        # rather than publishing an alternate controlled-deadline outcome.
        assert failed == []
        assert not any(
            kind in {"task.completed", "task.cancelled"} for kind, _ in events
        )
    # Fresh adapter normal success, exact binding and idempotence still work.
    fresh = PostgresChatLogDB(plain)
    try:
        create_chat_completion_attempt(
            fresh,
            request_id="control-request",
            backend_task_id="control-task",
            thread_id=thread,
            turn_id="control-turn",
        )
        control_deadline = build_accepted_chat_task_deadline(datetime.now(timezone.utc))
        with bounds.accepted_postgres_query_scope(control_deadline):
            bounds.use_postgres_terminal_budget()
            message, linked = fresh.create_assistant_message_for_completion_attempt(
                thread_id=thread,
                content="fresh normal control",
                request_id="control-request",
                backend_task_id="control-task",
                turn_id="control-turn",
            )
            assert fresh.create_assistant_message_for_completion_attempt(
                thread_id=thread,
                content="must not duplicate",
                request_id="control-request",
                backend_task_id="control-task",
                turn_id="control-turn",
            ) == (message, True)
        assert linked
        assert (
            get_chat_completion_attempt_by_task_id(fresh, "control-task")[
                "completed_message_id"
            ]
            == message
        )
        assert (
            get_chat_completion_attempt_by_task_id(fresh, "proof-task")[
                "completed_message_id"
            ]
            is None
        )
    finally:
        fresh._sa_engine.dispose()
    print(
        {
            "surface": surface,
            "duration_seconds": duration,
            "wait": wait,
            "no_late_write": True,
            "active_server_work": 0,
        }
    )


@pytest.mark.integration
@pytest.mark.parametrize("surface", ["raw", "pooled_orm"])
def test_slow_statement_is_bounded_and_does_not_leak_pool_limits(database, surface):
    repo, observer, _thread, label, _plain = database
    deadline = _terminal_snapshot(0.25)
    start = time.monotonic()
    with bounds.accepted_postgres_query_scope(deadline):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            if surface == "raw":
                with repo._connect() as connection:
                    connection.execute("SELECT pg_sleep(10)")
            else:
                with repo._sa_session() as session:
                    session.execute(text("SELECT pg_sleep(10)"))
    duration = time.monotonic() - start
    assert duration < 0.6
    # Cancellation/close must actually end server work, not just our observer.
    until = time.monotonic() + 0.3
    while observer.execute(
        "SELECT count(*) FROM pg_stat_activity "
        "WHERE application_name=%s AND state='active'",
        (label,),
    ).fetchone()[0]:
        assert time.monotonic() < until
        time.sleep(0.005)
    with repo._sa_session() as session:
        assert session.execute(text("SHOW statement_timeout")).scalar_one() == "0"
        assert session.execute(text("SHOW lock_timeout")).scalar_one() == "0"
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    print({"surface": surface, "duration_seconds": duration, "pool_limits_reset": True})


@pytest.mark.integration
def test_terminal_switch_preserves_frozen_parent_and_borrowed_transaction(database):
    repo, observer, thread, _label, _plain = database
    deadline = _terminal_snapshot(2)
    with bounds.accepted_postgres_query_scope(deadline):
        with repo.conversation_transaction():
            with repo._connect() as borrowed:
                with pytest.raises(RuntimeError, match="Cannot commit"):
                    borrowed.commit()
                with pytest.raises(RuntimeError, match="Cannot roll back"):
                    borrowed.rollback()
                with borrowed.cursor() as cursor:
                    cursor.execute(
                        "SELECT name, setting::int AS milliseconds FROM pg_settings "
                        "WHERE name IN ('statement_timeout', 'lock_timeout')"
                    )
                    limits = {
                        row["name"]: row["milliseconds"] for row in cursor.fetchall()
                    }
                    assert set(limits) == {"statement_timeout", "lock_timeout"}
                    assert all(0 < value <= 2000 for value in limits.values())
            repo.create_message(thread, "user", "bounded borrowed write")
    assert (
        observer.execute(
            "SELECT content FROM chat_messages WHERE thread_id=%s",
            (thread,),
        ).fetchone()[0]
        == "bounded borrowed write"
    )
    with repo._sa_session() as session:
        assert session.execute(text("SHOW statement_timeout")).scalar_one() == "0"


@pytest.mark.integration
def test_stricter_database_policy_is_not_replaced_by_parent_budget(database):
    repo, _observer, _thread, _label, _plain = database
    deadline = build_accepted_chat_task_deadline(datetime.now(timezone.utc))
    with bounds.accepted_postgres_query_scope(deadline):
        with repo._connect() as connection:
            connection.execute("SET LOCAL statement_timeout='40ms'")
            connection.execute("SHOW statement_timeout")
            assert (
                connection.execute("SHOW statement_timeout").fetchone()[
                    "statement_timeout"
                ]
                == "40ms"
            )
            started = time.monotonic()
            with pytest.raises(psycopg.errors.QueryCanceled):
                connection.execute("SELECT pg_sleep(5)")
            assert time.monotonic() - started < 0.3
            connection.rollback()


def test_scope_does_not_slide_or_leak_between_tasks(monkeypatch):
    now = datetime.now(timezone.utc)
    clock = [100.0]
    monkeypatch.setattr(bounds.time, "monotonic", lambda: clock[0])
    deadline = build_accepted_chat_task_deadline(now)
    with bounds.accepted_postgres_query_scope(deadline, now=now):
        budget = bounds._budget.get()
        assert budget.remaining() == 720
        clock[0] += 719
        assert budget.remaining() == 1
        bounds.use_postgres_terminal_budget()
        assert budget.remaining() == 61
        clock[0] += 61
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            budget.remaining()
    assert not bounds.accepted_postgres_queries_active()
    with bounds.accepted_postgres_query_scope(None):
        assert bounds._budget.get() is None


def test_expired_or_invalid_scope_starts_no_connection(monkeypatch):
    connect = Mock(side_effect=AssertionError("Must not start native connection"))
    monkeypatch.setattr(bounds.AcceptedDeadlineConnection, "connect", connect)
    expired = _terminal_snapshot(-1)
    with bounds.accepted_postgres_query_scope(expired):
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            bounds.connect_with_query_bounds("unused")
    with bounds.accepted_postgres_query_scope(None, invalid=True):
        with pytest.raises(ValueError):
            bounds.connect_with_query_bounds("unused")
    connect.assert_not_called()


@pytest.mark.parametrize("operation", ["commit", "rollback"])
def test_native_polling_discards_late_terminal_reply(monkeypatch, operation):
    now = datetime.now(timezone.utc)
    clock = [100.0]
    monkeypatch.setattr(bounds.time, "monotonic", lambda: clock[0])
    deadline = build_accepted_chat_task_deadline(now)
    closed = Mock()
    connection = SimpleNamespace(close=closed)

    def protocol_operation():
        # A protocol generator can finish without yielding again. A reply at
        # the deadline must still close the connection and preserve ambiguity.
        clock[0] += 780
        if False:
            yield
        return operation

    with bounds.accepted_postgres_query_scope(deadline, now=now):
        bounds.use_postgres_terminal_budget()
        with pytest.raises(AcceptedChatTaskDeadlineExceeded):
            bounds.AcceptedDeadlineConnection.wait(connection, protocol_operation())
    closed.assert_called_once()


def test_successful_generation_persistence_deadline_keeps_canonical_truth(monkeypatch):
    from tests.workers.test_chat_worker_tool_loop import (
        _build_task,
        _prepare_worker_harness,
    )

    events = _prepare_worker_harness(monkeypatch)
    task = _build_task(task_id="persistence-deadline-truth")
    snapshot = build_accepted_chat_task_deadline(datetime.now(timezone.utc)).to_dict()
    for name, value in snapshot.items():
        setattr(task, name, value)
    provider = Mock(return_value="A successfully generated reply")
    fallback = Mock(return_value=[])
    monkeypatch.setattr(chat_worker, "chat_with_ai", provider)
    monkeypatch.setattr(chat_worker, "_fallback_provider_candidates", fallback)

    def persistence_failure(*_args, **_kwargs):
        assert bounds._budget.get().terminal is True
        raise AcceptedChatTaskDeadlineExceeded()

    monkeypatch.setattr(
        chat_worker.dependencies.chatlog_db,
        "create_message",
        persistence_failure,
    )
    chat_worker._run_chat_task(task)
    terminal = [
        (kind, data)
        for kind, data in events
        if kind
        in {
            "task.failed",
            "task.completed",
            "task.cancelled",
        }
    ]
    assert [kind for kind, _data in terminal] == ["task.failed"]
    failed = terminal[0][1]
    assert failed["failure_code"] == "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED"
    assert failed["completion_truth"]["executed"] is True
    assert failed["completion_truth"]["completed"] is False
    assert failed["persistence_outcome"] == "failed"
    assert failed["attempted_provider"] == "groq"
    assert failed["resolved_provider"] == "groq"
    assert failed["resolved_model"] == "mock-model"
    assert failed["final_provider_truth"]["provider"] == "groq"
    assert {name: getattr(task, name) for name in snapshot} == snapshot
    provider.assert_called_once()
    fallback.assert_not_called()
    assert not bounds.accepted_postgres_queries_active()
