from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from guardian.core import chat_completion_service
from guardian.core.completion_terminal import CompletionTerminalEvidence
from guardian.protocol_tokens import (
    CompletionTerminalStatus,
    ToolLoopStopReason,
    ToolTurnState,
)
from guardian.providers.deepseek_adapter import DeepSeekResponse
from guardian.providers.whooshd_control_plane import parse_whooshd_runtime_provenance
from guardian.providers.whooshd_qualification import (
    STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
)
from guardian.providers.whooshd_tool_adapter import (
    WhooshdStructuredResponse,
    WhooshdStructuredTransportError,
)
from guardian.tasks.types import ChatCompletionTask


def _build_task(
    *,
    task_id: str = "task-tool-loop",
    thread_id: int = 7,
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
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


def _whooshd_stage_2e_response(
    content: str,
    *,
    command_id: str = "op::lookup_widget",
) -> WhooshdStructuredResponse:
    record = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    material = record.material
    runtime_provenance = parse_whooshd_runtime_provenance(
        {
            "schema_version": "whooshd.runtime.v1",
            "request_id": "req-stage2e",
            "requested_model_id": "gemma-4-12b-it-qat-4bit",
            "advertised_model_id": "gemma-4-12b-it-qat-4bit",
            "resolved_model_id": "gemma-4-12b-it-qat-4bit",
            "backend_reported_model_id": "gemma-4-12b-it-qat-4bit",
            "runtime_kind": "mlx_vlm",
            "adapter_name": "mlx-vlm",
            "resolution_source": "authoritative_registry",
            "execution_mode": "managed_sidecar",
            "streaming": False,
            "queued": False,
            "batched": False,
            "model_lifecycle": "ready",
            "whooshd_version": "0.1.0rc1",
            "qualification_attestation": {
                "attestation_schema_version": material.attestation_schema_version,
                "canonicalization_profile": material.canonicalization_profile,
                "digest_algorithm": record.digest_algorithm,
                "attestation_digest": record.expected_attestation_digest,
                "invocation_model_id": material.invocation_model_id,
                "resolved_model_id": material.resolved_model_id,
                "runtime_kind": material.runtime_kind,
                "adapter_name": material.adapter_name,
            },
        }
    )
    assert runtime_provenance is not None
    return WhooshdStructuredResponse(
        content=content,
        raw_payload={"choices": [{"message": {"content": content}}]},
        runtime_provenance=runtime_provenance,
        response_correlation=None,
        command_id=command_id,
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["widget_id"],
            "properties": {
                "widget_id": {"type": "string", "enum": ["alpha"]}
            },
        },
    )


def _whooshd_stage_2e_tool() -> dict[str, Any]:
    return {
        "command_id": "op::lookup_widget",
        "description": "Return a synthetic widget status.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["widget_id"],
            "properties": {
                "widget_id": {"type": "string", "enum": ["alpha"]}
            },
        },
    }


