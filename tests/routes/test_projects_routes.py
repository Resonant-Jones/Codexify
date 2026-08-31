"""Comprehensive tests for Guardian /projects/* API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope
from guardian.routes import projects as projects_routes


@pytest.fixture
def test_client(mock_db, mock_auth, monkeypatch):
    monkeypatch.setattr(projects_routes, "chatlog_db", mock_db)
    app = FastAPI()
    app.dependency_overrides[
        projects_routes.require_api_key
    ] = lambda: mock_auth
    app.dependency_overrides[
        projects_routes.get_request_user_scope
    ] = lambda: RequestUserScope(user_id="local", multi_user_enabled=False)
    app.include_router(projects_routes.router)
    app.include_router(projects_routes.api_router)
    return TestClient(app, headers={"X-API-Key": "test-api-key"})


class TestProjectsPatch:
    """Tests for PATCH /projects/{project_id} endpoint."""

    def test_patch_project_name_success(self, test_client, mock_db):
        """Test successful project name update returns 200."""
        payload = {"name": "Updated Project Name"}

        response = test_client.patch("/api/projects/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        mock_db.update_project.assert_called_once_with(
            1, name="Updated Project Name", description=None
        )

    def test_patch_project_description_success(self, test_client, mock_db):
        """Test successful project description update returns 200."""
        payload = {"description": "Updated project description"}

        response = test_client.patch("/api/projects/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        mock_db.update_project.assert_called_once_with(
            1, name=None, description="Updated project description"
        )

    def test_patch_project_both_fields(self, test_client, mock_db):
        """Test updating both name and description simultaneously."""
        payload = {"name": "New Name", "description": "New description"}

        response = test_client.patch("/api/projects/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        mock_db.update_project.assert_called_once_with(
            1, name="New Name", description="New description"
        )

    def test_patch_project_empty_payload(self, test_client, mock_db):
        """Test patching project with empty payload still succeeds."""
        payload = {}

        response = test_client.patch("/api/projects/1", json=payload)

        assert response.status_code == 200
        # Should call update_project with None values
        mock_db.update_project.assert_called_once_with(
            1, name=None, description=None
        )

    def test_patch_project_db_error(self, test_client, mock_db):
        """Test project patch handles database errors gracefully."""
        mock_db.update_project.side_effect = Exception(
            "Database constraint violation"
        )

        payload = {"name": "New Name"}
        response = test_client.patch("/api/projects/1", json=payload)

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert "error" in data

    def test_patch_project_invalid_id(self, test_client, mock_db):
        """Test patching project with invalid ID type."""
        # FastAPI should handle path parameter validation
        response = test_client.patch(
            "/api/projects/invalid", json={"name": "Test"}
        )

        # FastAPI returns 422 for validation errors
        assert response.status_code == 422

    def test_patch_project_null_name(self, test_client, mock_db):
        """Test patching project with null name."""
        payload = {"name": None}

        response = test_client.patch("/api/projects/1", json=payload)

        assert response.status_code == 200
        mock_db.update_project.assert_called_once_with(
            1, name=None, description=None
        )

    def test_patch_project_empty_string_name(self, test_client, mock_db):
        """Test patching project with empty string name."""
        payload = {"name": ""}

        response = test_client.patch("/api/projects/1", json=payload)

        assert response.status_code == 200
        # Empty string should be passed as-is
        mock_db.update_project.assert_called_once_with(
            1, name="", description=None
        )


class TestProjectsCreate:
    """Tests for POST /api/projects endpoint."""

    def test_create_project_success_on_api_route(self, test_client, mock_db):
        """Test successful project creation returns 200 on the mounted API route."""
        mock_db.create_project.return_value = 7

        response = test_client.post(
            "/api/projects",
            json={"name": "New Project", "description": ""},
        )

        assert response.status_code == 200
        assert response.json() == {
            "id": 7,
            "name": "New Project",
            "description": "",
        }
        mock_db.create_project.assert_called_once_with("New Project", "")

    def test_create_project_success_on_legacy_route_alias(
        self, test_client, mock_db
    ):
        """Test successful project creation also works on the mounted /projects alias."""
        mock_db.create_project.return_value = 8

        response = test_client.post(
            "/projects",
            json={"name": "Dashboard Project", "description": ""},
        )

        assert response.status_code == 200
        assert response.json() == {
            "id": 8,
            "name": "Dashboard Project",
            "description": "",
        }
        mock_db.create_project.assert_called_once_with("Dashboard Project", "")


class TestProjectsDelete:
    """Tests for DELETE /projects/{project_id} endpoint."""

    def test_delete_project_success(self, test_client, mock_db):
        """Test successful project deletion returns 200."""
        mock_db.list_projects.return_value = [
            {
                "id": 1,
                "name": "Archived project",
                "system_role": None,
                "archived_at": "2026-08-30T12:00:00+00:00",
            }
        ]
        response = test_client.delete("/api/projects/1")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        mock_db.eject_threads_from_project.assert_not_called()
        mock_db.delete_project.assert_called_once_with(1)

    def test_delete_project_not_found(self, test_client, mock_db):
        """Test deleting non-existent project returns 404."""
        response = test_client.delete("/api/projects/999")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_delete_active_project_is_rejected_before_ejection(self, test_client, mock_db):
        """Test active project deletion is rejected without route-side ejection."""
        mock_db.list_projects.return_value = [
            {
                "id": 1,
                "name": "Active project",
                "system_role": None,
                "archived_at": None,
            }
        ]
        response = test_client.delete("/api/projects/1")

        assert response.status_code == 409
        assert response.json()["error"] == "project_must_be_archived_before_delete"
        mock_db.eject_threads_from_project.assert_not_called()
        mock_db.delete_project.assert_not_called()

    def test_delete_project_does_not_use_route_side_ejection(self, test_client, mock_db):
        """Test core owns transactional ejection after lifecycle validation."""
        mock_db.list_projects.return_value = [
            {
                "id": 1,
                "name": "Archived project",
                "system_role": None,
                "archived_at": "2026-08-30T12:00:00+00:00",
            }
        ]

        response = test_client.delete("/api/projects/1")

        assert response.status_code == 200
        mock_db.eject_threads_from_project.assert_not_called()
        mock_db.delete_project.assert_called_once_with(1)

    def test_delete_project_db_error(self, test_client, mock_db):
        """Test project deletion handles database errors."""
        mock_db.list_projects.return_value = [
            {
                "id": 1,
                "name": "Archived project",
                "system_role": None,
                "archived_at": "2026-08-30T12:00:00+00:00",
            }
        ]
        mock_db.delete_project.side_effect = Exception("Foreign key constraint")

        response = test_client.delete("/api/projects/1")

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert "error" in data

    def test_delete_project_invalid_id(self, test_client, mock_db):
        """Test deleting project with invalid ID type."""
        response = test_client.delete("/api/projects/invalid")

        # FastAPI returns 422 for path parameter validation errors
        assert response.status_code == 422

    def test_delete_default_project(self, test_client, mock_db):
        """Test deleting the Imports built-in is rejected."""
        mock_db.list_projects.return_value = [
            {
                "id": 1,
                "name": "Imported history",
                "system_role": "imports",
                "archived_at": None,
            }
        ]
        response = test_client.delete("/api/projects/1")

        assert response.status_code == 409
        assert response.json()["error"] == "project_system_container_immutable"
        mock_db.delete_project.assert_not_called()


class TestProjectsIntegration:
    """Integration tests for projects endpoints."""

    def test_patch_archive_then_delete_project(self, test_client, mock_db):
        """Test renaming, archiving, then deleting a project in sequence."""
        # First, patch the project
        patch_response = test_client.patch(
            "/api/projects/2", json={"name": "To Be Deleted"}
        )
        assert patch_response.status_code == 200

        archive_response = test_client.patch(
            "/api/projects/2", json={"archived": True}
        )
        assert archive_response.status_code == 200
        mock_db.list_projects.return_value = [
            {
                "id": 2,
                "name": "To Be Deleted",
                "system_role": None,
                "archived_at": "2026-08-30T12:00:00+00:00",
            }
        ]

        delete_response = test_client.delete("/api/projects/2")
        assert delete_response.status_code == 200

        # Verify all lifecycle operations were called.
        mock_db.update_project.assert_called()
        mock_db.archive_project.assert_called_once_with(2, True)
        mock_db.delete_project.assert_called()

    def test_multiple_project_operations(self, test_client, mock_db):
        """Test multiple project operations in sequence."""
        mock_db.list_projects.return_value.append(
            {"id": 3, "name": "Project 3", "user_id": "local"}
        )
        # Patch multiple projects
        for project_id in [1, 2, 3]:
            response = test_client.patch(
                f"/api/projects/{project_id}",
                json={"name": f"Project {project_id}"},
            )
            assert response.status_code == 200

        # Verify all updates were called
        assert mock_db.update_project.call_count == 3
