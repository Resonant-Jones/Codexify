from __future__ import annotations

from typing import Any

from guardian.tasks.types import ChatCompletionTask, task_from_dict
from guardian.workers import chat_worker

TURN_ID = "11111111-1111-4111-8111-111111111111"


class _FakeRedis:
    def __init__(self) -> None:
        self._values: dict[str, bytes] = {}

    def setex(self, name: str, _ttl: int, value: str) -> bool:
        self._values[name] = str(value).encode("utf-8")
        return True

    def get(self, name: str) -> bytes | None:
        return self._values.get(name)


def _isolate_turn_anchor(monkeypatch) -> _FakeRedis:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(chat_worker, "get_redis_client", lambda: fake_redis)
    return fake_redis


def _build_task_payload(
    *,
    task_id: str = "task-1",
    latest_turn_message_id: int = 4,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "type": "chat_completion",
        "created_at": "2026-04-02T00:00:00+00:00",
        "origin": f"api:chat.complete|turn_id={TURN_ID}",
        "thread_id": 7,
        "provider": "local",
        "model": "test-model",
        "latest_turn_message_id": latest_turn_message_id,
    }


def test_worker_preserves_latest_turn_message_id_through_completion(
    monkeypatch,
):
    _isolate_turn_anchor(monkeypatch)
    task = task_from_dict(_build_task_payload())
    assert isinstance(task, ChatCompletionTask)
    assert task.latest_turn_message_id == 4

    published: list[tuple[str, dict[str, Any]]] = []
    observed_target_ids: list[int | None] = []

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_: True)
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_for_turn",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_persist_turn_id_metadata",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_emit_live_event",
        lambda *_args, **_kwargs: None,
    )

    def fake_run_chat_completion_task(task, **_kwargs):
        observed_target_ids.append(
            getattr(task, "latest_turn_message_id", None)
        )
        return {
            "message_id": 42,
            "provider": "local",
            "model": "test-model",
            "assistant_text": "answer B",
            "selection_source": "default",
            "latest_turn_message_id": 4,
            "retrieval_query": "question B",
            "retrieval_target": "latest_turn",
            "retrieval_query_matches_latest_turn": True,
            "payload_summary": {"message_count": 4},
        }

    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        fake_run_chat_completion_task,
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert observed_target_ids == [4]
    assert "task.running" in event_types
    assert "task.completed" in event_types
    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload["latest_turn_message_id"] == 4
    assert completed_payload["retrieval_query"] == "question B"
    assert completed_payload["retrieval_target"] == "latest_turn"
    assert completed_payload["retrieval_query_matches_latest_turn"] is True
    assert "task.failed" not in event_types


def test_worker_missing_target_turn_surfaces_explicit_failure(
    monkeypatch,
):
    _isolate_turn_anchor(monkeypatch)
    task = task_from_dict(_build_task_payload(latest_turn_message_id=99))
    assert isinstance(task, ChatCompletionTask)

    published: list[tuple[str, dict[str, Any]]] = []
    live_events: list[tuple[str, dict[str, Any]]] = []

    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_: True)
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_for_turn",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_find_assistant_message_id_by_turn_id",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_emit_live_event",
        lambda event_type, payload: live_events.append(
            (event_type, dict(payload or {}))
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("thread_target_turn_missing")
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        ),
    )

    chat_worker._run_chat_task(task)

    event_types = [event_type for event_type, _payload in published]
    assert "task.failed" in event_types
    failure_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.failed"
    )
    assert failure_payload["latest_turn_message_id"] == 99
    assert "thread_target_turn_missing" in failure_payload["error"]
    assert live_events
    assert live_events[-1][1]["latest_turn_message_id"] == 99
