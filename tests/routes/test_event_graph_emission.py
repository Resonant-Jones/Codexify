from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.core.event_graph import (
    _set_session_factory,
    get_event_writer,
    reset_event_writer,
)
from guardian.db.models import Base, EventGraphEvent
from guardian.routes import chat


def _setup_event_graph_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine, tables=[EventGraphEvent.__table__])
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    _set_session_factory(Session)
    reset_event_writer()


def test_chat_post_message_emits_thread_update_event(monkeypatch):
    _setup_event_graph_session()
    mock_db = MagicMock()
    mock_db.ensure_project.return_value = None
    mock_db.ensure_chat_thread.return_value = None
    mock_db.create_message.return_value = 55
    mock_db.write_audit_log.return_value = None
    mock_db.get_chat_thread.return_value = {"id": 1, "title": "Existing"}

    monkeypatch.setattr(chat, "chatlog_db", mock_db)
    monkeypatch.setattr(
        chat,
        "event_bus",
        SimpleNamespace(emit_event=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(chat, "acquire_turn_lock", lambda *a, **k: True)
    monkeypatch.setattr(chat, "release_turn_lock", lambda *a, **k: None)
    monkeypatch.setattr(chat, "_embed_message", lambda *a, **k: None)

    response = chat.chat_post_message(
        1,
        {"role": "user", "content": "hello", "user_id": "u1"},
        api_key="test-key",
    )
    assert response["ok"] is True

    event = get_event_writer().get_event_by_idempotency(
        "thread.update:1:message:55"
    )
    assert event is not None
    assert event.event_type == "thread.update"
    assert event.thread_id == 1
    assert event.payload_json.get("message_id") == 55
