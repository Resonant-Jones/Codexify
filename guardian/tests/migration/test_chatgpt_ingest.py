import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.rag import chatgpt_migration
from backend.rag.chatgpt_migration import ingest_chatgpt_export
from guardian.core import dependencies
from guardian.queue.redis_queue import dequeue_chat_import_embed
from guardian.tasks.types import ChatCompletionTask
from guardian.workers import chat_embedding_worker, chat_worker


def _build_mainline_export(
    turns: list[tuple[str, str, float]],
    *,
    thread_id: str = "t1",
    title: str = "Test Conversation",
) -> list[dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    parent: str | None = None
    for idx, (role, text, create_time) in enumerate(turns, start=1):
        node_id = f"m{idx}"
        mapping[node_id] = {
            "id": node_id,
            "parent": parent,
            "children": [],
            "message": {
                "author": {"role": role},
                "content": {"parts": [text]},
                "create_time": create_time,
            },
        }
        if parent:
            mapping[parent]["children"].append(node_id)
        parent = node_id
    return [
        {
            "id": thread_id,
            "title": title,
            "current_node": parent,
            "mapping": mapping,
        }
    ]


class DeterministicVectorStore:
    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []
        self.batch_sizes: list[int] = []

    def add_texts(self, items: list[dict[str, Any]]) -> int:
        self.batch_sizes.append(len(items))
        for item in items:
            text = str(item.get("text") or "")
            meta = dict(item.get("meta") or {})
            self._items.append({"text": text, "meta": meta})
        return len(items)

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        query_terms = {
            part.strip().lower() for part in query.split() if part.strip()
        }

        def _score(text: str) -> float:
            lowered = text.lower()
            if not query_terms:
                return 0.0
            overlap = sum(1 for token in query_terms if token in lowered)
            # Keep deterministic ranking: prioritize overlap, then recency.
            return float(overlap)

        scored: list[tuple[float, int, dict[str, Any]]] = []
        for idx, item in enumerate(self._items):
            score = _score(str(item.get("text") or ""))
            scored.append((score, idx, item))

        ranked = sorted(scored, key=lambda x: (x[0], x[1]), reverse=True)
        hits: list[dict[str, Any]] = []
        for score, _idx, item in ranked[: max(int(k), 0)]:
            meta = dict(item.get("meta") or {})
            hits.append(
                {
                    "text": item.get("text", ""),
                    "meta": meta,
                    "metadata": meta,
                    "score": score,
                }
            )
        return hits


def _drain_chat_import_embed_queue() -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    while True:
        payload = dequeue_chat_import_embed(block=False)
        if not payload:
            break
        payloads.append(payload)
    return payloads


class InMemoryChatlog:
    def __init__(self) -> None:
        self._next_thread_id = 1
        self._next_message_id = 1
        self._threads: dict[int, dict[str, Any]] = {}
        self._messages: list[dict[str, Any]] = []

    @property
    def latest_thread_id(self) -> int | None:
        if not self._threads:
            return None
        return max(self._threads)

    def ensure_project(self, _name: str, _description: str) -> int:
        return 1

    def list_projects(self) -> list[dict[str, Any]]:
        return [{"id": 1, "name": "Imports"}]

    def create_chat_thread(
        self,
        *,
        user_id: str,
        title: str,
        summary: str = "",
        project_id: int | None = None,
        metadata: dict[str, Any] | None = None,
        parent_id: int | None = None,
    ) -> dict[str, Any]:
        thread_id = self._next_thread_id
        self._next_thread_id += 1
        thread = {
            "id": thread_id,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "metadata": metadata,
            "parent_id": parent_id,
            "archived_at": None,
        }
        self._threads[thread_id] = thread
        return dict(thread)

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        thread = self._threads.get(thread_id)
        return dict(thread) if thread else None

    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        created_at: str | None = None,
    ) -> int:
        message_id = self._next_message_id
        self._next_message_id += 1
        message = {
            "id": message_id,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "created_at": created_at or datetime.now(timezone.utc).isoformat(),
        }
        self._messages.append(message)
        return message_id

    def list_messages(
        self,
        thread_id: int,
        limit: int = 50,
        offset: int = 0,
        exclude_kinds: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        _ = exclude_kinds
        items = [
            dict(message)
            for message in self._messages
            if int(message.get("thread_id") or 0) == int(thread_id)
        ]
        items.sort(key=lambda m: int(m.get("id") or 0))
        return items[offset : offset + limit]

    def count_messages(self, thread_id: int) -> int:
        return len(
            [
                message
                for message in self._messages
                if int(message.get("thread_id") or 0) == int(thread_id)
            ]
        )

    def write_audit_log(self, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs
        return None


def test_ingest_chatgpt_export_creates_threads_and_messages(monkeypatch):
    """Integration-style check that ingest_chatgpt_export processes a minimal export."""
    mock_db = MagicMock()
    mock_db.create_chat_thread.return_value = {"id": 42}
    message_ids = iter([1, 2])

    def fake_create_message(thread_id, role, content):
        return next(message_ids)

    mock_db.create_message.side_effect = fake_create_message

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    export = _build_mainline_export(
        [
            ("user", "Hello", 1),
            ("assistant", "Hi there", 2),
        ]
    )

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"), user_id="tester"
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    mock_db.create_chat_thread.assert_called_once()
    # ensure messages persisted with correct thread id
    mock_db.create_message.assert_any_call(42, "user", "Hello")
    mock_db.create_message.assert_any_call(42, "assistant", "Hi there")


def test_ingest_rejects_shared_conversations_metadata(monkeypatch):
    mock_db = MagicMock()
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)

    metadata_only = [
        {
            "id": "meta_1",
            "conversation_id": "conversation_1",
            "title": "Shared thread",
            "is_anonymous": False,
        }
    ]

    with pytest.raises(ValueError, match="shared_conversations"):
        ingest_chatgpt_export(
            json.dumps(metadata_only).encode("utf-8"), user_id="tester"
        )


def test_ingest_rejects_html_payload(monkeypatch):
    mock_db = MagicMock()
    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)

    with pytest.raises(ValueError, match="appears to be HTML"):
        ingest_chatgpt_export(
            b"<html><body>archive</body></html>", user_id="tester"
        )


