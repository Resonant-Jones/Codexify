from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeQuery:
    def __init__(self, items):
        self._items = items

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self._items


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeDoc:
    def __init__(self):
        self.id = "doc-1"
        self.src_url = "/media/documents/doc-1.pdf"
        self.filename = "doc-1.pdf"
        self.mime_type = "application/pdf"
        self.filesize = 123
        self.created_at = datetime(2026, 1, 23, tzinfo=timezone.utc)
        self.embedding_status = "pending"
        self.embedding_error = None
        self.embedding_started_at = None
        self.embedding_completed_at = None
        self.deleted_at = None


def test_documents_list_includes_embedding_status():
    doc = _FakeDoc()
    query = _FakeQuery([doc])
    session = MagicMock()
    session.query.return_value = query
    db = MagicMock()
    db.get_session.return_value = _SessionContext(session)

    from guardian.routes import media as media_routes

    app = FastAPI()
    app.include_router(media_routes.router, prefix="/api/media")

    with patch("guardian.routes.media._get_db", return_value=db):
        client = TestClient(app)
        response = client.get("/api/media/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    doc_payload = payload["documents"][0]
    assert doc_payload["embedding_status"] == "pending"
    assert doc_payload["embedding_error"] is None
    assert doc_payload["embedding_started_at"] is None
    assert doc_payload["embedding_completed_at"] is None
