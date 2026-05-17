from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


def _base_task() -> ChatCompletionTask:
    return ChatCompletionTask(
        user_id="user-1",
        thread_id=1,
        provider="local",
        model=None,
    )


def _seed_completion_service(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    captured: dict[str, object] = {
        "assemble_calls": [],
    }
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
        "archived_at": None,
    }
    mock_chatlog_db.list_messages.return_value = [
        {"id": 1, "role": "assistant", "content": "prior assistant context"},
        {"id": 2, "role": "user", "content": "alpha request"},
    ]

    class _FakeBroker:
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)

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
            **kwargs,
        ):
            captured["assemble_calls"].append(
                {
                    "thread_id": thread_id,
                    "query": query,
                    "depth_mode": depth_mode,
                    "user_id": user_id,
                    "project_id": project_id,
                    "source_mode": source_mode,
                    "retrieval_override": retrieval_override,
                    "retrieval_policy": retrieval_policy,
                    "kwargs": dict(kwargs),
                }
            )
            bundle: dict[str, object] = {
                "semantic": [{"id": "sem-1", "text": "semantic hit"}],
                "docs": {
                    "thread": [
                        {
                            "id": "doc-1",
                            "title": "Thread doc",
                            "excerpt": "doc excerpt",
                        }
                    ],
                    "project": [],
                    "global": [],
                },
                "memory": [
                    {
                        "id": "selected-1",
                        "user_id": "user-1",
                        "metadata": {"id": "selected-1"},
                        "text": "selected raw memory body",
                    },
                    {
                        "id": "suppressed-1",
                        "user_id": "user-1",
                        "metadata": {"id": "suppressed-1"},
                        "text": "suppressed raw memory body",
                    },
                    {
                        "user_id": "user-1",
                        "metadata": {"identity_depth": "light"},
                        "text": "no-id memory body",
                    },
                ],
            }
            trace: dict[str, object] = {
                "source_mode": "project",
                "documents": [],
                "graph": [],
            }

            trace_enabled = bool(
                kwargs.get("enable_memory_preselection_trace")
                or kwargs.get("enable_memory_preselection_active")
            )
            active_enabled = bool(
                kwargs.get("enable_memory_preselection_active")
            )
            if trace_enabled:
                trace["memory_preselection"] = {
                    "mode": "active" if active_enabled else "trace_only",
                    "enabled": True,
                    "active": active_enabled,
                    "selected_count": 1,
                    "suppressed_count": 1,
                    "selected_candidate_ids": ["selected-1"],
                    "suppressed": [
                        {
                            "candidate_id": "suppressed-1",
                            "reason": "not_relevant",
                        }
                    ],
                    "affected_retrieval": active_enabled,
                    "affected_prompt_injection": active_enabled,
                    "active_influence": {
                        "applied": active_enabled,
                        "allowed_candidate_ids": ["selected-1"],
                        "removed_candidate_ids": (
                            ["suppressed-1"] if active_enabled else []
                        ),
                        "unchanged_item_count": 2 if active_enabled else 3,
                    },
                }
            if active_enabled:
                bundle["memory"] = [
                    {
                        "id": "selected-1",
                        "user_id": "user-1",
                        "metadata": {"id": "selected-1"},
                        "text": "selected raw memory body",
                    },
                    {
                        "user_id": "user-1",
                        "metadata": {"identity_depth": "light"},
                        "text": "no-id memory body",
                    },
                ]

            return bundle, trace

    settings = SimpleNamespace(
        LLM_PROVIDER="local",
        LOCAL_LLM_MODEL="local-model",
        DEFAULT_LOCAL_MODEL="local-model",
        LLM_MODEL="local-model",
    )

    def _fake_context_message_with_meta(bundle: dict[str, object] | None):
        memory_ids = []
        for item in (bundle or {}).get("memory", []) or []:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("id") or "").strip()
            if candidate_id:
                memory_ids.append(candidate_id)
        message = "memory_ids:" + ",".join(memory_ids)
        return message, {"semantic": {"injected": True}}

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
    monkeypatch.setattr(
        chat_completion_service,
        "build_context_system_message_with_meta",
        _fake_context_message_with_meta,
    )
    monkeypatch.setattr(
        chat_completion_service, "resolve_thread_system_profile", None
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


async def _build(
    monkeypatch: pytest.MonkeyPatch,
    **kwargs,
) -> tuple[
    dict[str, object],
    list[dict[str, str]],
    str,
    str,
    dict[str, object],
    dict[str, object] | None,
]:
    captured = _seed_completion_service(monkeypatch)
    messages, provider, model, bundle, trace = (
        await chat_completion_service.build_messages_for_llm(
            _base_task(),
            **kwargs,
        )
    )
    return captured, messages, provider, model, bundle, trace


@pytest.mark.asyncio
async def test_no_preselection_options_forwarded_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, *_rest = await _build(monkeypatch)
    call = captured["assemble_calls"][0]
    assert call["kwargs"] == {}


@pytest.mark.asyncio
async def test_output_unchanged_when_no_options_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, messages_a, provider_a, model_a, bundle_a, trace_a = await _build(
        monkeypatch
    )
    _, messages_b, provider_b, model_b, bundle_b, trace_b = await _build(
        monkeypatch,
        enable_memory_preselection_trace=False,
        enable_memory_preselection_active=False,
    )
    assert messages_a == messages_b
    assert provider_a == provider_b
    assert model_a == model_b
    assert bundle_a == bundle_b
    assert trace_a == trace_b


@pytest.mark.asyncio
async def test_trace_unchanged_when_no_options_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _messages, _provider, _model, _bundle, trace = await _build(monkeypatch)
    assert isinstance(trace, dict)
    assert "memory_preselection" not in trace


@pytest.mark.asyncio
async def test_trace_only_option_forwards_trace_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, *_rest = await _build(
        monkeypatch,
        enable_memory_preselection_trace=True,
    )
    call = captured["assemble_calls"][0]
    assert call["kwargs"]["enable_memory_preselection_trace"] is True


@pytest.mark.asyncio
async def test_trace_only_option_does_not_forward_active_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, *_rest = await _build(
        monkeypatch,
        enable_memory_preselection_trace=True,
    )
    call = captured["assemble_calls"][0]
    assert "enable_memory_preselection_active" not in call["kwargs"]


@pytest.mark.asyncio
async def test_active_option_forwards_active_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured, *_rest = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
    )
    call = captured["assemble_calls"][0]
    assert call["kwargs"]["enable_memory_preselection_active"] is True


