from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


def _seed_retrieval_service(
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
async def test_build_messages_for_llm_uses_newest_user_turn_for_retrieval_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_retrieval_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "user", "content": "question A"},
            {"id": 2, "role": "assistant", "content": "answer A"},
            {"id": 3, "role": "user", "content": "question B"},
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
    assert captured["query"] == "question B"
    assert (
        bundle["_completion_assembly"]["latest_turn"]["content"] == "question B"
    )
    assert messages[-1] == {"role": "user", "content": "question B"}
    assert [msg["content"] for msg in messages if msg["role"] == "user"] == [
        "question A",
        "question B",
    ]
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_build_messages_for_llm_keeps_older_user_turns_out_of_retrieval_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_retrieval_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "user", "content": "question A"},
            {"id": 2, "role": "assistant", "content": "answer A"},
            {"id": 3, "role": "user", "content": "question B"},
            {"id": 4, "role": "assistant", "content": "answer B"},
            {"id": 5, "role": "user", "content": "question C"},
        ],
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        messages,
        _provider,
        _model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert captured["query"] == "question C"
    assert bundle["_completion_assembly"]["latest_turn"]["id"] == 5
    assert [msg["id"] for msg in bundle["_completion_assembly"]["history"]] == [
        1,
        2,
        3,
        4,
    ]
    assert [
        msg["content"]
        for msg in bundle["_completion_assembly"]["history"]
        if msg["role"] == "user"
    ] == [
        "question A",
        "question B",
    ]
    assert messages[-1] == {"role": "user", "content": "question C"}
    assert [msg["content"] for msg in messages if msg["role"] == "user"] == [
        "question A",
        "question B",
        "question C",
    ]
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_build_messages_for_llm_keeps_single_turn_retrieval_normal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_retrieval_service(
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
    assert captured["query"] == "What changed?"
    assert bundle["_completion_assembly"]["history"] == []
    assert (
        bundle["_completion_assembly"]["latest_turn"]["content"]
        == "What changed?"
    )
    assert messages[-1] == {"role": "user", "content": "What changed?"}
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_build_messages_for_llm_fails_safe_without_latest_user_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_retrieval_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "assistant", "content": "answer only"},
            {"id": 2, "role": "assistant", "content": "still answer only"},
        ],
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)

    with pytest.raises(ValueError, match="thread_has_no_usable_context"):
        await chat_completion_service.build_messages_for_llm(task)
