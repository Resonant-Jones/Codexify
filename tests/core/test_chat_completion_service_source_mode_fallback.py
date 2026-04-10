from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import quote

import pytest

from guardian.context.retrieval_router_policy import (
    RETRIEVAL_OVERRIDE_CONVERSATION,
    RETRIEVAL_OVERRIDE_NONE,
    RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE,
    RETRIEVAL_OVERRIDE_PROJECT,
    SOURCE_MODE_CONVERSATION,
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_PROJECT,
    WIDEN_REASON_NONE,
)
from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask, task_from_dict


def _seed_completion_service(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    captured: dict[str, object] = {}
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
    }
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
            source_mode=SOURCE_MODE_PROJECT,
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
                "widen_reason": WIDEN_REASON_NONE,
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


def _origin_with_source_mode_and_override(
    *,
    source_mode: str | None = None,
    retrieval_override: dict[str, object] | str | None = None,
) -> str:
    segments = ["api:chat.complete", "turn_id=abc"]
    if source_mode is not None:
        segments.append(f"source_mode={source_mode}")
    if retrieval_override is not None:
        if isinstance(retrieval_override, str):
            encoded_override = retrieval_override
        else:
            encoded_override = quote(
                json.dumps(retrieval_override, separators=(",", ":"))
            )
        segments.append(f"retrieval_override={encoded_override}")
    return "|".join(segments)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        "api:chat.complete|turn_id=abc",
        "api:chat.complete|turn_id=abc|source_mode=invalid",
        "api:chat.complete|turn_id=abc|retrieval_override=not-json",
        "malformed-origin-payload",
    ],
)
async def test_build_messages_for_llm_defaults_to_project_for_missing_or_malformed_origin(
    monkeypatch: pytest.MonkeyPatch, origin: str | None
) -> None:
    captured = _seed_completion_service(monkeypatch)

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        origin=origin,
    )
    (
        messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert messages
    assert captured["project_id"] == 42
    assert captured["source_mode"] == SOURCE_MODE_PROJECT
    assert trace["source_mode"] == SOURCE_MODE_PROJECT
    assert trace["widen_reason"] == WIDEN_REASON_NONE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requested_source_mode",
    [
        SOURCE_MODE_PROJECT,
        SOURCE_MODE_PERSONAL_KNOWLEDGE,
        SOURCE_MODE_CONVERSATION,
    ],
)
async def test_build_messages_for_llm_keeps_requested_source_mode_without_override(
    monkeypatch: pytest.MonkeyPatch,
    requested_source_mode: str,
) -> None:
    captured = _seed_completion_service(monkeypatch)

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        origin=_origin_with_source_mode_and_override(
            source_mode=requested_source_mode,
        ),
    )
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert captured["source_mode"] == requested_source_mode
    assert trace["source_mode"] == requested_source_mode
    assert trace["widen_reason"] == WIDEN_REASON_NONE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requested_source_mode,retrieval_override,expected_source_mode",
    [
        (
            SOURCE_MODE_PROJECT,
            {"mode": RETRIEVAL_OVERRIDE_PROJECT},
            SOURCE_MODE_PROJECT,
        ),
        (
            SOURCE_MODE_PROJECT,
            {"mode": RETRIEVAL_OVERRIDE_PERSONAL_KNOWLEDGE},
            SOURCE_MODE_PERSONAL_KNOWLEDGE,
        ),
        (
            SOURCE_MODE_PERSONAL_KNOWLEDGE,
            {"mode": RETRIEVAL_OVERRIDE_NONE},
            SOURCE_MODE_PERSONAL_KNOWLEDGE,
        ),
        (
            SOURCE_MODE_PERSONAL_KNOWLEDGE,
            {"mode": RETRIEVAL_OVERRIDE_CONVERSATION},
            SOURCE_MODE_CONVERSATION,
        ),
        (
            SOURCE_MODE_PERSONAL_KNOWLEDGE,
            {"mode": "bogus"},
            SOURCE_MODE_PERSONAL_KNOWLEDGE,
        ),
    ],
)
async def test_build_messages_for_llm_applies_explicit_retrieval_override_modes_on_queued_task(
    monkeypatch: pytest.MonkeyPatch,
    requested_source_mode: str,
    retrieval_override: dict[str, object],
    expected_source_mode: str,
) -> None:
    captured = _seed_completion_service(monkeypatch)

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        origin=_origin_with_source_mode_and_override(
            source_mode=requested_source_mode,
        ),
        retrieval_override=retrieval_override,
    )
    queued_task = task_from_dict(task.to_dict())
    assert isinstance(queued_task, ChatCompletionTask)
    assert queued_task.retrieval_override == retrieval_override
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(queued_task)

    assert captured["source_mode"] == expected_source_mode
    assert trace["source_mode"] == expected_source_mode
    assert trace["widen_reason"] == WIDEN_REASON_NONE
