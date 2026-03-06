"""Integration tests for thread-document linking.

Tests cover:
- Thread-document linking integrity
- GET /api/threads/{thread_id}/documents retrieval
- Multiple documents per thread
- Different relation types (autosave, attached, reference)
- Document ordering (newest first)
- Graceful degradation when thread/document missing
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.core.auth import issue_session_token
from guardian.routes import documents


class TestGetThreadDocuments:
    """Tests for GET /api/threads/{thread_id}/documents endpoint."""

    @patch("guardian.routes.documents.models")
    def test_get_documents_success(self, mock_models, mock_db):
        """Test successful document retrieval returns 200 with documents array."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 1
        mock_thread.user_id = "test_user"
        mock_thread.title = "Test Thread"
        mock_thread.project_id = 1

        # Mock thread-document links
        now = datetime.now()
        mock_link1 = MagicMock()
        mock_link1.id = 1
        mock_link1.thread_id = 1
        mock_link1.document_id = "doc-1"
        mock_link1.relation = "autosave"
        mock_link1.created_at = now

        mock_link2 = MagicMock()
        mock_link2.id = 2
        mock_link2.thread_id = 1
        mock_link2.document_id = "doc-2"
        mock_link2.relation = "attached"
        mock_link2.created_at = now

        # Mock documents
        mock_doc1 = MagicMock()
        mock_doc1.id = "doc-1"
        mock_doc1.title = "Session Notes"

        mock_doc2 = MagicMock()
        mock_doc2.id = "doc-2"
        mock_doc2.title = "Attached Doc"

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()
        mock_models.UploadedDocument = MagicMock()

        # Setup query mocking
        doc_index = [0]
        docs = [mock_doc1, mock_doc2]

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = mock_thread
                return q
            elif model == mock_models.ThreadDocument:
                q = MagicMock()
                filter_result = MagicMock()
                filter_result.order_by.return_value.all.return_value = [
                    mock_link1,
                    mock_link2,
                ]
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.GeneratedDocument:
                q = MagicMock()
                filter_result = MagicMock()

                def first_side_effect():
                    doc = docs[doc_index[0] % len(docs)]
                    doc_index[0] += 1
                    return doc

                filter_result.first.side_effect = first_side_effect
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.UploadedDocument:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = None
                return q
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        result = asyncio.run(get_thread_documents(1))

        # Verify
        assert result["ok"] is True
        assert len(result["documents"]) == 2
        assert result["documents"][0]["id"] == "doc-1"
        assert result["documents"][0]["relation"] == "autosave"
        assert result["documents"][1]["id"] == "doc-2"
        assert result["documents"][1]["relation"] == "attached"

    @patch("guardian.routes.documents.models")
    def test_get_documents_empty(self, mock_models, mock_db):
        """Test document retrieval for thread with no documents."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread exists
        mock_thread = MagicMock()
        mock_thread.id = 1

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()

        # Mock no links
        def query_side_effect(model):
            if model == mock_models.ChatThread:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = mock_thread
                return q
            elif model == mock_models.ThreadDocument:
                q = MagicMock()
                filter_result = MagicMock()
                filter_result.order_by.return_value.all.return_value = []
                q.filter_by.return_value = filter_result
                return q
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        result = asyncio.run(get_thread_documents(1))

        # Verify
        assert result["ok"] is True
        assert result["documents"] == []

    @patch("guardian.routes.documents.models")
    def test_get_documents_thread_not_found(self, mock_models, mock_db):
        """Test document retrieval for non-existent thread returns 404."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread not found
        mock_query = MagicMock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_thread_documents(999))

        assert exc_info.value.status_code == 404
        assert "Thread 999 not found" in exc_info.value.detail

    @patch("guardian.routes.documents.models")
    def test_get_documents_resolves_uploaded_documents(
        self, mock_models, mock_db
    ):
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        mock_thread = MagicMock()
        mock_thread.id = 1

        now = datetime.now()
        mock_link = MagicMock()
        mock_link.document_id = "upload-1"
        mock_link.relation = "attached"
        mock_link.created_at = now

        mock_uploaded_doc = MagicMock()
        mock_uploaded_doc.id = "upload-1"
        mock_uploaded_doc.filename = "requirements.pdf"

        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()
        mock_models.UploadedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = mock_thread
                return q
            if model == mock_models.ThreadDocument:
                q = MagicMock()
                filtered = MagicMock()
                filtered.order_by.return_value.all.return_value = [mock_link]
                q.filter_by.return_value = filtered
                return q
            if model == mock_models.GeneratedDocument:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = None
                return q
            if model == mock_models.UploadedDocument:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = mock_uploaded_doc
                return q
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        result = asyncio.run(get_thread_documents(1))

        assert result["ok"] is True
        assert result["documents"] == [
            {
                "id": "upload-1",
                "title": "requirements.pdf",
                "relation": "attached",
                "created_at": now.isoformat(),
            }
        ]


