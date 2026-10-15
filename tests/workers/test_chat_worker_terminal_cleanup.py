"""Durable-authorized cleanup never borrows mutable packet capabilities."""

from unittest.mock import Mock

import pytest

from guardian.core import chat_postgres_deadline as pg
from guardian.core import chat_redis_deadline as redis
from guardian.core.db import ChatAttemptReconciliation
from guardian.workers import chat_worker as worker
from tests.workers.test_chat_worker_streaming_chunks import _build_task


@pytest.fixture
def cleanup(monkeypatch):
    task = _build_task(task_id="cleanup-task")
    task.request_id = "cleanup-request"
    task.turn_lock_owner = "mutable-other-owner"
    task.turn_lock = {"lease_token": "mutable-other-token"}
    seen = []
    authority = ChatAttemptReconciliation(None, "task.failed", None, "original-token")

    def observe(_, **identity):
        assert pg._budget.get().operation
        assert pg._budget.get().remaining() <= 2
        with pytest.raises(ValueError):
            pg.require_accepted_work_budget()
        assert identity == dict(
            request_id=task.request_id,
            backend_task_id=task.task_id,
            thread_id=task.thread_id,
            turn_id=task.turn_id,
        )
        seen.append("durable-read")
        return authority

    def release(thread, *, owner_task_id, lease_token):
        assert pg._budget.get() is None and redis._budget.get().operation
        assert (thread, owner_task_id, lease_token) == (
            task.thread_id,
            task.task_id,
            "original-token",
        )
        seen.append("strict-cas")
        return True

    read, cas = Mock(side_effect=observe), Mock(side_effect=release)
    monkeypatch.setattr(worker, "observe_chat_completion_attempt_terminal", read)
    monkeypatch.setattr(worker, "release_terminal_attempt_turn_lock", cas)
    return task, authority, read, cas, seen


def test_original_durable_capability_and_ack_precede_cas(cleanup):
    task, authority, _, _, seen = cleanup
    assert worker._observe_and_cleanup_terminal_attempt(task) == authority
    assert seen == ["durable-read", "strict-cas"]
    assert pg._budget.get() is None and redis._budget.get() is None


@pytest.mark.parametrize(
    "outcome", ["pending", "missing-token", "requestless", "read-uncertain"]
)
def test_unconfirmed_authority_cannot_clean(cleanup, outcome):
    task, _, read, cas, _ = cleanup
    read.side_effect = None
    read.return_value = ChatAttemptReconciliation(None, "task.cancelled", None, None)
    if outcome == "pending":
        read.return_value = ChatAttemptReconciliation(
            None, None, None, "unavailable-cap"
        )
    elif outcome == "requestless":
        task.request_id = ""
    elif outcome == "read-uncertain":
        read.side_effect = RuntimeError("injected lost read/commit acknowledgement")
    worker._observe_and_cleanup_terminal_attempt(task)
    cas.assert_not_called()
    if outcome == "requestless":
        read.assert_not_called()


@pytest.mark.parametrize(
    "result", [False, RuntimeError("injected uncertain EVAL acknowledgement")]
)
def test_cas_mismatch_or_uncertainty_preserves_terminal_truth(cleanup, result):
    task, authority, _, cas, _ = cleanup
    cas.side_effect = result if isinstance(result, Exception) else None
    cas.return_value = result
    assert worker._observe_and_cleanup_terminal_attempt(task) == authority
    cas.assert_called_once_with(
        task.thread_id, owner_task_id=task.task_id, lease_token="original-token"
    )
    assert pg._budget.get() is None and redis._budget.get() is None


def test_cleanup_cannot_replace_inherited_execution_scope(cleanup):
    task, _, read, cas, _ = cleanup
    from guardian.tasks.chat_deadline import accepted_chat_deadline_for_task

    # No deadline fields is historical authority; inherited scope cannot be
    # replaced with maintenance to extend its task execution.
    with pg.postgres_operation_scope(1):
        assert worker._observe_and_cleanup_terminal_attempt(task) is None
    read.assert_not_called()
    cas.assert_not_called()
    assert accepted_chat_deadline_for_task(task) is None


def test_held_native_eval_times_out_without_cleanup_fallback(cleanup, monkeypatch):
    import time
    from redis.backoff import NoBackoff
    from redis.retry import Retry
    from guardian.queue import redis_queue, turn_lock
    from tests.queue.test_chat_redis_deadline import peer, factory

    task, authority, _, _, _ = cleanup
    monkeypatch.setattr(
        worker,
        "release_terminal_attempt_turn_lock",
        turn_lock.release_terminal_attempt_turn_lock,
    )
    monkeypatch.setattr(
        worker, "redis_operation_scope", lambda: redis.redis_operation_scope(0.25)
    )
    original = redis_queue._CLIENT
    with peer(b"EVAL") as (state, arrived, eof):
        factory(monkeypatch, state, retry=Retry(NoBackoff(), 3))
        started = time.monotonic()
        assert worker._observe_and_cleanup_terminal_attempt(task) == authority
        elapsed = time.monotonic() - started
        assert 0.20 < elapsed < 0.65
        assert arrived.is_set() and state["commands"] == 1 and eof.wait(0.25)
        assert state["eofs"] == 1
    assert redis_queue._CLIENT is original
    assert pg._budget.get() is None and redis._budget.get() is None
    print(
        {
            "surface": "worker_terminal_cleanup_EVAL",
            "duration": elapsed,
            "commands": 1,
            "eofs": 1,
        }
    )
