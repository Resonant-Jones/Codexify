from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from guardian.core.config import resolve_vector_store_runtime
from guardian.db.models import UploadedDocument
from guardian.vector import store as vector_store_module
from guardian.workers import document_embed_worker


class _FakeDoc:
    def __init__(self) -> None:
        self.id = "doc-1"
        self.parsed_text = "fresh sentinel from worker"
        self.filename = "doc-1.txt"
        self.user_id = "default"
        self.project_id = 7
        self.thread_id = 9
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


def _make_db(query: _FakeQuery):
    session = MagicMock()
    session.query.return_value = query
    db = MagicMock()
    db.get_session.return_value = _SessionContext(session)
    return db


class _RecordingVectorStore:
    created: list[_RecordingVectorStore] = []

    def __init__(self) -> None:
        self.runtime = resolve_vector_store_runtime()
        self.items: list[dict[str, object]] = []
        self.__class__.created.append(self)

    def add_texts(self, items: list[dict[str, object]]) -> int:
        self.items.extend(items)
        return len(items)


class _SharedEmbedder:
    _records: dict[tuple[str, str, str], list[dict[str, object]]] = {}

    def __init__(self, **kwargs) -> None:
        self.store = kwargs["store"]
        self.chroma_path = kwargs["chroma_path"]
        self.collection = kwargs["collection"]
        self._key = (self.store, self.chroma_path, self.collection)
        self._records.setdefault(self._key, [])

    def embed_and_index(self, texts, metadatas=None, ids=None):
        bucket = self._records.setdefault(self._key, [])
        for index, text in enumerate(texts):
            meta = (
                dict(metadatas[index])
                if metadatas is not None and index < len(metadatas)
                else {}
            )
            bucket.append(
                {
                    "text": text,
                    "meta": meta,
                    "metadata": meta,
                    "score": 1.0,
                }
            )
        return {"count": len(texts)}

    def search(self, query, k=5, namespace=None):
        needle = str(query or "").lower()
        matches: list[dict[str, object]] = []
        for item in self._records.get(self._key, []):
            meta = item.get("meta", {})
            if namespace and meta.get("namespace") != namespace:
                continue
            if needle not in str(item.get("text", "")).lower():
                continue
            matches.append(dict(item))
        return matches[:k]

    def embed_texts(self, texts):
        return [[0.0] for _ in texts]


def test_document_embed_worker_uses_canonical_vector_store_runtime(
    monkeypatch,
):
    _RecordingVectorStore.created.clear()

    doc = _FakeDoc()
    query = _FakeQuery(doc)
    db = _make_db(query)

    monkeypatch.setattr(
        document_embed_worker,
        "VectorStore",
        _RecordingVectorStore,
    )
    monkeypatch.setattr(
        document_embed_worker,
        "chunk_document_text",
        lambda _text: [
            SimpleNamespace(text="chunk-one", index=0),
            SimpleNamespace(text="chunk-two", index=1),
        ],
    )

    ok = document_embed_worker.process_document_embed_task(
        {"doc_id": doc.id},
        db=db,
    )

    assert ok is True
    assert len(_RecordingVectorStore.created) == 1
    store = _RecordingVectorStore.created[0]
    assert store.runtime.as_dict() == resolve_vector_store_runtime().as_dict()
    assert [item["text"] for item in store.items] == ["chunk-one", "chunk-two"]
    assert store.items[0]["meta"]["doc_id"] == doc.id
    assert store.items[0]["meta"]["chunk_index"] == 0
    assert store.items[1]["meta"]["chunk_index"] == 1
    assert len(query.updates) == 2
    assert query.updates[0][UploadedDocument.embedding_status] == "processing"
    assert query.updates[1][UploadedDocument.embedding_status] == "ready"
    assert isinstance(
        query.updates[1][UploadedDocument.embedding_completed_at],
        datetime,
    )


def test_worker_write_and_backend_search_share_canonical_store_seam(
    monkeypatch,
    tmp_path,
):
    _SharedEmbedder._records.clear()

    doc = _FakeDoc()
    query = _FakeQuery(doc)
    db = _make_db(query)

    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(tmp_path / "vector-runtime"))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "worker_backend_same_seam")
    monkeypatch.setattr(vector_store_module, "Embedder", _SharedEmbedder)
    monkeypatch.setattr(
        document_embed_worker,
        "chunk_document_text",
        lambda text: [SimpleNamespace(text=text, index=0)],
    )

    ok = document_embed_worker.process_document_embed_task(
        {"doc_id": doc.id},
        db=db,
    )
    backend_store = vector_store_module.VectorStore()
    matches = backend_store.search(
        "fresh sentinel",
        k=1,
        namespace="thread:9",
    )

    assert ok is True
    assert (
        backend_store.describe_runtime()
        == resolve_vector_store_runtime().as_dict()
    )
    assert matches
    assert matches[0]["text"] == "fresh sentinel from worker"
    assert matches[0]["meta"]["doc_id"] == doc.id
    assert matches[0]["meta"]["namespace"] == "thread:9"
