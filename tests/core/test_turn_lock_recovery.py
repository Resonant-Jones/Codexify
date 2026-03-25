from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from guardian.queue import task_events
from guardian.queue.turn_lock import TurnLockEnvelope, build_turn_lock_envelope

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
    }
    mock.write_audit_log.return_value = None
    return mock


@pytest.fixture
def test_client(mock_db, monkeypatch, tmp_path):
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))
    with patch("logging.info"):
        with patch("guardian.guardian_api.chatlog_db", mock_db):
            with patch("guardian.core.dependencies.chatlog_db", mock_db):
                with patch("guardian.routes.chat.chatlog_db", mock_db):
                    with patch(
                        "guardian.guardian_api.event_bus"
                    ) as mock_event_bus:
                        mock_event_bus.emit_event.return_value = None
                        from guardian.guardian_api import app, require_api_key

                        app.dependency_overrides[
                            require_api_key
                        ] = lambda: "test-api-key"
                        client = TestClient(app)
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
    batches = [
        [
            ("1-1", {"type": "task.running", "data": {"step": 1}}),
            ("1-2", {"type": "task.completed", "data": {"result": "ok"}}),
        ]
    ]

    def fake_read_events(
        _task_id: str,
        _last_id: str,
        *,
        block_ms: int = 15000,
        count: int = 100,
    ) -> list[tuple[str, dict[str, object]]]:
        _ = block_ms, count
        if batches:
            return batches.pop(0)
        return []

    monkeypatch.setattr(task_events, "read_events", fake_read_events)

    evidence = task_events.describe_terminal_state("task-123")

    assert evidence["state"] == "terminal"
    assert evidence["event_type"] == "task.completed"
    assert evidence["event"]["data"] == {"result": "ok"}


def test_complete_recovers_orphaned_turn_lock(
    test_client, mock_db, monkeypatch
):
    captured: dict[str, object] = {}
    acquire_calls = {"count": 0}

    def _acquire(*args, **kwargs):
        acquire_calls["count"] += 1
        if acquire_calls["count"] == 1:
            return None
        return build_turn_lock_envelope(
            args[0],
            args[1],
            turn_id=kwargs.get("turn_id"),
            source=kwargs.get("source"),
        )

    monkeypatch.setattr("guardian.routes.chat.acquire_turn_lock", _acquire)
    monkeypatch.setattr(
        "guardian.routes.chat.get_turn_lock", lambda *_: _stale_lock()
    )
    monkeypatch.setattr(
        "guardian.routes.chat.turn_lock_is_stale", lambda *_: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat._task_terminal_event",
        lambda *_: _terminal_evidence("terminal"),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._chat_worker_heartbeat_evidence",
        lambda: _heartbeat_evidence("fresh", age_seconds=1.0),
    )
    cleared: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "guardian.routes.chat.clear_turn_lock",
        lambda thread_id, expected=None: cleared.append(
            (thread_id, getattr(expected, "owner_task_id", ""))
        )
        or True,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 200
    assert cleared == [(1, "task-stale")]
    assert mock_db.write_audit_log.call_args[0] == (
        "recover_orphaned_turn_lock",
        "chat_thread",
        "1",
    )
    assert mock_db.write_audit_log.call_args.kwargs == {"user_id": "system"}
    task = captured["task"]
    assert getattr(task, "turn_lock_owner") == getattr(task, "task_id")
    assert getattr(task, "turn_lock")["turn_id"]


@pytest.mark.parametrize("worker_state", ["stale", "missing"])
def test_complete_recovers_orphaned_turn_lock_when_worker_not_fresh(
    test_client, mock_db, monkeypatch, worker_state
):
    captured: dict[str, object] = {}
    acquire_calls = {"count": 0}

    def _acquire(*args, **kwargs):
        acquire_calls["count"] += 1
        if acquire_calls["count"] == 1:
            return None
        return build_turn_lock_envelope(
            args[0],
            args[1],
            turn_id=kwargs.get("turn_id"),
            source=kwargs.get("source"),
        )

    monkeypatch.setattr("guardian.routes.chat.acquire_turn_lock", _acquire)
    monkeypatch.setattr(
        "guardian.routes.chat.get_turn_lock", lambda *_: _stale_lock()
    )
    monkeypatch.setattr(
        "guardian.routes.chat.turn_lock_is_stale", lambda *_: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat._task_terminal_event",
        lambda *_: _terminal_evidence("nonterminal"),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._chat_worker_heartbeat_evidence",
        lambda: _heartbeat_evidence(worker_state),
    )
    cleared: list[tuple[int, str]] = []
    monkeypatch.setattr(
        "guardian.routes.chat.clear_turn_lock",
        lambda thread_id, expected=None: cleared.append(
            (thread_id, getattr(expected, "owner_task_id", ""))
        )
        or True,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 200
    assert acquire_calls["count"] == 2
    assert cleared == [(1, "task-stale")]
    assert captured["queue_name"] == "codexify:queue:chat"
    assert getattr(captured["task"], "turn_lock_owner") == getattr(
        captured["task"], "task_id"
    )


def test_complete_denies_recovery_when_worker_fresh(
    test_client, mock_db, monkeypatch
):
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.get_turn_lock", lambda *_: _stale_lock()
    )
    monkeypatch.setattr(
        "guardian.routes.chat.turn_lock_is_stale", lambda *_: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat._task_terminal_event",
        lambda *_: _terminal_evidence("nonterminal"),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._chat_worker_heartbeat_evidence",
        lambda: _heartbeat_evidence("fresh", age_seconds=1.0),
    )
    clear_spy = MagicMock(return_value=False)
    monkeypatch.setattr("guardian.routes.chat.clear_turn_lock", clear_spy)

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 429
    assert response.json()["detail"] == "turn_in_flight"
    clear_spy.assert_not_called()
    mock_db.write_audit_log.assert_not_called()


def test_complete_denies_recovery_on_unknown_terminal_state(
    test_client, mock_db, monkeypatch
):
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.get_turn_lock", lambda *_: _stale_lock()
    )
    monkeypatch.setattr(
        "guardian.routes.chat.turn_lock_is_stale", lambda *_: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat._task_terminal_event",
        lambda *_: _terminal_evidence("unknown", reason="event_probe_failed"),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._chat_worker_heartbeat_evidence",
        lambda: _heartbeat_evidence("stale", age_seconds=27.0),
    )
    clear_spy = MagicMock(return_value=False)
    monkeypatch.setattr("guardian.routes.chat.clear_turn_lock", clear_spy)

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 429
    assert response.json()["detail"] == "turn_in_flight"
    clear_spy.assert_not_called()
    mock_db.write_audit_log.assert_not_called()


def test_complete_keeps_active_turn_lock_in_place(
    test_client, mock_db, monkeypatch
):
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.get_turn_lock", lambda *_: _stale_lock()
    )
    monkeypatch.setattr(
        "guardian.routes.chat.turn_lock_is_stale", lambda *_: False
    )
    clear_spy = MagicMock(return_value=False)
    monkeypatch.setattr("guardian.routes.chat.clear_turn_lock", clear_spy)

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 429
    assert response.json()["detail"] == "turn_in_flight"
    clear_spy.assert_not_called()
    mock_db.write_audit_log.assert_not_called()
