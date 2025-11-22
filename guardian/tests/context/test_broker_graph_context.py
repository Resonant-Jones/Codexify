import asyncio

import pytest

from guardian.context.broker import ContextBroker
from guardian.core.config import Settings


class DummyVector:
    def search(self, *args, **kwargs):
        return []


class DummyChatlog:
    def last_messages(self, *args, **kwargs):
        return []


@pytest.mark.asyncio
async def test_graph_context_flag_off(monkeypatch):
    calls = {"graph": 0}

    class TestBroker(ContextBroker):
        async def _get_graph_context(self, **kwargs):
            calls["graph"] += 1
            return [{"kind": "graph-fact", "text": "should-not-appear"}]

    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False)
    broker = TestBroker(DummyChatlog(), DummyVector(), settings=settings, memory_store=None, sensors=None)

    bundle = await broker.assemble(thread_id=1, query="hi", user_id="demo")
    assert calls["graph"] == 0
    assert bundle.get("graph") == []


@pytest.mark.asyncio
async def test_graph_context_flag_on(monkeypatch):
    class TestBroker(ContextBroker):
        async def _get_graph_context(self, **kwargs):
            return [{"kind": "graph-fact", "text": "from-graph", "source": "neo4j"}]

    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=True)
    broker = TestBroker(DummyChatlog(), DummyVector(), settings=settings, memory_store=None, sensors=None)

    bundle = await broker.assemble(thread_id=1, query="hi", user_id="demo")
    assert bundle.get("graph")
    assert bundle["graph"][0]["text"] == "from-graph"


@pytest.mark.asyncio
async def test_graph_context_failure_soft(monkeypatch):
    class TestBroker(ContextBroker):
        async def _get_graph_context(self, **kwargs):
            raise RuntimeError("boom")

    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=True)
    broker = TestBroker(DummyChatlog(), DummyVector(), settings=settings, memory_store=None, sensors=None)

    bundle = await broker.assemble(thread_id=1, query="hi", user_id="demo")
    assert bundle.get("graph") == []
