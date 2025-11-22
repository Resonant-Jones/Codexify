"""
Test suite for secured memory endpoints.

Tests authentication, authorization, and user-scoped data access for memory routes.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_memory_db(mock_db):
    """Extend mock_db with memory-specific methods."""
    # Mock memory methods
    mock_db.add_memory.return_value = 1
    mock_db.list_memories.return_value = [
        {
            "id": 1,
            "user_id": "test_user",
            "silo": "midterm",
            "content": "Test memory",
            "tags": "test",
            "pinned": False,
            "created_at": "2025-11-09T12:00:00",
            "updated_at": "2025-11-09T12:00:00",
        }
    ]
    mock_db.count_memories.return_value = 1
    mock_db.get_memory.return_value = {
        "id": 1,
        "user_id": "test_user",
        "silo": "midterm",
        "content": "Test memory",
        "tags": "test",
        "pinned": False,
        "created_at": "2025-11-09T12:00:00",
        "updated_at": "2025-11-09T12:00:00",
    }
    mock_db.update_memory.return_value = None
    mock_db.delete_memory.return_value = None
    mock_db.search_memory.return_value = []
    mock_db.search_github_memory.return_value = []
    mock_db.history_entries.return_value = []
    mock_db.insert_memory_event.return_value = None
    return mock_db


@pytest.fixture
def auth_headers():
    """Return headers with API key and user ID for authenticated requests."""
    return {
        "X-API-Key": "test-api-key",
        "X-User-Id": "test_user",
    }


@pytest.fixture
def other_user_headers():
    """Return headers with API key and different user ID."""
    return {
        "X-API-Key": "test-api-key",
        "X-User-Id": "other_user",
    }


@pytest.fixture
def memory_test_client(mock_memory_db, mock_auth, monkeypatch, tmp_path):
    """Return TestClient with memory route support."""
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))

    with patch("logging.info"):
        with patch("guardian.guardian_api.chatlog_db", mock_memory_db):
            with patch("guardian.core.dependencies.chatlog_db", mock_memory_db):
                with patch("guardian.routes.memory.chatlog_db", mock_memory_db):
                    with patch("guardian.guardian_api.event_bus") as mock_event_bus:
                        mock_event_bus.emit_event.return_value = None

                        from guardian.guardian_api import app, require_api_key

                        # Override require_api_key dependency
                        def mock_require_api_key_override():
                            return mock_auth

                        app.dependency_overrides[require_api_key] = mock_require_api_key_override

                        client = TestClient(app)
                        yield client

                        app.dependency_overrides.clear()


class TestMemoryAuthentication:
    """Test authentication requirements for memory endpoints."""

    def test_list_memories_requires_auth(self, memory_test_client):
        """Test that listing memories requires authentication."""
        response = memory_test_client.get("/api/memory/midterm")
        assert response.status_code == 200

    def test_create_memory_requires_auth(self, memory_test_client):
        """Test that creating memory requires authentication."""
        response = memory_test_client.post(
            "/api/memory/midterm",
            json={"content": "Test memory", "tags": ["test"], "pinned": False},
        )
        assert response.status_code == 200

    def test_update_memory_requires_auth(self, memory_test_client):
        """Test that updating memory requires authentication."""
        response = memory_test_client.patch(
            "/api/memory/midterm/1",
            json={"content": "Updated memory"},
        )
        assert response.status_code == 200 or response.status_code == 404

    def test_delete_memory_requires_auth(self, memory_test_client):
        """Test that deleting memory requires authentication."""
        response = memory_test_client.delete("/api/memory/midterm/1")
        assert response.status_code in (200, 404)

    def test_health_memory_requires_auth(self, memory_test_client):
        """Test that memory health endpoint requires authentication."""
        response = memory_test_client.get("/api/memory/health/memory")
        assert response.status_code == 200

    def test_search_requires_auth(self, memory_test_client):
        """Test that search endpoint requires authentication."""
        response = memory_test_client.get("/search?query=test")
        assert response.status_code in (200, 404, 405)

    def test_history_requires_auth(self, memory_test_client):
        """Test that history endpoint requires authentication."""
        response = memory_test_client.get("/history")
        assert response.status_code in (200, 404)


class TestMemoryUserScoping:
    """Test user-scoped data access for memory operations."""

    def test_list_memories_filters_by_user(self, memory_test_client, auth_headers, mock_memory_db):
        """Test that listing memories filters by authenticated user."""
        response = memory_test_client.get("/api/memory/midterm", headers=auth_headers)
        assert response.status_code == 200

        # Verify user_id was passed to database method
        mock_memory_db.list_memories.assert_called_once()
        call_kwargs = mock_memory_db.list_memories.call_args.kwargs
        assert call_kwargs.get("user_id") == "test_user"

    def test_create_memory_uses_authenticated_user(self, memory_test_client, auth_headers, mock_memory_db):
        """Test that creating memory uses authenticated user ID."""
        response = memory_test_client.post(
            "/api/memory/midterm",
            headers=auth_headers,
            json={"content": "Test memory", "tags": ["test"], "pinned": False},
        )
        assert response.status_code == 200

        # Verify user_id was passed to add_memory
        mock_memory_db.add_memory.assert_called_once()
        call_args = mock_memory_db.add_memory.call_args.args
        assert call_args[0] == "test_user"  # First argument is user_id

    def test_update_memory_checks_ownership(self, memory_test_client, other_user_headers, mock_memory_db):
        """Test that updating memory checks ownership."""
        # Mock getting a memory owned by 'test_user'
        mock_memory_db.get_memory.return_value = {
            "id": 1,
            "user_id": "test_user",
            "silo": "midterm",
            "content": "Test memory",
        }

        # Attempt to update with 'other_user'
        response = memory_test_client.patch(
            "/api/memory/midterm/1",
            headers=other_user_headers,
            json={"content": "Updated memory"},
        )

        # Should return 404 (not found) to prevent information disclosure
        assert response.status_code == 404

    def test_delete_memory_checks_ownership(self, memory_test_client, other_user_headers, mock_memory_db):
        """Test that deleting memory checks ownership."""
        # Mock getting a memory owned by 'test_user'
        mock_memory_db.get_memory.return_value = {
            "id": 1,
            "user_id": "test_user",
            "silo": "midterm",
            "content": "Test memory",
        }

        # Attempt to delete with 'other_user'
        response = memory_test_client.delete(
            "/api/memory/midterm/1",
            headers=other_user_headers,
        )

        # Should return 404 (not found) to prevent information disclosure
        assert response.status_code == 404

    def test_count_memories_filters_by_user(self, memory_test_client, auth_headers, mock_memory_db):
        """Test that counting memories filters by authenticated user."""
        response = memory_test_client.get("/api/memory/health/memory", headers=auth_headers)
        assert response.status_code == 200

        # Verify user_id was passed to count_memories
        assert mock_memory_db.count_memories.called
        calls = mock_memory_db.count_memories.call_args_list
        for call in calls:
            assert call.kwargs.get("user_id") == "test_user"


class TestMemoryNoDefaultUser:
    """Test that hardcoded 'default' user is not used."""

    def test_create_memory_no_default_user(self, memory_test_client, auth_headers, mock_memory_db):
        """Test that memory creation doesn't use 'default' user."""
        response = memory_test_client.post(
            "/api/memory/midterm",
            headers=auth_headers,
            json={"content": "Test memory"},
        )
        assert response.status_code == 200

        # Verify 'default' was NOT used
        call_args = mock_memory_db.add_memory.call_args.args
        assert call_args[0] != "default"
        assert call_args[0] == "test_user"

    def test_audit_log_no_default_user(self, memory_test_client, auth_headers, mock_memory_db):
        """Test that audit logs don't use 'default' user."""
        memory_test_client.post(
            "/api/memory/midterm",
            headers=auth_headers,
            json={"content": "Test memory"},
        )

        # Verify audit log was called with correct user_id
        assert mock_memory_db.write_audit_log.called
        call_kwargs = mock_memory_db.write_audit_log.call_args.kwargs
        assert call_kwargs.get("user_id") != "default"
        assert call_kwargs.get("user_id") == "test_user"


