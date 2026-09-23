from __future__ import annotations

from guardian.queue.redis_queue import CHAT_IMPORT_EMBED_TASK_TYPE
from guardian.vector.store import VectorStore
from guardian.workers import chat_embedding_worker


class _Store:
    def __init__(self):
        self.items = []

    def add_texts(self, items):
        self.items.extend(items)
        return len(items)


def test_import_embedding_redelivery_uses_one_canonical_vector_id(monkeypatch):
    store = _Store()
    db = object()
    statuses = []
    monkeypatch.setattr(
        chat_embedding_worker,
        "_load_message",
        lambda _db, _message_id: {
            "id": 42,
            "thread_id": 7,
            "role": "assistant",
            "content": "imported assistant marker",
            "extra_meta": {"embedding_status": "pending"},
        },
    )
    monkeypatch.setattr(
        chat_embedding_worker,
        "_update_embedding_status",
        lambda _db, _message_id, **kwargs: statuses.append(kwargs["status"]),
    )
    payload = {
        "type": CHAT_IMPORT_EMBED_TASK_TYPE,
        "message_id": 42,
        "thread_id": 7,
        "role": "assistant",
        "content": "imported assistant marker",
        "meta": {
            "user_id": "account-a",
            "source_thread_id": "source-1",
            "source_message_id": "source-message-1",
        },
    }

    assert chat_embedding_worker.process_chat_embed_task(
        payload, vector_store=store, db=db
    )
    assert chat_embedding_worker.process_chat_embed_task(
        payload, vector_store=store, db=db
    )
    assert [item["id"] for item in store.items] == [
        "chat-import-message:42",
        "chat-import-message:42",
    ]
    assert all(
        item["meta"]["user_id"] == "account-a"
        and item["meta"]["source_message_id"] == "source-message-1"
        for item in store.items
    )
    assert statuses == ["processing", "ready", "processing", "ready"]

    class _Embedder:
        def __init__(self):
            self.ids = []

        def embed_and_index(self, _texts, *, metadatas, ids):
            self.ids.append((ids, metadatas[0]["source_message_id"]))

    chroma_store = object.__new__(VectorStore)
    chroma_store.store = "chroma"
    chroma_store.embedder = _Embedder()
    for item in store.items:
        chroma_store.add_texts([item])
    assert chroma_store.embedder.ids == [
        (["chat-import-message:42"], "source-message-1"),
        (["chat-import-message:42"], "source-message-1"),
    ]


def test_ordinary_chat_embedding_keeps_existing_vector_id_behavior(monkeypatch):
    store = _Store()
    monkeypatch.setattr(chat_embedding_worker, "_load_message", lambda *_args: None)
    assert chat_embedding_worker.process_chat_embed_task(
        {"content": "ordinary chat", "thread_id": 9, "role": "user"},
        vector_store=store,
        db=object(),
    )
    assert "id" not in store.items[0]
