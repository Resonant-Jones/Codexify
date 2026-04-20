from __future__ import annotations

from unittest.mock import MagicMock

from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat as chat_routes
from guardian.routes import projects as projects_routes
from tests.utils import get_test_user_id


def _create_project(monkeypatch, expected_user_id: str) -> dict[str, object]:
    db = MagicMock()
    db.create_project.return_value = 17
    monkeypatch.setattr(projects_routes, "chatlog_db", db)

    result = projects_routes.create_project(
        projects_routes.ProjectCreate(
            name="Owned Project",
            description="Ownership check",
        ),
        request_user_scope=RequestUserScope(
            user_id=expected_user_id,
            account_id=expected_user_id,
            multi_user_enabled=True,
        ),
    )
    return {
        "id": result["id"],
        "user_id": db.create_project.call_args.kwargs["user_id"],
    }


def _create_thread(
    monkeypatch, expected_user_id: str, project_id: int
) -> dict[str, object]:
    db = MagicMock()
    db.get_recent_thread.return_value = None
    db.create_chat_thread.return_value = {
        "id": 23,
        "user_id": expected_user_id,
        "title": "Owned Thread",
        "summary": "",
        "project_id": project_id,
    }
    db.write_audit_log.return_value = None
    db.ensure_default_project.return_value = project_id
    monkeypatch.setattr(chat_routes, "chatlog_db", db)

    result = chat_routes.chat_create_thread(
        {"title": "Owned Thread", "project_id": project_id},
        api_key="test-api-key",
        request_user_scope=RequestUserScope(
            user_id=expected_user_id,
            account_id=expected_user_id,
            multi_user_enabled=True,
        ),
    )
    return {
        "id": result["id"],
        "user_id": db.create_chat_thread.call_args.kwargs["user_id"],
    }


def test_entities_share_same_user(monkeypatch):
    user_id = get_test_user_id()
    project = _create_project(monkeypatch, user_id)
    thread = _create_thread(monkeypatch, user_id, int(project["id"]))

    assert project["user_id"] == user_id
    assert thread["user_id"] == user_id
    assert project["user_id"] == thread["user_id"]
