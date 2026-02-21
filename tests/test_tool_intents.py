import json

import pytest

from guardian.context.broker import (
    build_assistant_response_payload,
    maybe_extract_tool_intents,
)
from guardian.context.tool_intents import (
    MAX_TOOL_INTENT_ARGS_JSON_BYTES,
    MAX_TOOL_INTENT_REASON_CHARS,
    MAX_TOOL_INTENTS_PER_MESSAGE,
    ToolIntentParseError,
    ToolRisk,
    classify_tool_intent,
    parse_tool_intents,
)


def test_parse_single_intent() -> None:
    text = """
    {"id":"11111111-1111-1111-1111-111111111111","tool":"fs.search","args":{"root":"/x","glob":"**/*.md"},"reason":"find notes"}
    """
    intents = parse_tool_intents(text)
    assert len(intents) == 1
    assert intents[0].tool == "fs.search"
    assert intents[0].args["root"] == "/x"
    assert intents[0].intent_id == "11111111-1111-1111-1111-111111111111"


def test_parse_array_intents() -> None:
    text = """
    [
      {"id":"11111111-1111-1111-1111-111111111111","tool":"fs.search","args":{"root":"/x","glob":"**/*.md"},"reason":"search"},
      {"id":"22222222-2222-2222-2222-222222222222","tool":"fs.read_file","args":{"path":"/x/a.md"},"reason":"read"}
    ]
    """
    intents = parse_tool_intents(text)
    assert len(intents) == 2
    assert intents[1].tool == "fs.read_file"


def test_reject_invalid_json() -> None:
    with pytest.raises(ToolIntentParseError):
        parse_tool_intents("{not json")


def test_reject_missing_required_keys() -> None:
    with pytest.raises(ToolIntentParseError):
        parse_tool_intents(
            '{"id":"11111111-1111-1111-1111-111111111111","tool":"fs.search","args":{}}'
        )


def test_policy_unknown_tool_defaults_sensitive() -> None:
    intents = parse_tool_intents(
        '{"id":"11111111-1111-1111-1111-111111111111","tool":"weird.tool","args":{},"reason":"check"}'
    )
    policy = classify_tool_intent(intents[0])
    assert policy.risk == ToolRisk.SENSITIVE


def test_broker_marks_fs_search_auto_approved() -> None:
    tool_block, tool_err = maybe_extract_tool_intents(
        '{"id":"11111111-1111-1111-1111-111111111111","tool":"fs.search","args":{"root":"/vault","glob":"**/*.md","query":"iddb_policy"},"reason":"find policy"}'
    )
    assert tool_err is None
    assert tool_block is not None
    assert len(tool_block["tool_intents"]) == 1
    record = tool_block["tool_intents"][0]
    assert record["tool"] == "fs.search"
    assert record["approved"] is True
    assert record["requires_consent"] is False
    assert tool_block["pending_tool_intents"] == []


def test_broker_marks_fs_read_file_consent_required() -> None:
    tool_block, tool_err = maybe_extract_tool_intents(
        '{"id":"22222222-2222-2222-2222-222222222222","tool":"fs.read_file","args":{"path":"/vault/secrets.md"},"reason":"need file contents"}'
    )
    assert tool_err is None
    assert tool_block is not None
    assert len(tool_block["tool_intents"]) == 1
    record = tool_block["tool_intents"][0]
    assert record["tool"] == "fs.read_file"
    assert record["approved"] is False
    assert record["requires_consent"] is True
    assert len(tool_block["pending_tool_intents"]) == 1


