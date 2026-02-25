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

<<<<<<< HEAD
    with patch.object(chat, "chatlog_db", mock_db), patch.object(
        chat,
        "ContextBroker",
        lambda *args, **kwargs: MagicMock(
            assemble=lambda *a, **k: (None, None)
        ),
    ):
        groq_mock = MagicMock(return_value="assistant")
        with patch.object(chat, "_groq_complete", groq_mock), patch.object(
            chat,
            "build_guardian_system_prompt",
            return_value=(
                "SYS_PROMPT",
                {
                    "total_chars": 10,
                    "estimated_tokens": 3,
                    "docs_count": 0,
                },
            ),
        ):
            request_body = chat.ChatCompletionRequest()
            response = await chat.chat_complete(1, request_body)

    # Route may enqueue (async) or return a sync assistant message.
    if "task_id" in response:
        assert isinstance(response["task_id"], str)
        assert response["task_id"].strip()
        assert groq_mock.call_count == 0
    else:
        assert response["message"]["role"] == "assistant"
        assert response["prompt_meta"]["system_prompt"]["char_length"] >= 10
        args, _ = groq_mock.call_args
        messages = args[0]
        system_messages = [m for m in messages if m.get("role") == "system"]
        assert len(system_messages) == 1
        assert system_messages[0]["content"] == "SYS_PROMPT"
=======
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
>>>>>>> 4e6eeb9b (feat(voice): add turn-based voice task pipeline and cached playback)
