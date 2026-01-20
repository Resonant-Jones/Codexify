"""Integration test for the RAG memory loop."""

from __future__ import annotations

import pytest


class StubChatLog:
    """Minimal chatlog stub for ContextBroker."""

    def list_messages(self, thread_id: int, limit: int = 6, offset: int = 0):
        return []


@pytest.mark.asyncio
async def test_rag_integration_memory_loop(monkeypatch):
    """Write memory -> embed -> retrieve -> assert."""
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "faiss")

    from guardian.context.broker import ContextBroker
    from guardian.vector.store import VectorStore

    vector_store = VectorStore()
    memory_text = "Remember: the Orion window is 2026-01-20."

    vector_store.add_texts(
        [{"text": memory_text, "meta": {"source": "test", "thread_id": 1}}]
    )

    # add_texts is synchronous; this search confirms embed completion.
    matches = vector_store.search(memory_text, k=5)
    assert any(match.get("text") == memory_text for match in matches)

    broker = ContextBroker(
        StubChatLog(),
        vector_store,
        memory_store=object(),
        sensors=None,
    )
    context, _ = await broker.assemble(
        thread_id=2,
        query=memory_text,
        depth_mode="deep",
        user_id="test_user",
    )

    memory_hits = context.get("memory", [])
    assert any(hit.get("text") == memory_text for hit in memory_hits)
