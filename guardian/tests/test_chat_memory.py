"""Tests for chat message CRUD, pagination, and turn-lock enforcement."""

import os

import pytest
from fastapi.testclient import TestClient

from guardian.config import get_settings
from guardian.guardian_api import app


def _pick_test_api_key(settings) -> str | None:
    # Prefer explicit single-key configs
    for name in ("GUARDIAN_API_KEY", "API_KEY", "X_API_KEY"):
        val = getattr(settings, name, None) or os.getenv(name)
        if isinstance(val, str) and val.strip():
            return val.strip()

    # Fall back to multi-key configs
    for name in ("GUARDIAN_API_KEYS", "API_KEYS"):
        val = getattr(settings, name, None) or os.getenv(name)
        if isinstance(val, (list, tuple)) and val:
            first = str(val[0]).strip()
            return first or None
        if isinstance(val, str) and val.strip():
            first = val.split(",")[0].strip()
            return first or None

    return None


_settings = get_settings()
_api_key = _pick_test_api_key(_settings)
if not _api_key:
    # Avoid a wall of 401s when auth is enabled but tests are misconfigured.
    pytest.skip(
        "No API key configured for tests (GUARDIAN_API_KEY / GUARDIAN_API_KEYS)"
    )

client = TestClient(app, headers={"X-API-Key": _api_key})


