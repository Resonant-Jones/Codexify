from __future__ import annotations

import copy
import inspect
from types import SimpleNamespace
from typing import Any

import pytest

from guardian.context.broker import (
    ContextBroker,
    _apply_memory_preselection_active_influence,
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
        _ = (thread_id, n, user_id)
        return [{"id": 101, "role": "user", "content": "alpha request"}]


def _default_memory_hits() -> list[dict[str, Any]]:
    return [
        {
            "id": "selected-1",
            "user_id": "user-1",
            "metadata": {
                "id": "selected-1",
                "title": "alpha request selected",
                "project_id": "7",
                "thread_id": "1",
                "identity_depth": "light",
            },
            "text": "selected body text",
            "score": 0.91,
        },
        {
            "id": "suppressed-1",
            "user_id": "user-1",
            "metadata": {
                "id": "suppressed-1",
                "title": "beta unrelated candidate",
                "project_id": "7",
                "thread_id": "1",
                "identity_depth": "light",
            },
            "text": "suppressed body text",
            "score": 0.73,
        },
        {
            "user_id": "user-1",
            "metadata": {
                "title": "no-id unrelated memory item",
                "project_id": "7",
                "thread_id": "1",
                "identity_depth": "light",
            },
            "text": "no-id item body",
            "score": 0.22,
        },
    ]


def _active_candidate_headers() -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "selected-1",
            "user_id": "user-1",
            "kind": "semantic",
            "title": "alpha request selected",
            "project_id": "7",
            "thread_id": "1",
            "identity_depth": "light",
        },
        {
            "candidate_id": "suppressed-1",
            "user_id": "user-1",
            "kind": "semantic",
            "title": "beta unrelated candidate",
            "project_id": "7",
            "thread_id": "1",
            "identity_depth": "light",
        },
    ]


def _make_broker(
    *,
    semantic_hits: list[dict[str, Any]] | None = None,
    memory_hits: list[dict[str, Any]] | None = None,
    docs_hits: dict[str, list[dict[str, Any]]] | None = None,
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
        "docs": [],
    }

    async def _resolve_project_id(*, thread_id: int, project_id: int | None):
        _ = thread_id
        return project_id if project_id is not None else 7

    async def _fetch_messages(
        thread_id: int,
        n: int,
        *,
        user_id: str,
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
                copy.deepcopy(memory_hits or _default_memory_hits()),
                WIDEN_REASON_NONE,
                {
                    "attempted": True,
                    "status": "contributed",
                    "reason": "results",
                    "count": len(memory_hits or _default_memory_hits()),
                },
            )

        calls["semantic"].append(payload)
        return (
            copy.deepcopy(semantic_hits or []),
            WIDEN_REASON_NONE,
            {
                "attempted": True,
                "status": (
                    "contributed" if semantic_hits else "attempted_no_hits"
                ),
                "reason": ("results" if semantic_hits else "no_hits"),
                "count": len(semantic_hits or []),
            },
        )

    async def _fake_scoped_documents(**kwargs):
        calls["docs"].append(
            {
                "thread_id": kwargs.get("thread_id"),
                "project_id": kwargs.get("project_id"),
                "user_id": kwargs.get("user_id"),
                "k_project_docs": kwargs.get("k_project_docs"),
                "k_thread_docs": kwargs.get("k_thread_docs"),
            }
        )
        return copy.deepcopy(
            docs_hits or {"project": [], "thread": [], "global": []}
        )

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
    broker: ContextBroker,
    **overrides: Any,
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


