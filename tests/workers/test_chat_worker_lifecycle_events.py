from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from guardian.tasks.types import ChatCompletionTask, TaskLifecycleState
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


class _TokenStream:
    def __iter__(self):
        return iter(["Hel", "lo"])

    def close(self):
        return None


def _isolate_turn_anchor(monkeypatch) -> _FakeRedis:
    fake_redis = _FakeRedis()
    monkeypatch.setattr(chat_worker, "get_redis_client", lambda: fake_redis)
    return fake_redis


def _build_task(
    *,
    task_id: str = "task-lifecycle",
    thread_id: int = 7,
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        task_id=task_id,
        thread_id=thread_id,
        provider="local",
        model="test-model",
        selection_source="explicit",
        origin=f"api:chat.complete|turn_id={TURN_ID}",
    )
    task.turn_id = TURN_ID
    task.turn_lock_owner = task_id
    return task


def test_chat_worker_emits_lifecycle_states_in_order(monkeypatch):
    _isolate_turn_anchor(monkeypatch)
    task = _build_task()

    published: list[tuple[str, dict[str, Any]]] = []

    mock_db = SimpleNamespace(
        create_message=lambda *_args, **_kwargs: 42,
        write_audit_log=lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        )
        or {"ok": True},
    )
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
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
        "_persist_message_extra_meta",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *_, **__: None)
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "build_sanitized_payload_summary",
        lambda *args, **kwargs: {"message_count": 2},
    )
    monkeypatch.setattr(chat_worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        chat_worker,
        "build_provider_truth",
        lambda provider, settings, **kwargs: {"provider": provider, **kwargs},
    )

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "hello"}],
            "local",
            "test-model",
            {},
            {},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker,
        "stream_local",
        lambda *_args, **_kwargs: _TokenStream(),
    )
    monkeypatch.setattr(
        chat_worker,
        "chat_with_ai",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("fallback should not be used")
        ),
    )

    chat_worker._run_chat_task(task)

    state_sequence = [
        payload["state"]
        for event_type, payload in published
        if event_type == "task.state"
    ]
    assert state_sequence == [
        TaskLifecycleState.QUEUED.value,
        TaskLifecycleState.AWAITING_MODEL.value,
        TaskLifecycleState.AWAITING_FIRST_TOKEN.value,
        TaskLifecycleState.STREAMING.value,
        TaskLifecycleState.COMPLETED.value,
    ]

    event_types = [event_type for event_type, _payload in published]
    assert "task.running" in event_types
    assert "task.progress" in event_types
    assert "task.completed" in event_types

    streaming_index = next(
        index
        for index, (event_type, payload) in enumerate(published)
        if event_type == "task.state"
        and payload["state"] == TaskLifecycleState.STREAMING.value
    )
    first_progress_index = event_types.index("task.progress")
    completed_state_index = next(
        index
        for index, (event_type, payload) in enumerate(published)
        if event_type == "task.state"
        and payload["state"] == TaskLifecycleState.COMPLETED.value
    )
    terminal_index = event_types.index("task.completed")

    assert streaming_index < first_progress_index
    assert completed_state_index < terminal_index


def test_chat_worker_completed_event_persists_retrieval_provenance(monkeypatch):
    _isolate_turn_anchor(monkeypatch)
    task = _build_task(task_id="task-provenance")

    published: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(
            create_message=lambda *_args, **_kwargs: 42,
            write_audit_log=lambda *_args, **_kwargs: None,
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, data: published.append(
            (event_type, dict(data or {}))
        )
        or {"ok": True},
    )
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
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
        "_persist_message_extra_meta",
        lambda **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_worker,
        "_schedule_assistant_message_audio_generation",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *_, **__: None)
    monkeypatch.setattr(
        chat_worker,
        "run_chat_completion_task",
        lambda *_args, **_kwargs: {
            "message_id": 42,
            "provider": "local",
            "model": "test-model",
            "retrieval_provenance": {
                "requested_source_mode": "Personal_Knowledge",
                "normalized_source_mode": "personal_knowledge",
                "source_hit_counts": {
                    "semantic_total": 2,
                    "thread_semantic": 0,
                    "obsidian_semantic": 2,
                    "other_semantic": 0,
                    "project_documents": 0,
                    "thread_documents": 0,
                    "global_documents": 0,
                    "other_documents": 0,
                    "memory": 0,
                    "graph": 0,
                },
                "retrieval_status": "obsidian_only_success",
            },
        },
    )

    chat_worker._run_chat_task(task)

    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload["retrieval_provenance"]["retrieval_status"] == (
        "obsidian_only_success"
    )
    assert completed_payload["retrieval_provenance"][
        "requested_source_mode"
    ] == ("Personal_Knowledge")
