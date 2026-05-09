from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock
from urllib.parse import quote

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


def _install_service_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    messages: list[dict[str, object]],
    bundle: dict[str, object],
    trace_payload: dict[str, object],
    retrieve_side_effect=None,
):
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.context.context_directive_resolver import (
    encode_context_request_plans_origin_segment,
)
from guardian.core import chat_completion_service
from guardian.core.chat_completion_service import (
    _context_request_plans_from_origin,
)
from guardian.tasks.types import ChatCompletionTask


def _fake_retrieval_plan() -> SimpleNamespace:
    return SimpleNamespace(
        intent=SimpleNamespace(value="conversation_only"),
        effective_depth=SimpleNamespace(value="normal"),
        default_scope=SimpleNamespace(value="thread"),
        time_mode=SimpleNamespace(value="none"),
        graph_allowance=SimpleNamespace(value="disallow"),
        retrieval_needed=False,
        allow_global_fallback=False,
        escalation_order=[],
        reasons=[],
    )


def _seed_completion_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    origin: str | None = None,
    retrieved_items: list[dict[str, object]] | None = None,
    retrieve_exception: Exception | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {}
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
    }
    mock_chatlog_db.list_messages.return_value = messages

    class _FakeBroker:
        def __init__(self, *args, **kwargs):
            self.retrieve_obsidian_context_command = AsyncMock(
                side_effect=retrieve_side_effect
            )
    mock_chatlog_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "Please use /obsidian memory decay"}
    ]

    class _FakeBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(
            self,
            thread_id,
            query,
            depth_mode,
            user_id,
            project_id=None,
            source_mode="project",
            retrieval_override=None,
            retrieval_policy=None,
        ):
            captured["thread_id"] = thread_id
            captured["query"] = query
            captured["depth_mode"] = depth_mode
            captured["user_id"] = user_id
            captured["project_id"] = project_id
            captured["source_mode"] = source_mode
            return dict(bundle), dict(trace_payload)
            return (
                {
                    "semantic": [{"text": "thread semantic"}],
                    "obsidian": [],
                    "connector_context": [],
                },
                {
                    "documents": [],
                    "graph": [],
                    "source_mode": source_mode,
                    "widen_reason": "none",
                },
            )

        async def retrieve_obsidian_context_command(
            self,
            *,
            query,
            user_id,
            project_id=None,
            k=4,
            retrieval_policy=None,
        ):
            captured["connector_query"] = query
            captured["connector_user_id"] = user_id
            captured["connector_project_id"] = project_id
            captured["connector_k"] = k
            captured["connector_policy"] = retrieval_policy
            if retrieve_exception is not None:
                raise retrieve_exception
            return list(retrieved_items or [])

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
        lambda **kwargs: ("BASE SYSTEM", {}),
    )
    monkeypatch.setattr(chat_completion_service, "ContextBroker", _FakeBroker)
    monkeypatch.setattr(
        chat_completion_service, "resolve_thread_system_profile", None
    )
    monkeypatch.setattr(
        chat_completion_service,
        "resolve_retrieval_plan",
        lambda *args, **kwargs: _fake_retrieval_plan(),
    )
    monkeypatch.setattr(
        chat_completion_service,
        "ContextBroker",
        _FakeBroker,
    )
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
        "DEFAULT_MODEL",
        "local-model",
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
    return captured


def _task_with_origin(origin: str) -> ChatCompletionTask:
    return ChatCompletionTask(
        user_id="user-1",
        thread_id=1,
        provider="local",
        model=None,
        origin=origin,
    )


def _context_plan_origin(plans: list[dict[str, object]]) -> str:
    return "api:chat.complete|context_request_plans=" + quote(
        json.dumps(plans, ensure_ascii=False, separators=(",", ":")),
        safe="",
    )


