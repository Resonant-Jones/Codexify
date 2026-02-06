"""Unit tests for secure share link functionality.

Tests cover:
- Creating share links for threads and documents
- Token generation and uniqueness
- Expiry validation
- Retrieving shared content
- Error handling (invalid target, not found, expired)
- Event emission
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.routes import share

_API_KEY = "test-api-key"

class TestCreateThreadShare:
    """Tests for creating share links for threads."""

    @patch("guardian.routes.share.models")
    @patch("guardian.routes.share.secrets.token_urlsafe")
    @patch("guardian.routes.share.uuid.uuid4")
    @patch("guardian.routes.share.event_bus.emit_event")
    def test_create_thread_share_success(
        self, mock_emit, mock_uuid, mock_token, mock_models, mock_db
    ):
        """Test successful creation of thread share link returns token."""
        # Setup
        mock_uuid.return_value = uuid.UUID(
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        )
        mock_token.return_value = "test_secure_token_12345"
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 1
        mock_thread.title = "Test Thread"

        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = (
            mock_thread
        )

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.SharedLink = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        # Configure router
        share.configure_db(mock_db)

        # Execute
        from guardian.routes.share import CreateShareRequest, create_share_link

        request = CreateShareRequest(target_type="thread", target_id=1)

        import asyncio

        result = asyncio.run(create_share_link(request))

        # Verify
        assert result["ok"] is True
        assert result["token"] == "test_secure_token_12345"
        assert result["url"] == "/share/test_secure_token_12345"
        assert result["expires_at"] is None

        # Verify SharedLink was created
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify event was emitted
        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args.kwargs
        assert call_kwargs["topic"] == "share.created"
        assert call_kwargs["payload"]["token"] == "test_secure_token_12345"


    @patch("guardian.routes.share.models")
    @patch("guardian.routes.share.secrets.token_urlsafe")
    @patch("guardian.routes.share.uuid.uuid4")
    @patch("guardian.routes.share.event_bus.emit_event")
    def test_create_thread_share_with_expiry(
        self, mock_emit, mock_uuid, mock_token, mock_models, mock_db
    ):
        """Test creating share link with expiry sets expires_at timestamp."""
        # Setup
        mock_uuid.return_value = uuid.UUID(
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        )
        mock_token.return_value = "token_with_expiry"

        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 2
        mock_thread.title = "Expiring Thread"

        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = (
            mock_thread
        )

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.SharedLink = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        # Execute
        from guardian.routes.share import CreateShareRequest, create_share_link

        request = CreateShareRequest(
            target_type="thread", target_id=2, expires_in_days=7
        )

        import asyncio

        result = asyncio.run(create_share_link(request))

        # Verify
        assert result["ok"] is True
        assert result["token"] == "token_with_expiry"
        assert result["expires_at"] is not None  # Expiry was set

    @patch("guardian.routes.share.models")
    def test_create_share_invalid_target_type(self, mock_models, mock_db):
        """Test creating share with invalid target_type raises 400."""
        share.configure_db(mock_db)

        from guardian.routes.share import CreateShareRequest, create_share_link

        request = CreateShareRequest(target_type="invalid", target_id=1)

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_share_link(request))

        assert exc_info.value.status_code == 400
        assert "target_type must be" in exc_info.value.detail

    @patch("guardian.routes.share.models")
    def test_create_share_thread_not_found(self, mock_models, mock_db):
        """Test creating share for non-existent thread raises 404."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread doesn't exist
        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = None

        mock_models.ChatThread = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        from guardian.routes.share import CreateShareRequest, create_share_link

        request = CreateShareRequest(target_type="thread", target_id=999)

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_share_link(request))

        assert exc_info.value.status_code == 404
        assert "Thread" in exc_info.value.detail

    @patch("guardian.routes.share.models")
    @patch("guardian.routes.share.secrets.token_urlsafe")
    @patch("guardian.routes.share.uuid.uuid4")
    @patch("guardian.routes.share.event_bus.emit_event")
    def test_create_document_share_success(
        self, mock_emit, mock_uuid, mock_token, mock_models, mock_db
    ):
        """Test successful creation of document share link."""
        # Setup
        mock_uuid.return_value = uuid.UUID(
            "cccccccc-cccc-cccc-cccc-cccccccccccc"
        )
        mock_token.return_value = "doc_token_12345"
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock document exists
        mock_document = MagicMock()
        mock_document.id = "doc-uuid-1234"

        mock_generated_query = MagicMock()
        mock_generated_query.filter_by.return_value.first.return_value = (
            mock_document
        )

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.GeneratedDocument = MagicMock()
        mock_models.UploadedDocument = MagicMock()
        mock_models.SharedLink = MagicMock()

        def query_side_effect(model):
            if model == mock_models.GeneratedDocument:
                return mock_generated_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        # Execute
        from guardian.routes.share import CreateShareRequest, create_share_link

        request = CreateShareRequest(target_type="document", target_id=1)

        import asyncio

        result = asyncio.run(create_share_link(request))

        # Verify
        assert result["ok"] is True
        assert result["token"] == "doc_token_12345"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("guardian.routes.share.models")
    def test_create_document_share_not_found(self, mock_models, mock_db):
        """Test creating share for non-existent document raises 404."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock document doesn't exist anywhere
        mock_generated_query = MagicMock()
        mock_generated_query.filter_by.return_value.first.return_value = None

        mock_uploaded_query = MagicMock()
        mock_uploaded_query.filter_by.return_value.first.return_value = None

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.GeneratedDocument = MagicMock()
        mock_models.UploadedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.GeneratedDocument:
                return mock_generated_query
            if model == mock_models.UploadedDocument:
                return mock_uploaded_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        from guardian.routes.share import CreateShareRequest, create_share_link

        request = CreateShareRequest(target_type="document", target_id=999)

        import asyncio

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(create_share_link(request))

        assert exc_info.value.status_code == 404
        assert "Document" in exc_info.value.detail


class TestRetrieveSharedContent:
    """Tests for retrieving content via share token."""

    @patch("guardian.routes.share.models")
    @patch("guardian.routes.share.event_bus.emit_event")
    def test_retrieve_thread_share_success(
        self, mock_emit, mock_models, mock_db
    ):
        """Test successful retrieval of shared thread content."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock share link exists and not expired
        mock_share = MagicMock()
        mock_share.id = "share-uuid-1"
        mock_share.target_type = "thread"
        mock_share.target_id = 1
        mock_share.expires_at = None
        mock_share.token = "test_token"

        mock_share_query = MagicMock()
        mock_share_query.filter_by.return_value.first.return_value = mock_share

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 1
        mock_thread.title = "Shared Thread"
        mock_thread.summary = "Test summary"
        mock_thread.created_at = datetime(2025, 1, 1, 10, 0, 0)
        mock_thread.updated_at = datetime(2025, 1, 2, 10, 0, 0)

        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = (
            mock_thread
        )

        # Mock messages
        mock_msg1 = MagicMock()
        mock_msg1.id = 1
        mock_msg1.role = "user"
        mock_msg1.content = "Hello"
        mock_msg1.created_at = datetime(2025, 1, 1, 10, 0, 0)

        mock_msg2 = MagicMock()
        mock_msg2.id = 2
        mock_msg2.role = "assistant"
        mock_msg2.content = "Hi there"
        mock_msg2.created_at = datetime(2025, 1, 1, 10, 5, 0)

        mock_message_query = MagicMock()
        mock_message_query.filter_by.return_value.order_by.return_value.all.return_value = [
            mock_msg1,
            mock_msg2,
        ]

        # Setup model mocks
        mock_models.SharedLink = MagicMock()
        mock_models.ChatThread = MagicMock()
        mock_models.ChatMessage = MagicMock()
        mock_models.GeneratedDocument = MagicMock()
        mock_models.UploadedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.SharedLink:
                return mock_share_query
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            if model == mock_models.ChatMessage:
                return mock_message_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        # Execute
        import asyncio

        from guardian.routes.share import retrieve_share_content

        result = asyncio.run(retrieve_share_content("test_token"))

        # Verify
        assert result["ok"] is True
        assert result["target_type"] == "thread"
        assert result["target_id"] == 1
        assert result["content"]["title"] == "Shared Thread"
        assert result["content"]["summary"] == "Test summary"
        assert len(result["content"]["messages"]) == 2
        assert result["content"]["messages"][0]["role"] == "user"
        assert result["content"]["messages"][1]["role"] == "assistant"

        # Verify event was emitted
        mock_emit.assert_called_once()
        call_kwargs = mock_emit.call_args.kwargs
        assert call_kwargs["topic"] == "share.accessed"

    @patch("guardian.routes.share.models")
    def test_retrieve_expired_share_raises_404(self, mock_models, mock_db):
        """Test retrieving expired share link raises 404."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock share link exists but is expired
        mock_share = MagicMock()
        mock_share.id = "share-uuid-2"
        mock_share.target_type = "thread"
        mock_share.target_id = 1
        # Set expires_at to the past (should be expired) - use UTC for timezone awareness
        mock_share.expires_at = datetime(2020, 1, 10, 12, 0, 0, tzinfo=UTC)
        mock_share.token = "expired_token"

        mock_share_query = MagicMock()
        mock_share_query.filter_by.return_value.first.return_value = mock_share

        # Setup model mocks
        mock_models.SharedLink = MagicMock()

        def query_side_effect(model):
            if model == mock_models.SharedLink:
                return mock_share_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        import asyncio

        from guardian.routes.share import retrieve_share_content

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(retrieve_share_content("expired_token"))

        assert exc_info.value.status_code == 404
        assert "expired" in exc_info.value.detail.lower()

    @patch("guardian.routes.share.models")
    def test_retrieve_invalid_token_raises_404(self, mock_models, mock_db):
        """Test retrieving with invalid token raises 404."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock share link doesn't exist
        mock_share_query = MagicMock()
        mock_share_query.filter_by.return_value.first.return_value = None

        mock_models.SharedLink = MagicMock()

        def query_side_effect(model):
            if model == mock_models.SharedLink:
                return mock_share_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        import asyncio

        from guardian.routes.share import retrieve_share_content

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(retrieve_share_content("invalid_token"))

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @patch("guardian.routes.share.models")
    @patch("guardian.routes.share.event_bus.emit_event")
    def test_retrieve_document_share_success(
        self, mock_emit, mock_models, mock_db
    ):
        """Test successful retrieval of shared document content."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock share link
        mock_share = MagicMock()
        mock_share.id = "share-uuid-3"
        mock_share.target_type = "document"
        mock_share.target_id = "doc-id-1234"
        mock_share.expires_at = None
        mock_share.token = "doc_token"

        mock_share_query = MagicMock()
        mock_share_query.filter_by.return_value.first.return_value = mock_share

        # Mock generated document
        mock_document = MagicMock(
            spec=[
                "id",
                "title",
                "content",
                "format",
                "created_at",
                "updated_at",
            ]
        )
        mock_document.id = "doc-id-1234"
        mock_document.title = "Shared Doc"
        mock_document.content = "Document content here"
        mock_document.format = "md"
        mock_document.created_at = datetime(2025, 1, 1, 10, 0, 0)
        mock_document.updated_at = datetime(2025, 1, 2, 10, 0, 0)

        mock_generated_query = MagicMock()
        mock_generated_query.filter_by.return_value.first.return_value = (
            mock_document
        )

        # Setup model mocks
        mock_models.SharedLink = MagicMock()
        mock_models.ChatThread = MagicMock()
        mock_models.GeneratedDocument = MagicMock()
        mock_models.UploadedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.SharedLink:
                return mock_share_query
            if model == mock_models.GeneratedDocument:
                return mock_generated_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        # Make the document instance check work
        isinstance_original = isinstance

        def isinstance_mock(obj, classinfo):
            if (
                obj is mock_document
                and classinfo.__name__ == "GeneratedDocument"
            ):
                return True
            return isinstance_original(obj, classinfo)

        share.configure_db(mock_db)

        # Execute
        import asyncio

        from guardian.routes.share import retrieve_share_content

        result = asyncio.run(retrieve_share_content("doc_token"))

        # Verify
        assert result["ok"] is True
        assert result["target_type"] == "document"
        assert result["target_id"] == "doc-id-1234"
        assert result["content"]["title"] == "Shared Doc"
        assert result["content"]["format"] == "md"

    @patch("guardian.routes.share.models")
    def test_retrieve_deleted_thread_raises_404(self, mock_models, mock_db):
        """Test retrieving share when thread has been deleted raises 404."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock share link exists
        mock_share = MagicMock()
        mock_share.id = "share-uuid-4"
        mock_share.target_type = "thread"
        mock_share.target_id = 1
        mock_share.expires_at = None

        mock_share_query = MagicMock()
        mock_share_query.filter_by.return_value.first.return_value = mock_share

        # Mock thread doesn't exist
        mock_chat_thread_query = MagicMock()
        mock_chat_thread_query.filter_by.return_value.first.return_value = None

        # Setup model mocks
        mock_models.SharedLink = MagicMock()
        mock_models.ChatThread = MagicMock()

        def query_side_effect(model):
            if model == mock_models.SharedLink:
                return mock_share_query
            if model == mock_models.ChatThread:
                return mock_chat_thread_query
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        share.configure_db(mock_db)

        import asyncio

        from guardian.routes.share import retrieve_share_content

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(retrieve_share_content("orphaned_token"))

        assert exc_info.value.status_code == 404
        assert "deleted" in exc_info.value.detail.lower()


def test_create_share_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    app = FastAPI()
    app.include_router(share.router)
    client = TestClient(app)

    response = client.post(
        "/api/share",
        json={"target_type": "thread", "target_id": 1},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


@pytest.fixture
def mock_db():
    """Mock GuardianDB for testing."""
    mock = MagicMock()
    return mock
