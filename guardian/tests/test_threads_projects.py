import sqlite3

from fastapi.testclient import TestClient

from guardian.config import get_settings
from guardian.guardian_api import app

client = TestClient(app)
settings = get_settings()


def _create_thread_row(title=None, project_id=None, user_id="default"):
    with sqlite3.connect(settings.GUARDIAN_DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_threads (user_id, title, project_id, created_at, updated_at) VALUES (?, ?, ?, datetime('now'), datetime('now'))",
            (user_id, title, project_id),
        )
        conn.commit()
        return c.lastrowid


def test_auto_title_on_first_message():
    tid = _create_thread_row(title=None)
    # Post first user message -> auto-title should be set
    r = client.post(
        f"/api/chat/{tid}/messages",
        json={
            "role": "user",
            "content": "This is a first message that should become title",
        },
    )
    assert r.status_code == 200
    # Fetch thread row
    with sqlite3.connect(settings.GUARDIAN_DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT title FROM chat_threads WHERE id = ?", (tid,))
        row = c.fetchone()
    assert row and isinstance(row[0], str) and len(row[0]) > 0


def test_thread_patch_and_delete_cascade():
    tid = _create_thread_row(title="Old")
    # Rename
    r = client.patch(f"/api/chat/threads/{tid}", json={"title": "New Title"})
    assert r.status_code == 200 and r.json().get("ok")
    # Move to project 1
    r = client.patch(f"/api/chat/threads/{tid}", json={"project_id": 1})
    assert r.status_code == 200 and r.json().get("ok")
    # Add a message then delete thread
    client.post(
        f"/api/chat/{tid}/messages", json={"role": "user", "content": "hi"}
    )
    r = client.delete(f"/api/chat/threads/{tid}")
    assert r.status_code == 200 and r.json().get("ok")
    with sqlite3.connect(settings.GUARDIAN_DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE thread_id = ?", (tid,)
        )
        assert c.fetchone()[0] == 0


def _create_project_row(name="P1", description="d"):
    with sqlite3.connect(settings.GUARDIAN_DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, created_at TEXT)"
        )
        c.execute(
            "INSERT INTO projects (name, description, created_at) VALUES (?, ?, datetime('now'))",
            (name, description),
        )
        conn.commit()
        return c.lastrowid


def test_project_patch_and_delete_ejects_threads():
    pid = _create_project_row()
    tid = _create_thread_row(project_id=pid)
    # Rename project
    r = client.patch(f"/projects/{pid}", json={"name": "Renamed"})
    assert r.status_code == 200 and r.json().get("ok")
    # Delete project -> thread survives, project_id becomes NULL
    r = client.delete(f"/projects/{pid}")
    assert r.status_code == 200 and r.json().get("ok")
    with sqlite3.connect(settings.GUARDIAN_DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT project_id FROM chat_threads WHERE id = ?", (tid,))
        row = c.fetchone()
    assert row is not None and row[0] is None
