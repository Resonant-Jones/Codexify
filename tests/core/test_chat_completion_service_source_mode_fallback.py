from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import quote

import pytest

from guardian.context.retrieval_posture_contract import (
    build_retrieval_posture_snapshot,
)
from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


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
@pytest.mark.parametrize(
    "origin",
    [
        None,
        "",
        "api:chat.complete|turn_id=abc",
        "api:chat.complete|turn_id=abc|source_mode=invalid",
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
    assert captured["source_mode"] == "project"
    assert trace["source_mode"] == "project"
    assert trace["widen_reason"] == "none"


@pytest.mark.asyncio
async def test_build_messages_for_llm_respects_personal_knowledge_origin_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch)

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        origin="api:chat.complete|turn_id=abc|source_mode=personal_knowledge",
    )
    (
        _messages,
        _provider,
        _model,
        _bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert captured["source_mode"] == "personal_knowledge"
    assert trace["source_mode"] == "personal_knowledge"
    assert trace["widen_reason"] == "none"


@pytest.mark.parametrize(
    ("snapshot_kwargs", "expected_snapshot"),
    [
        (
            {
                "source_mode": "personal_knowledge",
                "retrieval_override": {
                    "mode": "personal_knowledge",
                    "reason": "slash_personal_knowledge_hint",
                },
                "widen_reason": "explicit_personal_knowledge",
                "conversation_only": True,
            },
            {
                "source_mode": "personal_knowledge",
                "boundary_label": "conversation_only",
                "retrieval_override_mode": "personal_knowledge",
                "widen_reason": "explicit_personal_knowledge",
                "conversation_only": True,
            },
        ),
        (
            {
                "source_mode": "not-a-real-mode",
                "retrieval_override": {"mode": "bogus"},
                "widen_reason": None,
                "conversation_only": "yes",
            },
            {
                "source_mode": "project",
                "boundary_label": "same_user_same_project",
                "retrieval_override_mode": "none",
                "widen_reason": "none",
                "conversation_only": False,
            },
        ),
    ],
)
def test_build_retrieval_posture_snapshot_normalizes_supported_and_malformed_inputs(
    snapshot_kwargs: dict[str, object],
    expected_snapshot: dict[str, object],
) -> None:
    assert (
        build_retrieval_posture_snapshot(**snapshot_kwargs) == expected_snapshot
    )


def test_run_chat_completion_task_emits_retrieval_posture_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _seed_completion_service(monkeypatch)
    chat_completion_service.dependencies.chatlog_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "hello"}
    ]

    def _empty_stream(*_args, **_kwargs):
        if False:
            yield ""

    monkeypatch.setattr(chat_completion_service, "stream_local", _empty_stream)
    monkeypatch.setattr(
        chat_completion_service,
        "chat_with_ai",
        lambda *args, **kwargs: "ok",
    )

    retrieval_override = {
        "mode": "personal_knowledge",
        "reason": "slash_personal_knowledge_hint",
    }
    origin = (
        "api:chat.complete|turn_id=abc|source_mode=personal_knowledge"
        f"|retrieval_override={quote(json.dumps(retrieval_override, separators=(',', ':')), safe='')}"
    )
    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        origin=origin,
    )

    result = chat_completion_service.run_chat_completion_task(
        task,
        persist_assistant_message=False,
    )

    expected_snapshot = build_retrieval_posture_snapshot(
        source_mode="personal_knowledge",
        retrieval_override=retrieval_override,
        widen_reason="none",
        conversation_only=True,
    )

    assert captured["source_mode"] == "personal_knowledge"
    assert result["trace"]["source_mode"] == "personal_knowledge"
    assert result["trace"]["widen_reason"] == "none"
    assert result["payload_summary"]["retrieval_override"] == retrieval_override
    assert result["payload_summary"]["retrieval_posture"] == expected_snapshot
