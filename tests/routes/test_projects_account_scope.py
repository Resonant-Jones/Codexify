from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.core.project_ownership import PROJECT_OWNERSHIP_AUTHORITY_CONFLICT
from guardian.routes import projects as projects_routes
from tests.utils import get_test_user_id


def _patch_projects_db(monkeypatch, db: MagicMock) -> None:
    monkeypatch.setattr(projects_routes, "chatlog_db", db)


def _scope(account_id: str, *, multi_user: bool = True) -> RequestUserScope:
    return RequestUserScope(
        user_id=account_id,
        account_id=account_id,
        multi_user_enabled=multi_user,
    )


def _legacy_envelope(description: str, owner_user_id: str) -> str:
    return json.dumps(
        {
            "__codexify_project_owner__": True,
            "description": description,
            "owner_user_id": owner_user_id,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def test_single_user_create_writes_plain_description_without_envelope(
    monkeypatch,
) -> None:
    expected_user_id = get_test_user_id()
    db = MagicMock()
    db.create_project.return_value = 7
    _patch_projects_db(monkeypatch, db)

    created = projects_routes.create_project(
        projects_routes.ProjectCreate(
            name="New Project",
            description="  Human description  ",
        ),
        request_user_scope=_scope(expected_user_id, multi_user=False),
    )

    assert created == {
        "id": 7,
        "name": "New Project",
        "description": "  Human description  ",
    }
    db.create_project.assert_called_once_with("New Project", "  Human description  ")
    persisted_description = db.create_project.call_args.args[1]
    assert "__codexify_project_owner__" not in persisted_description


def test_multi_user_create_persists_authenticated_owner_and_plain_description(
    monkeypatch,
) -> None:
    db = MagicMock()
    db.create_project.return_value = 11
    _patch_projects_db(monkeypatch, db)

    result = projects_routes.create_project(
        projects_routes.ProjectCreate(
            name="Owned Project",
            description="Scoped description",
        ),
        request_user_scope=_scope("owner-a"),
    )

    assert result == {
        "id": 11,
        "name": "Owned Project",
        "description": "Scoped description",
    }
    db.create_project.assert_called_once_with(
        "Owned Project", "Scoped description", user_id="owner-a"
    )
    assert "__codexify_project_owner__" not in db.create_project.call_args.args[1]


def test_multi_user_list_uses_only_canonical_column_and_suppresses_conflicts(
    monkeypatch,
) -> None:
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 1,
            "user_id": "owner-a",
            "name": "Canonical",
            "description": "Canonical description",
        },
        {
            "id": 2,
            "user_id": "owner-a",
            "name": "Matching Legacy",
            "description": _legacy_envelope("  Exact legacy description  ", "owner-a"),
        },
        {
            "id": 3,
            "user_id": "owner-b",
            "name": "Envelope Cannot Grant",
            "description": _legacy_envelope("Hidden", "owner-a"),
        },
        {
            "id": 4,
            "user_id": "owner-a",
            "name": "Envelope Cannot Override",
            "description": _legacy_envelope("Suppressed", "owner-b"),
        },
        {
            "id": 5,
            "user_id": "owner-b",
            "name": "Other Canonical",
            "description": "Other",
        },
    ]
    _patch_projects_db(monkeypatch, db)

    listed = projects_routes.list_projects(request_user_scope=_scope("owner-a"))

    assert listed == [
        {
            "id": 1,
            "user_id": "owner-a",
            "name": "Canonical",
            "description": "Canonical description",
        },
        {
            "id": 2,
            "user_id": "owner-a",
            "name": "Matching Legacy",
            "description": "  Exact legacy description  ",
        },
    ]


@pytest.mark.parametrize(
    ("canonical_owner", "embedded_owner"),
    (("owner-b", "owner-a"), ("owner-a", "owner-b")),
)
def test_direct_project_operation_fails_closed_on_any_owner_conflict(
    monkeypatch,
    canonical_owner: str,
    embedded_owner: str,
) -> None:
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 21,
            "user_id": canonical_owner,
            "name": "Conflicted Project",
            "description": _legacy_envelope("description", embedded_owner),
        }
    ]
    _patch_projects_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        projects_routes.patch_project(
            21,
            {"name": "Blocked"},
            request_user_scope=_scope("owner-a"),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == PROJECT_OWNERSHIP_AUTHORITY_CONFLICT
    db.update_project.assert_not_called()


def test_patch_authorization_uses_canonical_owner_and_writes_plain_text(
    monkeypatch,
) -> None:
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 22,
            "user_id": "owner-a",
            "name": "Owned Project",
            "description": _legacy_envelope("old description", "owner-a"),
        }
    ]
    _patch_projects_db(monkeypatch, db)

    result = projects_routes.patch_project(
        22,
        {"description": "  replacement text  "},
        request_user_scope=_scope("owner-a"),
    )

    assert result == {"ok": True}
    db.update_project.assert_called_once_with(
        22,
        name=None,
        description="  replacement text  ",
    )
    persisted = db.update_project.call_args.kwargs["description"]
    assert "__codexify_project_owner__" not in persisted


def test_patch_rejects_different_canonical_owner_even_without_envelope(
    monkeypatch,
) -> None:
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 23,
            "user_id": "owner-b",
            "name": "Other Project",
            "description": "ordinary",
        }
    ]
    _patch_projects_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        projects_routes.patch_project(
            23,
            {"name": "Blocked"},
            request_user_scope=_scope("owner-a"),
        )

    assert exc_info.value.status_code == 403
    db.update_project.assert_not_called()


def test_delete_rejects_different_canonical_owner(monkeypatch) -> None:
    db = MagicMock()
    db.list_projects.return_value = [
        {
            "id": 31,
            "user_id": "owner-b",
            "name": "Other Project",
            "description": _legacy_envelope("description", "owner-b"),
        }
    ]
    _patch_projects_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        projects_routes.delete_project_and_eject(
            31,
            request_user_scope=_scope("owner-a"),
        )

    assert exc_info.value.status_code == 403
    db.delete_project.assert_not_called()


def test_multi_user_conflicting_client_user_id_is_rejected(monkeypatch) -> None:
    db = MagicMock()
    _patch_projects_db(monkeypatch, db)

    with pytest.raises(HTTPException) as exc_info:
        projects_routes.create_project(
            projects_routes.ProjectCreate(
                name="Rejected Project",
                description="Scoped description",
                user_id="other-account",
            ),
            request_user_scope=_scope("owner-a"),
        )

    assert exc_info.value.status_code == 403
    db.create_project.assert_not_called()
