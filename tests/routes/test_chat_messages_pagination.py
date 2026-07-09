"""Tests for chat message transcript pagination (before_message_id cursor + has_more)."""

from __future__ import annotations

from unittest.mock import MagicMock

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes


def _patch_chat_db(monkeypatch, db: MagicMock) -> None:
    monkeypatch.setattr(chat_routes, "chatlog_db", db)


def _make_chat_db() -> MagicMock:
    db = MagicMock()
    db.get_chat_thread.return_value = {"id": 1, "user_id": "tester"}
    return db


def _make_message(id: int, content: str = "") -> dict:
    return {
        "id": id,
        "thread_id": 1,
        "role": "user" if id % 2 == 1 else "assistant",
        "content": content or f"message-{id}",
        "event_at": f"2026-01-01T00:{id:02d}:00.000Z",
        "kind": None,
        "extra_meta": None,
        "created_at": f"2026-01-01T00:{id:02d}:00.000Z",
    }


def _scope():
    return RequestUserScope(
        user_id="tester", account_id="tester", multi_user_enabled=False
    )


class TestChatMessagesPagination:
    def test_latest_page_returns_has_more(self, monkeypatch):
        """When the thread has more messages than limit, has_more is true."""
        db = _make_chat_db()
        db.list_messages.return_value = [
            _make_message(i) for i in range(75, 100)
        ]
        db.count_messages.return_value = 150
        _patch_chat_db(monkeypatch, db)

        response = chat_routes.chat_list_messages(
            thread_id=1,
            limit=25,
            offset=0,
            api_key="test-key",
            request_user_scope=_scope(),
        )

        assert response["ok"] is True
        assert response["has_more"] is True
        assert response["total"] == 150
        assert len(response["messages"]) == 25

    def test_latest_page_no_more_when_total_equals_page(self, monkeypatch):
        """When limit >= total, has_more is false."""
        db = _make_chat_db()
        db.list_messages.return_value = [_make_message(i) for i in range(1, 6)]
        db.count_messages.return_value = 5
        _patch_chat_db(monkeypatch, db)

        response = chat_routes.chat_list_messages(
            thread_id=1,
            limit=50,
            offset=0,
            api_key="test-key",
            request_user_scope=_scope(),
        )

        assert response["ok"] is True
        assert response["has_more"] is False
        assert len(response["messages"]) == 5

    def test_before_message_id_returns_older_messages(self, monkeypatch):
        """Cursor-based pagination returns messages older than the cursor."""
        db = _make_chat_db()
        db.list_messages.return_value = [
            _make_message(i, f"older-{i}") for i in range(1, 6)
        ]
        db.count_messages.return_value = 30
        _patch_chat_db(monkeypatch, db)

        response = chat_routes.chat_list_messages(
            thread_id=1,
            limit=10,
            offset=0,
            before_message_id=11,
            api_key="test-key",
            request_user_scope=_scope(),
        )

        assert response["ok"] is True
        assert len(response["messages"]) == 5
        call_args = db.list_messages.call_args
        assert call_args.kwargs.get("before_message_id") == 11
        assert call_args.kwargs.get("limit") == 10

    def test_before_message_id_passes_cursor_to_db(self, monkeypatch):
        """before_message_id is forwarded to chatlog_db.list_messages."""
        db = _make_chat_db()
        db.list_messages.return_value = [_make_message(5)]
        db.count_messages.return_value = 10
        _patch_chat_db(monkeypatch, db)

        chat_routes.chat_list_messages(
            thread_id=1,
            limit=20,
            offset=0,
            before_message_id=50,
            api_key="test-key",
            request_user_scope=_scope(),
        )

        call_kwargs = db.list_messages.call_args.kwargs
        assert call_kwargs["before_message_id"] == 50

    def test_before_message_id_omitted_when_none(self, monkeypatch):
        """When before_message_id is not provided, it is not passed to the DB."""
        db = _make_chat_db()
        db.list_messages.return_value = [_make_message(1)]
        db.count_messages.return_value = 1
        _patch_chat_db(monkeypatch, db)

        chat_routes.chat_list_messages(
            thread_id=1,
            limit=10,
            offset=0,
            api_key="test-key",
            request_user_scope=_scope(),
        )

        call_kwargs = db.list_messages.call_args.kwargs
        assert "before_message_id" not in call_kwargs

    def test_messages_are_returned_chronologically(self, monkeypatch):
        """Ordering is preserved — messages appear in event_at / id order."""
        db = _make_chat_db()
        ordered = [
            _make_message(3, "third"),
            _make_message(5, "fifth"),
            _make_message(7, "seventh"),
        ]
        db.list_messages.return_value = ordered
        db.count_messages.return_value = 3
        _patch_chat_db(monkeypatch, db)

        response = chat_routes.chat_list_messages(
            thread_id=1,
            api_key="test-key",
            request_user_scope=_scope(),
        )

        ids = [m["id"] for m in response["messages"]]
        assert ids == [3, 5, 7]

    def test_empty_thread_has_more_false(self, monkeypatch):
        """Empty thread returns has_more=false and no messages."""
        db = _make_chat_db()
        db.list_messages.return_value = []
        db.count_messages.return_value = 0
        _patch_chat_db(monkeypatch, db)

        response = chat_routes.chat_list_messages(
            thread_id=1,
            api_key="test-key",
            request_user_scope=_scope(),
        )

        assert response["ok"] is True
        assert response["has_more"] is False
        assert response["total"] == 0
        assert response["messages"] == []
