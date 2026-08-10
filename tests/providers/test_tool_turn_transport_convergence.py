"""Stage 2H — cross-provider tool-turn semantic convergence proof.

This module proves, without modifying production code, that:

- DeepSeek native tool-call transport, and
- the exact Stage 2D-qualified Whoosh'd strict-structured transport

are two provider-specific representations of the same bounded Codexify
semantic tool action.  Both transports:

- normalize to a common canonical command identity and arguments,
- traverse the same Stage 1 advertised-subset authority gate,
- traverse the same ``execute_invoke`` seam,
- are limited to exactly one Command Bus invocation,
- produce the same canonical bounded tool-turn observability, and
- cannot bypass Stage 1 even if provider-private state is altered.

Provider-specific state (DeepSeek ``tool_call_id``/``reasoning_content``,
Whoosh'd ``runtime_provenance``/qualification digest) is acknowledged as
correlation or runtime evidence but never as command authority.
"""

from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from guardian.core import ai_router, chat_completion_service
from guardian.core.completion_terminal import CompletionTerminalEvidence
from guardian.protocol_tokens import CompletionTerminalStatus
from guardian.providers.deepseek_adapter import (
    DeepSeekResponse,
    build_tool_definitions,
    normalize_tool_calls,
)
from guardian.providers.deepseek_adapter import (
    parse_response as parse_deepseek_response,
)
from guardian.providers.whooshd_control_plane import parse_whooshd_runtime_provenance
from guardian.providers.whooshd_qualification import (
    STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
)
from guardian.providers.whooshd_tool_adapter import WhooshdStructuredResponse
from guardian.tasks.types import ChatCompletionTask

# ── Canonical fixture shared by both transport paths ────────────────────────


CANONICAL_COMMAND_ID = "op::lookup_widget"
CANONICAL_ARGUMENTS = {"widget_id": "alpha"}
CANONICAL_FINAL_ANSWER = "Widget alpha is green."
MOCKED_COMMAND_RESULT = {
    "run_id": "run-convergence",
    "status": "completed",
    "invoke_version": "1.0",
    "manifest_version": "1.0",
    "events_url": "/events/run-convergence",
    "inline_result": {"status": "green"},
}


def _canonical_tool_spec() -> dict[str, Any]:
    """Single bounded read-only capability shared by both provider paths."""

    return {
        "command_id": CANONICAL_COMMAND_ID,
        "description": "Return a synthetic widget status.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["widget_id"],
            "properties": {
                "widget_id": {"type": "string", "enum": ["alpha"]},
            },
        },
    }


def _canonical_semantic_tuple(normalized: ai_router.NormalizedCompletionOutput) -> tuple:
    """The common semantic core used to assert provider convergence.

    Provider-specific fields (``provider``, ``tool_call_id``,
    ``raw_assistant_message``, ``runtime_provenance``, ``raw_payload``)
    are deliberately excluded.
    """

    return (
        normalized.kind,
        normalized.command_id,
        normalized.arguments,
    )


def _build_task(
    *,
    task_id: str,
    provider: str,
    model: str,
    tools: list[Any] | None,
) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
        task_id=task_id,
        thread_id=7,
        provider=provider,
        model=model,
        origin="api:chat.complete|turn_id=22222222-2222-4222-8222-222222222222",
    )
    task.latest_turn_message_id = 2
    task.turn_id = "22222222-2222-4222-8222-222222222222"
    task.tools = tools
    return task


def _seed_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: str,
    model: str,
) -> None:
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(
            LOCAL_PROVIDER_VENDOR="whooshd" if provider == "local" else "deepseek"
        ),
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


# ── DeepSeek native wire-shape helpers ──────────────────────────────────────


def _deepseek_native_payload(
    *,
    alias_to_command: dict[str, str],
    alias: str,
    arguments: dict[str, Any],
    tool_call_id: str,
    reasoning_content: str | None = None,
) -> dict[str, Any]:
    """Build the bounded upstream DeepSeek chat-completion payload."""

    return {
        "id": "chatcmpl-convergence",
        "object": "chat.completion",
        "created": 0,
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "reasoning_content": reasoning_content,
                    "tool_calls": [
                        {
                            "id": tool_call_id,
                            "type": "function",
                            "function": {
                                "name": alias,
                                "arguments": json.dumps(arguments, sort_keys=True),
                            },
                        }
                    ],
                },
            }
        ],
    }