def _memory_ids(context: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in context.get("memory", []):
        if isinstance(item, dict):
            candidate_id = str(item.get("id") or "").strip()
            if candidate_id:
                ids.append(candidate_id)
    return ids


def _suppressed_reasons(trace: dict[str, Any]) -> dict[str, str]:
    return {
        str(item["candidate_id"]): str(item["reason"])
        for item in trace["memory_preselection"]["suppressed"]
    }


@pytest.mark.asyncio
async def test_default_behavior_unchanged_when_active_not_enabled() -> None:
    broker, _calls = _make_broker()
    context_base, trace_base = await _assemble(broker)
    context_flagged, trace_flagged = await _assemble(
        broker,
        enable_memory_preselection_active=False,
    )
    assert context_base == context_flagged
    assert trace_base == trace_flagged


@pytest.mark.asyncio
async def test_trace_only_mode_does_not_alter_memory_selection() -> None:
    broker, _calls = _make_broker()
    context_base, _trace_base = await _assemble(broker)
    context_trace_only, trace_trace_only = await _assemble(
        broker,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert _memory_ids(context_trace_only) == _memory_ids(context_base)
    assert trace_trace_only["memory_preselection"]["mode"] == "trace_only"
    assert trace_trace_only["memory_preselection"]["active"] is False
    assert trace_trace_only["memory_preselection"]["affected_retrieval"] is False
    assert (
        trace_trace_only["memory_preselection"]["affected_prompt_injection"]
        is False
    )


@pytest.mark.asyncio
async def test_active_mode_requires_explicit_enable_flag() -> None:
    broker_trace_only, _calls_trace_only = _make_broker()
    broker_active, _calls_active = _make_broker()

    context_trace_only, _trace_trace_only = await _assemble(
        broker_trace_only,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    context_active, _trace_active = await _assemble(
        broker_active,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )

    assert "suppressed-1" in _memory_ids(context_trace_only)
    assert "suppressed-1" not in _memory_ids(context_active)


@pytest.mark.asyncio
async def test_active_mode_emits_active_mode_trace_marker() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert trace["memory_preselection"]["mode"] == "active"


@pytest.mark.asyncio
async def test_active_mode_emits_active_true() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert trace["memory_preselection"]["active"] is True


@pytest.mark.asyncio
async def test_active_mode_marks_affected_retrieval_when_memory_filtered() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert trace["memory_preselection"]["affected_retrieval"] is True


@pytest.mark.asyncio
async def test_active_mode_marks_affected_prompt_injection_when_memory_filtered() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert trace["memory_preselection"]["affected_prompt_injection"] is True


@pytest.mark.asyncio
async def test_active_mode_keeps_selected_candidate_ids() -> None:
    broker, _calls = _make_broker()
    context, _trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert "selected-1" in _memory_ids(context)


@pytest.mark.asyncio
async def test_active_mode_removes_suppressed_candidate_ids() -> None:
    broker, _calls = _make_broker()
    context, _trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert "suppressed-1" not in _memory_ids(context)


@pytest.mark.asyncio
async def test_active_mode_does_not_remove_unrelated_no_id_items() -> None:
    broker, _calls = _make_broker()
    context, _trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    no_id_items = [
        item
        for item in context.get("memory", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip() == ""
    ]
    assert len(no_id_items) == 1


@pytest.mark.asyncio
async def test_active_mode_does_not_alter_semantic_vector_inputs() -> None:
    broker_disabled, calls_disabled = _make_broker()
    broker_enabled, calls_enabled = _make_broker()

    await _assemble(
        broker_disabled,
        enable_memory_preselection_active=False,
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    await _assemble(
        broker_enabled,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert calls_disabled["semantic"] == calls_enabled["semantic"]


@pytest.mark.asyncio
async def test_active_mode_does_not_alter_document_retrieval_inputs() -> None:
    broker_disabled, calls_disabled = _make_broker()
    broker_enabled, calls_enabled = _make_broker()

    await _assemble(broker_disabled, enable_memory_preselection_active=False)
    await _assemble(
        broker_enabled,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
    )

    assert calls_disabled["docs"] == calls_enabled["docs"]


@pytest.mark.asyncio
async def test_active_mode_does_not_alter_project_thread_message_history() -> None:
    broker_disabled, _calls_disabled = _make_broker()
    broker_enabled, _calls_enabled = _make_broker()

    context_disabled, _trace_disabled = await _assemble(
        broker_disabled,
        enable_memory_preselection_active=False,
    )
    context_enabled, _trace_enabled = await _assemble(
        broker_enabled,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert context_disabled["messages"] == context_enabled["messages"]


@pytest.mark.asyncio
async def test_diary_excluded_candidate_is_removed_in_active_mode() -> None:
    broker, _calls = _make_broker()
    headers = _active_candidate_headers()
    headers[1]["title"] = "alpha request diary match"
    headers[1]["diary_excluded"] = True

    context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=headers,
        memory_preselection_include_diary_excluded=False,
    )
    assert "suppressed-1" not in _memory_ids(context)
    assert _suppressed_reasons(trace)["suppressed-1"] == "diary_excluded"


@pytest.mark.asyncio
async def test_identity_depth_exceeded_candidate_is_removed_in_active_mode() -> None:
    broker, _calls = _make_broker()
    headers = _active_candidate_headers()
    headers[1]["title"] = "alpha request depth match"
    headers[1]["identity_depth"] = "deep"

    context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_candidate_headers=headers,
        memory_preselection_identity_depth="light",
    )
    assert "suppressed-1" not in _memory_ids(context)
    assert _suppressed_reasons(trace)["suppressed-1"] == "identity_depth_exceeded"


@pytest.mark.asyncio
async def test_project_scope_mismatch_candidate_is_removed_in_active_mode() -> None:
    broker, _calls = _make_broker()
    headers = _active_candidate_headers()
    headers[1]["title"] = "alpha request project match"
    headers[1]["project_id"] = "999"

    context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=headers,
    )
    assert "suppressed-1" not in _memory_ids(context)
    assert _suppressed_reasons(trace)["suppressed-1"] == "project_scope_mismatch"


@pytest.mark.asyncio
async def test_thread_scope_mismatch_candidate_is_removed_in_active_mode() -> None:
    broker, _calls = _make_broker()
    headers = _active_candidate_headers()
    headers[1]["title"] = "alpha request thread match"
    headers[1]["thread_id"] = "999"

    context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=headers,
    )
    assert "suppressed-1" not in _memory_ids(context)
    assert _suppressed_reasons(trace)["suppressed-1"] == "thread_scope_mismatch"


@pytest.mark.asyncio
async def test_persona_scope_mismatch_candidate_is_removed_in_active_mode() -> None:
    broker, _calls = _make_broker()
    headers = _active_candidate_headers()
    headers[1]["title"] = "alpha request persona match"
    headers[1]["persona_id"] = "persona-x"

    context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=headers,
        memory_preselection_persona_id="persona-1",
    )
    assert "suppressed-1" not in _memory_ids(context)
    assert _suppressed_reasons(trace)["suppressed-1"] == "persona_scope_mismatch"


def test_missing_user_scope_suppresses_all_in_active_helper_path() -> None:
    trace = _build_memory_preselection_trace(
        enabled=True,
        active=True,
        query="alpha request",
        user_id="",
        project_id=7,
        thread_id=1,
        persona_id=None,
        identity_depth="light",
        include_diary_excluded=False,
        memory_items=_default_memory_hits(),
        candidate_headers=_active_candidate_headers(),
    )
    assert trace is not None
    assert trace["selected_candidate_ids"] == []
    assert all(
        entry["reason"] == "missing_user_scope" for entry in trace["suppressed"]
    )
    filtered, influence, _applied = _apply_memory_preselection_active_influence(
        _default_memory_hits(),
        selected_candidate_ids=[],
        scoped_candidate_ids=[entry["candidate_id"] for entry in trace["suppressed"]],
    )
    assert [item.get("id") for item in filtered if isinstance(item, dict)] == [None]
    assert influence["removed_candidate_ids"] == ["selected-1", "suppressed-1"]


@pytest.mark.asyncio
async def test_trace_includes_allowed_and_removed_candidate_ids() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    influence = trace["memory_preselection"]["active_influence"]
    assert influence["allowed_candidate_ids"] == ["selected-1"]
    assert influence["removed_candidate_ids"] == ["suppressed-1"]


@pytest.mark.asyncio
async def test_trace_includes_unchanged_item_count() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert trace["memory_preselection"]["active_influence"]["unchanged_item_count"] == 2


@pytest.mark.asyncio
async def test_active_trace_exposes_no_raw_memory_body_text() -> None:
    broker, _calls = _make_broker()
    _context, trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    payload = trace["memory_preselection"]
    payload_text = str(payload)
    assert "selected body text" not in payload_text
    assert "suppressed body text" not in payload_text


@pytest.mark.asyncio
async def test_active_mode_is_deterministic_across_runs() -> None:
    broker, _calls = _make_broker()
    first_context, first_trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    second_context, second_trace = await _assemble(
        broker,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert first_context == second_context
    assert first_trace == second_trace


@pytest.mark.asyncio
async def test_memory_retriever_inputs_same_with_active_disabled_and_enabled() -> None:
    broker_disabled, calls_disabled = _make_broker()
    broker_enabled, calls_enabled = _make_broker()

    await _assemble(broker_disabled, enable_memory_preselection_active=False)
    await _assemble(
        broker_enabled,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )
    assert calls_disabled["memory"] == calls_enabled["memory"]


@pytest.mark.asyncio
async def test_context_bundle_changes_only_in_memory_section_when_active_applies() -> None:
    broker_disabled, _calls_disabled = _make_broker()
    broker_enabled, _calls_enabled = _make_broker()

    context_disabled, _trace_disabled = await _assemble(
        broker_disabled,
        enable_memory_preselection_active=False,
    )
    context_enabled, _trace_enabled = await _assemble(
        broker_enabled,
        enable_memory_preselection_active=True,
        memory_preselection_identity_depth="light",
        memory_preselection_candidate_headers=_active_candidate_headers(),
    )

    assert context_disabled["memory"] != context_enabled["memory"]

    disabled_without_memory = dict(context_disabled)
    enabled_without_memory = dict(context_enabled)
    disabled_without_memory.pop("memory", None)
    enabled_without_memory.pop("memory", None)
    assert disabled_without_memory == enabled_without_memory


def test_active_adapter_has_no_db_vector_llm_network_calls() -> None:
    import guardian.context.broker as module

    source = inspect.getsource(module._apply_memory_preselection_active_influence)
    forbidden_tokens = (
        "requests.",
        "chat_with_ai",
        "vector",
        "redis",
        "sqlalchemy",
    )
    for token in forbidden_tokens:
        assert token not in source
