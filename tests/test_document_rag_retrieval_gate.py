"""Tests for document retrieval readiness gate and status surface."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from guardian.core.dependencies import RequestUserScope
from guardian.routes import documents as documents_routes

# ── helpers ──────────────────────────────────────────────────────────────────


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeDoc:
    def __init__(
        self,
        *,
        doc_id: str = "doc-1",
        project_id: int = 1,
        thread_id: int | None = 7,
        status: str = "ready",
    ):
        self.id = doc_id
        self.src_url = f"/media/documents/{doc_id}.pdf"
        self.filename = f"{doc_id}.pdf"
        self.mime_type = "application/pdf"
        self.parsed_text = "Full document body"
        self.filesize = 123
        self.source_tag = "document"
        self.created_at = datetime(2026, 1, 23, tzinfo=timezone.utc)
        self.embedding_status = status
        self.embedding_error = None if status != "failed" else "chunk_error"
        self.embedding_started_at = None
        self.embedding_completed_at = None
        self.deleted_at = None
        self.project_id = project_id
        self.thread_id = thread_id
        self.user_id = "tester"


# ── context broker retrieval gate ────────────────────────────────────────────


class TestContextBrokerDocumentReadinessGate:
    """Verify the context broker only returns embedding_status=ready documents."""

    def test_load_doc_by_type_returns_ready_document(self):
        """_load_doc_by_type returns a document when embedding_status=ready."""
        from guardian.context.broker import ContextBroker
        from guardian.db.models import GeneratedDocument, UploadedDocument

        broker = ContextBroker(chatlog_db=MagicMock(), vector_store=MagicMock())

        ready_doc = _FakeDoc(doc_id="ready-1", status="ready")
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = ready_doc

        session = MagicMock()
        session.query.return_value = mock_query

        result = broker._load_doc_by_type(
            session=session,
            doc_id="ready-1",
            doc_type="uploaded",
            user_id="tester",
            generated_model=GeneratedDocument,
            uploaded_model=UploadedDocument,
        )

        # A ready document should be returned
        assert result is ready_doc
        # The query must have been against UploadedDocument
        session.query.assert_called_once_with(UploadedDocument)
        # Two filters were applied: by id and by embedding_status
        assert mock_query.filter.call_count == 2

    def test_load_doc_by_type_returns_none_when_no_ready_match(self):
        """When no document matches id + ready, returns None."""
        from guardian.context.broker import ContextBroker
        from guardian.db.models import GeneratedDocument, UploadedDocument

        broker = ContextBroker(chatlog_db=MagicMock(), vector_store=MagicMock())

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # SQL returns no match

        session = MagicMock()
        session.query.return_value = mock_query

        result = broker._load_doc_by_type(
            session=session,
            doc_id="missing-1",
            doc_type="uploaded",
            user_id="tester",
            generated_model=GeneratedDocument,
            uploaded_model=UploadedDocument,
        )

        assert result is None


# ── thread documents API surface ─────────────────────────────────────────────


class TestThreadDocumentsEmbeddingStatus:
    """The thread documents endpoint must surface embedding_status per doc."""

    @pytest.mark.anyio
    async def test_thread_documents_includes_embedding_status(
        self, monkeypatch
    ):
        """GET /api/threads/{id}/documents returns embedding_status for each doc."""
        from guardian.db import models as m

        ready_doc = _FakeDoc(doc_id="zip-1", status="ready")
        session = MagicMock()

        thread_query = MagicMock()
        thread_query.filter_by.return_value = thread_query
        thread_query.first.return_value = MagicMock(id=1, user_id="tester")

        link_row = MagicMock()
        link_row.document_id = "zip-1"
        link_row.relation = "attached"
        link_row.created_at = datetime.now(timezone.utc)

        def query_side_effect(model, *args, **kwargs):
            mock_q = MagicMock()
            if model == m.ChatThread:
                mock_q.filter_by.return_value = thread_query
                return mock_q
            if model == m.ThreadDocument:
                mock_q.filter_by.return_value = MagicMock(
                    order_by=MagicMock(
                        return_value=MagicMock(
                            all=MagicMock(return_value=[link_row])
                        )
                    )
                )
                return mock_q
            if model == m.UploadedDocument:
                mock_q.filter_by.return_value = MagicMock(
                    first=MagicMock(return_value=ready_doc)
                )
                return mock_q
            if model == m.GeneratedDocument:
                mock_q.filter_by.return_value = MagicMock(
                    first=MagicMock(return_value=None)
                )
                return mock_q
            return mock_q

        session.query.side_effect = query_side_effect

        db = MagicMock()
        db.get_session.return_value = _SessionContext(session)

        monkeypatch.setattr(documents_routes, "_get_db", lambda: db)
        monkeypatch.setattr(
            documents_routes,
            "_require_thread_account_scope",
            lambda *args, **kwargs: None,
        )

        result = await documents_routes._get_thread_documents_impl(
            thread_id=1,
            request_user_scope=RequestUserScope(
                user_id="tester", account_id="tester", multi_user_enabled=False
            ),
            _db=db,
        )

        assert result["ok"] is True
        assert len(result["documents"]) == 1
        assert result["documents"][0]["embedding_status"] == "ready"
        assert result["documents"][0]["embedding_error"] is None

    @pytest.mark.anyio
    async def test_thread_documents_surfaces_pending_status(self, monkeypatch):
        """A pending document shows embedding_status=pending in the response."""
        from guardian.db import models as m

        pending_doc = _FakeDoc(doc_id="pend-1", status="pending")
        session = MagicMock()

        thread_query = MagicMock()
        thread_query.filter_by.return_value = thread_query
        thread_query.first.return_value = MagicMock(id=1, user_id="tester")

        link_row = MagicMock(
            document_id="pend-1",
            relation="attached",
            created_at=datetime.now(timezone.utc),
        )

        def query_side_effect(model, *args, **kwargs):
            mock_q = MagicMock()
            if model == m.ChatThread:
                mock_q.filter_by.return_value = thread_query
                return mock_q
            if model == m.ThreadDocument:
                mock_q.filter_by.return_value = MagicMock(
                    order_by=MagicMock(
                        return_value=MagicMock(
                            all=MagicMock(return_value=[link_row])
                        )
                    )
                )
                return mock_q
            if model == m.UploadedDocument:
                mock_q.filter_by.return_value = MagicMock(
                    first=MagicMock(return_value=pending_doc)
                )
                return mock_q
            if model == m.GeneratedDocument:
                mock_q.filter_by.return_value = MagicMock(
                    first=MagicMock(return_value=None)
                )
                return mock_q
            return mock_q

        session.query.side_effect = query_side_effect
        db = MagicMock()
        db.get_session.return_value = _SessionContext(session)
        monkeypatch.setattr(documents_routes, "_get_db", lambda: db)
        monkeypatch.setattr(
            documents_routes,
            "_require_thread_account_scope",
            lambda *args, **kwargs: None,
        )

        result = await documents_routes._get_thread_documents_impl(
            thread_id=1,
            request_user_scope=RequestUserScope(
                user_id="tester", account_id="tester", multi_user_enabled=False
            ),
            _db=db,
        )

        assert result["documents"][0]["embedding_status"] == "pending"

    @pytest.mark.anyio
    async def test_thread_documents_surfaces_failed_with_error(
        self, monkeypatch
    ):
        """A failed document includes embedding_error."""
        from guardian.db import models as m

        failed_doc = _FakeDoc(doc_id="fail-1", status="failed")
        failed_doc.embedding_error = "parsed_text_missing"
        session = MagicMock()

        thread_query = MagicMock()
        thread_query.filter_by.return_value = thread_query
        thread_query.first.return_value = MagicMock(id=1, user_id="tester")

        link_row = MagicMock(
            document_id="fail-1",
            relation="attached",
            created_at=datetime.now(timezone.utc),
        )

        def query_side_effect(model, *args, **kwargs):
            mock_q = MagicMock()
            if model == m.ChatThread:
                mock_q.filter_by.return_value = thread_query
                return mock_q
            if model == m.ThreadDocument:
                mock_q.filter_by.return_value = MagicMock(
                    order_by=MagicMock(
                        return_value=MagicMock(
                            all=MagicMock(return_value=[link_row])
                        )
                    )
                )
                return mock_q
            if model == m.UploadedDocument:
                mock_q.filter_by.return_value = MagicMock(
                    first=MagicMock(return_value=failed_doc)
                )
                return mock_q
            if model == m.GeneratedDocument:
                mock_q.filter_by.return_value = MagicMock(
                    first=MagicMock(return_value=None)
                )
                return mock_q
            return mock_q

        session.query.side_effect = query_side_effect
        db = MagicMock()
        db.get_session.return_value = _SessionContext(session)
        monkeypatch.setattr(documents_routes, "_get_db", lambda: db)
        monkeypatch.setattr(
            documents_routes,
            "_require_thread_account_scope",
            lambda *args, **kwargs: None,
        )

        result = await documents_routes._get_thread_documents_impl(
            thread_id=1,
            request_user_scope=RequestUserScope(
                user_id="tester", account_id="tester", multi_user_enabled=False
            ),
            _db=db,
        )

        assert result["documents"][0]["embedding_status"] == "failed"
        assert (
            result["documents"][0]["embedding_error"] == "parsed_text_missing"
        )
