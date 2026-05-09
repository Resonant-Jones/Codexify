from __future__ import annotations

from unittest.mock import MagicMock

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes
from guardian.routes import projects as projects_routes


def _patch_chat_db(monkeypatch, db: MagicMock) -> None:
    monkeypatch.setattr(chat_routes, "chatlog_db", db)


def _patch_projects_db(monkeypatch, db: MagicMock) -> None:
    monkeypatch.setattr(projects_routes, "chatlog_db", db)


def test_chat_create_thread_does_not_depend_on_session_request_helper(
    monkeypatch,
):
    db = MagicMock()
    db.get_recent_thread.return_value = None
    db.create_chat_thread.return_value = {
        "id": 11,
        "user_id": "bearer-owner",
        "title": "Legacy",
        "summary": "",
        "project_id": 7,
    }
    db.write_audit_log.return_value = None
    db.ensure_default_project.return_value = 7

    _patch_chat_db(monkeypatch, db)
    monkeypatch.setattr(
        chat_routes,
        "get_current_user_id",
        lambda _request: (_ for _ in ()).throw(
            AssertionError("get_current_user_id should not be used here")
        ),
    )

    result = chat_routes.chat_create_thread(
        {"title": "Legacy", "user_id": "bearer-owner"},
        api_key="test-api-key",
        request=object(),
        request_user_scope=RequestUserScope(
            user_id="bearer-owner",
            account_id="bearer-owner",
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert result["thread"]["user_id"] == "bearer-owner"
    assert db.get_recent_thread.call_args.args[0] == "bearer-owner"


def test_project_create_does_not_depend_on_session_request_helper(
    monkeypatch,
):
    db = MagicMock()
    db.create_project.return_value = 17
    _patch_projects_db(monkeypatch, db)
    monkeypatch.setattr(
        projects_routes,
        "get_current_user_id",
        lambda _request: (_ for _ in ()).throw(
            AssertionError("get_current_user_id should not be used here")
        ),
    )

    result = projects_routes.create_project(
        projects_routes.ProjectCreate(
            name="Bearer Owned",
            description="Scoped description",
            user_id="bearer-owner",
        ),
        request=object(),
        request_user_scope=RequestUserScope(
            user_id="bearer-owner",
            account_id="bearer-owner",
            multi_user_enabled=False,
        ),
    )

    assert result == {
        "id": 17,
        "name": "Bearer Owned",
        "description": "Scoped description",
    }
    assert db.create_project.call_args.args[:2] == (
        "Bearer Owned",
        "Scoped description",
    )
