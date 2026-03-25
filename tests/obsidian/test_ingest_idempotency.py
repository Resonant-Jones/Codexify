"""Idempotency coverage for Obsidian ingest using real vector backend."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from guardian.cli import ingest_cli
from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.vector.store import VectorStore

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "obsidian_vault"
)


@pytest.mark.asyncio
async def test_obsidian_ingest_idempotency(tmp_path, monkeypatch):
    chromadb = pytest.importorskip("chromadb")

    vault_root = tmp_path / "vault"
    shutil.copytree(FIXTURE_ROOT, vault_root)

    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(chroma_path))
    monkeypatch.setenv("CODEXIFY_COLLECTION", "obsidian_idempotency")
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")

    ingest_cli.ingest_obsidian(str(vault_root))

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name="obsidian_idempotency")
    assert collection.count() == 4

    note_path = vault_root / "Distinctive Retrieval.md"
    source_id = ingest_cli._obsidian_source_id(vault_root, note_path)
    record = collection.get(ids=[source_id])
    meta = record["metadatas"][0]
    assert meta["source_type"] == "obsidian"
    assert meta["source_path"] == str(note_path)
    assert meta["source_relpath"] == "Distinctive Retrieval.md"
    first_hash = meta["source_content_hash"]
    assert "mariner-signal-lattice" in record["documents"][0]

    ingest_cli.ingest_obsidian(str(vault_root))
    assert collection.count() == 4
    record = collection.get(ids=[source_id])
    assert record["metadatas"][0]["source_content_hash"] == first_hash

    updated_text = (
        "The mariner-signal-lattice recalibrates after midnight.\n"
        "This update should replace the prior content.\n"
    )
    note_path.write_text(updated_text, encoding="utf-8")
    ingest_cli.ingest_obsidian(str(vault_root))

    assert collection.count() == 4
    record = collection.get(ids=[source_id])
    updated_hash = record["metadatas"][0]["source_content_hash"]
    assert updated_hash != first_hash
    assert updated_hash == ingest_cli._hash_text(updated_text)
    assert "recalibrates after midnight" in record["documents"][0]

    retriever = MemoryOSRetriever(VectorStore())
    results = await retriever.retrieve(updated_text, limit=3)
    hit = next(
        r for r in results if "recalibrates after midnight" in r.get("text", "")
    )
    assert hit["metadata"]["source_id"] == source_id
    assert hit["metadata"]["source_content_hash"] == updated_hash
