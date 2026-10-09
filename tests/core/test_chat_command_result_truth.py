"""Returned command failures must not become completed chat tool turns."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from guardian.core import chat_completion_service as service
from guardian.providers.deepseek_adapter import DeepSeekResponse
from guardian.tasks.chat_deadline import build_accepted_chat_task_deadline
from tests.providers.test_tool_turn_transport_convergence import (
    CANONICAL_ARGUMENTS,
    CANONICAL_COMMAND_ID,
    _build_task,
    _canonical_tool_spec,
    _deepseek_aliases,
    _deepseek_response,
    _seed_service,
    _whooshd_stage_2e_response,
)


@pytest.fixture(params=["local", "deepseek"])
def turn(request, monkeypatch):
    provider = request.param
    model = "gemma-4-12b-it-qat-4bit" if provider == "local" else "deepseek-v4-flash"
    _seed_service(monkeypatch, provider=provider, model=model)
    tools = [_canonical_tool_spec()]
    task = _build_task(
        task_id="fixture-command-result", provider=provider, model=model, tools=tools
    )
    snapshot = build_accepted_chat_task_deadline(datetime.now(timezone.utc)).to_dict()
    for key, value in snapshot.items():
        setattr(task, key, value)
    if provider == "local":
        first = _whooshd_stage_2e_response(
            kind="tool_decision",
            text=None,
            command_id=CANONICAL_COMMAND_ID,
            arguments=CANONICAL_ARGUMENTS,
        )
        final = _whooshd_stage_2e_response(
            kind="assistant",
            text="fixture final answer",
            command_id=None,
            arguments={},
        )
    else:
        _, aliases = _deepseek_aliases(tools)
        first, _ = _deepseek_response(
            alias_to_command=aliases,
            alias=next(iter(aliases)),
            arguments=CANONICAL_ARGUMENTS,
        )
        final = DeepSeekResponse(
            content="fixture final answer",
            reasoning_content=None,
            tool_calls=[],
            raw_assistant_message={
                "role": "assistant",
                "content": "fixture final answer",
            },
            raw_payload={},
        )
    generation = Mock(side_effect=[first, final])
    monkeypatch.setattr(service, "chat_with_ai", generation)
    return {"task": task, "snapshot": snapshot, "generation": generation}


def install_command(monkeypatch, status, asynchronous):
    result = {
        "run_id": "run-fixture-result",
        "status": status,
        "error": "fixture command outcome" if status != "completed" else None,
        "inline_result": {"ok": status == "completed"},
    }
    command = Mock(return_value=result)

    async def async_result(**kwargs):
        return result

    if asynchronous:
        command.side_effect = async_result
    monkeypatch.setattr(service, "execute_invoke", command)
    return command


@pytest.mark.parametrize("status", ["failed", "blocked"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_returned_command_failure_stops_before_final_answer(
    turn, monkeypatch, status, asynchronous
):
    command = install_command(monkeypatch, status, asynchronous)
    with pytest.raises(service.ToolLoopExecutionError) as caught:
        service.run_chat_completion_task(turn["task"], persist_assistant_message=False)
    metadata = caught.value.metadata
    assert metadata["toolTurnState"] == "failed"
    assert metadata["loopStopReason"] == (
        "tool_command_blocked" if status == "blocked" else "tool_command_failed"
    )
    assert metadata["commandRunId"] == "run-fixture-result"
    assert metadata["command_status"] == status
    assert metadata["command_error"]["error"] == "fixture command outcome"
    assert metadata["requestId"] == turn["task"].request_id
    assert metadata["messageId"] == turn["task"].latest_turn_message_id
    assert metadata["toolTurnId"]
    assert turn["generation"].call_count == command.call_count == 1
    assert command.call_args.kwargs["allow_write_execution"] is False
    assert command.call_args.kwargs["confirmation_granted"] is False
    assert {key: getattr(turn["task"], key) for key in turn["snapshot"]} == turn[
        "snapshot"
    ]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_completed_command_keeps_bounded_continuation(turn, monkeypatch, asynchronous):
    command = install_command(monkeypatch, "completed", asynchronous)
    result = service.run_chat_completion_task(
        turn["task"], persist_assistant_message=False
    )
    assert result["assistant_text"] == "fixture final answer"
    assert result["toolTurnState"] == "completed"
    assert result["loopStopReason"] == "tool_turn_completed"
    assert result["commandRunId"] == "run-fixture-result"
    assert turn["generation"].call_count == 2 and command.call_count == 1


def test_returned_command_diagnostic_is_bounded_and_credential_scrubbed(
    turn, monkeypatch
):
    command = install_command(monkeypatch, "failed", False)
    command.return_value["error"] = "Authorization: Bearer fixture-secret " + "x" * 2048
    with pytest.raises(service.ToolLoopExecutionError) as caught:
        service.run_chat_completion_task(turn["task"], persist_assistant_message=False)
    error = caught.value.metadata["command_error"]["error"]
    assert "fixture-secret" not in error
    assert len(error) <= 1024
    assert turn["generation"].call_count == 1