def _deepseek_aliases(tool_specs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    return build_tool_definitions(tool_specs)


def _deepseek_response(
    *,
    alias_to_command: dict[str, str],
    alias: str,
    arguments: dict[str, Any],
    tool_call_id: str = "call-convergence",
    reasoning_content: str | None = "private reasoning state",
) -> tuple[DeepSeekResponse, dict[str, Any]]:
    payload = _deepseek_native_payload(
        alias_to_command=alias_to_command,
        alias=alias,
        arguments=arguments,
        tool_call_id=tool_call_id,
        reasoning_content=reasoning_content,
    )
    response = parse_deepseek_response(payload)
    # ``parse_response`` preserves the provider-native function name.  The
    # adapter's next production step resolves that opaque alias back to the
    # Codexify-owned canonical command before the common carrier sees it.
    response = replace(
        response,
        tool_calls=normalize_tool_calls(response, alias_to_command),
    )
    return response, payload


# ── Whoosh'd strict-structured helpers ───────────────────────────────────────


def _whooshd_matching_provenance() -> Any:
    record = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD
    material = record.material
    return parse_whooshd_runtime_provenance(
        {
            "schema_version": "whooshd.runtime.v1",
            "request_id": "req-stage2h",
            "requested_model_id": material.invocation_model_id,
            "advertised_model_id": material.invocation_model_id,
            "resolved_model_id": material.invocation_model_id,
            "backend_reported_model_id": material.resolved_model_id,
            "runtime_kind": material.runtime_kind,
            "adapter_name": material.adapter_name,
            "resolution_source": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.route_resolution_source,
            "execution_mode": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.route_execution_mode,
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


def _whooshd_stage_2e_response(
    *,
    kind: str,
    text: str | None,
    command_id: str | None,
    arguments: dict[str, Any],
    tool_call_id_for_argument_schema: str = CANONICAL_COMMAND_ID,
) -> WhooshdStructuredResponse:
    runtime_provenance = _whooshd_matching_provenance()
    assert runtime_provenance is not None
    payload = json.dumps(
        {"kind": kind, "text": text, "command_id": command_id, "arguments": arguments},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return WhooshdStructuredResponse(
        content=payload,
        raw_payload={"choices": [{"message": {"content": payload}}]},
        runtime_provenance=runtime_provenance,
        response_correlation=None,
        command_id=tool_call_id_for_argument_schema,
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["widget_id"],
            "properties": {
                "widget_id": {"type": "string", "enum": ["alpha"]}
            },
        },
    )


# ── Provider-specific chat_with_ai stubs ────────────────────────────────────


def _drive_deepseek_tool_turn(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tool_specs: list[dict[str, Any]],
    alias: str,
    arguments: dict[str, Any],
    final_text: str = CANONICAL_FINAL_ANSWER,
    tool_call_id: str = "call-convergence",
    reasoning_content: str | None = "private reasoning state",
) -> dict[str, int]:
    """Drive the DeepSeek bounded tool turn end-to-end with mocked execute_invoke.

    Returns a small metrics dict with ``invoke_count`` and ``call_count``.
    """

    _definitions, aliases = _deepseek_aliases(tool_specs)
    assert alias in aliases, f"alias {alias!r} not present in built definitions"

    invoke_calls: list[Any] = []
    call_count = {"invoke": 0}

    def _execute_invoke(*, payload, **_kwargs):
        call_count["invoke"] += 1
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    response, _payload = _deepseek_response(
        alias_to_command=aliases,
        alias=alias,
        arguments=arguments,
        tool_call_id=tool_call_id,
        reasoning_content=reasoning_content,
    )
    final_response = DeepSeekResponse(
        content=final_text,
        reasoning_content=None,
        tool_calls=[],
        raw_assistant_message={"role": "assistant", "content": final_text},
        raw_payload={},
    )

    state = {"calls": 0}
    provider_calls: list[list[dict[str, Any]]] = []

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        provider_calls.append([dict(message) for message in messages])
        return response if state["calls"] == 1 else final_response

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    metrics = _run_loop(
        monkeypatch,
        provider="deepseek",
        model="deepseek-v4-flash",
        tool_specs=tool_specs,
        call_count=call_count,
    )
    metrics["invoke_payloads"] = invoke_calls
    metrics["provider_calls"] = provider_calls
    return metrics


def _drive_whooshd_tool_turn(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tool_specs: list[dict[str, Any]],
    command_id: str = CANONICAL_COMMAND_ID,
    arguments: dict[str, Any] | None = None,
    final_text: str = CANONICAL_FINAL_ANSWER,
) -> dict[str, int]:
    """Drive the Whoosh'd bounded tool turn end-to-end with mocked execute_invoke."""

    arguments = arguments or dict(CANONICAL_ARGUMENTS)
    invoke_calls: list[Any] = []
    call_count = {"invoke": 0}

    def _execute_invoke(*, payload, **_kwargs):
        call_count["invoke"] += 1
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    tool_decision_response = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id=command_id,
        arguments=arguments,
    )
    assistant_response = _whooshd_stage_2e_response(
        kind="assistant",
        text=final_text,
        command_id=None,
        arguments={},
        tool_call_id_for_argument_schema=command_id,
    )
    state = {"calls": 0}
    provider_calls: list[list[dict[str, Any]]] = []

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        provider_calls.append([dict(message) for message in messages])
        return tool_decision_response if state["calls"] == 1 else assistant_response

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    metrics = _run_loop(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        tool_specs=tool_specs,
        call_count=call_count,
    )
    metrics["invoke_payloads"] = invoke_calls
    metrics["provider_calls"] = provider_calls
    return metrics


def _run_loop(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: str,
    model: str,
    tool_specs: list[dict[str, Any]],
    call_count: dict[str, int],
) -> dict[str, Any]:
    """Drive ``run_chat_completion_task`` once and return a small metrics dict."""

    task = _build_task(
        task_id=f"task-convergence-{provider}",
        provider=provider,
        model=model,
        tools=list(tool_specs),
    )
    _seed_service(monkeypatch, provider=provider, model=model)
    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )
    return {
        "result": result,
        "task": task,
        "invoke_count": call_count["invoke"],
    }


# ── A. Adapter output common core ──────────────────────────────────────────


def test_deepseek_native_normalizes_to_canonical_semantic_tuple(monkeypatch: pytest.MonkeyPatch):
    """A DeepSeek native tool call, after alias translation, carries the same
    canonical (kind, command_id, arguments) tuple as a Whoosh'd
    strict-structured ModelTurn for the same semantic action.
    """

    tool_specs = [_canonical_tool_spec()]
    definitions, aliases = _deepseek_aliases(tool_specs)
    alias = next(iter(aliases))

    deepseek_response, _payload = _deepseek_response(
        alias_to_command=aliases,
        alias=alias,
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    deepseek_normalized = ai_router.normalize_completion_output(deepseek_response)

    deepseek_tuple = _canonical_semantic_tuple(deepseek_normalized)
    assert deepseek_tuple == (
        "tool_decision",
        CANONICAL_COMMAND_ID,
        dict(CANONICAL_ARGUMENTS),
    )

    # The DeepSeek carrier may carry provider-specific correlation fields.
    assert deepseek_normalized.provider == "deepseek"
    assert deepseek_normalized.tool_call_id == "call-convergence"
    assert deepseek_normalized.tool_call_count == 1
    assert deepseek_normalized.raw_assistant_message["reasoning_content"] == (
        "private reasoning state"
    )

    # The native alias the provider sees is opaque (not the canonical command).
    assert alias.startswith("codexify_tool_")
    assert CANONICAL_COMMAND_ID not in json.dumps(definitions)

    whooshd_response = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id=CANONICAL_COMMAND_ID,
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    whooshd_normalized = ai_router.normalize_completion_output(whooshd_response)

    whooshd_tuple = _canonical_semantic_tuple(whooshd_normalized)
    assert whooshd_tuple == deepseek_tuple


# ── B. Provider-specific state remains distinct ─────────────────────────────


def test_provider_specific_state_remains_distinct_after_normalization(
    monkeypatch: pytest.MonkeyPatch,
):
    """Common command semantics remain identical even though provider-private
    state differs.
    """

    tool_specs = [_canonical_tool_spec()]
    _definitions, aliases = _deepseek_aliases(tool_specs)
    alias = next(iter(aliases))

    deepseek_response, _payload = _deepseek_response(
        alias_to_command=aliases,
        alias=alias,
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    deepseek_normalized = ai_router.normalize_completion_output(deepseek_response)

    whooshd_response = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id=CANONICAL_COMMAND_ID,
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    whooshd_normalized = ai_router.normalize_completion_output(whooshd_response)

    # Common semantics agree.
    assert _canonical_semantic_tuple(deepseek_normalized) == (
        _canonical_semantic_tuple(whooshd_normalized)
    )

    # Provider-specific fields are populated on their side, absent on the other.
    assert deepseek_normalized.tool_call_id is not None
    assert deepseek_normalized.raw_assistant_message is not None
    assert whooshd_normalized.tool_call_id is None

    assert whooshd_normalized.runtime_provenance is not None
    assert whooshd_normalized.provider == "whooshd"
    assert deepseek_normalized.runtime_provenance is None


# ── C. Authorized execution ────────────────────────────────────────────────


def test_deepseek_authorizes_once_with_canonical_command_identity(
    monkeypatch: pytest.MonkeyPatch,
):
    metrics = _drive_deepseek_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
        alias="codexify_tool_0",
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    _assert_successful_completion(metrics)


def test_whooshd_authorizes_once_with_canonical_command_identity(
    monkeypatch: pytest.MonkeyPatch,
):
    metrics = _drive_whooshd_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
    )
    _assert_successful_completion(metrics)


def _assert_successful_completion(metrics: dict[str, Any]) -> None:
    assert metrics["invoke_count"] == 1
    result = metrics["result"]
    assert result["assistant_text"] == CANONICAL_FINAL_ANSWER
    payload_summary = result["payload_summary"]
    assert payload_summary["toolTurnState"] == "completed"
    assert payload_summary["loopStopReason"] == "tool_turn_completed"
    assert payload_summary["commandRunId"] == "run-convergence"
    assert payload_summary["toolTurnId"]
    assert payload_summary["requestId"]


def test_canonical_command_id_and_arguments_match_at_execute_invoke(
    monkeypatch: pytest.MonkeyPatch,
):
    """Both providers must hand the canonical command identity and arguments to
    the same ``execute_invoke`` seam."""

    deepseek_metrics = _drive_deepseek_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
        alias="codexify_tool_0",
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    whooshd_metrics = _drive_whooshd_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
    )

    assert deepseek_metrics["invoke_count"] == 1
    assert whooshd_metrics["invoke_count"] == 1
    deepseek_payload = deepseek_metrics["invoke_payloads"][0]
    whooshd_payload = whooshd_metrics["invoke_payloads"][0]
    for invoke_payload in (deepseek_payload, whooshd_payload):
        assert invoke_payload.command_id == CANONICAL_COMMAND_ID
        assert invoke_payload.arguments.body == dict(CANONICAL_ARGUMENTS)


# ── D. Final answer convergence ────────────────────────────────────────────


def test_final_assistant_answer_converges_for_both_providers(monkeypatch: pytest.MonkeyPatch):
    """Both bounded loops return the same canonical final answer for the same
    semantic mock result."""

    deepseek_metrics = _drive_deepseek_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
        alias="codexify_tool_0",
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    whooshd_metrics = _drive_whooshd_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
    )

    assert deepseek_metrics["result"]["assistant_text"] == CANONICAL_FINAL_ANSWER
    assert whooshd_metrics["result"]["assistant_text"] == CANONICAL_FINAL_ANSWER