def test_ingest_tags_imported_messages_with_origin_and_era(monkeypatch):
    mock_db = MagicMock()
    mock_db.create_chat_thread.return_value = {"id": 42}
    mock_db.create_message.return_value = 1

    captured_meta = []

    def capture_temporal_meta(
        chatlog_db, message_id, merged_meta, source_created_at
    ):
        captured_meta.append(dict(merged_meta))

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        capture_temporal_meta,
    )

    export = _build_mainline_export(
        [("user", "Hello", 1)],
        title="Archival Import",
    )

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"), user_id="tester"
    )

    assert stats["messages_imported"] == 1
    assert captured_meta
    assert captured_meta[0]["origin"] == "chatgpt_import"
    assert captured_meta[0]["era"] == "pre_codexify"


def test_imported_fact_is_recalled_in_post_import_completion(monkeypatch):
    imported_fact = "Migration recall anchor ORCHID-POLARIS-719."
    recall_prompt = "What is the migration recall anchor?"
    export = _build_mainline_export(
        [
            ("user", imported_fact, 1),
            ("assistant", "Acknowledged.", 2),
        ],
        title="Recall Fixture",
    )

    chatlog = InMemoryChatlog()
    vector_store = DeterministicVectorStore()
    memory_store = object()
    observed: dict[str, Any] = {}

    def fake_stream_local(
        messages: list[dict[str, str]], _model: str, **_kwargs
    ):
        system_text = "\n".join(
            str(message.get("content") or "")
            for message in messages
            if message.get("role") == "system"
        )
        has_memory_context = (
            "**Memory Context:**" in system_text
            and imported_fact in system_text
        )
        observed["system_text"] = system_text
        observed["has_memory_context"] = has_memory_context
        output = (
            f"Imported fact recalled: {imported_fact}"
            if has_memory_context
            else "Imported memory context missing."
        )
        for token in output.split():
            yield token + " "

    monkeypatch.setattr(dependencies, "chatlog_db", chatlog)
    monkeypatch.setattr(dependencies, "_vector_store", vector_store)
    monkeypatch.setattr(dependencies, "_memory_store", memory_store)
    monkeypatch.setattr(dependencies, "_sensors", None)
    monkeypatch.setattr(dependencies, "init_database", lambda: chatlog)

    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", chatlog)
    monkeypatch.setattr(chat_worker.dependencies, "_vector_store", vector_store)
    monkeypatch.setattr(chat_worker.dependencies, "_memory_store", memory_store)
    monkeypatch.setattr(chat_worker.dependencies, "_sensors", None)
    monkeypatch.setattr(chat_worker, "stream_local", fake_stream_local)
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "clear_cancelled", lambda *_args: None)
    monkeypatch.setattr(
        chat_worker.event_bus, "emit_event", lambda *_args, **_kwargs: None
    )
    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )
    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2

    imported_payloads = _drain_chat_import_embed_queue()
    assert imported_payloads
    for payload in imported_payloads:
        payload = dict(payload)
        payload.pop("message_id", None)
        assert (
            chat_embedding_worker.process_chat_embed_task(
                payload,
                vector_store=vector_store,
            )
            is True
        )

    thread_id = chatlog.latest_thread_id
    assert thread_id is not None
    chatlog.create_message(thread_id, "user", recall_prompt)

    task = ChatCompletionTask(
        thread_id=thread_id,
        provider="local",
        model="test-local-model",
        depth_mode="deep",
        origin="test:migration.import_recall",
    )
    chat_worker._run_chat_task(task)

    messages = chatlog.list_messages(thread_id, limit=50, offset=0)
    assistant_messages = [
        message for message in messages if message.get("role") == "assistant"
    ]
    assert assistant_messages
    assistant_text = str(assistant_messages[-1].get("content") or "")
    assert imported_fact in assistant_text
    assert observed.get("has_memory_context") is True


