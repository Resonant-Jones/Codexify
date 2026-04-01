"""Regression tests for ChatGPT import personal-fact extraction."""

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


class InMemoryImportStore:
    def __init__(self) -> None:
        self._next_thread_id = 1
        self._next_message_id = 1
        self._next_fact_id = 1
        self._next_evidence_id = 1
        self.threads: dict[int, dict[str, Any]] = {}
        self.messages: list[dict[str, Any]] = []
        self.facts: dict[int, dict[str, Any]] = {}
        self.evidence: list[dict[str, Any]] = []

    @property
    def latest_thread_id(self) -> int | None:
        if not self.threads:
            return None
        return max(self.threads)

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
            "metadata": metadata or {},
            "parent_id": parent_id,
            "archived_at": None,
        }
        self.threads[thread_id] = thread
        return dict(thread)

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        thread = self.threads.get(thread_id)
        return dict(thread) if thread else None

    def update_thread_metadata(
        self, thread_id: int, metadata: dict[str, Any]
    ) -> bool:
        thread = self.threads.get(thread_id)
        if not thread:
            return False
        thread["metadata"] = dict(metadata)
        return True

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
        rows = [
            dict(message)
            for message in self.messages
            if int(message.get("thread_id") or 0) == int(thread_id)
        ]
        rows.sort(key=lambda row: int(row.get("id") or 0))
        return rows[offset : offset + limit]

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

    def list_facts(
        self,
        user_id: str,
        status: str | None = None,
        active_only: bool = True,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        rows = [
            dict(fact)
            for fact in self.facts.values()
            if str(fact.get("user_id") or "") == user_id
        ]
        if status is not None:
            rows = [fact for fact in rows if fact.get("status") == status]
        if active_only:
            rows = [fact for fact in rows if fact.get("is_active")]
        rows.sort(key=lambda fact: fact.get("updated_at"), reverse=True)
        return rows[:limit]

    def create_fact(
        self,
        user_id: str,
        key: str,
        value: str,
        status: str = "candidate",
        confidence: float = 0.5,
    ) -> int:
        existing = next(
            (
                fact
                for fact in self.facts.values()
                if fact["user_id"] == user_id
                and fact["key"] == key
                and fact["is_active"]
            ),
            None,
        )
        if existing is not None:
            raise ValueError("duplicate active fact")

        fact_id = self._next_fact_id
        self._next_fact_id += 1
        now = datetime.now(timezone.utc)
        fact = {
            "id": fact_id,
            "user_id": user_id,
            "key": key,
            "value": value,
            "status": status,
            "confidence": confidence,
            "is_active": True,
            "last_confirmed_at": None,
            "created_at": now,
            "updated_at": now,
        }
        self.facts[fact_id] = fact
        return fact_id

    def get_fact(self, fact_id: int) -> dict[str, Any] | None:
        fact = self.facts.get(fact_id)
        return dict(fact) if fact else None

    def update_fact(
        self,
        fact_id: int,
        *,
        value: str | None = None,
        status: str | None = None,
        confidence: float | None = None,
        actor: str = "system",
        reason: str | None = None,
    ) -> dict[str, Any]:
        _ = actor, reason
        fact = self.facts[fact_id]
        if value is not None:
            fact["value"] = value
        if status is not None:
            fact["status"] = status
        if confidence is not None:
            fact["confidence"] = confidence
        if status == "verified":
            fact["last_confirmed_at"] = datetime.now(timezone.utc)
        fact["updated_at"] = datetime.now(timezone.utc)
        return dict(fact)

    def list_fact_evidence(self, fact_id: int) -> list[dict[str, Any]]:
        rows = [
            dict(evidence)
            for evidence in self.evidence
            if int(evidence.get("fact_id") or 0) == int(fact_id)
        ]
        rows.sort(key=lambda row: row.get("created_at"))
        return rows

    def add_fact_evidence(
        self,
        fact_id: int,
        source_message_id: int | None,
        excerpt: str | None,
        *,
        modality: str = "text",
        confidence: float = 0.5,
        source_type: str = "runtime_extraction",
        evidence_meta: dict | None = None,
    ) -> int:
        evidence_id = self._next_evidence_id
        self._next_evidence_id += 1
        evidence = {
            "id": evidence_id,
            "fact_id": fact_id,
            "source_message_id": source_message_id,
            "excerpt": excerpt,
            "modality": modality,
            "confidence": confidence,
            "source_type": source_type,
            "evidence_meta": evidence_meta or {},
            "created_at": datetime.now(timezone.utc),
        }
        self.evidence.append(evidence)
        return evidence_id


@pytest.fixture
def import_store(monkeypatch):
    store = InMemoryImportStore()
    original_create_chat_thread = store.create_chat_thread
    original_create_message = store.create_message
    monkeypatch.setattr(dependencies, "chatlog_db", store)
    monkeypatch.setattr(dependencies, "_vector_store", None)
    monkeypatch.setattr(dependencies, "init_database", lambda: store)
    monkeypatch.setattr(chatgpt_migration, "_IMPORT_EMBEDDINGS_ENABLED", False)
    monkeypatch.setattr(
        chatgpt_migration,
        "_persist_temporal_metadata",
        lambda *args, **kwargs: None,
    )

    thread_to_id: dict[str, int] = {}
    message_to_id: dict[tuple[int, str], int] = {}
    last_source_thread = {"value": ""}
    last_source_message = {"value": ""}

    def fake_find_thread(_chatlog_db, *, user_id, source_thread_id):
        _ = user_id
        last_source_thread["value"] = source_thread_id
        return thread_to_id.get(source_thread_id)

    def fake_find_message(_chatlog_db, *, thread_id, source_message_id):
        last_source_message["value"] = source_message_id
        mid = message_to_id.get((thread_id, source_message_id))
        if mid is None:
            return None
        return {
            "id": mid,
            "extra_meta": {"source_message_id": source_message_id},
        }

    def fake_create_thread(**kwargs):
        thread = original_create_chat_thread(**kwargs)
        thread_to_id[last_source_thread["value"]] = int(thread["id"])
        return thread

    def fake_create_message(thread_id, role, content, created_at=None):
        message_id = original_create_message(
            thread_id, role, content, created_at=created_at
        )
        message_to_id[(thread_id, last_source_message["value"])] = message_id
        return message_id

    monkeypatch.setattr(
        chatgpt_migration, "_find_existing_thread_for_source", fake_find_thread
    )
    monkeypatch.setattr(
        chatgpt_migration,
        "_find_existing_message_for_source",
        fake_find_message,
    )
    monkeypatch.setattr(store, "create_chat_thread", fake_create_thread)
    monkeypatch.setattr(store, "create_message", fake_create_message)
    return store


def test_ingest_chatgpt_export_creates_personal_fact_review_candidates(
    import_store,
):
    export = _build_mainline_export(
        [
            ("user", "I live in Boston and I prefer tea.", 1),
            ("assistant", "Noted.", 2),
            ("user", "My name is Sam.", 3),
        ],
        thread_id="chat-thread-1",
        title="Profile import",
    )

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 3

    facts = import_store.list_facts("tester", active_only=True)
    assert len(facts) == 3
    assert {fact["status"] for fact in facts} == {"candidate"}
    assert {fact["key"] for fact in facts} == {
        "location",
        "preference",
        "name",
    }

    evidence_by_fact_key = {
        next(
            fact["key"] for fact in facts if fact["id"] == evidence["fact_id"]
        ): evidence
        for evidence in import_store.evidence
    }

    location_evidence = evidence_by_fact_key["location"]
    assert location_evidence["source_type"] == "chatgpt_import"
    assert location_evidence["source_message_id"] == 1
    assert (
        location_evidence["evidence_meta"]["import_source"] == "chatgpt_import"
    )
    assert (
        location_evidence["evidence_meta"]["source_thread_id"]
        == "chat-thread-1"
    )
    assert (
        location_evidence["evidence_meta"]["source_message_export_id"] == "m1"
    )

    name_evidence = evidence_by_fact_key["name"]
    assert name_evidence["source_message_id"] == 3
    assert name_evidence["evidence_meta"]["source_message_export_id"] == "m3"


def test_ingest_chatgpt_export_is_idempotent_for_personal_fact_candidates(
    import_store,
):
    export = _build_mainline_export(
        [("user", "I live in Boston. I prefer tea.", 1)],
        thread_id="repeat-thread",
        title="Repeat import",
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
    assert stats_first["messages_imported"] == 1
    assert stats_second["threads_imported"] == 0
    assert stats_second["messages_imported"] == 0

    facts = import_store.list_facts("tester", active_only=True)
    assert len(facts) == 2
    assert {fact["key"] for fact in facts} == {"location", "preference"}
    assert len(import_store.evidence) == 2


def test_ingest_chatgpt_export_without_fact_candidates_succeeds(import_store):
    export = _build_mainline_export(
        [
            ("user", "Hello there.", 1),
            ("assistant", "General Kenobi.", 2),
        ],
        thread_id="no-facts-thread",
        title="No facts",
    )

    stats = ingest_chatgpt_export(
        json.dumps(export).encode("utf-8"),
        user_id="tester",
    )

    assert stats["threads_imported"] == 1
    assert stats["messages_imported"] == 2
    assert import_store.list_facts("tester", active_only=True) == []
    assert import_store.evidence == []
