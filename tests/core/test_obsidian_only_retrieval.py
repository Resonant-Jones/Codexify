from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardian.context.broker import ContextBroker
from guardian.core import chat_completion_service
from guardian.tasks.types import ChatCompletionTask


@pytest.mark.asyncio
async def test_obsidian_only_retrieval_returns_only_obsidian_hits() -> None:
    chatlog_db = AsyncMock()
    chatlog_db.last_messages = MagicMock(
        return_value=[{"id": 1, "role": "user", "content": "Find the note"}]
    )
    chatlog_db.get_chat_thread = MagicMock(
        return_value={"id": 1, "user_id": "user-1", "project_id": 10}
    )
    chatlog_db.get_connector_config = MagicMock(
        return_value={
            "name": "obsidian_local",
            "type": "obsidian",
            "settings": {"vault_root": "/vault", "enabled": True},
        }
    )
    vector_store = AsyncMock()

    def _search(query, k, namespace=None):
        if namespace == "obsidian:local":
            return [
                {
                    "id": "obs-1",
                    "text": "obsidian note hit",
                    "metadata": {"filename": "note.md"},
                    "score": 0.99,
                }
            ]
        raise AssertionError(
            f"semantic widening should not run for namespace={namespace!r}"
        )

    vector_store.search = MagicMock(side_effect=_search)

    broker = ContextBroker(
        chatlog_db=chatlog_db,
        vector_store=vector_store,
        memory_store=AsyncMock(),
        sensors=None,
        settings=SimpleNamespace(GUARDIAN_ENABLE_GRAPH_CONTEXT=True),
    )
    broker.get_scoped_documents = AsyncMock(
        side_effect=AssertionError("document widening should not run")
    )

    context, trace = await broker.assemble(
        thread_id=1,
        query="Find the note",
        depth_mode="normal",
        source_mode="obsidian_only",
    )

    assert context["semantic"] == []
    assert context["memory"] == []
    assert context["docs"] == {"project": [], "thread": [], "global": []}
    assert context["obsidian"] == [
        {
            "id": "obs-1",
            "text": "obsidian note hit",
            "metadata": {"filename": "note.md"},
            "score": 0.99,
        }
    ]
    assert context["retrieval_status"] == "obsidian_only_success"
    assert trace["source_mode"] == "obsidian_only"
    assert trace["retrieval_status"] == "obsidian_only_success"
    assert [
        call.kwargs.get("namespace")
        for call in vector_store.search.call_args_list
    ] == ["obsidian:local"]


@pytest.mark.asyncio
async def test_obsidian_only_retrieval_raises_when_no_obsidian_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeBroker:
        def __init__(self, *args, **kwargs):
            pass

        async def assemble(self, thread_id, query, depth_mode, user_id):
            captured["thread_id"] = thread_id
            captured["query"] = query
            captured["depth_mode"] = depth_mode
            captured["user_id"] = user_id
            return (
                {
                    "messages": [{"role": "user", "content": "Find the note"}],
                    "semantic": [],
                    "memory": [],
                    "docs": {"project": [], "thread": [], "global": []},
                    "obsidian": [],
                    "retrieval_status": "no_obsidian_results",
                },
                {
                    "source_mode": "obsidian_only",
                    "retrieval_status": "no_obsidian_results",
                    "documents": [],
                    "graph": [],
                },
            )

    mock_chatlog_db = MagicMock()
    mock_chatlog_db.get_chat_thread.return_value = {
        "id": 1,
        "user_id": "user-1",
        "project_id": 10,
    }
    mock_chatlog_db.list_messages.return_value = [
        {"id": 1, "role": "user", "content": "Find the note"}
    ]

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

    task = ChatCompletionTask(
        thread_id=1,
        provider="local",
        model=None,
        origin="api:chat.complete|turn_id=abc|source_mode=obsidian_only",
    )

    with pytest.raises(
        ValueError, match="Obsidian-only retrieval returned no results"
    ):
        await chat_completion_service.build_messages_for_llm(task)

    assert captured["thread_id"] == 1
    assert captured["query"] == "Find the note"
    assert captured["depth_mode"] == "normal"
    assert captured["user_id"] == "user-1"
