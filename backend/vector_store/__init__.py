"""Pluggable vector store abstractions for the backend."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


DEFAULT_NAMESPACE = "default"


class VectorStore(Protocol):
    """Minimal protocol every vector store implementation must satisfy."""

    def upsert(
        self,
        *,
        id: str,
        embedding: Sequence[float],
        metadata: Mapping[str, Any],
    ) -> None:
        """Persist or update an embedding for ``id``."""

    def query(
        self,
        *,
        embedding: Sequence[float],
        top_k: int,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the ``top_k`` most similar entries to ``embedding``."""

    def delete(
        self,
        *,
        namespace: str | None = None,
        ids: Sequence[str] | None = None,
    ) -> int:
        """Delete embeddings by namespace and/or identifiers; return rows removed."""


__all__ = ["DEFAULT_NAMESPACE", "VectorStore"]
