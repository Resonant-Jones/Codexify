from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.protocol_tokens import LoopStopReason, ToolTurnState
from guardian.tasks.types import ChatCompletionTask


def _setup_runtime(monkeypatch: pytest.MonkeyPatch):
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 7,
        "user_id": "user-1",
        "project_id": 42,
    }
    mock_chatlog_db.list_messages.return_value = [
        {"id": 11, "role": "user", "content": "Hello"}
    ]

    monkeypatch.setattr(
        chat_completion_service,
        "_build_candidate_trace",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_apply_image_attachment_routing",
        lambda messages, **kwargs: (
            list(messages),
            {
                "image_routing_path": "text",
                "image_attachment_count": 0,
                "derived_image_context_injected": False,
            },
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_task_routing_debug_metadata",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_resolve_command_bus_app",
        lambda: object(),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_sanitized_payload_summary",
        lambda messages, bundle, **kwargs: {
            "message_count": len(messages),
            "bundle_keys": sorted(bundle.keys())
            if isinstance(bundle, dict)
            else [],
        },
    )
    monkeypatch.setattr(
        chat_completion_service,
        "validate_llm_config",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(
            LLM_PROVIDER="openai",
            LLM_MODEL="gpt-4o",
            DEFAULT_LOCAL_MODEL="gpt-4o",
            LOCAL_LLM_MODEL="gpt-4o",
            LOCAL_CHAT_MODEL="gpt-4o",
            ALLOW_CLOUD_PROVIDERS=True,
        ),
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "chatlog_db",
        mock_chatlog_db,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "CHAT_PROVIDER",
        "openai",
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_vector_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_memory_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_sensors",
        None,
        raising=False,
    )

    return mock_chatlog_db


def _build_task(
    *, request_id: str, latest_turn_message_id: int
) -> ChatCompletionTask:
    return ChatCompletionTask(
        user_id="user-1",
        thread_id=7,
        request_id=request_id,
        latest_turn_message_id=latest_turn_message_id,
        provider="openai",
        model="gpt-4o",
        depth_mode="normal",
    )


def test_plain_completion_does_not_invoke_command_bus(
    monkeypatch: pytest.MonkeyPatch,
):
    _setup_runtime(monkeypatch)

    async def _build_messages_for_llm(_task, **_kwargs):
        return (
            [{"role": "user", "content": "Hello"}],
            "openai",
            "gpt-4o",
            {"_prompt_meta": {}},
            {"latest_turn_message_id": 11, "source_mode": "project"},
        )

    chat_calls: list[list[dict[str, object]]] = []

    monkeypatch.setattr(
        chat_completion_service,
        "_build_messages_for_llm_compat",
        _build_messages_for_llm,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda messages, **kwargs: chat_calls.append(list(messages))
        or "plain assistant answer",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("command bus should not be invoked")
        ),
    )

    task = _build_task(request_id="req-plain", latest_turn_message_id=11)
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert result["assistant_text"] == "plain assistant answer"
    assert result["requestId"] == "req-plain"
    assert result["messageId"] == 11
    assert result["toolTurnId"] is None
    assert result["toolTurnState"] == ToolTurnState.NOT_STARTED.value
    assert result["loopStopReason"] == LoopStopReason.MODEL_FINAL_ANSWER.value
    assert result["commandRunId"] is None
    assert len(chat_calls) == 1


def test_tool_decision_executes_command_bus_once_and_reinjects_result(
    monkeypatch: pytest.MonkeyPatch,
):
    _setup_runtime(monkeypatch)

    async def _build_messages_for_llm(_task, **_kwargs):
        return (
            [{"role": "user", "content": "Switch me"}],
            "openai",
            "gpt-4o",
            {"_prompt_meta": {}},
            {"latest_turn_message_id": 11, "source_mode": "project"},
        )

    chat_calls: list[list[dict[str, object]]] = []
    invoke_calls: list[dict[str, object]] = []

    responses = iter(
        [
            {
                "kind": "tool_decision",
                "tool_decision": {
                    "command_id": "guardian.profile.switch",
                    "arguments": {
                        "path_params": {"thread_id": 7},
                        "body": {"profile_id": "local"},
                    },
                },
            },
            "final assistant answer",
        ]
    )

    async def _fake_execute_invoke(**kwargs):
        invoke_calls.append(dict(kwargs))
        return {
            "run_id": "run-123",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/api/guardian/commands/runs/run-123/events?after_seq=0",
            "inline_result": {"ok": True},
            "policy_warnings": [],
        }

    monkeypatch.setattr(
        chat_completion_service,
        "_build_messages_for_llm_compat",
        _build_messages_for_llm,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda messages, **kwargs: chat_calls.append(list(messages))
        or next(responses),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        _fake_execute_invoke,
    )

    task = _build_task(request_id="req-tool", latest_turn_message_id=11)
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert result["assistant_text"] == "final assistant answer"
    assert result["requestId"] == "req-tool"
    assert result["messageId"] == 11
    assert result["toolTurnState"] == ToolTurnState.COMPLETED.value
    assert result["loopStopReason"] == LoopStopReason.TOOL_TURN_COMPLETED.value
    assert result["commandRunId"] == "run-123"
    assert result["toolTurnId"]
    assert result["messageId"] != result["requestId"]
    assert len(chat_calls) == 2
    assert len(invoke_calls) == 1
    reinjected_messages = chat_calls[1]
    assert any(
        str(message.get("role")) == "system"
        and "Bounded tool result for one final assistant answer"
        in str(message.get("content"))
        for message in reinjected_messages
    )
    tool_loop = result["tool_loop"]
    assert tool_loop["toolTurnState"] == ToolTurnState.COMPLETED.value
    assert (
        tool_loop["loopStopReason"] == LoopStopReason.TOOL_TURN_COMPLETED.value
    )
    assert tool_loop["commandRunId"] == "run-123"


