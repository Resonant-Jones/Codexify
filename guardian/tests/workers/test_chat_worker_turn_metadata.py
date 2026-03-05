from __future__ import annotations

from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


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
