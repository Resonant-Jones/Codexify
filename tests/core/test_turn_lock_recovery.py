from __future__ import annotations

import os
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from guardian.queue import task_events
from guardian.protocol_tokens import ChatEventType, ErrorCode
from guardian.core.db import ChatAttemptReconciliation
from guardian.queue.turn_lock import TurnLockEnvelope, build_turn_lock_envelope
from guardian.core import chat_completion_service
from guardian.routes import chat as chat_routes
from tests.utils import get_test_api_key, get_test_auth_headers

os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("STORAGE_BASE_PATH", "/tmp/test_media")
os.environ.setdefault("ENABLE_BLIP_MODEL", "false")
os.environ.setdefault("GUARDIAN_ENABLE_MONDREAM", "0")
os.environ.setdefault("ENABLE_CONNECTOR_WORKER", "0")


@pytest.fixture
def mock_db():
    mock = MagicMock()
    mock.list_messages.return_value = [
        {
            "id": 1,
            "thread_id": 1,
            "role": "user",
            "content": "Test message",
            "created_at": "2026-03-13T12:00:00",
        }
    ]
    mock.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "title": "Test Thread",
        "summary": "",
        "project_id": 1,
        "active_profile_id": None,
        "active_profile_revision": None,
    }
    mock.write_audit_log.return_value = None
    return mock


@pytest.fixture
def test_client(mock_db, monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "test_user")
    # These cases exercise orphan recovery; lease renewal has separate coverage.
    monkeypatch.setattr(
        chat_completion_service,
        "renew_turn_lock",
        lambda _thread_id, lock, **_kwargs: lock,
    )
    with patch("logging.info"):
        with patch("guardian.guardian_api.chatlog_db", mock_db):
            with patch("guardian.core.dependencies.chatlog_db", mock_db):
                with patch.object(chat_routes, "chatlog_db", mock_db):
                    with patch.object(
                        chat_routes,
                        "run_with_redis_timeout",
                        lambda fn, *_, **__: fn(),
                    ):
                        with patch.object(
                            chat_routes.task_events,
                            "publish_with_visibility",
                            lambda task_id, event_type, payload: {
                                "ok": True,
                                "task_id": task_id,
                                "event_type": event_type,
                                "event_id": "1-1",
                                "visibility_scope": "live",
                                "terminal_visibility": False,
                                "execution_continued": True,
                                "payload": payload,
                            },
                        ):
                            with patch.object(
                                chat_routes.task_events,
                                "read_events",
                                lambda *_, **__: [],
                            ):
                                with patch(
                                    "guardian.guardian_api.event_bus"
                                ) as mock_event_bus:
                                    mock_event_bus.emit_event.return_value = None
                                    from guardian.guardian_api import (
                                        app,
                                        require_api_key,
                                    )

                                    app.dependency_overrides[
                                        require_api_key
                                    ] = lambda: get_test_api_key()
                                    app.dependency_overrides[
                                        chat_routes.get_request_user_scope
                                    ] = lambda: chat_routes.RequestUserScope(
                                        user_id="test_user",
                                        subject_id="test_user",
                                        account_id="test_user",
                                        multi_user_enabled=False,
                                    )
                                    client = TestClient(
                                        app, headers=get_test_auth_headers()
                                    )
                                    try:
                                        yield client
                                    finally:
                                        app.dependency_overrides.clear()


def _stale_lock(thread_id: int = 1) -> TurnLockEnvelope:
    lock = build_turn_lock_envelope(
        thread_id,
        "task-stale",
        turn_id="44444444-4444-4444-8444-444444444444",
        ttl_seconds=30,
        source="worker:chat",
    )
    return TurnLockEnvelope(
        thread_id=lock.thread_id,
        owner_task_id=lock.owner_task_id,
        turn_id=lock.turn_id,
        acquired_at="2026-03-13T12:00:00+00:00",
        renewed_at="2026-03-13T12:00:00+00:00",
        lease_expires_at="2026-03-13T12:00:30+00:00",
        lease_ttl_seconds=30,
        lease_token=lock.lease_token,
        source=lock.source,
    )


