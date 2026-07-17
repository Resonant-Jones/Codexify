from guardian.providers.deepseek_adapter import (
    build_payload,
    build_tool_definitions,
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