class TestMultipleDocumentsPerThread:
    """Tests for threads with multiple linked documents."""

    @patch("guardian.routes.documents.models")
    def test_multiple_documents_different_relations(self, mock_models, mock_db):
        """Test thread can have multiple documents with different relation types."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread
        mock_thread = MagicMock()
        mock_thread.id = 1

        # Mock links with different relations
        now = datetime.now()
        links = []
        for i, rel in enumerate(["autosave", "attached", "reference"]):
            link = MagicMock()
            link.id = i + 1
            link.thread_id = 1
            link.document_id = f"doc-{rel}"
            link.relation = rel
            link.created_at = now
            links.append(link)

        # Mock documents
        docs = []
        for rel in ["autosave", "attached", "reference"]:
            doc = MagicMock()
            doc.id = f"doc-{rel}"
            doc.title = f"{rel.capitalize()} Doc"
            docs.append(doc)

        doc_index = [0]

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = mock_thread
                return q
            elif model == mock_models.ThreadDocument:
                q = MagicMock()
                filter_result = MagicMock()
                filter_result.order_by.return_value.all.return_value = links
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.GeneratedDocument:
                q = MagicMock()
                filter_result = MagicMock()

                def first_side_effect():
                    doc = docs[doc_index[0] % len(docs)]
                    doc_index[0] += 1
                    return doc

                filter_result.first.side_effect = first_side_effect
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.UploadedDocument:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = None
                return q
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        result = asyncio.run(get_thread_documents(1))

        # Verify
        assert result["ok"] is True
        assert len(result["documents"]) == 3

        relations = [doc["relation"] for doc in result["documents"]]
        assert "autosave" in relations
        assert "attached" in relations
        assert "reference" in relations


class TestDocumentOrdering:
    """Tests for document ordering (newest first)."""

    @patch("guardian.routes.documents.models")
    def test_documents_ordered_newest_first(self, mock_models, mock_db):
        """Test documents are returned in descending order by created_at."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread
        mock_thread = MagicMock()
        mock_thread.id = 1

        # Mock links with different timestamps
        old_time = datetime(2025, 1, 1, 10, 0, 0)
        new_time = datetime(2025, 1, 2, 10, 0, 0)

        link_new = MagicMock()
        link_new.id = 1
        link_new.thread_id = 1
        link_new.document_id = "doc-new"
        link_new.relation = "autosave"
        link_new.created_at = new_time

        link_old = MagicMock()
        link_old.id = 2
        link_old.thread_id = 1
        link_old.document_id = "doc-old"
        link_old.relation = "attached"
        link_old.created_at = old_time

        doc_new = MagicMock()
        doc_new.id = "doc-new"
        doc_new.title = "Newer Doc"

        doc_old = MagicMock()
        doc_old.id = "doc-old"
        doc_old.title = "Older Doc"

        docs = [doc_new, doc_old]
        doc_index = [0]

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = mock_thread
                return q
            elif model == mock_models.ThreadDocument:
                q = MagicMock()
                filter_result = MagicMock()
                # Simulate order_by(desc()) returning newest first
                filter_result.order_by.return_value.all.return_value = [
                    link_new,
                    link_old,
                ]
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.GeneratedDocument:
                q = MagicMock()
                filter_result = MagicMock()

                def first_side_effect():
                    doc = docs[doc_index[0] % len(docs)]
                    doc_index[0] += 1
                    return doc

                filter_result.first.side_effect = first_side_effect
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.UploadedDocument:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = None
                return q
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        result = asyncio.run(get_thread_documents(1))

        # Verify newest document is first
        assert result["ok"] is True
        assert len(result["documents"]) == 2
        assert result["documents"][0]["id"] == "doc-new"
        assert result["documents"][0]["created_at"] == new_time.isoformat()
        assert result["documents"][1]["id"] == "doc-old"
        assert result["documents"][1]["created_at"] == old_time.isoformat()


