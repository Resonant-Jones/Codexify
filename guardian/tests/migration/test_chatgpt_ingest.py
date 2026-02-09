import json
from unittest.mock import MagicMock

import pytest

from backend.rag import chatgpt_migration
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

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    mock_db.create_chat_thread.assert_called_once()
    # ensure messages persisted with correct thread id
    mock_db.create_message.assert_any_call(42, "user", "Hello")
    mock_db.create_message.assert_any_call(42, "assistant", "Hi there")


def test_ingest_rejects_shared_conversations_metadata(monkeypatch):
    mock_db = MagicMock()
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)

    metadata_only = [
        {
            "id": "meta_1",
            "conversation_id": "conversation_1",
            "title": "Shared thread",
            "is_anonymous": False,
        }
    ]

    with pytest.raises(ValueError, match="shared_conversations"):
        ingest_chatgpt_export(
            json.dumps(metadata_only).encode("utf-8"), user_id="tester"
        )


def test_ingest_rejects_html_payload(monkeypatch):
    mock_db = MagicMock()
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)

    with pytest.raises(ValueError, match="appears to be HTML"):
        ingest_chatgpt_export(
            b"<html><body>archive</body></html>", user_id="tester"
        )


def test_ingest_tags_imported_messages_with_origin_and_era(monkeypatch):
    mock_db = MagicMock()
    mock_db.create_chat_thread.return_value = {"id": 42}
    mock_db.create_message.return_value = 1

    captured_meta = []

    def capture_temporal_meta(
        chatlog_db, message_id, merged_meta, source_created_at
    ):
        captured_meta.append(dict(merged_meta))

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        capture_temporal_meta,
    )

    export = [
        {
            "id": "t1",
            "title": "Archival Import",
            "mapping": {
                "m1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Hello"]},
                        "create_time": 1,
                    }
                }
            },
        }
    ]

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"), user_id="tester"
    )

    assert stats["messages_imported"] == 1
    assert captured_meta
    assert captured_meta[0]["origin"] == "chatgpt_import"
    assert captured_meta[0]["era"] == "pre_codexify"
