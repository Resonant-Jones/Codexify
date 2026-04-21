from __future__ import annotations

from tests.utils import get_test_user_id


def test_chat_complete_thread_config_beats_request_overrides(
    test_client, mock_db, monkeypatch
):
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
        "project_id": 7,
        "thread_config": {
            "providerId": "local",
            "modelId": "qwen3.5:14b",
            "inferenceMode": "fast",
            "retrievalSource": "project",
            "personaId": "persona-7",
        },
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        "guardian.routes.chat._get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    response = test_client.post(
        "/chat/1/complete",
        json={
            "provider": "groq",
            "model": "override-model",
            "reasoning_mode": "think",
            "source_mode": "personal_knowledge",
            "depth_mode": "normal",
        },
    )

    assert response.status_code == 200
    assert response.json()["source_mode"] == "project"
    assert captured["queue_name"] == "codexify:queue:chat"
    task = captured["task"]
    assert getattr(task, "provider") == "local"
    assert getattr(task, "model") == "override-model"
    assert getattr(task, "reasoning_mode") == "think"
    assert "|source_mode=project" in getattr(task, "origin")


def test_chat_complete_legacy_thread_without_thread_config_still_completes(
    test_client, mock_db, monkeypatch
):
    expected_user_id = get_test_user_id()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": expected_user_id,
        "project_id": 7,
        "thread_config": None,
    }
    mock_db.list_messages.return_value = [{"role": "user", "content": "Hello"}]

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "guardian.routes.chat.acquire_turn_lock",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "guardian.routes.chat.enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.chat._publish_completion_start_event",
        lambda **_kwargs: {"ok": True, "event_id": "evt-1"},
    )
    monkeypatch.setattr(
        "guardian.routes.chat._get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )

    response = test_client.post(
        "/chat/1/complete",
        json={
            "provider": "groq",
            "model": "override-model",
            "reasoning_mode": "think",
            "source_mode": "personal_knowledge",
            "depth_mode": "normal",
        },
    )

    assert response.status_code == 200
    assert response.json()["source_mode"] == "personal_knowledge"
    assert captured["queue_name"] == "codexify:queue:chat"
    task = captured["task"]
    assert getattr(task, "provider") == "groq"
    assert getattr(task, "model") == "override-model"
    assert getattr(task, "reasoning_mode") == "think"
    assert "|source_mode=personal_knowledge" in getattr(task, "origin")
