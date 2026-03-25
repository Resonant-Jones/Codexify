from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


@pytest.mark.asyncio
async def test_build_messages_for_llm_sanitizes_attachment_markers_and_injects_thread_docs(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
    }
    mock_chatlog_db.list_messages.return_value = [
        {
            "id": 1,
            "role": "user",
            "content": (
                "<!-- cfy-media:document:doc-1 -->\n\n"
                "<!-- cfy-media-src:https://example.test/project-plan.pdf -->\n\n"
                "<!-- cfy-media-name:Project Plan.pdf -->\n\n"
                "Please summarize this."
            ),
        }
    ]

    captured: dict[str, str] = {}

    class _FakeBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, thread_id, query, depth_mode, user_id):
            captured["query"] = query
            return (
                {
                    "docs": {
                        "thread": [
                            {
                                "title": "Project Plan.pdf",
                                "excerpt": "Quarterly goals and milestones.",
                                "provenance": {"relation": "attached"},
                            }
                        ]
                    }
                },
                None,
            )

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
        lambda **kwargs: ("BASE SYSTEM", {"estimated_tokens": 16}),
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

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)

    (
        messages_for_llm,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert provider == "local"
    assert model == "local-model"
    assert trace is None
    assert bundle["docs"]["thread"][0]["title"] == "Project Plan.pdf"
    assert captured["query"] == (
        "Attached document: Project Plan.pdf\n\nPlease summarize this."
    )
    assert bundle["_prompt_meta"]["docs"]["count"] == 1
    assert bundle["_prompt_meta"]["docs"]["injected"] is True
    assert messages_for_llm[0] == {"role": "system", "content": "BASE SYSTEM"}
    assert messages_for_llm[1]["role"] == "system"
    assert messages_for_llm[1]["content"].startswith(
        "Linked document excerpts are available"
    )
    assert "Project Plan.pdf" in messages_for_llm[1]["content"]
    assert messages_for_llm[-1] == {
        "role": "user",
        "content": (
            "Attached document: Project Plan.pdf\n\nPlease summarize this."
        ),
    }


@pytest.mark.asyncio
async def test_build_messages_for_llm_no_doc_injection_when_empty(
    monkeypatch: pytest.MonkeyPatch,
):
    """Doc prompt is omitted and meta stays accurate when no linked docs."""
    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 42,
    }
    mock_chatlog_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "Hello"}
    ]

    class _EmptyBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, thread_id, query, depth_mode, user_id):
            return {"docs": {"thread": [], "project": []}}, None

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
        lambda **kwargs: ("BASE SYSTEM", {"estimated_tokens": 16}),
    )
    monkeypatch.setattr(chat_completion_service, "ContextBroker", _EmptyBroker)
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

    task = ChatCompletionTask(thread_id=1, provider="local", model=None)
    (
        messages_for_llm,
        provider,
        model,
        bundle,
        trace,
    ) = await chat_completion_service.build_messages_for_llm(task)

    assert provider == "local"
    assert model == "local-model"
    assert bundle["_prompt_meta"]["docs"]["count"] == 0
    assert bundle["_prompt_meta"]["docs"]["injected"] is False
    assert all(
        "Linked document excerpts" not in msg.get("content", "")
        for msg in messages_for_llm
        if msg.get("role") == "system"
    )
