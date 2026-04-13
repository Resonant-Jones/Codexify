from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes


def _patch_chat_db(monkeypatch, db: MagicMock) -> None:
    monkeypatch.setattr(chat_routes, "chatlog_db", db)


def test_thread_list_scopes_to_account_in_multi_user_mode(monkeypatch):
    db = MagicMock()
    db.list_threads.return_value = [
        {
            "id": 101,
            "user_id": "owner-a",
            "title": "Owned thread",
        }
    ]
    _patch_chat_db(monkeypatch, db)

    response = chat_routes.list_threads(
        user_id=None,
        project_id=None,
        api_key="test-api-key",
        request_user_scope=RequestUserScope(
            account_id="owner-a",
            multi_user_enabled=True,
        ),
    )

    assert response == {"threads": db.list_threads.return_value}
    assert db.list_threads.call_args.kwargs["user_id"] == "owner-a"


def test_thread_list_rejects_conflicting_user_filter(monkeypatch):
    db = MagicMock()
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.list_threads(
            user_id="owner-b",
            project_id=None,
            api_key="test-api-key",
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    db.list_threads.assert_not_called()


def test_thread_read_rejects_other_account(monkeypatch):
    db = MagicMock()
    db.get_chat_thread.return_value = {
        "id": 201,
        "user_id": "owner-b",
        "title": "Foreign thread",
        "project_id": 7,
        "archived_at": None,
    }
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.get_thread(
            201,
            api_key="test-api-key",
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403


def test_child_threads_rejects_other_account(monkeypatch):
    db = MagicMock()
    db.get_chat_thread.return_value = {
        "id": 301,
        "user_id": "owner-b",
        "title": "Foreign parent",
        "project_id": 7,
        "archived_at": None,
    }
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.get_child_threads(
            301,
            api_key="test-api-key",
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403


def test_thread_summary_rejects_other_account(monkeypatch):
    db = MagicMock()
    db.get_chat_thread.return_value = {
        "id": 401,
        "user_id": "owner-b",
        "title": "Foreign parent",
        "project_id": 7,
        "archived_at": None,
    }
    db.get_thread_summary.return_value = "summary"
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.get_thread_summary(
            401,
            api_key="test-api-key",
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