def test_ordinary_chat_reaches_deepseek_provider_with_no_effective_tools(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch, provider="deepseek")
    task = _build_task(task_id="task-no-effective-tools")
    task.provider = "deepseek"

    provider_tools: list[Any] = []

    def _chat_with_ai(_messages, **kwargs):
        provider_tools.append(kwargs.get("tools"))
        return DeepSeekResponse(
            content="plain answer",
            reasoning_content=None,
            tool_calls=[],
            raw_assistant_message={
                "role": "assistant",
                "content": "plain answer",
            },
            raw_payload={},
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert task.tools is None
    assert provider_tools == [None]
    assert result["assistant_text"] == "plain answer"
    assert result["payload_summary"]["toolTurnState"] == "idle"


def test_whooshd_structured_tool_turn_executes_once_and_uses_adapter_continuation(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(LOCAL_PROVIDER_VENDOR="whooshd"),
    )
    task = _build_task(task_id="task-whooshd-structured")
    task.provider = "local"
    task.model = "gemma-4-12b-it-qat-4bit"
    task.tools = [_whooshd_stage_2e_tool()]

    command_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *, payload, **_kwargs: command_calls.append(payload)
        or {"run_id": "run-whooshd", "status": "completed", "inline_result": {"status": "green"}},
    )
    provider_calls: list[tuple[list[dict[str, Any]], dict[str, Any]]] = []

    def _chat_with_ai(messages, **kwargs):
        provider_calls.append(([dict(message) for message in messages], kwargs))
        if len(provider_calls) == 1:
            return _whooshd_stage_2e_response(
                '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}'
            )
        return _whooshd_stage_2e_response(
            '{"kind":"assistant","text":"Widget alpha is green.","command_id":null,"arguments":{}}'
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert len(command_calls) == 1
    assert command_calls[0].command_id == "op::lookup_widget"
    assert len(provider_calls) == 2
    assert provider_calls[0][1]["tools"] == task.tools
    continuation = provider_calls[1][0]
    assert continuation[-2] == {
        "role": "assistant",
        "content": '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}',
    }
    assert continuation[-1]["role"] == "user"
    assert "Whoosh'd structured tool result:" in continuation[-1]["content"]
    assert "tool_call_id" not in continuation[-1]["content"]
    assert result["assistant_text"] == "Widget alpha is green."
    assert result["payload_summary"]["toolTurnState"] == "completed"
    assert result["payload_summary"]["loopStopReason"] == "tool_turn_completed"


def test_whooshd_structured_valid_transport_still_hits_stage_1_authority_gate(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(LOCAL_PROVIDER_VENDOR="whooshd"),
    )
    task = _build_task(task_id="task-whooshd-unadvertised")
    task.provider = "local"
    task.model = "gemma-4-12b-it-qat-4bit"
    task.tools = [{**_whooshd_stage_2e_tool(), "command_id": "op::advertised"}]
    command_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *args, **kwargs: command_calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: _whooshd_stage_2e_response(
            '{"kind":"tool_decision","text":null,"command_id":"op::returned","arguments":{"widget_id":"alpha"}}',
            command_id="op::returned",
        ),
    )

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert command_calls == []
    assert exc.value.metadata["loopStopReason"] == "tool_command_blocked"


def test_whooshd_structured_provenance_mismatch_blocks_before_execute_invoke(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(LOCAL_PROVIDER_VENDOR="whooshd"),
    )
    task = _build_task(task_id="task-whooshd-provenance-mismatch")
    task.provider = "local"
    task.model = "gemma-4-12b-it-qat-4bit"
    task.tools = [_whooshd_stage_2e_tool()]
    command_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *args, **kwargs: command_calls.append((args, kwargs)),
    )
    response = _whooshd_stage_2e_response(
        '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}'
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: replace(
            response,
            runtime_provenance=replace(
                response.runtime_provenance,
                resolved_model_id="another-model",
            ),
        ),
    )

    with pytest.raises(WhooshdStructuredTransportError, match="provenance"):
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert command_calls == []


def test_whooshd_structured_qualification_mismatch_blocks_before_execute_invoke(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(LOCAL_PROVIDER_VENDOR="whooshd"),
    )
    task = _build_task(task_id="task-whooshd-qualification-mismatch")
    task.provider = "local"
    task.model = "gemma-4-12b-it-qat-4bit"
    task.tools = [_whooshd_stage_2e_tool()]
    command_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *args, **kwargs: command_calls.append((args, kwargs)),
    )
    response = _whooshd_stage_2e_response(
        '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}'
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: replace(
            response,
            runtime_provenance=replace(
                response.runtime_provenance,
                qualification_attestation=replace(
                    response.runtime_provenance.qualification_attestation,
                    attestation_digest="sha256:" + "0" * 64,
                ),
            ),
        ),
    )

    with pytest.raises(WhooshdStructuredTransportError, match="mismatch"):
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert command_calls == []


def test_whooshd_structured_insufficient_evidence_blocks_before_execute_invoke(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(LOCAL_PROVIDER_VENDOR="whooshd"),
    )
    task = _build_task(task_id="task-whooshd-insufficient-evidence")
    task.provider = "local"
    task.model = "gemma-4-12b-it-qat-4bit"
    task.tools = [_whooshd_stage_2e_tool()]
    command_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *args, **kwargs: command_calls.append((args, kwargs)),
    )
    response = _whooshd_stage_2e_response(
        '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}'
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: replace(
            response,
            runtime_provenance=replace(
                response.runtime_provenance,
                qualification_attestation=None,
            ),
        ),
    )

    with pytest.raises(WhooshdStructuredTransportError, match="insufficient_evidence"):
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert command_calls == []


