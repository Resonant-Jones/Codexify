from __future__ import annotations

from types import SimpleNamespace
from typing import Any
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


def _matrix_hit(
    *,
    hit_id: str,
    text: str,
    filename: str,
    score: float,
    thread_id: int,
    project_id: int,
    user_id: str,
) -> dict[str, Any]:
    return {
        "id": hit_id,
        "text": text,
        "metadata": {
            "filename": filename,
            "message_id": hit_id,
            "thread_id": thread_id,
            "project_id": project_id,
            "source_thread_id": str(thread_id),
            "user_id": user_id,
        },
        "score": score,
    }


def _trace_document(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(hit["id"]),
        "title": str(hit["metadata"]["filename"]),
        "score": float(hit["score"]),
        "snippet": f"{str(hit['text'])[:100]}...",
    }


ALPHA_HIT = _matrix_hit(
    hit_id="doc-alpha",
    text="aurora-lattice-sentinel-alpha",
    filename="project-a-thread-1.md",
    score=0.98,
    thread_id=1,
    project_id=11,
    user_id="user-1",
)
BETA_HIT = _matrix_hit(
    hit_id="doc-beta",
    text="frontend-rim-bezel-sentinel-beta",
    filename="project-b-thread-3.md",
    score=0.91,
    thread_id=3,
    project_id=22,
    user_id="user-1",
)
DECOY_HIT = _matrix_hit(
    hit_id="doc-decoy",
    text="static-cinder-sentinel-decoy",
    filename="project-a-decoy.md",
    score=0.44,
    thread_id=2,
    project_id=11,
    user_id="user-1",
)
OMEGA_HIT = _matrix_hit(
    hit_id="doc-omega",
    text="cross-user-phantom-sentinel-omega",
    filename="cross-user-thread-6.md",
    score=0.96,
    thread_id=6,
    project_id=11,
    user_id="user-2",
)

MATRIX_RESULTS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "thread:1": {
        "aurora-lattice-sentinel-alpha": [ALPHA_HIT],
        "frontend-rim-bezel-sentinel-beta": [],
        "void-horizon-sentinel-zeta": [],
        "cross-user-phantom-sentinel-omega": [],
    },
    "thread:2": {
        "aurora-lattice-sentinel-alpha": [],
        "frontend-rim-bezel-sentinel-beta": [],
        "void-horizon-sentinel-zeta": [],
        "cross-user-phantom-sentinel-omega": [],
        "static-cinder-sentinel-decoy": [DECOY_HIT],
    },
    "thread:3": {
        "aurora-lattice-sentinel-alpha": [],
        "frontend-rim-bezel-sentinel-beta": [BETA_HIT],
        "void-horizon-sentinel-zeta": [],
        "cross-user-phantom-sentinel-omega": [],
    },
    "thread:6": {
        "cross-user-phantom-sentinel-omega": [OMEGA_HIT],
    },
}

MATRIX_CASES = [
    pytest.param(
        {
            "test_case_id": "project-local-success",
            "query": "aurora-lattice-sentinel-alpha",
            "source_mode": "project",
            "expected_hits": [ALPHA_HIT],
            "expected_excluded": [
                BETA_HIT["text"],
                DECOY_HIT["text"],
                OMEGA_HIT["text"],
            ],
            "expected_namespaces": ["thread:1"],
            "expected_widen_reason": "none",
        },
        id="project-local-success",
    ),
    pytest.param(
        {
            "test_case_id": "personal-knowledge-widening-success",
            "query": "frontend-rim-bezel-sentinel-beta",
            "source_mode": "personal_knowledge",
            "expected_hits": [BETA_HIT],
            "expected_excluded": [
                ALPHA_HIT["text"],
                DECOY_HIT["text"],
                OMEGA_HIT["text"],
            ],
            "expected_namespaces": ["thread:1", "thread:2", "thread:3"],
            "expected_widen_reason": "explicit_personal_knowledge",
        },
        id="personal-knowledge-widening-success",
    ),
    pytest.param(
        {
            "test_case_id": "truthful-empty-result",
            "query": "void-horizon-sentinel-zeta",
            "source_mode": "project",
            "expected_hits": [],
            "expected_excluded": [
                ALPHA_HIT["text"],
                BETA_HIT["text"],
                DECOY_HIT["text"],
                OMEGA_HIT["text"],
            ],
            "expected_namespaces": ["thread:1", "thread:2"],
            "expected_widen_reason": "insufficient_thread_hits",
        },
        id="truthful-empty-result",
    ),
    pytest.param(
        {
            "test_case_id": "no-cross-user-bleed",
            "query": "cross-user-phantom-sentinel-omega",
            "source_mode": "personal_knowledge",
            "expected_hits": [],
            "expected_excluded": [OMEGA_HIT["text"]],
            "expected_namespaces": ["thread:1", "thread:2", "thread:3"],
            "expected_widen_reason": "insufficient_thread_hits",
        },
        id="no-cross-user-bleed",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", MATRIX_CASES)
async def test_deterministic_retrieval_matrix_proves_boundary_model(
    context_broker, mock_vector_store, case
):
    def _search(query, k, namespace=None):
        hits = MATRIX_RESULTS.get(namespace or "", {}).get(query, [])
        return [
            {
                "id": hit["id"],
                "text": hit["text"],
                "metadata": dict(hit["metadata"]),
                "score": hit["score"],
            }
            for hit in hits[:k]
        ]

    mock_vector_store.search = MagicMock(side_effect=_search)

    context, trace = await context_broker.assemble(
        thread_id=1,
        query=case["query"],
        depth_mode="normal",
        k_semantic=1,
        source_mode=case["source_mode"],
    )

    expected_docs = [_trace_document(hit) for hit in case["expected_hits"]]
    actual_texts = [item["text"] for item in context["semantic"]]

    assert trace["thread_id"] == 1
    assert trace["project_id"] == 11
    assert trace["depth_mode"] == "normal"
    assert trace["source_mode"] == case["source_mode"]
    assert trace["widen_reason"] == case["expected_widen_reason"]
    assert _namespaces(mock_vector_store) == case["expected_namespaces"]
    assert actual_texts == [hit["text"] for hit in case["expected_hits"]]
    assert trace["documents"] == expected_docs

    for excluded in case["expected_excluded"]:
        assert excluded not in actual_texts
        assert excluded not in " ".join(
            doc["snippet"] for doc in trace["documents"]
        )


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

    context, trace = await context_broker.assemble(
        thread_id=1,
        query="status",
        depth_mode="normal",
        k_semantic=1,
        source_mode="project",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "project sibling hit"
    ]
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
