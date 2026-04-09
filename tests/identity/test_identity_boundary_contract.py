from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from guardian.context.broker import ContextBroker

ACTIVE_THREAD = {
    "id": 1,
    "user_id": "user-1",
    "project_id": 11,
    "archived_at": None,
}

THREAD_ROWS = [
    ACTIVE_THREAD,
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
        "user_id": "user-1",
        "project_id": 11,
        "archived_at": None,
        "modeling_excluded": True,
    },
    {
        "id": 7,
        "user_id": "user-2",
        "project_id": 11,
        "archived_at": None,
    },
]


def _identity_hit(
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


def _searched_namespaces(search_mock: MagicMock) -> list[str | None]:
    return [call.kwargs.get("namespace") for call in search_mock.call_args_list]


def _document_titles(trace: dict[str, Any]) -> list[str]:
    return [document["title"] for document in trace["documents"]]


def _semantic_thread_ids(context: dict[str, Any]) -> list[int]:
    return [int(item["metadata"]["thread_id"]) for item in context["semantic"]]


@pytest.fixture
def identity_boundary_broker():
    search_results: dict[str | None, list[dict[str, Any]]] = {}

    chatlog_db = MagicMock()
    chatlog_db.get_chat_thread.return_value = ACTIVE_THREAD
    chatlog_db.last_messages.return_value = [
        {
            "id": 101,
            "role": "user",
            "content": "Where is the identity boundary?",
        }
    ]
    chatlog_db.list_chat_threads.return_value = list(THREAD_ROWS)
    chatlog_db.get_connector_config.return_value = None

    vector_store = MagicMock()

    def _search(query: str, k: int, namespace: str | None = None):
        return search_results.get(namespace, [])

    vector_store.search = MagicMock(side_effect=_search)

    broker = ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )

    return SimpleNamespace(
        broker=broker,
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        search_results=search_results,
    )


