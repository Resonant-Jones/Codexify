from __future__ import annotations

import json

import pytest

from guardian.providers.whooshd_tool_adapter import (
    QUALIFIED_ADAPTER_NAME,
    QUALIFIED_EXECUTION_MODE,
    QUALIFIED_MODEL_ALIAS,
    QUALIFIED_RESOLUTION_SOURCE,
    QUALIFIED_RUNTIME_KIND,
    WhooshdStructuredResponse,
    WhooshdStructuredTransportError,
    build_continuation_messages,
    is_qualified_transport_candidate,
    parse_structured_response,
    prepare_structured_transport,
)


def _tool(command_id: str = "op::lookup_widget") -> dict:
    return {
        "command_id": command_id,
        "description": "Return the status of one synthetic widget.",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["widget_id"],
            "properties": {
                "widget_id": {"type": "string", "enum": ["alpha"]}
            },
        },
    }


def _provenance(**overrides) -> dict:
    payload = {
        "requested_model_id": QUALIFIED_MODEL_ALIAS,
        "advertised_model_id": QUALIFIED_MODEL_ALIAS,
        "resolved_model_id": QUALIFIED_MODEL_ALIAS,
        "runtime_kind": QUALIFIED_RUNTIME_KIND,
        "adapter_name": QUALIFIED_ADAPTER_NAME,
        "resolution_source": QUALIFIED_RESOLUTION_SOURCE,
        "execution_mode": QUALIFIED_EXECUTION_MODE,
        "streaming": False,
    }
    payload.update(overrides)
    return payload


def _response(content: str, *, command_id: str = "op::lookup_widget", **overrides):
    prepared = prepare_structured_transport(
        provider_vendor="whooshd",
        model=QUALIFIED_MODEL_ALIAS,
        tools=[_tool(command_id)],
    )
    assert prepared is not None
    return WhooshdStructuredResponse(
        content=content,
        raw_payload={"choices": [{"message": {"content": content}}]},
        runtime_provenance=_provenance(**overrides),
        response_correlation=None,
        command_id=prepared.command_id,
        argument_schema=prepared.argument_schema,
    )


def test_exact_target_gate_is_not_provider_or_model_family_capability():
    assert is_qualified_transport_candidate(
        provider="local",
        provider_vendor="whooshd",
        model=QUALIFIED_MODEL_ALIAS,
        tools=[_tool()],
    )
    for provider, vendor, model in (
        ("local", "whooshd", "another-gemma"),
        ("local", "whooshd", "another-mlx-model"),
        ("local", "ollama", QUALIFIED_MODEL_ALIAS),
        ("deepseek", "whooshd", QUALIFIED_MODEL_ALIAS),
    ):
        assert not is_qualified_transport_candidate(
            provider=provider,
            provider_vendor=vendor,
            model=model,
            tools=[_tool()],
        )


def test_prepare_one_tool_preserves_exact_model_turn_schema_and_instruction():
    prepared = prepare_structured_transport(
        provider_vendor="whooshd",
        model=QUALIFIED_MODEL_ALIAS,
        tools=[_tool()],
    )

    assert prepared is not None
    assert prepared.command_id == "op::lookup_widget"
    schema = prepared.response_format["json_schema"]["schema"]
    assert prepared.response_format["type"] == "json_schema"
    assert prepared.response_format["json_schema"]["strict"] is True
    assert schema["oneOf"][0]["properties"]["kind"] == {"const": "assistant"}
    tool_branch = schema["oneOf"][1]
    assert tool_branch["properties"]["command_id"] == {"const": "op::lookup_widget"}
    assert tool_branch["properties"]["arguments"] == _tool()["input_schema"]
    assert "op::lookup_widget" in prepared.transport_instruction
    assert "free-form JSON prompting" in prepared.transport_instruction


def test_prepare_rejects_multiple_tools_and_unsupported_schema_before_inference():
    with pytest.raises(WhooshdStructuredTransportError, match="exactly one"):
        prepare_structured_transport(
            provider_vendor="whooshd",
            model=QUALIFIED_MODEL_ALIAS,
            tools=[_tool(), _tool("op::other")],
        )

    unsupported = _tool()
    unsupported["input_schema"]["properties"]["widget_id"] = {
        "type": "string",
        "pattern": ".*",
    }
    with pytest.raises(WhooshdStructuredTransportError, match="does not support"):
        prepare_structured_transport(
            provider_vendor="whooshd",
            model=QUALIFIED_MODEL_ALIAS,
            tools=[unsupported],
        )


