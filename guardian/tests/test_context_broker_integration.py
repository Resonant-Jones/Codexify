from __future__ import annotations

from typing import Any

import pytest

from guardian.context.broker import ContextBroker
from guardian.core.config import Settings


class DummyChatlog:
    def last_messages(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"role": "user", "content": "hello"}]


class DummyVector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, str | None]] = []

    def search(
        self,
        query: str,
        k: int = 5,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((query, k, namespace))
        return [
            {
                "id": "doc-1",
                "text": "alpha snippet",
                "score": 0.9,
                "metadata": {"filename": "alpha.txt"},
            }
        ]


@pytest.mark.asyncio
async def test_context_broker_assemble_integration():
    vector = DummyVector()
    chatlog = DummyChatlog()
    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False)
    broker = ContextBroker(chatlog, vector, settings=settings)

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode="normal",
        user_id="default",
    )

    assert vector.calls == [("hello", 4, "thread:1")]
    assert context["messages"] == [{"role": "user", "content": "hello"}]
    assert context["semantic"] == [
        {
            "id": "doc-1",
            "text": "alpha snippet",
            "score": 0.9,
            "metadata": {"filename": "alpha.txt"},
        }
    ]
    assert trace["documents"] == [
        {
            "id": "doc-1",
            "title": "alpha.txt",
            "score": 0.9,
            "snippet": "alpha snippet...",
        }
    ]
