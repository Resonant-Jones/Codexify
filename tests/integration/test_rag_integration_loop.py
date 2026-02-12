"""Integration test for deterministic queue-backed RAG memory loop execution."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from guardian.core import dependencies
from guardian.queue import task_events
from guardian.queue import redis_queue
from guardian.queue.redis_queue import dequeue, dequeue_chat_embed
from guardian.routes import chat as chat_routes
from guardian.tasks.types import ChatCompletionTask, task_from_dict
from guardian.vector.store import VectorStore
from guardian.workers import chat_embedding_worker, chat_worker

CHAT_QUEUE_NAME = "codexify:queue:chat"


class StubChatLog:
    """In-memory chatlog stub used by the route and worker path."""

    def __init__(self, thread_id: int = 1) -> None:
        self.thread = {
            "id": thread_id,
            "user_id": "test_user",
            "title": "Deterministic RAG Thread",
            "summary": "",
            "project_id": None,
            "parent_id": None,
            "archived_at": None,
        }
        self._messages: list[dict[str, Any]] = []
        self._next_id = 1

    def ensure_chat_thread(
        self,
        *,
        thread_id: int,
        user_id: str,
        title: str,
        summary: str,
        project_id: int | None = None,
    ) -> dict[str, Any]:
        if thread_id != self.thread["id"]:
            self.thread = {
                **self.thread,
                "id": thread_id,
                "user_id": user_id,
                "title": title,
                "summary": summary,
                "project_id": project_id,
            }
        return dict(self.thread)

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        if thread_id != self.thread["id"]:
            return None
        return dict(self.thread)

    def create_message(self, thread_id: int, role: str, content: str) -> int:
        message_id = self._next_id
        self._next_id += 1
        self._messages.append(
            {
                "id": message_id,
                "thread_id": thread_id,
                "role": role,
                "content": content,
            }
        )
        return message_id

    def list_messages(
        self,
        thread_id: int,
        limit: int = 50,
        offset: int = 0,
        exclude_kinds: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        _ = exclude_kinds
        messages = [
            message
            for message in self._messages
            if message.get("thread_id") == thread_id
        ]
        messages.sort(key=lambda item: int(item.get("id") or 0))
        return messages[offset : offset + limit]

    def count_messages(self, thread_id: int) -> int:
        return len(
            [
                message
                for message in self._messages
                if message.get("thread_id") == thread_id
            ]
        )

    def update_thread(self, thread_id: int, **updates: Any) -> dict[str, Any]:
        if thread_id != self.thread["id"]:
            return {}
        for key, value in updates.items():
            if value is not None and key != "project_id_set":
                self.thread[key] = value
        return dict(self.thread)

    def write_audit_log(self, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs
        return None


def _drain_chat_queue() -> None:
    while dequeue(CHAT_QUEUE_NAME, block=False):
        pass


def _drain_chat_embed_queue() -> None:
    while dequeue_chat_embed(block=False):
        pass


async def _wait_for_terminal_event(
    task_id: str, timeout_seconds: float = 3.0
) -> list[dict[str, Any]]:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last_id = "0"
    events: list[dict[str, Any]] = []

    while asyncio.get_running_loop().time() < deadline:
        batch = task_events.read_events(
            task_id, last_id, count=100, block_ms=5
        )
        if batch:
            for event_id, event in batch:
                last_id = event_id
                events.append(event)

            event_types = {str(event.get("type")) for event in events}
            if "task.completed" in event_types or "task.failed" in event_types:
                return events
        await asyncio.sleep(0.01)

    return events


@pytest.mark.asyncio
async def test_rag_integration_memory_loop(monkeypatch):
    """POST message -> embed queue -> completion queue -> worker completion -> retrieval output."""
    monkeypatch.setenv("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
    monkeypatch.setenv("CODEXIFY_VECTOR_STORE", "faiss")

    memory_text = "Remember: the Orion window is 2026-01-20."
    observed: dict[str, Any] = {}
    chatlog = StubChatLog(thread_id=1)
    vector_store = VectorStore()
    memory_store = object()

    def fake_stream_local(messages: list[dict[str, str]], _model: str):
        system_text = "\n".join(
            str(message.get("content") or "")
            for message in messages
            if message.get("role") == "system"
        )
        has_memory_context = (
            "**Memory Context:**" in system_text and memory_text in system_text
        )
        observed["system_text"] = system_text
        observed["has_memory_context"] = has_memory_context

        output = (
            f"RAG memory confirmed: {memory_text}"
            if has_memory_context
            else "RAG memory missing."
        )
        for token in output.split():
            yield token + " "

    monkeypatch.setattr(dependencies, "chatlog_db", chatlog)
    monkeypatch.setattr(dependencies, "_vector_store", vector_store)
    monkeypatch.setattr(dependencies, "_memory_store", memory_store)
    monkeypatch.setattr(dependencies, "_sensors", None)
    monkeypatch.setattr(chat_routes, "chatlog_db", chatlog)
    monkeypatch.setattr(chat_routes, "_vector_store", vector_store)
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", chatlog)
    monkeypatch.setattr(chat_worker.dependencies, "_vector_store", vector_store)
    monkeypatch.setattr(chat_worker.dependencies, "_memory_store", memory_store)
    monkeypatch.setattr(chat_worker.dependencies, "_sensors", None)
    monkeypatch.setattr(
        chat_routes.event_bus, "emit_event", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(chat_worker, "stream_local", fake_stream_local)
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(redis_queue, "_CLIENT", None)

    chat_routes._thread_latest_task.clear()
    _drain_chat_queue()
    _drain_chat_embed_queue()

    try:
        posted = chat_routes.chat_post_message(
            thread_id=1,
            body={
                "role": "user",
                "content": memory_text,
                "user_id": "test_user",
            },
            api_key="test",
        )
        assert posted["ok"] is True

        embed_payload = dequeue_chat_embed(block=False)
        assert isinstance(embed_payload, dict)
        assert embed_payload.get("content") == memory_text
        assert (
            chat_embedding_worker.process_chat_embed_task(
                embed_payload, vector_store=vector_store
            )
            is True
        )
        assert dequeue_chat_embed(block=False) is None

        completion = await chat_routes.chat_complete(
            1,
            chat_routes.ChatCompletionRequest(
                provider="local",
                model="test-local-model",
                depth_mode="deep",
            ),
            api_key="test",
        )
        assert isinstance(completion, dict)
        task_id = completion.get("task_id")
        assert isinstance(task_id, str)
        assert task_id.strip()

        queued_payload = dequeue(CHAT_QUEUE_NAME, block=False)
        assert isinstance(queued_payload, dict)
        assert queued_payload.get("task_id") == task_id

        task = task_from_dict(queued_payload)
        assert isinstance(task, ChatCompletionTask)

        await asyncio.to_thread(chat_worker._run_chat_task, task)
        assert dequeue(CHAT_QUEUE_NAME, block=False) is None

        events = await _wait_for_terminal_event(task_id)
        event_types = [str(event.get("type")) for event in events]
        assert "task.running" in event_types
        assert "task.completed" in event_types
        assert "task.failed" not in event_types

        messages = chatlog.list_messages(1, limit=50, offset=0)
        assistant_messages = [
            message for message in messages if message.get("role") == "assistant"
        ]
        assert assistant_messages
        assistant_text = str(assistant_messages[-1].get("content") or "")
        assert memory_text in assistant_text
        assert observed.get("has_memory_context") is True
    finally:
        _drain_chat_queue()
        _drain_chat_embed_queue()