def test_prepare_preserves_no_tools_and_other_targets_as_ordinary_local_chat():
    assert (
        prepare_structured_transport(
            provider_vendor="whooshd", model=QUALIFIED_MODEL_ALIAS, tools=None
        )
        is None
    )
    assert (
        prepare_structured_transport(
            provider_vendor="whooshd", model="other-local-model", tools=[_tool()]
        )
        is None
    )


def test_strict_parser_normalizes_assistant_and_tool_decision_without_tool_call_id():
    assistant = parse_structured_response(
        _response(
            '{"kind":"assistant","text":"Hello","command_id":null,"arguments":{}}'
        )
    )
    assert assistant.kind == "assistant"
    assert assistant.text == "Hello"
    assert assistant.command_id is None

    tool = parse_structured_response(
        _response(
            '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}'
        )
    )
    assert tool.kind == "tool_decision"
    assert tool.command_id == "op::lookup_widget"
    assert tool.arguments == {"widget_id": "alpha"}


@pytest.mark.parametrize(
    "content",
    [
        '```json\n{"kind":"assistant","text":"Hello","command_id":null,"arguments":{}}\n```',
        'Here is JSON: {"kind":"assistant","text":"Hello","command_id":null,"arguments":{}}',
        '{"kind":"assistant","text":"Hello","command_id":null}',
        '{"kind":"assistant","text":"Hello","command_id":null,"arguments":{},"extra":true}',
        '{"kind":"assistant","text":"Hello","command_id":"op::lookup_widget","arguments":{}}',
        '{"kind":"tool_decision","text":"not null","command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}',
        '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"beta"}}',
        '{"kind":"unknown","text":"Hello","command_id":null,"arguments":{}}',
    ],
)
def test_strict_parser_rejects_non_model_turn_content(content: str):
    with pytest.raises(WhooshdStructuredTransportError):
        parse_structured_response(_response(content))


def test_strict_parser_rejects_alternate_command_and_duplicate_fields():
    with pytest.raises(WhooshdStructuredTransportError, match="not advertised"):
        parse_structured_response(
            _response(
                '{"kind":"tool_decision","text":null,"command_id":"op::other","arguments":{"widget_id":"alpha"}}'
            )
        )
    with pytest.raises(WhooshdStructuredTransportError, match="duplicate"):
        parse_structured_response(
            _response(
                '{"kind":"assistant","kind":"assistant","text":"Hello","command_id":null,"arguments":{}}'
            )
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"resolved_model_id": "different-model"},
        {"resolved_model_id": None},
        {"runtime_kind": "llama_cpp"},
        {"adapter_name": "mlx-lm"},
        {"streaming": True},
        {"requested_model_id": None},
    ],
)
def test_tool_decision_fails_closed_on_missing_or_mismatched_runtime_provenance(
    overrides: dict,
):
    with pytest.raises(WhooshdStructuredTransportError, match="provenance"):
        parse_structured_response(
            _response(
                '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}',
                **overrides,
            )
        )


def test_structured_continuation_contains_only_semantic_decision_and_result():
    messages = build_continuation_messages(
        [{"role": "user", "content": "What is widget alpha?"}],
        command_id="op::lookup_widget",
        arguments={"widget_id": "alpha"},
        command_result={"status": "green"},
    )

    assert messages[1] == {
        "role": "assistant",
        "content": '{"kind":"tool_decision","text":null,"command_id":"op::lookup_widget","arguments":{"widget_id":"alpha"}}',
    }
    assert messages[2]["role"] == "user"
    envelope = json.loads(messages[2]["content"].split("\n", 1)[1])
    assert envelope["command_id"] == "op::lookup_widget"
    assert envelope["arguments"] == {"widget_id": "alpha"}
    assert envelope["result"] == {"status": "green"}
    assert "tools" not in envelope
    assert "tool_calls" not in envelope
    assert "tool_call_id" not in envelope