@pytest.mark.asyncio
async def test_context_request_plans_from_origin_decodes_valid_metadata() -> None:
    plans = chat_completion_service._context_request_plans_from_origin(
        _context_plan_origin(
def test_context_request_plans_from_origin_decodes_valid_metadata() -> None:
    origin = (
        "api:chat.complete|turn_id=abc"
        + encode_context_request_plans_origin_segment(
            [
                {
                    "request_kind": "read_only_context_request",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                    "status": "accepted_not_executed",
                }
            ]
        )
    )

    assert plans == [
                    "execution_required": False,
                }
            ]
        )
    )

    assert _context_request_plans_from_origin(origin) == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": "accepted_not_executed",
        }
    ]


def test_context_request_plans_from_origin_handles_missing_or_malformed_data() -> None:
    assert chat_completion_service._context_request_plans_from_origin(
        "api:chat.complete|turn_id=1"
    ) == []
    assert chat_completion_service._context_request_plans_from_origin(
        "api:chat.complete|context_request_plans=%7Bnot-json"
    ) == []


@pytest.mark.asyncio
async def test_build_messages_for_llm_consumes_supported_obsidian_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_service_fakes(
        monkeypatch,
        messages=[{"id": 1, "role": "user", "content": "general ask"}],
        bundle={
            "semantic": [{"text": "thread semantic"}],
            "docs": {"thread": [], "project": [], "global": []},
            "connector_context": [],
        },
        trace_payload={"documents": [], "graph": [], "source_mode": "project"},
        retrieve_side_effect=None,
    )
    fake_broker = chat_completion_service.ContextBroker(
        None, None, None, None
    )
    fake_broker.retrieve_obsidian_context_command = AsyncMock(
        return_value=[
            {
                "text": "obsidian connector hit",
                "metadata": {"namespace": "obsidian:local"},
            }
        ]
    )
    monkeypatch.setattr(
        chat_completion_service, "ContextBroker", lambda *args, **kwargs: fake_broker
    )

    task = _task_with_origin(
        _context_plan_origin(
            "execution_required": False,
        }
    ]