def test_whooshd_structured_second_tool_decision_keeps_one_turn_hard_stop(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(LOCAL_PROVIDER_VENDOR="whooshd"),
    )
    task = _build_task(task_id="task-whooshd-limit")
    task.provider = "local"
    task.model = "gemma-4-12b-it-qat-4bit"
    task.tools = [_whooshd_stage_2e_tool()]
    command_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *, payload, **_kwargs: command_calls.append(payload)
        or {"run_id": "run-whooshd-limit", "status": "completed"},
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: _whooshd_stage_2e_response(
            '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}'
        ),
    )

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert len(command_calls) == 1
    assert exc.value.metadata["loopStopReason"] == "tool_turn_limit_reached"
    assert exc.value.metadata["toolTurnState"] == "limit_reached"


def test_whooshd_ordinary_chat_with_no_tools_keeps_stream_path(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(LOCAL_PROVIDER_VENDOR="whooshd"),
    )
    task = _build_task(task_id="task-whooshd-ordinary")
    task.provider = "local"
    task.model = "gemma-4-12b-it-qat-4bit"
    stream_calls: list[dict[str, Any]] = []

    def _stream_local(_messages, _model, **kwargs):
        stream_calls.append(kwargs)

        def _stream():
            yield "ordinary local answer"
            return CompletionTerminalEvidence(
                status=CompletionTerminalStatus.SUCCESS,
                visible_output_emitted=True,
                explicit_provider_terminal_observed=True,
                finish_reason="stop",
                transport_ended_cleanly=True,
                provider="local",
                model="gemma-4-12b-it-qat-4bit",
            )

        return _stream()

    monkeypatch.setattr(chat_completion_service, "stream_local", _stream_local)
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("ordinary no-tools local chat must stream")
        ),
    )

    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert task.tools is None
    assert len(stream_calls) == 1
    assert result["assistant_text"] == "ordinary local answer"


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
    assert result["payload_summary"]["messageId"] == 2
    assert result["payload_summary"]["requestId"] == task.request_id
    assert task.request_id != task.task_id
    assert result["payload_summary"]["toolTurnId"] is None
    assert result["payload_summary"]["toolTurnState"] == "idle"
    assert result["payload_summary"]["loopStopReason"] == "plain_answer"
    assert result["payload_summary"]["commandRunId"] is None
    assert result["payload_summary"]["toolTurnState"] == "idle"
    assert result["payload_summary"]["loopStopReason"] == "plain_answer"


def test_single_tool_decision_path_invokes_command_bus_once_and_reinjects_result(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch)
    task = _build_task(task_id="task-tool-decision")
    task.tools = [{"command_id": "op::echo", "description": "echo"}]

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
    assert result["payload_summary"]["toolTurnId"] is not None
    assert result["payload_summary"]["toolTurnState"] == "completed"
    assert result["payload_summary"]["loopStopReason"] == "tool_turn_completed"
    assert result["payload_summary"]["commandRunId"] == "run-123"
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
    task.tools = [{"command_id": "op::echo", "description": "echo"}]

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


def test_deepseek_native_tool_call_replays_losslessly_and_runs_once(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch, provider="deepseek")
    task = _build_task(task_id="task-deepseek-native")
    task.provider = "deepseek"
    task.tools = [{"command_id": "op::echo", "description": "echo"}]

    command_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        command_calls.append(payload)
        return {
            "run_id": "run-deepseek",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/events/run-deepseek",
            "inline_result": {"value": "ok"},
        }

    monkeypatch.setattr(chat_completion_service, "execute_invoke", _execute_invoke)
    assistant_message = {
        "role": "assistant",
        "content": None,
        "reasoning_content": "opaque reasoning",
        "tool_calls": [{"id": "call-1", "type": "function"}],
    }
    calls: list[list[dict[str, Any]]] = []

    def _chat_with_ai(messages, **_kwargs):
        calls.append([dict(message) for message in messages])
        if len(calls) == 1:
            return DeepSeekResponse(
                content="",
                reasoning_content="opaque reasoning",
                tool_calls=[
                    {
                        "command_id": "op::echo",
                        "tool_call_id": "call-1",
                        "arguments": {"body": {"value": "alpha"}},
                    }
                ],
                raw_assistant_message=assistant_message,
                raw_payload={"choices": [{"message": assistant_message}]},
            )
        return DeepSeekResponse(
            content="final answer",
            reasoning_content=None,
            tool_calls=[],
            raw_assistant_message={"role": "assistant", "content": "final answer"},
            raw_payload={},
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)
    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    assert len(command_calls) == 1
    assert command_calls[0].command_id == "op::echo"
    assert result["assistant_text"] == "final answer"
    assert calls[1][-2] == assistant_message
    assert calls[1][-1] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": '{"run_id": "run-deepseek", "status": "completed", "invoke_version": "1.0", "manifest_version": "1.0", "events_url": "/events/run-deepseek", "inline_result": {"value": "ok"}}',
    }


