"""Native read-only terminal capability observation and acknowledgement."""

from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from guardian.core.chat_postgres_deadline import postgres_operation_scope
from guardian.core.db import (
    get_chat_completion_attempt_by_task_id,
    observe_chat_completion_attempt_terminal,
    reconcile_chat_completion_attempt_after_deadline,
    record_chat_completion_attempt_terminal_event,
)
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker as worker
from tests.db.test_chat_completion_attempt_migration import (
    disposable_database as _disposable_database_fixture,
    recovery_database as _recovery_database_fixture,
)

disposable_database = _disposable_database_fixture
recovery_database = _recovery_database_fixture


@pytest.mark.integration
@pytest.mark.parametrize(
    "kind", ["pending", "task.failed", "task.cancelled", "orphan", "completion"]
)
def test_native_observation_is_read_only_and_capability_private(
    recovery_database, kind
):
    _, _, repo, deadline, create = recovery_database
    identity = create("observe")
    if kind in {"task.failed", "task.cancelled"}:
        assert record_chat_completion_attempt_terminal_event(
            repo, **identity, event_type=kind
        )
    elif kind == "orphan":
        reconcile_chat_completion_attempt_after_deadline(
            repo, **identity, now=deadline.terminal_deadline_at
        )
    elif kind == "completion":
        repo.create_assistant_message_for_completion_attempt(
            **identity, content="native terminal authority"
        )
    before = get_chat_completion_attempt_by_task_id(repo, identity["backend_task_id"])
    with postgres_operation_scope(2):
        result = observe_chat_completion_attempt_terminal(repo, **identity)
    assert (
        get_chat_completion_attempt_by_task_id(repo, identity["backend_task_id"])
        == before
    )
    assert before["deadline_snapshot"] == deadline.to_dict()
    assert "turn_lock_token" not in before
    assert result.turn_lock_token == (None if kind == "pending" else "lock-observe")
    if kind == "pending":
        assert result.terminal_event_type is None and result.terminal_outcome is None
    if kind == "completion":
        assert result.completed_message_id == before["completed_message_id"]
    for field in ("request_id", "backend_task_id", "thread_id", "turn_id"):
        wrong = {**identity, field: -1 if field == "thread_id" else "wrong"}
        with postgres_operation_scope(2), pytest.raises(ValueError):
            observe_chat_completion_attempt_terminal(repo, **wrong)


@pytest.mark.integration
def test_native_read_commit_uncertainty_cannot_authorize_cleanup(
    recovery_database, monkeypatch
):
    _, _, repo, _, create = recovery_database
    identity = create("ack")
    assert record_chat_completion_attempt_terminal_event(
        repo, **identity, event_type="task.cancelled"
    )
    before = get_chat_completion_attempt_by_task_id(repo, identity["backend_task_id"])
    original = repo._sa_session

    @contextmanager
    def uncertain_ack():
        with original() as session:
            yield session
        raise RuntimeError("injected lost read transaction acknowledgement")

    monkeypatch.setattr(repo, "_sa_session", uncertain_ack)
    monkeypatch.setattr(worker.dependencies, "chatlog_db", repo)
    cas = Mock(
        side_effect=AssertionError("uncertain terminal read authorized Redis cleanup")
    )
    monkeypatch.setattr(worker, "release_terminal_attempt_turn_lock", cas)
    task = ChatCompletionTask(
        user_id="recovery-account",
        request_id=identity["request_id"],
        task_id=identity["backend_task_id"],
        thread_id=identity["thread_id"],
    )
    task.turn_id = identity["turn_id"]
    assert worker._observe_and_cleanup_terminal_attempt(task) is None
    cas.assert_not_called()
    monkeypatch.setattr(repo, "_sa_session", original)
    assert get_chat_completion_attempt_by_task_id(repo, task.task_id) == before


@pytest.mark.integration
def test_native_invalid_assistant_link_cannot_publish_or_clean(
    recovery_database, monkeypatch
):
    from sqlalchemy import text

    _, engine, repo, _, create = recovery_database
    identity = create("bad-assistant")
    user_message = repo.create_message(
        identity["thread_id"], "user", "not an assistant"
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE chat_completion_attempts SET completed_message_id=:message WHERE backend_task_id=:task"
            ),
            {"message": user_message, "task": identity["backend_task_id"]},
        )
    monkeypatch.setattr(worker.dependencies, "chatlog_db", repo)
    cas, publish, body = Mock(), Mock(), Mock()
    monkeypatch.setattr(worker, "release_terminal_attempt_turn_lock", cas)
    monkeypatch.setattr(worker, "_safe_publish", publish)
    monkeypatch.setattr(worker, "_run_chat_task_with_query_budget", body)
    task = ChatCompletionTask(
        user_id="recovery-account",
        request_id=identity["request_id"],
        task_id=identity["backend_task_id"],
        thread_id=identity["thread_id"],
    )
    task.turn_id = identity["turn_id"]
    worker._run_chat_task(task)
    cas.assert_not_called()
    publish.assert_not_called()
    body.assert_not_called()
