from __future__ import annotations

import copy
import inspect
from types import SimpleNamespace
from typing import Any

import pytest

from guardian.context.broker import (
    ContextBroker,
    _build_memory_preselection_trace,
)
from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_PROJECT,
    WIDEN_REASON_NONE,
)


class _StubChatlog:
    def get_chat_thread(self, thread_id: int):
        return {"id": thread_id, "user_id": "user-1", "project_id": 7}

    def last_messages(
        self,
        thread_id: int,
        n: int,
        user_id: str | None = None,
    ):
        return [{"id": 101, "role": "user", "content": "alpha request"}]


def _make_broker(
    *,
    semantic_hits: list[dict[str, Any]] | None = None,
    memory_hits: list[dict[str, Any]] | None = None,
) -> tuple[ContextBroker, dict[str, list[dict[str, Any]]]]:
    broker = ContextBroker(
        chatlog_db=_StubChatlog(),
        vector_store=None,
        memory_store=object(),
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=False),
    )

    calls: dict[str, list[dict[str, Any]]] = {
        "semantic": [],
        "memory": [],
    }

    async def _resolve_project_id(*, thread_id: int, project_id: int | None):
        _ = thread_id
        return project_id if project_id is not None else 7

    async def _fetch_messages(
        thread_id: int, n: int, *, user_id: str
    ) -> list[dict[str, Any]]:
        _ = (thread_id, n, user_id)
        return [{"id": 101, "role": "user", "content": "alpha request"}]

    async def _search_with_widening(**kwargs):
        search_name = getattr(kwargs.get("search_fn"), "__name__", "")
        payload = {
            "query": kwargs.get("query"),
            "k": kwargs.get("k"),
            "thread_id": kwargs.get("thread_id"),
            "user_id": kwargs.get("user_id"),
            "project_id": kwargs.get("project_id"),
            "source_mode": kwargs.get("source_mode"),
            "widening_enabled": kwargs.get("widening_enabled"),
        }
        if search_name == "_search_memory":
            calls["memory"].append(payload)
            return (
                copy.deepcopy(memory_hits or []),
                WIDEN_REASON_NONE,
                {
                    "attempted": True,
                    "status": "contributed" if memory_hits else "attempted_no_hits",
                    "reason": "results" if memory_hits else "no_hits",
                    "count": len(memory_hits or []),
                },
            )

        calls["semantic"].append(payload)
        return (
            copy.deepcopy(semantic_hits or []),
            WIDEN_REASON_NONE,
            {
                "attempted": True,
                "status": "contributed" if semantic_hits else "attempted_no_hits",
                "reason": "results" if semantic_hits else "no_hits",
                "count": len(semantic_hits or []),
            },
        )

    async def _fake_scoped_documents(**_kwargs):
        return {"project": [], "thread": [], "global": []}

    async def _fake_verified_personal_facts(**_kwargs):
        return [], {
            "attempted": False,
            "status": "skipped",
            "reason": "not_requested",
            "count": 0,
            "retrieved_count": 0,
            "included_ids": [],
            "user_id": "user-1",
            "source_mode": SOURCE_MODE_PROJECT,
            "boundary": "same_user_same_project",
        }

    broker._resolve_project_id = _resolve_project_id  # type: ignore[assignment]
    broker._fetch_messages = _fetch_messages  # type: ignore[assignment]
    broker._search_with_widening = _search_with_widening  # type: ignore[assignment]
    broker.get_scoped_documents = _fake_scoped_documents  # type: ignore[assignment]
    broker._fetch_verified_personal_facts = _fake_verified_personal_facts  # type: ignore[assignment]

    return broker, calls


async def _assemble(
    broker: ContextBroker, **overrides: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload: dict[str, Any] = {
        "thread_id": 1,
        "query": "alpha request",
        "depth_mode": "deep",
        "user_id": "user-1",
        "project_id": 7,
        "source_mode": SOURCE_MODE_PROJECT,
    }
    payload.update(overrides)
    return await broker.assemble(**payload)


def _suppressed_reasons(trace: dict[str, Any]) -> dict[str, str]:
    preselection = trace["memory_preselection"]
    return {
        str(item["candidate_id"]): str(item["reason"])
        for item in preselection["suppressed"]
    }


def _headers() -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "selected-1",
            "user_id": "user-1",
            "kind": "semantic",
            "title": "alpha title",
            "summary": "secret body should not surface",
            "tags": ("alpha",),
            "silo": "midterm",
            "project_id": "7",
            "thread_id": "1",
            "persona_id": "persona-1",
            "identity_depth": "light",
            "diary_excluded": False,
        },
        {
            "candidate_id": "project-mismatch",
            "user_id": "user-1",
            "kind": "semantic",
            "title": "alpha title",
            "project_id": "9",
            "thread_id": "1",
            "persona_id": "persona-1",
            "identity_depth": "light",
        },
    ]


