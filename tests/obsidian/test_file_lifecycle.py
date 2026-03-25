"""File lifecycle coverage for Obsidian ingest (rename/move/delete)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from guardian.cli import ingest_cli
from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.vector.store import VectorStore

pytestmark = pytest.mark.xfail(
    reason="Deferred for beta read-only Obsidian mode: file lifecycle pruning guarantees are out of scope; supported refresh is full namespace rebuild.",
    strict=False,
)

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "obsidian_vault"
)


@pytest.mark.asyncio
async def test_obsidian_file_lifecycle_prune(tmp_path, monkeypatch):
    chromadb = pytest.importorskip("chromadb")

    vault_root = tmp_path / "vault"
    shutil.copytree(FIXTURE_ROOT, vault_root)

    chroma_path = tmp_path / "chroma"
    collection_name = "obsidian_lifecycle"

    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "chroma")
    monkeypatch.setenv("CODEXIFY_CHROMA_PATH", str(chroma_path))
    monkeypatch.setenv("CODEXIFY_COLLECTION", collection_name)
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")

    def get_collection():
        client = chromadb.PersistentClient(path=str(chroma_path))
        return client.get_or_create_collection(name=collection_name)

    def has_id(collection, source_id: str) -> bool:
        record = collection.get(ids=[source_id])
        return bool(record.get("ids"))

    ingest_cli.ingest_obsidian(str(vault_root), prune=False)
    collection = get_collection()
    assert collection.count() == 4

    old_path = vault_root / "Plain Note.md"
    renamed_path = vault_root / "Plain Note Renamed.md"
    old_id = ingest_cli._obsidian_source_id(vault_root, old_path)
    new_id = ingest_cli._obsidian_source_id(vault_root, renamed_path)
    old_path.rename(renamed_path)

    ingest_cli.ingest_obsidian(str(vault_root), prune=False)
    collection = get_collection()
    assert collection.count() == 5
    assert has_id(collection, old_id)
    assert has_id(collection, new_id)

    ingest_cli.ingest_obsidian(str(vault_root), prune=True)
    collection = get_collection()
    assert collection.count() == 4
    assert not has_id(collection, old_id)
    assert has_id(collection, new_id)

    move_src = vault_root / "Tagged Metadata.md"
    move_dst_dir = vault_root / "Moved"
    move_dst_dir.mkdir()
    move_dst = move_dst_dir / "Tagged Metadata.md"
    move_old_id = ingest_cli._obsidian_source_id(vault_root, move_src)
    move_new_id = ingest_cli._obsidian_source_id(vault_root, move_dst)
    move_src.rename(move_dst)

    ingest_cli.ingest_obsidian(str(vault_root), prune=True)
    collection = get_collection()
    assert collection.count() == 4
    assert not has_id(collection, move_old_id)
    assert has_id(collection, move_new_id)

    delete_path = vault_root / "Frontmatter Note.md"
    delete_id = ingest_cli._obsidian_source_id(vault_root, delete_path)
    deleted_text = delete_path.read_text(encoding="utf-8")
    delete_path.unlink()

    ingest_cli.ingest_obsidian(str(vault_root), prune=True)
    collection = get_collection()
    assert collection.count() == 3
    assert not has_id(collection, delete_id)

    retriever = MemoryOSRetriever(VectorStore())
    results = await retriever.retrieve(deleted_text, limit=3)
    assert all(r["metadata"].get("source_id") != delete_id for r in results)