def test_provider_continuations_translate_the_same_command_result_differently(
    monkeypatch: pytest.MonkeyPatch,
):
    """Provider continuations are adapter-owned representations of one result."""

    deepseek_metrics = _drive_deepseek_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
        alias="codexify_tool_0",
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    whooshd_metrics = _drive_whooshd_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
    )

    deepseek_continuation = deepseek_metrics["provider_calls"][1]
    assert deepseek_continuation[-2]["role"] == "assistant"
    assert deepseek_continuation[-2]["reasoning_content"] == "private reasoning state"
    assert deepseek_continuation[-1]["role"] == "tool"
    assert deepseek_continuation[-1]["tool_call_id"] == "call-convergence"
    assert json.loads(deepseek_continuation[-1]["content"]) == MOCKED_COMMAND_RESULT

    whooshd_continuation = whooshd_metrics["provider_calls"][1]
    assert json.loads(whooshd_continuation[-2]["content"]) == {
        "kind": "tool_decision",
        "text": None,
        "command_id": CANONICAL_COMMAND_ID,
        "arguments": CANONICAL_ARGUMENTS,
    }
    assert whooshd_continuation[-1]["role"] == "user"
    assert "tool_call_id" not in whooshd_continuation[-1]["content"]
    whooshd_result = json.loads(
        whooshd_continuation[-1]["content"].split("\n", 1)[1]
    )
    assert whooshd_result["command_id"] == CANONICAL_COMMAND_ID
    assert whooshd_result["arguments"] == CANONICAL_ARGUMENTS
    assert whooshd_result["result"] == MOCKED_COMMAND_RESULT


