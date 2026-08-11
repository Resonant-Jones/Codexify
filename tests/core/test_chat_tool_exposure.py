from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI

from guardian.command_bus.manifest import build_manifest
from guardian.core import chat_completion_service
from guardian.core.completion_terminal import CompletionTerminalEvidence
from guardian.protocol_tokens import CompletionTerminalStatus
from guardian.providers.deepseek_adapter import DeepSeekResponse
from guardian.providers.whooshd_control_plane import (
    fetch_whooshd_runtime_inventory_entry,
    parse_whooshd_runtime_inventory_entry,
    parse_whooshd_runtime_provenance,
)
from guardian.providers.whooshd_qualification import (
    STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD,
)
from guardian.providers.whooshd_tool_adapter import WhooshdStructuredResponse
from guardian.providers.whooshd_tool_capability import (
    project_whooshd_tool_capability,
)
from guardian.routes import health
from guardian.tasks.types import ChatCompletionTask
from guardian.tools.chat_exposure import (
    HEALTH_COMMAND_ID,
    resolve_ordinary_chat_tools,
)


def _command_bus_app() -> FastAPI:
    """Use the production health router that the runtime manifest exposes."""

    app = FastAPI()
    app.include_router(health.router)
    return app


def _manifest_commands() -> list[Any]:
    return build_manifest(_command_bus_app()).commands


def _health_command() -> Any:
    return next(
        command
        for command in _manifest_commands()
        if command.command_id == HEALTH_COMMAND_ID
    )


def _full_inventory_attestation() -> dict[str, object]:
    material = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.material
    return {
        "attestation_schema_version": material.attestation_schema_version,
        "canonicalization_profile": material.canonicalization_profile,
        "invocation_model_id": material.invocation_model_id,
        "resolved_model_id": material.resolved_model_id,
        "artifact_identity": {
            "kind": material.artifact_identity_kind,
            "value": material.artifact_identity_value,
        },
        "quantization": material.quantization,
        "runtime_kind": material.runtime_kind,
        "adapter": {
            "name": material.adapter_name,
            "semantic_build": material.adapter_semantic_build,
        },
        "whooshd_build_identity": material.whooshd_build_identity,
        "serving_runtime": {
            "package": material.serving_runtime_package,
            "version": material.serving_runtime_version,
        },
        "structured_decoder": {
            "package": material.structured_decoder_package,
            "version": material.structured_decoder_version,
        },
        "tokenizer": {
            "implementation": material.tokenizer_implementation,
            "identity_fingerprint": material.tokenizer_identity_fingerprint,
        },
        "chat_template_fingerprint": material.chat_template_fingerprint,
        "tool_template_parser": {
            "relationship": material.tool_template_parser_relationship,
            "identity_fingerprint": material.tool_template_parser_identity_fingerprint,
        },
        "structured_transport": {
            "mode": material.structured_transport_mode,
            "protocol_version": material.structured_transport_protocol_version,
        },
        "qualification_protocol_version": material.qualification_protocol_version,
        "digest_algorithm": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.digest_algorithm,
        "attestation_digest": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.expected_attestation_digest,
    }


def _inventory_entry(
    *,
    loaded: bool = True,
    lifecycle: str = "ready",
) -> dict[str, object]:
    return {
        "id": "gemma-4-12b-it-qat-4bit",
        "loaded": loaded,
        "runtime_provenance": {
            "runtime_kind": "mlx_vlm",
            "adapter_name": "mlx-vlm",
            "resolution_source": "authoritative_registry",
        },
        "model_lifecycle": lifecycle,
        "capabilities": ["chat", "streaming", "json", "vision"],
        "qualification_attestation": _full_inventory_attestation(),
    }