def test_ingest_with_template_metadata_stays_in_imports_container(monkeypatch):
    mock_db = MagicMock()
    mock_db.list_projects.return_value = [{"id": 1, "name": "Imports"}]

    def ensure_project(name: str, _description: str = "") -> int:
        if name == "Imports":
            return 1
        return 11

    mock_db.ensure_project.side_effect = ensure_project

    thread_ids = iter([101, 102])
    mock_db.create_chat_thread.side_effect = lambda **_: {
        "id": next(thread_ids)
    }
    message_ids = iter([1, 2, 3, 4])
    mock_db.create_message.side_effect = lambda *args, **kwargs: next(
        message_ids
    )

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    export = _build_mainline_export(
        [("user", "One", 1), ("assistant", "A", 2)],
        thread_id="thread-one",
        title="Template Alpha",
    ) + _build_mainline_export(
        [("user", "Two", 3), ("assistant", "B", 4)],
        thread_id="thread-two",
        title="Template Beta",
    )
    export[0]["conversation_template_id"] = "g-p-aaaaaaaa11111111"
    export[1]["conversation_template_id"] = "g-p-aaaaaaaa11111111"
    export[0]["gizmo_id"] = "gizmo-alpha"
    export[0]["gizmo_type"] = "assistants"
    export[1]["gizmo_id"] = "gizmo-alpha"
    export[1]["gizmo_type"] = "assistants"

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 2
    assert stats["messages_imported"] == 4
    assert stats["projects_created"] == 0
    assert stats["projects_reused"] == 0
    mock_db.ensure_project.assert_called_once_with(
        "Imports", "Default bucket for imported threads"
    )

    first_call = mock_db.create_chat_thread.call_args_list[0].kwargs
    second_call = mock_db.create_chat_thread.call_args_list[1].kwargs
    assert first_call["project_id"] == 1
    assert second_call["project_id"] == 1
    assert (
        first_call["metadata"]["source_conversation_template_id"]
        == "g-p-aaaaaaaa11111111"
    )
    assert first_call["metadata"]["source_gizmo_id"] == "gizmo-alpha"
    assert first_call["metadata"]["source_gizmo_type"] == "assistants"