# ── E. Successful observability ────────────────────────────────────────────


def test_successful_canonical_observability_converges(monkeypatch: pytest.MonkeyPatch):
    deepseek_metrics = _drive_deepseek_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
        alias="codexify_tool_0",
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    whooshd_metrics = _drive_whooshd_tool_turn(
        monkeypatch,
        tool_specs=[_canonical_tool_spec()],
    )

    deepseek_loop = deepseek_metrics["result"]["payload_summary"]
    whooshd_loop = whooshd_metrics["result"]["payload_summary"]

    for field in ("toolTurnState", "loopStopReason", "commandRunId", "messageId"):
        assert deepseek_loop[field] == whooshd_loop[field], field

    assert deepseek_loop["toolTurnState"] == "completed"
    assert deepseek_loop["loopStopReason"] == "tool_turn_completed"
    assert deepseek_loop["commandRunId"] == "run-convergence"
    assert deepseek_loop["messageId"] == whooshd_loop["messageId"]


# ── F. Unadvertised command convergence ─────────────────────────────────────


def test_deepseek_unadvertised_command_blocked_by_stage_1(monkeypatch: pytest.MonkeyPatch):
    """DeepSeek may produce a wire-valid proposal with an unadvertised canonical
    command id. Stage 1 must block it before ``execute_invoke``."""

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    tool_specs = [_canonical_tool_spec()]
    _definitions, aliases = _deepseek_aliases(tool_specs)
    # Inject an unknown alias mapping the provider does not have authority for.
    aliases["synthetic_evil_alias"] = "op::unadvertised"

    deepseek_response, _payload = _deepseek_response(
        alias_to_command=aliases,
        alias="synthetic_evil_alias",
        arguments=dict(CANONICAL_ARGUMENTS),
        tool_call_id="call-evil",
    )
    final_response = DeepSeekResponse(
        content=CANONICAL_FINAL_ANSWER,
        reasoning_content=None,
        tool_calls=[],
        raw_assistant_message={"role": "assistant", "content": CANONICAL_FINAL_ANSWER},
        raw_payload={},
    )
    state = {"calls": 0}

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        return deepseek_response if state["calls"] == 1 else final_response

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    task = _build_task(
        task_id="task-deepseek-unadvertised",
        provider="deepseek",
        model="deepseek-v4-flash",
        tools=list(tool_specs),
    )
    _seed_service(monkeypatch, provider="deepseek", model="deepseek-v4-flash")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )

    assert invoke_calls == []
    assert exc.value.metadata["loopStopReason"] == "tool_command_blocked"
    assert exc.value.metadata["toolTurnState"] == "failed"
    assert exc.value.metadata["commandRunId"] is None
    assert exc.value.metadata["command_id"] == "op::unadvertised"