def _matching_response(content: str) -> WhooshdStructuredResponse:
    material = STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.material
    provenance = parse_whooshd_runtime_provenance(
        {
            "schema_version": "whooshd.runtime.v1",
            "request_id": "req-stage2i",
            "requested_model_id": material.invocation_model_id,
            "advertised_model_id": material.invocation_model_id,
            "resolved_model_id": material.invocation_model_id,
            "backend_reported_model_id": material.invocation_model_id,
            "runtime_kind": material.runtime_kind,
            "adapter_name": material.adapter_name,
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
                "digest_algorithm": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.digest_algorithm,
                "attestation_digest": STAGE_2D_GEMMA_4_12B_IT_QAT_4BIT_RECORD.expected_attestation_digest,
                "invocation_model_id": material.invocation_model_id,
                "resolved_model_id": material.resolved_model_id,
                "runtime_kind": material.runtime_kind,
                "adapter_name": material.adapter_name,
            },
        }
    )
    assert provenance is not None
    return WhooshdStructuredResponse(
        content=content,
        raw_payload={},
        runtime_provenance=provenance,
        response_correlation=None,
        command_id=HEALTH_COMMAND_ID,
        argument_schema={
            "type": "object",
            "additionalProperties": False,
            "maxProperties": 0,
        },
    )


def _task(*, provider: str, model: str) -> ChatCompletionTask:
    task = ChatCompletionTask(
        user_id="local",
        task_id="task-stage2i",
        thread_id=7,
        provider=provider,
        model=model,
        origin="api:chat.complete|turn_id=11111111-1111-4111-8111-111111111111",
    )
    task.latest_turn_message_id = 2
    task.turn_id = "11111111-1111-4111-8111-111111111111"
    return task


def _seed_completion(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: str,
    model: str,
    settings: Any,
) -> None:
    monkeypatch.setattr(chat_completion_service, "get_settings", lambda: settings)
    monkeypatch.setattr(chat_completion_service, "_command_bus_app", _command_bus_app)
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
        lambda messages, **_kwargs: (messages, {"image_attachment_count": 0}),
    )
    monkeypatch.setattr(
        chat_completion_service, "_task_routing_debug_metadata", lambda _task: {}
    )

    async def _build_messages(_task: ChatCompletionTask):
        return (
            [{"role": "user", "content": "Check health."}],
            provider,
            model,
            {},
            None,
        )

    monkeypatch.setattr(
        chat_completion_service, "build_messages_for_llm", _build_messages
    )


def test_manifest_health_command_is_exact_safe_and_requires_no_arguments() -> None:
    command = _health_command()

    assert command.method == "GET"
    assert command.path_template == "/health"
    assert command.effect == "read"
    assert command.risk == "read_only"
    assert command.idempotency == "safe"
    assert command.approval_mode == "none"
    assert command.input_schema == {
        "path_params": {"type": "object", "properties": {}, "required": []},
        "query": {"type": "object", "properties": {}, "required": []},
        "headers": {"type": "object", "properties": {}, "required": []},
        "body": {},
    }


def test_exposure_allowlist_returns_only_zero_argument_health_for_deepseek() -> None:
    tools = resolve_ordinary_chat_tools(
        provider="deepseek",
        model="deepseek-model",
        provider_vendor=None,
        manifest_commands=_manifest_commands(),
    )

    assert tools == [
        {
            "command_id": HEALTH_COMMAND_ID,
            "description": "Read the current Guardian health status (GET /health).",
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "maxProperties": 0,
            },
        }
    ]


def test_exposure_rejects_unknown_and_mutating_manifest_entries() -> None:
    health_command = _health_command()
    mutating_health = health_command.model_copy(
        update={
            "effect": "write",
            "risk": "mutating",
            "approval_mode": "blocked_phase1",
        }
    )

    assert (
        resolve_ordinary_chat_tools(
            provider="deepseek",
            model="deepseek-model",
            provider_vendor=None,
            manifest_commands=[mutating_health],
        )
        is None
    )
    assert (
        resolve_ordinary_chat_tools(
            provider="deepseek",
            model="deepseek-model",
            provider_vendor=None,
            manifest_commands=[],
        )
        is None
    )


@pytest.mark.parametrize(
    ("provider", "provider_vendor"),
    [
        ("openai", None),
        ("groq", None),
        ("minimax", None),
        ("alibaba", None),
        ("local", "other-runtime"),
    ],
)
def test_other_providers_and_local_runtimes_receive_no_automatic_tools(
    provider: str,
    provider_vendor: str | None,
) -> None:
    assert (
        resolve_ordinary_chat_tools(
            provider=provider,
            model="unqualified-model",
            provider_vendor=provider_vendor,
            manifest_commands=_manifest_commands(),
        )
        is None
    )


