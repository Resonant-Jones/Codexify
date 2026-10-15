from __future__ import annotations

from guardian.core.config import (
    DEFAULT_VECTOR_STORE_BACKEND,
    DEFAULT_VECTOR_STORE_COLLECTION,
    resolve_vector_store_runtime,
)
from guardian.vector import store as vector_store_module


class _RecordingEmbedder:
    def __init__(self, **kwargs) -> None:
        self.kwargs = dict(kwargs)

    def embed_and_index(self, texts, metadatas=None, ids=None):
        return {"count": len(texts)}

    def search(self, query, k=5, namespace=None):
        return []

    def embed_texts(self, texts):
        return [[0.0] for _ in texts]


def test_vector_store_uses_canonical_runtime_from_env(
    monkeypatch,
    tmp_path,
):
    created: dict[str, object] = {}

    def _factory(**kwargs):
        created["kwargs"] = dict(kwargs)
        return _RecordingEmbedder(**kwargs)

    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(tmp_path / "supported"))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "supported_path_collection")
    monkeypatch.setattr(vector_store_module, "Embedder", _factory)

    store = vector_store_module.VectorStore()
    runtime = resolve_vector_store_runtime()

    assert store.describe_runtime() == runtime.as_dict()
    assert created["kwargs"] == {
        "store": runtime.backend,
        "chroma_path": runtime.chroma_path,
        "collection": runtime.collection,
    }


def test_vector_store_blank_env_defaults_to_canonical_shared_runtime(
    monkeypatch,
):
    created: dict[str, object] = {}

    def _factory(**kwargs):
        created["kwargs"] = dict(kwargs)
        return _RecordingEmbedder(**kwargs)

    monkeypatch.delenv("CODEXIFY_VECTOR_STORE", raising=False)
    monkeypatch.delenv("CODEXIFY_CHROMA_PATH", raising=False)
    monkeypatch.delenv("CODEXIFY_COLLECTION", raising=False)
    monkeypatch.setattr(vector_store_module, "Embedder", _factory)

    store = vector_store_module.VectorStore()
    runtime = resolve_vector_store_runtime()

    assert runtime.backend == DEFAULT_VECTOR_STORE_BACKEND
    assert runtime.collection == DEFAULT_VECTOR_STORE_COLLECTION
    assert store.store == runtime.backend
    assert store.describe_runtime() == runtime.as_dict()
    assert created["kwargs"]["store"] == DEFAULT_VECTOR_STORE_BACKEND