def test_ingest_without_template_falls_back_to_imports(monkeypatch):
    mock_db = MagicMock()
    mock_db.ensure_project.side_effect = lambda name, _description="": (
        1 if name == "Imports" else 99
    )
    mock_db.list_projects.return_value = [{"id": 1, "name": "Imports"}]
    mock_db.create_chat_thread.return_value = {"id": 42}
    mock_db.create_message.return_value = 1

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    export = _build_mainline_export([("user", "Hello imports", 1)])

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 1
    assert stats["projects_created"] == 0
    assert stats["projects_reused"] == 0

    kwargs = mock_db.create_chat_thread.call_args.kwargs
    assert kwargs["project_id"] == 1
    assert kwargs["metadata"]["import_source"] == "chatgpt"
    assert "source_conversation_template_id" not in kwargs["metadata"]


def test_ingest_filters_internal_noise_and_tracks_filtered(monkeypatch):
    mock_db = MagicMock()
    mock_db.ensure_project.return_value = 1
    mock_db.list_projects.return_value = [{"id": 1, "name": "Imports"}]
    mock_db.create_chat_thread.return_value = {"id": 42}
    mock_db.create_message.side_effect = [1, 2]

    captured_meta: list[dict[str, Any]] = []

    def capture_temporal_meta(
        chatlog_db, message_id, merged_meta, source_created_at
    ):
        captured_meta.append(dict(merged_meta))

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        capture_temporal_meta,
    )

    export = [
        {
            "id": "filter-thread",
            "title": "Filter Test",
            "current_node": "m4",
            "mapping": {
                "m1": {
                    "id": "m1",
                    "parent": None,
                    "children": ["m2"],
                    "message": {
                        "author": {"role": "system"},
                        "content": {
                            "content_type": "text",
                            "parts": ["Internal system prompt"],
                        },
                        "create_time": 1,
                    },
                },
                "m2": {
                    "id": "m2",
                    "parent": "m1",
                    "children": ["m3"],
                    "message": {
                        "author": {"role": "user"},
                        "content": {
                            "content_type": "text",
                            "parts": ["Keep this user message"],
                        },
                        "create_time": 2,
                    },
                },
                "m3": {
                    "id": "m3",
                    "parent": "m2",
                    "children": ["m4"],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"content_type": "text", "parts": [""]},
                        "create_time": 3,
                    },
                },
                "m4": {
                    "id": "m4",
                    "parent": "m3",
                    "children": [],
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {
                            "content_type": "text",
                            "parts": ["Canonical assistant reply"],
                        },
                        "create_time": 4,
                    },
                },
            },
        }
    ]

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    assert stats["messages_filtered"] == 2
    assert captured_meta
    assert all(
        meta.get("canonical_filter_profile") == "chatgpt_v1_canonical"
        for meta in captured_meta
    )
    assert all(
        isinstance(meta.get("raw_message"), dict) for meta in captured_meta
    )