def test_whooshd_exposure_requires_real_stage_2g_eligibility() -> None:
    inventory = parse_whooshd_runtime_inventory_entry(_inventory_entry())
    assert inventory is not None
    eligible = project_whooshd_tool_capability(
        inventory=inventory,
        exposure_allowed=True,
    )

    tools = resolve_ordinary_chat_tools(
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        provider_vendor="whooshd",
        manifest_commands=_manifest_commands(),
        whooshd_capability=eligible,
    )
    assert tools is not None
    assert [tool["command_id"] for tool in tools] == [HEALTH_COMMAND_ID]

    for ineligible in (
        project_whooshd_tool_capability(inventory=None, exposure_allowed=True),
        project_whooshd_tool_capability(
            inventory=replace(inventory, loaded=False), exposure_allowed=True
        ),
        project_whooshd_tool_capability(
            inventory=replace(inventory, model_lifecycle="warming"),
            exposure_allowed=True,
        ),
        project_whooshd_tool_capability(inventory=inventory, exposure_allowed=False),
    ):
        assert (
            resolve_ordinary_chat_tools(
                provider="local",
                model="gemma-4-12b-it-qat-4bit",
                provider_vendor="whooshd",
                manifest_commands=_manifest_commands(),
                whooshd_capability=ineligible,
            )
            is None
        )


def test_whooshd_inventory_reader_uses_one_bounded_models_request_and_discards_raw_metadata() -> (
    None
):
    calls: list[dict[str, Any]] = []

    class _Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, Any]:
            entry = _inventory_entry()
            entry.update({"path": "/private/model", "endpoint": "http://private"})
            return {"data": [entry]}

    def _get(url: str, **kwargs: Any) -> _Response:
        calls.append({"url": url, **kwargs})
        return _Response()

    evidence = fetch_whooshd_runtime_inventory_entry(
        SimpleNamespace(
            LOCAL_PROVIDER_VENDOR="whooshd", LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
        ),
        model="gemma-4-12b-it-qat-4bit",
        request_get=_get,
    )

    assert evidence is not None
    assert calls[0]["url"] == "http://127.0.0.1:8000/v1/models"
    assert calls[0]["timeout"] == 1.0
    assert "/private/model" not in repr(evidence)
    assert "http://private" not in repr(evidence)


def test_ordinary_deepseek_health_tool_executes_once_and_plain_answer_is_optional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion(
        monkeypatch,
        provider="deepseek",
        model="deepseek-model",
        settings=SimpleNamespace(LOCAL_PROVIDER_VENDOR=None),
    )
    task = _task(provider="deepseek", model="deepseek-model")
    executions: list[Any] = []
    provider_tools: list[Any] = []

    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *, payload, **_kwargs: (
            executions.append(payload)
            or {"run_id": "run-stage2i-deepseek", "status": "completed"}
        ),
    )

    def _chat(_messages: list[dict[str, Any]], **kwargs: Any) -> DeepSeekResponse:
        provider_tools.append(kwargs.get("tools"))
        if len(provider_tools) == 1:
            return DeepSeekResponse(
                content="",
                reasoning_content=None,
                tool_calls=[
                    {
                        "command_id": HEALTH_COMMAND_ID,
                        "tool_call_id": "call-health",
                        "arguments": {},
                    }
                ],
                raw_assistant_message={"role": "assistant", "tool_calls": []},
                raw_payload={},
            )
        return DeepSeekResponse(
            content="Guardian is healthy.",
            reasoning_content=None,
            tool_calls=[],
            raw_assistant_message={
                "role": "assistant",
                "content": "Guardian is healthy.",
            },
            raw_payload={},
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat)
    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )

    assert task.tools is not None and [tool["command_id"] for tool in task.tools] == [
        HEALTH_COMMAND_ID
    ]
    assert len(executions) == 1
    assert executions[0].command_id == HEALTH_COMMAND_ID
    assert executions[0].arguments.model_dump() == {
        "path_params": {},
        "query": {},
        "headers": {},
        "body": {},
    }
    assert provider_tools[0] == task.tools
    assert result["assistant_text"] == "Guardian is healthy."
    assert result["payload_summary"]["toolTurnState"] == "completed"
    assert result["payload_summary"]["loopStopReason"] == "tool_turn_completed"
    assert result["payload_summary"]["commandRunId"] == "run-stage2i-deepseek"
    assert result["payload_summary"]["toolExposure"] == {
        "automatic": True,
        "advertisedToolCount": 1,
        "advertisedToolCommandIds": [HEALTH_COMMAND_ID],
        "providerDispatchToolCount": 1,
        "providerDispatchToolCommandIds": [HEALTH_COMMAND_ID],
        "commandIdsTruncated": False,
    }


