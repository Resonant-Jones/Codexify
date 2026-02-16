from __future__ import annotations

import numpy as np

from backend.rag.embedder import LocalSemanticEmbedder


class _DummyFaissIndex:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def search(self, _vectors, k: int):
        self.calls.append(k)
        scores = np.array([[0.9, 0.8, 0.7]], dtype="float32")
        indices = np.array([[0, 1, 2]], dtype="int64")
        return scores, indices


class _DummyChromaCollection:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "documents": [["doc one"]],
            "metadatas": [[{"namespace": "thread:5"}]],
            "distances": [[0.2]],
            "ids": [["id-1"]],
        }


def test_faiss_search_filters_by_namespace():
    embedder = object.__new__(LocalSemanticEmbedder)
    embedder.store = "faiss"
    embedder._index = _DummyFaissIndex()
    embedder._texts = ["alpha", "beta", "gamma"]
    embedder._metadatas = [
        {"namespace": "thread:5"},
        {"namespace": "thread:9"},
        {"namespace": "thread:5"},
    ]
    embedder._embed_np = lambda _texts: np.array([[1.0, 0.0]], dtype="float32")

    results = embedder.search("query", k=2, namespace="thread:5")

    assert embedder._index.calls == [3]
    assert [item["text"] for item in results] == ["alpha", "gamma"]
    assert all(item["meta"]["namespace"] == "thread:5" for item in results)


def test_chroma_search_passes_namespace_where_filter():
    embedder = object.__new__(LocalSemanticEmbedder)
    embedder.store = "chroma"
    embedder._chroma_collection = _DummyChromaCollection()
    embedder._embed_np = lambda _texts: np.array([[1.0, 0.0]], dtype="float32")

    results = embedder.search("query", k=1, namespace="thread:5")

    assert embedder._chroma_collection.calls[0]["where"] == {
        "namespace": "thread:5"
    }
    assert results[0]["metadata"]["namespace"] == "thread:5"
