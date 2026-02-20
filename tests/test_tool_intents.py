import json

import pytest

from guardian.context.broker import maybe_extract_tool_intents
from guardian.context.tool_intents import (
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
