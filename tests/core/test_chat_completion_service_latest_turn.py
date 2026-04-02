from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.core.chat_completion_service import split_history_and_latest_turn
from guardian.tasks.types import ChatCompletionTask


def _seed_completion_service(
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


def test_split_history_and_latest_turn_selects_latest_user_message() -> None:
    messages = [
        {"id": 1, "role": "system", "content": "BASE SYSTEM"},
        {"id": 2, "role": "user", "content": "first question"},
        {"id": 3, "role": "assistant", "content": "first answer"},
        {"id": 4, "role": "user", "content": "second question"},
        {"id": 5, "role": "assistant", "content": "stale assistant"},
    ]

    result = split_history_and_latest_turn(messages)

    assert [msg["id"] for msg in result["history"]] == [1, 2, 3]
    assert result["latest_turn"] is not None
    assert result["latest_turn"]["id"] == 4
    assert result["latest_turn"]["content"] == "second question"
    assert all(msg["id"] != 5 for msg in result["history"])


def test_split_history_and_latest_turn_returns_safe_null_when_no_user() -> None:
    messages = [
        {"id": 1, "role": "assistant", "content": "answer only"},
        {"id": 2, "role": "assistant", "content": "still answer only"},
    ]

    result = split_history_and_latest_turn(messages)

    assert [msg["id"] for msg in result["history"]] == [1, 2]
    assert result["latest_turn"] is None


def test_split_history_and_latest_turn_honors_explicit_target_message_id() -> (
    None
):
    messages = [
        {"id": 1, "role": "system", "content": "BASE SYSTEM"},
        {"id": 2, "role": "user", "content": "first question"},
        {"id": 3, "role": "assistant", "content": "first answer"},
        {"id": 4, "role": "user", "content": "second question"},
        {"id": 5, "role": "assistant", "content": "second answer"},
        {"id": 6, "role": "user", "content": "newer question"},
    ]

    result = split_history_and_latest_turn(messages, latest_turn_message_id=4)

    assert [msg["id"] for msg in result["history"]] == [1, 2, 3]
    assert result["latest_turn"] is not None
    assert result["latest_turn"]["id"] == 4
    assert result["latest_turn"]["content"] == "second question"
    assert all(msg["id"] != 6 for msg in result["history"])


@pytest.mark.asyncio
async def test_build_messages_for_llm_fails_safely_without_user_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "assistant", "content": "answer only"},
            {"id": 2, "role": "assistant", "content": "more answer only"},
        ],
    )

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)

    with pytest.raises(ValueError, match="thread_has_no_usable_context"):
        await chat_completion_service.build_messages_for_llm(task)


@pytest.mark.asyncio
async def test_build_messages_for_llm_preserves_latest_turn_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(
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
    assert captured["query"] == "second question"
    assert messages[-1] == {"role": "user", "content": "second question"}
    assert all(msg.get("content") != "stale assistant" for msg in messages)

    completion_assembly = bundle["_completion_assembly"]
    assert [msg["id"] for msg in completion_assembly["history"]] == [1, 2, 3]
    assert completion_assembly["latest_turn"]["id"] == 4
    assert isinstance(completion_assembly["retrieved_context"], list)
    assert trace["source_mode"] == "project"


@pytest.mark.asyncio
async def test_build_messages_for_llm_honors_explicit_target_message_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "system", "content": "BASE SYSTEM"},
            {"id": 2, "role": "user", "content": "first question"},
            {"id": 3, "role": "assistant", "content": "first answer"},
            {"id": 4, "role": "user", "content": "second question"},
            {"id": 5, "role": "assistant", "content": "second answer"},
            {"id": 6, "role": "user", "content": "newer question"},
        ],
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        latest_turn_message_id=4,
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
    assert captured["query"] == "second question"
    assert messages[-1] == {"role": "user", "content": "second question"}
    assert [msg["content"] for msg in messages if msg["role"] == "user"] == [
        "first question",
        "second question",
    ]
    completion_assembly = bundle["_completion_assembly"]
    assert [msg["id"] for msg in completion_assembly["history"]] == [1, 2, 3]
    assert completion_assembly["latest_turn"]["id"] == 4
    assert trace["latest_turn_message_id"] == 4
    assert trace["retrieval_query"] == "second question"
    assert trace["retrieval_target"] == "latest_turn"


@pytest.mark.asyncio
async def test_build_messages_for_llm_fails_when_explicit_target_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_completion_service(
        monkeypatch,
        messages=[
            {"id": 1, "role": "user", "content": "first question"},
            {"id": 2, "role": "assistant", "content": "first answer"},
            {"id": 3, "role": "user", "content": "second question"},
        ],
    )

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        latest_turn_message_id=999,
    )

    with pytest.raises(ValueError, match="thread_target_turn_missing"):
        await chat_completion_service.build_messages_for_llm(task)