def test_build_assistant_response_payload_defaults_to_redacted_tool_views(
    monkeypatch,
) -> None:
    monkeypatch.delenv("CODEXIFY_DEBUG_UNREDACTED_TOOL_INTENTS", raising=False)

    payload = {
        "id": "66666666-6666-6666-6666-666666666666",
        "tool": "fs.read_file",
        "args": {
            "path": "/vault/secrets.md",
            "api_key": "test",
            "headers": {"Authorization": "Bearer test"},
            "nested": {"client_secret": "test"},
            "query": "find policy",
            "model": "gpt-test",
        },
        "reason": "need file contents",
    }

    response = build_assistant_response_payload(json.dumps(payload))

    assert len(response["tool_intents"]) == 1
    assert len(response["tool_intents_redacted"]) == 1
    assert len(response["pending_tool_intents"]) == 1
    assert len(response["pending_tool_intents_redacted"]) == 1

    redacted = response["tool_intents"][0]

    # Redacted payload masks sensitive keys and keeps safe fields.
    assert redacted["args"]["api_key"] == "[REDACTED]"
    assert redacted["args"]["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["args"]["nested"]["client_secret"] == "[REDACTED]"
    assert redacted["args"]["query"] == "find policy"
    assert redacted["args"]["model"] == "gpt-test"

    pending_redacted = response["pending_tool_intents_redacted"][0]
    assert pending_redacted["args"]["api_key"] == "[REDACTED]"
    assert pending_redacted["args"]["headers"]["Authorization"] == "[REDACTED]"
    assert "tool_intents_unredacted" not in response
    assert "pending_tool_intents_unredacted" not in response


def test_build_assistant_response_payload_debug_emits_unredacted_tool_views(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_DEBUG_UNREDACTED_TOOL_INTENTS", "1")

    payload = {
        "id": "66666666-6666-6666-6666-666666666666",
        "tool": "fs.read_file",
        "args": {
            "path": "/vault/secrets.md",
            "api_key": "test",
            "headers": {"Authorization": "Bearer test"},
            "nested": {"client_secret": "test"},
            "query": "find policy",
            "model": "gpt-test",
        },
        "reason": "need file contents",
    }

    response = build_assistant_response_payload(json.dumps(payload))
    assert len(response["tool_intents"]) == 1
    assert len(response["tool_intents_unredacted"]) == 1
    assert len(response["pending_tool_intents"]) == 1
    assert len(response["pending_tool_intents_unredacted"]) == 1

    # Default fields remain redacted.
    assert response["tool_intents"][0]["args"]["api_key"] == "[REDACTED]"
    assert (
        response["tool_intents"][0]["args"]["headers"]["Authorization"]
        == "[REDACTED]"
    )
    # Debug fields expose raw values.
    assert response["tool_intents_unredacted"][0]["args"]["api_key"] == "test"
    assert (
        response["tool_intents_unredacted"][0]["args"]["headers"][
            "Authorization"
        ]
        == "Bearer test"
    )


def test_parse_tool_intents_accepts_fenced_json_single_intent() -> None:
    payload = """```json
    {
      "id": "11111111-1111-1111-1111-111111111111",
      "tool": "fs.search",
      "args": {"query": "hello"},
      "reason": "find the thing"
    }
    ```"""
    intents = parse_tool_intents(payload)
    assert len(intents) == 1
    assert intents[0].tool == "fs.search"


def test_parse_tool_intents_accepts_fenced_json_compact_closing() -> None:
    payload = (
        "```json\n"
        "{"
        '  "id": "33333333-3333-3333-3333-333333333333",'
        '  "tool": "fs.search",'
        '  "args": {"query": "hello"},'
        '  "reason": "find the thing"'
        "}```"
    )
    intents = parse_tool_intents(payload)
    assert len(intents) == 1
    assert intents[0].tool == "fs.search"


def test_parse_tool_intents_allows_extra_keys() -> None:
    payload = {
        "id": "22222222-2222-2222-2222-222222222222",
        "tool": "fs.search",
        "args": {"query": "hello"},
        "reason": "find the thing",
        "extra_field": "ignored",
        "nested_extra": {"a": 1},
    }
    intents = parse_tool_intents(json.dumps(payload))
    assert len(intents) == 1
    assert intents[0].tool == "fs.search"


def test_parse_tool_intents_rejects_too_many_intents() -> None:
    payload = [
        {
            "id": f"{i:08d}-0000-0000-0000-000000000000",
            "tool": "fs.search",
            "args": {"query": "x"},
            "reason": "r",
        }
        for i in range(MAX_TOOL_INTENTS_PER_MESSAGE + 1)
    ]
    with pytest.raises(ToolIntentParseError) as exc:
        parse_tool_intents(json.dumps(payload))
    assert "tool_intents_too_many" in str(exc.value)


def test_parse_tool_intents_rejects_reason_too_long() -> None:
    payload = {
        "id": "44444444-4444-4444-4444-444444444444",
        "tool": "fs.search",
        "args": {"query": "hello"},
        "reason": "x" * (MAX_TOOL_INTENT_REASON_CHARS + 1),
    }
    with pytest.raises(ToolIntentParseError) as exc:
        parse_tool_intents(json.dumps(payload))
    assert "tool_intents_reason_too_long" in str(exc.value)


def test_parse_tool_intents_rejects_args_too_large() -> None:
    # Build a payload that will exceed MAX_TOOL_INTENT_ARGS_JSON_BYTES
    big = "x" * (MAX_TOOL_INTENT_ARGS_JSON_BYTES + 1024)
    payload = {
        "id": "55555555-5555-5555-5555-555555555555",
        "tool": "fs.search",
        "args": {"blob": big},
        "reason": "r",
    }
    with pytest.raises(ToolIntentParseError) as exc:
        parse_tool_intents(json.dumps(payload))
    assert "tool_intents_args_too_large" in str(exc.value)
