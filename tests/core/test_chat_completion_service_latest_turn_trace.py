from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.core.chat_completion_service import _latest_turn_trace_fields
from guardian.tasks.types import ChatCompletionTask


def _seed_trace_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    messages: list[dict[str, object]],
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
    return captured


@pytest.mark.asyncio
async def test_build_messages_for_llm_emits_latest_turn_trace_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_trace_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "user", "content": "question A"},
            {"id": 2, "role": "assistant", "content": "answer A"},
            {"id": 3, "role": "user", "content": "question B"},
            {"id": 4, "role": "assistant", "content": "stale assistant"},
        ],
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="local", model=None
    )
    (
        messages,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert provider == "local"
    assert model == "local-model"
    assert captured["query"] == "question B"
    assert messages[-1] == {"role": "user", "content": "question B"}

    completion_assembly = bundle["_completion_assembly"]
    assert completion_assembly["latest_turn"]["id"] == 3
    assert completion_assembly["latest_turn"]["content"] == "question B"
    assert completion_assembly["retrieval_query"] == "question B"
    assert completion_assembly["retrieval_target"] == "latest_turn"
    assert completion_assembly["retrieval_query_matches_latest_turn"] is True

    assert trace["latest_turn_message_id"] == 3
    assert trace["latest_turn_content"] == "question B"
    assert trace["retrieval_query"] == "question B"
    assert trace["retrieval_target"] == "latest_turn"
    assert trace["retrieval_query_matches_latest_turn"] is True


@pytest.mark.asyncio
async def test_build_messages_for_llm_keeps_single_turn_trace_truthful(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_trace_service(
        monkeypatch,
        messages=[
            {"id": 11, "role": "user", "content": "What changed?"},
        ],
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="local", model=None
    )
    (
        messages,
        _provider,
        _model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert messages[-1] == {"role": "user", "content": "What changed?"}
    assert bundle["_completion_assembly"]["latest_turn"]["id"] == 11
    assert trace["latest_turn_message_id"] == 11
    assert trace["retrieval_query"] == "What changed?"
    assert trace["retrieval_target"] == "latest_turn"
    assert trace["retrieval_query_matches_latest_turn"] is True


@pytest.mark.asyncio
async def test_build_messages_for_llm_fails_safe_without_user_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_trace_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "assistant", "content": "answer only"},
            {"id": 2, "role": "assistant", "content": "still answer only"},
        ],
    )

    task = ChatCompletionTask(
        user_id="local", thread_id=1, provider="local", model=None
    )

    with pytest.raises(ValueError, match="thread_has_no_usable_context"):
        await chat_completion_service.build_messages_for_llm(task)

    assert (
        _latest_turn_trace_fields(None, retrieval_query="stale history") == {}
    )
