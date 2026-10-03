"""Immutable accepted-deadline admission and error truth at the tool seam."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from guardian.core import chat_completion_service as service
from guardian.protocol_tokens import ErrorCode
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    build_accepted_chat_task_deadline,
)
from tests.providers.test_tool_turn_transport_convergence import (
    CANONICAL_ARGUMENTS,
    CANONICAL_COMMAND_ID,
    MOCKED_COMMAND_RESULT,
    _build_task,
    _canonical_tool_spec,
    _seed_service,
    _whooshd_stage_2e_response,
)


@pytest.fixture
def loop(monkeypatch):
    model = "gemma-4-12b-it-qat-4bit"
    _seed_service(monkeypatch, provider="local", model=model)
    task = _build_task(
        task_id="fixture-tool-admission-deadline",
        provider="local",
        model=model,
        tools=[_canonical_tool_spec()],
    )
    now = datetime.now(timezone.utc)
    clock = {"now": now}
    snapshot = build_accepted_chat_task_deadline(now - timedelta(seconds=719)).to_dict()
    for key, value in snapshot.items():
        setattr(task, key, value)

    class Clock:
        @classmethod
        def now(cls, zone=None):
            return clock["now"] if zone is None else clock["now"].astimezone(zone)

    monkeypatch.setattr(service, "datetime", Clock)
    outputs = [
        _whooshd_stage_2e_response(
            kind="tool_decision",
            text=None,
            command_id=CANONICAL_COMMAND_ID,
            arguments=CANONICAL_ARGUMENTS,
        ),
        _whooshd_stage_2e_response(
            kind="assistant", text="done", command_id=None, arguments={}
        ),
    ]
    provider = Mock(side_effect=outputs)
    invoke = Mock(return_value=dict(MOCKED_COMMAND_RESULT))
    monkeypatch.setattr(service, "chat_with_ai", provider)
    monkeypatch.setattr(service, "execute_invoke", invoke)
    state = {
        "task": task,
        "clock": clock,
        "expiry": now + timedelta(seconds=1),
        "snapshot": snapshot,
        "provider": provider,
        "invoke": invoke,
    }
    return state


def run(loop):
    return service.run_chat_completion_task(
        loop["task"], persist_assistant_message=False
    )


def assert_deadline(loop, *, invoke_count):
    with pytest.raises(HTTPException) as caught:
        run(loop)
    assert caught.value.detail["failure_code"] == (
        ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert caught.value.detail["completion_truth"]["attempted"] is True
    assert caught.value.detail["completion_truth"]["completed"] is False
    assert loop["provider"].call_count == 1
    assert loop["invoke"].call_count == invoke_count
    assert {key: getattr(loop["task"], key) for key in loop["snapshot"]} == loop[
        "snapshot"
    ]
    return caught.value


def test_expiry_while_normalizing_decision_prevents_command_admission(
    loop, monkeypatch
):
    normalize = service.normalize_completion_output

    def normalize_then_expire(output):
        result = normalize(output)
        if result.kind == "tool_decision":
            loop["clock"]["now"] = loop["expiry"]
        return result

    monkeypatch.setattr(service, "normalize_completion_output", normalize_then_expire)
    assert_deadline(loop, invoke_count=0)


def test_expiry_during_argument_preparation_prevents_command_admission(
    loop, monkeypatch
):
    prepare = service._tool_turn_invoke_arguments

    def prepare_then_expire(arguments):
        result = prepare(arguments)
        loop["clock"]["now"] = loop["expiry"]
        return result

    monkeypatch.setattr(service, "_tool_turn_invoke_arguments", prepare_then_expire)
    assert_deadline(loop, invoke_count=0)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("serialized", [False, True])
def test_command_deadline_is_not_wrapped_as_a_tool_failure(
    loop, asynchronous, serialized
):
    original = AcceptedChatTaskDeadlineExceeded(attempted=True)
    if serialized:
        original = HTTPException(status_code=504, detail=dict(original.detail))

    def fail():
        raise original

    async def async_fail(**kwargs):
        fail()

    loop["invoke"].side_effect = async_fail if asynchronous else lambda **kwargs: fail()
    assert assert_deadline(loop, invoke_count=1) is original


@pytest.mark.parametrize("asynchronous", [False, True])
def test_expired_command_error_yields_parent_deadline(loop, asynchronous):
    def fail():
        loop["clock"]["now"] = loop["expiry"]
        raise RuntimeError("synthetic command failure")

    async def async_fail(**kwargs):
        fail()

    loop["invoke"].side_effect = async_fail if asynchronous else lambda **kwargs: fail()
    assert_deadline(loop, invoke_count=1)


@pytest.mark.parametrize("asynchronous", [False, True])
def test_command_success_after_expiry_cannot_start_followup_generation(
    loop, asynchronous
):
    def succeed():
        loop["clock"]["now"] = loop["expiry"]
        return dict(MOCKED_COMMAND_RESULT)

    async def async_succeed(**kwargs):
        return succeed()

    loop["invoke"].side_effect = (
        async_succeed if asynchronous else lambda **kwargs: succeed()
    )
    assert_deadline(loop, invoke_count=1)


@pytest.mark.parametrize("legacy", [False, True])
def test_in_budget_and_legacy_tool_continuation_still_succeed(loop, legacy):
    if legacy:
        for key in loop["snapshot"]:
            setattr(loop["task"], key, None)
    result = run(loop)
    assert result["assistant_text"] == "done"
    assert loop["invoke"].call_count == 1
    assert loop["provider"].call_count == 2
    payload = loop["invoke"].call_args.kwargs["payload"]
    assert payload.command_id == CANONICAL_COMMAND_ID
    assert loop["invoke"].call_args.kwargs["allow_write_execution"] is False
    assert loop["invoke"].call_args.kwargs["confirmation_granted"] is False
    if not legacy:
        assert {key: getattr(loop["task"], key) for key in loop["snapshot"]} == loop[
            "snapshot"
        ]


def test_command_error_before_deadline_keeps_existing_failure(loop):
    loop["invoke"].side_effect = RuntimeError("synthetic command failure")
    with pytest.raises(service.ToolLoopExecutionError) as caught:
        run(loop)
    assert str(caught.value) == "tool_command_execution_failed"
    assert loop["invoke"].call_count == 1
    assert loop["provider"].call_count == 1