@pytest.mark.asyncio
async def test_active_option_returns_preselection_trace_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _messages, _provider, _model, _bundle, trace = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
    )
    assert isinstance(trace, dict)
    payload = trace["memory_preselection"]
    assert payload["mode"] == "active"
    assert payload["active"] is True


@pytest.mark.asyncio
async def test_trace_only_mode_keeps_prompt_bound_context_content_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, messages_base, _provider, _model, bundle_base, _trace_base = await _build(
        monkeypatch
    )
    _, messages_trace, _provider2, _model2, bundle_trace, _trace_trace = await _build(
        monkeypatch,
        enable_memory_preselection_trace=True,
    )
    assert bundle_base == bundle_trace
    assert messages_base == messages_trace


@pytest.mark.asyncio
async def test_active_mode_changes_only_memory_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _messages_base, _provider, _model, bundle_base, _trace_base = await _build(
        monkeypatch
    )
    _, _messages_active, _provider2, _model2, bundle_active, _trace_active = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
    )

    assert bundle_base["memory"] != bundle_active["memory"]
    for key in ("semantic", "docs", "messages", "graph", "obsidian"):
        if key in bundle_base or key in bundle_active:
            assert bundle_base.get(key) == bundle_active.get(key)


@pytest.mark.asyncio
async def test_active_mode_does_not_change_semantic_vector_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_base, *_rest = await _build(monkeypatch)
    captured_active, *_rest2 = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
    )
    base_call = captured_base["assemble_calls"][0]
    active_call = captured_active["assemble_calls"][0]
    for key in (
        "query",
        "depth_mode",
        "thread_id",
        "user_id",
        "source_mode",
        "retrieval_override",
        "retrieval_policy",
    ):
        assert base_call[key] == active_call[key]


@pytest.mark.asyncio
async def test_active_mode_does_not_change_document_retrieval_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_base, *_rest = await _build(monkeypatch)
    captured_active, *_rest2 = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
    )
    base_call = captured_base["assemble_calls"][0]
    active_call = captured_active["assemble_calls"][0]
    assert base_call["project_id"] == active_call["project_id"]
    assert base_call["source_mode"] == active_call["source_mode"]


@pytest.mark.asyncio
async def test_active_mode_does_not_change_project_thread_message_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, messages_base, *_rest = await _build(monkeypatch)
    _, messages_active, *_rest2 = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
    )
    history_base = [
        msg for msg in messages_base if msg["role"] in {"assistant", "user"}
    ]
    history_active = [
        msg for msg in messages_active if msg["role"] in {"assistant", "user"}
    ]
    assert history_base == history_active


