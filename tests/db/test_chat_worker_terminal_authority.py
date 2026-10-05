"""Native persisted orphan fencing at worker observation boundaries."""

from unittest.mock import Mock

import pytest
from sqlalchemy import text

from guardian.core import chat_postgres_deadline as bounds
from guardian.core.db import (
    get_chat_completion_attempt_by_task_id,
    reconcile_chat_completion_attempt_after_deadline,
    record_chat_completion_attempt_terminal_event,
)
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker as worker
from tests.db.test_chat_completion_attempt_migration import (
    disposable_database as _disposable_database_fixture,
    recovery_database as _recovery_database_fixture,
)

disposable_database = _disposable_database_fixture
recovery_database = _recovery_database_fixture


def packet(identity, deadline):
    task = ChatCompletionTask(
        user_id="recovery-account",
        task_id=identity["backend_task_id"],
        request_id=identity["request_id"],
        thread_id=identity["thread_id"],
    )
    task.turn_id = identity["turn_id"]
    for key, value in deadline.to_dict().items():
        setattr(task, key, value)
    return task


@pytest.mark.integration
@pytest.mark.parametrize("boundary", ["preflight", "after-scopes"])
def test_native_orphan_projection_never_recasts_crash_or_changes_rows(
    recovery_database, monkeypatch, boundary
):
    _, engine, repo, deadline, create = recovery_database
    identity = create("worker-" + boundary)
    task = packet(identity, deadline)
    monkeypatch.setattr(worker.dependencies, "chatlog_db", repo)
    events = []
    monkeypatch.setattr(
        worker,
        "_safe_publish",
        lambda _, kind, data: events.append((kind, dict(data))) or {"ok": False},
    )
    provider = Mock(side_effect=AssertionError("orphan observation invoked generation"))
    monkeypatch.setattr(worker, "chat_with_ai", provider)
    enqueue = Mock(side_effect=AssertionError("orphan observation replayed task"))
    monkeypatch.setattr(worker._chat_completion_service, "enqueue", enqueue)

    def reconcile():
        return reconcile_chat_completion_attempt_after_deadline(
            repo,
            **identity,
            now=deadline.terminal_deadline_at,
        )

    body = Mock(side_effect=AssertionError("already orphaned task executed"))
    if boundary == "preflight":
        reconcile()
    else:

        def late_body(_):
            assert not bounds._budget.get().operation
            # Simulate another bounded controller committing terminal truth
            # while this worker still carries its original task scope.
            with engine.begin() as connection:
                from sqlalchemy.dialects.postgresql import JSONB
                from sqlalchemy import bindparam

                outcome = {
                    "failure_code": "CHAT_ACCEPTED_TASK_ORPHANED",
                    "reconciled_at": deadline.terminal_deadline_at.isoformat(),
                }
                connection.execute(
                    text(
                        "UPDATE chat_completion_attempts SET terminal_event_type='task.failed', terminal_outcome=:outcome WHERE backend_task_id=:task"
                    ).bindparams(bindparam("outcome", type_=JSONB)),
                    {"outcome": outcome, "task": task.task_id},
                )

        body = Mock(side_effect=late_body)
    monkeypatch.setattr(worker, "_run_chat_task_with_query_budget", body)
    worker._run_chat_task(task)
    after = get_chat_completion_attempt_by_task_id(repo, task.task_id)
    assert after["completed_message_id"] is None
    assert after["deadline_snapshot"] == deadline.to_dict()
    assert after["terminal_outcome"] == {
        "failure_code": "CHAT_ACCEPTED_TASK_ORPHANED",
        "reconciled_at": deadline.terminal_deadline_at.isoformat(),
    }
    assert len(events) == 1 and events[0][0] == "task.failed"
    assert events[0][1]["terminal_outcome"] == after["terminal_outcome"]
    assert events[0][1]["failure_code"] == "CHAT_ACCEPTED_TASK_ORPHANED"
    assert all(
        key not in events[0][1]
        for key in (
            "completion_truth",
            "attempted_provider",
            "error_type",
            "provider_request_started",
        )
    )
    assert not record_chat_completion_attempt_terminal_event(
        repo, **identity, event_type="task.failed"
    )
    assert get_chat_completion_attempt_by_task_id(repo, task.task_id) == after
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM chat_messages WHERE thread_id=:thread"),
                {"thread": task.thread_id},
            ).scalar_one()
            == 0
        )
    provider.assert_not_called()
    enqueue.assert_not_called()
    if boundary == "preflight":
        body.assert_not_called()
    assert bounds._budget.get() is None


