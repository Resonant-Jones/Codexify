"""Worker lifecycle proof for immutable accepted deadlines during rescue."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from guardian.protocol_tokens import ErrorCode
from guardian.tasks.chat_deadline import (
    AcceptedChatTaskDeadlineExceeded,
    build_accepted_chat_task_deadline,
)
from guardian.tasks.types import TaskLifecycleState
from guardian.workers import chat_worker
from tests.workers.test_chat_worker_streaming_chunks import (
    _build_task,
    _prepare_worker_harness,
)


def provider_error():
    return HTTPException(status_code=502, detail={"failure_kind": "http_error"})


def deadline_error(serialized=False):
    error = AcceptedChatTaskDeadlineExceeded(attempted=True)
    return (
        HTTPException(status_code=504, detail=dict(error.detail))
        if serialized
        else error
    )


@pytest.fixture
def worker(monkeypatch):
    events = _prepare_worker_harness(
        monkeypatch, provider="groq", model="cloud-model", stream_tokens=["rescued"]
    )
    now = datetime.now(timezone.utc)
    clock = {"now": now}

    class Clock:
        @classmethod
        def now(cls, zone=None):
            return clock["now"] if zone is None else clock["now"].astimezone(zone)

    monkeypatch.setattr(chat_worker, "datetime", Clock)
    monkeypatch.setattr(chat_worker._chat_completion_service, "datetime", Clock)
    monkeypatch.setattr(
        chat_worker, "schedule_post_completion_eval", lambda *args, **kwargs: None
    )
    task = _build_task(
        task_id="fixture-rescue-deadline", provider="groq", model="cloud-model"
    )
    task.selection_source = "default"
    task.provider_pinned = False
    task.latest_turn_message_id = 51
    snapshot = build_accepted_chat_task_deadline(now - timedelta(seconds=719)).to_dict()
    for key, value in snapshot.items():
        setattr(task, key, value)
    state = {
        "task": task,
        "snapshot": snapshot,
        "clock": clock,
        "expiry": now + timedelta(seconds=1),
        "events": events,
        "calls": [],
        "persisted": [],
    }
    release = Mock(return_value=True)
    monkeypatch.setattr(chat_worker, "release_turn_lock", release)
    state["release"] = release
    monkeypatch.setattr(
        chat_worker.dependencies,
        "chatlog_db",
        SimpleNamespace(
            create_message=lambda thread_id, role, text: state["persisted"].append(text)
            or 42,
            write_audit_log=lambda *args, **kwargs: None,
        ),
    )
    candidate = Mock(return_value=[("local", "test-model")])
    state["candidates"] = candidate
    monkeypatch.setattr(chat_worker, "_fallback_provider_candidates", candidate)
    return state


def install_first_failure(monkeypatch, state, error, *, expires=False):
    def fail(*args, **kwargs):
        state["calls"].append(kwargs["provider"])
        if expires:
            state["clock"]["now"] = state["expiry"]
        raise error

    monkeypatch.setattr(chat_worker, "chat_with_ai", fail)
    monkeypatch.setattr(chat_worker._chat_completion_service, "chat_with_ai", fail)


def assert_deadline_failure(state, *, fallback_attempted):
    task = state["task"]
    failed = [payload for event, payload in state["events"] if event == "task.failed"]
    assert len(failed) == 1
    payload = failed[0]
    assert (
        payload["failure_code"] == ErrorCode.CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED.value
    )
    assert payload["completion_truth"] == {
        "accepted": True,
        "attempted": True,
        "fallback_attempted": fallback_attempted,
        "executed": False,
        "completed": False,
    }
    assert payload["task_id"] == task.task_id
    assert payload["request_id"] == task.request_id
    assert payload["thread_id"] == task.thread_id
    assert payload["latest_turn_message_id"] == 51
    assert payload["turn_id"] == task.turn_id
    assert payload["request_correlation"]["request_id"] == task.request_id
    assert payload["request_correlation"]["task_id"] == task.task_id
    assert payload["request_correlation"]["attempt_id"] == task.attempt_id
    assert "runtime_status" not in payload
    assert state["persisted"] == []
    assert not any(
        event in {"task.completed", "task.cancelled"} for event, _ in state["events"]
    )
    state["release"].assert_called_once_with(task.thread_id, task.turn_lock_owner)
    assert {key: getattr(task, key) for key in state["snapshot"]} == state["snapshot"]
    return payload


@pytest.mark.parametrize("serialized", [False, True])
def test_canonical_deadline_failure_never_discovers_or_starts_rescue(
    worker, monkeypatch, serialized
):
    install_first_failure(monkeypatch, worker, deadline_error(serialized), expires=True)
    chat_worker._run_chat_task(worker["task"])
    worker["candidates"].assert_not_called()
    assert worker["calls"] == ["groq"]
    assert_deadline_failure(worker, fallback_attempted=False)


def test_provider_failure_after_budget_expires_becomes_deadline_truth(
    worker, monkeypatch
):
    install_first_failure(monkeypatch, worker, provider_error(), expires=True)
    chat_worker._run_chat_task(worker["task"])
    worker["candidates"].assert_not_called()
    assert worker["calls"] == ["groq"]
    assert_deadline_failure(worker, fallback_attempted=False)


@pytest.mark.parametrize("has_candidate", [False, True])
def test_candidate_discovery_cannot_mint_a_new_work_budget(
    worker, monkeypatch, has_candidate
):
    install_first_failure(monkeypatch, worker, provider_error())

    def discover(**kwargs):
        worker["clock"]["now"] = worker["expiry"]
        return [("local", "test-model")] if has_candidate else []

    worker["candidates"].side_effect = discover
    chat_worker._run_chat_task(worker["task"])
    worker["candidates"].assert_called_once()
    assert worker["calls"] == ["groq"]
    assert_deadline_failure(worker, fallback_attempted=False)


@pytest.mark.parametrize("serialized", [False, True])
def test_deadline_during_rescue_wins_over_the_earlier_provider_error(
    worker, monkeypatch, serialized
):
    install_first_failure(monkeypatch, worker, provider_error())

    def local_fails(*args, **kwargs):
        worker["calls"].append("local")
        worker["clock"]["now"] = worker["expiry"]
        raise deadline_error(serialized)

    monkeypatch.setattr(
        chat_worker._chat_completion_service, "stream_local", local_fails
    )
    chat_worker._run_chat_task(worker["task"])
    assert worker["calls"] == ["groq", "local"]
    payload = assert_deadline_failure(worker, fallback_attempted=True)
    assert payload["resolved_provider"] == "local"
    assert payload["resolved_model"] == "test-model"


@pytest.mark.parametrize("has_next_candidate", [False, True])
def test_expiry_after_first_rescue_failure_prevents_the_next_candidate(
    worker, monkeypatch, has_next_candidate
):
    install_first_failure(monkeypatch, worker, provider_error())
    worker["candidates"].return_value = [("local", "test-model")]
    if has_next_candidate:
        worker["candidates"].return_value.append(("deepseek", "other-model"))

    def local_fails(*args, **kwargs):
        worker["calls"].append("local")
        worker["clock"]["now"] = worker["expiry"]
        raise provider_error()

    monkeypatch.setattr(
        chat_worker._chat_completion_service, "stream_local", local_fails
    )
    chat_worker._run_chat_task(worker["task"])
    assert worker["calls"] == ["groq", "local"]
    payload = assert_deadline_failure(worker, fallback_attempted=True)
    assert payload["resolved_provider"] == "local"
    assert payload["resolved_model"] == "test-model"


@pytest.mark.parametrize("legacy", [False, True])
def test_permitted_rescue_before_deadline_and_legacy_rescue_keep_success(
    worker, monkeypatch, legacy
):
    if legacy:
        for key in worker["snapshot"]:
            setattr(worker["task"], key, None)
    install_first_failure(monkeypatch, worker, provider_error())
    chat_worker._run_chat_task(worker["task"])
    assert worker["persisted"] == ["rescued"]
    completed = [
        payload for event, payload in worker["events"] if event == "task.completed"
    ]
    assert len(completed) == 1
    assert completed[0]["completion_truth"]["completed"] is True
    assert completed[0]["completion_truth"]["fallback_attempted"] is True
    assert not any(event == "task.failed" for event, _ in worker["events"])
    worker["release"].assert_called_once_with(
        worker["task"].thread_id, worker["task"].turn_lock_owner
    )
    if not legacy:
        assert {
            key: getattr(worker["task"], key) for key in worker["snapshot"]
        } == worker["snapshot"]


def test_partial_rescue_output_cannot_hide_authoritative_deadline_failure(
    worker, monkeypatch
):
    install_first_failure(monkeypatch, worker, provider_error())
    worker["candidates"].return_value = [
        ("local", "test-model"),
        ("deepseek", "other-model"),
    ]

    def partial_then_deadline(*args, **kwargs):
        worker["calls"].append("local")
        yield "partial"
        worker["clock"]["now"] = worker["expiry"]
        raise deadline_error()

    monkeypatch.setattr(
        chat_worker._chat_completion_service, "stream_local", partial_then_deadline
    )
    chat_worker._run_chat_task(worker["task"])
    assert worker["calls"] == ["groq", "local"]
    payload = assert_deadline_failure(worker, fallback_attempted=True)
    assert payload["visible_output_emitted"] is True
    assert payload["first_output_observed"] is True
    assert payload["failed_after_state"] == TaskLifecycleState.STREAMING.value
    assert payload["resolved_provider"] == "local"
    assert payload["resolved_model"] == "test-model"
    assert any(event == "task.chunk" for event, _ in worker["events"])
