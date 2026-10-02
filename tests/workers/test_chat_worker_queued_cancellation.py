from unittest.mock import Mock

import pytest

from guardian.queue import turn_lock
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


class _StopWorker(BaseException):
    pass


class _InlineExecutor:
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def submit(self, fn, *args):
        fn(*args)


class _LockRedis:
    """Exercise canonical lock compare-and-delete without external Redis."""

    def __init__(self):
        self.values = {}

    def set(self, key, value, *, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)


@pytest.mark.parametrize("lock_owner", ["cancelled-task", "successor-task"])
def test_dequeued_cancellation_releases_only_its_turn_lock(monkeypatch, lock_owner):
    task = ChatCompletionTask(
        user_id="local",
        thread_id=71,
        task_id="cancelled-task",
        latest_turn_message_id=52,
    )
    task.turn_id = "authored-turn"
    task.turn_lock_owner = task.task_id
    client = _LockRedis()
    monkeypatch.setattr(turn_lock, "_with_reconnect", lambda fn: fn(client))
    lock = turn_lock.acquire_turn_lock(
        task.thread_id,
        lock_owner,
        turn_id=task.turn_id,
        return_envelope=True,
        ttl_seconds=840,
    )
    assert lock is not None
    events = []
    provider_work = Mock()
    persistence = Mock()
    cleared = Mock()
    payloads = iter(
        [{**task.to_dict(), "turn_id": task.turn_id, "turn_lock_owner": task.task_id}]
    )

    def dequeue(*args, **kwargs):
        try:
            return next(payloads)
        except StopIteration:
            raise _StopWorker

    monkeypatch.setattr(chat_worker, "_initialize_worker", lambda: None)
    monkeypatch.setattr(chat_worker, "_publish_worker_heartbeat", lambda *a: None)
    monkeypatch.setattr(chat_worker, "ThreadPoolExecutor", _InlineExecutor)
    monkeypatch.setattr(chat_worker, "dequeue", dequeue)
    monkeypatch.setattr(
        chat_worker, "is_cancelled", lambda task_id: task_id == task.task_id
    )
    monkeypatch.setattr(chat_worker, "clear_cancelled", cleared)
    monkeypatch.setattr(
        chat_worker, "_find_assistant_message_for_turn", lambda **k: None
    )
    monkeypatch.setattr(chat_worker, "run_chat_completion_task", provider_work)
    monkeypatch.setattr(
        chat_worker.dependencies, "chatlog_db", Mock(create_message=persistence)
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda task_id, event, data: events.append((task_id, event, dict(data)))
        or {"ok": True},
    )

    with pytest.raises(_StopWorker):
        chat_worker.run_forever()

    cancelled = [e for e in events if e[1] == "task.cancelled"]
    assert len(cancelled) == 1
    assert cancelled[0][0] == task.task_id
    provider_work.assert_not_called()
    persistence.assert_not_called()
    cleared.assert_called_once_with(task.task_id)
    if lock_owner == task.task_id:
        assert turn_lock.get_turn_lock(task.thread_id) is None
        assert turn_lock.acquire_turn_lock(task.thread_id, "next-task")
    else:
        assert turn_lock.get_turn_lock(task.thread_id) == lock
        assert not turn_lock.acquire_turn_lock(task.thread_id, "next-task")
    assert cancelled[0][2]["thread_id"] == task.thread_id
    assert cancelled[0][2]["turn_id"] == task.turn_id
    assert not any(e[1] in {"task.completed", "task.failed"} for e in events)
