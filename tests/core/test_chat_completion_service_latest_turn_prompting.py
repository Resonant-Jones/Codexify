from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


def _seed_prompt_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    messages: list[dict[str, object]],
) -> None:
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
    }
    mock_chatlog_db.list_messages.return_value = messages

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
            return {"semantic": []}, {
                "documents": [],
                "graph": [],
                "source_mode": source_mode,
                "widen_reason": "none",
            }

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


@pytest.mark.asyncio
async def test_build_messages_for_llm_adds_latest_turn_only_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_prompt_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "system", "content": "BASE SYSTEM"},
            {"id": 2, "role": "user", "content": "first question"},
            {"id": 3, "role": "assistant", "content": "first answer"},
            {"id": 4, "role": "user", "content": "second question"},
            {"id": 5, "role": "assistant", "content": "stale assistant"},
        ],
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        messages,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert provider == "local"
    assert model == "local-model"
    assert messages[0] == {"role": "system", "content": "BASE SYSTEM"}
    assert "prior messages as context only" in messages[1]["content"]
    assert "most recent user message" in messages[1]["content"]
    assert [msg["content"] for msg in messages if msg["role"] == "user"] == [
        "first question",
        "second question",
    ]
    assert messages[-1] == {"role": "user", "content": "second question"}
    assert all(msg["content"] != "stale assistant" for msg in messages)
    assert bundle["_completion_assembly"]["latest_turn"]["id"] == 4
    assert [
        msg["content"]
        for msg in bundle["_completion_assembly"]["history"]
        if msg["role"] == "user"
    ] == [
        "first question",
    ]
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_build_messages_for_llm_keeps_normal_single_turn_threads_functional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_prompt_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "user", "content": "What changed?"},
        ],
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        messages,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert provider == "local"
    assert model == "local-model"
    assert messages[0] == {"role": "system", "content": "BASE SYSTEM"}
    assert "most recent user message" in messages[1]["content"]
    assert messages[-1] == {"role": "user", "content": "What changed?"}
    assert bundle["_completion_assembly"]["history"] == []
    assert (
        bundle["_completion_assembly"]["latest_turn"]["content"]
        == "What changed?"
    )
    assert trace["source_mode"] == "project"
