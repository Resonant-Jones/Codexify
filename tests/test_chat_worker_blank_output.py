from unittest.mock import MagicMock

from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_worker


def test_worker_replaces_blank_output(monkeypatch):
    mock_db = MagicMock()
    mock_db.create_message.return_value = 123
    mock_db.write_audit_log = MagicMock()

    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat_worker, "_safe_publish", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        chat_worker, "_embed_message", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        chat_worker, "is_cancelled", lambda *args, **kwargs: False
    )
    monkeypatch.setattr(
        chat_worker, "clear_cancelled", lambda *args, **kwargs: None
    )

    async def fake_build_messages(_task):
        return [], "groq", "model", {}, None, None

    monkeypatch.setattr(
        chat_worker, "_build_messages_for_llm", fake_build_messages
    )
    monkeypatch.setattr(chat_worker, "chat_with_ai", lambda *args, **kwargs: "")

    task = ChatCompletionTask(thread_id=1, provider="groq", model="model")
    chat_worker._run_chat_task(task)

    args, _kwargs = mock_db.create_message.call_args
    assert args[0] == 1
    assert args[1] == "assistant"
    assert args[2].strip() != ""
