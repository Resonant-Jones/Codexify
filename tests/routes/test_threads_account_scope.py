from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import threads as threads_routes

API_KEY = "test-api-key"
SERVER_USER_ID = "local_user"


class _ThreadDB:
    def __init__(self) -> None:
        self._rows: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def seed_thread(
        self,
        *,
        user_id: str,
        title: str,
        project_id: str | None = None,
        thread_id: int | None = None,
    ) -> int:
        row_id = thread_id or self._next_id
        self._next_id = max(self._next_id, row_id + 1)
        row = {
            "id": row_id,
            "thread_id": row_id,
            "parent_thread_id": None,
            "session_id": f"seed:{row_id}",
            "summary": title,
            "title": title,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:00Z",
            "user_id": user_id,
            "project_id": project_id,
        }
        self._rows[row_id] = row
        return row_id

    def create_thread(
        self,
        *,
        parent_thread_id: int | None,
        session_id: str,
        summary: str,
        user_id: str,
        project_id: str | None = None,
    ) -> int:
        row_id = self._next_id
        self._next_id += 1
        self._rows[row_id] = {
            "id": row_id,
            "thread_id": row_id,
            "parent_thread_id": parent_thread_id,
            "session_id": session_id,
            "summary": summary,
            "title": summary,
            "created_at": "2026-04-12T00:00:00Z",
            "updated_at": "2026-04-12T00:00:00Z",
            "user_id": user_id,
            "project_id": project_id,
        }
        return row_id

    def list_threads(
        self,
        *,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = list(self._rows.values())
        if user_id is not None:
            rows = [row for row in rows if row["user_id"] == user_id]
        if project_id is not None:
            rows = [row for row in rows if row.get("project_id") == project_id]
        return [dict(row) for row in rows]

    def get_thread(self, thread_id: int) -> dict[str, Any] | None:
        row = self._rows.get(thread_id)
        return dict(row) if row else None


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", API_KEY)
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", SERVER_USER_ID)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")


def _make_client(db: _ThreadDB, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(threads_routes, "chatlog_db", db, raising=False)
    app = FastAPI()
    app.include_router(threads_routes.router)
    app.include_router(threads_routes.api_router)
    return TestClient(app)


def _headers(*, user_id: str) -> dict[str, str]:
    return {"X-API-Key": API_KEY, "X-User-Id": user_id}


def test_single_user_mode_preserves_current_thread_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")
    db = _ThreadDB()
    db.seed_thread(user_id="foreign_user", title="foreign")
    db.seed_thread(user_id=SERVER_USER_ID, title="local")
    client = _make_client(db, monkeypatch)

    list_response = client.get(
        "/threads", headers=_headers(user_id="spoofed_user")
    )
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert len(list_data["threads"]) == 2

    create_response = client.post(
        "/threads",
        headers=_headers(user_id="spoofed_user"),
        json={
            "title": "single-user-thread",
            "project_id": "p-1",
            "user_id": "caller-supplied",
        },
    )
    assert create_response.status_code == 200, create_response.text
    thread_id = create_response.json()["thread_id"]
    created = db.get_thread(thread_id)
    assert created is not None
    assert created["user_id"] == SERVER_USER_ID
    assert created["summary"] == "single-user-thread"


def test_multi_user_create_persists_authenticated_principal_as_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    db = _ThreadDB()
    client = _make_client(db, monkeypatch)
    headers = _headers(user_id="alice")

    response = client.post(
        "/threads",
        headers=headers,
        json={"title": "alice-thread", "project_id": "p-2"},
    )
    assert response.status_code == 200, response.text
    thread_id = response.json()["thread_id"]
    created = db.get_thread(thread_id)
    assert created is not None
    assert created["user_id"] == "alice"
    assert created["summary"] == "alice-thread"


def test_multi_user_list_read_returns_only_threads_for_authenticated_principal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    db = _ThreadDB()
    alice_thread_id = db.seed_thread(user_id="alice", title="alice-one")
    bob_thread_id = db.seed_thread(user_id="bob", title="bob-one")
    client = _make_client(db, monkeypatch)
    headers = _headers(user_id="alice")

    list_response = client.get("/threads", headers=headers)
    assert list_response.status_code == 200, list_response.text
    threads = list_response.json()["threads"]
    assert len(threads) == 1
    assert threads[0]["user_id"] == "alice"
    assert threads[0]["thread_id"] == alice_thread_id

    read_response = client.get(f"/threads/{alice_thread_id}", headers=headers)
    assert read_response.status_code == 200, read_response.text
    thread = read_response.json()["thread"]
    assert thread["user_id"] == "alice"
    assert thread["thread_id"] == alice_thread_id

    foreign_read = client.get(f"/threads/{bob_thread_id}", headers=headers)
    assert foreign_read.status_code == 404


def test_conflicting_caller_supplied_user_id_is_rejected_in_multi_user_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    db = _ThreadDB()
    client = _make_client(db, monkeypatch)
    headers = _headers(user_id="alice")

    list_conflict = client.get("/threads?user_id=bob", headers=headers)
    assert list_conflict.status_code == 403
    assert "authenticated principal" in list_conflict.json()["detail"]

    create_conflict = client.post(
        "/threads",
        headers=headers,
        json={"title": "conflict", "user_id": "bob"},
    )
    assert create_conflict.status_code == 403
    assert "authenticated principal" in create_conflict.json()["detail"]
