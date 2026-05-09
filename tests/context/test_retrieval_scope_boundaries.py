from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PROJECT,
    SOURCE_MODE_WORKSPACE,
)
from tests.utils import get_test_user_id


class _Chatlog:
    def __init__(self, *, user_id: str, project_id: int | None):
        self._user_id = user_id
        self._project_id = project_id

    def get_chat_thread(self, thread_id):
        return {
            "id": thread_id,
            "user_id": self._user_id,
            "project_id": self._project_id,
            "archived_at": None,
        }

    def list_messages(self, thread_id, limit, offset):
        return [
            {
                "id": 1,
                "role": "user",
                "content": "What changed in this thread?",
            }
        ]

    def list_chat_threads(self, *args, **kwargs):
        return [
            {
                "id": 1,
                "user_id": self._user_id,
                "project_id": self._project_id,
                "archived_at": None,
            },
            {
                "id": 2,
                "user_id": self._user_id,
                "project_id": 99 if self._project_id == 7 else self._project_id,
                "archived_at": None,
            },
        ]


def _make_broker(chatlog_db, vector_store):
    return ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )


def _semantic_hits(label: str, user_id: str):
    return [
        {
            "id": f"{label}-assistant",
            "score": 0.98,
            "text": f"{label} assistant authored refusal",
            "user_id": user_id,
            "metadata": {"role": "assistant"},
        },
        {
            "id": f"{label}-user",
            "score": 0.55,
            "text": f"{label} user evidence",
            "user_id": user_id,
            "metadata": {"role": "user"},
        },
    ]


@pytest.mark.asyncio
async def test_default_project_bound_turn_stays_thread_first_and_keeps_project_docs(
    monkeypatch,
):
    user_id = get_test_user_id()
    chatlog = _Chatlog(user_id=user_id, project_id=7)
    vector_calls: list[str | None] = []

    class _VectorStore:
        def search(self, query, k, namespace=None, user_id=None):
            vector_calls.append(namespace)
            if namespace == "thread:1":
                return _semantic_hits("thread", user_id)
            if namespace == "thread:2":
                pytest.fail(
                    "thread widening should not happen for ordinary direct QA"
                )
            return []

    broker = _make_broker(chatlog, _VectorStore())
    doc_calls: dict[str, object] = {}

    async def _fake_get_scoped_documents(**kwargs):
        doc_calls.update(kwargs)
        include_project_docs = bool(kwargs.get("include_project_docs"))
        include_thread_docs = bool(kwargs.get("include_thread_docs"))
        return {
            "project": (
                [
                    {
                        "id": "project-doc-1",
                        "title": "Project note",
                        "excerpt": "project scoped evidence",
                        "user_id": user_id,
                        "provenance": {"relation": "project_library"},
                    }
                ]
                if include_project_docs
                else []
            ),
            "thread": (
                [
                    {
                        "id": "thread-doc-1",
                        "title": "Thread note",
                        "excerpt": "thread scoped evidence",
                        "user_id": user_id,
                        "provenance": {"relation": "thread_link"},
                    }
                ]
                if include_thread_docs
                else []
            ),
            "global": [],
        }

    monkeypatch.setattr(
        broker, "get_scoped_documents", _fake_get_scoped_documents
    )

    context, trace = await broker.assemble(
        1,
        query="What changed in this thread?",
        depth_mode="normal",
        user_id=user_id,
        project_id=7,
        source_mode=SOURCE_MODE_PROJECT,
    )

    assert vector_calls == ["thread:1"]
    assert trace["retrieval_policy"]["allow_semantic_widening"] is False
    assert trace["retrieval_policy"]["allow_project_docs"] is True
    assert doc_calls["include_project_docs"] is True
    assert doc_calls["include_thread_docs"] is True
    assert context["docs"]["project"][0]["id"] == "project-doc-1"
    assert context["docs"]["thread"][0]["id"] == "thread-doc-1"
    assert [item["id"] for item in context["semantic"]] == [
        "thread-user",
        "thread-assistant",
    ]


