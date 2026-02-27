from unittest.mock import MagicMock, patch

import pytest

from guardian.routes import chat


@pytest.mark.asyncio
async def test_chat_complete_uses_single_system_message():
    mock_db = MagicMock()
    mock_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test",
        "project_id": None,
    }
    mock_db.list_messages.return_value = [
        {"role": "user", "content": "Hello", "id": 1},
    ]
    mock_db.count_messages.return_value = 1
    mock_db.create_message.return_value = 2

    captured: dict[str, object] = {}

    with patch.object(chat, "chatlog_db", mock_db):
        with patch.object(chat, "acquire_turn_lock", return_value=True):
            with patch.object(
                chat,
                "enqueue",
                side_effect=lambda task, queue_name: captured.update(
                    {"task": task, "queue_name": queue_name}
                ),
            ):
                request_body = chat.ChatCompletionRequest()
                response = await chat.chat_complete(1, request_body)

    assert isinstance(response.get("task_id"), str)
    assert captured["queue_name"] == "codexify:queue:chat"
    assert getattr(captured["task"], "thread_id") == 1
    assert getattr(captured["task"], "turn_lock_owner") == response["task_id"]
