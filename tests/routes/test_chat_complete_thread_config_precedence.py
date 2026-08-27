from __future__ import annotations

from guardian.core import chat_completion_service
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


def _capture_accepted_completion(captured: dict[str, object]):
    def fake_enqueue(task, **_kwargs):
        captured["task"] = task
        task_created_event = chat_completion_service.ChatCompletionTaskCreatedEventResult(
            ok=True,
            task_id=task.task_id,
            event_type="task.created",
            event_id=f"{task.task_id}:created",
            visibility_scope="progress",
            terminal_visibility=False,
            execution_continued=True,
        )
        return chat_completion_service.ChatCompletionEnqueueResult(
            task=task,
            task_id=task.task_id,
            acceptance_status="accepted",
            acceptance_warnings=(),
            queue_accepted=True,
            degraded=False,
            turn_lock_acquired=True,
            turn_lock={},
            task_created_event=task_created_event,
        )

    return fake_enqueue


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
        chat_routes,
        "enqueue_chat_completion",
        _capture_accepted_completion(captured),
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )
    _override_request_scope(test_client, expected_user_id)

    try:
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
    finally:
        test_client.app.dependency_overrides.pop(
            chat_routes.get_request_user_scope, None
        )

    assert response.status_code == 200
    assert response.json()["source_mode"] == "project"
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
        chat_routes,
        "enqueue_chat_completion",
        _capture_accepted_completion(captured),
    )
    monkeypatch.setattr(
        chat_routes,
        "_get_task_completed_payload",
        lambda *_args, **_kwargs: None,
    )
    _override_request_scope(test_client, expected_user_id)

    try:
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
    finally:
        test_client.app.dependency_overrides.pop(
            chat_routes.get_request_user_scope, None
        )

    assert response.status_code == 200
    assert response.json()["source_mode"] == "personal_knowledge"
    task = captured["task"]
    assert getattr(task, "provider") == "groq"
    assert getattr(task, "model") == "override-model"
    assert getattr(task, "reasoning_mode") == "think"
    assert "|source_mode=personal_knowledge" in getattr(task, "origin")
