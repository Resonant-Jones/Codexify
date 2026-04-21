from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from guardian.tasks.types import ChatCompletionTask
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


def _build_task(
    *,
    task_id: str,
    thread_id: int = 7,
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
        task_id=task_id,
        thread_id=thread_id,
        provider="groq",
        model="mock-model",
        selection_source="explicit",
        origin=f"api:chat.complete|turn_id={TURN_ID}",
    )
    task.turn_id = TURN_ID
    task.turn_lock_owner = task_id
    task.latest_turn_message_id = 2
    return task


def _prepare_worker_harness(
    monkeypatch,
) -> list[tuple[str, dict[str, Any]]]:
    published: list[tuple[str, dict[str, Any]]] = []
    _isolate_turn_anchor(monkeypatch)

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
        lambda messages, bundle, provider, model, **_kwargs: {
            "message_count": len(messages),
            "resolved_provider": provider,
            "resolved_model": model,
        },
    )
    monkeypatch.setattr(chat_worker, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "get_settings",
        chat_worker.get_settings,
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "validate_llm_config",
        chat_worker.validate_llm_config,
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "ContextBroker",
        chat_worker.ContextBroker,
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "chat_with_ai",
        lambda *args, **kwargs: chat_worker.chat_with_ai(*args, **kwargs),
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "stream_local",
        lambda *args, **kwargs: chat_worker.stream_local(*args, **kwargs),
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "build_guardian_system_prompt",
        chat_worker.build_guardian_system_prompt,
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "build_context_system_message_with_meta",
        chat_worker._build_context_system_message_with_meta_compat,
    )
    monkeypatch.setattr(
        chat_worker,
        "build_provider_truth",
        lambda provider, settings, **kwargs: {"provider": provider, **kwargs},
    )
    monkeypatch.setattr(
        chat_worker,
        "_fallback_provider_candidates",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "_command_bus_app",
        lambda: SimpleNamespace(name="command-bus-app"),
    )
    monkeypatch.setattr(
        chat_worker,
        "stream_local",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("stream_local should not be used")
        ),
    )

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "What changed?"}],
            "groq",
            "mock-model",
            {"_prompt_meta": {}},
            {"source_mode": "project", "effective_policy": None},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    return published


def test_worker_surfaces_tool_loop_metadata_on_completion(
    monkeypatch,
):
    published = _prepare_worker_harness(monkeypatch)
    task = _build_task(task_id="task-worker-tool-success")

    command_calls: list[dict[str, Any]] = []

    def _execute_invoke(*, payload, **_kwargs):
        command_calls.append({"payload": payload})
        return {
            "run_id": "run-worker-123",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/api/guardian/commands/runs/run-worker-123/events?after_seq=0",
            "inline_result": {"summary": "command result"},
        }

    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "execute_invoke",
        _execute_invoke,
    )

    chat_calls: list[list[dict[str, Any]]] = []

    def _chat_with_ai(messages, **_kwargs):
        snapshot = [dict(message) for message in messages]
        chat_calls.append(snapshot)
        if len(chat_calls) == 1:
            return (
                '{"type":"tool_decision","command_id":"op::echo","arguments":'
                '{"body":{"value":"alpha"}}}'
            )
        return "final answer"

    monkeypatch.setattr(chat_worker, "chat_with_ai", _chat_with_ai)

    chat_worker._run_chat_task(task)

    assert len(command_calls) == 1
    assert len(chat_calls) == 2
    assert command_calls[0]["payload"].command_id == "op::echo"

    completed_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.completed"
    )
    assert completed_payload["messageId"] == 2
    assert completed_payload["requestId"] == task.task_id
    assert completed_payload["toolTurnId"] is not None
    assert completed_payload["toolTurnState"] == "completed"
    assert completed_payload["loopStopReason"] == "tool_turn_completed"
    assert completed_payload["commandRunId"] == "run-worker-123"
    assert completed_payload["message_id"] == 42


def test_worker_surfaces_bounded_failure_metadata_on_tool_execution_error(
    monkeypatch,
):
    published = _prepare_worker_harness(monkeypatch)
    task = _build_task(task_id="task-worker-tool-failure")

    command_calls: list[dict[str, Any]] = []

    def _execute_invoke(*args, **kwargs):
        command_calls.append({"args": args, "kwargs": kwargs})
        raise RuntimeError("command bus unavailable")

    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "execute_invoke",
        _execute_invoke,
    )
    monkeypatch.setattr(
        chat_worker,
        "chat_with_ai",
        lambda *_args, **_kwargs: (
            '{"type":"tool_decision","command_id":"op::echo","arguments":'
            '{"body":{"value":"alpha"}}}'
        ),
    )

    chat_worker._run_chat_task(task)

    assert len(command_calls) == 1
    assert any(
        event_type == "task.failed" for event_type, _payload in published
    )
    failure_payload = next(
        payload
        for event_type, payload in published
        if event_type == "task.failed"
    )
    assert failure_payload["toolTurnId"] is not None
    assert failure_payload["toolTurnState"] == "failed"
    assert failure_payload["loopStopReason"] == "tool_command_failed"
    assert failure_payload.get("commandRunId") is None