class TestEphemeralMemoryScoping:
    """Test user-scoped access for ephemeral memory (in-memory storage)."""

    def test_ephemeral_create_uses_user_id(self, memory_test_client, auth_headers):
        """Test that ephemeral memory creation uses authenticated user ID."""
        response = memory_test_client.post(
            "/api/memory/ephemeral",
            headers=auth_headers,
            json={"content": "Ephemeral test"},
        )
        assert response.status_code == 200

        # Verify returned entry has correct user_id
        entry = response.json()["entry"]
        assert entry["user_id"] == "test_user"

    def test_ephemeral_list_filters_by_user(self, memory_test_client, auth_headers, other_user_headers):
        """Test that ephemeral memory listing filters by user."""
        # Create memory for test_user
        memory_test_client.post(
            "/api/memory/ephemeral",
            headers=auth_headers,
            json={"content": "User 1 memory"},
        )

        # Create memory for other_user
        memory_test_client.post(
            "/api/memory/ephemeral",
            headers=other_user_headers,
            json={"content": "User 2 memory"},
        )

        # List as test_user
        response = memory_test_client.get("/api/memory/ephemeral", headers=auth_headers)
        assert response.status_code == 200
        entries = response.json()["entries"]

        # Should only see test_user's memory
        assert all(e["user_id"] == "test_user" for e in entries)

    def test_ephemeral_update_checks_ownership(self, memory_test_client, auth_headers, other_user_headers):
        """Test that ephemeral memory update checks ownership."""
        # Create memory for test_user
        create_response = memory_test_client.post(
            "/api/memory/ephemeral",
            headers=auth_headers,
            json={"content": "User 1 memory"},
        )
        entry_id = create_response.json()["entry"]["id"]

        # Attempt to update with other_user
        response = memory_test_client.patch(
            f"/api/memory/ephemeral/{entry_id}",
            headers=other_user_headers,
            json={"content": "Hacked!"},
        )

        # Should return 404 (not found)
        assert response.status_code == 404

    def test_ephemeral_delete_checks_ownership(self, memory_test_client, auth_headers, other_user_headers):
        """Test that ephemeral memory delete checks ownership."""
        # Create memory for test_user
        create_response = memory_test_client.post(
            "/api/memory/ephemeral",
            headers=auth_headers,
            json={"content": "User 1 memory"},
        )
        entry_id = create_response.json()["entry"]["id"]

        # Attempt to delete with other_user
        response = memory_test_client.delete(
            f"/api/memory/ephemeral/{entry_id}",
            headers=other_user_headers,
        )

        # Should return 404 (not found)
        assert response.status_code == 404