def test_tool_decision_hard_stops_after_one_tool_turn(
    monkeypatch: pytest.MonkeyPatch,
):
    _setup_runtime(monkeypatch)

    async def _build_messages_for_llm(_task, **_kwargs):
        return (
            [{"role": "user", "content": "Switch me"}],
            "openai",
            "gpt-4o",
            {"_prompt_meta": {}},
            {"latest_turn_message_id": 11, "source_mode": "project"},
        )

    chat_calls: list[list[dict[str, object]]] = []
    invoke_calls: list[dict[str, object]] = []

    responses = iter(
        [
            {
                "kind": "tool_decision",
                "tool_decision": {
                    "command_id": "guardian.profile.switch",
                    "arguments": {
                        "path_params": {"thread_id": 7},
                        "body": {"profile_id": "local"},
                    },
                },
            },
            {
                "kind": "tool_decision",
                "tool_decision": {
                    "command_id": "guardian.profile.switch",
                    "arguments": {
                        "path_params": {"thread_id": 7},
                        "body": {"profile_id": "support"},
                    },
                },
            },
        ]
    )

    async def _fake_execute_invoke(**kwargs):
        invoke_calls.append(dict(kwargs))
        return {
            "run_id": "run-123",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/api/guardian/commands/runs/run-123/events?after_seq=0",
            "inline_result": {"ok": True},
            "policy_warnings": [],
        }

    monkeypatch.setattr(
        chat_completion_service,
        "_build_messages_for_llm_compat",
        _build_messages_for_llm,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda messages, **kwargs: chat_calls.append(list(messages))
        or next(responses),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        _fake_execute_invoke,
    )

    task = _build_task(request_id="req-stop", latest_turn_message_id=11)
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert (
        result["assistant_text"] == "Tool loop stopped after one bounded turn."
    )
    assert result["toolTurnState"] == ToolTurnState.BLOCKED.value
    assert (
        result["loopStopReason"] == LoopStopReason.TOOL_TURN_LIMIT_REACHED.value
    )
    assert len(chat_calls) == 2
    assert len(invoke_calls) == 1


def test_tool_execution_failure_returns_bounded_stop_reason(
    monkeypatch: pytest.MonkeyPatch,
):
    _setup_runtime(monkeypatch)

    async def _build_messages_for_llm(_task, **_kwargs):
        return (
            [{"role": "user", "content": "Switch me"}],
            "openai",
            "gpt-4o",
            {"_prompt_meta": {}},
            {"latest_turn_message_id": 11, "source_mode": "project"},
        )

    chat_calls: list[list[dict[str, object]]] = []
    invoke_calls: list[dict[str, object]] = []

    responses = iter(
        [
            {
                "kind": "tool_decision",
                "tool_decision": {
                    "command_id": "guardian.profile.switch",
                    "arguments": {
                        "path_params": {"thread_id": 7},
                        "body": {"profile_id": "local"},
                    },
                },
            },
            "final assistant answer after failure",
        ]
    )

    async def _fake_execute_invoke(**kwargs):
        invoke_calls.append(dict(kwargs))
        raise RuntimeError("tool transport failure")

    monkeypatch.setattr(
        chat_completion_service,
        "_build_messages_for_llm_compat",
        _build_messages_for_llm,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda messages, **kwargs: chat_calls.append(list(messages))
        or next(responses),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        _fake_execute_invoke,
    )

    task = _build_task(request_id="req-fail", latest_turn_message_id=11)
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert result["assistant_text"] == "final assistant answer after failure"
    assert result["toolTurnState"] == ToolTurnState.FAILED.value
    assert result["loopStopReason"] == LoopStopReason.TOOL_TURN_FAILED.value
    assert result["commandRunId"] is None
    assert len(chat_calls) == 2
    assert len(invoke_calls) == 1
