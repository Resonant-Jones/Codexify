from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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
        "guardian.routes.chat._task_terminal_event", lambda *_: None
    )
    monkeypatch.setattr(
        "guardian.routes.chat._chat_worker_heartbeat_age_seconds",
        lambda: None,
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
    monkeypatch.setattr(
        "guardian.routes.chat._task_terminal_event", lambda *_: None
    )
    monkeypatch.setattr(
        "guardian.routes.chat._chat_worker_heartbeat_age_seconds",
        lambda: 1.0,
    )
    clear_spy = MagicMock(return_value=False)
    monkeypatch.setattr("guardian.routes.chat.clear_turn_lock", clear_spy)

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 429
    assert response.json()["detail"] == "turn_in_flight"
    clear_spy.assert_not_called()
    mock_db.write_audit_log.assert_not_called()
