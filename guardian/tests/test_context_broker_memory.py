from __future__ import annotations

from typing import Any

import pytest

from guardian.context.broker import ContextBroker
from guardian.core import dependencies
from guardian.core.config import Settings
from guardian.memory.query_memory import MemoryStore


class DummyChatlog:
    def last_messages(self, *args, **kwargs):
        return []


class DummyVector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        self.calls.append((query, k))
        return [
            {
                "text": "remembered fact",
                "meta": {"source": "memory"},
                "score": 0.42,
            }
        ]


def test_memory_store_initialized_in_dependencies():
    assert isinstance(dependencies._memory_store, MemoryStore)


@pytest.mark.asyncio
async def test_context_broker_memory_integration():
    vector = DummyVector()
    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False)
    broker = ContextBroker(
        DummyChatlog(),
        vector,
        memory_store=dependencies._memory_store,
        settings=settings,
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode="deep",
        user_id="default",
    )

    assert vector.calls == [("hello", 4), ("hello", 5)]
    assert context["memory"] == [
        {
            "text": "remembered fact",
            "metadata": {"source": "memory"},
            "score": 0.42,
        }
    ]
    assert "documents" in trace
