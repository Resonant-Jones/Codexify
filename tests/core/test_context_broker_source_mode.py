from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker


class _TemporalLike:
    def __init__(self, iso_text: str) -> None:
        self._iso_text = iso_text

    def isoformat(self) -> str:
        return self._iso_text


@pytest.fixture
def mock_chatlog_db():
    mock = AsyncMock()
    mock.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "hello"}]
    )
    mock.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": "user-1", "project_id": 11}
    )
    mock.get_connector_config = MagicMock(return_value=None)
    mock.list_chat_threads = MagicMock(
        return_value=[
            {
                "id": 1,
                "user_id": "user-1",
                "project_id": 11,
                "archived_at": None,
            },
            {
                "id": 2,
                "user_id": "user-1",
                "project_id": 11,
                "archived_at": None,
            },
            {
                "id": 3,
                "user_id": "user-1",
                "project_id": 22,
                "archived_at": None,
            },
            {
                "id": 4,
                "user_id": "user-1",
                "project_id": 11,
                "archived_at": "2026-03-31T10:00:00Z",
            },
            {
                "id": 5,
                "user_id": "user-1",
                "project_id": 11,
                "archived_at": None,
                "exclude_from_identity": True,
            },
            {
                "id": 6,
                "user_id": "user-2",
                "project_id": 11,
                "archived_at": None,
            },
        ]
    )
    return mock


@pytest.fixture
def mock_vector_store():
    return AsyncMock()


@pytest.fixture
def context_broker(mock_chatlog_db, mock_vector_store):
    return ContextBroker(
        chatlog_db=mock_chatlog_db,
        vector_store=mock_vector_store,
        memory_store=AsyncMock(),
        sensors=None,
    )


def _namespaces(mock_vector_store):
    return [
        call.kwargs.get("namespace")
        for call in mock_vector_store.search.call_args_list
    ]


@pytest.mark.asyncio
async def test_project_source_widens_only_within_same_project(
    context_broker, mock_vector_store
):
    def _search(query, k, namespace=None):
        if namespace == "thread:1":
            return []
        if namespace == "thread:2":
            return [
                {
                    "text": "project sibling hit",
                    "metadata": {"message_id": 20},
                    "score": 0.81,
                }
            ]
        if namespace == "thread:3":
            return [
                {
                    "text": "cross project hit",
                    "metadata": {"message_id": 30},
                    "score": 0.92,
                }
            ]
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=2,
        source_mode="project",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "project sibling hit"
    ]
    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "insufficient_thread_hits"
    assert _namespaces(mock_vector_store) == ["thread:1", "thread:2"]


@pytest.mark.asyncio
async def test_personal_knowledge_widens_same_user_across_projects(
    context_broker, mock_vector_store
):
    def _search(query, k, namespace=None):
        if namespace == "thread:1":
            return []
        if namespace == "thread:2":
            return [
                {
                    "text": "same project sibling",
                    "metadata": {"message_id": 20},
                    "score": 0.73,
                }
            ]
        if namespace == "thread:3":
            return [
                {
                    "text": "cross project sibling",
                    "metadata": {"message_id": 30},
                    "score": 0.77,
                }
            ]
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=2,
        source_mode="personal_knowledge",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "same project sibling",
        "cross project sibling",
    ]
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"
    assert _namespaces(mock_vector_store) == [
        "thread:1",
        "thread:2",
        "thread:3",
    ]


@pytest.mark.asyncio
async def test_low_confidence_thread_hits_trigger_project_widening(
    context_broker, mock_vector_store
):
    def _search(query, k, namespace=None):
        if namespace == "thread:1":
            return [
                {
                    "text": "weak local hit",
                    "metadata": {"message_id": 10},
                    "score": 0.05,
                }
            ]
        if namespace == "thread:2":
            return [
                {
                    "text": "project sibling hit",
                    "metadata": {"message_id": 20},
                    "score": 0.95,
                }
            ]
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)

    _context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=1,
        source_mode="project",
    )

    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "low_confidence_thread_hits"
    assert _namespaces(mock_vector_store) == ["thread:1", "thread:2"]


@pytest.mark.asyncio
async def test_personal_knowledge_marks_explicit_widening_even_when_same_project_hit_satisfies_query(
    context_broker, mock_vector_store
):
    def _search(query, k, namespace=None):
        if namespace == "thread:1":
            return []
        if namespace == "thread:2":
            return [
                {
                    "text": "same project sibling",
                    "metadata": {"message_id": 20},
                    "score": 0.89,
                }
            ]
        if namespace == "thread:3":
            return [
                {
                    "text": "cross project sibling",
                    "metadata": {"message_id": 30},
                    "score": 0.91,
                }
            ]
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=1,
        source_mode="personal_knowledge",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "same project sibling"
    ]
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"
    assert _namespaces(mock_vector_store) == ["thread:1", "thread:2"]


