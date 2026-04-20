from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PROJECT,
    WIDEN_REASON_INSUFFICIENT_THREAD_HITS,
    WIDEN_REASON_NONE,
)

USER_A = "user-a"
USER_B = "user-b"


def _broker() -> ContextBroker:
    chatlog_db = AsyncMock()
    chatlog_db.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "hello"}]
    )
    chatlog_db.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": USER_A, "project_id": 11}
    )
    chatlog_db.get_connector_config = MagicMock(return_value=None)
    chatlog_db.list_chat_threads = MagicMock(
        return_value=[
            {"id": 1, "user_id": USER_A, "project_id": 11, "archived_at": None},
            {"id": 2, "user_id": USER_A, "project_id": 11, "archived_at": None},
        ]
    )

    vector_store = AsyncMock()
    vector_store.search = MagicMock(return_value=[])

    return ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=AsyncMock(),
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )


@pytest.mark.asyncio
async def test_retrieval_is_user_scoped() -> None:
    broker = _broker()

    broker._search_with_widening = AsyncMock(
        return_value=(
            [
                {
                    "text": "owned semantic hit",
                    "user_id": USER_A,
                    "metadata": {"message_id": 11},
                    "score": 0.9,
                }
            ],
            WIDEN_REASON_NONE,
            {
                "attempted": True,
                "status": "contributed",
                "reason": "local_hits",
                "count": 1,
                "widened": False,
            },
        )
    )
    broker.get_scoped_documents = AsyncMock(
        return_value={
            "project": [
                {
                    "id": "doc-1",
                    "title": "owned doc",
                    "user_id": USER_A,
                }
            ],
            "thread": [],
            "global": [],
        }
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="hello",
        depth_mode="normal",
        source_mode=SOURCE_MODE_PROJECT,
        user_id=USER_A,
    )

    assert all(item["user_id"] == USER_A for item in context["semantic"])
    assert all(item["user_id"] == USER_A for item in context["docs"]["project"])
    assert trace["source_mode"] == SOURCE_MODE_PROJECT
    assert trace["widen_reason"] == WIDEN_REASON_NONE


@pytest.mark.asyncio
async def test_cross_user_data_excluded() -> None:
    broker = _broker()

    broker._search_with_widening = AsyncMock(
        return_value=(
            [
                {
                    "text": "owned semantic hit",
                    "user_id": USER_A,
                    "metadata": {"message_id": 11},
                    "score": 0.9,
                },
                {
                    "text": "cross-user semantic hit",
                    "user_id": USER_B,
                    "metadata": {"message_id": 12},
                    "score": 0.8,
                },
            ],
            WIDEN_REASON_NONE,
            {
                "attempted": True,
                "status": "contributed",
                "reason": "local_hits",
                "count": 2,
                "widened": False,
            },
        )
    )
    broker.get_scoped_documents = AsyncMock(
        return_value={"project": [], "thread": [], "global": []}
    )

    with pytest.raises(
        AssertionError, match="retrieval_user_isolation_violation"
    ):
        await broker.assemble(
            thread_id=1,
            query="hello",
            depth_mode="normal",
            source_mode=SOURCE_MODE_PROJECT,
            user_id=USER_A,
        )


@pytest.mark.asyncio
async def test_widening_sets_reason() -> None:
    broker = _broker()

    async def _search(query, k, namespace=None, user_id=None):
        if namespace == "thread:1":
            return []
        if namespace == "thread:2":
            return [
                {
                    "text": "project sibling",
                    "user_id": USER_A,
                    "metadata": {"message_id": 21},
                    "score": 0.92,
                }
            ]
        return []

    hits, widen_reason, diagnostics = await broker._search_with_widening(
        query="hello",
        k=2,
        thread_id=1,
        user_id=USER_A,
        project_id=11,
        source_mode=SOURCE_MODE_PROJECT,
        search_fn=_search,
        widening_enabled=True,
    )

    assert [hit["text"] for hit in hits] == ["project sibling"]
    assert widen_reason == WIDEN_REASON_INSUFFICIENT_THREAD_HITS
    assert diagnostics["widened"] is True


@pytest.mark.asyncio
async def test_no_widening_sets_none() -> None:
    broker = _broker()

    async def _search(query, k, namespace=None, user_id=None):
        if namespace == "thread:1":
            return [
                {
                    "text": "owned local hit",
                    "user_id": USER_A,
                    "metadata": {"message_id": 31},
                    "score": 0.99,
                }
            ]
        return []

    hits, widen_reason, diagnostics = await broker._search_with_widening(
        query="hello",
        k=1,
        thread_id=1,
        user_id=USER_A,
        project_id=11,
        source_mode=SOURCE_MODE_PROJECT,
        search_fn=_search,
        widening_enabled=True,
    )

    assert [hit["text"] for hit in hits] == ["owned local hit"]
    assert widen_reason == WIDEN_REASON_NONE
    assert diagnostics["widened"] is False