def test_whooshd_unadvertised_command_blocked_by_stage_1(monkeypatch: pytest.MonkeyPatch):
    """Equivalent Whoosh'd structured proposal whose canonical command id is not
    in ``task.tools`` must be blocked by Stage 1 before ``execute_invoke``.

    Because the strict structured response shape is bound to the one prepared
    tool, the simplest faithful reproduction is a syntactically valid
    ``tool_decision`` whose canonical ``command_id`` is not in the authorized
    set.
    """

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    tool_specs = [_canonical_tool_spec()]
    response = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id="op::unadvertised",
        arguments=dict(CANONICAL_ARGUMENTS),
        tool_call_id_for_argument_schema="op::unadvertised",
    )

    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_a, **_kw: response,
    )

    task = _build_task(
        task_id="task-whooshd-unadvertised",
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        tools=list(tool_specs),
    )
    _seed_service(monkeypatch, provider="local", model="gemma-4-12b-it-qat-4bit")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )

    assert invoke_calls == []
    assert exc.value.metadata["loopStopReason"] == "tool_command_blocked"
    assert exc.value.metadata["toolTurnState"] == "failed"
    assert exc.value.metadata["commandRunId"] is None


# ── G. Malformed transport fail-closed ──────────────────────────────────────


def test_deepseek_unknown_alias_does_not_execute(monkeypatch: pytest.MonkeyPatch):
    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    tool_specs = [_canonical_tool_spec()]
    _definitions, aliases = _deepseek_aliases(tool_specs)
    # Use an alias that does not exist in the built definitions.
    response, _payload = _deepseek_response(
        alias_to_command=aliases,
        alias="synthetic_unknown_alias",
        arguments=dict(CANONICAL_ARGUMENTS),
        tool_call_id="call-unknown",
    )
    final_response = DeepSeekResponse(
        content=CANONICAL_FINAL_ANSWER,
        reasoning_content=None,
        tool_calls=[],
        raw_assistant_message={"role": "assistant", "content": CANONICAL_FINAL_ANSWER},
        raw_payload={},
    )
    state = {"calls": 0}

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        return response if state["calls"] == 1 else final_response

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    task = _build_task(
        task_id="task-deepseek-unknown-alias",
        provider="deepseek",
        model="deepseek-v4-flash",
        tools=list(tool_specs),
    )
    _seed_service(monkeypatch, provider="deepseek", model="deepseek-v4-flash")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError):
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert invoke_calls == []


