"""Shared test fixtures for Guardian API route tests."""

from __future__ import annotations

import os

# Force mock embeddings backend BEFORE any app imports to avoid loading model
os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set environment variables early to avoid /app/media creation and startup issues
os.environ.setdefault("STORAGE_BASE_PATH", "/tmp/test_media")
os.environ.setdefault("ENABLE_BLIP_MODEL", "false")
os.environ.setdefault("GUARDIAN_ENABLE_MONDREAM", "0")
os.environ.setdefault("ENABLE_CONNECTOR_WORKER", "0")


@pytest.fixture
def mock_db():
    """Mock database connection/session for testing."""
    mock = MagicMock()

    # Mock common database methods
    mock.create_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "title": "Test Thread",
        "summary": "Test summary",
        "project_id": 1,
        "project_name": "Imports",
        "last_interaction_at": "2025-11-09T12:00:00",
        "parent_id": None,
        "created_at": "2025-11-09T12:00:00",
        "updated_at": "2025-11-09T12:00:00",
        "archived_at": None,
    }

    mock.list_chat_threads.return_value = [
        {
            "id": 1,
            "user_id": "test_user",
            "title": "Test Thread",
            "summary": "Test summary",
            "project_id": 1,
            "project_name": "Imports",
            "last_interaction_at": "2025-11-09T12:00:00",
            "parent_id": None,
            "created_at": "2025-11-09T12:00:00",
            "updated_at": "2025-11-09T12:00:00",
            "archived_at": None,
        }
    ]

    mock.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "title": "Test Thread",
        "summary": "Test summary",
        "project_id": 1,
        "project_name": "Imports",
        "last_interaction_at": "2025-11-09T12:00:00",
        "parent_id": None,
        "created_at": "2025-11-09T12:00:00",
        "updated_at": "2025-11-09T12:00:00",
        "archived_at": None,
    }

    mock.create_message.return_value = 1
    mock.list_messages.return_value = [
        {
            "id": 1,
            "thread_id": 1,
            "role": "user",
            "content": "Test message",
            "created_at": "2025-11-09T12:00:00",
        }
    ]
    mock.count_messages.return_value = 1

    mock.delete_message.return_value = True
    mock.update_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "title": "Updated Thread",
        "summary": "Updated summary",
        "project_id": 1,
        "project_name": "Imports",
        "last_interaction_at": "2025-11-09T12:00:00",
        "parent_id": None,
        "created_at": "2025-11-09T12:00:00",
        "updated_at": "2025-11-09T12:00:00",
        "archived_at": None,
    }
    mock.delete_thread.return_value = True
    mock.archive_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "title": "Test Thread",
        "summary": "Test summary",
        "project_id": 1,
        "project_name": "Imports",
        "last_interaction_at": "2025-11-09T12:00:00",
        "parent_id": None,
        "created_at": "2025-11-09T12:00:00",
        "updated_at": "2025-11-09T12:00:00",
        "archived_at": "2025-11-09T12:30:00",
    }

    mock.update_project.return_value = True
    mock.delete_project.return_value = True
    mock.eject_threads_from_project.return_value = None
    mock.ensure_project.return_value = 1
    mock.ensure_default_project.return_value = 1

    mock.get_recent_thread.return_value = None
    mock.ensure_chat_thread.return_value = {
        "id": 1,
        "user_id": "test_user",
        "title": "Test Thread",
        "summary": "",
        "project_id": 1,
        "project_name": "Imports",
        "last_interaction_at": "2025-11-09T12:00:00",
        "parent_id": None,
        "created_at": "2025-11-09T12:00:00",
        "updated_at": "2025-11-09T12:00:00",
        "archived_at": None,
    }

    mock.write_audit_log.return_value = None
    mock.record_thread_move.return_value = {
        "id": 1,
        "thread_id": 1,
        "from_project_id": 1,
        "to_project_id": 2,
        "user_id": "test_user",
        "timestamp": "2025-11-09T12:00:00",
    }
    mock.list_projects.return_value = [
        {"id": 1, "name": "Imports"},
        {"id": 2, "name": "General"},
    ]

    # Memory-related mocks
    mock.list_memories.return_value = []
    mock.add_memory.return_value = {"id": 1, "content": "test"}
    mock.update_memory.return_value = True
    mock.delete_memory.return_value = True
    mock.query_memories.return_value = []

    return mock


@pytest.fixture
def mock_auth():
    """Mock authentication dependency."""
    return "test-api-key"


@pytest.fixture
def mock_require_api_key(mock_auth):
    """Mock the require_api_key dependency function."""

    def _mock_require_api_key(api_key: str = None):
        return mock_auth

    return _mock_require_api_key


@pytest.fixture
def mock_request_user_id():
    return "test_user"


@pytest.fixture
def sample_thread_data() -> dict[str, Any]:
    """Sample thread payload for testing."""
    return {
        "title": "Test Thread",
        "user_id": "test_user",
        "summary": "This is a test thread",
        "project_id": 1,
    }


@pytest.fixture
def sample_project_data() -> dict[str, Any]:
    """Sample project payload for testing."""
    return {
        "name": "Test Project",
        "description": "This is a test project",
    }


@pytest.fixture
def test_client(mock_db, mock_auth, monkeypatch, tmp_path):
    """Return FastAPI TestClient for the guardian_api app with mocked dependencies."""
    # Set environment variable to use temp directory instead of /app/media
    monkeypatch.setenv("STORAGE_BASE_PATH", str(tmp_path / "media"))

    # Patch logging to work around the bool formatting issue in guardian_api.py
    with patch("logging.info"):
        # Import the app here to avoid circular imports and ensure fresh state
        # Patch chatlog_db at all import locations to ensure proper mock isolation
        with patch("guardian.guardian_api.chatlog_db", mock_db):
            with patch("guardian.core.dependencies.chatlog_db", mock_db):
                with patch("guardian.routes.chat.chatlog_db", mock_db):
                    with patch("guardian.routes.projects.chatlog_db", mock_db):
                        with patch(
                            "guardian.routes.memory.chatlog_db", mock_db
                        ):
                            with patch(
                                "guardian.guardian_api.event_bus"
                            ) as mock_event_bus:
                                mock_event_bus.emit_event.return_value = None

                                from guardian.guardian_api import (
                                    app,
                                    require_api_key,
                                )

                                # Override the dependency injection for require_api_key
                                def mock_require_api_key_override():
                                    return mock_auth

                                app.dependency_overrides[
                                    require_api_key
                                ] = mock_require_api_key_override
                                from guardian.core.dependencies import (
                                    get_request_user_id,
                                )

                                app.dependency_overrides[
                                    get_request_user_id
                                ] = lambda: "test_user"

                                client = TestClient(app)
                                yield client

                                # Clean up dependency override
                                app.dependency_overrides.clear()


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    mock = MagicMock()
    mock.emit_event.return_value = None
    return mock


@pytest.fixture
def api_headers():
    """Return headers with API key for authenticated requests."""
    return {"X-API-Key": "test-api-key"}
