from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker


def _make_broker() -> ContextBroker:
    chatlog_db = AsyncMock()
    chatlog_db.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": "user-1", "project_id": 7}
    )
    chatlog_db.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "hello"}]
    )
    chatlog_db.get_connector_config = MagicMock(return_value=None)
    chatlog_db.list_facts = MagicMock(return_value=[])

    vector_store = AsyncMock()
    vector_store.search = MagicMock(return_value=[])

    broker = ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=AsyncMock(),
        sensors=None,
    )
    broker._fetch_messages = AsyncMock(
        return_value=[{"id": 1, "role": "user", "content": "hello"}]
    )
    broker._search_semantic = AsyncMock(return_value=[])
    broker._search_memory = AsyncMock(
        return_value=([], {"attempted": False, "status": "skipped", "reason": "no_retriever", "count": 0})
    )
    broker._fetch_verified_personal_facts = AsyncMock(
        return_value=(
            [],
            {
                "attempted": False,
                "status": "skipped",
                "reason": "no_fact_adapter",
                "count": 0,
                "retrieved_count": 0,
                "included_ids": [],
                "user_id": "user-1",
            },
        )
    )
    broker.get_scoped_documents = AsyncMock(
        return_value={"project": [], "thread": [], "global": []}
    )
    return broker


@pytest.mark.asyncio
async def test_blank_context_command_query_returns_empty_without_retrieval():
    broker = _make_broker()
    broker._retrieve_obsidian_documents = AsyncMock()

    results = await broker.retrieve_obsidian_context_command(
        query="   ",
        user_id="user-1",
        project_id=7,
    )

    assert results == []
    broker._retrieve_obsidian_documents.assert_not_called()


@pytest.mark.asyncio
async def test_context_command_passes_user_and_project_scope():
    broker = _make_broker()
    broker._retrieve_obsidian_documents = AsyncMock(
        return_value=[{"text": "obsidian hit"}]
    )

    results = await broker.retrieve_obsidian_context_command(
        query="memory decay",
        user_id="user-1",
        project_id=7,
        k=4,
        retrieval_policy={"source_mode": "project"},
    )

    broker._retrieve_obsidian_documents.assert_awaited_once_with(
        "memory decay",
        user_id="user-1",
        project_scope=7,
        k=4,
        retrieval_policy={"source_mode": "project"},
    )
    assert results[0]["text"] == "obsidian hit"
    assert results[0]["source_type"] == "obsidian"
    assert results[0]["retrieval_lane"] == "connector_context"
    assert results[0]["connector_id"] == "obsidian"
    assert results[0]["context_command"] is True
    assert results[0]["metadata"]["connector_id"] == "obsidian"
    assert results[0]["meta"]["retrieval_lane"] == "connector_context"
    assert results[0]["meta"]["context_command"] is True


@pytest.mark.asyncio
async def test_assemble_keeps_ordinary_source_mode_behavior():
    broker = _make_broker()
    broker.retrieve_obsidian_context_command = AsyncMock(
        side_effect=AssertionError("context command helper should not run")
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="test query",
        depth_mode="normal",
        user_id="user-1",
        source_mode="project",
    )

    assert context["messages"]
    assert context["semantic"] == []
    assert trace["source_mode"] == "project"
    broker.retrieve_obsidian_context_command.assert_not_called()
