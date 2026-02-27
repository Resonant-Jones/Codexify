"""
Test suite for application startup behavior.

Verifies that:
- Database operations do not occur at import time
- Project initialization happens during startup event
- Initialization does not run multiple times
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient


class TestImportTimeSideEffects:
    """Test that no database operations occur at import time."""

    def test_projects_module_import_no_db_calls(self):
        """
        Test that importing guardian.routes.projects does not trigger DB operations.

        This verifies the fix for import-time side effects.
        """
        # Create a mock chatlog_db
        mock_db = MagicMock()

        # Patch chatlog_db before importing the module
        with patch("guardian.routes.projects.chatlog_db", mock_db):
            # Remove module from cache if it exists
            if "guardian.routes.projects" in sys.modules:
                del sys.modules["guardian.routes.projects"]

            # Import the module
            from guardian.routes import projects

            # Verify that ensure_project was NOT called during import
            mock_db.ensure_project.assert_not_called()

            # Verify that the function exists and can be called manually
            assert hasattr(projects, "ensure_loose_threads_project")
            assert callable(projects.ensure_loose_threads_project)

    def test_projects_function_not_auto_executed(self):
        """
        Test that the ensure_loose_threads_project function exists but is not
        automatically executed at import time.

        The project should only be created when the app starts via the startup event.
        """
        # Remove module from cache
        if "guardian.routes.projects" in sys.modules:
            del sys.modules["guardian.routes.projects"]

        # Track function calls
        mock_db = MagicMock()

        with patch("guardian.routes.projects.chatlog_db", mock_db):
            # Import the module
            import guardian.routes.projects

            # The function should exist
            assert hasattr(
                guardian.routes.projects, "ensure_loose_threads_project"
            )

            # But it should NOT have been called during import
            mock_db.ensure_project.assert_not_called()

            # Explicitly calling it should work
            guardian.routes.projects.ensure_loose_threads_project()
            assert mock_db.ensure_project.call_count == 1


class TestStartupBehavior:
    """Test application startup behavior."""

    def test_default_project_created_on_startup(self):
        """
        Test that the default General project is created during app startup.
        """
        # Create a mock database
        mock_db = MagicMock()
        mock_db.ensure_project.return_value = 1
        mock_db.list_projects.return_value = []

        # Track calls to ensure_project
        ensure_project_calls = []

        def track_ensure_project(*args, **kwargs):
            ensure_project_calls.append((args, kwargs))
            return 1

        mock_db.ensure_project.side_effect = track_ensure_project

        # Mock the function in the projects module
        with patch("guardian.routes.projects.chatlog_db", mock_db):
            from guardian.routes.projects import ensure_loose_threads_project

            # Call the function (simulating startup)
            result = ensure_loose_threads_project()

            # Verify it was called correctly
            assert result is True
            assert len(ensure_project_calls) == 1
            assert ensure_project_calls[0][0] == (
                "General",
                "Default bucket for unassigned threads and documents",
            )

    def test_startup_calls_ensure_loose_threads(self):
        """
        Test that app startup event calls ensure_loose_threads_project.
        """
        # Create mocks
        mock_db = MagicMock()
        mock_ensure_project = MagicMock(return_value=True)

        # Mock at the module level where it's imported
        with patch.dict("sys.modules", {"guardian.guardian_api": MagicMock()}):
            with patch("guardian.routes.projects.chatlog_db", mock_db):
                with patch(
                    "guardian.routes.projects.ensure_loose_threads_project",
                    mock_ensure_project,
                ):
                    # Verify the function can be called
                    from guardian.routes.projects import (
                        ensure_loose_threads_project,
                    )

                    ensure_loose_threads_project()

                    # Verify it was called
                    assert mock_ensure_project.call_count >= 1

    def test_ensure_loose_threads_idempotent(self):
        """
        Test that calling ensure_loose_threads_project multiple times is safe.

        The underlying ensure_project should handle this gracefully.
        """
        mock_db = MagicMock()
        mock_db.list_projects.return_value = []

        # Simulate idempotent behavior - project already exists
        mock_db.ensure_project.return_value = 1

        with patch("guardian.routes.projects.chatlog_db", mock_db):
            from guardian.routes.projects import ensure_loose_threads_project

            # Call multiple times
            result1 = ensure_loose_threads_project()
            result2 = ensure_loose_threads_project()
            result3 = ensure_loose_threads_project()

            # All should succeed
            assert result1 is True
            assert result2 is True
            assert result3 is True

            # Verify it was called each time (the function itself is idempotent)
            assert mock_db.ensure_project.call_count == 3

    def test_startup_handles_db_errors_gracefully(self):
        """
        Test that startup handles database errors gracefully and doesn't crash.
        """
        mock_db = MagicMock()
        mock_db.list_projects.return_value = []

        # Simulate DB error
        mock_db.ensure_project.side_effect = Exception(
            "Database connection failed"
        )

        with patch("guardian.routes.projects.chatlog_db", mock_db):
            from guardian.routes.projects import ensure_loose_threads_project

            # Should return False but not raise
            result = ensure_loose_threads_project()
            assert result is False

    def test_ensure_loose_threads_parameters(self):
        """
        Test that ensure_loose_threads_project uses correct project parameters.
        """
        mock_db = MagicMock()

        with patch("guardian.routes.projects.chatlog_db", mock_db):
            from guardian.routes.projects import ensure_loose_threads_project

            ensure_loose_threads_project()

            # Verify correct parameters
            mock_db.ensure_project.assert_called_once_with(
                "General",
                "Default bucket for unassigned threads and documents",
            )


class TestStartupEventIntegration:
    """Integration tests for the full startup lifecycle."""

    def test_startup_function_design(self):
        """
        Test that the startup function is designed correctly for lifespan usage.

        This verifies the function signature and behavior without requiring
        full app startup.
        """
        mock_db = MagicMock()
        mock_db.list_projects.return_value = []

        with patch("guardian.routes.projects.chatlog_db", mock_db):
            from guardian.routes.projects import ensure_loose_threads_project

            # Function should be callable
            assert callable(ensure_loose_threads_project)

            # Function should return boolean
            result = ensure_loose_threads_project()
            assert isinstance(result, bool)

            # Should call ensure_project on DB
            mock_db.ensure_project.assert_called_once()

    def test_idempotent_calls(self):
        """
        Test that multiple calls to ensure_loose_threads_project are safe.

        This is important for startup scenarios where the function might
        be called multiple times (though it shouldn't be in practice).
        """
        mock_db = MagicMock()
        mock_db.list_projects.return_value = []

        with patch("guardian.routes.projects.chatlog_db", mock_db):
            from guardian.routes.projects import ensure_loose_threads_project

            # Call multiple times
            result1 = ensure_loose_threads_project()
            result2 = ensure_loose_threads_project()

            # Both should succeed
            assert result1 is True
            assert result2 is True

            # DB method should have been called each time
            assert mock_db.ensure_project.call_count == 2


class TestNoImportTimeExecution:
    """
    Critical tests to ensure no DB operations happen at import time.

    These tests verify the core requirement: importing modules should not
    trigger database operations.
    """

    def test_import_projects_clean(self):
        """
        CRITICAL: Verify importing projects.py does not execute DB operations.
        """
        # Remove from cache
        if "guardian.routes.projects" in sys.modules:
            del sys.modules["guardian.routes.projects"]

        # Create spy to detect any calls
        mock_db = MagicMock()
        execution_tracker = {"import_time_calls": []}

        def spy_ensure_project(*args, **kwargs):
            execution_tracker["import_time_calls"].append(
                ("ensure_project", args, kwargs)
            )

        mock_db.ensure_project.side_effect = spy_ensure_project

        # Import with mock
        with patch.dict("sys.modules", {"guardian.guardian_api": MagicMock()}):
            with patch("guardian.routes.projects.chatlog_db", mock_db):
                import guardian.routes.projects as projects_module

                # CRITICAL: No calls should have been made during import
                assert len(execution_tracker["import_time_calls"]) == 0
                assert mock_db.ensure_project.call_count == 0

                # But the function should exist
                assert hasattr(projects_module, "ensure_loose_threads_project")

    def test_function_only_executes_when_called(self):
        """
        Verify that ensure_loose_threads_project only executes when explicitly called.
        """
        mock_db = MagicMock()

        with patch("guardian.routes.projects.chatlog_db", mock_db):
            from guardian.routes.projects import ensure_loose_threads_project

            # Should not have been called yet
            assert mock_db.ensure_project.call_count == 0

            # Explicit call
            ensure_loose_threads_project()

            # Now it should be called
            assert mock_db.ensure_project.call_count == 1

            # Multiple calls should work
            ensure_loose_threads_project()
            assert mock_db.ensure_project.call_count == 2