def test_deepseek_multiple_native_tool_calls_do_not_execute_twice(
    monkeypatch: pytest.MonkeyPatch,
):
    """A DeepSeek response with >1 native tool call must hit
    ``tool_turn_limit_reached`` without ``execute_invoke`` running."""

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    payload = {
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-a",
                            "type": "function",
                            "function": {
                                "name": "codexify_tool_0",
                                "arguments": json.dumps(CANONICAL_ARGUMENTS),
                            },
                        },
                        {
                            "id": "call-b",
                            "type": "function",
                            "function": {
                                "name": "codexify_tool_0",
                                "arguments": json.dumps(CANONICAL_ARGUMENTS),
                            },
                        },
                    ],
                },
            }
        ]
    }
    response = parse_deepseek_response(payload)
    final_response = DeepSeekResponse(
        content=CANONICAL_FINAL_ANSWER,
        reasoning_content=None,
        tool_calls=[],
        raw_assistant_message={"role": "assistant", "content": CANONICAL_FINAL_ANSWER},
        raw_payload={},
    )
    state = {"calls": 0}

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        return response if state["calls"] == 1 else final_response

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    task = _build_task(
        task_id="task-deepseek-multitool",
        provider="deepseek",
        model="deepseek-v4-flash",
        tools=[_canonical_tool_spec()],
    )
    _seed_service(monkeypatch, provider="deepseek", model="deepseek-v4-flash")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert invoke_calls == []
    assert exc.value.metadata["loopStopReason"] == "tool_turn_limit_reached"
    assert exc.value.metadata["toolTurnState"] == "limit_reached"


def test_whooshd_qualification_mismatch_blocks_before_execute_invoke(
    monkeypatch: pytest.MonkeyPatch,
):
    """Whoosh'd transport-level qualification mismatch must fail closed before
    ``execute_invoke``."""

    from guardian.providers.whooshd_tool_adapter import (
        WhooshdStructuredTransportError,
    )

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    response = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id=CANONICAL_COMMAND_ID,
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    tampered_provenance = replace(
        response.runtime_provenance,
        qualification_attestation=replace(
            response.runtime_provenance.qualification_attestation,
            attestation_digest="sha256:" + "0" * 64,
        ),
    )
    response = replace(response, runtime_provenance=tampered_provenance)

    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_a, **_kw: response,
    )

    task = _build_task(
        task_id="task-whooshd-qual-mismatch",
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        tools=[_canonical_tool_spec()],
    )
    _seed_service(monkeypatch, provider="local", model="gemma-4-12b-it-qat-4bit")

    with pytest.raises(WhooshdStructuredTransportError):
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert invoke_calls == []


def test_whooshd_invalid_model_turn_shape_blocks_before_execute_invoke(
    monkeypatch: pytest.MonkeyPatch,
):
    """A malformed strict ModelTurn shape must fail closed before execution."""

    from guardian.providers.whooshd_tool_adapter import (
        WhooshdStructuredTransportError,
    )

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    response = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id=CANONICAL_COMMAND_ID,
        arguments={"widget_id": "beta"},  # not in enum
    )

    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_a, **_kw: response,
    )

    task = _build_task(
        task_id="task-whooshd-bad-arg",
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        tools=[_canonical_tool_spec()],
    )
    _seed_service(monkeypatch, provider="local", model="gemma-4-12b-it-qat-4bit")

    with pytest.raises(WhooshdStructuredTransportError):
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert invoke_calls == []


