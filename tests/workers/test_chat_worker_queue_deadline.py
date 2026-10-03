from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from guardian.protocol_tokens import ErrorCode
from guardian.queue.redis_queue import _deserialize, _serialize
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from guardian.tasks.types import ChatCompletionTask, TaskLifecycleState, task_from_dict
from guardian.workers import chat_worker


NOW = datetime(2026, 10, 2, 15, tzinfo=timezone.utc)


class _WorkReached(BaseException):
    """Stop before any real completion operation if the guard admits work."""


def _task(age):
    snapshot = (
        build_accepted_chat_task_deadline(NOW - timedelta(seconds=age)).to_dict()
        if age is not None
        else {}
    )
    task = task_from_dict(_deserialize(_serialize(ChatCompletionTask(
        user_id="local", thread_id=71, task_id="queued-task",
        attempt_id="queued-attempt", latest_turn_message_id=51, **snapshot
    ))))
    task.turn_id = "authored-turn"
    task.turn_lock_owner = "queued-owner"
    return task, snapshot


@pytest.fixture
def worker(monkeypatch):
    class Clock:
        @classmethod
        def now(cls, zone=None):
            return NOW if zone is None else NOW.astimezone(zone)

    events = []
    work = Mock(side_effect=_WorkReached)
    release = Mock(return_value=True)
    cleared = Mock()
    monkeypatch.setattr(chat_worker, "datetime", Clock)
    monkeypatch.setattr(chat_worker, "_find_assistant_message_for_turn", lambda **k: None)
    monkeypatch.setattr(
        chat_worker, "_find_assistant_message_id_by_turn_id", lambda **k: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda _: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", cleared)
    monkeypatch.setattr(chat_worker, "run_chat_completion_task", work)
    monkeypatch.setattr(chat_worker, "release_turn_lock", release)
    monkeypatch.setattr(chat_worker, "_safe_emit_live_event", lambda *a, **k: None)
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda task_id, event, payload: events.append((event, dict(payload))),
    )
    return events, work, release, cleared


@pytest.mark.parametrize("age", [720, 721, 800])
def test_expired_queue_task_fails_before_completion_work(worker, age, monkeypatch):
    task, snapshot = _task(age)
    events, work, release, _ = worker
    record_terminal = Mock(return_value=True)
    monkeypatch.setattr(
        chat_worker,
        "_record_chat_completion_attempt_terminal",
        record_terminal,
    )
    chat_worker._run_chat_task(task)

    release.assert_called_once_with(71, "queued-owner")
    record_terminal.assert_called_once_with(task, "task.failed")
    work.assert_not_called()
    failed = [p for e, p in events if e == "task.failed"]
    assert len(failed) == 1
    assert failed[0]["failure_code"] == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    assert failed[0]["thread_id"] == task.thread_id
    assert failed[0]["task_id"] == task.task_id
    assert failed[0]["request_id"] == task.request_id
    assert failed[0]["attempt_id"] == task.attempt_id
    assert failed[0]["latest_turn_message_id"] == 51
    assert failed[0]["turn_id"] == task.turn_id
    assert failed[0]["failed_after_state"] == TaskLifecycleState.QUEUED.value
    assert failed[0]["provider_request_started"] is False
    assert failed[0]["first_output_observed"] is False
    assert "runtime_status" not in failed[0]
    assert failed[0]["completion_truth"] == {
        "accepted": True,
        "attempted": False,
        "fallback_attempted": False,
        "executed": False,
        "completed": False,
    }
    assert not any(e in {"task.completed", "task.cancelled"} for e, _ in events)
    assert {k: getattr(task, k) for k in snapshot} == snapshot


@pytest.mark.parametrize("age", [0, 719, None])
def test_future_or_legacy_queue_task_keeps_existing_work_path(worker, age):
    task, snapshot = _task(age)
    events, work, release, _ = worker
    with pytest.raises(_WorkReached):
        chat_worker._run_chat_task(task)

    assert work.call_count == 1
    assert work.call_args.args[0] is task
    release.assert_called_once_with(71, "queued-owner")
    assert not any(e in {"task.completed", "task.failed", "task.cancelled"} for e, _ in events)
    assert {k: getattr(task, k) for k in snapshot} == snapshot
    if age is None:
        assert "accepted_at" not in task.to_dict()


@pytest.mark.parametrize(
    "dedupe_lookup",
    ["_find_assistant_message_for_turn", "_find_assistant_message_id_by_turn_id"],
)
def test_existing_durable_completion_precedes_queue_expiry(worker, monkeypatch, dedupe_lookup):
    task, _ = _task(721)
    events, work, release, _ = worker
    monkeypatch.setattr(chat_worker, dedupe_lookup, lambda **k: 52)
    monkeypatch.setattr(
        chat_worker, "_record_chat_completion_attempt_link", lambda *_a: True
    )
    chat_worker._run_chat_task(task)

    completed = [p for e, p in events if e == "task.completed"]
    assert len(completed) == 1
    assert completed[0]["message_id"] == 52
    assert not any(e in {"task.failed", "task.cancelled"} for e, _ in events)
    work.assert_not_called()
    release.assert_called_once_with(71, "queued-owner")


def test_explicit_cancellation_precedes_queue_expiry(worker, monkeypatch):
    task, _ = _task(721)
    events, work, release, cleared = worker
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda _: True)
    record_terminal = Mock(return_value=True)
    monkeypatch.setattr(
        chat_worker,
        "_record_chat_completion_attempt_terminal",
        record_terminal,
    )
    chat_worker._run_chat_task(task)

    cancelled = [p for e, p in events if e == "task.cancelled"]
    assert len(cancelled) == 1
    record_terminal.assert_called_once_with(task, "task.cancelled")
    assert cancelled[0]["thread_id"] == 71
    assert not any(e in {"task.failed", "task.completed"} for e, _ in events)
    work.assert_not_called()
    cleared.assert_called_once_with(task.task_id)
    release.assert_called_once_with(71, "queued-owner")


@pytest.mark.parametrize("field,value", [
    ("terminal_deadline_at", None),
    ("work_deadline_at", "invalid"),
])
def test_malformed_deadline_cannot_start_work(worker, field, value):
    task, _ = _task(0)
    # Model an invalid in-memory task; canonical queue decoding rejects this
    # payload earlier. The worker must not repair or refresh its authority.
    setattr(task, field, value)
    events, work, release, _ = worker
    chat_worker._run_chat_task(task)
    work.assert_not_called()
    release.assert_called_once_with(71, "queued-owner")
    failed = [payload for event, payload in events if event == "task.failed"]
    assert len(failed) == 1
    assert failed[0]["error_type"] == "ValueError"
    assert "failure_code" not in failed[0]
    assert not any(event in {"task.completed", "task.cancelled"} for event, _ in events)
    assert getattr(task, field) == value
