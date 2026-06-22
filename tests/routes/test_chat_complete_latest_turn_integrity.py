from __future__ import annotations

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes
from tests.utils import get_test_user_id


def _override_request_scope(test_client, user_id: str) -> None:
    test_client.app.dependency_overrides[
        chat_routes.get_request_user_scope
    ] = lambda: RequestUserScope(
        user_id=user_id,
        subject_id=user_id,
        account_id=user_id,
        multi_user_enabled=False,
    )


def _thread_config_snapshot() -> dict[str, object]:
    return {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }


def test_chat_complete_queues_latest_user_turn_identity(
    test_client, mock_db, monkeypatch
):
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
        "project_id": 1,
        "thread_config": _thread_config_snapshot(),
    }
    mock_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "question A"},
        {"id": 2, "role": "assistant", "content": "answer A"},
        {"id": 3, "role": "user", "content": "question B"},
        {"id": 4, "role": "assistant", "content": "stale answer"},
    ]

    captured: dict[str, object] = {}

    monkeypatch.setattr(chat_routes, "acquire_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(chat_routes, "release_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(
        chat_routes,
        "_publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    def _capture_enqueue(task, queue_name):
        captured["task"] = task
        captured["queue_name"] = queue_name
        captured["queued_payload"] = task.to_dict()
        return None

    monkeypatch.setattr(chat_routes, "enqueue", _capture_enqueue)
    _override_request_scope(test_client, expected_user_id)

    try:
        response = test_client.post("/chat/1/complete", json={})
    finally:
        test_client.app.dependency_overrides.pop(
            chat_routes.get_request_user_scope, None
        )

    assert response.status_code == 200
    assert captured["queue_name"] == "codexify:queue:chat"
    task = captured["task"]
    assert getattr(task, "latest_turn_message_id") == 3
    assert captured["queued_payload"]["latest_turn_message_id"] == 3
    assert "turn_id=" in getattr(task, "origin")


def test_chat_complete_rejects_threads_without_a_user_turn(
    test_client, mock_db, monkeypatch
):
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
        "project_id": 1,
        "thread_config": _thread_config_snapshot(),
    }
    mock_db.list_messages.return_value = [
        {"id": 1, "role": "assistant", "content": "answer only"},
        {"id": 2, "role": "assistant", "content": "still answer only"},
    ]

    enqueue_calls: list[object] = []
    publish_calls: list[object] = []

    monkeypatch.setattr(chat_routes, "acquire_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(chat_routes, "release_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(
        chat_routes,
        "enqueue",
        lambda *a, **k: enqueue_calls.append((a, k)),
    )
    monkeypatch.setattr(
        chat_routes,
        "_publish_completion_start_event",
        lambda *a, **k: publish_calls.append((a, k)),
    )
    _override_request_scope(test_client, expected_user_id)

    try:
        response = test_client.post("/chat/1/complete", json={})
    finally:
        test_client.app.dependency_overrides.pop(
            chat_routes.get_request_user_scope, None
        )

    assert response.status_code == 400
    assert enqueue_calls == []
    assert publish_calls == []
