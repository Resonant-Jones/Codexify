from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


def _seed_completion_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    user_content: str,
    trace_payload: dict[str, object] | None,
    prompt_meta: dict[str, object] | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {}
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
    }
    mock_chatlog_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": user_content}
    ]

    class _FakeBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, thread_id, query, depth_mode, user_id):
            captured["thread_id"] = thread_id
            captured["query"] = query
            captured["depth_mode"] = depth_mode
            captured["user_id"] = user_id
            return {"semantic": []}, trace_payload

    settings = SimpleNamespace(
        LLM_PROVIDER="local",
        LOCAL_LLM_MODEL="local-model",
        DEFAULT_LOCAL_MODEL="local-model",
        LLM_MODEL="local-model",
    )

    monkeypatch.setattr(
        chat_completion_service, "get_settings", lambda: settings
    )
    monkeypatch.setattr(
        chat_completion_service,
        "validate_llm_config",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_guardian_system_prompt",
        lambda **kwargs: (
            "BASE SYSTEM",
            dict(prompt_meta or {}),
        ),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "build_context_system_message_with_meta",
        lambda *args, **kwargs: (None, {}),
    )
    monkeypatch.setattr(chat_completion_service, "ContextBroker", _FakeBroker)
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "chatlog_db",
        mock_chatlog_db,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "CHAT_PROVIDER",
        "local",
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_vector_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_memory_store",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "_sensors",
        None,
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "DEFAULT_MODEL",
        "local-model",
        raising=False,
    )
    return captured


@pytest.mark.asyncio
async def test_completion_assembly_emits_retrieval_plan_when_trace_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        user_content="What is the status?",
        trace_payload={"documents": [], "graph": []},
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert isinstance(trace, dict)
    assert trace["documents"] == []
    assert trace["graph"] == []
    assert chat_completion_service.RETRIEVAL_PLAN_TRACE_KEY in trace


@pytest.mark.asyncio
async def test_conversation_style_query_resolves_to_no_retrieval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        user_content="hello",
        trace_payload={"documents": [], "graph": []},
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert isinstance(trace, dict)
    plan = trace[chat_completion_service.RETRIEVAL_PLAN_TRACE_KEY]
    assert plan["intent"] == "conversation_only"
    assert plan["retrieval_needed"] is False


@pytest.mark.asyncio
async def test_timeline_style_query_resolves_to_chronological_time_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        user_content="What happened before this change?",
        trace_payload={"documents": [], "graph": []},
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert isinstance(trace, dict)
    plan = trace[chat_completion_service.RETRIEVAL_PLAN_TRACE_KEY]
    assert plan["intent"] == "timeline_recall"
    assert plan["time_mode"] == "chronological"


@pytest.mark.asyncio
async def test_provenance_style_query_resolves_to_graph_permissive_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        user_content="Where did this come from?",
        trace_payload={"documents": [], "graph": []},
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert isinstance(trace, dict)
    plan = trace[chat_completion_service.RETRIEVAL_PLAN_TRACE_KEY]
    assert plan["intent"] == "provenance"
    assert plan["graph_allowance"] == "prefer_enrichment"


@pytest.mark.asyncio
async def test_retrieval_plan_tracing_does_not_mutate_broker_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(
        monkeypatch,
        user_content="Please summarize this thread.",
        trace_payload={"documents": [], "graph": []},
        prompt_meta={"resolved_persona_id": 7},
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        depth_mode="deep",
    )
    await chat_completion_service.build_messages_for_llm(task)

    assert captured == {
        "thread_id": 1,
        "query": "Please summarize this thread.",
        "depth_mode": "deep",
        "user_id": "user-1",
    }


@pytest.mark.asyncio
async def test_emitted_retrieval_plan_values_are_debug_safe_scalars_and_lists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        user_content="Search globally across all projects for related notes.",
        trace_payload={"documents": [], "graph": []},
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert isinstance(trace, dict)
    plan = trace[chat_completion_service.RETRIEVAL_PLAN_TRACE_KEY]
    assert plan["intent"] == "explicit_global_search"
    assert plan["user_depth"] == "normal"
    assert plan["resolved_depth"] == "normal"
    assert plan["primary_scope"] == "global"
    assert plan["time_mode"] == "none"
    assert plan["graph_allowance"] == "allow_enrichment"
    assert isinstance(plan["retrieval_needed"], bool)
    assert isinstance(plan["allow_global_fallback"], bool)
    assert isinstance(plan["escalation_order"], list)
    assert all(isinstance(item, str) for item in plan["escalation_order"])
    assert isinstance(plan["reasons"], list)
    assert all(isinstance(item, str) for item in plan["reasons"])