def test_ingest_is_idempotent_on_reimport(monkeypatch):
    mock_db = MagicMock()
    mock_db.ensure_project.return_value = 1
    mock_db.list_projects.return_value = [{"id": 1, "name": "Imports"}]

    source_to_thread: dict[str, int] = {}
    source_to_message: dict[tuple[int, str], int] = {}
    last_source_thread = {"value": ""}
    last_source_message = {"value": ""}
    next_thread_id = {"value": 500}
    next_message_id = {"value": 1}

    def fake_find_thread(chatlog_db, user_id, source_thread_id):
        last_source_thread["value"] = source_thread_id
        return source_to_thread.get(source_thread_id)

    def fake_create_thread(**_kwargs):
        thread_id = next_thread_id["value"]
        next_thread_id["value"] += 1
        source_to_thread[last_source_thread["value"]] = thread_id
        return {"id": thread_id}

    def fake_find_message(chatlog_db, thread_id, source_message_id):
        last_source_message["value"] = source_message_id
        mid = source_to_message.get((thread_id, source_message_id))
        if mid is None:
            return None
        return {"id": mid, "extra_meta": {}}

    def fake_create_message(thread_id, role, content, created_at=None):
        _ = role, content, created_at
        mid = next_message_id["value"]
        next_message_id["value"] += 1
        source_to_message[(thread_id, last_source_message["value"])] = mid
        return mid

    mock_db.create_chat_thread.side_effect = fake_create_thread
    mock_db.create_message.side_effect = fake_create_message

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        fake_find_thread,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        fake_find_message,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )

    export = _build_mainline_export(
        [("user", "Hello", 1), ("assistant", "World", 2)],
        thread_id="repeat-thread",
    )

    stats_first = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )
    stats_second = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats_first["threads_imported"] == 1
    assert stats_first["messages_imported"] == 2
    assert stats_second["threads_imported"] == 0
    assert stats_second["messages_imported"] == 0


def test_ingest_marks_graph_pending_without_blocking_completion(monkeypatch):
    mock_db = MagicMock()
    mock_db.ensure_project.return_value = 1
    mock_db.list_projects.return_value = [{"id": 1, "name": "Imports"}]
    mock_db.create_chat_thread.return_value = {"id": 42}
    mock_db.create_message.return_value = 1

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", MagicMock())
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    _drain_chat_import_embed_queue()

    export = _build_mainline_export([("user", "Hello graph", 1)])

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 1
    assert (
        mock_db.create_chat_thread.call_args.kwargs["metadata"]["graph_status"]
        == "pending"
    )


def test_ingest_enqueues_embedding_backlog_without_inline_embedding(
    monkeypatch,
):
    mock_db = MagicMock()
    mock_db.ensure_project.return_value = 1
    mock_db.list_projects.return_value = [{"id": 1, "name": "Imports"}]
    mock_db.create_chat_thread.return_value = {"id": 42}

    message_ids = iter([1, 2, 3, 4, 5])

    def fake_create_message(*_args, **_kwargs):
        return next(message_ids)

    vector_store = MagicMock()
    _drain_chat_import_embed_queue()

    monkeypatch.setattr(dependencies, "chatlog_db", mock_db)
    monkeypatch.setattr(dependencies, "_vector_store", vector_store)
    monkeypatch.setattr(dependencies, "init_database", lambda: mock_db)
    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBED_BATCH_SIZE", 2)
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_thread_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *_args, **_kwargs: None,
    )
    mock_db.create_message.side_effect = fake_create_message

    export = _build_mainline_export(
        [
            ("user", "Alpha", 1),
            ("assistant", "Bravo", 2),
            ("user", "Charlie", 3),
            ("assistant", "Delta", 4),
            ("user", "Echo", 5),
        ],
        thread_id="batch-thread",
    )

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 5
    assert stats["embedding_candidates"] == 5
    assert stats["embeddings_persisted"] == 5
    assert stats["embeddings_failed"] == 0
    assert stats["embedding_coverage_degraded"] is False
    assert vector_store.add_texts.call_count == 0
    assert mock_db.create_message.call_count == 5

    queued_payloads = _drain_chat_import_embed_queue()
    assert len(queued_payloads) == 5
    assert {payload["type"] for payload in queued_payloads} == {
        "chat_import_embed"
    }
    assert all(
        payload["meta"]["embedding_status"] == "pending"
        for payload in queued_payloads
    )


