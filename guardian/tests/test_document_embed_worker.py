from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from guardian.db.models import UploadedDocument
from guardian.workers import document_embed_worker


class _FakeDoc:
    def __init__(self) -> None:
        self.id = "doc-1"
        self.parsed_text = "Hello world"
        self.filename = "doc-1.txt"
        self.user_id = "default"
        self.project_id = 1
        self.thread_id = 2
        self.embedding_status = "pending"


class _FakeQuery:
    def __init__(self, doc: _FakeDoc) -> None:
        self._doc = doc
        self.updates: list[dict] = []

    def filter_by(self, **_kwargs):
        return self

    def first(self):
        return self._doc

    def update(self, values):
        self.updates.append(values)
        return 1


class _SessionContext:
    def __init__(self, session) -> None:
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEmbedder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def embed_and_index(self, docs, metadatas=None):
        self.calls.append({"docs": docs, "metadatas": metadatas})
        return {"count": len(docs)}


class _FailEmbedder:
    def embed_and_index(self, _docs, metadatas=None):
        raise RuntimeError("boom")


def _make_db(query: _FakeQuery):
    session = MagicMock()
    session.query.return_value = query
    db = MagicMock()
    db.get_session.return_value = _SessionContext(session)
    return db


def test_document_embed_worker_status_transitions():
    doc = _FakeDoc()
    query = _FakeQuery(doc)
    db = _make_db(query)
    embedder = _FakeEmbedder()

    ok = document_embed_worker.process_document_embed_task(
        {"doc_id": doc.id},
        db=db,
        embedder_factory=lambda: embedder,
    )

    assert ok is True
    assert len(query.updates) == 2
    first, second = query.updates
    assert first[UploadedDocument.embedding_status] == "processing"
    assert isinstance(first[UploadedDocument.embedding_started_at], datetime)
    assert second[UploadedDocument.embedding_status] == "ready"
    assert second[UploadedDocument.embedding_error] is None
    assert isinstance(second[UploadedDocument.embedding_completed_at], datetime)

    assert len(embedder.calls) == 1
    call = embedder.calls[0]
    assert call["docs"] == ["Hello world"]
    assert call["metadatas"][0]["doc_id"] == doc.id
    assert call["metadatas"][0]["chunk_index"] == 0
    assert call["metadatas"][0]["chunk_count"] == 1


def test_document_embed_worker_records_failure():
    doc = _FakeDoc()
    query = _FakeQuery(doc)
    db = _make_db(query)

    ok = document_embed_worker.process_document_embed_task(
        {"doc_id": doc.id},
        db=db,
        embedder_factory=lambda: _FailEmbedder(),
    )

    assert ok is False
    assert len(query.updates) == 2
    _, second = query.updates
    assert second[UploadedDocument.embedding_status] == "failed"
    assert second[UploadedDocument.embedding_error] == "boom"
    assert isinstance(second[UploadedDocument.embedding_completed_at], datetime)
