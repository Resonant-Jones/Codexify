from __future__ import annotations


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
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
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

    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat.release_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat._publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        "guardian.routes.chat._get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    def _capture_enqueue(task, queue_name):
        captured["task"] = task
        captured["queue_name"] = queue_name
        captured["queued_payload"] = task.to_dict()
        return None

    monkeypatch.setattr("guardian.routes.chat.enqueue", _capture_enqueue)

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 200
    assert captured["queue_name"] == "codexify:queue:chat"
    task = captured["task"]
    assert getattr(task, "latest_turn_message_id") == 3
    assert captured["queued_payload"]["latest_turn_message_id"] == 3
    assert "turn_id=" in getattr(task, "origin")


def test_chat_complete_rejects_threads_without_a_user_turn(
    test_client, mock_db, monkeypatch
):
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "project_id": 1,
        "thread_config": _thread_config_snapshot(),
    }
    mock_db.list_messages.return_value = [
        {"id": 1, "role": "assistant", "content": "answer only"},
        {"id": 2, "role": "assistant", "content": "still answer only"},
    ]

    enqueue_calls: list[object] = []
    publish_calls: list[object] = []

    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat.release_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda *a, **k: enqueue_calls.append((a, k)),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._publish_completion_start_event",
        lambda *a, **k: publish_calls.append((a, k)),
    )

    response = test_client.post("/chat/1/complete", json={})

    assert response.status_code == 400
    assert enqueue_calls == []
    assert publish_calls == []
