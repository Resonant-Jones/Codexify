from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.context.broker import ContextBroker

ACTIVE_THREAD_ID = 1
ACTIVE_USER_ID = "user-1"
ACTIVE_PROJECT_ID = 11


def _identity_hit(
    *,
    hit_id: str,
    text: str,
    filename: str,
    score: float,
    thread_id: int,
    project_id: int,
    user_id: str,
) -> dict[str, object]:
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


def _trace_document(hit: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(hit["id"]),
        "title": str(hit["metadata"]["filename"]),
        "score": float(hit["score"]),
        "snippet": f"{str(hit['text'])[:100]}...",
    }


def _namespaces(mock_vector_store) -> list[str | None]:
    return [
        call.kwargs.get("namespace")
        for call in mock_vector_store.search.call_args_list
    ]


def _install_search(
    mock_vector_store,
    results_by_namespace: dict[str, list[dict[str, object]]],
) -> None:
    def _search(query, k, namespace=None):
        hits = results_by_namespace.get(namespace or "", [])
        return [deepcopy(hit) for hit in hits[:k]]

    mock_vector_store.search = MagicMock(side_effect=_search)


@pytest.fixture
def identity_chatlog_db():
    return SimpleNamespace(
        last_messages=MagicMock(
            return_value=[
                {
                    "id": 1,
                    "role": "user",
                    "content": "identity boundary query",
                }
            ]
        ),
        get_chat_thread=MagicMock(
            return_value={
                "id": ACTIVE_THREAD_ID,
                "user_id": ACTIVE_USER_ID,
                "project_id": ACTIVE_PROJECT_ID,
            }
        ),
        get_connector_config=MagicMock(return_value=None),
        list_chat_threads=MagicMock(
            return_value=[
                {
                    "id": 2,
                    "user_id": ACTIVE_USER_ID,
                    "project_id": ACTIVE_PROJECT_ID,
                    "archived_at": None,
                },
                {
                    "id": 3,
                    "user_id": ACTIVE_USER_ID,
                    "project_id": 22,
                    "archived_at": None,
                },
                {
                    "id": 4,
                    "user_id": ACTIVE_USER_ID,
                    "project_id": ACTIVE_PROJECT_ID,
                    "archived_at": "2026-03-31T10:00:00Z",
                },
                {
                    "id": 5,
                    "user_id": ACTIVE_USER_ID,
                    "project_id": ACTIVE_PROJECT_ID,
                    "archived_at": None,
                    "exclude_from_identity": True,
                },
                {
                    "id": 6,
                    "user_id": "user-2",
                    "project_id": ACTIVE_PROJECT_ID,
                    "archived_at": None,
                },
            ]
        ),
    )


@pytest.fixture
def mock_vector_store():
    return SimpleNamespace()


@pytest.fixture
def identity_broker(identity_chatlog_db, mock_vector_store):
    return ContextBroker(
        chatlog_db=identity_chatlog_db,
        vector_store=mock_vector_store,
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )


@pytest.mark.asyncio
async def test_identity_boundary_project_scope_stays_local(
    identity_broker, mock_vector_store
):
    same_project_hit = _identity_hit(
        hit_id="doc-project-2",
        text="project-local widening hit",
        filename="project-2.md",
        score=0.91,
        thread_id=2,
        project_id=ACTIVE_PROJECT_ID,
        user_id=ACTIVE_USER_ID,
    )
    cross_project_hit = _identity_hit(
        hit_id="doc-project-3",
        text="cross-project leakage candidate",
        filename="project-3.md",
        score=0.99,
        thread_id=3,
        project_id=22,
        user_id=ACTIVE_USER_ID,
    )
    _install_search(
        mock_vector_store,
        {
            "thread:1": [],
            "thread:2": [same_project_hit],
            "thread:3": [cross_project_hit],
        },
    )

    context, trace = await identity_broker.assemble(
        thread_id=ACTIVE_THREAD_ID,
        query="project scope check",
        depth_mode="normal",
        k_semantic=2,
        source_mode="project",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "project-local widening hit"
    ]
    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "insufficient_thread_hits"
    assert trace["documents"] == [_trace_document(same_project_hit)]
    assert _namespaces(mock_vector_store) == ["thread:1", "thread:2"]
    assert "cross-project leakage candidate" not in " ".join(
        doc["snippet"] for doc in trace["documents"]
    )


@pytest.mark.asyncio
async def test_identity_boundary_personal_knowledge_widening_is_explicit(
    identity_broker, mock_vector_store
):
    same_project_hit = _identity_hit(
        hit_id="doc-personal-2",
        text="same-user project widening hit",
        filename="personal-2.md",
        score=0.84,
        thread_id=2,
        project_id=ACTIVE_PROJECT_ID,
        user_id=ACTIVE_USER_ID,
    )
    cross_project_hit = _identity_hit(
        hit_id="doc-personal-3",
        text="same-user cross-project widening hit",
        filename="personal-3.md",
        score=0.88,
        thread_id=3,
        project_id=22,
        user_id=ACTIVE_USER_ID,
    )
    _install_search(
        mock_vector_store,
        {
            "thread:1": [],
            "thread:2": [same_project_hit],
            "thread:3": [cross_project_hit],
        },
    )

    context, trace = await identity_broker.assemble(
        thread_id=ACTIVE_THREAD_ID,
        query="personal knowledge check",
        depth_mode="normal",
        k_semantic=2,
        source_mode="personal_knowledge",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "same-user project widening hit",
        "same-user cross-project widening hit",
    ]
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"
    assert trace["documents"] == [
        _trace_document(same_project_hit),
        _trace_document(cross_project_hit),
    ]
    assert _namespaces(mock_vector_store) == [
        "thread:1",
        "thread:2",
        "thread:3",
    ]


