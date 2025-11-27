"""Unit tests for document autosave functionality.

Tests cover:
- Successful autosave creation
- Autosave update on duplicate thread
- Event emission
- Validation errors
- Thread not found errors
- EventBus integration
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import HTTPException

from guardian.routes import documents


class TestAutosaveCreation:
    """Tests for creating new autosave documents."""

    @patch("guardian.routes.documents.models")
    @patch("guardian.routes.documents.uuid.uuid4")
    @patch("guardian.routes.documents.event_bus.emit_event")
    def test_autosave_success(self, mock_emit, mock_uuid, mock_models, mock_db):
        """Test successful autosave creation returns 200 with document_id."""
        # Setup
        mock_uuid.return_value = uuid.UUID(
            "12345678-1234-5678-1234-567812345678"
        )
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 1
        mock_thread.user_id = "test_user"
        mock_thread.title = "Test Thread"
        mock_thread.project_id = 1

        # Setup query chain
        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = (
            mock_thread
        )

        mock_thread_doc_query = MagicMock()
        mock_thread_doc_query.filter_by.return_value.first.return_value = None

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()

        # Query returns different results based on model type
        def query_side_effect(model):
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            elif model == mock_models.ThreadDocument:
                return mock_thread_doc_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        # Configure documents router
        documents.configure_db(mock_db)

        # Execute
        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=1, content="Session notes content")

        # Run async function in sync context
        import asyncio

        result = asyncio.run(autosave_document(request))

        # Verify
        assert result["ok"] is True
        assert result["document_id"] == "12345678-1234-5678-1234-567812345678"
        assert result["relation"] == "autosave"

        # Verify document was created
        assert mock_session.add.call_count == 2  # Document + Link
        mock_session.commit.assert_called_once()

        # Verify event was emitted
        mock_emit.assert_called_once_with(
            topic="document.autosave",
            payload={
                "thread_id": 1,
                "document_id": "12345678-1234-5678-1234-567812345678",
            },
        )

    @patch("guardian.routes.documents.models")
    @patch("guardian.routes.documents.uuid.uuid4")
    @patch("guardian.routes.documents.event_bus.emit_event")
    def test_autosave_update_existing(
        self, mock_emit, mock_uuid, mock_models, mock_db
    ):
        """Test autosave updates existing document instead of creating new one."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        existing_doc_id = "existing-doc-id"

        # Mock thread
        mock_thread = MagicMock()
        mock_thread.id = 1
        mock_thread.user_id = "test_user"
        mock_thread.title = "Test Thread"
        mock_thread.project_id = 1

        # Mock existing autosave link
        mock_link = MagicMock()
        mock_link.id = 1
        mock_link.thread_id = 1
        mock_link.document_id = existing_doc_id
        mock_link.relation = "autosave"

        # Mock existing document
        mock_document = MagicMock()
        mock_document.id = existing_doc_id
        mock_document.title = "Old title"
        mock_document.content = "Old content"

        # Setup query chains
        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = (
            mock_thread
        )

        mock_thread_doc_query = MagicMock()
        mock_thread_doc_query.filter_by.return_value.first.return_value = (
            mock_link
        )

        mock_gen_doc_query = MagicMock()
        mock_gen_doc_query.filter_by.return_value.first.return_value = (
            mock_document
        )

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()

        # Query returns different results based on model type
        def query_side_effect(model):
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            elif model == mock_models.ThreadDocument:
                return mock_thread_doc_query
            elif model == mock_models.GeneratedDocument:
                return mock_gen_doc_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        # Configure documents router
        documents.configure_db(mock_db)

        # Execute
        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=1, content="Updated content")

        import asyncio

        result = asyncio.run(autosave_document(request))

        # Verify
        assert result["ok"] is True
        assert result["document_id"] == existing_doc_id
        assert result["relation"] == "autosave"

        # Verify document content was updated
        assert mock_document.content == "Updated content"

        # Verify no new document was added (only updates)
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()

        # Verify event was emitted
        mock_emit.assert_called_once()


