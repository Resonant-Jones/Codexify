"""Comprehensive tests for Guardian /projects/* API routes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


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


class TestProjectsDelete:
    """Tests for DELETE /projects/{project_id} endpoint."""

    def test_delete_project_success(self, test_client, mock_db):
        """Test successful project deletion returns 200."""
        response = test_client.delete("/api/projects/1")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        # Should eject threads first, then delete project
        mock_db.eject_threads_from_project.assert_called_once_with(1)
        mock_db.delete_project.assert_called_once_with(1)

    def test_delete_project_not_found(self, test_client, mock_db):
        """Test deleting non-existent project returns 404."""
        mock_db.delete_project.return_value = False

        response = test_client.delete("/api/projects/999")

        assert response.status_code == 404
        data = response.json()
        assert data["ok"] is False
        assert "error" in data

    def test_delete_project_ejects_threads_first(self, test_client, mock_db):
        """Test project deletion ejects threads before deleting."""
        response = test_client.delete("/api/projects/1")

        assert response.status_code == 200
        # Verify eject was called before delete
        assert mock_db.eject_threads_from_project.called
        assert mock_db.delete_project.called
        # Get call order
        calls = [(call[0], call[1]) for call in mock_db.method_calls]
        eject_call_index = next(
            i
            for i, (name, args) in enumerate(calls)
            if name == "eject_threads_from_project"
        )
        delete_call_index = next(
            i
            for i, (name, args) in enumerate(calls)
            if name == "delete_project"
        )
        assert eject_call_index < delete_call_index

    def test_delete_project_eject_error_continues(self, test_client, mock_db):
        """Test project deletion continues even if eject fails."""
        mock_db.eject_threads_from_project.side_effect = Exception(
            "Eject failed"
        )

        response = test_client.delete("/api/projects/1")

        # Should still attempt to delete project
        assert response.status_code == 200
        mock_db.delete_project.assert_called_once_with(1)

    def test_delete_project_db_error(self, test_client, mock_db):
        """Test project deletion handles database errors."""
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
        """Test deleting default project (Loose Threads, id=1)."""
        # This should work technically, but might have special handling
        response = test_client.delete("/api/projects/1")

        # If it succeeds, verify behavior
        if response.status_code == 200:
            mock_db.delete_project.assert_called_once_with(1)
        # If it fails, should be handled gracefully
        else:
            assert response.status_code in [400, 404, 403]


class TestProjectsIntegration:
    """Integration tests for projects endpoints."""

    def test_patch_then_delete_project(self, test_client, mock_db):
        """Test updating then deleting a project in sequence."""
        # First, patch the project
        patch_response = test_client.patch(
            "/api/projects/2", json={"name": "To Be Deleted"}
        )
        assert patch_response.status_code == 200

        # Then delete it
        delete_response = test_client.delete("/api/projects/2")
        assert delete_response.status_code == 200

        # Verify both operations were called
        mock_db.update_project.assert_called()
        mock_db.delete_project.assert_called()

    def test_multiple_project_operations(self, test_client, mock_db):
        """Test multiple project operations in sequence."""
        # Patch multiple projects
        for project_id in [1, 2, 3]:
            response = test_client.patch(
                f"/api/projects/{project_id}",
                json={"name": f"Project {project_id}"},
            )
            assert response.status_code == 200

        # Verify all updates were called
        assert mock_db.update_project.call_count == 3
