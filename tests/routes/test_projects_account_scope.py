from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.routes import projects as projects_routes
from tests.utils import get_test_user_id


def _patch_projects_db(monkeypatch, db: MagicMock) -> None:
    monkeypatch.setattr(projects_routes, "chatlog_db", db)


def _encode_owner(description: str, owner_user_id: str) -> str:
    return json.dumps(
        {
            "__codexify_project_owner__": True,
            "description": description,
            "owner_user_id": owner_user_id,
        },
        sort_keys=True,
    )


def test_single_user_create_and_list_preserve_legacy_behavior(monkeypatch):
    expected_user_id = get_test_user_id()
    db = MagicMock()
    db.list_projects.return_value = [
        {"id": 1, "name": "Imports", "description": "Legacy"},
        {"id": 2, "name": "General", "description": ""},
    ]
    db.create_project.return_value = 7
    _patch_projects_db(monkeypatch, db)

    created = projects_routes.create_project(
        projects_routes.ProjectCreate(
            name="New Project",
            description="Legacy description",
        ),
        request_user_scope=RequestUserScope(
            user_id=expected_user_id,
            account_id=expected_user_id,
            multi_user_enabled=False,
        ),
    )
    listed = projects_routes.list_projects(
        request_user_scope=RequestUserScope(
            user_id=expected_user_id,
            account_id=expected_user_id,
            multi_user_enabled=False,
        ),
    )

    assert created == {
        "id": 7,
        "name": "New Project",
        "description": "Legacy description",
    }
    assert listed == [
        {"id": 1, "name": "Imports", "description": "Legacy"},
        {
            "id": 2,
            "name": "General",
            "description": "Default project for content without a specified project",
        },
    ]
    db.create_project.assert_called_once_with(
        "New Project", "Legacy description"
    )


def test_multi_user_create_persists_authenticated_principal(monkeypatch):
    db = MagicMock()
    db.create_project.return_value = 11
    _patch_projects_db(monkeypatch, db)

    result = projects_routes.create_project(
        projects_routes.ProjectCreate(
            name="Owned Project",
            description="Scoped description",
        ),
        request_user_scope=RequestUserScope(
            user_id="owner-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
    )

    created_description = db.create_project.call_args.args[1]
    created_payload = json.loads(created_description)

    assert result == {
        "id": 11,
        "name": "Owned Project",
        "description": "Scoped description",
    }
    assert created_payload["__codexify_project_owner__"] is True
    assert created_payload["owner_user_id"] == "owner-a"
    assert created_payload["description"] == "Scoped description"


def test_multi_user_list_returns_only_owned_projects(monkeypatch):
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 1,
            "name": "Owned Project",
            "description": _encode_owner("Owned description", "owner-a"),
        },
        {
            "id": 2,
            "name": "Other Project",
            "description": _encode_owner("Other description", "owner-b"),
        },
        {"id": 3, "name": "Legacy Project", "description": "Legacy"},
    ]
    _patch_projects_db(monkeypatch, db)

    listed = projects_routes.list_projects(
        request_user_scope=RequestUserScope(
            user_id="owner-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
    )

    assert listed == [
        {
            "id": 1,
            "name": "Owned Project",
            "description": "Owned description",
        }
    ]


def test_multi_user_patch_rejects_cross_account_access(monkeypatch):
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 21,
            "name": "Other Project",
            "description": _encode_owner("Other description", "owner-b"),
        }
    ]
    _patch_projects_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        projects_routes.patch_project(
            21,
            {"name": "Blocked"},
            request_user_scope=RequestUserScope(
                user_id="owner-a",
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    db.update_project.assert_not_called()


def test_multi_user_delete_rejects_cross_account_access(monkeypatch):
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 31,
            "name": "Other Project",
            "description": _encode_owner("Other description", "owner-b"),
        }
    ]
    _patch_projects_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        projects_routes.delete_project_and_eject(
            31,
            request_user_scope=RequestUserScope(
                user_id="owner-a",
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    db.eject_threads_from_project.assert_not_called()
    db.delete_project.assert_not_called()


def test_multi_user_conflicting_user_id_is_rejected(monkeypatch):
    db = MagicMock()
    _patch_projects_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        projects_routes.create_project(
            projects_routes.ProjectCreate(
                name="Rejected Project",
                description="Scoped description",
                user_id="other-account",
            ),
            request_user_scope=RequestUserScope(
                user_id="owner-a",
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    db.create_project.assert_not_called()
