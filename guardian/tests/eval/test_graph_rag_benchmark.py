import asyncio
import json
from pathlib import Path

import pytest

from guardian.eval.run_graph_rag_benchmark import run_prompt
from guardian.core.config import Settings


@pytest.mark.asyncio
async def test_run_prompt_with_graph(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("GROQ_API_KEY", "dummy")

    async def fake_get_graph_context(self, **kwargs):
        return [{"kind": "graph-fact", "text": "graph fact", "source": "neo4j"}]

    monkeypatch.setattr(
        "guardian.eval.run_graph_rag_benchmark.ContextBroker._get_graph_context",
        fake_get_graph_context,
    )
    monkeypatch.setattr(
        "guardian.eval.run_graph_rag_benchmark.chat_with_ai", lambda messages, **kw: "answer"
    )

    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=True)
    prompt_spec = {
        "id": "p1",
        "user_id": "demo",
        "thread_title": "t",
        "seed_docs": [],
        "question": "What is graph?",
    }
    res = await run_prompt(prompt_spec, settings, mode="with-graph")
    assert res["mode"] == "with-graph"
    assert res["answer"] == "answer"


@pytest.mark.asyncio
async def test_run_prompt_without_graph(monkeypatch):
    calls = {"graph": 0}

    async def fake_get_graph_context(self, **kwargs):
        calls["graph"] += 1
        return []

    monkeypatch.setattr(
        "guardian.eval.run_graph_rag_benchmark.ContextBroker._get_graph_context",
        fake_get_graph_context,
    )
    monkeypatch.setattr(
        "guardian.eval.run_graph_rag_benchmark.chat_with_ai", lambda messages, **kw: "answer"
    )

    settings = Settings(GUARDIAN_ENABLE_GRAPH_CONTEXT=False)
    prompt_spec = {
        "id": "p1",
        "user_id": "demo",
        "thread_title": "t",
        "seed_docs": [],
        "question": "What is graph?",
    }
    res = await run_prompt(prompt_spec, settings, mode="without-graph")
    assert res["mode"] == "without-graph"
    assert calls["graph"] == 0