class TestAutosaveValidation:
    """Tests for autosave request validation."""

    def test_autosave_missing_thread_id(self, mock_db):
        """Test autosave with missing thread_id returns 400."""
        documents.configure_db(mock_db)

        from guardian.routes.documents import AutosaveRequest, autosave_document

        # thread_id=0 should be treated as missing
        request = AutosaveRequest(thread_id=0, content="Some content")

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(autosave_document(request))

        assert exc_info.value.status_code == 400
        assert "thread_id is required" in exc_info.value.detail

    def test_autosave_missing_content(self, mock_db):
        """Test autosave with missing content returns 400."""
        documents.configure_db(mock_db)

        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=1, content="")

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(autosave_document(request))

        assert exc_info.value.status_code == 400
        assert "content is required" in exc_info.value.detail

    def test_autosave_whitespace_only_content(self, mock_db):
        """Test autosave with whitespace-only content returns 400."""
        documents.configure_db(mock_db)

        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=1, content="   \n\t   ")

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(autosave_document(request))

        assert exc_info.value.status_code == 400
        assert "content is required" in exc_info.value.detail


class TestAutosaveThreadNotFound:
    """Tests for autosave with non-existent thread."""

    def test_autosave_thread_not_found(self, mock_db):
        """Test autosave for non-existent thread returns 404."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread not found
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        documents.configure_db(mock_db)

        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=999, content="Some content")

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(autosave_document(request))

        assert exc_info.value.status_code == 404
        assert "Thread 999 not found" in exc_info.value.detail


class TestAutosaveEventBus:
    """Tests for EventBus integration with autosave."""

    @patch("guardian.routes.documents.models")
    @patch("guardian.routes.documents.uuid.uuid4")
    @patch("guardian.routes.documents.event_bus.emit_event")
    def test_autosave_emits_event(
        self, mock_emit, mock_uuid, mock_models, mock_db
    ):
        """Test autosave emits document.autosave event."""
        # Setup
        mock_uuid.return_value = uuid.UUID(
            "12345678-1234-5678-1234-567812345678"
        )
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 1
        mock_thread.user_id = "test_user"
        mock_thread.title = "Test Thread"
        mock_thread.project_id = 1

        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = (
            mock_thread
        )

        mock_thread_doc_query = MagicMock()
        mock_thread_doc_query.filter_by.return_value.first.return_value = None

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            elif model == mock_models.ThreadDocument:
                return mock_thread_doc_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        documents.configure_db(mock_db)

        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=1, content="Content")

        import asyncio

        asyncio.run(autosave_document(request))

        # Verify event emission
        mock_emit.assert_called_once_with(
            topic="document.autosave",
            payload={
                "thread_id": 1,
                "document_id": "12345678-1234-5678-1234-567812345678",
            },
        )

    @patch("guardian.routes.documents.models")
    @patch("guardian.routes.documents.uuid.uuid4")
    @patch("guardian.routes.documents.event_bus.emit_event")
    def test_autosave_continues_on_event_error(
        self, mock_emit, mock_uuid, mock_models, mock_db
    ):
        """Test autosave succeeds even if event emission fails."""
        # Setup
        mock_uuid.return_value = uuid.UUID(
            "12345678-1234-5678-1234-567812345678"
        )
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 1
        mock_thread.user_id = "test_user"
        mock_thread.title = "Test Thread"
        mock_thread.project_id = 1

        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = (
            mock_thread
        )

        mock_thread_doc_query = MagicMock()
        mock_thread_doc_query.filter_by.return_value.first.return_value = None

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            elif model == mock_models.ThreadDocument:
                return mock_thread_doc_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        # Make event emission fail
        mock_emit.side_effect = Exception("Event bus down")

        documents.configure_db(mock_db)

        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=1, content="Content")

        import asyncio

        result = asyncio.run(autosave_document(request))

        # Verify autosave still succeeded
        assert result["ok"] is True
        assert result["document_id"] == "12345678-1234-5678-1234-567812345678"


class TestAutosaveDatabaseErrors:
    """Tests for database error handling."""

    def test_autosave_database_error(self, mock_db):
        """Test autosave handles database errors gracefully."""
        # Setup
        mock_db.get_session.side_effect = Exception(
            "Database connection failed"
        )

        documents.configure_db(mock_db)

        from guardian.routes.documents import AutosaveRequest, autosave_document

        request = AutosaveRequest(thread_id=1, content="Content")

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(autosave_document(request))

        assert exc_info.value.status_code == 500
        assert "Failed to autosave document" in exc_info.value.detail
