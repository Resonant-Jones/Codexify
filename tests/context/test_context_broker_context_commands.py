from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import SOURCE_MODE_PROJECT


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
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )
    broker._fetch_messages = AsyncMock(
        return_value=[{"id": 1, "role": "user", "content": "hello"}]
    )
    broker._search_semantic = AsyncMock(return_value=[])
    broker._search_memory = AsyncMock(
        return_value=(
            [],
            {
                "attempted": False,
                "status": "skipped",
                "reason": "no_retriever",
                "count": 0,
            },
        )
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


@pytest.fixture
def broker() -> ContextBroker:
    return _make_broker()


@pytest.mark.asyncio
async def test_blank_query_returns_empty_without_retrieval_call(
    broker: ContextBroker,
) -> None:
    broker._retrieve_obsidian_documents = AsyncMock(
        side_effect=AssertionError("obsidian retrieval should not run")
    )

    items = await broker.retrieve_obsidian_context_command(
        query="   ",
        user_id="user-1",
        project_id=42,
    )

    assert items == []
    broker._retrieve_obsidian_documents.assert_not_called()


@pytest.mark.asyncio
async def test_context_command_passes_user_and_project_scope(
    broker: ContextBroker,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_retrieve(
        query, *, user_id, project_scope, k, retrieval_policy=None
    ):
        captured.update(
            {
                "query": query,
                "user_id": user_id,
                "project_scope": project_scope,
                "k": k,
                "retrieval_policy": retrieval_policy,
            }
        )
        return [
            {
                "id": "obs-1",
                "text": "obsidian hit",
                "user_id": user_id,
                "metadata": {"filename": "note.md"},
                "score": 0.93,
            }
        ]

    broker._retrieve_obsidian_documents = _fake_retrieve

    items = await broker.retrieve_obsidian_context_command(
        query=" memory decay ",
        user_id="user-1",
        project_id=42,
        k=3,
        retrieval_policy={"mode": "connector_context"},
    )

    assert captured == {
        "query": "memory decay",
        "user_id": "user-1",
        "project_scope": 42,
        "k": 3,
        "retrieval_policy": {"mode": "connector_context"},
    }
    assert len(items) == 1
    assert items[0]["text"] == "obsidian hit"


@pytest.mark.asyncio
async def test_context_command_annotates_returned_items(
    broker: ContextBroker,
) -> None:
    async def _fake_retrieve(
        query, *, user_id, project_scope, k, retrieval_policy=None
    ):
        return [
            {
                "id": "obs-1",
                "text": "obsidian hit",
                "user_id": user_id,
                "metadata": {"filename": "note.md"},
                "score": 0.93,
            }
        ]

    broker._retrieve_obsidian_documents = _fake_retrieve

    items = await broker.retrieve_obsidian_context_command(
        query="memory decay",
        user_id="user-1",
        project_id=42,
    )

    assert len(items) == 1
    item = items[0]
    assert item["id"] == "obs-1"
    assert item["text"] == "obsidian hit"
    assert item["source_type"] == "obsidian"
    assert item["connector_id"] == "obsidian"
    assert item["retrieval_lane"] == "connector_context"
    assert item["context_command"] is True
    assert item["project_id"] == 42
    assert item["metadata"]["filename"] == "note.md"
    assert item["metadata"]["source_type"] == "obsidian"
    assert item["metadata"]["connector_id"] == "obsidian"
    assert item["metadata"]["retrieval_lane"] == "connector_context"
    assert item["metadata"]["context_command"] is True


@pytest.mark.asyncio
async def test_context_command_does_not_change_ordinary_assemble_behavior(
    broker: ContextBroker,
) -> None:
    broker.retrieve_obsidian_context_command = AsyncMock(
        side_effect=AssertionError("context command helper should not be used")
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="test query",
        depth_mode="normal",
        user_id="user-1",
        project_id=42,
        source_mode=SOURCE_MODE_PROJECT,
    )

    assert context["messages"]
    assert context["semantic"] == []
    assert trace["source_mode"] == SOURCE_MODE_PROJECT
    broker.retrieve_obsidian_context_command.assert_not_called()
