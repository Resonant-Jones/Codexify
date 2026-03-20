from __future__ import annotations

import logging
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
from guardian.queue import task_events
from guardian.routes import chat
from guardian.workers import chat_worker


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


def test_chat_worker_safe_publish_keeps_success_semantics(monkeypatch, caplog):
    published: list[tuple[str, dict[str, object]]] = []

    monkeypatch.setattr(task_events, "publish", lambda *_a, **_k: "1-0")
    monkeypatch.setattr(
        chat_worker,
        "_safe_emit_live_event",
        lambda event_type, payload: published.append(
            (event_type, dict(payload))
        ),
    )

    with caplog.at_level(logging.WARNING):
        result = chat_worker._safe_publish(
            "task-1",
            "task.running",
            {"step": 1},
        )

    assert result["ok"] is True
    assert result["visibility_scope"] == "progress"
    assert result["terminal_visibility"] is False
    assert result["execution_continued"] is True
    assert result["event_id"] == "1-0"
    assert published == [("task.running", {"step": 1, "task_id": "task-1"})]
    assert not any(
        record.levelno >= logging.WARNING for record in caplog.records
    )


def test_chat_worker_safe_publish_surfaces_progress_failure(
    monkeypatch, caplog
):
    def _raise_publish(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(task_events, "publish", _raise_publish)
    monkeypatch.setattr(
        chat_worker,
        "_safe_emit_live_event",
        lambda *_args, **_kwargs: None,
    )

    with caplog.at_level(logging.WARNING):
        result = chat_worker._safe_publish(
            "task-2",
            "task.progress",
            {"token": "x"},
        )

    assert result["ok"] is False
    assert result["visibility_scope"] == "progress"
    assert result["terminal_visibility"] is False
    assert result["execution_continued"] is True
    assert result["failure_class"] == "RuntimeError"
    assert any(
        "task_event_visibility_degraded" in record.message
        and "visibility_scope=progress" in record.message
        for record in caplog.records
    )


def test_chat_worker_safe_publish_surfaces_terminal_failure(
    monkeypatch, caplog
):
    def _raise_publish(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(task_events, "publish", _raise_publish)
    monkeypatch.setattr(
        chat_worker,
        "_safe_emit_live_event",
        lambda *_args, **_kwargs: None,
    )

    with caplog.at_level(logging.ERROR):
        result = chat_worker._safe_publish(
            "task-3",
            "task.completed",
            {"message_id": 77},
        )

    assert result["ok"] is False
    assert result["visibility_scope"] == "terminal"
    assert result["terminal_visibility"] is True
    assert result["execution_continued"] is True
    assert result["failure_class"] == "RuntimeError"
    assert any(
        record.levelno >= logging.ERROR
        and "task_event_visibility_degraded" in record.message
        and "visibility_scope=terminal" in record.message
        for record in caplog.records
    )