@pytest.mark.asyncio
async def test_missing_context_request_plans_is_a_no_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch)

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model=None,
        origin="api:chat.complete|turn_id=abc|source_mode=project",
    )
    (
        _messages,
        _provider,
        _model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert "connector_query" not in captured
    assert bundle["connector_context"] == []
    assert trace["context_request_results"] == []


@pytest.mark.asyncio
async def test_malformed_context_request_plans_do_not_crash_completion_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch)

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model=None,
        origin="api:chat.complete|turn_id=abc|context_request_plans=not-json",
    )
    (
        _messages,
        _provider,
        _model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert "connector_query" not in captured
    assert bundle["connector_context"] == []
    assert trace["context_request_results"] == []


@pytest.mark.asyncio
async def test_obsidian_context_request_plan_is_executed_additively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(
        monkeypatch,
        retrieved_items=[
            {
                "id": "obs-1",
                "text": "obsidian hit",
                "metadata": {"filename": "note.md"},
                "score": 0.93,
            }
        ],
    )
    origin = (
        "api:chat.complete|turn_id=abc"
        + encode_context_request_plans_origin_segment(
            [
                {
                    "request_kind": "read_only_context_request",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                    "status": "accepted_not_executed",
                    "execution_required": False,
                }
            ]
        )
    )

    messages, provider, model, bundle, trace = await chat_completion_service.build_messages_for_llm(
        task
    )

    assert captured["query"] == "general ask"
    fake_broker.retrieve_obsidian_context_command.assert_awaited_once_with(
        query="memory decay",
        user_id="user-1",
        project_id=42,
        k=4,
        retrieval_policy=ANY,
    )
    assert provider == "local"
    assert model == "local-model"
    assert bundle["_completion_assembly"]["latest_turn"]["content"] == "general ask"
    assert messages[-1]["content"] == "general ask"
    assert bundle["semantic"] == [{"text": "thread semantic"}]
    assert len(bundle["connector_context"]) == 1
    assert bundle["connector_context"][0]["retrieval_lane"] == "connector_context"
    assert bundle["connector_context"][0]["connector_id"] == "obsidian"
    assert bundle["_prompt_meta"]["context"]["connector_context"]["count"] == 1
    assert bundle["_prompt_meta"]["context"]["connector_context"]["injected"] is True
    assert any(
        "obsidian connector hit" in str(message.get("content") or "")
        for message in messages
        if message.get("role") == "system"
    )
    assert trace["source_mode"] == "project"
    assert trace["context_request_results"][0]["status"] == "executed"
    assert trace["context_request_results"][0]["result_count"] == 1
    assert trace["context_request_results"][0]["injected"] is True


@pytest.mark.asyncio
async def test_build_messages_for_llm_records_no_results_without_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_service_fakes(
        monkeypatch,
        messages=[{"id": 1, "role": "user", "content": "general ask"}],
        bundle={
            "semantic": [{"text": "thread semantic"}],
            "docs": {"thread": [], "project": [], "global": []},
            "connector_context": [],
        },
        trace_payload={"documents": [], "graph": [], "source_mode": "project"},
        retrieve_side_effect=None,
    )
    fake_broker = chat_completion_service.ContextBroker(
        None, None, None, None
    )
    fake_broker.retrieve_obsidian_context_command = AsyncMock(return_value=[])
    monkeypatch.setattr(
        chat_completion_service, "ContextBroker", lambda *args, **kwargs: fake_broker
    )

    task = _task_with_origin(
        _context_plan_origin(
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model=None,
        origin=origin,
    )
    (
        messages,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert captured["connector_query"] == "memory decay"
    assert captured["connector_user_id"] == "local"
    assert captured["connector_project_id"] == 42
    assert captured["source_mode"] == "project"
    assert provider == "local"
    assert model == "local-model"
    assert bundle["semantic"] == [{"text": "thread semantic"}]
    assert bundle["connector_context"][0]["retrieval_lane"] == "connector_context"
    assert bundle["connector_context"][0]["connector_id"] == "obsidian"
    assert bundle["connector_context"][0]["context_command"] == "turn_scoped"
    assert trace["context_request_results"] == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": "executed",
            "result_count": 1,
            "injected": True,
        }
    ]
    assert bundle["_prompt_meta"]["context"]["connector_context"] == {
        "count": 1,
        "injected": True,
        "connectors": {"obsidian": 1},
    }
    assert any(
        "**Connector Context: Obsidian**" in message["content"]
        for message in messages
        if message["role"] == "system"
    )


@pytest.mark.asyncio
async def test_obsidian_context_request_plan_records_no_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(monkeypatch, retrieved_items=[])
    origin = (
        "api:chat.complete|turn_id=abc"
        + encode_context_request_plans_origin_segment(
            [
                {
                    "request_kind": "read_only_context_request",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                    "status": "accepted_not_executed",
                    "execution_required": False,
                }
            ]
        )
    )

    _messages, _provider, _model, bundle, trace = await chat_completion_service.build_messages_for_llm(
        task
    )

    fake_broker.retrieve_obsidian_context_command.assert_awaited_once_with(
        query="memory decay",
        user_id="user-1",
        project_id=42,
        k=4,
        retrieval_policy=ANY,
    )
    assert bundle["connector_context"] == []
    assert bundle["_prompt_meta"]["context"]["connector_context"]["count"] == 0
    assert bundle["_prompt_meta"]["context"]["connector_context"]["injected"] is False
    assert trace["context_request_results"][0]["status"] == "no_results"
    assert trace["context_request_results"][0]["result_count"] == 0
    assert trace["context_request_results"][0]["injected"] is False


@pytest.mark.asyncio
async def test_build_messages_for_llm_records_failed_context_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_service_fakes(
        monkeypatch,
        messages=[{"id": 1, "role": "user", "content": "general ask"}],
        bundle={
            "semantic": [{"text": "thread semantic"}],
            "docs": {"thread": [], "project": [], "global": []},
            "connector_context": [],
        },
        trace_payload={"documents": [], "graph": [], "source_mode": "project"},
        retrieve_side_effect=RuntimeError("boom /tmp/secret"),
    )
    fake_broker = chat_completion_service.ContextBroker(
        None, None, None, None
    )
    fake_broker.retrieve_obsidian_context_command = AsyncMock(
        side_effect=RuntimeError("boom /tmp/secret")
    )
    monkeypatch.setattr(
        chat_completion_service, "ContextBroker", lambda *args, **kwargs: fake_broker
    )

    task = _task_with_origin(
        _context_plan_origin(
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model=None,
        origin=origin,
    )
    (
        _messages,
        _provider,
        _model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert bundle["connector_context"] == []
    assert trace["context_request_results"] == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": "no_results",
            "result_count": 0,
            "injected": False,
        }
    ]
    assert bundle["_prompt_meta"]["context"]["connector_context"] == {
        "count": 0,
        "injected": False,
        "connectors": {},
    }


@pytest.mark.asyncio
async def test_obsidian_context_request_plan_fail_soft_on_retrieval_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        retrieve_exception=RuntimeError("vault missing: /private/tmp/obsidian"),
    )
    origin = (
        "api:chat.complete|turn_id=abc"
        + encode_context_request_plans_origin_segment(
            [
                {
                    "request_kind": "read_only_context_request",
                    "connector_id": "obsidian",
                    "invocation": "turn_scoped",
                    "query_text": "memory decay",
                    "status": "accepted_not_executed",
                    "execution_required": False,
                }
            ]
        )
    )

    _messages, _provider, _model, bundle, trace = await chat_completion_service.build_messages_for_llm(
        task
    )

    fake_broker.retrieve_obsidian_context_command.assert_awaited_once_with(
        query="memory decay",
        user_id="user-1",
        project_id=42,
        k=4,
        retrieval_policy=ANY,
    )
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model=None,
        origin=origin,
    )
    (
        _messages,
        _provider,
        _model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert bundle["connector_context"] == []
    assert trace["context_request_results"][0]["status"] == "failed"
    assert trace["context_request_results"][0]["result_count"] == 0
    assert trace["context_request_results"][0]["injected"] is False
    assert trace["context_request_results"][0]["error"] == "RuntimeError"
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_unsupported_context_request_plans_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_service_fakes(
        monkeypatch,
        messages=[{"id": 1, "role": "user", "content": "general ask"}],
        bundle={
            "semantic": [{"text": "thread semantic"}],
            "docs": {"thread": [], "project": [], "global": []},
            "connector_context": [],
        },
        trace_payload={"documents": [], "graph": [], "source_mode": "project"},
        retrieve_side_effect=None,
    )
    fake_broker = chat_completion_service.ContextBroker(
        None, None, None, None
    )
    fake_broker.retrieve_obsidian_context_command = AsyncMock(
        side_effect=AssertionError("unsupported plan should be ignored")
    )
    monkeypatch.setattr(
        chat_completion_service, "ContextBroker", lambda *args, **kwargs: fake_broker
    )

    task = _task_with_origin(
        _context_plan_origin(
    assert trace["context_request_results"][0]["error"].startswith(
        "RuntimeError: "
    )
    assert bundle["_prompt_meta"]["context"]["connector_context"] == {
        "count": 0,
        "injected": False,
        "connectors": {},
    }


@pytest.mark.asyncio
async def test_unsupported_context_request_plans_are_not_treated_as_successful_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch)
    origin = (
        "api:chat.complete|turn_id=abc"
        + encode_context_request_plans_origin_segment(
            [
                {
                    "request_kind": "read_only_context_request",
                    "connector_id": "github",
                    "invocation": "turn_scoped",
                    "query_text": "repo issue",
                    "query_text": "repo search",
                    "status": "accepted_not_executed",
                    "execution_required": False,
                }
            ]
        )
    )

    _messages, _provider, _model, _bundle, trace = await chat_completion_service.build_messages_for_llm(
        task
    )

    fake_broker.retrieve_obsidian_context_command.assert_not_called()
    assert trace["context_request_results"] == []
    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="local",
        model=None,
        origin=origin,
    )
    (
        _messages,
        _provider,
        _model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert "connector_query" not in captured
    assert bundle["connector_context"] == []
    assert trace["context_request_results"] == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "github",
            "invocation": "turn_scoped",
            "query_text": "repo search",
            "status": "failed",
            "result_count": 0,
            "injected": False,
            "error": "unsupported_context_request_plan",
        }
    ]
