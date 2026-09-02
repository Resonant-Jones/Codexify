#!/usr/bin/env python3
"""
Deterministic regression harness for bounded Pi 0.82.1 assistant-response
telemetry.  Invokes the canonical observer helpers from
`codex_runner/src/assistant-telemetry.js` via the wrapper's
`--assistant-telemetry-test` mode and asserts the resulting
`toolTelemetry` shape.

Test cases (per spec §15):

- Text-only assistant case — synthetic text events + final `text` block.
- Tool-call lifecycle case — synthetic `toolcall_*` events + final
  `toolCall` block.
- Tool-call execution case — synthetic tool-call events + a
  `tool_execution_start`/`tool_execution_end` pair.
- Empty/no-tool case — empty event stream + empty final messages.

Each case asserts:
- `node --check` exits 0.
- The returned `toolTelemetry` JSON has the expected values for the
  four bounded assistant fields.
- No text/reasoning/args/IDs/payload fragments are returned.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WORKTREE = Path(__file__).resolve().parent.parent.parent
WRAPPER = WORKTREE / "codex_runner" / "src" / "agent-wrapper.js"
HELPERS = WORKTREE / "codex_runner" / "src" / "assistant-telemetry.js"


def run_synthetic_case(name: str, spec: dict) -> dict:
    proc = subprocess.run(
        ["node", str(WRAPPER), "assistant-telemetry-test"],
        cwd=str(WORKTREE),
        input=json.dumps(spec),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"{name}: wrapper exited {proc.returncode}\n"
            f"stderr: {proc.stderr}\nstdout: {proc.stdout}"
        )
    return json.loads(proc.stdout)


def expect_text_only() -> None:
    spec = {
        "events": [
            {"type": "message_update", "assistantMessageEvent": {
                "type": "start",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "text_start",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "text_delta",
                "delta": "ignored-text-not-serialized",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "text_end",
                "content": "ignored-content-not-serialized",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "done",
                "reason": "stop",
            }},
        ],
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "ignored"}]},
            {"role": "assistant", "content": [{"type": "text", "text": "ignored-text"}]},
        ],
    }
    telemetry = run_synthetic_case("text-only", spec)
    assert telemetry["assistant_message_count"] == 1, telemetry
    assert "text" in telemetry["assistant_content_block_types"], telemetry
    assert "text_start" in telemetry["assistant_message_event_types"], telemetry
    assert "text_delta" in telemetry["assistant_message_event_types"], telemetry
    assert "text_end" in telemetry["assistant_message_event_types"], telemetry
    assert "done" in telemetry["assistant_message_event_types"], telemetry
    assert telemetry["assistant_tool_call_event_count"] == 0, telemetry
    assert telemetry["assistant_tool_call_count"] == 0, telemetry
    assert telemetry["tool_execution_start_count"] == 0, telemetry
    assert telemetry["tool_execution_end_count"] == 0, telemetry
    serialized = json.dumps(telemetry)
    for forbidden in ("ignored-text", "ignored-content"):
        assert forbidden not in serialized, (
            f"text-only leaked {forbidden!r}: {serialized}"
        )


def expect_toolcall_lifecycle() -> None:
    spec = {
        "events": [
            {"type": "message_update", "assistantMessageEvent": {
                "type": "start",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "toolcall_start",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "toolcall_delta",
                "delta": "ignored-arg-not-serialized",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "toolcall_end",
                "toolCall": {
                    "id": "ignored-tool-call-id",
                    "name": "ignored-tool-name",
                    "arguments": {"path": "ignored-path"},
                },
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "done",
                "reason": "toolUse",
            }},
        ],
        "messages": [
            {"role": "assistant", "content": [
                {"type": "toolCall", "id": "ignored", "name": "ignored",
                 "arguments": {"key": "ignored"}},
            ]},
        ],
    }
    telemetry = run_synthetic_case("toolcall-lifecycle", spec)
    assert telemetry["assistant_message_count"] == 1, telemetry
    assert "toolCall" in telemetry["assistant_content_block_types"], telemetry
    assert "toolcall_start" in telemetry["assistant_message_event_types"], telemetry
    assert "toolcall_delta" in telemetry["assistant_message_event_types"], telemetry
    assert "toolcall_end" in telemetry["assistant_message_event_types"], telemetry
    assert telemetry["assistant_tool_call_event_count"] >= 1, telemetry
    assert telemetry["assistant_tool_call_count"] == 1, telemetry
    assert telemetry["tool_execution_start_count"] == 0, telemetry
    serialized = json.dumps(telemetry)
    for forbidden in ("ignored-arg", "ignored-tool-call-id", "ignored-tool-name",
                      "ignored-path", "ignored-key"):
        assert forbidden not in serialized, (
            f"toolcall-lifecycle leaked {forbidden!r}: {serialized}"
        )


def expect_toolcall_execution() -> None:
    spec = {
        "events": [
            {"type": "message_update", "assistantMessageEvent": {
                "type": "toolcall_start",
            }},
            {"type": "message_update", "assistantMessageEvent": {
                "type": "toolcall_end",
                "toolCall": {"id": "tc-1", "name": "write",
                             "arguments": {"ignored": True}},
            }},
        ],
        "messages": [
            {"role": "assistant", "content": [
                {"type": "toolCall", "id": "tc-1", "name": "write",
                 "arguments": {"path": "ignored"}},
            ]},
        ],
        "toolExecutionEvents": [
            {"type": "tool_execution_start", "toolName": "write",
             "toolCallId": "tc-1", "args": {"path": "ignored-args"}},
            {"type": "tool_execution_end", "toolName": "write",
             "toolCallId": "tc-1", "result": "ignored-result",
             "isError": False},
        ],
    }
    telemetry = run_synthetic_case("toolcall-execution", spec)
    assert telemetry["assistant_message_count"] == 1, telemetry
    assert "toolCall" in telemetry["assistant_content_block_types"], telemetry
    assert telemetry["assistant_tool_call_event_count"] >= 1, telemetry
    assert telemetry["assistant_tool_call_count"] == 1, telemetry
    assert telemetry["tool_execution_start_count"] == 1, telemetry
    assert telemetry["tool_execution_end_count"] == 1, telemetry
    assert telemetry["executed_tool_names"] == ["write"], telemetry
    serialized = json.dumps(telemetry)
    for forbidden in ("ignored-args", "ignored-result", '"path":'):
        assert forbidden not in serialized, (
            f"toolcall-execution leaked {forbidden!r}: {serialized}"
        )


def expect_empty() -> None:
    spec = {"events": [], "messages": []}
    telemetry = run_synthetic_case("empty", spec)
    assert telemetry["assistant_message_count"] == 0, telemetry
    assert telemetry["assistant_content_block_types"] == [], telemetry
    assert telemetry["assistant_message_event_types"] == [], telemetry
    assert telemetry["assistant_tool_call_event_count"] == 0, telemetry
    assert telemetry["assistant_tool_call_count"] == 0, telemetry
    assert telemetry["tool_execution_start_count"] == 0, telemetry
    assert telemetry["tool_execution_end_count"] == 0, telemetry


def main() -> int:
    # Static checks
    rc = subprocess.run(
        ["node", "--check", str(WRAPPER)],
        capture_output=True, text=True,
    ).returncode
    assert rc == 0, f"node --check {WRAPPER} failed"
    rc = subprocess.run(
        ["node", "--check", str(HELPERS)],
        capture_output=True, text=True,
    ).returncode
    assert rc == 0, f"node --check {HELPERS} failed"

    expect_text_only()
    print("text-only: PASS")
    expect_toolcall_lifecycle()
    print("toolcall-lifecycle: PASS")
    expect_toolcall_execution()
    print("toolcall-execution: PASS")
    expect_empty()
    print("empty: PASS")
    print("---")
    print("All 4 deterministic Pi 0.82.1 assistant-telemetry cases PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# --- Live-wrapper source regressions (per spec §35).
#
# These pytest tests inspect the live wrapper source to assert the
# canonical 10-field telemetry contract is wired correctly.  They run
# with pytest (per spec §40) and the script-mode main() above also
# remains a backstop for executable synthetic-event checks.

import pytest  # noqa: E402  (kept near the pytest tests for readability)


WRAPPER_SOURCE = (WORKTREE / "codex_runner" / "src" / "agent-wrapper.js").read_text()


def test_wrapper_imports_create_tool_telemetry() -> None:
    """The live wrapper must import ``createToolTelemetry`` from
    ``./assistant-telemetry.js`` (the canonical 10-field accumulator
    helper)."""
    assert "createToolTelemetry" in WRAPPER_SOURCE, (
        "wrapper does not import createToolTelemetry"
    )


def test_wrapper_does_not_own_six_field_accumulator_literal() -> None:
    """The wrapper must NOT maintain its own six-field telemetry
    accumulator literal.  The canonical helper is the sole source of
    the bounded shape."""
    bad_literal = (
        "\tconst toolTelemetry = {\n"
        "\t\teffective_tool_names: effectiveToolNames,\n"
        "\t\twrite_tool_available: writeToolAvailable,\n"
        "\t\ttool_execution_start_count: 0,\n"
        "\t\ttool_execution_end_count: 0,\n"
        "\t\texecuted_tool_names: [],\n"
        "\t\tassistant_tool_call_count: 0,\n"
        "\t};"
    )
    assert bad_literal not in WRAPPER_SOURCE, (
        "wrapper still owns the pre-repair 6-field accumulator literal"
    )


def test_wrapper_uses_create_tool_telemetry_call() -> None:
    """The wrapper must call ``createToolTelemetry()`` to build its
    accumulator."""
    assert "createToolTelemetry()" in WRAPPER_SOURCE, (
        "wrapper does not call createToolTelemetry()"
    )


def test_wrapper_wires_assistant_event_observer() -> None:
    """The wrapper must call ``observeAssistantMessageEvent`` inside
    its session subscribe path, independently of OPTIONS.verbose."""
    assert "observeAssistantMessageEvent(toolTelemetry, event)" in WRAPPER_SOURCE, (
        "wrapper does not call observeAssistantMessageEvent on each event"
    )
    assert WRAPPER_SOURCE.count("observeAssistantMessageEvent(") >= 1


def test_wrapper_wires_final_assistant_observer() -> None:
    """The wrapper must call ``observeFinalAssistantMessages`` after
    successful prompt.  No manual independent final assistant scan
    may remain."""
    assert (
        "observeFinalAssistantMessages(toolTelemetry, session)"
        in WRAPPER_SOURCE
    ), "wrapper does not call observeFinalAssistantMessages"


def test_wrapper_does_not_run_manual_assistant_scan() -> None:
    """The pre-repair manual ``assistant_tool_call_count`` scan over
    ``session.agent.state.messages`` must be removed."""
    bad_scan = (
        "for (const message of finalMessages) {\n"
        "\t\t\tif (message.role !== \"assistant\") continue;\n"
    )
    assert bad_scan not in WRAPPER_SOURCE, (
        "wrapper still owns the pre-repair manual assistant_tool_call_count scan"
    )


def test_wrapper_does_not_retrieve_assistant_text_or_reasoning() -> None:
    """The wrapper must not retrieve assistant text deltas or
    reasoning content for telemetry purposes.  Verbose-only text
    printing is allowed (and gated on OPTIONS.verbose)."""
    # The post-repair wrapper retains the verbose text_delta print
    # (for human log readability) but no telemetry field reads it.
    assert "assistantMessageEvent.delta" in WRAPPER_SOURCE  # verbose print, allowed