@pytest.mark.asyncio
async def test_behavior_unchanged_when_memory_preselection_trace_disabled() -> None:
    broker, _calls = _make_broker()

    context_base, trace_base = await _assemble(broker)
    context_disabled, trace_disabled = await _assemble(
        broker,
        enable_memory_preselection_trace=False,
    )

    assert context_base == context_disabled
    assert trace_base == trace_disabled


@pytest.mark.asyncio
async def test_no_memory_preselection_trace_emitted_when_disabled() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=False,
    )
    assert "memory_preselection" not in trace


@pytest.mark.asyncio
async def test_enabled_trace_emits_memory_preselection_payload() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
        memory_preselection_persona_id="persona-1",
        memory_preselection_identity_depth="light",
    )
    assert trace["memory_preselection"]["enabled"] is True


@pytest.mark.asyncio
async def test_selected_candidate_ids_appear_in_trace() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
        memory_preselection_persona_id="persona-1",
        memory_preselection_identity_depth="light",
    )
    assert trace["memory_preselection"]["selected_candidate_ids"] == ["selected-1"]


@pytest.mark.asyncio
async def test_suppressed_candidate_ids_and_reasons_appear_in_trace() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
        memory_preselection_persona_id="persona-1",
        memory_preselection_identity_depth="light",
    )
    assert _suppressed_reasons(trace)["project-mismatch"] == "project_scope_mismatch"


@pytest.mark.asyncio
async def test_trace_marks_affected_retrieval_false() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
    )
    assert trace["memory_preselection"]["affected_retrieval"] is False


@pytest.mark.asyncio
async def test_trace_marks_affected_prompt_injection_false() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
    )
    assert trace["memory_preselection"]["affected_prompt_injection"] is False


@pytest.mark.asyncio
async def test_trace_exposes_no_raw_memory_body_text() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
    )
    payload = trace["memory_preselection"]
    payload_text = str(payload)
    assert "secret body should not surface" not in payload_text
    assert "summary" not in payload_text


def test_missing_user_scope_suppresses_through_preselector_path() -> None:
    trace = _build_memory_preselection_trace(
        enabled=True,
        query="alpha",
        user_id="",
        project_id=7,
        thread_id=1,
        persona_id=None,
        identity_depth="light",
        include_diary_excluded=False,
        memory_items=(),
        candidate_headers=[
            {
                "candidate_id": "cand-1",
                "user_id": "user-1",
                "kind": "semantic",
                "title": "alpha",
                "identity_depth": "light",
            }
        ],
    )
    assert trace is not None
    assert trace["suppressed"][0]["reason"] == "missing_user_scope"


@pytest.mark.asyncio
async def test_project_scope_mismatch_reason_is_emitted() -> None:
    broker, _calls = _make_broker()
    headers = _headers()
    headers[0]["project_id"] = "2"
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=headers,
    )
    assert _suppressed_reasons(trace)["selected-1"] == "project_scope_mismatch"


@pytest.mark.asyncio
async def test_thread_scope_mismatch_reason_is_emitted() -> None:
    broker, _calls = _make_broker()
    headers = _headers()
    headers[0]["thread_id"] = "99"
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=headers,
    )
    assert _suppressed_reasons(trace)["selected-1"] == "thread_scope_mismatch"


@pytest.mark.asyncio
async def test_persona_scope_mismatch_reason_is_emitted() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
        memory_preselection_persona_id="persona-x",
    )
    assert _suppressed_reasons(trace)["selected-1"] == "persona_scope_mismatch"


@pytest.mark.asyncio
async def test_diary_excluded_reason_is_emitted_when_diary_not_included() -> None:
    broker, _calls = _make_broker()
    headers = _headers()
    headers[0]["diary_excluded"] = True
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=headers,
        memory_preselection_include_diary_excluded=False,
    )
    assert _suppressed_reasons(trace)["selected-1"] == "diary_excluded"