@pytest.mark.integration
def test_native_pending_packet_cannot_extend_original_deadline(
    recovery_database, monkeypatch
):
    _, _, repo, deadline, create = recovery_database
    identity = create("worker-mismatch")
    task = packet(identity, deadline)
    task.accepted_at = None
    monkeypatch.setattr(worker.dependencies, "chatlog_db", repo)
    body = Mock()
    publish = Mock()
    monkeypatch.setattr(worker, "_run_chat_task_with_query_budget", body)
    monkeypatch.setattr(worker, "_safe_publish", publish)
    before = get_chat_completion_attempt_by_task_id(repo, task.task_id)
    worker._run_chat_task(task)
    assert get_chat_completion_attempt_by_task_id(repo, task.task_id) == before
    body.assert_not_called()
    publish.assert_not_called()


@pytest.mark.integration
def test_native_lagging_worker_rejected_failure_projects_orphan(
    recovery_database, monkeypatch
):
    """Injected lag permits entry; durable fencing remains authoritative."""
    from datetime import timedelta
    from tests.workers.test_chat_worker_streaming_chunks import _prepare_worker_harness

    _, engine, repo, deadline, create = recovery_database
    identity = create("worker-lag")
    task = packet(identity, deadline)
    observe = worker._read_attempt_for_worker
    record = worker._record_chat_completion_attempt_terminal
    events = _prepare_worker_harness(monkeypatch, provider="local", model="test-model")
    monkeypatch.setattr(worker, "_read_attempt_for_worker", observe)
    monkeypatch.setattr(worker, "_record_chat_completion_attempt_terminal", record)
    monkeypatch.setattr(worker.dependencies, "chatlog_db", repo)

    class Clock:
        @classmethod
        def now(cls, zone=None):
            return deadline.accepted_at + timedelta(seconds=1)

    monkeypatch.setattr(worker, "datetime", Clock)
    invoked = []

    def late_completion(*_, **__):
        invoked.append(True)
        # Other actor's durable transaction is injected here. This is native
        # database/worker arbitration evidence, not a real clock-skew runtime.
        from sqlalchemy import bindparam
        from sqlalchemy.dialects.postgresql import JSONB

        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE chat_completion_attempts SET terminal_event_type='task.failed', terminal_outcome=:outcome WHERE backend_task_id=:task"
                ).bindparams(bindparam("outcome", type_=JSONB)),
                {
                    "outcome": {
                        "failure_code": "CHAT_ACCEPTED_TASK_ORPHANED",
                        "reconciled_at": deadline.terminal_deadline_at.isoformat(),
                    },
                    "task": task.task_id,
                },
            )
        raise RuntimeError("injected late worker exception")

    monkeypatch.setattr(worker, "run_chat_completion_task", late_completion)
    worker._run_chat_task(task)
    assert invoked == [True]
    terminals = [
        (kind, payload)
        for kind, payload in events
        if kind in {"task.failed", "task.completed", "task.cancelled"}
    ]
    assert terminals and all(kind == "task.failed" for kind, _ in terminals)
    assert all(
        payload.get("failure_code") == "CHAT_ACCEPTED_TASK_ORPHANED"
        for _, payload in terminals
    )
    assert all(
        "completion_truth" not in payload and "error_type" not in payload
        for _, payload in terminals
    )
    after = get_chat_completion_attempt_by_task_id(repo, task.task_id)
    assert after["deadline_snapshot"] == deadline.to_dict()
    assert after["completed_message_id"] is None
    assert not record_chat_completion_attempt_terminal_event(
        repo, **identity, event_type="task.cancelled"
    )
    assert get_chat_completion_attempt_by_task_id(repo, task.task_id) == after
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM chat_messages WHERE thread_id=:thread"),
                {"thread": task.thread_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.integration
def test_native_observed_terminal_bounds_live_outbox_and_preserves_truth(
    recovery_database, monkeypatch
):
    import time

    _, engine, repo, deadline, create = recovery_database
    identity = create("worker-outbox")
    task = packet(identity, deadline)
    reconcile_chat_completion_attempt_after_deadline(
        repo, **identity, now=deadline.terminal_deadline_at
    )
    before = get_chat_completion_attempt_by_task_id(repo, task.task_id)
    repo.ensure_event_outbox()
    monkeypatch.setattr(worker.event_bus, "_store", repo)
    monkeypatch.setattr(worker.event_bus, "_subscribers", [])
    monkeypatch.setattr(
        worker.task_events, "publish_with_visibility", lambda *_: {"ok": True}
    )
    with engine.begin() as held:
        held.execute(text("LOCK TABLE events_outbox IN ACCESS EXCLUSIVE MODE"))
        started = time.monotonic()
        assert worker._project_observed_terminal(task, before)
        elapsed = time.monotonic() - started
        # The lock is still held. Failed live visibility cannot replace the
        # acknowledged durable orphan or leave an insert to execute later.
        assert 1.8 < elapsed < 2.5
    assert get_chat_completion_attempt_by_task_id(repo, task.task_id) == before
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM events_outbox")).scalar_one()
            == 0
        )
    assert bounds._budget.get() is None