@pytest.mark.asyncio
async def test_missing_options_preserve_provider_model_selection_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _messages, provider, model, _bundle, _trace = await _build(monkeypatch)
    assert provider == "local"
    assert model == "local-model"


def test_missing_options_preserve_tool_loop_invocation_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_build_messages_for_llm_compat(task, *, user_id=None):
        captured["compat_task"] = task
        captured["compat_user_id"] = user_id
        return (
            [
                {"role": "system", "content": "BASE SYSTEM"},
                {"role": "user", "content": "alpha"},
            ],
            "local",
            "local-model",
            {"semantic": [], "docs": {"thread": [], "project": [], "global": []}},
            {"source_mode": "project", "documents": [], "graph": []},
        )

    def _fake_execute(task, *, provider, model, messages_for_llm, **kwargs):
        captured["execute_task"] = task
        captured["execute_provider"] = provider
        captured["execute_model"] = model
        captured["execute_messages"] = list(messages_for_llm)
        return {
            "assistant_text": "ok",
            "provider": provider,
            "model": model,
            "bundle": kwargs.get("bundle"),
            "trace": kwargs.get("trace"),
            "payload_summary": dict(kwargs.get("base_payload_summary") or {}),
            "execution": {
                "attempted_provider": provider,
                "attempted_model": model,
                "final_provider": provider,
                "final_model": model,
                "fallback_triggered": False,
            },
        }

    monkeypatch.setattr(
        chat_completion_service,
        "_build_messages_for_llm_compat",
        _fake_build_messages_for_llm_compat,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "_execute_bounded_tool_turn_completion",
        _fake_execute,
    )
    monkeypatch.setattr(
        chat_completion_service,
        "get_settings",
        lambda: SimpleNamespace(
            LLM_PROVIDER="local",
            LOCAL_LLM_MODEL="local-model",
            DEFAULT_LOCAL_MODEL="local-model",
            LLM_MODEL="local-model",
        ),
    )
    result = chat_completion_service.run_chat_completion_task(
        _base_task(),
        persist_assistant_message=False,
    )

    assert captured["compat_user_id"] is None
    assert captured["execute_provider"] == "local"
    assert captured["execute_model"] == "local-model"
    assert result["provider"] == "local"
    assert result["model"] == "local-model"


@pytest.mark.asyncio
async def test_candidate_headers_forwarded_only_when_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate_headers = [
        {
            "candidate_id": "cand-1",
            "user_id": "user-1",
            "kind": "semantic",
            "title": "alpha title",
            "identity_depth": "light",
        }
    ]
    captured_default, *_rest = await _build(monkeypatch)
    captured_with_headers, *_rest2 = await _build(
        monkeypatch,
        memory_preselection_candidate_headers=candidate_headers,
    )
    assert (
        "memory_preselection_candidate_headers"
        not in captured_default["assemble_calls"][0]["kwargs"]
    )
    assert (
        captured_with_headers["assemble_calls"][0]["kwargs"][
            "memory_preselection_candidate_headers"
        ]
        == candidate_headers
    )


@pytest.mark.asyncio
async def test_preselection_trace_does_not_expose_raw_memory_body_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _messages, _provider, _model, _bundle, trace = await _build(
        monkeypatch,
        enable_memory_preselection_trace=True,
    )
    assert isinstance(trace, dict)
    payload = trace["memory_preselection"]
    payload_text = str(payload)
    assert "selected raw memory body" not in payload_text
    assert "suppressed raw memory body" not in payload_text


def test_pass_through_helper_has_no_direct_db_vector_llm_network_calls() -> None:
    source = inspect.getsource(
        chat_completion_service._broker_memory_preselection_kwargs
    )
    for token in ("requests.", "chat_with_ai", "redis", "sqlalchemy", "vector"):
        assert token not in source


@pytest.mark.asyncio
async def test_repeated_explicit_option_calls_are_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, first_messages, first_provider, first_model, first_bundle, first_trace = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=[
            {
                "candidate_id": "cand-1",
                "user_id": "user-1",
                "kind": "semantic",
                "title": "alpha title",
                "identity_depth": "light",
            }
        ],
    )
    _, second_messages, second_provider, second_model, second_bundle, second_trace = await _build(
        monkeypatch,
        enable_memory_preselection_active=True,
        enable_memory_preselection_trace=True,
        memory_preselection_candidate_headers=[
            {
                "candidate_id": "cand-1",
                "user_id": "user-1",
                "kind": "semantic",
                "title": "alpha title",
                "identity_depth": "light",
            }
        ],
    )

    assert first_messages == second_messages
    assert first_provider == second_provider
    assert first_model == second_model
    assert first_bundle == second_bundle
    assert first_trace == second_trace
