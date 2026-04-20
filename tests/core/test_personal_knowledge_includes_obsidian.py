from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
)


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
    assert context["obsidian"] == [
        {
            "text": "obsidian semantic hit",
            "user_id": "user-1",
            "metadata": {"filename": "note.md"},
            "score": 0.97,
        }
    ]
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