def test_chat_crud():
    # Create message
    r = client.post(
        "/api/chat/1/messages", json={"role": "user", "content": "hello"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    mid = data.get("message", {}).get("id")
    assert isinstance(mid, int)

    # List messages
    r = client.get("/api/chat/1/messages", params={"limit": 50, "offset": 0})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("total") >= 1
    assert any(m.get("id") == mid for m in data.get("messages", []))

    # Delete message
    r = client.delete(f"/api/chat/1/messages/{mid}")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_chat_post_empty_400():
    r = client.post(
        "/api/chat/2/messages", json={"role": "user", "content": ""}
    )
    assert r.status_code == 400
    assert r.json().get("ok") is False


def test_chat_turn_lock_rejects(monkeypatch):
    from guardian.routes import chat as chat_routes

    def fake_acquire_turn_lock(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(
        chat_routes, "acquire_turn_lock", fake_acquire_turn_lock
    )
    r = client.post(
        "/api/chat/555/messages", json={"role": "user", "content": "hi"}
    )
    assert r.status_code == 429
    assert r.json().get("error") == "turn_in_flight"


def test_chat_message_turn_lock_owner_contract(monkeypatch):
    from guardian.routes import chat as chat_routes

    class _StubChatlogDB:
        def __init__(self) -> None:
            self._thread: dict[str, object] = {"id": 556, "title": ""}

        def ensure_chat_thread(self, **_kwargs) -> None:
            return None

        def create_message(
            self, thread_id: int, role: str, content: str
        ) -> int:
            _ = (thread_id, role, content)
            return 9001

        def write_audit_log(self, *_args, **_kwargs) -> None:
            return None

        def get_chat_thread(self, thread_id: int):
            self._thread["id"] = thread_id
            return self._thread

        def count_messages(self, _thread_id: int) -> int:
            return 1

        def update_thread(self, _thread_id: int, **_kwargs) -> None:
            return None

    calls: dict[str, tuple[object, ...]] = {}

    def fake_acquire_turn_lock(
        thread_id: int, owner: str, *, ttl_seconds: int | None = None
    ) -> bool:
        calls["acquire"] = (thread_id, owner, ttl_seconds)
        return True

    def fake_release_turn_lock(thread_id: int, owner: str) -> bool:
        calls["release"] = (thread_id, owner)
        return True

    monkeypatch.setattr(
        chat_routes, "acquire_turn_lock", fake_acquire_turn_lock
    )
    monkeypatch.setattr(
        chat_routes, "release_turn_lock", fake_release_turn_lock
    )
    monkeypatch.setattr(chat_routes, "chatlog_db", _StubChatlogDB())
    monkeypatch.setattr(
        chat_routes.event_bus, "emit_event", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        chat_routes, "_emit_thread_update_event", lambda **_kwargs: None
    )
    monkeypatch.setattr(chat_routes, "_embed_message", lambda *_a, **_k: None)

    thread_id = 556
    message = chat_routes._persist_message_to_thread(
        thread_id=thread_id,
        role="user",
        content="hi",
        owner="default",
    )
    assert message["id"] == 9001
    assert calls["acquire"][0] == thread_id
    assert calls["acquire"][1] == calls["release"][1]


def test_route_message_write_enqueues_embed_task(monkeypatch):
    from guardian.routes import chat as chat_routes

    class _StubChatlogDB:
        def __init__(self) -> None:
            self._thread: dict[str, object] = {"id": 557, "title": ""}

        def ensure_chat_thread(self, **_kwargs) -> None:
            return None

        def create_message(
            self, thread_id: int, role: str, content: str
        ) -> int:
            _ = (thread_id, role, content)
            return 9002

        def write_audit_log(self, *_args, **_kwargs) -> None:
            return None

        def get_chat_thread(self, thread_id: int):
            self._thread["id"] = thread_id
            return self._thread

        def count_messages(self, _thread_id: int) -> int:
            return 1

        def update_thread(self, _thread_id: int, **_kwargs) -> None:
            return None

    captured: list[dict[str, object]] = []

    def fake_enqueue_chat_embed(payload: dict[str, object]) -> str:
        captured.append(payload)
        return "embed-task-1"

    monkeypatch.setattr(chat_routes, "chatlog_db", _StubChatlogDB())
    monkeypatch.setattr(chat_routes, "_vector_store", object())
    monkeypatch.setattr(
        chat_routes, "enqueue_chat_embed", fake_enqueue_chat_embed
    )
    monkeypatch.setattr(
        chat_routes.event_bus, "emit_event", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        chat_routes, "_emit_thread_update_event", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        chat_routes,
        "acquire_turn_lock",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        chat_routes,
        "release_turn_lock",
        lambda *_args, **_kwargs: True,
    )

    thread_id = 557
    message = chat_routes._persist_message_to_thread(
        thread_id=thread_id,
        role="user",
        content="queue this",
        owner="default",
    )
    message_id = message["id"]
    assert captured == [
        {
            "thread_id": thread_id,
            "role": "user",
            "content": "queue this",
            "message_id": message_id,
        }
    ]


def test_chat_complete_turn_lock_blocks_parallel_requests(monkeypatch):
    from guardian.routes import chat as chat_routes

    class _StubChatlogDB:
        def get_chat_thread(self, _thread_id: int):
            return {"id": 558, "project_id": None}

        def list_messages(self, _thread_id: int, limit: int, offset: int):
            _ = (limit, offset)
            return [{"id": 1, "role": "user", "content": "seed context"}]

    thread_id = 558
    held_locks: dict[int, str] = {}

    def fake_acquire_turn_lock(
        requested_thread_id: int,
        owner: str,
        *,
        ttl_seconds: int | None = None,
    ) -> bool:
        _ = ttl_seconds
        if requested_thread_id in held_locks:
            return False
        held_locks[requested_thread_id] = owner
        return True

    def fake_release_turn_lock(requested_thread_id: int, owner: str) -> bool:
        if held_locks.get(requested_thread_id) != owner:
            return False
        del held_locks[requested_thread_id]
        return True

    async def fake_doc_context_override(**_kwargs):
        return None

    enqueued: list[object] = []

    def fake_enqueue(task, queue_name: str) -> None:
        enqueued.append((task, queue_name))

    monkeypatch.setattr(chat_routes, "chatlog_db", _StubChatlogDB())
    monkeypatch.setattr(
        chat_routes, "acquire_turn_lock", fake_acquire_turn_lock
    )
    monkeypatch.setattr(
        chat_routes, "release_turn_lock", fake_release_turn_lock
    )
    monkeypatch.setattr(
        chat_routes, "_build_doc_context_override", fake_doc_context_override
    )
    monkeypatch.setattr(chat_routes, "enqueue", fake_enqueue)
    monkeypatch.setattr(
        chat_routes.task_events, "publish", lambda *_a, **_k: None
    )

    first = client.post(f"/api/chat/{thread_id}/complete", json={})
    assert first.status_code == 200
    assert len(enqueued) == 1
    assert enqueued[0][0].turn_lock_owner == enqueued[0][0].task_id
    assert held_locks[thread_id] == enqueued[0][0].turn_lock_owner

    second = client.post(f"/api/chat/{thread_id}/complete", json={})
    assert second.status_code == 429
    assert second.json().get("detail") == "turn_in_flight"


def test_memory_crud_and_health():
    # Add longterm entry
    r = client.post(
        "/api/memory/longterm",
        json={"content": "keep this", "tags": ["x"], "pinned": True},
    )
    assert r.status_code == 200
    eid = r.json().get("id")
    assert eid

    # List
    r = client.get("/api/memory/longterm", params={"limit": 50, "offset": 0})
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("count") >= 1
    assert any(e.get("id") == eid for e in data.get("entries", []))

    # Update
    r = client.patch(
        f"/api/memory/longterm/{eid}",
        json={"content": "updated", "pinned": False},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # Delete
    r = client.delete(f"/api/memory/longterm/{eid}")
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # Health endpoints
    r = client.get("/health/memory")
    assert r.status_code == 200
    assert r.json().get("ok") is True
    r = client.get("/health/chat")
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_chat_pagination():
    # Insert > 60 messages into thread 99
    for i in range(60):
        client.post(
            "/api/chat/99/messages",
            json={"role": "user", "content": f"msg {i}"},
        )
    # Page 1
    r = client.get("/api/chat/99/messages", params={"limit": 50, "offset": 0})
    data = r.json()
    assert data["ok"] is True
    assert len(data["messages"]) == 50
    total = data["total"]
    assert total >= 60
    # Page 2
    r = client.get("/api/chat/99/messages", params={"limit": 50, "offset": 50})
    data = r.json()
    assert data["ok"] is True
    assert len(data["messages"]) >= 10


def test_memory_pagination():
    # Add > 60 longterm entries
    for i in range(60):
        client.post("/api/memory/longterm", json={"content": f"entry {i}"})
    # Page 1
    r = client.get("/api/memory/longterm", params={"limit": 50, "offset": 0})
    data = r.json()
    assert data["ok"] is True
    assert len(data["entries"]) == 50
    count = data["count"]
    assert count >= 60
    # Page 2
    r = client.get("/api/memory/longterm", params={"limit": 50, "offset": 50})
    data = r.json()
    assert data["ok"] is True
    assert len(data["entries"]) >= 10


def test_midterm_retention_pruning():
    from datetime import datetime, timedelta

    # Insert a midterm entry older than retention
    cutoff = datetime.utcnow() - timedelta(days=91)
    old_entry = {
        "user_id": "default",
        "silo": "midterm",
        "content": "old",
        "tags": "",
        "pinned": False,
        "created_at": cutoff.isoformat(),
        "updated_at": cutoff.isoformat(),
    }
    import sqlite3

    from sqlalchemy import text

    from guardian.config import get_settings
    from guardian.core.db import GuardianDB

    settings = get_settings()

    # Prefer a DB URL (works for Postgres + SQLite). Fall back to any legacy DB path.
    db_url = (
        getattr(settings, "DATABASE_URL", None)
        or getattr(settings, "database_url", None)
        or os.getenv("DATABASE_URL")
        or os.getenv("GUARDIAN_DATABASE_URL")
    )

    legacy_path = (
        getattr(settings, "GUARDIAN_DB_PATH", None)
        or getattr(settings, "MEMORY_DB_PATH", None)
        or getattr(settings, "GUARDIAN_MEMORY_DB_PATH", None)
        or os.getenv("GUARDIAN_DB_PATH")
        or os.getenv("MEMORY_DB_PATH")
        or os.getenv("GUARDIAN_MEMORY_DB_PATH")
    )

    if not db_url and not legacy_path:
        pytest.skip("No database configured for midterm pruning test")

    # Insert the old entry in a DB-agnostic way.
    if db_url and isinstance(db_url, str) and db_url.startswith("sqlite"):
        # sqlite URL forms: sqlite:///path/to.db or sqlite:////abs/path
        path = db_url.split("sqlite:///", 1)[-1]
        with sqlite3.connect(path) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO memory_entries (user_id, silo, content, tags, pinned, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    old_entry["user_id"],
                    old_entry["silo"],
                    old_entry["content"],
                    old_entry["tags"],
                    0,
                    old_entry["created_at"],
                    old_entry["updated_at"],
                ),
            )
            conn.commit()
        db = GuardianDB(db_url)
    else:
        # Postgres (or other SQLAlchemy-supported DB)
        db = GuardianDB(db_url or legacy_path)
        with db.get_session() as session:
            session.execute(
                text(
                    "INSERT INTO memory_entries (user_id, silo, content, tags, pinned, created_at, updated_at) "
                    "VALUES (:user_id, :silo, :content, :tags, :pinned, :created_at, :updated_at)"
                ),
                {
                    "user_id": old_entry["user_id"],
                    "silo": old_entry["silo"],
                    "content": old_entry["content"],
                    "tags": old_entry["tags"],
                    "pinned": False,
                    "created_at": old_entry["created_at"],
                    "updated_at": old_entry["updated_at"],
                },
            )
            session.commit()

    deleted = db.prune_midterm(cutoff.isoformat())
    assert deleted >= 1


def test_ephemeral_memory_clears_on_restart():
    # Add ephemeral entry
    r = client.post("/api/memory/ephemeral", json={"content": "temp"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # Present
    r = client.get("/api/memory/ephemeral")
    data = r.json()
    assert data["count"] >= 1
    # Simulate restart by clearing in-memory list
    from guardian.guardian_api import EPHEMERAL_MEMORY

    EPHEMERAL_MEMORY.clear()
    # Now empty
    r = client.get("/api/memory/ephemeral")
    data = r.json()
    assert data["count"] == 0


def test_chat_infinite_scroll():
    """Simulate infinite scroll loading with backend pagination."""
    thread_id = 1234
    # Insert > 100 messages
    for i in range(105):
        r = client.post(
            f"/api/chat/{thread_id}/messages",
            json={"role": "user", "content": f"scroll msg {i}"},
        )
        assert r.status_code == 200
    # Page 1
    r1 = client.get(
        f"/api/chat/{thread_id}/messages", params={"limit": 50, "offset": 0}
    )
    d1 = r1.json()
    assert d1["ok"] is True
    assert len(d1["messages"]) == 50
    ids1 = [m["id"] for m in d1["messages"]]
    # Page 2
    r2 = client.get(
        f"/api/chat/{thread_id}/messages", params={"limit": 50, "offset": 50}
    )
    d2 = r2.json()
    assert d2["ok"] is True
    assert len(d2["messages"]) in (50, 55)
    ids2 = [m["id"] for m in d2["messages"]]
    # Ensure no overlap
    assert not set(ids1).intersection(set(ids2))
    # Combined does not exceed total
    combined = ids1 + ids2
    assert len(combined) <= d1["total"]
    # IDs are monotonic ascending
    assert combined == sorted(combined)
