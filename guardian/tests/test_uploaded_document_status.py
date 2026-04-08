from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class _FakeQuery:
    def __init__(self, items):
        self._items = list(items)

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        self._items = [
            item
            for item in self._items
            if all(
                getattr(item, key, None) == value
                for key, value in kwargs.items()
            )
        ]
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


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
    ):
        self.id = doc_id
        self.src_url = f"/media/documents/{doc_id}.pdf"
        self.filename = f"{doc_id}.pdf"
        self.mime_type = "application/pdf"
        self.parsed_text = "Full document body"
        self.filesize = 123
        self.source_tag = "document"
        self.created_at = datetime(2026, 1, 23, tzinfo=timezone.utc)
        self.embedding_status = "pending"
        self.embedding_error = None
        self.embedding_started_at = None
        self.embedding_completed_at = None
        self.deleted_at = None
        self.project_id = project_id
        self.thread_id = thread_id


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
    assert doc_payload["src_url"].startswith("/media/documents/doc-1.pdf")
    assert doc_payload["project_id"] == 1
    assert doc_payload["thread_id"] == 7
    assert "sig=" in doc_payload["src_url"]
    assert doc_payload["embedding_status"] == "pending"
    assert doc_payload["embedding_error"] is None
    assert doc_payload["embedding_started_at"] is None
    assert doc_payload["embedding_completed_at"] is None


def test_documents_list_filters_by_project_and_thread():
    docs = [
        _FakeDoc(doc_id="doc-a", project_id=10, thread_id=101),
        _FakeDoc(doc_id="doc-b", project_id=10, thread_id=102),
        _FakeDoc(doc_id="doc-c", project_id=11, thread_id=101),
    ]
    session = MagicMock()
    session.query.side_effect = lambda *_args, **_kwargs: _FakeQuery(docs)
    db = MagicMock()
    db.get_session.return_value = _SessionContext(session)

    from guardian.routes import media as media_routes

    app = FastAPI()
    app.include_router(media_routes.router, prefix="/api/media")

    with patch("guardian.routes.media._get_db", return_value=db):
        client = TestClient(app)

        project_only = client.get(
            "/api/media/documents", params={"project_id": 10}
        )
        assert project_only.status_code == 200
        payload = project_only.json()
        assert payload["count"] == 2
        assert {doc["id"] for doc in payload["documents"]} == {"doc-a", "doc-b"}

        project_and_thread = client.get(
            "/api/media/documents",
            params={"project_id": 10, "thread_id": 101},
        )
        assert project_and_thread.status_code == 200
        subset = project_and_thread.json()
        assert subset["count"] == 1
        assert subset["documents"][0]["id"] == "doc-a"


def test_delete_document_soft_deletes_uploaded_document():
    doc = _FakeDoc()
    session = MagicMock()
    session.query.side_effect = lambda *_args, **_kwargs: _FakeQuery([doc])
    db = MagicMock()
    db.get_session.return_value = _SessionContext(session)

    from guardian.routes import media as media_routes

    app = FastAPI()
    app.include_router(media_routes.router, prefix="/api/media")

    with patch("guardian.routes.media._get_db", return_value=db):
        client = TestClient(app)
        response = client.delete("/api/media/documents/doc-1")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert doc.deleted_at is not None
    session.commit.assert_called_once()


def test_get_document_returns_full_document_body():
    doc = _FakeDoc()
    session = MagicMock()
    session.query.return_value = _FakeQuery([doc])
    db = MagicMock()
    db.get_session.return_value = _SessionContext(session)

    from guardian.routes import media as media_routes

    app = FastAPI()
    app.include_router(media_routes.router, prefix="/api/media")

    with patch("guardian.routes.media._get_db", return_value=db):
        client = TestClient(app)
        response = client.get("/api/media/documents/doc-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "doc-1"
    assert payload["content"] == "Full document body"
    assert payload["parsed_text"] == "Full document body"
    assert payload["src_url"].startswith("/media/documents/doc-1.pdf")
