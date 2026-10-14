"""Exact durable terminal authority at worker entry and late error boundaries."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from guardian.core.db import ChatAttemptReconciliation
from guardian.core import chat_postgres_deadline as pg
from guardian.core import chat_redis_deadline as redis
from guardian.tasks.chat_deadline import (
    build_accepted_chat_task_deadline,
    DEADLINE_FIELDS,
)
from guardian.workers import chat_worker as worker
from tests.workers.test_chat_worker_streaming_chunks import (
    _build_task,
    _prepare_worker_harness,
)


@pytest.fixture
def packet(monkeypatch):
    task = _build_task(task_id="terminal-task")
    task.request_id = "terminal-request"
    deadline = build_accepted_chat_task_deadline(datetime.now(timezone.utc))
    for key, value in deadline.to_dict().items():
        setattr(task, key, value)
    row = dict(
        backend_task_id=task.task_id,
        request_id=task.request_id,
        thread_id=task.thread_id,
        turn_id=task.turn_id,
        completed_message_id=None,
        terminal_event_type=None,
        terminal_outcome=None,
        deadline_snapshot=deadline.to_dict(),
    )
    events = []
    monkeypatch.setattr(
        worker, "get_chat_completion_attempt_by_task_id", lambda *_: dict(row)
    )
    monkeypatch.setattr(
        worker,
        "_safe_publish",
        lambda _, kind, data: events.append((kind, data)) or {"ok": True},
    )
    monkeypatch.setattr(
        worker,
        "observe_chat_completion_attempt_terminal",
        lambda *_, **__: ChatAttemptReconciliation(
            row["completed_message_id"],
            row["terminal_event_type"],
            row["terminal_outcome"],
            None,
        ),
    )
    body = Mock()
    monkeypatch.setattr(worker, "_run_chat_task_with_query_budget", body)
    return task, row, events, body


@pytest.mark.parametrize(
    "terminal", ["completion", "task.cancelled", "task.failed", "orphan"]
)
def test_existing_terminal_wins_without_execution(packet, terminal):
    task, row, events, body = packet
    if terminal == "completion":
        row["completed_message_id"] = 42
    else:
        row["terminal_event_type"] = "task.failed" if terminal == "orphan" else terminal
    if terminal == "orphan":
        row["terminal_outcome"] = {
            "failure_code": "CHAT_ACCEPTED_TASK_ORPHANED",
            "reconciled_at": "2026-10-04T00:00:00+00:00",
        }
    # Even an expired or malformed packet cannot override already durable truth.
    task.work_deadline_at = "invalid"
    worker._run_chat_task(task)
    body.assert_not_called()
    assert len(events) == 1
    kind, payload = events[0]
    assert kind == (
        "task.completed" if terminal == "completion" else row["terminal_event_type"]
    )
    assert (
        payload["request_id"] == task.request_id and payload["turn_id"] == task.turn_id
    )
    assert "completion_truth" not in payload and "provider" not in payload
    if terminal == "orphan":
        assert payload["terminal_outcome"] == row["terminal_outcome"]
        assert payload["failure_code"] == "CHAT_ACCEPTED_TASK_ORPHANED"
    assert pg._budget.get() is None and redis._budget.get() is None


@pytest.mark.parametrize(
    "field", ["backend_task_id", "request_id", "thread_id", "turn_id"]
)
def test_identity_mismatch_never_executes(packet, field):
    task, row, events, body = packet
    row[field] = "other"
    worker._run_chat_task(task)
    body.assert_not_called()
    assert events == []


@pytest.mark.parametrize(
    "mutation", ["missing", "invalid", "shifted", "durable-invalid"]
)
def test_original_snapshot_cannot_be_repaired(packet, mutation):
    task, row, events, body = packet
    if mutation == "missing":
        for key in DEADLINE_FIELDS:
            setattr(task, key, None)
    elif mutation == "invalid":
        task.work_deadline_at = "invalid"
    elif mutation == "shifted":
        changed = build_accepted_chat_task_deadline(
            datetime.now(timezone.utc) + timedelta(seconds=10)
        )
        for key, value in changed.to_dict().items():
            setattr(task, key, value)
    else:
        row["deadline_snapshot"] = {}
    worker._run_chat_task(task)
    body.assert_not_called()
    assert events == []


def test_missing_or_uncertain_attempt_never_executes(packet, monkeypatch):
    task, _, events, body = packet
    for read in (
        Mock(return_value=None),
        Mock(side_effect=RuntimeError("injected uncertainty")),
    ):
        monkeypatch.setattr(worker, "get_chat_completion_attempt_by_task_id", read)
        worker._run_chat_task(task)
    body.assert_not_called()
    assert events == []


def test_preparation_consumes_original_budget_and_maintenance_grants_no_work(
    packet, monkeypatch
):
    task, row, _, body = packet
    observed = []
    elapsed = [0]
    accepted = datetime.fromisoformat(task.accepted_at)

    class Clock:
        @classmethod
        def now(cls, zone=None):
            return accepted + timedelta(seconds=elapsed[0])

    monkeypatch.setattr(worker, "datetime", Clock)

    def read(*_):
        assert pg._budget.get().operation
        with pytest.raises(ValueError):
            pg.require_accepted_work_budget()
        observed.append(True)
        elapsed[0] = 3
        return dict(row)

    def run(_):
        assert not pg._budget.get().operation
        assert 716 < pg.require_accepted_work_budget() <= 717
        assert {name: getattr(task, name) for name in DEADLINE_FIELDS} == row[
            "deadline_snapshot"
        ]

    monkeypatch.setattr(worker, "get_chat_completion_attempt_by_task_id", read)
    body.side_effect = run
    worker._run_chat_task(task)
    body.assert_called_once_with(task)
    assert len(observed) == 1
    assert pg._budget.get() is None and redis._budget.get() is None


def test_orphan_after_task_scope_is_observation_only(packet):
    task, row, events, body = packet

    def run(_):
        assert not pg._budget.get().operation
        row["terminal_event_type"] = "task.failed"
        row["terminal_outcome"] = {
            "failure_code": "CHAT_ACCEPTED_TASK_ORPHANED",
            "reconciled_at": "2026-10-04T00:00:00+00:00",
        }

    body.side_effect = run
    worker._run_chat_task(task)
    assert (
        len(events) == 1 and events[0][1]["terminal_outcome"] == row["terminal_outcome"]
    )
    assert "completion_truth" not in events[0][1]


@pytest.mark.parametrize("cause", ["early-cancel", "cancel", "error"])
@pytest.mark.parametrize(
    "durable", ["unknown", "orphan", "completion", "task.cancelled"]
)
def test_rejected_terminal_write_cannot_publish_alternate(monkeypatch, cause, durable):
    events = _prepare_worker_harness(monkeypatch, provider="local", model="test-model")
    task = _build_task(task_id="terminal-rejected")
    task.request_id = "terminal-rejected-request"
    row = dict(
        backend_task_id=task.task_id,
        request_id=task.request_id,
        thread_id=task.thread_id,
        turn_id=task.turn_id,
        completed_message_id=42 if durable == "completion" else None,
        terminal_event_type="task.failed"
        if durable == "orphan"
        else (durable if durable == "task.cancelled" else None),
        terminal_outcome={
            "failure_code": "CHAT_ACCEPTED_TASK_ORPHANED",
            "reconciled_at": "2026-10-04T00:00:00+00:00",
        }
        if durable == "orphan"
        else None,
    )
    monkeypatch.setattr(
        worker, "get_chat_completion_attempt_by_task_id", lambda *_: row
    )
    monkeypatch.setattr(
        worker,
        "observe_chat_completion_attempt_terminal",
        lambda *_, **__: ChatAttemptReconciliation(
            row["completed_message_id"],
            row["terminal_event_type"],
            row["terminal_outcome"],
            None,
        ),
    )
    monkeypatch.setattr(
        worker, "_record_chat_completion_attempt_terminal", lambda *_: False
    )
    monkeypatch.setattr(worker, "is_cancelled", lambda *_: cause == "early-cancel")

    async def rejected(_):
        if cause == "cancel":
            raise worker.ChatTaskCancelled("injected cancellation")
        raise ValueError("injected failure")

    monkeypatch.setattr(worker, "_build_messages_for_llm", rejected)
    worker._run_chat_task_with_query_budget(task)
    terminal_events = [
        (kind, payload)
        for kind, payload in events
        if kind in {"task.failed", "task.cancelled", "task.completed"}
    ]
    if durable == "unknown":
        assert terminal_events == []
    else:
        assert len(terminal_events) == 1
        assert terminal_events[0][0] == (
            "task.completed" if durable == "completion" else row["terminal_event_type"]
        )
        assert "error_type" not in terminal_events[0][1]
        if durable == "orphan":
            assert (
                terminal_events[0][1]["failure_code"] == "CHAT_ACCEPTED_TASK_ORPHANED"
            )
            assert "completion_truth" not in terminal_events[0][1]


def test_normal_completion_is_not_published_again_after_scopes(packet):
    task, row, events, body = packet

    def run(_):
        row["completed_message_id"] = 42
        events.append(("task.completed", {"message_id": 42}))

    body.side_effect = run
    worker._run_chat_task(task)
    assert events == [("task.completed", {"message_id": 42})]


def test_observed_projection_owns_resource_scopes_but_no_execution_authority(
    packet, monkeypatch
):
    task, row, _, body = packet
    row["terminal_event_type"] = "task.cancelled"
    seen = []

    def unavailable_visibility(_, kind, payload):
        assert pg._budget.get().operation and redis._budget.get().operation
        with pytest.raises(ValueError):
            pg.require_accepted_work_budget()
        assert kind == "task.cancelled"
        assert "run_id" not in payload and "duration_ms" not in payload
        seen.append(payload)
        return {"ok": False}

    monkeypatch.setattr(worker, "_safe_publish", unavailable_visibility)
    worker._run_chat_task(task)
    body.assert_not_called()
    assert len(seen) == 1
    assert pg._budget.get() is None and redis._budget.get() is None
