"""Executable Chroma storage/search evaluation pack for Obsidian ingest."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from guardian.cli import ingest_cli
from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.obsidian.indexer import OBSIDIAN_NAMESPACE
from guardian.vector.store import VectorStore

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "obsidian_vault"
)
DISTINCTIVE_NOTE = FIXTURE_ROOT / "Distinctive Retrieval.md"
PLAIN_NOTE = FIXTURE_ROOT / "Plain Note.md"


def _copy_fixture_vault(tmp_path: Path) -> Path:
    vault_root = tmp_path / "vault"
    shutil.copytree(FIXTURE_ROOT, vault_root)
    return vault_root


def _configure_chroma_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, collection: str
) -> Path:
    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(chroma_path))
    monkeypatch.setenv("CODEXIFY_COLLECTION", collection)
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    return chroma_path


def _make_retriever() -> tuple[VectorStore, MemoryOSRetriever]:
    store = VectorStore()
    return store, MemoryOSRetriever(store)


def _query_ingested_docs(store: VectorStore, query: str, limit: int = 3) -> list[dict]:
    collection = store.embedder._chroma_collection
    assert collection is not None
    found = collection.query(
        query_embeddings=store.embedder._embed_np([query]).tolist(),
        n_results=limit,
        where={"namespace": OBSIDIAN_NAMESPACE},
        include=["documents", "metadatas"],
    )
    return [
        {"text": text, "metadata": metadata}
        for text, metadata in zip(found["documents"][0], found["metadatas"][0])
    ]


# Retrieval Eval A
def test_retrieval_eval_distinctive_fixture_hit(tmp_path, monkeypatch):
    pytest.importorskip("chromadb")

    vault_root = _copy_fixture_vault(tmp_path)
    _configure_chroma_runtime(monkeypatch, tmp_path, "retrieval_eval_a")

    ingest_cli.ingest_obsidian(str(vault_root))

    source_id = ingest_cli._obsidian_source_id(
        vault_root, vault_root / DISTINCTIVE_NOTE.name
    )
    store = VectorStore()
    query = DISTINCTIVE_NOTE.read_text(encoding="utf-8")
    results = _query_ingested_docs(store, query)

    assert results
    hit = next(
        result
        for result in results
        if "mariner-signal-lattice" in result["text"]
    )
    assert "distinctive phrase" in hit["text"].lower()
    assert hit["metadata"]["path"].endswith("Distinctive Retrieval.md")
    assert hit["metadata"]["source_id"] == source_id


# Retrieval Eval B
@pytest.mark.asyncio
async def test_retrieval_eval_absent_query_does_not_false_hit_distinctive_note(
    tmp_path, monkeypatch
):
    pytest.importorskip("chromadb")

    vault_root = _copy_fixture_vault(tmp_path)
    _configure_chroma_runtime(monkeypatch, tmp_path, "retrieval_eval_b")

    ingest_cli.ingest_obsidian(str(vault_root))

    source_id = ingest_cli._obsidian_source_id(
        vault_root, vault_root / DISTINCTIVE_NOTE.name
    )
    _, retriever = _make_retriever()

    results, trace = await retriever.retrieve_with_trace(
        "", limit=3, user_id="local-test-account"
    )

    assert results == []
    assert trace["reason"] == "empty_query"
    assert trace["status"] == "skipped"
    assert trace["attempted"] is False
    assert source_id not in {
        result["metadata"].get("source_id") for result in results
    }


# Retrieval Eval C
def test_retrieval_eval_repeat_ingest_is_stable(tmp_path, monkeypatch):
    pytest.importorskip("chromadb")

    vault_root = _copy_fixture_vault(tmp_path)
    _configure_chroma_runtime(monkeypatch, tmp_path, "retrieval_eval_c")

    ingest_cli.ingest_obsidian(str(vault_root))
    ingest_cli.ingest_obsidian(str(vault_root))

    source_path = vault_root / DISTINCTIVE_NOTE.name
    source_id = ingest_cli._obsidian_source_id(vault_root, source_path)
    store = VectorStore()
    collection = store.embedder._chroma_collection
    assert collection is not None
    assert collection.count() == 4

    record = collection.get(ids=[source_id])
    assert record["ids"] == [source_id]
    assert record["metadatas"][0]["source_id"] == source_id
    assert record["documents"][0].startswith("The mariner-signal-lattice")

    results = _query_ingested_docs(store, "mariner-signal-lattice")
    hit = next(
        result
        for result in results
        if result["metadata"].get("source_id") == source_id
    )
    assert hit["text"].startswith("The mariner-signal-lattice")
    assert hit["metadata"]["source_content_hash"] == ingest_cli._hash_text(
        record["documents"][0]
    )


# Retrieval Eval D
def test_retrieval_eval_updated_note_replaces_prior_content(
    tmp_path, monkeypatch
):
    pytest.importorskip("chromadb")

    vault_root = _copy_fixture_vault(tmp_path)
    _configure_chroma_runtime(monkeypatch, tmp_path, "retrieval_eval_d")

    ingest_cli.ingest_obsidian(str(vault_root))

    note_path = vault_root / DISTINCTIVE_NOTE.name
    source_id = ingest_cli._obsidian_source_id(vault_root, note_path)
    original_text = note_path.read_text(encoding="utf-8")
    original_hash = ingest_cli._hash_text(original_text)

    updated_text = (
        "The mariner-signal-lattice recalibrates after midnight.\n"
        "This update should replace the prior content.\n"
    )
    note_path.write_text(updated_text, encoding="utf-8")
    ingest_cli.ingest_obsidian(str(vault_root))

    store = VectorStore()
    collection = store.embedder._chroma_collection
    assert collection is not None

    record = collection.get(ids=[source_id])
    assert record["ids"] == [source_id]
    assert record["metadatas"][0]["source_content_hash"] != original_hash
    assert record["documents"][0] == updated_text

    results = _query_ingested_docs(store, updated_text)
    hit = next(
        result
        for result in results
        if result["metadata"].get("source_id") == source_id
    )
    assert "recalibrates after midnight" in hit["text"]
    assert "distinctive phrase should be retrievable" not in hit["text"]
    assert hit["metadata"]["source_id"] == source_id
    assert hit["metadata"]["source_content_hash"] == ingest_cli._hash_text(
        updated_text
    )
