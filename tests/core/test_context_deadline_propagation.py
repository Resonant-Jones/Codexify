from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from guardian.context.broker import ContextBroker
from guardian.context.retrieval_router_policy import SOURCE_MODE_PROJECT
from guardian.core import chat_completion_service as service
from guardian.memoryos.retriever import MemoryOSRetriever
from guardian.tasks.chat_deadline import AcceptedChatTaskDeadlineExceeded
from guardian.tasks.types import ChatCompletionTask
from tests.core.test_chat_completion_service_source_mode_fallback import (
    _seed_completion_service,
)


def broker():
    return ContextBroker(SimpleNamespace(), None, settings=SimpleNamespace())


@pytest.mark.asyncio
async def test_primary_search_deadline_is_not_optional_or_widened():
    instance = broker()
    error = AcceptedChatTaskDeadlineExceeded()
    search = AsyncMock(side_effect=error)
    with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
        await instance._search_with_widening(
            query="test", k=2, thread_id=1, user_id="owner",
            project_id=None, source_mode=SOURCE_MODE_PROJECT, search_fn=search,
        )
    assert caught.value is error
    assert search.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("surface", ["history", "semantic", "documents", "personal_facts", "memory"])
async def test_broker_does_not_continue_assembly_after_parent_expiry(monkeypatch, surface):
    instance = broker()
    instance.memory = SimpleNamespace()
    monkeypatch.setattr(instance, "_resolve_project_id", AsyncMock(return_value=None))
    monkeypatch.setattr(instance, "_fetch_messages", AsyncMock(return_value=[]))
    monkeypatch.setattr(instance, "_search_semantic", AsyncMock(return_value=[]))
    monkeypatch.setattr(instance, "get_scoped_documents", AsyncMock(return_value={}))
    monkeypatch.setattr(instance, "_fetch_verified_personal_facts", AsyncMock(return_value=([], {})))
    monkeypatch.setattr(instance, "_search_memory", AsyncMock(return_value=([], {})))
    monkeypatch.setattr(instance, "_obsidian_retrieval_enabled", lambda: False)
    names = {
        "history": "_fetch_messages", "semantic": "_search_semantic",
        "documents": "get_scoped_documents", "personal_facts": "_fetch_verified_personal_facts",
        "memory": "_search_memory",
    }
    error = AcceptedChatTaskDeadlineExceeded()
    failing = AsyncMock(side_effect=error)
    monkeypatch.setattr(instance, names[surface], failing)
    with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
        await instance.assemble(1, "test", user_id="owner", depth_mode="deep")
    assert caught.value is error
    assert failing.await_count == 1


@pytest.mark.asyncio
async def test_memory_deadline_never_starts_legacy_fallback():
    instance = broker()
    error = AcceptedChatTaskDeadlineExceeded()
    instance.memory_retriever = SimpleNamespace(retrieve_with_trace=AsyncMock(side_effect=error))
    legacy = Mock()
    instance.memory = SimpleNamespace(search_related=legacy)
    with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
        await instance._search_memory("test", 2, user_id="owner")
    assert caught.value is error
    legacy.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("deadline", [True, False])
async def test_retriever_distinguishes_deadline_from_optional_failure(deadline):
    error = AcceptedChatTaskDeadlineExceeded() if deadline else RuntimeError("optional")
    search = Mock(side_effect=error)
    instance = MemoryOSRetriever(SimpleNamespace(search=search))
    if deadline:
        with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
            await instance.retrieve_with_trace("test", user_id="owner")
        assert caught.value is error
    else:
        results, trace = await instance.retrieve_with_trace("test", user_id="owner")
        assert results == [] and trace["status"] == "failed"
    assert search.call_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("deadline", [True, False])
async def test_shared_builder_preserves_deadline_and_optional_context_policy(monkeypatch, deadline):
    _seed_completion_service(monkeypatch)
    error = AcceptedChatTaskDeadlineExceeded() if deadline else RuntimeError("optional")
    monkeypatch.setattr(service.ContextBroker, "assemble", AsyncMock(side_effect=error))
    task = ChatCompletionTask(user_id="local", thread_id=1, provider="local", model=None)
    if deadline:
        with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
            await service.build_messages_for_llm(task)
        assert caught.value is error
    else:
        result = await service.build_messages_for_llm(task)
        assert result[0]


def test_context_deadline_reaches_completion_caller_before_provider(monkeypatch):
    _seed_completion_service(monkeypatch)
    error = AcceptedChatTaskDeadlineExceeded()
    monkeypatch.setattr(service.ContextBroker, "assemble", AsyncMock(side_effect=error))
    execute = Mock(side_effect=AssertionError("Provider reached after context expiry"))
    monkeypatch.setattr(service, "_execute_completion_attempt", execute)
    task = ChatCompletionTask(user_id="local", thread_id=1, provider="local", model=None)
    with pytest.raises(AcceptedChatTaskDeadlineExceeded) as caught:
        service.run_chat_completion_task(task)
    assert caught.value is error
    execute.assert_not_called()
