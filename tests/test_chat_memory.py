import json
from fastapi.testclient import TestClient
from guardian.guardian_api import app


client = TestClient(app)


def test_chat_crud():
  # Create message
  r = client.post("/api/chat/1/messages", json={"role": "user", "content": "hello"})
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
  r = client.post("/api/chat/2/messages", json={"role": "user", "content": ""})
  assert r.status_code == 400
  assert r.json().get("ok") is False


def test_memory_crud_and_health():
  # Add longterm entry
  r = client.post("/api/memory/longterm", json={"content": "keep this", "tags": ["x"], "pinned": True})
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
  r = client.patch(f"/api/memory/longterm/{eid}", json={"content": "updated", "pinned": False})
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
    client.post("/api/chat/99/messages", json={"role": "user", "content": f"msg {i}"})
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
  old_entry = {"user_id": "default", "silo": "midterm", "content": "old", "tags": "", "pinned": False,
               "created_at": cutoff.isoformat(), "updated_at": cutoff.isoformat()}
  import sqlite3
  from guardian.config import get_settings
  settings = get_settings()
  with sqlite3.connect(settings.GUARDIAN_DB_PATH) as conn:
    c = conn.cursor()
    c.execute(
      "INSERT INTO memory_entries (user_id, silo, content, tags, pinned, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
      (old_entry["user_id"], old_entry["silo"], old_entry["content"], old_entry["tags"], 0, old_entry["created_at"], old_entry["updated_at"]))
    conn.commit()
  from guardian.core.db import GuardianDB
  db = GuardianDB(settings.GUARDIAN_DB_PATH)
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
    r = client.post(f"/api/chat/{thread_id}/messages", json={"role": "user", "content": f"scroll msg {i}"})
    assert r.status_code == 200
  # Page 1
  r1 = client.get(f"/api/chat/{thread_id}/messages", params={"limit": 50, "offset": 0})
  d1 = r1.json()
  assert d1["ok"] is True
  assert len(d1["messages"]) == 50
  ids1 = [m["id"] for m in d1["messages"]]
  # Page 2
  r2 = client.get(f"/api/chat/{thread_id}/messages", params={"limit": 50, "offset": 50})
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