# ── H. One-tool hard limit ─────────────────────────────────────────────────


def test_deepseek_second_tool_decision_keeps_one_turn_hard_stop(
    monkeypatch: pytest.MonkeyPatch,
):
    """After one execution, a second DeepSeek native tool proposal must not run.

    The deepseek path uses the bounded chat runtime's second-attempt decision
    check; we force the second turn to also produce a tool call and confirm
    ``execute_invoke`` ran exactly once total and the bounded runtime refused
    the second proposal.
    """

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    tool_specs = [_canonical_tool_spec()]
    _, aliases = _deepseek_aliases(tool_specs)
    first_response, _ = _deepseek_response(
        alias_to_command=aliases,
        alias="codexify_tool_0",
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    # Second attempt also returns a tool call (forbidden).
    second_tool_response, _ = _deepseek_response(
        alias_to_command=aliases,
        alias="codexify_tool_0",
        arguments=dict(CANONICAL_ARGUMENTS),
        tool_call_id="call-second",
    )
    state = {"calls": 0}

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            return first_response
        return second_tool_response

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    task = _build_task(
        task_id="task-deepseek-second",
        provider="deepseek",
        model="deepseek-v4-flash",
        tools=list(tool_specs),
    )
    _seed_service(monkeypatch, provider="deepseek", model="deepseek-v4-flash")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert len(invoke_calls) == 1
    assert exc.value.metadata["loopStopReason"] == "tool_turn_limit_reached"
    assert exc.value.metadata["toolTurnState"] == "limit_reached"


def test_whooshd_second_tool_decision_keeps_one_turn_hard_stop(
    monkeypatch: pytest.MonkeyPatch,
):
    """After one execution, a second Whoosh'd tool_decision must not run."""

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    tool_specs = [_canonical_tool_spec()]
    first = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id=CANONICAL_COMMAND_ID,
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    second = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id=CANONICAL_COMMAND_ID,
        arguments=dict(CANONICAL_ARGUMENTS),
    )
    state = {"calls": 0}

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        return first if state["calls"] == 1 else second

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    task = _build_task(
        task_id="task-whooshd-second",
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        tools=list(tool_specs),
    )
    _seed_service(monkeypatch, provider="local", model="gemma-4-12b-it-qat-4bit")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert len(invoke_calls) == 1
    assert exc.value.metadata["loopStopReason"] == "tool_turn_limit_reached"
    assert exc.value.metadata["toolTurnState"] == "limit_reached"


# ── I. Plain-answer ────────────────────────────────────────────────────────


def test_deepseek_plain_assistant_completion_does_not_execute(
    monkeypatch: pytest.MonkeyPatch,
):
    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    response = DeepSeekResponse(
        content="plain answer",
        reasoning_content=None,
        tool_calls=[],
        raw_assistant_message={"role": "assistant", "content": "plain answer"},
        raw_payload={},
    )
    monkeypatch.setattr(chat_completion_service, "chat_with_ai", lambda *_a, **_kw: response)

    task = _build_task(
        task_id="task-deepseek-plain",
        provider="deepseek",
        model="deepseek-v4-flash",
        tools=None,
    )
    _seed_service(monkeypatch, provider="deepseek", model="deepseek-v4-flash")

    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )
    assert invoke_calls == []
    assert task.tools is None
    assert result["assistant_text"] == "plain answer"
    assert result["payload_summary"]["toolTurnState"] == "idle"
    assert result["payload_summary"]["loopStopReason"] == "plain_answer"


def test_whooshd_plain_assistant_completion_keeps_stream_path(
    monkeypatch: pytest.MonkeyPatch,
):
    """Ordinary Whoosh'd no-tools chat must not enter the bounded tool-turn
    path.  ``chat_with_ai`` must not be called; ``stream_local`` must be used.
    """

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

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

    task = _build_task(
        task_id="task-whooshd-plain",
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        tools=None,
    )
    _seed_service(monkeypatch, provider="local", model="gemma-4-12b-it-qat-4bit")

    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )

    assert invoke_calls == []
    assert task.tools is None
    assert result["assistant_text"] == "ordinary local answer"
    assert result["payload_summary"]["toolTurnState"] == "idle"
    assert result["payload_summary"]["loopStopReason"] == "plain_answer"


