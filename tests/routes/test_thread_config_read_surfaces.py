from __future__ import annotations

from typing import Any

from guardian.routes import chat as chat_routes


def _thread_row(
    thread_id: int,
    *,
    title: str | None = None,
    thread_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": thread_id,
        "user_id": "test_user",
        "title": title or f"Thread {thread_id}",
        "summary": "",
        "project_id": 1,
        "parent_id": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "archived_at": None,
        "thread_config": thread_config,
    }


def test_chat_thread_list_response_preserves_thread_config(
    test_client, mock_db
):
    thread_config = {
        "providerId": "local",
        "modelId": "qwen3.5:14b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }
    mock_db.list_chat_threads.return_value = [
        _thread_row(1, thread_config=thread_config),
        _thread_row(2, thread_config=None),
    ]

    response = test_client.get("/api/chat/threads")

    assert response.status_code == 200
    data = response.json()
    assert data["threads"][0]["thread_config"] == thread_config
    assert data["threads"][1]["thread_config"] is None


def test_chat_single_thread_fetch_preserves_thread_config(monkeypatch, mock_db):
    thread_config = {
        "providerId": "local",
        "modelId": "qwen3.5:0.8b",
        "inferenceMode": "fast",
        "retrievalSource": "project",
        "personaId": None,
    }
    mock_db.get_chat_thread.return_value = _thread_row(
        42, thread_config=thread_config
    )
    monkeypatch.setattr(chat_routes, "chatlog_db", mock_db)

    result = chat_routes.get_thread(42, api_key="test-api-key")

    assert result["thread_id"] == 42
    assert result["thread_config"] == thread_config


def test_chat_single_thread_fetch_keeps_null_thread_config(
    monkeypatch, mock_db
):
    mock_db.get_chat_thread.return_value = _thread_row(42, thread_config=None)
    monkeypatch.setattr(chat_routes, "chatlog_db", mock_db)

    result = chat_routes.get_thread(42, api_key="test-api-key")

    assert result["thread_id"] == 42
    assert result["thread_config"] is None