def test_retry_chatgpt_import_embeddings_batches_retry_items(monkeypatch):
    dummy_db = object()
    retry_items = [
        {
            "message_id": 301,
            "text": "Recovered import chunk A",
            "meta": {"message_id": 301, "thread_id": 21},
        },
        {
            "message_id": 302,
            "text": "Recovered import chunk B",
            "meta": {"message_id": 302, "thread_id": 21},
        },
        {
            "message_id": 303,
            "text": "Recovered import chunk C",
            "meta": {"message_id": 303, "thread_id": 21},
        },
        {
            "message_id": 304,
            "text": "Recovered import chunk D",
            "meta": {"message_id": 304, "thread_id": 21},
        },
        {
            "message_id": 305,
            "text": "Recovered import chunk E",
            "meta": {"message_id": 305, "thread_id": 21},
        },
    ]

    _drain_chat_import_embed_queue()
    monkeypatch.setattr(dependencies, "chatlog_db", dummy_db)
    monkeypatch.setattr(dependencies, "init_database", lambda: dummy_db)
    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBED_BATCH_SIZE", 2)
    monkeypatch.setattr(
        chatgpt_migration,
        "_fetch_retryable_chatgpt_embedding_items",
        lambda _db, *, user_id, limit=5000: retry_items
        if user_id == "tester"
        else [],
    )

    stats = chatgpt_migration.retry_chatgpt_import_embeddings(
        user_id="tester",
        limit=5,
    )

    assert stats["embedding_candidates"] == 5
    assert stats["embeddings_persisted"] == 5
    assert stats["embeddings_failed"] == 0
    assert stats["embedding_coverage_degraded"] is False
    queued_payloads = _drain_chat_import_embed_queue()
    assert len(queued_payloads) == 5
    assert {payload["type"] for payload in queued_payloads} == {
        "chat_import_embed"
    }


class _FakeChatMessageRow:
    def __init__(self, message_id: str, content: str) -> None:
        self.id = message_id
        self.thread_id = 7
        self.role = "user"
        self.content = content
        self.extra_meta: dict[str, Any] = {
            "embedding_status": "pending",
            "embedding_error": None,
        }


class _FakeChatQuery:
    def __init__(self, row: _FakeChatMessageRow) -> None:
        self._row = row

    def filter_by(self, **kwargs):
        assert str(kwargs.get("id")) == str(self._row.id)
        return self

    def first(self):
        return self._row


class _FakeChatSession:
    def __init__(self, row: _FakeChatMessageRow) -> None:
        self._row = row
        self.commits = 0

    def query(self, model):
        _ = model
        return _FakeChatQuery(self._row)

    def commit(self) -> None:
        self.commits += 1


class _FakeChatDbContext:
    def __init__(self, row: _FakeChatMessageRow) -> None:
        self._session = _FakeChatSession(row)

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeChatDb:
    def __init__(self, row: _FakeChatMessageRow) -> None:
        self._row = row

    def get_session(self):
        return _FakeChatDbContext(self._row)


class _FailingChatVectorStore:
    def add_texts(self, _items):
        raise RuntimeError("boom")


def test_chat_embedding_worker_marks_failed_without_mutating_content():
    row = _FakeChatMessageRow("m-1", "Preserve me")
    db = _FakeChatDb(row)

    ok = chat_embedding_worker.process_chat_embed_task(
        {
            "thread_id": 7,
            "role": "user",
            "message_id": "m-1",
            "content": "Preserve me",
            "meta": {
                "origin": "chatgpt_import",
                "source": "chatgpt_import",
            },
        },
        vector_store=_FailingChatVectorStore(),
        db=db,
    )

    assert ok is False
    assert row.content == "Preserve me"
    assert row.extra_meta["embedding_status"] == "failed"
    assert row.extra_meta["embedding_error"] == "boom"
    assert row.extra_meta["embedding_started_at"] is not None
    assert row.extra_meta["embedding_completed_at"] is not None
