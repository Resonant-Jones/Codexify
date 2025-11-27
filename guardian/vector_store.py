from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class VectorEntry:
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class VectorStore:
    """Minimal in-memory vector store with cosine similarity search.

    This is a lightweight stub intended to unblock the API. It stores
    vectors in memory only and is not suitable for large-scale usage.
    """

    def __init__(self) -> None:
        self._entries: list[VectorEntry] = []

    def add(
        self, *, text: str, embedding: list[float], metadata: dict[str, Any]
    ) -> None:
        self._entries.append(
            VectorEntry(text=text, embedding=embedding, metadata=metadata)
        )

    def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        scored: list[tuple[float, VectorEntry]] = []
        for e in self._entries:
            score = _cosine_similarity(query_embedding, e.embedding)
            scored.append((score, e))
        scored.sort(key=lambda t: t[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, entry in scored[: max(0, top_k)]:
            results.append(
                {
                    "text": entry.text,
                    "score": score,
                    "metadata": entry.metadata,
                }
            )
        return results
