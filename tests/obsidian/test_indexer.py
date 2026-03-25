from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from guardian.cli import ingest_cli
from guardian.obsidian import indexer as obsidian_indexer


class StubEmbedder:
    def __init__(self, existing_ids=None, calls=None):
        self.existing_ids = list(existing_ids or [])
        self.calls = calls if calls is not None else []

    def get_ids(self, where):
        self.calls.append(("get_ids", where))
        return list(self.existing_ids)

    def delete_by_ids(self, ids):
        self.calls.append(("delete_by_ids", list(ids)))
        return len(ids)


class StubVectorStore:
    def __init__(self, existing_ids=None):
        self.calls = []
        self.embedder = StubEmbedder(
            existing_ids=existing_ids, calls=self.calls
        )
        self.added_items = []

    def add_texts(self, items):
        self.calls.append(("add_texts", len(items)))
        self.added_items.extend(items)
        return len(items)


def _setup_vault(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    allowed_dir = vault / "allowed"
    allowed_dir.mkdir()
    outside_dir = vault / "outside"
    outside_dir.mkdir()
    allowed_file = allowed_dir / "Note.md"
    allowed_file.write_text("# Allowed\n", encoding="utf-8")
    outside_file = outside_dir / "Outside.md"
    outside_file.write_text("# Outside\n", encoding="utf-8")
    return vault, allowed_dir, outside_dir, allowed_file, outside_file


def test_allowlisted_notes_indexed_and_outside_excluded(tmp_path):
    vault, allowed_dir, outside_dir, allowed_file, outside_file = _setup_vault(
        tmp_path
    )
    store = StubVectorStore(existing_ids=[])
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)

    summary = obsidian_indexer.index_obsidian_vault_readonly(
        vault,
        allowed_paths=[allowed_dir],
        vector_store=store,
        now=now,
    )

    assert summary["indexed"] == 1
    assert summary["namespace"] == obsidian_indexer.OBSIDIAN_NAMESPACE

    indexed_paths = [item["meta"]["source_path"] for item in store.added_items]
    assert str(allowed_file.resolve()) in indexed_paths
    assert str(outside_file.resolve()) not in indexed_paths

    indexed_item = store.added_items[0]
    assert (
        indexed_item["meta"]["namespace"] == obsidian_indexer.OBSIDIAN_NAMESPACE
    )
    assert indexed_item["meta"]["source_type"] == "obsidian"
    assert (
        indexed_item["meta"]["vault_namespace"]
        == obsidian_indexer.OBSIDIAN_NAMESPACE
    )
    assert indexed_item["meta"]["indexed_at"] == now.isoformat()
    assert indexed_item["meta"]["content_hash"]


def test_readonly_mode_requires_rebuild_refresh(tmp_path):
    vault, allowed_dir, _, _, _ = _setup_vault(tmp_path)
    store = StubVectorStore(existing_ids=[])

    with pytest.raises(
        ValueError, match="obsidian_beta_requires_rebuild_refresh"
    ):
        obsidian_indexer.index_obsidian_vault_readonly(
            vault,
            allowed_paths=[allowed_dir],
            vector_store=store,
            rebuild=False,
        )


def test_path_traversal_rejected(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    store = StubVectorStore(existing_ids=[])

    with pytest.raises(ValueError):
        obsidian_indexer.index_obsidian_vault(
            vault,
            allowed_paths=[outside],
            vector_store=store,
        )


def test_namespace_rebuild_deletes_existing_ids(tmp_path):
    vault, allowed_dir, _, _, _ = _setup_vault(tmp_path)
    store = StubVectorStore(existing_ids=["a", "b"])

    summary = obsidian_indexer.rebuild_obsidian_namespace(
        vault,
        allowed_paths=[allowed_dir],
        vector_store=store,
    )

    assert summary["deleted"] == 2
    assert summary["mode"] == obsidian_indexer.BETA_READONLY_MODE
    assert summary["read_only"] is True
    assert summary["refresh_strategy"] == "rebuild"
    assert store.calls[0] == (
        "get_ids",
        {"namespace": obsidian_indexer.OBSIDIAN_NAMESPACE},
    )
    assert store.calls[1] == ("delete_by_ids", ["a", "b"])
    assert store.calls[2][0] == "add_texts"


def test_cli_delegates_to_indexer(monkeypatch, tmp_path):
    called = {}

    def fake_index(
        vault_root,
        allowed_paths=None,
        allowed_tags=None,
        vector_store=None,
        now=None,
        rebuild=True,
    ):
        called["vault_root"] = vault_root
        called["rebuild"] = rebuild
        return {
            "vault_root": str(Path(vault_root).resolve()),
            "namespace": obsidian_indexer.OBSIDIAN_NAMESPACE,
            "mode": obsidian_indexer.BETA_READONLY_MODE,
            "read_only": True,
            "refresh_strategy": "rebuild",
            "indexed": 0,
            "deleted": 0,
            "scanned": 0,
            "failures": [],
        }

    monkeypatch.setattr(ingest_cli, "index_obsidian_vault_readonly", fake_index)

    ingest_cli.ingest_obsidian(str(tmp_path))

    assert called["vault_root"] == str(tmp_path)
    assert called["rebuild"] is True
