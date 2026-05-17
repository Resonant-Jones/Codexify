from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock
from urllib.parse import quote

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
    messages: list[dict[str, object]] | None = None,
    retrieved_items: list[dict[str, object]] | None = None,
    retrieve_exception: Exception | None = None,
    bundle: dict[str, object] | None = None,
    trace_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    captured: dict[str, object] = {}
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
        "archived_at": None,
    }
    mock_chatlog_db.list_messages.return_value = list(
        messages
        or [{"id": 1, "role": "user", "content": "general ask"}]
    )

    class _FakeBroker:
        def __init__(self, *args, **kwargs):
            captured["broker"] = self
            self.retrieve_obsidian_context_command = AsyncMock(
                side_effect=retrieve_exception,
                return_value=list(retrieved_items or []),
            )

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
            captured["retrieval_override"] = retrieval_override
            captured["retrieval_policy"] = retrieval_policy

            assembled_bundle: dict[str, object] = {
                "semantic": [{"text": "thread semantic"}],
                "docs": {"thread": [], "project": [], "global": []},
                "connector_context": [],
            }
            if bundle:
                assembled_bundle.update(bundle)

            assembled_trace: dict[str, object] = {
                "documents": [],
                "graph": [],
                "source_mode": "project",
            }
            if trace_payload:
                assembled_trace.update(trace_payload)

            return assembled_bundle, assembled_trace

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


def test_context_request_plans_from_origin_decodes_valid_metadata() -> None:
    origin = "api:chat.complete|turn_id=abc" + encode_context_request_plans_origin_segment(
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

    assert _context_request_plans_from_origin(origin) == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": "accepted_not_executed",
            "execution_required": False,
        }
    ]


def test_context_request_plans_from_origin_handles_missing_or_malformed_data() -> None:
    assert _context_request_plans_from_origin("api:chat.complete|turn_id=1") == []
    assert _context_request_plans_from_origin(
        "api:chat.complete|context_request_plans=%7Bnot-json"
    ) == []


@pytest.mark.asyncio
async def test_build_messages_for_llm_consumes_supported_obsidian_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(
        monkeypatch,
        retrieved_items=[
            {
                "text": "obsidian hit",
                "metadata": {"filename": "note.md"},
                "retrieval_lane": "connector_context",
                "connector_id": "obsidian",
                "context_command": "turn_scoped",
            }
        ],
    )
    task = _task_with_origin(
        _context_plan_origin(
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

    messages, provider, model, bundle, trace = (
        await chat_completion_service.build_messages_for_llm(task)
    )

    captured["broker"].retrieve_obsidian_context_command.assert_awaited_once_with(
        query="memory decay",
        user_id="user-1",
        project_id=42,
        k=4,
        retrieval_policy=ANY,
    )
    assert captured["query"] == "general ask"
    assert provider == "local"
    assert model == "local-model"
    assert bundle["semantic"] == [{"text": "thread semantic"}]
    assert bundle["connector_context"] == [
        {
            "text": "obsidian hit",
            "metadata": {"filename": "note.md"},
            "retrieval_lane": "connector_context",
            "connector_id": "obsidian",
            "context_command": "turn_scoped",
        }
    ]
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
    assert messages[-1]["content"] == "general ask"


@pytest.mark.asyncio
async def test_build_messages_for_llm_records_no_results_without_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch, retrieved_items=[])
    task = _task_with_origin(
        _context_plan_origin(
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

    _messages, _provider, _model, bundle, trace = (
        await chat_completion_service.build_messages_for_llm(task)
    )

    captured["broker"].retrieve_obsidian_context_command.assert_awaited_once_with(
        query="memory decay",
        user_id="user-1",
        project_id=42,
        k=4,
        retrieval_policy=ANY,
    )
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


@pytest.mark.asyncio
async def test_build_messages_for_llm_records_failed_context_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(
        monkeypatch,
        retrieve_exception=RuntimeError("vault missing: /private/tmp/obsidian"),
    )
    task = _task_with_origin(
        _context_plan_origin(
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

    _messages, _provider, _model, bundle, trace = (
        await chat_completion_service.build_messages_for_llm(task)
    )

    captured["broker"].retrieve_obsidian_context_command.assert_awaited_once_with(
        query="memory decay",
        user_id="user-1",
        project_id=42,
        k=4,
        retrieval_policy=ANY,
    )
    assert bundle["connector_context"] == []
    assert trace["context_request_results"] == [
        {
            "request_kind": "read_only_context_request",
            "connector_id": "obsidian",
            "invocation": "turn_scoped",
            "query_text": "memory decay",
            "status": "failed",
            "result_count": 0,
            "injected": False,
            "error": "RuntimeError: vault missing: [redacted]",
        }
    ]


@pytest.mark.asyncio
async def test_unsupported_context_request_plans_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch)
    origin = (
        "api:chat.complete|turn_id=abc|context_request_plans="
        + quote(
            json.dumps(
                [
                    {
                        "request_kind": "read_only_context_request",
                        "connector_id": "github",
                        "invocation": "turn_scoped",
                        "query_text": "repo issue",
                        "status": "accepted_not_executed",
                        "execution_required": False,
                    }
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            safe="",
        )
    )
    task = _task_with_origin(origin)

    _messages, _provider, _model, bundle, trace = (
        await chat_completion_service.build_messages_for_llm(task)
    )

    captured["broker"].retrieve_obsidian_context_command.assert_not_called()
    assert bundle["connector_context"] == []
    assert trace["context_request_results"] == []
