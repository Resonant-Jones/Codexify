from __future__ import annotations

from typing import Any

from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


class _FakeRedis:
    def __init__(self) -> None:
        self._values: dict[str, bytes] = {}

    def setex(self, name: str, _ttl: int, value: str) -> bool:
        self._values[name] = str(value).encode("utf-8")
        return True

    def get(self, name: str) -> bytes | None:
        return self._values.get(name)


def _isolate_turn_anchor(monkeypatch) -> None:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(chat_worker, "get_redis_client", lambda: fake_redis)


def _build_task(
    *,
    task_id: str = "task-1",
    turn_id: str = "11111111-1111-4111-8111-111111111111",
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        task_id=task_id,
        thread_id=7,
        provider="local",
        model="test-model",
        origin=f"api:chat.complete|turn_id={turn_id}",
    )
    task.turn_id = turn_id
    task.turn_lock_owner = task_id
    return task


def test_metadata_persistence_failure_is_non_fatal(monkeypatch):
    _isolate_turn_anchor(monkeypatch)
    task = _build_task(task_id="task-meta-warning")
    published: list[tuple[str, str, dict[str, Any]]] = []

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: {
            "message_id": 42,
            "provider": "local",
            "model": "test-model",
            "selection_source": "default",
            "catalog_version_hash": "abc123",
        },
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda task_id, event_type, data: published.append(
            (task_id, event_type, data)
        ),
    )
    monkeypatch.setattr(
        chat_worker, "_persist_turn_id_metadata", lambda **_kwargs: False
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert "task.completed" in event_types
    assert "task.failed" not in event_types


def test_duplicate_turn_short_circuits_new_completion(monkeypatch):
    _isolate_turn_anchor(monkeypatch)
    task = _build_task(task_id="task-duplicate")
    published: list[tuple[str, str, dict[str, Any]]] = []

    run_completion_calls = {"count": 0}

    def _run_completion(*_args, **_kwargs):
        run_completion_calls["count"] += 1
        return {"message_id": 999}

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
    monkeypatch.setattr(
        chat_worker, "run_chat_completion_task", _run_completion
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda task_id, event_type, data: published.append(
            (task_id, event_type, data)
        ),
    )
    monkeypatch.setattr(
        chat_worker, "_find_assistant_message_for_turn", lambda **_kwargs: 55
    )

    chat_worker._run_chat_task(task)

    assert run_completion_calls["count"] == 0
    completed_payloads = [
        payload
        for _task_id, event_type, payload in published
        if event_type == "task.completed"
    ]
    assert completed_payloads
    assert completed_payloads[-1]["message_id"] == 55
    assert completed_payloads[-1]["selection_source"] == "turn_id_dedupe"


def test_missing_assistant_message_marks_task_failed_and_releases_lock(
    monkeypatch,
):
    _isolate_turn_anchor(monkeypatch)
    task = _build_task(task_id="task-missing-assistant")
    published: list[tuple[str, str, dict[str, Any]]] = []
    released: list[tuple[int, str]] = []

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: {"provider": "local", "model": "test-model"},
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda task_id, event_type, data: published.append(
            (task_id, event_type, data)
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "release_turn_lock",
        lambda thread_id, owner: released.append((thread_id, owner)) or True,
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for _task_id, event_type, _payload in published]
    assert "task.failed" in event_types
    assert released == [(task.thread_id, task.task_id)]
