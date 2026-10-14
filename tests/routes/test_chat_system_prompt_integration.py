from unittest.mock import MagicMock

import pytest

from guardian.routes import chat
from guardian.core import chat_completion_service
from guardian.core import dependencies
from guardian.core.dependencies import RequestUserScope
from guardian.queue.turn_lock import build_turn_lock_envelope


@pytest.mark.asyncio
async def test_chat_complete_uses_single_system_message(monkeypatch):
    mock_db = MagicMock()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test",
        "project_id": None,
        "active_profile_id": None,
        "active_profile_revision": None,
    }
    mock_db.list_messages.return_value = [
        {"role": "user", "content": "Hello", "id": 1},
    ]
    mock_db.count_messages.return_value = 1
    mock_db.create_message.return_value = 2

    captured: dict[str, object] = {}

    monkeypatch.setattr(chat, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_completion_service,
        "acquire_turn_lock",
        lambda thread_id, owner, **kwargs: build_turn_lock_envelope(
            thread_id, owner, turn_id=kwargs.get("turn_id")
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "renew_turn_lock",
        lambda _thread_id, lock, **_kwargs: lock,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "enqueue",
        lambda task, queue_name: captured.update(
            {"task": task, "queue_name": queue_name}
        ),
    )
    monkeypatch.setattr(
        chat, "_get_task_completed_payload", lambda *_args, **_kwargs: None
    )
    request_body = chat.ChatCompletionRequest()
    response = await chat.chat_complete(
        1,
        request_body,
        api_key="test",
        request_id=None,
        request_user_scope=RequestUserScope(user_id="test", multi_user_enabled=False),
    )

    assert isinstance(response.get("task_id"), str)
    assert captured["queue_name"] == "codexify:queue:chat"
    assert getattr(captured["task"], "thread_id") == 1
    assert getattr(captured["task"], "turn_lock_owner") == response["task_id"]
