from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PROJECT,
    WIDEN_REASON_NONE,
)
from guardian.core.chat_completion_service import (
    _filter_image_refusal_semantic_context,
)
from guardian.protocol_tokens import TraceSuppressionReason


class _StubChatlog:
    def get_chat_thread(self, thread_id: int):
        return {
            "id": thread_id,
            "user_id": "local",
            "project_id": 8,
        }

    def last_messages(self, thread_id: int, n: int, user_id: str | None = None):
        return [{"id": 91, "role": "user", "content": "Describe this."}]


@pytest.mark.asyncio
async def test_context_broker_emits_containment_trace_fields() -> None:
    broker = ContextBroker(
        chatlog_db=_StubChatlog(),
        vector_store=None,
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )

    async def _fake_resolve_project_id(*_args, **_kwargs):
        return 8

    async def _fake_search_with_widening(*_args, **_kwargs):
        diagnostics = {
            "attempted": True,
            "status": "attempted_no_hits",
            "reason": "no_hits",
            "source_mode": SOURCE_MODE_PROJECT,
            "boundary": "project",
            "widening_enabled": True,
            "primary_hit_count": 0,
            "candidate_thread_count": 0,
            "candidate_hit_count": 0,
            "result_count": 0,
            "widened": False,
        }
        return [], WIDEN_REASON_NONE, diagnostics

    async def _fake_scoped_documents(*_args, **_kwargs):
        return {"project": [], "thread": [], "global": []}

    async def _fake_verified_personal_facts(*_args, **_kwargs):
        return [], {
            "attempted": False,
            "status": "skipped",
            "reason": "depth_not_allowed",
            "count": 0,
            "retrieved_count": 0,
            "included_ids": [],
            "user_id": "local",
            "source_mode": SOURCE_MODE_PROJECT,
            "boundary": "project",
        }

    broker._resolve_project_id = _fake_resolve_project_id  # type: ignore[assignment]
    broker._search_with_widening = _fake_search_with_widening  # type: ignore[assignment]
    broker.get_scoped_documents = _fake_scoped_documents  # type: ignore[assignment]
    broker._fetch_verified_personal_facts = _fake_verified_personal_facts  # type: ignore[assignment]

    context, trace = await broker.assemble(
        8,
        "Describe this.",
        depth_mode="normal",
        source_mode=SOURCE_MODE_PROJECT,
        user_id="local",
    )

    assert context["messages"] == [
        {"id": 91, "role": "user", "content": "Describe this."}
    ]
    assert trace["retrieval_policy"] == {
        "source_mode": SOURCE_MODE_PROJECT,
        "widening_enabled": True,
        "identity_scope": SOURCE_MODE_PROJECT,
    }
    assert trace["retrieval_executed"] is True
    assert trace["retrieval_absence_reason"] == "retrieval_no_candidates"
    assert (
        trace["retrieval_provenance"]["source_hit_counts"]["semantic_total"]
        == 0
    )
    assert trace["retrieval_provenance"]["retrieval_status"] == "no_candidates"
    assert trace["retrieval_suppression"] == {
        "items": [],
        "summary": {"total_suppressed": 0},
    }
    assert trace["image_routing_path"] is None
    assert (
        trace["image_routing_absence_reason"] == "image_routing_not_evaluated"
    )


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


def _make_broker(chatlog_db, vector_store):
    return ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=None,
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )


@pytest.mark.asyncio
async def test_retrieval_trace_surfaces_provenance_and_policy_suppression():
    user_id = "user-123"
    chatlog = _Chatlog(user_id=user_id, project_id=7)

    class _VectorStore:
        def search(self, query, k, namespace=None, user_id=None):
            return [
                {
                    "id": "thread-hit-1",
                    "score": 0.87,
                    "text": "thread evidence",
                    "user_id": user_id,
                    "metadata": {
                        "role": "assistant",
                        "source_type": "semantic-note",
                    },
                }
            ]

    broker = _make_broker(chatlog, _VectorStore())
    retrieval_policy = {
        "source_mode": "project",
        "widening_source_mode": "project",
        "thread_project_bound": True,
        "allow_thread_semantic": True,
        "allow_thread_docs": True,
        "allow_project_docs": True,
        "allow_semantic_widening": False,
        "allow_global_widening": False,
        "reasons": ["test policy"],
    }

    context, trace = await broker.assemble(
        thread_id=1,
        query="What changed?",
        depth_mode="normal",
        user_id=user_id,
        source_mode="project",
        retrieval_policy=retrieval_policy,
    )

    assert context["semantic"]
    semantic_item = context["semantic"][0]
    assert semantic_item["source_type"] == "semantic-note"
    assert semantic_item["role"] == "assistant"
    assert semantic_item["thread_id"] == 1
    assert semantic_item["project_id"] == 7
    assert semantic_item["retrieval_lane"] == "thread_semantic"
    assert semantic_item["score"] == pytest.approx(0.87)
    assert semantic_item["policy_reason"] == "local_hits"
    assert semantic_item["retrieval_policy"] == retrieval_policy

    trace_item = trace["documents"][0]
    assert trace_item["source_type"] == "semantic-note"
    assert trace_item["role"] == "assistant"
    assert trace_item["thread_id"] == 1
    assert trace_item["project_id"] == 7
    assert trace_item["retrieval_lane"] == "thread_semantic"
    assert trace_item["policy_reason"] == "local_hits"
    assert trace_item["retrieval_policy"] == retrieval_policy
    assert trace["retrieval_policy"] == {
        "source_mode": "project",
        "widening_enabled": True,
        "identity_scope": "project",
    }
    assert trace["retrieval_suppression"] == {
        "items": [],
        "summary": {"total_suppressed": 0},
    }


def test_image_turn_refusal_suppression_is_annotated():
    latest_user_meta = {
        "attachments": [{"kind": "image", "src": "http://example.test/a.png"}]
    }
    semantic_items = [
        {
            "id": "refusal-1",
            "content": "I can't directly see the image.",
            "thread_id": 2,
            "project_id": 9,
            "retrieval_lane": "thread_semantic",
            "score": 0.2,
            "source_type": "retrieval",
            "role": "assistant",
            "retrieval_policy": {"source_mode": "project"},
        },
        {
            "id": "keep-1",
            "content": "User evidence that stays in context.",
            "thread_id": 2,
            "project_id": 9,
            "retrieval_lane": "thread_semantic",
            "score": 0.5,
            "source_type": "retrieval",
            "role": "user",
            "retrieval_policy": {"source_mode": "project"},
        },
    ]

    filtered, suppression = _filter_image_refusal_semantic_context(
        semantic_items,
        latest_user_meta,
    )

    assert len(filtered) == 1
    assert filtered[0]["id"] == "keep-1"
    assert suppression is not None
    assert suppression["count"] == 1
    suppressed = suppression["items"][0]
    assert suppressed["suppression_reason"] == (
        TraceSuppressionReason.ASSISTANT_VISION_REFUSAL_ON_IMAGE_TURN.value
    )
    assert suppressed["source_type"] == "retrieval"
    assert suppressed["role"] == "assistant"
    assert suppressed["thread_id"] == 2
    assert suppressed["project_id"] == 9
    assert suppressed["retrieval_lane"] == "thread_semantic"
    assert suppressed["policy_reason"] == (
        TraceSuppressionReason.ASSISTANT_VISION_REFUSAL_ON_IMAGE_TURN.value
    )
