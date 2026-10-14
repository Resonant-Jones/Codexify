"""Live storage proof for Obsidian ingest using real Chroma search."""

from pathlib import Path

import pytest

from guardian.cli import ingest_cli
from guardian.obsidian.indexer import OBSIDIAN_NAMESPACE
from guardian.vector.store import VectorStore

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "obsidian_vault"
)
DISTINCTIVE_NOTE = FIXTURE_ROOT / "Distinctive Retrieval.md"


def test_obsidian_live_chroma_retrieval(tmp_path, monkeypatch):
    pytest.importorskip("chromadb")

    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(chroma_path))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "obsidian_live_proof")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")

    ingest_cli.ingest_obsidian(str(FIXTURE_ROOT))

    store = VectorStore()
    query = DISTINCTIVE_NOTE.read_text(encoding="utf-8")
    results = store.embedder._chroma_collection.query(
        query_embeddings=store.embedder._embed_np([query]).tolist(),
        n_results=3,
        where={"namespace": OBSIDIAN_NAMESPACE},
        include=["documents", "metadatas"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    hit_index = next(
        index
        for index, document in enumerate(documents)
        if "mariner-signal-lattice" in document
    )
    assert metadatas[hit_index]["path"].endswith("Distinctive Retrieval.md")
