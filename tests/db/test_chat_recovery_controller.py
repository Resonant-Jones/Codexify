"""Native durable recovery controller arbitration and receipt readback."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import text

from guardian.core import chat_completion_service as service
from guardian.core.db import get_chat_completion_attempt_by_task_id
from guardian.queue.turn_lock import build_turn_lock_envelope
from guardian.routes import chat
from tests.db.test_chat_completion_attempt_migration import (
    disposable_database as _disposable_database_fixture,
    recovery_database as _recovery_database_fixture,
)

disposable_database = _disposable_database_fixture
recovery_database = _recovery_database_fixture


def route(monkeypatch, repo, thread):
    monkeypatch.setattr(chat, "chatlog_db", repo)
    # Account-scope-before-mutation is proven separately by route unit tests.
    monkeypatch.setattr(chat, "_require_thread_account_scope", lambda *a, **kw: None)
    monkeypatch.setattr(chat.task_events, "describe_terminal_state_in_scope", lambda *_: {
        "state": "unknown", "event_type": None, "reason": "task_events_missing",
    })
    return lambda: chat.chat_list_tasks(thread, api_key="inert", request_user_scope=Mock())


@pytest.mark.integration
def test_native_receipt_orphan_commits_before_cleanup_and_retries_after_redis_failure(recovery_database, monkeypatch):
    _config, _engine, repo, deadline, create = recovery_database
    identity = create("controller")
    read_receipts = route(monkeypatch, repo, identity["thread_id"])
    observed = []

    def uncertain_cleanup(thread, *, owner_task_id, lease_token):
        row = get_chat_completion_attempt_by_task_id(repo, owner_task_id)
        assert row["terminal_event_type"] == "task.failed"
        assert row["terminal_outcome"]["failure_code"] == "CHAT_ACCEPTED_TASK_ORPHANED"
        assert thread == identity["thread_id"] and lease_token == "lock-controller"
        assert row["deadline_snapshot"] == deadline.to_dict()
        observed.append(row["terminal_outcome"])
        raise RuntimeError("injected lost Redis acknowledgement")

    monkeypatch.setattr(service, "release_terminal_attempt_turn_lock", uncertain_cleanup)
    first = read_receipts()
    receipt = next(row for row in first["tasks"] if row["task_id"] == identity["backend_task_id"])
    assert receipt["state"] == "terminal" and receipt["event_type"] == "task.failed"
    assert receipt["failure_code"] == "CHAT_ACCEPTED_TASK_ORPHANED"
    assert receipt["deadline_snapshot"] == deadline.to_dict()
    assert "lock-controller" not in repr(first)
    cleanup = Mock(return_value=True)
    monkeypatch.setattr(service, "release_terminal_attempt_turn_lock", cleanup)
    second = read_receipts()
    assert second["tasks"] == first["tasks"]
    cleanup.assert_called_once_with(identity["thread_id"], owner_task_id=identity["backend_task_id"], lease_token="lock-controller")
    assert observed == [receipt["terminal_outcome"]]


@pytest.mark.integration
def test_native_retry_reconciles_before_lock_safety_expiry_without_queue_or_heartbeat(recovery_database, monkeypatch):
    _config, _engine, repo, deadline, create = recovery_database
    identity = create("retry")
    lock = build_turn_lock_envelope(
        identity["thread_id"], identity["backend_task_id"], turn_id=identity["turn_id"],
        lease_token="lock-retry", acquired_at=datetime.now(timezone.utc).isoformat(), ttl_seconds=840,
    )
    assert datetime.fromisoformat(lock.lease_expires_at) > datetime.now(timezone.utc)
    monkeypatch.setattr(service.dependencies, "chatlog_db", repo)
    monkeypatch.setattr(service, "get_turn_lock", lambda *_: lock)
    monkeypatch.setattr(service, "_chat_worker_heartbeat_evidence", Mock(side_effect=AssertionError("heartbeat consulted")))
    monkeypatch.setattr(service, "_task_terminal_event", Mock(side_effect=AssertionError("Redis terminal used as recovery authority")))
    enqueue = Mock(side_effect=AssertionError("recovery replayed work"))
    monkeypatch.setattr(service, "enqueue", enqueue)

    def cleanup(thread, *, owner_task_id, lease_token):
        row = get_chat_completion_attempt_by_task_id(repo, owner_task_id)
        assert row["terminal_outcome"]["failure_code"] == "CHAT_ACCEPTED_TASK_ORPHANED"
        assert row["deadline_snapshot"] == deadline.to_dict()
        assert (thread, lease_token) == (identity["thread_id"], "lock-retry")
        return True

    monkeypatch.setattr(service, "release_terminal_attempt_turn_lock", cleanup)
    assert service._recover_orphaned_turn_lock(identity["thread_id"])
    enqueue.assert_not_called()


@pytest.mark.integration
def test_native_controller_leaves_legacy_and_unconfirmed_admission_unknown(recovery_database, monkeypatch):
    _config, _engine, repo, _deadline, create = recovery_database
    legacy = create("legacy", legacy=True)
    unconfirmed = create("unconfirmed", accepted=False)
    read_receipts = route(monkeypatch, repo, legacy["thread_id"])
    cleanup = Mock()
    monkeypatch.setattr(service, "release_terminal_attempt_turn_lock", cleanup)
    result = read_receipts()
    assert len(result["tasks"]) == 2
    assert all(row["state"] == "unknown" and row["event_type"] is None for row in result["tasks"])
    for identity in (legacy, unconfirmed):
        row = get_chat_completion_attempt_by_task_id(repo, identity["backend_task_id"])
        assert row["terminal_outcome"] is None and row["terminal_event_type"] is None
    cleanup.assert_not_called()


@pytest.mark.integration
def test_native_controller_database_failure_cannot_fall_back_to_redis_truth(recovery_database, monkeypatch):
    _config, engine, repo, _deadline, create = recovery_database
    identity = create("failure")
    read_receipts = route(monkeypatch, repo, identity["thread_id"])
    cleanup = Mock()
    observer = Mock(side_effect=AssertionError("uncertainty fell back to Redis"))
    monkeypatch.setattr(service, "release_terminal_attempt_turn_lock", cleanup)
    monkeypatch.setattr(chat.task_events, "describe_terminal_state_in_scope", observer)
    with engine.begin() as connection:
        connection.execute(text("""CREATE FUNCTION reject_controller_outcome() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
                IF NEW.terminal_outcome IS NOT NULL THEN RAISE EXCEPTION 'injected controller failure'; END IF;
                RETURN NEW;
            END; $$"""))
        connection.execute(text("CREATE TRIGGER reject_controller_outcome BEFORE UPDATE ON chat_completion_attempts "
                                "FOR EACH ROW EXECUTE FUNCTION reject_controller_outcome()"))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        read_receipts()
    assert error.value.status_code == 503
    row = get_chat_completion_attempt_by_task_id(repo, identity["backend_task_id"])
    assert row["terminal_outcome"] is None and row["terminal_event_type"] is None
    cleanup.assert_not_called()
    observer.assert_not_called()