def _terminal_evidence(
    state: str,
    *,
    event_type: str = "task.completed",
    reason: str = "terminal_event_found",
    task_id: str = "task-stale",
) -> dict[str, object]:
    if state == "terminal":
        return {
            "task_id": task_id,
            "state": "terminal",
            "event_id": "1-2",
            "event": {"type": event_type, "data": {}},
            "event_type": event_type,
            "reason": reason,
        }
    if state == "nonterminal":
        return {
            "task_id": task_id,
            "state": "nonterminal",
            "event_id": None,
            "event": None,
            "event_type": None,
            "reason": reason,
        }
    return {
        "task_id": task_id,
        "state": "unknown",
        "event_id": None,
        "event": None,
        "event_type": None,
        "reason": reason,
    }


def _heartbeat_evidence(
    state: str,
    *,
    age_seconds: float | None = None,
    reason: str = "ok",
) -> dict[str, object]:
    if state == "missing":
        return {
            "key": "codexify:worker:chat:heartbeat",
            "state": "missing",
            "age_seconds": None,
            "detected": False,
            "reason": "heartbeat_missing" if reason == "ok" else reason,
            "error": None,
        }
    if state == "unknown":
        return {
            "key": "codexify:worker:chat:heartbeat",
            "state": "unknown",
            "age_seconds": None,
            "detected": False,
            "reason": reason,
            "error": "probe_failed",
        }
    if age_seconds is None:
        age_seconds = {
            "fresh": 1.0,
            "stale": 27.0,
            "dead": 61.0,
        }.get(state, 1.0)
    return {
        "key": "codexify:worker:chat:heartbeat",
        "state": state,
        "age_seconds": age_seconds,
        "detected": True,
        "reason": reason,
        "error": None,
    }


def test_terminal_state_helper_detects_terminal_event(monkeypatch):
    client = MagicMock()
    client.xrange.return_value = [
        ("1-1", {"type": "task.running", "data": '{"step":1}'}),
        ("1-2", {"type": "task.completed", "data": '{"result":"ok"}'}),
    ]
    monkeypatch.setattr(task_events, "_with_reconnect", lambda fn: fn(client))

    evidence = task_events.describe_terminal_state("task-123")

    assert evidence["state"] == "terminal"
    assert evidence["event_type"] == "task.completed"
    assert evidence["event"]["data"] == {"result": "ok"}



@pytest.fixture
def durable_recovery(monkeypatch):
    lock = _stale_lock()
    attempt = {"request_id": "request-stale", "backend_task_id": lock.owner_task_id,
               "thread_id": lock.thread_id, "turn_id": lock.turn_id}
    read = MagicMock(return_value=attempt)
    reconcile = MagicMock(return_value=ChatAttemptReconciliation(None, None, None, None))
    cleanup = MagicMock(return_value=True)
    monkeypatch.setattr(chat_completion_service, "get_turn_lock", lambda *_: lock)
    monkeypatch.setattr(chat_completion_service, "get_chat_completion_attempt_by_task_id", read)
    monkeypatch.setattr(chat_completion_service, "reconcile_chat_completion_attempt_after_deadline", reconcile)
    monkeypatch.setattr(chat_completion_service, "release_terminal_attempt_turn_lock", cleanup)
    monkeypatch.setattr(chat_completion_service, "_task_terminal_event", MagicMock(side_effect=AssertionError("Redis events are not recovery authority")))
    monkeypatch.setattr(chat_completion_service, "_chat_worker_heartbeat_evidence", MagicMock(side_effect=AssertionError("Heartbeat is not recovery authority")))
    return lock, attempt, read, reconcile, cleanup


def test_complete_recovers_from_durable_orphan_with_only_new_queue_identity(
    test_client, mock_db, monkeypatch, durable_recovery
):
    lock, _attempt, _read, reconcile, cleanup = durable_recovery
    reconcile.return_value = ChatAttemptReconciliation(None, "task.failed", {
        "failure_code": ErrorCode.CHAT_ACCEPTED_TASK_ORPHANED.value,
        "reconciled_at": "2026-10-04T00:00:00+00:00",
    }, lock.lease_token)
    captured, calls, events = {}, [], []

    def acquire(thread, owner, **kwargs):
        calls.append(owner)
        if len(calls) == 1:
            return None
        return build_turn_lock_envelope(thread, owner, turn_id=kwargs["turn_id"])

    monkeypatch.setattr(chat_completion_service, "acquire_turn_lock", acquire)
    monkeypatch.setattr(chat_completion_service, "enqueue", lambda task, queue_name: captured.update(task=task, queue_name=queue_name))
    monkeypatch.setattr(chat_routes.event_bus, "emit_event", lambda name, payload: events.append(name))
    response = test_client.post("/chat/1/complete", json={})
    assert response.status_code == 200
    task = captured["task"]
    assert len(calls) == 2 and calls[0] == calls[1] == task.task_id
    assert task.task_id != lock.owner_task_id and task.request_id != "request-stale"
    assert captured["queue_name"] == "codexify:queue:chat"
    cleanup.assert_called_once_with(1, owner_task_id=lock.owner_task_id, lease_token=lock.lease_token)
    mock_db.write_audit_log.assert_not_called()
    assert ChatEventType.ORPHANED_TURN_RECOVERED.value not in events