@pytest.mark.asyncio
async def test_identity_depth_exceeded_reason_is_emitted() -> None:
    broker, _calls = _make_broker()
    headers = _headers()
    headers[0]["identity_depth"] = "deep"
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=headers,
        memory_preselection_identity_depth="light",
    )
    assert _suppressed_reasons(trace)["selected-1"] == "identity_depth_exceeded"


@pytest.mark.asyncio
async def test_allowed_candidate_can_appear_in_selected_trace() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=[
            {
                "candidate_id": "allowed-1",
                "user_id": "user-1",
                "kind": "semantic",
                "title": "alpha request",
                "project_id": "7",
                "thread_id": "1",
                "identity_depth": "light",
            }
        ],
        memory_preselection_identity_depth="light",
    )
    assert trace["memory_preselection"]["selected_candidate_ids"] == ["allowed-1"]


@pytest.mark.asyncio
async def test_memory_adapter_can_build_headers_from_memory_metadata() -> None:
    memory_hits = [
        {
            "id": "memory-hit-1",
            "user_id": "user-1",
            "metadata": {
                "title": "alpha request from memory",
                "project_id": "7",
                "thread_id": "1",
                "identity_depth": "light",
            },
            "score": 0.8,
        }
    ]
    broker, _calls = _make_broker(memory_hits=memory_hits)
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_identity_depth="light",
    )
    assert trace["memory_preselection"]["selected_candidate_ids"] == ["memory-hit-1"]


@pytest.mark.asyncio
async def test_memory_retriever_inputs_are_same_with_trace_disabled_and_enabled() -> None:
    memory_hits = [
        {
            "id": "memory-hit-1",
            "user_id": "user-1",
            "metadata": {"identity_depth": "light"},
        }
    ]
    broker_disabled, calls_disabled = _make_broker(memory_hits=memory_hits)
    broker_enabled, calls_enabled = _make_broker(memory_hits=memory_hits)

    await _assemble(broker_disabled, enable_memory_preselection_trace=False)
    await _assemble(
        broker_enabled,
        enable_memory_preselection_trace=True,
        memory_preselection_identity_depth="light",
    )

    assert calls_disabled["memory"] == calls_enabled["memory"]


@pytest.mark.asyncio
async def test_semantic_retriever_inputs_are_same_with_trace_disabled_and_enabled() -> None:
    semantic_hits = [
        {
            "id": "sem-1",
            "text": "semantic hit",
            "user_id": "user-1",
            "metadata": {"user_id": "user-1"},
            "score": 0.9,
        }
    ]
    broker_disabled, calls_disabled = _make_broker(semantic_hits=semantic_hits)
    broker_enabled, calls_enabled = _make_broker(semantic_hits=semantic_hits)

    await _assemble(broker_disabled, enable_memory_preselection_trace=False)
    await _assemble(
        broker_enabled,
        enable_memory_preselection_trace=True,
        memory_preselection_identity_depth="light",
    )

    assert calls_disabled["semantic"] == calls_enabled["semantic"]


@pytest.mark.asyncio
async def test_context_bundle_unchanged_except_trace_metadata() -> None:
    broker_disabled, _calls_disabled = _make_broker()
    broker_enabled, _calls_enabled = _make_broker()

    context_disabled, trace_disabled = await _assemble(
        broker_disabled,
        enable_memory_preselection_trace=False,
    )
    context_enabled, trace_enabled = await _assemble(
        broker_enabled,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_headers(),
    )

    assert context_disabled == context_enabled
    trace_enabled_without_preselection = dict(trace_enabled)
    trace_enabled_without_preselection.pop("memory_preselection", None)
    assert trace_disabled == trace_enabled_without_preselection


def test_preselector_adapter_has_no_db_vector_llm_network_calls() -> None:
    import guardian.context.broker as module

    source = inspect.getsource(module._build_memory_preselection_trace)
    forbidden_tokens = (
        "requests.",
        "chat_with_ai",
        "vector",
        "redis",
        "sqlalchemy",
    )
    for token in forbidden_tokens:
        assert token not in source


def test_trace_only_path_is_deterministic_across_runs() -> None:
    kwargs = {
        "enabled": True,
        "query": "alpha request",
        "user_id": "user-1",
        "project_id": 7,
        "thread_id": 1,
        "persona_id": "persona-1",
        "identity_depth": "light",
        "include_diary_excluded": False,
        "memory_items": (),
        "candidate_headers": _headers(),
    }
    first = _build_memory_preselection_trace(**kwargs)
    second = _build_memory_preselection_trace(**kwargs)
    assert first == second

