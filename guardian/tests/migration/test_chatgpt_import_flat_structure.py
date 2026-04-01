"""Regression tests for flat ChatGPT imports with hidden grouping metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

from backend.rag import chatgpt_migration
from backend.rag.chatgpt_migration import ingest_chatgpt_export
from guardian.core import dependencies


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


class InMemoryFlatImportStore:
    def __init__(self) -> None:
        self._next_thread_id = 1
        self._next_message_id = 1
        self.threads: dict[int, dict[str, Any]] = {}
        self.messages: list[dict[str, Any]] = []
        self.ensure_project_calls: list[tuple[str, str]] = []

    def ensure_project(self, name: str, description: str) -> int:
        self.ensure_project_calls.append((name, description))
        return 1 if name == "Imports" else 99

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
            "metadata": metadata or {},
            "parent_id": parent_id,
            "archived_at": None,
        }
        self.threads[thread_id] = thread
        return dict(thread)

    def update_thread_metadata(
        self, thread_id: int, metadata: dict[str, Any]
    ) -> bool:
        thread = self.threads.get(thread_id)
        if not thread:
            return False
        thread["metadata"] = dict(metadata)
        return True

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        thread = self.threads.get(thread_id)
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
        self.messages.append(message)
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
            for message in self.messages
            if int(message.get("thread_id") or 0) == int(thread_id)
        ]
        items.sort(key=lambda item: int(item.get("id") or 0))
        return items[offset : offset + limit]

    def count_messages(self, thread_id: int) -> int:
        return len(
            [
                message
                for message in self.messages
                if int(message.get("thread_id") or 0) == int(thread_id)
            ]
        )

    def write_audit_log(self, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs
        return None


@pytest.fixture
def import_store(monkeypatch):
    store = InMemoryFlatImportStore()
    monkeypatch.setattr(dependencies, "chatlog_db", store)
    monkeypatch.setattr(dependencies, "_vector_store", None)
    monkeypatch.setattr(dependencies, "init_database", lambda: store)
    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBEDDINGS_ENABLED", False)
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
    return store


def test_chatgpt_import_keeps_grouping_flat_and_metadata_hidden(
    import_store,
    monkeypatch,
):
    captured_temporal_meta: list[dict[str, Any]] = []

    def capture_temporal_meta(
        chatlog_db, message_id, merged_meta, source_created_at
    ):
        _ = chatlog_db, message_id, source_created_at
        captured_temporal_meta.append(dict(merged_meta))

    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        capture_temporal_meta,
    )

    export = _build_mainline_export(
        [("user", "This import stays flat.", 1), ("assistant", "Noted.", 2)],
        thread_id="flat-thread",
        title="Flat Import",
    )
    export[0]["conversation_template_id"] = "g-p-aaaaaaaa11111111"
    export[0]["gizmo_id"] = "gizmo-alpha"
    export[0]["gizmo_type"] = "assistants"

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    assert stats["projects_created"] == 0
    assert stats["projects_reused"] == 0
    assert import_store.ensure_project_calls == [
        ("Imports", "Default bucket for imported threads")
    ]

    thread = import_store.threads[1]
    assert thread["project_id"] == 1
    assert thread["metadata"]["import_source"] == "chatgpt"
    assert (
        thread["metadata"]["source_conversation_template_id"]
        == "g-p-aaaaaaaa11111111"
    )
    assert thread["metadata"]["source_gizmo_id"] == "gizmo-alpha"
    assert thread["metadata"]["source_gizmo_type"] == "assistants"

    assert captured_temporal_meta
    assert (
        captured_temporal_meta[0]["source_conversation_template_id"]
        == "g-p-aaaaaaaa11111111"
    )
    assert captured_temporal_meta[0]["source_gizmo_id"] == "gizmo-alpha"
    assert captured_temporal_meta[0]["source_gizmo_type"] == "assistants"
    assert captured_temporal_meta[0]["source_thread_id"] == "flat-thread"
