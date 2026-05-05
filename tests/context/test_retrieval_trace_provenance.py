from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PROJECT,
    WIDEN_REASON_NONE,
)


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

    assert context["messages"] == [{"id": 91, "role": "user", "content": "Describe this."}]
    assert trace["retrieval_policy"] == {
        "source_mode": SOURCE_MODE_PROJECT,
        "widening_enabled": True,
        "identity_scope": SOURCE_MODE_PROJECT,
    }
    assert trace["retrieval_executed"] is True
    assert trace["retrieval_absence_reason"] == "retrieval_no_candidates"
    assert trace["retrieval_provenance"]["source_hit_counts"]["semantic_total"] == 0
    assert trace["retrieval_provenance"]["retrieval_status"] == "no_candidates"
    assert trace["retrieval_suppression"] == {
        "items": [],
        "summary": {"total_suppressed": 0},
    }
    assert trace["image_routing_path"] is None
    assert trace["image_routing_absence_reason"] == "image_routing_not_evaluated"
