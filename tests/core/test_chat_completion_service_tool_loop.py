from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


def _build_task(
    *,
    task_id: str = "task-tool-loop",
    thread_id: int = 7,
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="user-1",
        task_id=task_id,
        thread_id=thread_id,
        provider="groq",
        model="mock-model",
        origin="api:chat.complete|turn_id=11111111-1111-4111-8111-111111111111",
    )
    task.latest_turn_message_id = 2
    task.turn_id = "11111111-1111-4111-8111-111111111111"
    return task


def _seed_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: str = "groq",
    model: str = "mock-model",
):
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_sanitized_payload_summary",
        lambda messages, bundle, provider, model, **_kwargs: {
            "message_count": len(messages),
            "resolved_provider": provider,
            "resolved_model": model,
        },
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **kwargs: (
            messages,
            {
                "image_routing_path": "none",
                "image_attachment_count": 0,
                "derived_image_context_injected": False,
            },
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_task_routing_debug_metadata",
        lambda _task: {},
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_command_bus_app",
        lambda: SimpleNamespace(name="command-bus-app"),
    )

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "What changed?"}],
            provider,
            model,
            {"_prompt_meta": {}},
            {"source_mode": "project", "effective_policy": None},
        )

    monkeypatch.setattr(
        chat_completion_service,
        "build_messages_for_llm",
        _build_messages,
    )


def test_plain_answer_path_skips_command_bus(monkeypatch: pytest.MonkeyPatch):
    _seed_service(monkeypatch)
    task = _build_task()

    command_bus_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *args, **kwargs: command_bus_calls.append(
            {"args": args, "kwargs": kwargs}
        )
        or (_ for _ in ()).throw(AssertionError("command bus should not run")),
    )

    chat_calls: list[list[dict[str, Any]]] = []

    def _chat_with_ai(messages, **_kwargs):
        chat_calls.append([dict(message) for message in messages])
        return "plain answer"

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert not command_bus_calls
    assert len(chat_calls) == 1
    assert result["assistant_text"] == "plain answer"
    assert result["messageId"] == 2
    assert result["requestId"] == task.task_id
    assert result["toolTurnId"] is None
    assert result["toolTurnState"] == "idle"
    assert result["loopStopReason"] == "plain_answer"
    assert result["commandRunId"] is None
    assert result["payload_summary"]["toolTurnState"] == "idle"
    assert result["payload_summary"]["loopStopReason"] == "plain_answer"


def test_single_tool_decision_path_invokes_command_bus_once_and_reinjects_result(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch)
    task = _build_task(task_id="task-tool-decision")

    command_calls: list[dict[str, Any]] = []

    def _execute_invoke(*, payload, **_kwargs):
        command_calls.append({"payload": payload})
        return {
            "run_id": "run-123",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/api/guardian/commands/runs/run-123/events?after_seq=0",
            "inline_result": {"summary": "command result"},
        }

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
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

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert len(command_calls) == 1
    assert len(chat_calls) == 2
    assert command_calls[0]["payload"].command_id == "op::echo"
    assert result["assistant_text"] == "final answer"
    assert result["toolTurnId"] is not None
    assert result["toolTurnState"] == "completed"
    assert result["loopStopReason"] == "tool_turn_completed"
    assert result["commandRunId"] == "run-123"
    assert result["payload_summary"]["toolTurnState"] == "completed"
    assert result["payload_summary"]["loopStopReason"] == "tool_turn_completed"
    assert result["payload_summary"]["commandRunId"] == "run-123"
    assert any(
        message["content"].startswith("Tool result injection:\n")
        for message in chat_calls[1]
        if message.get("role") == "system"
    )
    assert (
        len(
            [
                message
                for message in chat_calls[1]
                if message.get("role") == "system"
                and str(message.get("content") or "").startswith(
                    "Tool result injection:\n"
                )
            ]
        )
        == 1
    )


def test_second_tool_decision_hard_stops_after_one_bounded_turn(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch)
    task = _build_task(task_id="task-tool-limit")

    command_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *args, **kwargs: command_calls.append(
            {"args": args, "kwargs": kwargs}
        )
        or {
            "run_id": "run-456",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/api/guardian/commands/runs/run-456/events?after_seq=0",
        },
    )

    chat_calls: list[list[dict[str, Any]]] = []

    def _chat_with_ai(messages, **_kwargs):
        chat_calls.append([dict(message) for message in messages])
        return (
            '{"type":"tool_decision","command_id":"op::echo","arguments":'
            '{"body":{"value":"alpha"}}}'
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert len(command_calls) == 1
    assert len(chat_calls) == 2
    assert exc.value.metadata["loopStopReason"] == "tool_turn_limit_reached"
    assert exc.value.metadata["toolTurnState"] == "limit_reached"
    assert exc.value.metadata["commandRunId"] == "run-456"


def test_tool_execution_failure_surfaces_bounded_stop_reason(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch)
    task = _build_task(task_id="task-tool-failure")

    command_calls: list[dict[str, Any]] = []

    def _execute_invoke(*args, **kwargs):
        command_calls.append({"args": args, "kwargs": kwargs})
        raise RuntimeError("command bus unavailable")

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: (
            '{"type":"tool_decision","command_id":"op::echo","arguments":'
            '{"body":{"value":"alpha"}}}'
        ),
    )

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert len(command_calls) == 1
    assert exc.value.metadata["loopStopReason"] == "tool_command_failed"
    assert exc.value.metadata["toolTurnState"] == "failed"
    assert exc.value.metadata["toolTurnId"] is not None
    assert exc.value.metadata["commandRunId"] is None
