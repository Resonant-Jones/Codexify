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
    {"type":"tool_intent","tool":"fs.search","args":{"root":"/x","glob":"**/*.md"},"reason":"find notes"}
    """
    intents = parse_tool_intents(text)
    assert len(intents) == 1
    assert intents[0].tool == "fs.search"
    assert intents[0].args["root"] == "/x"
    assert intents[0].intent_id


def test_parse_array_intents() -> None:
    text = """
    [
      {"type":"tool_intent","tool":"fs.search","args":{"root":"/x","glob":"**/*.md"}},
      {"type":"tool_intent","tool":"fs.read_file","args":{"path":"/x/a.md"}}
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
        parse_tool_intents('{"type":"tool_intent","tool":"fs.search"}')


def test_policy_unknown_tool_defaults_sensitive() -> None:
    intents = parse_tool_intents(
        '{"type":"tool_intent","tool":"weird.tool","args":{}}'
    )
    policy = classify_tool_intent(intents[0])
    assert policy.risk == ToolRisk.SENSITIVE


def test_broker_marks_fs_search_auto_approved() -> None:
    tool_block, tool_err = maybe_extract_tool_intents(
        '{"type":"tool_intent","tool":"fs.search","args":{"root":"/vault","glob":"**/*.md","query":"iddb_policy"}}'
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
        '{"type":"tool_intent","tool":"fs.read_file","args":{"path":"/vault/secrets.md"}}'
    )
    assert tool_err is None
    assert tool_block is not None
    assert len(tool_block["tool_intents"]) == 1
    record = tool_block["tool_intents"][0]
    assert record["tool"] == "fs.read_file"
    assert record["approved"] is False
    assert record["requires_consent"] is True
    assert len(tool_block["pending_tool_intents"]) == 1
