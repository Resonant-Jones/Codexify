"""Live runtime proof for Obsidian ingest using real vector backend."""

from pathlib import Path

import pytest

from guardian.cli import ingest_cli
from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.vector.store import VectorStore

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "obsidian_vault"
)
DISTINCTIVE_NOTE = FIXTURE_ROOT / "Distinctive Retrieval.md"


@pytest.mark.asyncio
async def test_obsidian_live_chroma_retrieval(tmp_path, monkeypatch):
    pytest.importorskip("chromadb")

    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(chroma_path))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "obsidian_live_proof")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")

    ingest_cli.ingest_obsidian(str(FIXTURE_ROOT))

    store = VectorStore()
    retriever = MemoryOSRetriever(store)
    query = DISTINCTIVE_NOTE.read_text(encoding="utf-8")
    results = await retriever.retrieve(query, limit=3)

    assert results
    hit = next(r for r in results if "mariner-signal-lattice" in r["text"])
    assert hit["metadata"]["path"].endswith("Distinctive Retrieval.md")