@pytest.mark.asyncio
async def test_unbound_thread_does_not_pull_project_docs_by_default(
    monkeypatch,
):
    user_id = get_test_user_id()
    chatlog = _Chatlog(user_id=user_id, project_id=None)
    vector_calls: list[str | None] = []

    class _VectorStore:
        def search(self, query, k, namespace=None, user_id=None):
            vector_calls.append(namespace)
            if namespace == "thread:1":
                return _semantic_hits("thread", user_id)
            return []

    broker = _make_broker(chatlog, _VectorStore())
    doc_calls: dict[str, object] = {}

    async def _fake_get_scoped_documents(**kwargs):
        doc_calls.update(kwargs)
        include_project_docs = bool(kwargs.get("include_project_docs"))
        include_thread_docs = bool(kwargs.get("include_thread_docs"))
        return {
            "project": (
                [
                    {
                        "id": "project-doc-1",
                        "title": "Project note",
                        "excerpt": "project scoped evidence",
                        "user_id": user_id,
                        "provenance": {"relation": "project_library"},
                    }
                ]
                if include_project_docs
                else []
            ),
            "thread": (
                [
                    {
                        "id": "thread-doc-1",
                        "title": "Thread note",
                        "excerpt": "thread scoped evidence",
                        "user_id": user_id,
                        "provenance": {"relation": "thread_link"},
                    }
                ]
                if include_thread_docs
                else []
            ),
            "global": [],
        }

    monkeypatch.setattr(
        broker, "get_scoped_documents", _fake_get_scoped_documents
    )

    context, trace = await broker.assemble(
        1,
        query="What changed in this thread?",
        depth_mode="normal",
        user_id=user_id,
        project_id=None,
        source_mode=SOURCE_MODE_PROJECT,
    )

    assert vector_calls == ["thread:1"]
    assert trace["retrieval_policy"]["allow_project_docs"] is False
    assert trace["retrieval_policy"]["allow_semantic_widening"] is False
    assert doc_calls["include_project_docs"] is False
    assert doc_calls["include_thread_docs"] is True
    assert context["docs"]["project"] == []
    assert context["docs"]["thread"][0]["id"] == "thread-doc-1"


@pytest.mark.asyncio
async def test_workspace_source_mode_can_widen_across_threads_when_supported(
    monkeypatch,
):
    user_id = get_test_user_id()
    chatlog = _Chatlog(user_id=user_id, project_id=7)
    vector_calls: list[str | None] = []

    class _VectorStore:
        def search(self, query, k, namespace=None, user_id=None):
            vector_calls.append(namespace)
            if namespace == "thread:1":
                return _semantic_hits("thread", user_id)
            if namespace == "thread:2":
                return [
                    {
                        "id": "candidate-user",
                        "score": 0.88,
                        "text": "candidate thread evidence",
                        "user_id": user_id,
                        "metadata": {"role": "user"},
                    }
                ]
            return []

    broker = _make_broker(chatlog, _VectorStore())

    async def _fake_get_scoped_documents(**kwargs):
        return {"project": [], "thread": [], "global": []}

    async def _fake_retrieve_obsidian_documents(*_args, **_kwargs):
        return []

    monkeypatch.setattr(
        broker,
        "_retrieve_obsidian_documents",
        _fake_retrieve_obsidian_documents,
    )
    monkeypatch.setattr(
        broker, "get_scoped_documents", _fake_get_scoped_documents
    )

    context, trace = await broker.assemble(
        1,
        query="What changed across the workspace?",
        depth_mode="normal",
        user_id=user_id,
        project_id=7,
        source_mode=SOURCE_MODE_WORKSPACE,
    )

    assert vector_calls == ["thread:1", "thread:2"]
    assert trace["retrieval_policy"]["allow_semantic_widening"] is True
    assert trace["retrieval_policy"]["widening_source_mode"] == (
        SOURCE_MODE_WORKSPACE
    )
    assert [item["id"] for item in context["semantic"]] == [
        "candidate-user",
        "thread-user",
        "thread-assistant",
    ]