# ── J. Provider-private state isolation ────────────────────────────────────


def test_deepseek_tool_call_id_does_not_grant_command_authority(
    monkeypatch: pytest.MonkeyPatch,
):
    """Changing DeepSeek's tool_call_id cannot turn an unadvertised command into
    an authorized one.  The canonical command identity is the authority."""

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    tool_specs = [_canonical_tool_spec()]
    _, aliases = _deepseek_aliases(tool_specs)
    aliases["synthetic_authority_attempt"] = "op::unadvertised"

    response, _payload = _deepseek_response(
        alias_to_command=aliases,
        alias="synthetic_authority_attempt",
        arguments=dict(CANONICAL_ARGUMENTS),
        tool_call_id="call-claimed-authority",
    )
    final_response = DeepSeekResponse(
        content=CANONICAL_FINAL_ANSWER,
        reasoning_content=None,
        tool_calls=[],
        raw_assistant_message={"role": "assistant", "content": CANONICAL_FINAL_ANSWER},
        raw_payload={},
    )
    state = {"calls": 0}

    def _chat_with_ai(messages, **_kwargs):
        state["calls"] += 1
        return response if state["calls"] == 1 else final_response

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat_with_ai)

    task = _build_task(
        task_id="task-deepseek-private-state",
        provider="deepseek",
        model="deepseek-v4-flash",
        tools=list(tool_specs),
    )
    _seed_service(monkeypatch, provider="deepseek", model="deepseek-v4-flash")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert invoke_calls == []
    assert exc.value.metadata["loopStopReason"] == "tool_command_blocked"


def test_whooshd_qualification_match_does_not_grant_command_authority(
    monkeypatch: pytest.MonkeyPatch,
):
    """A Whoosh'd transport with matching qualification and matching Stage 2F.1b
    reference is *eligible* for the structured path, but Stage 1 still
    authorizes the canonical command identity itself."""

    invoke_calls: list[Any] = []

    def _execute_invoke(*, payload, **_kwargs):
        invoke_calls.append(payload)
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    # Stage 1 has ``op::other_advertised`` — proposal is for an unadvertised
    # canonical command id.
    other_spec = {
        "command_id": "op::other_advertised",
        "description": "Other advertised canonical command.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": [],
            "properties": {},
        },
    }
    response = _whooshd_stage_2e_response(
        kind="tool_decision",
        text=None,
        command_id="op::unadvertised",
        arguments=dict(CANONICAL_ARGUMENTS),
        tool_call_id_for_argument_schema="op::unadvertised",
    )

    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_a, **_kw: response,
    )

    task = _build_task(
        task_id="task-whooshd-qual-not-authority",
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        tools=[other_spec],
    )
    _seed_service(monkeypatch, provider="local", model="gemma-4-12b-it-qat-4bit")

    with pytest.raises(chat_completion_service.ToolLoopExecutionError) as exc:
        chat_completion_service.run_chat_completion_task(
            task, persist_assistant_message=False
        )
    assert invoke_calls == []
    assert exc.value.metadata["loopStopReason"] == "tool_command_blocked"


# ── K. Production exposure regression ─────────────────────────────────────


def test_ordinary_production_task_tools_remains_none(
    monkeypatch: pytest.MonkeyPatch,
):
    """Ordinary production chat completion must not derive ``task.tools``
    from the new projection.  ``task.tools`` is supplied only by test/
    task fixtures explicitly."""

    def _execute_invoke(*, payload, **_kwargs):
        return dict(MOCKED_COMMAND_RESULT)

    monkeypatch.setattr(
        chat_completion_service, "execute_invoke", _execute_invoke
    )

    response = DeepSeekResponse(
        content="plain",
        reasoning_content=None,
        tool_calls=[],
        raw_assistant_message={"role": "assistant", "content": "plain"},
        raw_payload={},
    )
    monkeypatch.setattr(chat_completion_service, "chat_with_ai", lambda *_a, **_kw: response)

    task = _build_task(
        task_id="task-production-no-tools",
        provider="deepseek",
        model="deepseek-v4-flash",
        tools=None,
    )
    _seed_service(monkeypatch, provider="deepseek", model="deepseek-v4-flash")

    chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )
    assert task.tools is None
