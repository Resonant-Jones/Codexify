from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from guardian.queue import task_events
from guardian.routes import chat


@pytest.fixture(autouse=True)
def _ensure_groq_key(monkeypatch):
    """Keep chat completion configuration stable for route tests."""
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    try:
        chat.llm_settings.LLM_PROVIDER = "groq"
        chat.llm_settings.LLM_MODEL = "moonshotai-kimi-k2-instruct-9050"
    except Exception:
        pass


def test_task_event_publish_error_preserves_cause():
    cause = RuntimeError("redis down")
    with pytest.raises(task_events.TaskEventPublishError) as excinfo:
        raise task_events.TaskEventPublishError(
            task_id="task-1",
            event_type="task.created",
            cause=cause,
            visibility_scope="progress",
            failure_class="RuntimeError",
            error=str(cause),
        ) from cause

    error = excinfo.value
    assert error.error_code == "TASK_EVENT_PUBLISH_FAILED"
    assert error.task_id == "task-1"
    assert error.event_type == "task.created"
    assert error.visibility_scope == "progress"
    assert error.cause_class == "RuntimeError"
    assert error.__cause__ is cause


def test_api_chat_complete_logs_tagged_task_created_publish_failure(
    test_client, mock_db, monkeypatch, caplog
):
    mock_db.list_messages.return_value = [
        {"role": "user", "content": "Hello there"}
    ]

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

    def _publish_with_visibility(task_id, event_type, data):
        return {
            "ok": False,
            "task_id": task_id,
            "event_type": event_type,
            "visibility_scope": "progress",
            "terminal_visibility": False,
            "execution_continued": True,
            "event_id": None,
            "failure_class": "RuntimeError",
            "error_code": "TASK_EVENT_PUBLISH_FAILED",
            "error": "redis down",
            "exception": RuntimeError("redis down"),
        }

    monkeypatch.setattr(
        "guardian.routes.chat.task_events.publish_with_visibility",
        MagicMock(side_effect=_publish_with_visibility),
    )

    with caplog.at_level(logging.ERROR, logger="guardian.routes.chat"):
        response = test_client.post(
            "/api/chat/1/complete",
            json={},
            headers={"X-Request-ID": "req-chat-complete-1"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["acceptance_status"] == "accepted_degraded"
    assert payload["acceptance_warnings"] == [
        "task_created_event_publish_failed"
    ]
    assert captured["queue_name"] == "codexify:queue:chat"
    task = captured["task"]
    assert getattr(task, "thread_id") == 1
    assert getattr(task, "turn_lock_owner") == payload["task_id"]

    tagged_records = [
        record
        for record in caplog.records
        if record.name == "guardian.routes.chat"
        and "CHAT_COMPLETE_TASK_CREATED_EVENT_FAILED" in record.message
    ]
    assert len(tagged_records) == 1
    record = tagged_records[0]
    assert "request_id=req-chat-complete-1" in record.message
    assert "thread_id=1" in record.message
    assert f"task_id={payload['task_id']}" in record.message
    assert "turn_id=" in record.message
    assert "depth_mode=" in record.message
    assert "event_type=task.created" in record.message
    assert "cause_class=RuntimeError" in record.message
