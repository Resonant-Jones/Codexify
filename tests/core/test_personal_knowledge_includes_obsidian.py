from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_WORKSPACE,
)
from guardian.obsidian.indexer import OBSIDIAN_NAMESPACE


def _build_broker(vector_search_side_effect):
    chatlog_db = AsyncMock()
    chatlog_db.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "What changed?"}]
    )
    chatlog_db.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": "user-1", "project_id": 42}
    )
    chatlog_db.get_connector_config = MagicMock(
        return_value={
            "name": "obsidian_local",
            "type": "obsidian",
            "settings": {"vault_root": "/vault", "enabled": True},
        }
    )

    vector_store = AsyncMock()
    vector_store.search = MagicMock(side_effect=vector_search_side_effect)

    broker = ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=AsyncMock(),
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )
    broker.get_scoped_documents = AsyncMock(
        return_value={"project": [], "thread": [], "global": []}
    )
    return broker, vector_store


@pytest.mark.asyncio
async def test_personal_knowledge_includes_obsidian_when_hits_exist() -> None:
    def _search(query, k, namespace=None, user_id=None):
        if namespace == "thread:1":
            return [
                {
                    "text": "thread semantic hit",
                    "user_id": "user-1",
                    "metadata": {"message_id": 1},
                    "score": 0.92,
                }
            ]
        if namespace == "obsidian:local":
            return [
                {
                    "text": "obsidian semantic hit",
                    "user_id": "user-1",
                    "metadata": {"filename": "note.md"},
                    "score": 0.97,
                }
            ]
        return []

    broker, vector_store = _build_broker(_search)

    context, trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        source_mode=SOURCE_MODE_PERSONAL_KNOWLEDGE,
        user_id="user-1",
    )

    assert context["semantic"]
    assert len(context["obsidian"]) == 1
    obsidian_hit = context["obsidian"][0]
    assert obsidian_hit["text"] == "obsidian semantic hit"
    assert obsidian_hit["user_id"] == "user-1"
    assert obsidian_hit["namespace"] == "obsidian:local"
    assert obsidian_hit["source_type"] == "obsidian"
    assert obsidian_hit["role"] == "document"
    assert obsidian_hit["retrieval_lane"] == "obsidian_semantic"
    assert obsidian_hit["metadata"]["filename"] == "note.md"
    assert obsidian_hit["metadata"]["namespace"] == "obsidian:local"
    assert "retrieval_warnings" not in context
    assert trace["source_mode"] == SOURCE_MODE_PERSONAL_KNOWLEDGE
    assert [
        call.kwargs.get("namespace")
        for call in vector_store.search.call_args_list
    ] == ["thread:1", "obsidian:local"]


@pytest.mark.asyncio
async def test_personal_knowledge_warns_when_obsidian_is_empty() -> None:
    def _search(query, k, namespace=None, user_id=None):
        if namespace == "thread:1":
            return [
                {
                    "text": "thread semantic hit",
                    "user_id": "user-1",
                    "metadata": {"message_id": 1},
                    "score": 0.91,
                }
            ]
        if namespace == "obsidian:local":
            return []
        return []

    broker, vector_store = _build_broker(_search)

    context, trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        source_mode=SOURCE_MODE_PERSONAL_KNOWLEDGE,
        user_id="user-1",
    )

    assert context["semantic"]
    assert context["obsidian"] == []
    assert context["retrieval_warnings"] == [
        "obsidian_empty_in_personal_knowledge"
    ]
    assert trace["source_mode"] == SOURCE_MODE_PERSONAL_KNOWLEDGE
    assert [
        call.kwargs.get("namespace")
        for call in vector_store.search.call_args_list
    ] == ["thread:1", "obsidian:local"]


@pytest.mark.asyncio
async def test_workspace_retrieval_falls_back_to_backend_obsidian_hits_when_local_search_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend_hit = {
        "id": "obs-backend-1",
        "text": "The workspace-only answer is amber-lattice-47.",
        "metadata": {"filename": "sentinel.md"},
        "score": 0.99,
    }

    def _search(query, k, namespace=None, user_id=None):
        if namespace == "thread:1":
            return [
                {
                    "text": "thread semantic hit",
                    "user_id": "user-1",
                    "metadata": {"message_id": 1},
                    "score": 0.92,
                }
            ]
        if namespace == "obsidian:local":
            return []
        return []

    broker, vector_store = _build_broker(_search)

    backend_calls: list[dict[str, object]] = []

    def _backend_results(*, query, user_id, k):
        backend_calls.append({"query": query, "user_id": user_id, "k": k})
        return [dict(backend_hit)]

    monkeypatch.setattr(
        "guardian.context.broker._workspace_backend_obsidian_results",
        _backend_results,
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        source_mode=SOURCE_MODE_WORKSPACE,
        user_id="user-1",
    )

    assert context["semantic"]
    assert len(context["obsidian"]) == 1
    obsidian_hit = context["obsidian"][0]
    assert obsidian_hit["id"] == "obs-backend-1"
    assert obsidian_hit["text"] == (
        "The workspace-only answer is amber-lattice-47."
    )
    assert obsidian_hit["namespace"] == OBSIDIAN_NAMESPACE
    assert obsidian_hit["source_type"] == "obsidian"
    assert obsidian_hit["role"] == "document"
    assert obsidian_hit["retrieval_lane"] == "obsidian_semantic"
    assert obsidian_hit["policy_reason"] == "workspace"
    assert obsidian_hit["metadata"]["namespace"] == OBSIDIAN_NAMESPACE
    assert obsidian_hit["metadata"]["source_type"] == "obsidian"
    assert obsidian_hit["meta"]["namespace"] == OBSIDIAN_NAMESPACE
    assert obsidian_hit["meta"]["source_type"] == "obsidian"
    assert context["semantic"][-1]["namespace"] == OBSIDIAN_NAMESPACE
    assert trace["source_mode"] == SOURCE_MODE_WORKSPACE
    assert trace["retrieval_provenance"]["retrieval_status"] == (
        "workspace_local_success"
    )
    assert (
        trace["retrieval_provenance"]["source_hit_counts"]["obsidian_semantic"]
        == 1
    )
    assert backend_calls == [
        {
            "query": "What changed?",
            "user_id": "user-1",
            "k": 4,
        }
    ]
    assert [
        call.kwargs.get("namespace")
        for call in vector_store.search.call_args_list
    ] == ["thread:1", "obsidian:local"]