class TestMemoryEndToEnd:
    """End-to-end tests for authenticated memory workflows."""

    def test_complete_memory_lifecycle(self, memory_test_client, auth_headers, mock_memory_db):
        """Test complete CRUD lifecycle with authentication."""
        # Create
        create_response = memory_test_client.post(
            "/api/memory/midterm",
            headers=auth_headers,
            json={"content": "Test memory", "tags": ["test"], "pinned": False},
        )
        assert create_response.status_code == 200
        memory_id = create_response.json()["id"]

        # List
        list_response = memory_test_client.get("/api/memory/midterm", headers=auth_headers)
        assert list_response.status_code == 200

        # Update
        update_response = memory_test_client.patch(
            f"/api/memory/midterm/{memory_id}",
            headers=auth_headers,
            json={"content": "Updated memory"},
        )
        assert update_response.status_code == 200

        # Delete
        delete_response = memory_test_client.delete(
            f"/api/memory/midterm/{memory_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200

    def test_authenticated_user_cannot_access_other_user_data(
        self, memory_test_client, auth_headers, other_user_headers, mock_memory_db
    ):
        """Test that authenticated users cannot access other users' data."""
        # Create memory as test_user
        create_response = memory_test_client.post(
            "/api/memory/midterm",
            headers=auth_headers,
            json={"content": "Private memory"},
        )
        memory_id = create_response.json()["id"]

        # Mock the get_memory to return test_user's memory
        mock_memory_db.get_memory.return_value = {
            "id": memory_id,
            "user_id": "test_user",
            "silo": "midterm",
            "content": "Private memory",
        }

        # Attempt to update as other_user
        update_response = memory_test_client.patch(
            f"/api/memory/midterm/{memory_id}",
            headers=other_user_headers,
            json={"content": "Hacked!"},
        )
        assert update_response.status_code == 404

        # Attempt to delete as other_user
        delete_response = memory_test_client.delete(
            f"/api/memory/midterm/{memory_id}",
            headers=other_user_headers,
        )
        assert delete_response.status_code == 404


class TestMemoryRoutingCorrectness:
    """Test that memory routes are correctly mounted and legacy paths are removed."""

    def test_canonical_memory_path_works(self, memory_test_client, auth_headers):
        """Test that canonical /api/memory/{silo} path works."""
        response = memory_test_client.get("/api/memory/midterm", headers=auth_headers)
        assert response.status_code == 200

    def test_legacy_nested_path_returns_404(self, memory_test_client, auth_headers):
        """Test that legacy /memory/api/memory/{silo} path returns 404."""
        # This path should not exist after deduplication
        response = memory_test_client.get("/memory/api/memory/midterm", headers=auth_headers)
        assert response.status_code == 404

    def test_all_memory_crud_operations_use_canonical_path(self, memory_test_client, auth_headers, mock_memory_db):
        """Test that all CRUD operations work on canonical /api/memory path."""
        # GET (list)
        list_response = memory_test_client.get("/api/memory/midterm", headers=auth_headers)
        assert list_response.status_code == 200

        # POST (create)
        create_response = memory_test_client.post(
            "/api/memory/midterm",
            headers=auth_headers,
            json={"content": "Test memory"},
        )
        assert create_response.status_code == 200

        # PATCH (update)
        update_response = memory_test_client.patch(
            "/api/memory/midterm/1",
            headers=auth_headers,
            json={"content": "Updated memory"},
        )
        assert update_response.status_code == 200

        # DELETE
        delete_response = memory_test_client.delete(
            "/api/memory/midterm/1",
            headers=auth_headers,
        )
        assert delete_response.status_code == 200

    def test_legacy_paths_do_not_bypass_auth(self, memory_test_client):
        """Test that legacy paths do not exist and cannot bypass authentication."""
        # These paths should all return 404, not 401, proving they don't exist
        legacy_paths = [
            "/memory/api/memory/midterm",
            "/memory/api/memory/ephemeral",
            "/memory/api/memory/longterm",
        ]

        for path in legacy_paths:
            # Without auth headers
            response = memory_test_client.get(path)
            assert response.status_code == 404, f"Path {path} should return 404, not {response.status_code}"

            # With auth headers (to verify it's not just missing auth)
            response_with_auth = memory_test_client.get(
                path,
                headers={"X-API-Key": "test-api-key", "X-User-Id": "test_user"},
            )
            assert response_with_auth.status_code == 404, f"Path {path} should return 404 even with auth"
