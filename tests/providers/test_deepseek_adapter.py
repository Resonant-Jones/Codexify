from guardian.providers.deepseek_adapter import (
    build_continuation_messages,
    build_payload,
    build_tool_definitions,
    normalize_tool_calls,
    parse_response,
)


def test_thinking_payload_is_root_level_and_omits_sampling_controls():
    payload = build_payload(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": "solve"}],
        reasoning_mode="think",
        temperature=0.2,
    )

    assert payload["thinking"] == {"type": "enabled"}
    assert payload["reasoning_effort"] == "high"
    for key in ("temperature", "top_p", "presence_penalty", "frequency_penalty"):
        assert key not in payload
    assert "extra_body" not in payload


def test_default_and_no_think_explicitly_disable_thinking():
    for mode in (None, "default", "no_think"):
        payload = build_payload(
            model="deepseek-v4-flash",
            messages=[],
            reasoning_mode=mode,
            temperature=0.3,
        )
        assert payload["thinking"] == {"type": "disabled"}
        assert payload["temperature"] == 0.3
        assert "reasoning_effort" not in payload


def test_native_response_preserves_reasoning_and_raw_assistant_message():
    response = parse_response(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "visible",
                        "reasoning_content": "opaque",
                        "tool_calls": [],
                    }
                }
            ]
        }
    )

    assert response.content == "visible"
    assert response.reasoning_content == "opaque"
    assert response.raw_assistant_message["reasoning_content"] == "opaque"


def test_authorized_commands_use_safe_aliases():
    definitions, aliases = build_tool_definitions(
        [{"command_id": "op::guardian.some_command", "description": "read"}]
    )

    assert aliases == {"codexify_tool_0": "op::guardian.some_command"}
    assert definitions[0]["function"]["name"] == "codexify_tool_0"
    assert "op::guardian.some_command" not in str(definitions)


# ---------------------------------------------------------------------------
# Stage 2B canonical provider-neutral contract tests.
# ---------------------------------------------------------------------------


def test_build_continuation_messages_replays_assistant_envelope_and_tool_call_id():
    """Test F: native result continuation preserves the correlation identity.

    The adapter receives the semantic assistant message envelope (opaque), the
    correlation identity, and the command result. It returns the DeepSeek
    continuation messages (assistant replay + tool message) without inspecting
    its private fields.
    """
    raw_assistant_message = {
        "role": "assistant",
        "content": None,
        "reasoning_content": "private reasoning",
        "tool_calls": [{"id": "call-7", "type": "function"}],
    }
    command_result = {
        "run_id": "run-7",
        "status": "completed",
        "invoke_version": "1.0",
        "manifest_version": "1.0",
        "events_url": "/events/run-7",
        "inline_result": {"value": "ok"},
    }

    next_messages = build_continuation_messages(
        [
            {"role": "user", "content": "initial"},
        ],
        raw_assistant_message=raw_assistant_message,
        tool_call_id="call-7",
        command_result=command_result,
    )

    assert next_messages[0] == {"role": "user", "content": "initial"}
    assert next_messages[1] == raw_assistant_message
    tool_message = next_messages[2]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call-7"
    assert "private reasoning" not in tool_message["content"]
    assert "run_id" in tool_message["content"]
    assert "call-7" not in tool_message["content"]


def test_build_continuation_messages_preserves_provider_private_reasoning_through_round_trip():
    """Test G: provider continuation-state isolation.

    The adapter preserves reasoning_content inside the assistant message
    envelope opaquely. The generic runtime does not inspect, branch on, or
    persist this field. The continuation request must replay the full
    assistant message so the provider can continue inference.
    """
    raw_assistant_message = {
        "role": "assistant",
        "content": "",
        "reasoning_content": "deepseek-private-thinking",
        "tool_calls": [{"id": "call-R", "type": "function"}],
    }

    next_messages = build_continuation_messages(
        [],
        raw_assistant_message=raw_assistant_message,
        tool_call_id="call-R",
        command_result={"status": "ok"},
    )

    # The full assistant message envelope (including provider-private
    # reasoning) is replayed intact. The adapter does not parse, redact, or
    # rewrite the reasoning content.
    assert next_messages[0]["reasoning_content"] == "deepseek-private-thinking"
    assert next_messages[1]["role"] == "tool"
    assert next_messages[1]["tool_call_id"] == "call-R"


def test_build_continuation_messages_handles_missing_assistant_envelope():
    """The adapter tolerates a missing raw assistant message envelope.

    The provider-neutral contract forbids the generic runtime from requiring
    provider-private fields. The adapter must therefore accept a None
    assistant message and still emit a valid tool continuation.
    """
    next_messages = build_continuation_messages(
        [{"role": "user", "content": "ask"}],
        raw_assistant_message=None,
        tool_call_id="call-none",
        command_result={"status": "ok"},
    )

    assert next_messages == [
        {"role": "user", "content": "ask"},
        {
            "role": "tool",
            "tool_call_id": "call-none",
            "content": "{\"status\": \"ok\"}",
        },
    ]


def test_normalize_tool_calls_returns_unknown_alias_marker_for_unmapped_native_call():
    """Test C: unknown alias cannot yield an executable canonical command.

    When the DeepSeek adapter receives a native tool call whose provider-visible
    function name has no entry in the alias map (for example, a stale
    codexify_tool_N mapping from a previous authorized set), the normalized
    command_id is empty. The Stage 1 advertised-subset gate treats this as
    zero authority and blocks before execute_invoke.
    """
    response = parse_response(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-stale",
                                "type": "function",
                                "function": {
                                    "name": "codexify_tool_77",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )

    normalized = normalize_tool_calls(
        response,
        aliases={"codexify_tool_0": "op::advertised"},
    )

    assert normalized[0]["tool_call_id"] == "call-stale"
    # The empty command_id is what the Stage 1 gate sees. The model-generated
    # provider alias does not become a canonical command_id.
    assert normalized[0]["command_id"] == ""
    assert normalized[0]["alias"] == "codexify_tool_77"
    # The raw JSON argument string is preserved untouched by the adapter; the
    # downstream chat completion normalization is responsible for parsing it.
    assert normalized[0]["arguments"] == "{}"