@pytest.mark.asyncio
async def test_strong_thread_hits_keep_trace_stable_without_widening(
    context_broker, mock_vector_store
):
    def _search(query, k, namespace=None):
        if namespace == "thread:1":
            return [
                {
                    "text": "strong local hit",
                    "metadata": {"message_id": 10},
                    "score": 0.91,
                }
            ]
        if namespace == "thread:2":
            return [
                {
                    "text": "project sibling hit",
                    "metadata": {"message_id": 20},
                    "score": 0.99,
                }
            ]
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=1,
        source_mode="project",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "strong local hit"
    ]
    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "none"
    assert _namespaces(mock_vector_store) == ["thread:1"]


@pytest.mark.asyncio
async def test_graph_context_temporal_values_are_coerced(
    mock_chatlog_db, mock_vector_store, monkeypatch
):
    mock_vector_store.search = MagicMock(return_value=[])

    broker = ContextBroker(
        chatlog_db=mock_chatlog_db,
        vector_store=mock_vector_store,
        memory_store=AsyncMock(),
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=True),
    )

    monkeypatch.setattr("guardian.graph.connection.connect_neo4j", lambda: None)

    def _cypher_query(query, params):
        if "ThreadNode" in query:
            return (
                [
                    (
                        "msg-1",
                        "graph content",
                        _TemporalLike("2026-03-31T12:00:00+00:00"),
                        "1",
                        "user-1",
                    )
                ],
                [
                    "message_id",
                    "content",
                    "created_at",
                    "thread_id",
                    "user_id",
                ],
            )
        return (
            [],
            ["message_id", "content", "created_at", "thread_id", "user_id"],
        )

    monkeypatch.setattr("neomodel.db.cypher_query", _cypher_query)

    context, trace = await broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="shallow",
    )

    assert context["graph"][0]["message_id"] == "msg-1"
    assert context["graph"][0]["created_at"] == "2026-03-31T12:00:00+00:00"
    assert trace["graph_context"]["status"] == "contributed"
    assert trace["graph_context"]["scope"] == "thread"


@pytest.mark.asyncio
async def test_personal_knowledge_memory_trace_skips_when_depth_disallows_it(
    context_broker,
):
    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        source_mode="personal_knowledge",
    )

    assert "memory" not in context
    assert trace["memory_context"]["status"] == "skipped"
    assert trace["memory_context"]["reason"] == "depth_not_allowed"


@pytest.mark.asyncio
async def test_personal_knowledge_memory_trace_reports_no_eligible_candidates(
    context_broker, mock_chatlog_db, mock_vector_store
):
    def _search(query, k, namespace=None):
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)
    mock_chatlog_db.list_chat_threads = MagicMock(return_value=[])

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="deep",
        k_memory=2,
        source_mode="personal_knowledge",
    )

    assert context["memory"] == []
    assert trace["memory_context"]["status"] == "no_eligible_candidates"
    assert trace["memory_context"]["reason"] == "no_eligible_candidates"


@pytest.mark.asyncio
async def test_personal_knowledge_memory_trace_reports_attempted_no_hits(
    context_broker, mock_chatlog_db, mock_vector_store
):
    def _search(query, k, namespace=None):
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="deep",
        k_memory=2,
        source_mode="personal_knowledge",
    )

    assert context["memory"] == []
    assert trace["memory_context"]["status"] == "attempted_no_hits"
    assert trace["memory_context"]["reason"] == "no_hits"


@pytest.mark.asyncio
async def test_personal_knowledge_memory_trace_reports_contributed_hits(
    context_broker, mock_vector_store
):
    def _search(query, k, namespace=None):
        if namespace == "thread:1":
            return []
        if namespace == "thread:2":
            return [
                {
                    "text": "same-user memory hit",
                    "metadata": {"message_id": 201},
                    "score": 0.88,
                }
            ]
        return []

    mock_vector_store.search = MagicMock(side_effect=_search)

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="deep",
        k_memory=1,
        source_mode="personal_knowledge",
    )

    assert [item["text"] for item in context["memory"]] == [
        "same-user memory hit"
    ]
    assert trace["memory_context"]["status"] == "contributed"
    assert trace["memory_context"]["boundary"] == "same_user_only"
    assert "thread:6" not in _namespaces(mock_vector_store)
