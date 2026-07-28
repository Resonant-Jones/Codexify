from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service as service
from guardian.protocol_tokens import AcceptanceStatus
from guardian.queue.redis_queue import QueueEnqueueError
from guardian.queue.turn_lock import build_turn_lock_envelope
from guardian.tasks.types import ChatCompletionTask


def _task() -> ChatCompletionTask:
    return ChatCompletionTask(
        request_id="request-1",
        user_id="user-1",
        thread_id=1,
        latest_turn_message_id=7,
        provider="groq",
        model="model-1",
        origin="api:chat.complete|turn_id=turn-1|source_mode=project",
    )


def _lock(task: ChatCompletionTask, *, turn_id: str):
    return build_turn_lock_envelope(
        1,
        task.task_id,
        turn_id=turn_id,
        source="api:chat.complete",
    )


def _event_result(task: ChatCompletionTask, *, event_id: str | None = "evt-1"):
    return {
        "ok": True,
        "task_id": task.task_id,
        "event_type": "task.created",
        "visibility_scope": "progress",
        "terminal_visibility": False,
        "execution_continued": True,
        "event_id": event_id,
        "failure_class": None,
        "error_code": None,
        "error": None,
    }


@pytest.fixture
def immediate_redis(monkeypatch):
    monkeypatch.setattr(
        service,
        "run_with_redis_timeout",
        lambda operation, *_args, **_kwargs: operation(),
    )


def test_success_preserves_queue_event_and_serialization_contract(
    monkeypatch, immediate_redis
):
    task = _task()
    captured: dict[str, object] = {}
    lock = _lock(task, turn_id="turn-1")
    expected_payload = task.to_dict()
    monkeypatch.setattr(service, "acquire_turn_lock", lambda *_a, **_k: lock)
    monkeypatch.setattr(
        service,
        "enqueue",
        lambda queued_task, queue_name: captured.update(
            {
                "task": queued_task,
                "queue_name": queue_name,
                "payload": queued_task.to_dict(),
            }
        ),
    )
    publish = MagicMock(return_value=_event_result(task))
    monkeypatch.setattr(service.task_events, "publish_with_visibility", publish)

    result = service.enqueue_chat_completion(
        task, thread_id=1, turn_id="turn-1", request_id="request-1"
    )

    assert result.acceptance_status == AcceptanceStatus.ACCEPTED.value
    assert result.acceptance_warnings == ()
    assert result.queue_accepted is True
    assert result.degraded is False
    assert result.task_id == task.task_id
    assert captured["queue_name"] == "codexify:queue:chat"
    assert captured["payload"] == expected_payload
    assert captured["payload"]["type"] == "chat_completion"
    assert "hosted" + "_room" not in captured["payload"]
    assert "actor" + "_ref" not in captured["payload"]
    publish.assert_called_once_with(
        task.task_id,
        "task.created",
        {
            "type": "chat_completion",
            "thread_id": 1,
            "origin": task.origin,
            "turn_id": "turn-1",
            "latest_turn_message_id": 7,
        },
    )


def test_missing_event_id_is_accepted_degraded(monkeypatch, immediate_redis):
    task = _task()
    lock = _lock(task, turn_id="turn-1")
    monkeypatch.setattr(service, "acquire_turn_lock", lambda *_a, **_k: lock)
    monkeypatch.setattr(service, "enqueue", lambda *_a, **_k: None)
    monkeypatch.setattr(
        service.task_events,
        "publish_with_visibility",
        lambda *_a, **_k: _event_result(task, event_id=None),
    )

    result = service.enqueue_chat_completion(task, thread_id=1, turn_id="turn-1")

    assert result.acceptance_status == AcceptanceStatus.ACCEPTED_DEGRADED.value
    assert result.degraded is True
    assert result.acceptance_warnings == ("task_created_event_missing_event_id",)


def test_event_publish_failure_is_degraded_and_does_not_expose_cause(
    monkeypatch, immediate_redis
):
    task = _task()
    lock = _lock(task, turn_id="turn-1")
    monkeypatch.setattr(service, "acquire_turn_lock", lambda *_a, **_k: lock)
    monkeypatch.setattr(service, "enqueue", lambda *_a, **_k: None)
    monkeypatch.setattr(
        service.task_events,
        "publish_with_visibility",
        lambda *_a, **_k: {
            **_event_result(task, event_id=None),
            "ok": False,
            "error_code": "TASK_EVENT_PUBLISH_FAILED",
            "failure_class": "RuntimeError",
            "exception": RuntimeError("redis down"),
        },
    )

    result = service.enqueue_chat_completion(task, thread_id=1, turn_id="turn-1")

    assert result.acceptance_status == AcceptanceStatus.ACCEPTED_DEGRADED.value
    assert result.task_created_event.raised_publish_error is True
    assert result.task_created_event.cause_class == "RuntimeError"
    assert "redis down" not in repr(result)


