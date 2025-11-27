import json
from unittest.mock import MagicMock

from backend.rag.chatgpt_migration import ingest_chatgpt_export
from guardian.core import dependencies


def test_ingest_chatgpt_export_creates_threads_and_messages(monkeypatch):
    """Integration-style check that ingest_chatgpt_export processes a minimal export."""
    mock_db = MagicMock()
    mock_db.create_chat_thread.return_value = {"id": 42}
    message_ids = iter([1, 2])

    def fake_create_message(thread_id, role, content):
        return next(message_ids)

    mock_db.create_message.side_effect = fake_create_message

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)

    export = [
        {
            "id": "t1",
            "title": "Test Conversation",
            "mapping": {
                "m1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Hello"]},
                        "create_time": 1,
                    }
                },
                "m2": {
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["Hi there"]},
                        "create_time": 2,
                    }
                },
            },
        }
    ]

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"), user_id="tester"
    )

    assert stats["threads"] == 1
    assert stats["messages"] == 2
    mock_db.create_chat_thread.assert_called_once()
    # ensure messages persisted with correct thread id
    mock_db.create_message.assert_any_call(42, "user", "Hello")
    mock_db.create_message.assert_any_call(42, "assistant", "Hi there")
