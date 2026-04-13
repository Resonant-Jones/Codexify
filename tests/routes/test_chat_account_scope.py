from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes


def _patch_chat_db(monkeypatch, db: MagicMock) -> None:
    monkeypatch.setattr(chat_routes, "chatlog_db", db)


def test_single_user_create_thread_keeps_legacy_owner_hint(monkeypatch):
    db = MagicMock()
    db.get_recent_thread.return_value = None
    db.create_chat_thread.return_value = {
        "id": 11,
        "user_id": "legacy-user",
        "title": "Legacy",
        "summary": "",
        "project_id": 7,
    }
    db.write_audit_log.return_value = None
    db.ensure_default_project.return_value = 7

    _patch_chat_db(monkeypatch, db)

    result = chat_routes.chat_create_thread(
        {"title": "Legacy", "user_id": "legacy-user"},
        api_key="test-api-key",
        request_user_scope=RequestUserScope(
            account_id="local",
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert result["thread"]["user_id"] == "legacy-user"
    assert db.create_chat_thread.call_args.kwargs["user_id"] == "legacy-user"


def test_multi_user_create_thread_rejects_conflicting_user_id(monkeypatch):
    db = MagicMock()
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.chat_create_thread(
            {"title": "Rejected", "user_id": "other-account"},
            api_key="test-api-key",
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    db.create_chat_thread.assert_not_called()


def test_multi_user_message_list_returns_owned_thread_data(monkeypatch):
    db = MagicMock()
    db.get_chat_thread.return_value = {
        "id": 21,
        "user_id": "owner-a",
        "project_id": 7,
        "archived_at": None,
    }
    db.list_messages.return_value = [
        {
            "id": 1,
            "thread_id": 21,
            "role": "user",
            "content": "Owned thread message",
        }
    ]
    db.count_messages.return_value = 1
    _patch_chat_db(monkeypatch, db)

    response = chat_routes.chat_list_messages(
        21,
        api_key="test-api-key",
        request_user_scope=RequestUserScope(
            account_id="owner-a",
            multi_user_enabled=True,
        ),
    )

    assert response["ok"] is True
    assert response["messages"][0]["content"] == "Owned thread message"
    assert db.list_messages.call_args.args[0] == 21


def test_multi_user_message_post_rejects_cross_account_thread(monkeypatch):
    db = MagicMock()
    db.get_chat_thread.return_value = {
        "id": 31,
        "user_id": "owner-b",
        "project_id": 7,
        "archived_at": None,
    }
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.chat_post_message(
            31,
            {"role": "user", "content": "Hello", "user_id": "owner-a"},
            api_key="test-api-key",
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    db.create_message.assert_not_called()


@pytest.mark.asyncio
async def test_multi_user_completion_rejects_other_principal_thread(
    monkeypatch,
):
    db = MagicMock()
    db.get_chat_thread.return_value = {
        "id": 41,
        "user_id": "owner-b",
        "project_id": 7,
        "archived_at": None,
    }
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        await chat_routes.chat_complete(
            41,
            chat_routes.ChatCompletionRequest(),
            request=None,
            api_key="test-api-key",
            request_id=None,
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403


def test_multi_user_debug_posture_rejects_other_principal_thread(monkeypatch):
    db = MagicMock()
    db.get_chat_thread.return_value = {
        "id": 51,
        "user_id": "owner-b",
        "project_id": 7,
        "archived_at": None,
    }
    _patch_chat_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        chat_routes.get_latest_retrieval_posture(
            51,
            api_key="test-api-key",
            request_user_scope=RequestUserScope(
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