def test_advertised_deepseek_health_capability_does_not_force_tool_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion(
        monkeypatch,
        provider="deepseek",
        model="deepseek-model",
        settings=SimpleNamespace(LOCAL_PROVIDER_VENDOR=None),
    )
    task = _task(provider="deepseek", model="deepseek-model")
    executions: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *, payload, **_kwargs: executions.append(payload),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: DeepSeekResponse(
            content="No health check needed.",
            reasoning_content=None,
            tool_calls=[],
            raw_assistant_message={
                "role": "assistant",
                "content": "No health check needed.",
            },
            raw_payload={},
        ),
    )

    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )

    assert task.tools is not None
    assert executions == []
    assert result["assistant_text"] == "No health check needed."
    assert result["payload_summary"]["toolTurnState"] == "idle"
    assert result["payload_summary"]["loopStopReason"] == "plain_answer"
    assert result["payload_summary"]["commandRunId"] is None
    assert result["payload_summary"]["toolExposure"] == {
        "automatic": True,
        "advertisedToolCount": 1,
        "advertisedToolCommandIds": [HEALTH_COMMAND_ID],
        "providerDispatchToolCount": 1,
        "providerDispatchToolCommandIds": [HEALTH_COMMAND_ID],
        "commandIdsTruncated": False,
    }


def test_explicit_empty_tools_remain_empty_and_are_observed_as_nonautomatic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion(
        monkeypatch,
        provider="deepseek",
        model="deepseek-model",
        settings=SimpleNamespace(LOCAL_PROVIDER_VENDOR=None),
    )
    task = _task(provider="deepseek", model="deepseek-model")
    task.tools = []
    provider_tools: list[Any] = []
    executions: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *, payload, **_kwargs: executions.append(payload),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **kwargs: (
            provider_tools.append(kwargs.get("tools"))
            or DeepSeekResponse(
                content="Plain answer.",
                reasoning_content=None,
                tool_calls=[],
                raw_assistant_message={"role": "assistant", "content": "Plain answer."},
                raw_payload={},
            )
        ),
    )

    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )

    assert task.tools == []
    assert provider_tools == [[]]
    assert executions == []
    assert result["payload_summary"]["toolExposure"] == {
        "automatic": False,
        "advertisedToolCount": 0,
        "advertisedToolCommandIds": [],
        "providerDispatchToolCount": 0,
        "providerDispatchToolCommandIds": [],
        "commandIdsTruncated": False,
    }


def test_automatic_unsupported_provider_records_no_exposure_or_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion(
        monkeypatch,
        provider="groq",
        model="unsupported-model",
        settings=SimpleNamespace(LOCAL_PROVIDER_VENDOR=None),
    )
    task = _task(provider="groq", model="unsupported-model")
    provider_tools: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **kwargs: provider_tools.append(kwargs.get("tools"))
        or "Plain answer.",
    )

    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )

    assert task.tools is None
    assert provider_tools == [None]
    assert result["payload_summary"]["toolExposure"] == {
        "automatic": True,
        "advertisedToolCount": 0,
        "advertisedToolCommandIds": [],
        "providerDispatchToolCount": 0,
        "providerDispatchToolCommandIds": [],
        "commandIdsTruncated": False,
    }