def test_active_lock_does_not_publish(monkeypatch, immediate_redis):
    task = _task()
    monkeypatch.setattr(service, "acquire_turn_lock", lambda *_a, **_k: None)
    monkeypatch.setattr(service, "_recover_orphaned_turn_lock", lambda *_: False)
    enqueue = MagicMock()
    monkeypatch.setattr(service, "enqueue", enqueue)

    with pytest.raises(service.ChatCompletionEnqueueError) as exc_info:
        service.enqueue_chat_completion(task, thread_id=1, turn_id="turn-1")

    assert exc_info.value.reason == "turn_in_flight"
    enqueue.assert_not_called()


def test_concurrent_duplicate_requests_publish_once(monkeypatch, immediate_redis):
    tasks = [_task(), _task()]
    held = threading.Lock()
    published: list[str] = []

    def acquire(task_id, *_args, **_kwargs):
        if not held.acquire(blocking=False):
            return None
        return _lock(tasks[0] if task_id == 1 else tasks[1], turn_id="turn-1")

    def enqueue(task, _queue_name):
        published.append(task.task_id)

    monkeypatch.setattr(service, "acquire_turn_lock", acquire)
    monkeypatch.setattr(service, "enqueue", enqueue)
    monkeypatch.setattr(
        service.task_events,
        "publish_with_visibility",
        lambda task_id, *_a, **_k: {
            **_event_result(tasks[0]),
            "task_id": task_id,
        },
    )

    def submit(task):
        try:
            return service.enqueue_chat_completion(
                task, thread_id=1, turn_id="turn-1"
            )
        except service.ChatCompletionEnqueueError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(submit, tasks))

    assert len(published) == 1
    assert sum(isinstance(result, service.ChatCompletionEnqueueResult) for result in results) == 1
    failures = [
        result
        for result in results
        if isinstance(result, service.ChatCompletionEnqueueError)
    ]
    assert len(failures) == 1
    assert failures[0].reason == "turn_in_flight"


def test_stale_terminal_lock_is_recovered(monkeypatch, immediate_redis):
    task = _task()
    stale = build_turn_lock_envelope(1, "stale-task", turn_id="old-turn")
    fresh = _lock(task, turn_id="turn-1")
    acquire_calls = 0
    cleared: list[tuple[int, object]] = []
    orphan_events: list[tuple[str, dict[str, object]]] = []

    def acquire(*_args, **_kwargs):
        nonlocal acquire_calls
        acquire_calls += 1
        return None if acquire_calls == 1 else fresh

    monkeypatch.setattr(service, "acquire_turn_lock", acquire)
    monkeypatch.setattr(service, "get_turn_lock", lambda *_: stale)
    monkeypatch.setattr(service, "turn_lock_is_stale", lambda *_: True)
    monkeypatch.setattr(
        service,
        "_task_terminal_event",
        lambda *_: {"state": "terminal", "reason": "completed"},
    )
    monkeypatch.setattr(
        service,
        "clear_turn_lock",
        lambda thread_id, expected=None: cleared.append((thread_id, expected))
        or True,
    )
    monkeypatch.setattr(service.dependencies, "chatlog_db", MagicMock())
    monkeypatch.setattr(
        service.event_bus,
        "emit_event",
        lambda name, payload: orphan_events.append((name, payload)),
    )
    monkeypatch.setattr(service, "enqueue", lambda *_a, **_k: None)
    monkeypatch.setattr(
        service.task_events,
        "publish_with_visibility",
        lambda *_a, **_k: _event_result(task),
    )

    result = service.enqueue_chat_completion(task, thread_id=1, turn_id="turn-1")

    assert result.acceptance_status == AcceptanceStatus.ACCEPTED.value
    assert acquire_calls == 2
    assert len(cleared) == 1
    assert orphan_events[0][0] == "chat.orphaned_turn_recovered"


def test_queue_failure_releases_lock_and_returns_safe_typed_failure(
    monkeypatch, immediate_redis
):
    task = _task()
    lock = _lock(task, turn_id="turn-1")
    released: list[tuple[int, object]] = []
    cause = RuntimeError("redis down")
    error = QueueEnqueueError("codexify:queue:chat", cause=cause)
    monkeypatch.setattr(service, "acquire_turn_lock", lambda *_a, **_k: lock)
    monkeypatch.setattr(service, "enqueue", MagicMock(side_effect=error))
    monkeypatch.setattr(
        service,
        "release_turn_lock",
        lambda thread_id, owner: released.append((thread_id, owner)),
    )

    with pytest.raises(service.ChatCompletionEnqueueError) as exc_info:
        service.enqueue_chat_completion(task, thread_id=1, turn_id="turn-1")

    exc = exc_info.value
    assert exc.reason == "queue_unavailable"
    assert exc.error_code == "CHAT_COMPLETE_ENQUEUE_FAILED"
    assert exc.queue_name == "codexify:queue:chat"
    assert exc.cause_class == "RuntimeError"
    assert "redis down" not in str(exc)
    assert released == [(1, task.task_id)]
