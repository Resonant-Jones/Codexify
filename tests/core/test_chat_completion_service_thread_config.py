from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.core.chat_completion_service import (
    resolve_thread_completion_settings,
)
from guardian.tasks.types import ChatCompletionTask


def _seed_completion_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    thread_row: dict[str, object],
) -> dict[str, object]:
    captured: dict[str, object] = {}
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = thread_row
    mock_chatlog_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "What changed?"}
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
        ):
            captured["thread_id"] = thread_id
            captured["query"] = query
            captured["depth_mode"] = depth_mode
            captured["user_id"] = user_id
            captured["project_id"] = project_id
            captured["source_mode"] = source_mode
            return {"semantic": []}, {
                "documents": [],
                "graph": [],
                "source_mode": source_mode,
                "widen_reason": "none",
            }

    def _build_guardian_system_prompt(**kwargs):
        bundle = kwargs.get("bundle") or {}
        captured["prompt_bundle"] = dict(bundle)
        return "BASE SYSTEM", {
            "resolved_persona_id": bundle.get("requested_persona"),
        }

    settings = SimpleNamespace(
        LLM_PROVIDER="groq",
        LOCAL_LLM_MODEL="runtime-local-model",
        DEFAULT_LOCAL_MODEL="runtime-local-model",
        LLM_MODEL="runtime-local-model",
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
        _build_guardian_system_prompt,
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
        "groq",
        raising=False,
    )
    monkeypatch.setattr(
        chat_completion_service.dependencies,
        "DEFAULT_MODEL",
        "runtime-default-model",
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


def test_resolve_thread_completion_settings_prefers_thread_config_over_request_values():
    settings = SimpleNamespace(
        LLM_PROVIDER="groq",
        LOCAL_LLM_MODEL="runtime-local-model",
        DEFAULT_LOCAL_MODEL="runtime-local-model",
        LLM_MODEL="runtime-local-model",
    )
    result = resolve_thread_completion_settings(
        {
            "id": 1,
            "thread_config": {
                "providerId": "local",
                "modelId": "qwen3.5:14b",
                "inferenceMode": "fast",
                "retrievalSource": "personal_knowledge",
                "personaId": "persona-7",
            },
        },
        requested_provider="groq",
        requested_model="override-model",
        requested_reasoning_mode="think",
        requested_source_mode="project",
        settings=settings,
    )

    assert result.provider == "local"
    assert result.model == "qwen3.5:14b"
    assert result.reasoning_mode == "fast"
    assert result.source_mode == "personal_knowledge"
    assert result.persona_id == "persona-7"
    assert result.has_thread_config is True


def test_resolve_thread_completion_settings_null_thread_config_uses_legacy_fallbacks():
    settings = SimpleNamespace(
        LLM_PROVIDER="groq",
        LOCAL_LLM_MODEL="runtime-local-model",
        DEFAULT_LOCAL_MODEL="runtime-local-model",
        LLM_MODEL="runtime-local-model",
    )
    result = resolve_thread_completion_settings(
        {"id": 1, "thread_config": None},
        requested_provider="local",
        requested_model=None,
        requested_reasoning_mode="think",
        requested_source_mode="personal_knowledge",
        settings=settings,
    )

    assert result.provider == "local"
    assert result.model == "runtime-local-model"
    assert result.reasoning_mode == "think"
    assert result.source_mode == "personal_knowledge"
    assert result.persona_id is None
    assert result.has_thread_config is False


@pytest.mark.parametrize(
    (
        "thread_config",
        "requested_provider",
        "requested_model",
        "requested_reasoning_mode",
        "requested_source_mode",
        "expected_provider",
        "expected_model",
        "expected_reasoning_mode",
        "expected_source_mode",
        "expected_has_thread_config",
    ),
    [
        (
            {"providerId": "local"},
            "groq",
            "override-model",
            "think",
            "personal_knowledge",
            "local",
            "runtime-local-model",
            None,
            "project",
            True,
        ),
        (
            "not-json",
            "local",
            "override-model",
            "think",
            "personal_knowledge",
            "local",
            "override-model",
            "think",
            "personal_knowledge",
            False,
        ),
    ],
)
def test_resolve_thread_completion_settings_falls_back_safely_for_partial_or_malformed_thread_config(
    thread_config,
    requested_provider,
    requested_model,
    requested_reasoning_mode,
    requested_source_mode,
    expected_provider,
    expected_model,
    expected_reasoning_mode,
    expected_source_mode,
    expected_has_thread_config,
):
    settings = SimpleNamespace(
        LLM_PROVIDER="groq",
        LOCAL_LLM_MODEL="runtime-local-model",
        DEFAULT_LOCAL_MODEL="runtime-local-model",
        LLM_MODEL="runtime-local-model",
    )
    result = resolve_thread_completion_settings(
        {"id": 1, "thread_config": thread_config},
        requested_provider=requested_provider,
        requested_model=requested_model,
        requested_reasoning_mode=requested_reasoning_mode,
        requested_source_mode=requested_source_mode,
        settings=settings,
    )

    assert result.provider == expected_provider
    assert result.model == expected_model
    assert result.reasoning_mode == expected_reasoning_mode
    assert result.source_mode == expected_source_mode
    assert result.has_thread_config is expected_has_thread_config


@pytest.mark.asyncio
async def test_build_messages_for_llm_uses_thread_config_source_mode_and_persona(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(
        monkeypatch,
        thread_row={
            "id": 1,
            "user_id": "user-1",
            "project_id": 42,
            "thread_config": {
                "providerId": "local",
                "modelId": "qwen3.5:14b",
                "inferenceMode": "fast",
                "retrievalSource": "personal_knowledge",
                "personaId": "persona-7",
            },
        },
    )

    task = ChatCompletionTask(
        user_id="local",
        thread_id=1,
        provider="groq",
        model="override-model",
        reasoning_mode="think",
        origin="api:chat.complete|turn_id=abc|source_mode=project",
    )
    (
        messages,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert messages
    assert provider == "local"
    assert model == "qwen3.5:14b"
    assert captured["source_mode"] == "personal_knowledge"
    assert trace["source_mode"] == "personal_knowledge"
    assert captured["prompt_bundle"]["requested_persona"] == "persona-7"
    assert bundle["_prompt_meta"]["resolved_persona_id"] == "persona-7"