@pytest.mark.parametrize("worker_state", ["fresh", "stale", "missing", "unknown"])
def test_complete_does_not_infer_recovery_from_heartbeat(
    test_client, mock_db, monkeypatch, durable_recovery, worker_state
):
    _lock, _attempt, _read, reconcile, cleanup = durable_recovery
    monkeypatch.setattr(chat_completion_service, "acquire_turn_lock", lambda *a, **kw: None)
    # None of these observational states can override an unresolved durable attempt.
    probe = MagicMock(return_value=_heartbeat_evidence(worker_state))
    monkeypatch.setattr(chat_completion_service, "_chat_worker_heartbeat_evidence", probe)
    response = test_client.post("/chat/1/complete", json={})
    assert response.status_code == 429 and response.json()["detail"] == "turn_in_flight"
    assert reconcile.call_count == 1
    cleanup.assert_not_called()
    probe.assert_not_called()
    mock_db.write_audit_log.assert_not_called()


@pytest.mark.parametrize("kind", ["completed", "task.failed", "task.cancelled"])
def test_durable_terminal_truth_releases_lock_without_claiming_orphan(durable_recovery, kind):
    lock, _attempt, _read, reconcile, cleanup = durable_recovery
    reconcile.return_value = ChatAttemptReconciliation(
        71 if kind == "completed" else None, None if kind == "completed" else kind, None, lock.lease_token
    )
    assert chat_completion_service._recover_orphaned_turn_lock(1)
    cleanup.assert_called_once_with(1, owner_task_id=lock.owner_task_id, lease_token=lock.lease_token)


def test_terminal_recovery_does_not_wait_for_lock_safety_margin(durable_recovery, monkeypatch):
    lock, _attempt, _read, reconcile, _cleanup = durable_recovery
    monkeypatch.setattr(chat_completion_service, "get_turn_lock", lambda *_: replace(lock, lease_expires_at="2099-01-01T00:00:00+00:00"))
    reconcile.return_value = ChatAttemptReconciliation(None, "task.failed", {
        "failure_code": ErrorCode.CHAT_ACCEPTED_TASK_ORPHANED.value,
    }, lock.lease_token)
    assert chat_completion_service._recover_orphaned_turn_lock(1)


@pytest.mark.parametrize("binding", ["thread_id", "turn_id", "missing"])
def test_mismatched_attempt_lock_binding_fails_closed(durable_recovery, binding):
    _lock, attempt, read, reconcile, cleanup = durable_recovery
    read.return_value = None if binding == "missing" else attempt | {binding: 999 if binding == "thread_id" else "wrong"}
    assert not chat_completion_service._recover_orphaned_turn_lock(1)
    reconcile.assert_not_called()
    cleanup.assert_not_called()


def test_legacy_terminal_uses_only_matching_observed_capability(durable_recovery):
    lock, _attempt, _read, reconcile, cleanup = durable_recovery
    reconcile.return_value = ChatAttemptReconciliation(71, None, None, None)
    assert chat_completion_service._recover_orphaned_turn_lock(1)
    cleanup.assert_called_once_with(1, owner_task_id=lock.owner_task_id, lease_token=lock.lease_token)


def test_reconciliation_error_cannot_release_lock(durable_recovery):
    from fastapi import HTTPException

    _lock, _attempt, _read, reconcile, cleanup = durable_recovery
    reconcile.side_effect = RuntimeError("injected uncertain commit")
    with pytest.raises(HTTPException) as error:
        chat_completion_service._recover_orphaned_turn_lock(1)
    assert error.value.status_code == 503
    cleanup.assert_not_called()


def test_replacement_lock_cannot_be_released(durable_recovery):
    lock, _attempt, _read, reconcile, cleanup = durable_recovery
    reconcile.return_value = ChatAttemptReconciliation(None, "task.failed", None, lock.lease_token)
    cleanup.return_value = False
    assert not chat_completion_service._recover_orphaned_turn_lock(1)
