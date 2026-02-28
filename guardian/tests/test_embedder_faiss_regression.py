from __future__ import annotations

from types import SimpleNamespace

import numpy as np

import backend.rag.embedder as embedder_module
from backend.rag.embedder import DEFAULT_STORE, LocalSemanticEmbedder


class _DummyFaissIndex:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.add_calls: list[np.ndarray] = []
        self._vectors = np.empty((0, dim), dtype="float32")

    def add(self, vectors: np.ndarray) -> None:
        arr = np.asarray(vectors, dtype="float32")
        self.add_calls.append(arr.copy())
        if self._vectors.size == 0:
            self._vectors = arr
            return
        self._vectors = np.vstack([self._vectors, arr])

    def search(self, vectors: np.ndarray, k: int):
        query = np.asarray(vectors, dtype="float32")
        if self._vectors.size == 0:
            return (
                np.zeros((query.shape[0], k), dtype="float32"),
                -np.ones((query.shape[0], k), dtype="int64"),
            )
        scores = query @ self._vectors.T
        order = np.argsort(-scores, axis=1)
        top_indices = order[:, :k].astype("int64")
        top_scores = np.take_along_axis(scores, top_indices, axis=1).astype(
            "float32"
        )
        return top_scores, top_indices


def test_default_faiss_embed_and_search_regression(monkeypatch):
    monkeypatch.setattr(
        embedder_module,
        "faiss",
        SimpleNamespace(IndexFlatIP=_DummyFaissIndex),
    )
    monkeypatch.setattr(
        LocalSemanticEmbedder, "_init_embedding_model", lambda _self: object()
    )

    vectors_by_text = {
        "alpha": [3.0, 4.0],
        "beta": [4.0, 3.0],
        "query": [3.0, 4.0],
    }

    def _fake_embed_np(self, texts, batch_size=64):
        _ = batch_size
        return np.asarray(
            [vectors_by_text[text] for text in texts], dtype="float32"
        )

    monkeypatch.setattr(LocalSemanticEmbedder, "_embed_np", _fake_embed_np)

    embedder = LocalSemanticEmbedder(backend="mock")
    assert embedder.store == DEFAULT_STORE == "faiss"

    indexed = embedder.embed_and_index(
        ["alpha", "beta"],
        metadatas=[{"namespace": "thread:1"}, {"namespace": "thread:2"}],
    )
    assert indexed == {"store": "faiss", "count": 2}

    norms = np.linalg.norm(embedder._index.add_calls[0], axis=1)
    np.testing.assert_allclose(norms, np.ones(2), atol=1e-6)

    hits = embedder.search("query", k=1, namespace="thread:1")
    assert len(hits) == 1
    assert hits[0]["text"] == "alpha"
