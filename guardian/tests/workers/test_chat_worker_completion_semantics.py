from __future__ import annotations

from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker

TURN_ID = "11111111-1111-4111-8111-111111111111"


def _build_task(
    *, thread_id: int = 11, turn_id: str = TURN_ID
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        thread_id=thread_id,
        provider="groq",
        model="moonshotai-kimi-k2-instruct-9050",
    )
    task.turn_id = turn_id
    task.turn_lock_owner = f"lock-{thread_id}"
    return task


def test_metadata_persistence_failure_is_non_fatal(monkeypatch):
    published: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker, "_safe_emit_live_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_a, **_k: False)
    monkeypatch.setattr(
        chat_worker, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_a, **_k: {
            "message_id": 501,
            "provider": "groq",
            "model": "moonshotai-kimi-k2-instruct-9050",
        },
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        lambda **_kwargs: False,
    )

    chat_worker._run_chat_task(_build_task())

    event_types = [event_type for event_type, _payload in published]
    assert "task.completed" in event_types
    assert "task.failed" not in event_types


def test_worker_failure_before_assistant_emit_marks_failed_and_emits_completion_error(
    monkeypatch,
):
    published: list[tuple[str, dict]] = []
    mirrored_live_events: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_emit_live_event",
        lambda event_type, payload: mirrored_live_events.append(
            (event_type, dict(payload or {}))
        ),
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_a, **_k: False)
    monkeypatch.setattr(
        chat_worker, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )

    def _raise_failure(*_a, **_k):
        raise RuntimeError("provider crashed")

    monkeypatch.setattr(chat_worker, "run_chat_completion_task", _raise_failure)

    task = _build_task(thread_id=17)
    chat_worker._run_chat_task(task)

    assert any(event_type == "task.failed" for event_type, _ in published)
    assert any(
        event_type == "completion.error"
        for event_type, _ in mirrored_live_events
    )
    completion_error_payload = next(
        payload
        for event_type, payload in mirrored_live_events
        if event_type == "completion.error"
    )
    assert completion_error_payload.get("task_id") == task.task_id
    assert completion_error_payload.get("thread_id") == 17


def test_duplicate_turn_is_prevented_before_new_completion(monkeypatch):
    published: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker, "_safe_emit_live_event", lambda *a, **k: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_a, **_k: False)
    monkeypatch.setattr(
        chat_worker, "release_turn_lock", lambda *_a, **_k: True
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: 90210,
    )

    completion_called = False

    def _should_not_run(*_a, **_k):
        nonlocal completion_called
        completion_called = True
        return {"message_id": 1}

    monkeypatch.setattr(
        chat_worker, "run_chat_completion_task", _should_not_run
    )

    chat_worker._run_chat_task(_build_task(thread_id=23))

    assert completion_called is False
    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload.get("message_id") == 90210
    assert completed_payload.get("deduplicated") is True
