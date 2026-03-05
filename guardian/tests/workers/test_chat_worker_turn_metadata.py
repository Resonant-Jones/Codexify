from __future__ import annotations

import uuid

from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


def _task_with_turn_id() -> ChatCompletionTask:
    turn_id = str(uuid.uuid4())
    return ChatCompletionTask(
        task_id="task-1",
        thread_id=123,
        origin=f"test|turn_id={turn_id}",
    )


def test_metadata_persist_failure_does_not_fail_task(monkeypatch, caplog):
    published: list[str] = []

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_: True)
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *args, **kwargs: {"message_id": 77, "provider": "local"},
    )
    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, _data: published.append(event_type),
    )

    caplog.set_level("WARNING")
    chat_worker._run_chat_task(_task_with_turn_id())

    assert "task.completed" in published
    assert "task.failed" not in published
    assert "completion_turn_metadata_missing" in caplog.text


def test_missing_assistant_message_id_still_fails_task(monkeypatch):
    published: list[str] = []

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_: True)
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *args, **kwargs: {"message_id": None},
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, _data: published.append(event_type),
    )

    chat_worker._run_chat_task(_task_with_turn_id())

    assert "task.failed" in published
    assert "task.completed" not in published
def test_metadata_persistence_failure_is_non_fatal(monkeypatch):
    events: list[str] = []
    run_calls: list[bool] = []

    def fake_run_chat_completion_task(task, **kwargs):
        run_calls.append(bool(kwargs.get("persist_assistant_message")))
        return {"message_id": 321, "provider": "local", "model": "x"}

    monkeypatch.setattr(
        chat_worker, "run_chat_completion_task", fake_run_chat_completion_task
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(
        chat_worker,
        "release_turn_lock",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        lambda **_kwargs: False,
    )

    def fake_publish(_task_id: str, event_type: str, _data: dict):
        events.append(event_type)

    monkeypatch.setattr(chat_worker, "_safe_publish", fake_publish)

    task = ChatCompletionTask(thread_id=10, origin="api|turn_id=11111111-1111-1111-1111-111111111111")
    chat_worker._run_chat_task(task)

    assert run_calls == [True]
    assert "task.completed" in events
    assert "task.failed" not in events