@pytest.mark.asyncio
async def test_identity_boundary_excludes_archived_and_other_user_threads(
    identity_broker, mock_vector_store, identity_chatlog_db
):
    allowed_same_project_hit = _identity_hit(
        hit_id="doc-allowed-2",
        text="allowed same-project identity hit",
        filename="allowed-2.md",
        score=0.83,
        thread_id=2,
        project_id=ACTIVE_PROJECT_ID,
        user_id=ACTIVE_USER_ID,
    )
    allowed_cross_project_hit = _identity_hit(
        hit_id="doc-allowed-3",
        text="allowed same-user cross-project identity hit",
        filename="allowed-3.md",
        score=0.81,
        thread_id=3,
        project_id=22,
        user_id=ACTIVE_USER_ID,
    )
    archived_hit = _identity_hit(
        hit_id="doc-archived-4",
        text="archived thread should not participate",
        filename="archived-4.md",
        score=0.99,
        thread_id=4,
        project_id=ACTIVE_PROJECT_ID,
        user_id=ACTIVE_USER_ID,
    )
    excluded_hit = _identity_hit(
        hit_id="doc-excluded-5",
        text="exclude_from_identity thread should not participate",
        filename="excluded-5.md",
        score=0.98,
        thread_id=5,
        project_id=ACTIVE_PROJECT_ID,
        user_id=ACTIVE_USER_ID,
    )
    other_user_hit = _identity_hit(
        hit_id="doc-other-user-6",
        text="other-user thread should not participate",
        filename="other-user-6.md",
        score=0.97,
        thread_id=6,
        project_id=ACTIVE_PROJECT_ID,
        user_id="user-2",
    )
    identity_chatlog_db.list_chat_threads.return_value = [
        {
            "id": 2,
            "user_id": ACTIVE_USER_ID,
            "project_id": ACTIVE_PROJECT_ID,
            "archived_at": None,
        },
        {
            "id": 3,
            "user_id": ACTIVE_USER_ID,
            "project_id": 22,
            "archived_at": None,
        },
        {
            "id": 4,
            "user_id": ACTIVE_USER_ID,
            "project_id": ACTIVE_PROJECT_ID,
            "archived_at": "2026-03-31T10:00:00Z",
        },
        {
            "id": 5,
            "user_id": ACTIVE_USER_ID,
            "project_id": ACTIVE_PROJECT_ID,
            "archived_at": None,
            "exclude_from_identity": True,
        },
        {
            "id": 6,
            "user_id": "user-2",
            "project_id": ACTIVE_PROJECT_ID,
            "archived_at": None,
        },
    ]
    _install_search(
        mock_vector_store,
        {
            "thread:1": [],
            "thread:2": [allowed_same_project_hit],
            "thread:3": [allowed_cross_project_hit],
            "thread:4": [archived_hit],
            "thread:5": [excluded_hit],
            "thread:6": [other_user_hit],
        },
    )

    context, trace = await identity_broker.assemble(
        thread_id=ACTIVE_THREAD_ID,
        query="identity exclusion check",
        depth_mode="normal",
        k_semantic=4,
        source_mode="personal_knowledge",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "allowed same-project identity hit",
        "allowed same-user cross-project identity hit",
    ]
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "explicit_personal_knowledge"
    assert trace["documents"] == [
        _trace_document(allowed_same_project_hit),
        _trace_document(allowed_cross_project_hit),
    ]
    assert _namespaces(mock_vector_store) == [
        "thread:1",
        "thread:2",
        "thread:3",
    ]
    assert "thread:4" not in _namespaces(mock_vector_store)
    assert "thread:5" not in _namespaces(mock_vector_store)
    assert "thread:6" not in _namespaces(mock_vector_store)


@pytest.mark.asyncio
async def test_identity_boundary_active_thread_first_contract(
    identity_broker, mock_vector_store
):
    local_hit = _identity_hit(
        hit_id="doc-fallback-2",
        text="fallback stays narrow",
        filename="fallback-2.md",
        score=0.87,
        thread_id=2,
        project_id=ACTIVE_PROJECT_ID,
        user_id=ACTIVE_USER_ID,
    )
    _install_search(
        mock_vector_store,
        {
            "thread:1": [],
            "thread:2": [local_hit],
            "thread:3": [
                _identity_hit(
                    hit_id="doc-fallback-3",
                    text="cross-project fallback candidate",
                    filename="fallback-3.md",
                    score=0.95,
                    thread_id=3,
                    project_id=22,
                    user_id=ACTIVE_USER_ID,
                )
            ],
        },
    )

    context, trace = await identity_broker.assemble(
        thread_id=ACTIVE_THREAD_ID,
        query="fallback check",
        depth_mode="normal",
        k_semantic=2,
        source_mode="not-a-real-source-mode",
    )

    assert [item["text"] for item in context["semantic"]] == [
        "fallback stays narrow"
    ]
    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "insufficient_thread_hits"
    assert trace["documents"] == [_trace_document(local_hit)]
    assert _namespaces(mock_vector_store) == ["thread:1", "thread:2"]
