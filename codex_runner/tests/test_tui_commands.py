from __future__ import annotations

from tui_commands import (
    ParsedCommand,
    apply_change,
    coerce_value,
    filter_suggestions,
    parse_bool,
    parse_command,
    suggestion_pool,
)
from tui_state import RunnerSettings


def test_parse_command() -> None:
    parsed = parse_command("/set provider claude")
    assert isinstance(parsed, ParsedCommand)
    assert parsed.name == "set"
    assert parsed.args == ["provider", "claude"]


def test_coerce_value() -> None:
    assert coerce_value("provider", "claude") == "claude"
    assert coerce_value("passes", "3") == 3
    assert coerce_value("execute_mode", "execute") == "execute"
    assert coerce_value("codex_config", "a,b") == ["a", "b"]


def test_parse_bool() -> None:
    assert parse_bool("true") is True
    assert parse_bool("false") is False
    assert parse_bool("maybe") is None


def test_apply_change() -> None:
    settings = RunnerSettings()
    apply_change(settings, "provider", "claude")
    assert settings.provider == "claude"


def test_filter_suggestions() -> None:
    settings = RunnerSettings()
    pool = suggestion_pool(settings, {}, ["fast", "safe"])
    filtered = filter_suggestions(pool, "preset fa")
    assert any(item == "/preset fast" for item in filtered)
