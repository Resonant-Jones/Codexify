"""Chroma-backed vector store implementation."""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

import chromadb
from chromadb.api import ClientAPI
from chromadb.config import Settings

from . import DEFAULT_NAMESPACE, VectorStore


class ChromaVectorStore(VectorStore):
    """Vector store powered by ChromaDB."""

    def __init__(
        self,
        *,
        client: ClientAPI | None = None,
        collection_prefix: str = "guardian",
    ) -> None:
        self._client = client or _default_client()
        self._collection_prefix = collection_prefix
        self._collections: dict[str, Any] = {}

    def upsert(
        self,
        *,
        id: str,
        embedding: Sequence[float],
        metadata: Mapping[str, Any],
    ) -> None:
        namespace = _namespace_from_metadata(metadata)
        collection = self._get_collection(namespace)
        collection.upsert(
            ids=[id],
            embeddings=[list(embedding)],
            metadatas=[dict(metadata)],
        )

    def query(
        self,
        *,
        embedding: Sequence[float],
        top_k: int,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []

        target_namespace = namespace or DEFAULT_NAMESPACE
        collection = self._get_collection(target_namespace)
        result = collection.query(
            query_embeddings=[list(embedding)], n_results=top_k
        )

        ids = result.get("ids", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        metadatas = result.get("metadatas", [[]])[0] or []

        matches: list[dict[str, Any]] = []
        for idx, doc_id in enumerate(ids):
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            score = 1.0 - distance
            metadata = metadatas[idx] if idx < len(metadatas) else {}
            matches.append(
                {
                    "id": doc_id,
                    "score": score,
                    "metadata": metadata,
                    "namespace": (metadata or {}).get(
                        "namespace", target_namespace
                    ),
                }
            )
        return matches

    def delete(
        self,
        *,
        namespace: str | None = None,
        ids: Sequence[str] | None = None,
    ) -> int:
        target_namespace = namespace or DEFAULT_NAMESPACE
        collection = self._get_collection(target_namespace)
        if ids:
            collection.delete(ids=list(ids))
        elif namespace:
            collection.delete(where={"namespace": target_namespace})
        else:
            collection.delete()
        # Chroma does not report affected rows; return -1 to signal unknown.
        return -1

    def _get_collection(self, namespace: str) -> Any:
        resolved_namespace = namespace or DEFAULT_NAMESPACE
        key = f"{self._collection_prefix}_{resolved_namespace}"
        if key not in self._collections:
            self._collections[key] = self._client.get_or_create_collection(
                name=key
            )
        return self._collections[key]


def _default_client() -> ClientAPI:
    persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY")
    if persist_directory:
        return chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
    return chromadb.Client(settings=Settings(anonymized_telemetry=False))


def _namespace_from_metadata(metadata: Mapping[str, Any]) -> str:
    namespace = (
        metadata.get("namespace") if isinstance(metadata, Mapping) else None
    )
    if isinstance(namespace, str) and namespace.strip():
        return namespace.strip()
    return DEFAULT_NAMESPACE


__all__ = ["ChromaVectorStore"]
