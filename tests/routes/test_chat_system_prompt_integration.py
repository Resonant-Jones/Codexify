import pytest
from unittest.mock import MagicMock, patch

from guardian.routes import chat


@pytest.mark.asyncio
async def test_chat_complete_uses_single_system_message():
    mock_db = MagicMock()
    mock_db.get_chat_thread.return_value = {"id": 1, "user_id": "test", "project_id": None}
    mock_db.list_messages.return_value = [
        {"role": "user", "content": "Hello", "id": 1},
    ]
    mock_db.count_messages.return_value = 1
    mock_db.create_message.return_value = 2

    async def fake_complete(*args, **kwargs):
        return "assistant-response"

    fake_context_broker = MagicMock()
    fake_context_broker.return_value = None

    with patch.object(chat, "chatlog_db", mock_db):
        with patch.object(chat, "ContextBroker", lambda *args, **kwargs: MagicMock(assemble=lambda *a, **k: (None, None))):
            groq_mock = MagicMock(return_value="assistant")
            with patch.object(chat, "_groq_complete", groq_mock):
                with patch.object(
                    chat,
                    "build_guardian_system_prompt",
                    return_value=("SYS_PROMPT", {"total_chars": 10, "estimated_tokens": 3, "docs_count": 0}),
                ):
                    response = await chat.chat_complete(1, {})

    assert response["message"]["role"] == "assistant"
    assert response["prompt_meta"]["system_prompt"]["char_length"] >= 10
    args, _ = groq_mock.call_args
    messages = args[0]
    system_messages = [m for m in messages if m.get("role") == "system"]
    assert len(system_messages) == 1
    assert system_messages[0]["content"] == "SYS_PROMPT"
