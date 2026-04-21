from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker, _assert_user_scoped_results
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_CONVERSATION,
    SOURCE_MODE_PROJECT,
    WIDEN_REASON_INSUFFICIENT_THREAD_HITS,
    WIDEN_REASON_NONE,
)


def _make_broker() -> ContextBroker:
    chatlog_db = AsyncMock()
    chatlog_db.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "hello"}]
    )
    chatlog_db.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": "user-a", "project_id": 11}
    )
    chatlog_db.get_connector_config = MagicMock(return_value=None)
    chatlog_db.list_chat_threads = MagicMock(
        return_value=[
            {"id": 1, "user_id": "user-a", "project_id": 11},
            {"id": 2, "user_id": "user-a", "project_id": 11},
            {"id": 6, "user_id": "user-b", "project_id": 11},
        ]
    )

    broker = ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=MagicMock(),
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )
    return broker


def test_retrieval_is_user_scoped() -> None:
    user_a = "user-a"
    results = [
        {"metadata": {"user_id": user_a}, "content": "valid"},
        {"metadata": {"user_id": user_a}, "content": "also valid"},
    ]

    filtered = _assert_user_scoped_results(results, user_id=user_a)

    assert len(filtered) == 2
    assert all(item["metadata"]["user_id"] == user_a for item in filtered)


def test_cross_user_data_excluded() -> None:
    user_a = "user-a"
    user_b = "user-b"
    results = [{"metadata": {"user_id": user_b}, "content": "should_not_show"}]

    with pytest.raises(
        AssertionError, match="retrieval_user_isolation_violation"
    ):
        _assert_user_scoped_results(results, user_id=user_a)


@pytest.mark.asyncio
async def test_widening_sets_reason() -> None:
    broker = _make_broker()

    async def _search_semantic(query, k, namespace=None, user_id=None):
        if namespace == "thread:1":
            return []
        if namespace == "thread:2":
            return [
                {
                    "text": "project fallback hit",
                    "metadata": {"user_id": "user-a", "message_id": 20},
                    "score": 0.91,
                }
            ]
        return []

    broker._search_semantic = AsyncMock(side_effect=_search_semantic)

    context, trace = await broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=1,
        user_id="user-a",
        source_mode=SOURCE_MODE_PROJECT,
    )

    assert [item["text"] for item in context["semantic"]] == [
        "project fallback hit"
    ]
    assert trace["source_mode"] == SOURCE_MODE_PROJECT
    assert trace["widen_reason"] == WIDEN_REASON_INSUFFICIENT_THREAD_HITS


@pytest.mark.asyncio
async def test_no_widening_sets_none() -> None:
    broker = _make_broker()

    async def _search_semantic(query, k, namespace=None, user_id=None):
        if namespace == "thread:1":
            return [
                {
                    "text": "strong local hit",
                    "metadata": {"user_id": "user-a", "message_id": 10},
                    "score": 0.99,
                }
            ]
        return []

    broker._search_semantic = AsyncMock(side_effect=_search_semantic)

    context, trace = await broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=1,
        user_id="user-a",
        source_mode=SOURCE_MODE_PROJECT,
    )

    assert [item["text"] for item in context["semantic"]] == [
        "strong local hit"
    ]
    assert trace["source_mode"] == SOURCE_MODE_PROJECT
    assert trace["widen_reason"] == WIDEN_REASON_NONE


@pytest.mark.asyncio
async def test_violation_raises() -> None:
    broker = _make_broker()

    async def _search_semantic(query, k, namespace=None, user_id=None):
        return [
            {
                "text": "cross-user hit",
                "metadata": {"user_id": "user-b", "message_id": 99},
                "score": 0.88,
            }
        ]

    broker._search_semantic = AsyncMock(side_effect=_search_semantic)

    with pytest.raises(
        AssertionError, match="retrieval_user_isolation_violation"
    ):
        await broker.assemble(
            thread_id=1,
            query="status",
            depth_mode="normal",
            k_semantic=1,
            user_id="user-a",
            source_mode=SOURCE_MODE_PROJECT,
        )


@pytest.mark.asyncio
async def test_no_widening_defaults_to_none() -> None:
    broker = _make_broker()
    broker._search_semantic = AsyncMock(
        side_effect=AssertionError("search should not run for shallow scope")
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="shallow",
        user_id="user-a",
        source_mode=SOURCE_MODE_CONVERSATION,
    )

    assert context["semantic"] == []
    assert trace["source_mode"] == SOURCE_MODE_CONVERSATION
    assert trace["widen_reason"] == WIDEN_REASON_NONE
