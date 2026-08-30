from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope
from guardian.routes import projects as projects_routes


PROJECTS = [
    {
        "id": 1,
        "name": "Home",
        "user_id": "local",
        "system_role": "general",
        "archived_at": None,
    },
    {
        "id": 2,
        "name": "Imported history",
        "user_id": "local",
        "system_role": "imports",
        "archived_at": None,
    },
    {
        "id": 3,
        "name": "Active work",
        "user_id": "local",
        "system_role": None,
        "archived_at": None,
    },
    {
        "id": 4,
        "name": "Old work",
        "user_id": "local",
        "system_role": None,
        "archived_at": "2026-08-30T12:00:00+00:00",
    },
]


@pytest.fixture
def lifecycle_client(monkeypatch):
    database = MagicMock()
    database.list_projects.return_value = PROJECTS
    database.delete_project.return_value = True
    monkeypatch.setattr(projects_routes, "chatlog_db", database)

    app = FastAPI()
    app.dependency_overrides[projects_routes.require_api_key] = lambda: "test"
    app.dependency_overrides[
        projects_routes.get_request_user_scope
    ] = lambda: RequestUserScope(user_id="local", multi_user_enabled=False)
    app.include_router(projects_routes.api_router)
    return TestClient(app), database


def test_project_list_exposes_durable_lifecycle_fields(lifecycle_client) -> None:
    client, _ = lifecycle_client

    response = client.get("/api/projects")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Home"
    assert response.json()[0]["system_role"] == "general"
    assert response.json()[3]["archived_at"] == "2026-08-30T12:00:00+00:00"


def test_patch_archives_and_restores_ordinary_project(lifecycle_client) -> None:
    client, database = lifecycle_client

    archived = client.patch("/api/projects/3", json={"archived": True})
    restored = client.patch("/api/projects/3", json={"archived": False})

    assert archived.status_code == 200
    assert restored.status_code == 200
    assert database.archive_project.call_args_list == [
        ((3, True), {}),
        ((3, False), {}),
    ]


@pytest.mark.parametrize("project_id", [1, 2])
def test_built_in_projects_can_rename_but_cannot_archive(
    lifecycle_client, project_id: int
) -> None:
    client, database = lifecycle_client

    renamed = client.patch(
        f"/api/projects/{project_id}", json={"name": "Renamed container"}
    )
    assert renamed.status_code == 200
    for archived in (True, False):
        rejected = client.patch(
            f"/api/projects/{project_id}", json={"archived": archived}
        )
        assert rejected.status_code == 409
        assert rejected.json()["error"] == "project_system_container_immutable"
    database.archive_project.assert_not_called()


def test_delete_rejects_active_project_without_ejecting_threads(
    lifecycle_client,
) -> None:
    client, database = lifecycle_client

    response = client.delete("/api/projects/3")

    assert response.status_code == 409
    assert response.json()["error"] == "project_must_be_archived_before_delete"
    database.delete_project.assert_not_called()
    database.eject_threads_from_project.assert_not_called()


@pytest.mark.parametrize("project_id", [1, 2])
def test_delete_rejects_built_in_projects(lifecycle_client, project_id: int) -> None:
    client, database = lifecycle_client

    response = client.delete(f"/api/projects/{project_id}")

    assert response.status_code == 409
    assert response.json()["error"] == "project_system_container_immutable"
    database.delete_project.assert_not_called()
    database.eject_threads_from_project.assert_not_called()


def test_delete_allows_only_archived_ordinary_project(lifecycle_client) -> None:
    client, database = lifecycle_client

    response = client.delete("/api/projects/4")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    database.delete_project.assert_called_once_with(4)
    database.eject_threads_from_project.assert_not_called()
