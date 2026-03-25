"""Proof test that Obsidian ingest content can be retrieved."""

from pathlib import Path

import pytest

from guardian.cli import ingest_cli
from guardian.memoryos.retriever import MemoryOSRetriever

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "obsidian_vault"
)


class InMemoryVectorStore:
    """Minimal vector store seam for ingest+retrieve proof.

    This avoids real embedding backends; it only proves that ingest packaging
    survives into MemoryOSRetriever with metadata intact.
    """

    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def add_texts(self, items: list[dict[str, object]]) -> int:
        for item in items:
            self.items.append(
                {
                    "text": item.get("text", ""),
                    "meta": item.get("meta", {}),
                    "score": 1.0,
                }
            )
        return len(items)

    def search(self, query: str, k: int, namespace: str | None = None):
        needle = query.lower()
        hits = [
            item
            for item in self.items
            if needle in str(item.get("text", "")).lower()
        ]
        if not hits:
            hits = list(self.items)
        return hits[:k]


@pytest.mark.asyncio
async def test_obsidian_ingest_retrieval_proof():
    store = InMemoryVectorStore()
    items = ingest_cli._build_obsidian_items(FIXTURE_ROOT)
    assert store.add_texts(items) == len(items)

    retriever = MemoryOSRetriever(store)
    results = await retriever.retrieve("mariner-signal-lattice", limit=3)

    assert results
    hit = next(r for r in results if "mariner-signal-lattice" in r["text"])
    assert hit["metadata"]["path"].endswith("Distinctive Retrieval.md")
