from __future__ import annotations

from typing import Any

from guardian.vector import store as vector_store_module


class _RecordingEmbedder:
    def __init__(self) -> None:
        self.index_calls: list[dict[str, Any]] = []
        self.search_calls: list[dict[str, Any]] = []

    def embed_and_index(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
    ) -> dict[str, Any]:
        self.index_calls.append(
            {
                "texts": list(texts),
                "metadatas": list(metadatas or []),
                "ids_prefix": ids_prefix,
            }
        )
        return {"count": len(texts)}

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        self.search_calls.append(
            {"query": query, "k": k, "namespace": namespace}
        )
        return []


class _LegacyEmbedder:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def embed_and_index(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids_prefix: str = "doc",
    ) -> dict[str, Any]:
        return {"count": len(texts)}

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "k": k})
        return []


def test_add_texts_assigns_namespace_metadata(monkeypatch):
    recorder = _RecordingEmbedder()
    monkeypatch.setattr(
        vector_store_module,
        "Embedder",
        lambda **_: recorder,
    )

    store = vector_store_module.VectorStore()
    count = store.add_texts(
        [
            {"text": "alpha", "meta": {"thread_id": 7}},
            {"text": "beta", "meta": {"project_id": "55"}},
            {"text": "gamma", "meta": {"namespace": "custom:scope"}},
            {"text": "delta", "meta": {}},
            {"text": "epsilon", "namespace": "top:level"},
        ]
    )

    assert count == 5
    metadatas = recorder.index_calls[0]["metadatas"]
    assert [meta.get("namespace") for meta in metadatas] == [
        "thread:7",
        "project:55",
        "custom:scope",
        "global",
        "top:level",
    ]


def test_search_forwards_namespace_to_embedder(monkeypatch):
    recorder = _RecordingEmbedder()
    monkeypatch.setattr(
        vector_store_module,
        "Embedder",
        lambda **_: recorder,
    )

    store = vector_store_module.VectorStore()
    store.search("where is it", k=3, namespace=" thread:9 ")

    assert recorder.search_calls == [
        {"query": "where is it", "k": 3, "namespace": "thread:9"}
    ]


def test_search_namespace_is_backward_compatible_with_legacy_embedder(
    monkeypatch,
):
    legacy = _LegacyEmbedder()
    monkeypatch.setattr(
        vector_store_module,
        "Embedder",
        lambda **_: legacy,
    )

    store = vector_store_module.VectorStore()
    store.search("legacy-query", k=2, namespace="thread:1")

    assert legacy.calls == [{"query": "legacy-query", "k": 2}]