# Identity Boundary A - Project scope stays local
@pytest.mark.asyncio
async def test_identity_boundary_project_scope_stays_local(
    identity_boundary_broker,
) -> None:
    identity_boundary_broker.search_results.update(
        {
            "thread:1": [],
            "thread:2": [
                _identity_hit(
                    hit_id="doc-project-sibling",
                    text="project-local sibling evidence",
                    filename="project-sibling.md",
                    score=0.93,
                    thread_id=2,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:3": [
                _identity_hit(
                    hit_id="doc-cross-project",
                    text="cross-project evidence",
                    filename="cross-project.md",
                    score=0.98,
                    thread_id=3,
                    project_id=22,
                    user_id="user-1",
                )
            ],
        }
    )

    context, trace = await identity_boundary_broker.broker.assemble(
        thread_id=1,
        query="identity boundary",
        depth_mode="normal",
        k_semantic=2,
        source_mode="project",
    )

    assert _searched_namespaces(
        identity_boundary_broker.vector_store.search
    ) == [
        "thread:1",
        "thread:2",
    ]
    assert (
        identity_boundary_broker.chatlog_db.list_chat_threads.call_args.kwargs[
            "user_id"
        ]
        == "user-1"
    )
    assert (
        identity_boundary_broker.chatlog_db.list_chat_threads.call_args.kwargs[
            "project_id"
        ]
        == 11
    )
    assert _semantic_thread_ids(context) == [2]
    assert context["semantic"][0]["metadata"]["project_id"] == 11
    assert context["semantic"][0]["metadata"]["user_id"] == "user-1"
    assert _document_titles(trace) == ["project-sibling.md"]
    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "insufficient_thread_hits"


# Identity Boundary B - Personal knowledge widening is explicit, not ambient
@pytest.mark.asyncio
async def test_identity_boundary_personal_knowledge_widening_is_explicit(
    identity_boundary_broker,
) -> None:
    identity_boundary_broker.search_results.update(
        {
            "thread:1": [],
            "thread:2": [
                _identity_hit(
                    hit_id="doc-project-sibling",
                    text="project-local sibling evidence",
                    filename="project-sibling.md",
                    score=0.93,
                    thread_id=2,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:3": [
                _identity_hit(
                    hit_id="doc-cross-project",
                    text="cross-project evidence",
                    filename="cross-project.md",
                    score=0.98,
                    thread_id=3,
                    project_id=22,
                    user_id="user-1",
                )
            ],
        }
    )

    context, trace = await identity_boundary_broker.broker.assemble(
        thread_id=1,
        query="identity boundary",
        depth_mode="normal",
        k_semantic=2,
        source_mode="personal_knowledge",
    )

    assert _searched_namespaces(
        identity_boundary_broker.vector_store.search
    ) == [
        "thread:1",
        "thread:2",
        "thread:3",
    ]
    assert (
        identity_boundary_broker.chatlog_db.list_chat_threads.call_args.kwargs[
            "user_id"
        ]
        == "user-1"
    )
    assert (
        identity_boundary_broker.chatlog_db.list_chat_threads.call_args.kwargs[
            "project_id"
        ]
        is None
    )
    assert _semantic_thread_ids(context) == [2, 3]
    assert [item["metadata"]["project_id"] for item in context["semantic"]] == [
        11,
        22,
    ]
    assert all(
        item["metadata"]["user_id"] == "user-1" for item in context["semantic"]
    )
    assert _document_titles(trace) == [
        "project-sibling.md",
        "cross-project.md",
    ]
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"


# Identity Boundary C - Excluded material does not participate
@pytest.mark.asyncio
async def test_identity_boundary_excludes_archived_and_other_user_threads(
    identity_boundary_broker,
) -> None:
    identity_boundary_broker.search_results.update(
        {
            "thread:1": [],
            "thread:2": [
                _identity_hit(
                    hit_id="doc-project-sibling",
                    text="project-local sibling evidence",
                    filename="project-sibling.md",
                    score=0.93,
                    thread_id=2,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:3": [
                _identity_hit(
                    hit_id="doc-cross-project",
                    text="cross-project evidence",
                    filename="cross-project.md",
                    score=0.98,
                    thread_id=3,
                    project_id=22,
                    user_id="user-1",
                )
            ],
            "thread:4": [
                _identity_hit(
                    hit_id="doc-archived",
                    text="archived evidence",
                    filename="archived.md",
                    score=0.97,
                    thread_id=4,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:5": [
                _identity_hit(
                    hit_id="doc-excluded",
                    text="exclude_from_identity evidence",
                    filename="excluded.md",
                    score=0.96,
                    thread_id=5,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:6": [
                _identity_hit(
                    hit_id="doc-modeling-excluded",
                    text="modeling_excluded evidence",
                    filename="modeling-excluded.md",
                    score=0.95,
                    thread_id=6,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:7": [
                _identity_hit(
                    hit_id="doc-other-user",
                    text="other-user evidence",
                    filename="other-user.md",
                    score=0.94,
                    thread_id=7,
                    project_id=11,
                    user_id="user-2",
                )
            ],
        }
    )

    context, trace = await identity_boundary_broker.broker.assemble(
        thread_id=1,
        query="identity boundary",
        depth_mode="normal",
        k_semantic=4,
        source_mode="personal_knowledge",
    )

    searched_namespaces = _searched_namespaces(
        identity_boundary_broker.vector_store.search
    )
    assert searched_namespaces == ["thread:1", "thread:2", "thread:3"]
    assert "thread:4" not in searched_namespaces
    assert "thread:5" not in searched_namespaces
    assert "thread:6" not in searched_namespaces
    assert "thread:7" not in searched_namespaces
    assert {item["metadata"]["thread_id"] for item in context["semantic"]} == {
        2,
        3,
    }
    assert {item["metadata"]["user_id"] for item in context["semantic"]} == {
        "user-1"
    }
    assert _document_titles(trace) == [
        "project-sibling.md",
        "cross-project.md",
    ]
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"


# Identity Boundary D - Contract language stays honest
@pytest.mark.asyncio
async def test_identity_boundary_active_thread_first_contract(
    identity_boundary_broker,
) -> None:
    identity_boundary_broker.search_results.update(
        {
            "thread:1": [
                _identity_hit(
                    hit_id="doc-local",
                    text="local thread evidence",
                    filename="local-thread.md",
                    score=0.99,
                    thread_id=1,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:2": [
                _identity_hit(
                    hit_id="doc-project-sibling",
                    text="project-local sibling evidence",
                    filename="project-sibling.md",
                    score=0.93,
                    thread_id=2,
                    project_id=11,
                    user_id="user-1",
                )
            ],
            "thread:3": [
                _identity_hit(
                    hit_id="doc-cross-project",
                    text="cross-project evidence",
                    filename="cross-project.md",
                    score=0.98,
                    thread_id=3,
                    project_id=22,
                    user_id="user-1",
                )
            ],
        }
    )

    context, trace = await identity_boundary_broker.broker.assemble(
        thread_id=1,
        query="identity boundary",
        depth_mode="normal",
        k_semantic=1,
        source_mode="not-a-real-mode",
    )

    assert _searched_namespaces(
        identity_boundary_broker.vector_store.search
    ) == [
        "thread:1",
    ]
    assert identity_boundary_broker.chatlog_db.list_chat_threads.call_count == 0
    assert _semantic_thread_ids(context) == [1]
    assert context["semantic"][0]["metadata"]["project_id"] == 11
    assert _document_titles(trace) == ["local-thread.md"]
    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "none"