class TestGracefulDegradation:
    """Tests for graceful handling of missing documents."""

    @patch("guardian.routes.documents.models")
    def test_missing_document_skipped(self, mock_models, mock_db):
        """Test that links to missing documents are skipped gracefully."""
        # Setup
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock thread
        mock_thread = MagicMock()
        mock_thread.id = 1

        # Mock links (one points to missing document)
        now = datetime.now()
        link_exists = MagicMock()
        link_exists.id = 1
        link_exists.thread_id = 1
        link_exists.document_id = "doc-exists"
        link_exists.relation = "autosave"
        link_exists.created_at = now

        link_missing = MagicMock()
        link_missing.id = 2
        link_missing.thread_id = 1
        link_missing.document_id = "doc-missing"
        link_missing.relation = "attached"
        link_missing.created_at = now

        # Only one document exists
        mock_doc = MagicMock()
        mock_doc.id = "doc-exists"
        mock_doc.title = "Existing Doc"

        doc_index = [0]

        # Setup model mocks
        mock_models.ChatThread = MagicMock()
        mock_models.ThreadDocument = MagicMock()
        mock_models.GeneratedDocument = MagicMock()
        mock_models.UploadedDocument = MagicMock()

        def query_side_effect(model):
            if model == mock_models.ChatThread:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = mock_thread
                return q
            elif model == mock_models.ThreadDocument:
                q = MagicMock()
                filter_result = MagicMock()
                filter_result.order_by.return_value.all.return_value = [
                    link_exists,
                    link_missing,
                ]
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.GeneratedDocument:
                q = MagicMock()
                filter_result = MagicMock()

                def first_side_effect():
                    # First call returns doc, second returns None
                    if doc_index[0] == 0:
                        doc_index[0] += 1
                        return mock_doc
                    else:
                        return None

                filter_result.first.side_effect = first_side_effect
                q.filter_by.return_value = filter_result
                return q
            elif model == mock_models.UploadedDocument:
                q = MagicMock()
                q.filter_by.return_value.first.return_value = None
                return q
            return MagicMock()

        mock_session.query.side_effect = query_side_effect

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        result = asyncio.run(get_thread_documents(1))

        # Verify only existing document is returned
        assert result["ok"] is True
        assert len(result["documents"]) == 1
        assert result["documents"][0]["id"] == "doc-exists"


class TestDatabaseErrors:
    """Tests for database error handling."""

    @patch("guardian.routes.documents.models")
    def test_get_documents_database_error(self, mock_models, mock_db):
        """Test document retrieval handles database errors gracefully."""
        # Setup
        mock_db.get_session.side_effect = Exception(
            "Database connection failed"
        )

        documents.configure_db(mock_db)

        import asyncio

        from guardian.routes.documents import get_thread_documents

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(get_thread_documents(1))

        assert exc_info.value.status_code == 500
        assert "Failed to retrieve thread documents" in exc_info.value.detail


@contextmanager
def _thread_documents_client(
    monkeypatch,
    *,
    exposure_mode: str,
    auth_mode: str,
    session_secret: str | None = None,
    api_key: str = "local-test-key",
):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", exposure_mode)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", auth_mode)
    monkeypatch.setenv("GUARDIAN_API_KEY", api_key)
    if session_secret is not None:
        monkeypatch.setenv("GUARDIAN_SESSION_SECRET", session_secret)
    else:
        monkeypatch.delenv("GUARDIAN_SESSION_SECRET", raising=False)
    monkeypatch.delenv("GUARDIAN_JWT_SECRET", raising=False)

    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session

    mock_thread = MagicMock()
    mock_thread.id = 1

    thread_query = MagicMock()
    thread_query.filter_by.return_value.first.return_value = mock_thread

    links_query = MagicMock()
    links_query.filter_by.return_value.order_by.return_value.all.return_value = (
        []
    )

    mock_session.query.side_effect = [thread_query, links_query]

    documents.configure_db(mock_db)

    app = FastAPI()
    app.include_router(documents.router)
    with TestClient(app) as client:
        client.headers.pop("x-api-key", None)
        client.headers.pop("X-API-Key", None)
        yield client


def test_thread_documents_list_denies_unauthenticated_in_public_allowlist(
    monkeypatch,
):
    with _thread_documents_client(
        monkeypatch,
        exposure_mode="public_allowlist",
        auth_mode="local",
        session_secret="remote-session-secret",
    ) as client:
        response = client.get("/api/threads/1/documents")

    assert response.status_code == 401
    assert "session/jwt" in str(response.json().get("detail", "")).lower()


def test_thread_documents_list_allows_local_api_key_in_local_safe(monkeypatch):
    with _thread_documents_client(
        monkeypatch,
        exposure_mode="local_safe",
        auth_mode="local",
        api_key="local-test-key",
    ) as client:
        response = client.get(
            "/api/threads/1/documents", headers={"X-API-Key": "local-test-key"}
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "documents": []}


def test_thread_documents_list_allows_bearer_in_public_allowlist(monkeypatch):
    with _thread_documents_client(
        monkeypatch,
        exposure_mode="public_allowlist",
        auth_mode="local",
        session_secret="remote-session-secret",
    ) as client:
        session_token, _expires = issue_session_token(
            subject="thread-documents-route-auth-test",
            ttl_seconds=60,
        )
        response = client.get(
            "/api/threads/1/documents",
            headers={"Authorization": f"Bearer {session_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "documents": []}