def test_deepseek_rejects_unadvertised_command_before_command_bus(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch, provider="deepseek")
    task = _build_task(task_id="task-unadvertised-command")
    task.provider = "deepseek"
    task.tools = [
        {
            "command_id": "op::advertised",
            "description": "The only advertised command",
        }
    ]

    command_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        command_calls.append(payload)
        return {
            "run_id": "run-unadvertised",
            "status": "completed",
            "invoke_version": "1.0",
            "manifest_version": "1.0",
            "events_url": "/events/run-unadvertised",
        }

    monkeypatch.setattr(chat_completion_service, "execute_invoke", _execute_invoke)

    provider_calls: list[list[dict[str, Any]]] = []
    assistant_message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{"id": "call-unadvertised", "type": "function"}],
    }

    def _chat_with_ai(messages, **_kwargs):
        provider_calls.append([dict(message) for message in messages])
        if len(provider_calls) == 1:
            return DeepSeekResponse(
                content="",
                reasoning_content=None,
                tool_calls=[
                    {
                        "command_id": "op::unadvertised",
                        "tool_call_id": "call-unadvertised",
                        "arguments": {},
                    }
                ],
                raw_assistant_message=assistant_message,
                raw_payload={"choices": [{"message": assistant_message}]},
            )
        return DeepSeekResponse(
            content="should not reach a second provider call",
            reasoning_content=None,
            tool_calls=[],
            raw_assistant_message={
                "role": "assistant",
                "content": "should not reach a second provider call",
            },
            raw_payload={},
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert command_calls == []
    assert len(provider_calls) == 1
    assert exc.value.metadata["messageId"] == 2
    assert exc.value.metadata["requestId"] == task.request_id
    assert task.request_id != task.task_id
    assert exc.value.metadata["toolTurnId"] is not None
    assert (
        exc.value.metadata["loopStopReason"]
        == ToolLoopStopReason.TOOL_COMMAND_BLOCKED.value
    )
    assert exc.value.metadata["toolTurnState"] == ToolTurnState.FAILED.value
    assert exc.value.metadata["commandRunId"] is None


@pytest.mark.parametrize(
    "advertised_tools",
    [None, []],
    ids=["none", "empty"],
)
def test_plaintext_tool_decision_without_advertised_tools_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
    advertised_tools: list[dict[str, Any]] | None,
):
    _seed_service(monkeypatch)
    task = _build_task(task_id="task-no-advertised-tools")
    task.tools = advertised_tools

    command_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *args, **kwargs: command_calls.append(
            {"args": args, "kwargs": kwargs}
        ),
    )

    provider_calls: list[list[dict[str, Any]]] = []

    def _chat_with_ai(messages, **_kwargs):
        provider_calls.append([dict(message) for message in messages])
        return (
            '{"type":"tool_decision","command_id":"op::unadvertised",'
            '"arguments":{}}'
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task,
            persist_assistant_message=False,
        )

    assert task.tools == advertised_tools
    assert command_calls == []
    assert len(provider_calls) == 1
    assert exc.value.metadata["messageId"] == 2
    assert exc.value.metadata["requestId"] == task.request_id
    assert task.request_id != task.task_id
    assert exc.value.metadata["toolTurnId"] is not None
    assert (
        exc.value.metadata["loopStopReason"]
        == ToolLoopStopReason.TOOL_COMMAND_BLOCKED.value
    )
    assert exc.value.metadata["toolTurnState"] == ToolTurnState.FAILED.value
    assert exc.value.metadata["commandRunId"] is None


def test_tool_execution_failure_surfaces_bounded_stop_reason(
    monkeypatch: pytest.MonkeyPatch,
):
    _seed_service(monkeypatch)
    task = _build_task(task_id="task-tool-failure")
    task.tools = [{"command_id": "op::echo", "description": "echo"}]

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
