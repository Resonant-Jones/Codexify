"""Operator-facing retrieval diagnostics on the broker's ``rag_trace``.

These tests pin the behaviour the ``rag-trace`` / ``retrieval-posture``
operator surfaces depend on:

* a successful retrieval and a failed retrieval are reported differently
  (the surface used to report "empty" for both);
* the surface names the documents that actually contributed, including the
  project/thread document lanes;
* the surface states its own evidence scope, so an operator can tell
  "retrieval produced nothing" apart from "this surface is not evidence";
* per-message ``retrieval_provenance`` keeps carrying the truth;
* nothing withheld from the model leaks through the diagnostic surface.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian import protocol_tokens
from guardian.context.broker import (
    RAG_TRACE_EVIDENCE_CAPABLE,
    RAG_TRACE_EVIDENCE_KEY,
    RAG_TRACE_EVIDENCE_SCOPE,
    ContextBroker,
)
from guardian.core.chat_completion_service import _build_retrieval_provenance

USER_ID = "user-123"
PROJECT_ID = 7


class _Chatlog:
    def __init__(self, *, user_id: str = USER_ID, project_id: int = PROJECT_ID):
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

    def last_messages(self, thread_id, n, user_id=None):
        return self.list_messages(thread_id, n, 0)


def _make_broker(vector_store=None) -> ContextBroker:
    return ContextBroker(
        chatlog_db=_Chatlog(),
        vector_store=vector_store,
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )


def _thread_doc_record(broker: ContextBroker) -> dict:
    return broker._serialize_doc_record(
        row=SimpleNamespace(
            id="doc-thread-9",
            filename="thread-fact.txt",
            parsed_text="A bounded excerpt used by the provider.",
            source_tag="upload",
            mime_type="text/plain",
            project_id=PROJECT_ID,
            thread_id=1,
            user_id=USER_ID,
            created_at=None,
            model=None,
        ),
        doc_type="uploaded",
        scope="thread",
        excerpt_chars=420,
        relation="thread_scope",
        attached_at=None,
        attached_by=USER_ID,
        retrieval_policy={"source_mode": "project"},
    )


class _EmptyVectorStore:
    def search(self, query, k, namespace=None, user_id=None):
        return []


def _install_docs(broker: ContextBroker, docs: dict) -> None:
    async def _fake_scoped_documents(*_args, **_kwargs):
        return docs

    broker.get_scoped_documents = _fake_scoped_documents  # type: ignore[assignment]


def _stub_document_readiness(broker: ContextBroker) -> None:
    """Keep hits carrying a ``doc_id`` (ingestion readiness is out of scope)."""
    broker._uploaded_document_is_ready = (  # type: ignore[assignment]
        lambda **_kwargs: True
    )


@pytest.mark.asyncio
async def test_rag_trace_reports_document_lane_retrieval_as_observed() -> None:
    """A retrieval that landed a document is visible on the surface."""
    broker = _make_broker(_EmptyVectorStore())
    record = _thread_doc_record(broker)
    _install_docs(
        broker,
        {"project": [], "thread": [record], "global": []},
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        user_id=USER_ID,
        source_mode="project",
    )

    # The document reached the model context ...
    assert context["docs"]["thread"] == [record]

    # ... and the operator surface reports it instead of an empty list.
    assert trace["documents"], "surface must not report empty for a live retrieval"
    trace_doc = trace["documents"][0]
    assert trace_doc["id"] == record["id"]
    assert trace_doc["title"] == record["title"]
    assert trace_doc["retrieval_lane"] == "thread_docs"
    assert trace_doc["chunk_index"] == 0

    # The surface carries the executed state and the absence reason.
    assert trace["retrieval_executed"] is True
    assert trace["retrieval_absence_reason"] is None
    assert (
        trace["retrieval_provenance"]["source_hit_counts"]["thread_documents"]
        == 1
    )
    assert trace["retrieval_policy"]["source_mode"] == "project"

    evidence = trace[RAG_TRACE_EVIDENCE_KEY]
    assert evidence["evidence_capable"] is True
    assert evidence["retrieval_observed"] is True
    assert evidence["absence_reason"] is None
    assert "thread_documents" in evidence["observed_lanes"]


@pytest.mark.asyncio
async def test_rag_trace_distinguishes_failed_retrieval_from_successful() -> None:
    """A failed retrieval is reported as failed, not as an empty surface."""
    broker = _make_broker(_EmptyVectorStore())
    _install_docs(broker, {"project": [], "thread": [], "global": []})

    _context, trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        user_id=USER_ID,
        source_mode="project",
    )

    assert trace["documents"] == []
    assert trace["retrieval_executed"] is True
    assert trace["retrieval_absence_reason"] == "retrieval_no_candidates"
    assert (
        trace["retrieval_provenance"]["source_hit_counts"]["thread_documents"]
        == 0
    )
    assert trace["retrieval_provenance"]["retrieval_status"] == "no_candidates"

    evidence = trace[RAG_TRACE_EVIDENCE_KEY]
    assert evidence["evidence_capable"] is True
    assert evidence["retrieval_observed"] is False
    assert evidence["absence_reason"] == "retrieval_no_candidates"
    assert evidence["observed_lanes"] == []


@pytest.mark.asyncio
async def test_successful_and_failed_retrieval_traces_are_distinguishable() -> None:
    """The two surfaces differ in shape, not only in size."""
    success_broker = _make_broker(_EmptyVectorStore())
    _install_docs(
        success_broker,
        {
            "project": [],
            "thread": [_thread_doc_record(success_broker)],
            "global": [],
        },
    )
    _success_context, success_trace = await success_broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        user_id=USER_ID,
        source_mode="project",
    )

    failure_broker = _make_broker(_EmptyVectorStore())
    _install_docs(failure_broker, {"project": [], "thread": [], "global": []})
    _failure_context, failure_trace = await failure_broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        user_id=USER_ID,
        source_mode="project",
    )

    assert success_trace["documents"] != failure_trace["documents"]
    assert (
        success_trace["retrieval_absence_reason"]
        != failure_trace["retrieval_absence_reason"]
    )
    assert (
        success_trace[RAG_TRACE_EVIDENCE_KEY]["retrieval_observed"]
        != failure_trace[RAG_TRACE_EVIDENCE_KEY]["retrieval_observed"]
    )


@pytest.mark.asyncio
async def test_obsidian_only_path_reports_retrieval_truth() -> None:
    """The Obsidian-only assembly path reports the retrieval truth too."""
    chatlog_db = AsyncMock()
    chatlog_db.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "Find the note"}]
    )
    chatlog_db.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": USER_ID, "project_id": PROJECT_ID}
    )
    chatlog_db.get_connector_config = MagicMock(
        return_value={
            "name": "obsidian_local",
            "type": "obsidian",
            "settings": {"vault_root": "/vault", "enabled": True},
        }
    )
    vector_store = AsyncMock()

    def _search(query, k, namespace=None, user_id=None):
        if namespace == "obsidian:local":
            return [
                {
                    "id": "obs-1",
                    "text": "obsidian note hit",
                    "user_id": USER_ID,
                    "metadata": {"filename": "note.md"},
                    "score": 0.99,
                }
            ]
        return []

    vector_store.search = MagicMock(side_effect=_search)

    broker = ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=AsyncMock(),
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=True),
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="Find the note",
        depth_mode="normal",
        source_mode="obsidian_only",
        user_id=USER_ID,
    )

    assert len(context["obsidian"]) == 1
    assert trace["retrieval_executed"] is True
    assert trace["retrieval_absence_reason"] is None
    assert trace["retrieval_provenance"]["source_hit_counts"]["obsidian_semantic"] == 1
    assert trace[RAG_TRACE_EVIDENCE_KEY]["retrieval_observed"] is True
    assert trace["documents"], "obsidian hit must be visible on the surface"


@pytest.mark.asyncio
async def test_withheld_entries_are_not_reported_as_retrieved() -> None:
    """A withheld hit stays out of the model context and out of the trace."""
    user_id = USER_ID

    class _VectorStore:
        def search(self, query, k, namespace=None, user_id=None):
            return [
                {
                    "id": "codex-entry-1",
                    "score": 0.91,
                    "text": "codex entry text",
                    "user_id": user_id,
                    "metadata": {
                        "source_type": "codex_entry",
                        "filename": "entry.md",
                    },
                },
                {
                    "id": "thread-hit-1",
                    "score": 0.87,
                    "text": "thread evidence",
                    "user_id": user_id,
                    "metadata": {
                        "role": "assistant",
                        "source_type": "semantic-note",
                    },
                },
            ]

    broker = _make_broker(_VectorStore())
    _install_docs(broker, {"project": [], "thread": [], "global": []})

    context, trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        user_id=user_id,
        source_mode="project",
    )

    context_ids = {str(item.get("id")) for item in context["semantic"]}
    trace_ids = {str(item.get("id")) for item in trace["documents"]}

    assert "codex-entry-1" not in context_ids
    assert "codex-entry-1" not in trace_ids
    assert "thread-hit-1" in context_ids
    assert "thread-hit-1" in trace_ids


@pytest.mark.asyncio
async def test_per_message_retrieval_provenance_still_carries_the_truth() -> None:
    """Per-message provenance is unchanged and still names contributors."""
    user_id = USER_ID

    class _VectorStore:
        def search(self, query, k, namespace=None, user_id=None):
            return [
                {
                    "id": "thread-hit-1",
                    "score": 0.87,
                    "text": "thread evidence",
                    "user_id": user_id,
                    "metadata": {
                        "role": "user",
                        "source_type": "retrieval",
                        "doc_id": "retained-document",
                        "chunk_index": 3,
                        "namespace": "thread:1",
                        "user_id": user_id,
                    },
                }
            ]

    broker = _make_broker(_VectorStore())
    _stub_document_readiness(broker)
    _install_docs(broker, {"project": [], "thread": [], "global": []})

    context, _trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        user_id=user_id,
        source_mode="project",
    )

    bundle = {
        "semantic": context["semantic"],
        "docs": context["docs"],
        "_prompt_meta": {
            "context": {
                "semantic": {"count": len(context["semantic"]), "injected": True}
            },
            "docs": {"count": 0, "injected": False},
        },
        "retrieval_suppression": context.get("retrieval_suppression"),
    }
    provenance = _build_retrieval_provenance(
        requested_source_mode="project",
        normalized_source_mode="project",
        bundle=bundle,
    )

    assert provenance["contributing_items"] == [
        {
            "source_type": "retrieval",
            "role": "user",
            "document_id": "retained-document",
            "chunk_id": "thread-hit-1",
            "chunk_index": 3,
            "project_id": PROJECT_ID,
            "thread_id": 1,
            "retrieval_lane": "thread_semantic",
            "namespace": "thread:1",
            "score": 0.87,
        }
    ]


def test_rag_trace_evidence_marker_is_module_local_and_greppable() -> None:
    """The marker is a stable, machine-greppable label outside the registry."""
    assert RAG_TRACE_EVIDENCE_KEY == "rag_trace_evidence"
    assert RAG_TRACE_EVIDENCE_CAPABLE is True
    assert RAG_TRACE_EVIDENCE_SCOPE == "context_broker_retrieval_diagnostics"

    # ADR-016: the canonical protocol-token registry is documentation-only, so
    # a new runtime label must not be registered there.
    assert not hasattr(protocol_tokens, RAG_TRACE_EVIDENCE_KEY)
    assert not hasattr(protocol_tokens, "RAG_TRACE_EVIDENCE_KEY")