def test_tool_exposure_evidence_is_bounded_and_contains_no_tool_payloads() -> None:
    tools = [
        {
            "command_id": f"op::read_{index:02d}",
            "description": "private description",
            "input_schema": {"type": "object", "properties": {"secret": {}}},
            "arguments": {"secret": "do-not-record"},
            "messages": ["do-not-record"],
        }
        for index in range(17)
    ]
    evidence = chat_completion_service._build_tool_exposure_evidence(
        automatic=True,
        tools=tools,
    )
    chat_completion_service._record_provider_dispatch_tool_exposure(
        evidence,
        tools=tools,
    )
    payload = chat_completion_service._tool_exposure_payload(evidence)

    assert payload["advertisedToolCount"] == 17
    assert payload["providerDispatchToolCount"] == 17
    assert len(payload["advertisedToolCommandIds"]) == 16
    assert len(payload["providerDispatchToolCommandIds"]) == 16
    assert payload["commandIdsTruncated"] is True
    assert set(payload) == {
        "automatic",
        "advertisedToolCount",
        "advertisedToolCommandIds",
        "providerDispatchToolCount",
        "providerDispatchToolCommandIds",
        "commandIdsTruncated",
    }
    rendered = repr(payload)
    for forbidden in (
        "description",
        "input_schema",
        "parameters",
        "arguments",
        "messages",
        "payload",
        "credential",
        "reasoning_content",
        "do-not-record",
    ):
        assert forbidden not in rendered


def test_eligible_whooshd_executes_once_and_stale_response_identity_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        LOCAL_PROVIDER_VENDOR="whooshd", LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
    )
    _seed_completion(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        settings=settings,
    )
    inventory = parse_whooshd_runtime_inventory_entry(_inventory_entry())
    assert inventory is not None
    monkeypatch.setattr(
        chat_completion_service,
        "fetch_whooshd_runtime_inventory_entry",
        lambda _settings, *, model: inventory,
    )
    task = _task(provider="local", model="gemma-4-12b-it-qat-4bit")
    executions: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *, payload, **_kwargs: (
            executions.append(payload)
            or {"run_id": "run-stage2i-whooshd", "status": "completed"}
        ),
    )
    calls = 0

    def _chat(
        _messages: list[dict[str, Any]], **_kwargs: Any
    ) -> WhooshdStructuredResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _matching_response(
                '{"kind":"tool_decision","text":null,"command_id":"op::health_health_get","arguments":{}}'
            )
        return _matching_response(
            '{"kind":"assistant","text":"Guardian is healthy.","command_id":null,"arguments":{}}'
        )

    monkeypatch.setattr(chat_completion_service, "chat_with_ai", _chat)
    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )

    assert task.tools is not None
    assert len(executions) == 1
    assert executions[0].command_id == HEALTH_COMMAND_ID
    assert result["payload_summary"]["toolTurnState"] == "completed"

    stale_task = _task(provider="local", model="gemma-4-12b-it-qat-4bit")
    stale_calls: list[Any] = []
    monkeypatch.setattr(
        chat_completion_service,
        "execute_invoke",
        lambda *, payload, **_kwargs: stale_calls.append(payload),
    )
    stale_response = _matching_response(
        '{"kind":"tool_decision","text":null,"command_id":"op::health_health_get","arguments":{}}'
    )
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *_args, **_kwargs: replace(
            stale_response,
            runtime_provenance=replace(
                stale_response.runtime_provenance, resolved_model_id="other-model"
            ),
        ),
    )

    with pytest.raises(Exception, match="provenance"):
        chat_completion_service.run_chat_completion_task(
            stale_task, persist_assistant_message=False
        )
    assert stale_task.tools is not None
    assert stale_calls == []


def test_ineligible_whooshd_keeps_the_ordinary_streaming_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        LOCAL_PROVIDER_VENDOR="whooshd", LOCAL_BASE_URL="http://127.0.0.1:8000/v1"
    )
    _seed_completion(
        monkeypatch,
        provider="local",
        model="gemma-4-12b-it-qat-4bit",
        settings=settings,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "fetch_whooshd_runtime_inventory_entry",
        lambda _settings, *, model: None,
    )
    task = _task(provider="local", model="gemma-4-12b-it-qat-4bit")
    streams: list[Any] = []

    def _stream(*_args: Any, **_kwargs: Any):
        streams.append(True)

        def _iterator():
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

        return _iterator()

    monkeypatch.setattr(chat_completion_service, "stream_local", _stream)
    result = chat_completion_service.run_chat_completion_task(
        task, persist_assistant_message=False
    )

    assert task.tools is None
    assert streams == [True]
    assert result["assistant_text"] == "ordinary local answer"
