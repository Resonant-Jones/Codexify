from __future__ import annotations

import pytest

from guardian.workers import (
    chat_embedding_worker,
    document_embed_worker,
    embedding_backfill_worker,
)


def test_chat_embedding_worker_fails_fast_on_vector_store_init(monkeypatch):
    class BoomStore:
        def __init__(self):
            raise RuntimeError("vector init failed")

    monkeypatch.setattr(chat_embedding_worker, "VectorStore", BoomStore)

    with pytest.raises(SystemExit):
        chat_embedding_worker.run_forever()


def test_document_embed_worker_fails_fast_on_embedder_boot(monkeypatch):
    import guardian.runtime.embed.embedder as runtime_embed

    class BoomEmbedder:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("embedder boot failed")

    monkeypatch.setattr(runtime_embed, "CodexifyEmbedder", BoomEmbedder)

    with pytest.raises(SystemExit):
        document_embed_worker.run_forever()


def test_embedding_backfill_worker_fails_before_processing_when_vector_store_invalid(
    monkeypatch,
):
    class BoomStore:
        def __init__(self):
            raise RuntimeError("vector init failed")

    monkeypatch.setattr(embedding_backfill_worker, "VectorStore", BoomStore)
    monkeypatch.setattr(
        embedding_backfill_worker, "_acquire_lock", lambda _path: True
    )
    monkeypatch.setattr(
        embedding_backfill_worker, "_release_lock", lambda _path: None
    )
    monkeypatch.setattr(
        embedding_backfill_worker,
        "update_status_snapshot",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        embedding_backfill_worker,
        "_resolve_database_url",
        lambda: "sqlite+pysqlite:///:memory:",
    )
    monkeypatch.setattr(
        embedding_backfill_worker,
        "fetch_unembedded_messages",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("should not process batches")
        ),
    )

    exit_code = embedding_backfill_worker.run_once()
    assert exit_code == 1
