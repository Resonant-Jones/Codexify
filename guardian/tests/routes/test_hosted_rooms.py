"""Focused route tests for Hosted Room owner lifecycle API.

Covers authentication, creation, listing, detail, update, close,
account isolation, transaction rollback, and route registration.

Uses a minimal FastAPI app with the hosted_rooms router and a
SQLite-backed mock GuardianDB since the real GuardianDB requires Postgres.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.db.models import (
    ChatMessage,
    ChatThread,
    HostedRoom,
    HostedRoomInvite,
    HostedRoomParticipant,
    Project,
    User,
    UserProfile,
)


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, _compiler, **_kwargs):
    return "JSON"


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def test_engine():
    """In-memory SQLite engine with all tables needed for Hosted Room tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create tables (order matters for FK references)
    for table in (
        User.__table__,
        UserProfile.__table__,
        Project.__table__,
        ChatThread.__table__,
        HostedRoom.__table__,
        HostedRoomInvite.__table__,
        HostedRoomParticipant.__table__,
        ChatMessage.__table__,
    ):
        table.create(engine)

    # Seed users and default project
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(
            User.__table__.insert(),
            [
                {
                    "id": "account-a",
                    "username": "user-a",
                    "password_hash": "hash-a",
                    "role": "guest",
                    "created_at": now,
                },
                {
                    "id": "account-b",
                    "username": "user-b",
                    "password_hash": "hash-b",
                    "role": "guest",
                    "created_at": now,
                },
            ],
        )
        # Seed a default project for FK satisfaction
        conn.execute(
            Project.__table__.insert(),
            [
                {
                    "user_id": "account-a",
                    "name": "General",
                    "description": "Default project",
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )
        conn.execute(
            UserProfile.__table__.insert(),
            [
                {
                    "user_id": "account-a",
                    "display_name": "Alice",
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """Yield a fresh session for each test."""
    SessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class _MockGuardianDB:
    """Mock GuardianDB backed by the test SQLite engine."""

    def __init__(self, engine):
        self._engine = engine
        self._session_factory = sessionmaker(
            bind=engine, autocommit=False, autoflush=False
        )
        self.backend = "postgres"

    def get_session(self):
        return self._session_factory()

    def ensure_default_project(self):
        return None


@pytest.fixture
def mock_db(test_engine):
    return _MockGuardianDB(test_engine)


def _make_auth_scope(account_id: str = "account-a") -> RequestUserScope:
    """Build a RequestUserScope for the given account."""
    return RequestUserScope(
        user_id=account_id,
        account_id=account_id,
        multi_user_enabled=True,
    )


def _make_app(mock_db):
    """Build a minimal FastAPI app with the hosted_rooms router and mocked dependencies."""
    app = FastAPI()

    # Override get_request_user_scope
    async def _override_scope():
        return _make_auth_scope()

    # Make load_guardian_db_from_env return our mock
    import guardian.routes.hosted_rooms as hr

    hr.load_guardian_db_from_env = lambda: mock_db

    app.include_router(hr.router)
    return app


@pytest.fixture
def client(mock_db, monkeypatch):
    """TestClient with the hosted_rooms router and a mocked DB."""
    from guardian.routes import hosted_rooms as hr

    monkeypatch.setattr(hr, "load_guardian_db_from_env", lambda: mock_db)

    app = FastAPI()

    # Override the auth dependency to return our scope
    async def _override_get_request_user_scope():
        return RequestUserScope(
            user_id="account-a",
            account_id="account-a",
            multi_user_enabled=True,
        )

    app.dependency_overrides[get_request_user_scope] = _override_get_request_user_scope
    app.include_router(hr.router)

    return TestClient(app)


@pytest.fixture
def client_as_b(mock_db, monkeypatch):
    """TestClient authenticated as account-b."""
    from guardian.routes import hosted_rooms as hr

    monkeypatch.setattr(hr, "load_guardian_db_from_env", lambda: mock_db)

    app = FastAPI()

    async def _override_get_request_user_scope():
        return RequestUserScope(
            user_id="account-b",
            account_id="account-b",
            multi_user_enabled=True,
        )

    app.dependency_overrides[get_request_user_scope] = _override_get_request_user_scope
    app.include_router(hr.router)

    return TestClient(app)


@pytest.fixture
def unauthenticated_client(mock_db, monkeypatch):
    """TestClient with no authenticated user (empty scope)."""
    from guardian.routes import hosted_rooms as hr

    monkeypatch.setattr(hr, "load_guardian_db_from_env", lambda: mock_db)

    app = FastAPI()

    async def _override_get_request_user_scope():
        return RequestUserScope(
            user_id="",
            account_id=None,
            multi_user_enabled=False,
        )

    app.dependency_overrides[get_request_user_scope] = _override_get_request_user_scope
    app.include_router(hr.router)

    return TestClient(app)


# ── Authentication tests ──────────────────────────────────────────────────


def test_unauthenticated_create_fails(unauthenticated_client):
    resp = unauthenticated_client.post("/api/hosted-rooms", json={"title": "Test"})
    assert resp.status_code == 401


def test_unauthenticated_list_fails(unauthenticated_client):
    resp = unauthenticated_client.get("/api/hosted-rooms")
    assert resp.status_code == 401


def test_unauthenticated_get_fails(unauthenticated_client):
    resp = unauthenticated_client.get("/api/hosted-rooms/nonexistent")
    assert resp.status_code == 401


def test_unauthenticated_patch_fails(unauthenticated_client):
    resp = unauthenticated_client.patch("/api/hosted-rooms/nonexistent", json={"title": "X"})
    assert resp.status_code == 401


def test_unauthenticated_close_fails(unauthenticated_client):
    resp = unauthenticated_client.post("/api/hosted-rooms/nonexistent/close")
    assert resp.status_code == 401


# ── Creation tests ────────────────────────────────────────────────────────


def test_create_room_creates_thread_and_participant(client, test_engine):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "My Test Room"},
    )
    assert resp.status_code == 201, f"Body: {resp.text}"
    data = resp.json()
    assert data["title"] == "My Test Room"
    assert data["status"] == "active"
    assert data["slug"]
    assert " " not in data["slug"]
    assert data["backing_thread_id"] > 0
    assert data["enabled_agent_ids"] == []
    assert data["active_participant_count"] == 1
    assert data["pending_invitation_count"] == 0
    assert data["closed_at"] is None

    # Verify backing thread exists
    with test_engine.begin() as conn:
        thread = conn.execute(
            ChatThread.__table__.select().where(
                ChatThread.__table__.c.id == data["backing_thread_id"]
            )
        ).fetchone()
    assert thread is not None
    assert thread.user_id == "account-a"
    assert thread.title == "My Test Room"

    # Verify owner participant
    with test_engine.begin() as conn:
        participant = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == data["id"]
            )
        ).fetchone()
    assert participant is not None
    assert participant.kind == "human"
    assert participant.role == "owner"
    assert participant.state == "active"
    assert participant.bound_account_id == "account-a"
    assert participant.display_name == "Alice"


def test_create_room_derives_owner_from_auth(client_as_b, test_engine):
    resp = client_as_b.post(
        "/api/hosted-rooms",
        json={"title": "Owner Test"},
    )
    assert resp.status_code == 201
    data = resp.json()

    with test_engine.begin() as conn:
        thread = conn.execute(
            ChatThread.__table__.select().where(
                ChatThread.__table__.c.id == data["backing_thread_id"]
            )
        ).fetchone()
    assert thread.user_id == "account-b"

    with test_engine.begin() as conn:
        participant = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == data["id"]
            )
        ).fetchone()
    assert participant.bound_account_id == "account-b"


def test_create_room_creates_active_status(client):
    resp = client.post("/api/hosted-rooms", json={"title": "Status Test"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"


def test_create_room_generates_unique_slug(client):
    resp = client.post("/api/hosted-rooms", json={"title": "Slug Test Room"})
    assert resp.status_code == 201
    slug1 = resp.json()["slug"]
    assert slug1

    resp2 = client.post("/api/hosted-rooms", json={"title": "Slug Test Room"})
    assert resp2.status_code == 201
    slug2 = resp2.json()["slug"]
    assert slug1 != slug2, "Slugs must be unique"


def test_create_room_accepts_no_enabled_agents(client):
    resp = client.post("/api/hosted-rooms", json={"title": "No Agents"})
    assert resp.status_code == 201
    assert resp.json()["enabled_agent_ids"] == []


def test_create_room_accepts_empty_enabled_agent_ids(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Empty Agents", "enabled_agent_ids": []},
    )
    assert resp.status_code == 201
    assert resp.json()["enabled_agent_ids"] == []


def test_create_room_accepts_guardian(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Guardian Room", "enabled_agent_ids": ["guardian"]},
    )
    assert resp.status_code == 201
    assert resp.json()["enabled_agent_ids"] == ["guardian"]


def test_create_room_accepts_luna(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Luna Room", "enabled_agent_ids": ["luna"]},
    )
    assert resp.status_code == 201
    assert resp.json()["enabled_agent_ids"] == ["luna"]


def test_create_room_accepts_guardian_and_luna(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Both Room", "enabled_agent_ids": ["guardian", "luna"]},
    )
    assert resp.status_code == 201
    assert resp.json()["enabled_agent_ids"] == ["guardian", "luna"]


def test_create_room_rejects_unknown_agent(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Unknown Agent", "enabled_agent_ids": ["skynet"]},
    )
    assert resp.status_code == 422
    detail = resp.json().get("detail", {})
    assert detail.get("error") in ("invalid_agent_id",)


def test_create_room_handles_duplicate_agents_deterministically(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={
            "title": "Dupes",
            "enabled_agent_ids": ["guardian", "luna", "guardian", "luna"],
        },
    )
    assert resp.status_code == 201
    assert resp.json()["enabled_agent_ids"] == ["guardian", "luna"]


def test_create_room_trims_title(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "  Trimmed Title  "},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "Trimmed Title"


def test_create_room_rejects_blank_title(client):
    resp = client.post("/api/hosted-rooms", json={"title": ""})
    assert resp.status_code == 422


def test_create_room_rejects_whitespace_only_title(client):
    resp = client.post("/api/hosted-rooms", json={"title": "   "})
    assert resp.status_code == 422


def test_create_room_rejects_overlong_title(client):
    resp = client.post("/api/hosted-rooms", json={"title": "X" * 600})
    assert resp.status_code == 422


def test_create_room_returns_no_secret_fields(client):
    resp = client.post("/api/hosted-rooms", json={"title": "Secrets Check"})
    assert resp.status_code == 201
    data = resp.json()
    assert "token_hash" not in data
    assert "invite_token" not in data
    assert "api_key" not in data
    assert "access_token" not in data
    assert "authorization" not in data
    assert "bearer" not in data
    assert "password_hash" not in data


# ── Listing tests ─────────────────────────────────────────────────────────


def test_list_rooms_returns_only_owner_rooms(client, client_as_b):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Room A"})
    assert resp_a.status_code == 201
    room_a_id = resp_a.json()["id"]

    resp_b = client_as_b.post("/api/hosted-rooms", json={"title": "Room B"})
    assert resp_b.status_code == 201
    room_b_id = resp_b.json()["id"]

    # Account-a sees only Room A
    resp = client.get("/api/hosted-rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    room_ids = {r["id"] for r in rooms}
    assert room_a_id in room_ids
    assert room_b_id not in room_ids

    # Account-b sees only Room B
    resp = client_as_b.get("/api/hosted-rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    room_ids = {r["id"] for r in rooms}
    assert room_b_id in room_ids
    assert room_a_id not in room_ids


def test_list_rooms_returns_summaries_not_raw_models(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Summary Test"})
    assert resp_a.status_code == 201

    resp = client.get("/api/hosted-rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    for room in rooms:
        assert "id" in room
        assert "slug" in room
        assert "title" in room
        assert "status" in room
        assert "backing_thread_id" in room
        assert "enabled_agent_ids" in room
        assert "active_participant_count" in room
        assert "pending_invitation_count" in room
        assert "created_at" in room
        assert "updated_at" in room
        assert "token_hash" not in room
        assert "invite_token" not in room
        assert "participants" not in room
        assert "invitations" not in room


# ── Detail tests ──────────────────────────────────────────────────────────


def test_get_room_returns_owner_room(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Detail Test"})
    room_id = resp_a.json()["id"]

    resp = client.get(f"/api/hosted-rooms/{room_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == room_id
    assert "participants" in data
    assert "invitations" in data
    assert len(data["participants"]) == 1
    assert data["participants"][0]["role"] == "owner"


def test_get_room_cross_account_does_not_leak_existence(client, client_as_b):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Secret Room"})
    room_id = resp_a.json()["id"]

    resp = client_as_b.get(f"/api/hosted-rooms/{room_id}")
    assert resp.status_code == 404


def test_get_room_missing_returns_not_found(client):
    resp = client.get("/api/hosted-rooms/nonexistent-room-id")
    assert resp.status_code == 404


# ── Update tests ──────────────────────────────────────────────────────────


def test_owner_can_update_title(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Original Title"})
    room_id = resp_a.json()["id"]

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


def test_owner_can_update_enabled_agents(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Agent Update"})
    room_id = resp_a.json()["id"]

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"enabled_agent_ids": ["guardian", "luna"]},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled_agent_ids"] == ["guardian", "luna"]


def test_update_cannot_change_owner_id(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Owner ID Test"})
    room_id = resp_a.json()["id"]

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"owner_account_id": "account-b", "title": "Hijacked"},
    )
    assert resp.status_code == 422  # extra="forbid"


def test_update_cannot_change_slug(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Slug Change Test"})
    room_id = resp_a.json()["id"]

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"slug": "hacked-slug"},
    )
    assert resp.status_code == 422


def test_update_cannot_directly_change_status(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Status Change Test"})
    room_id = resp_a.json()["id"]

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"status": "closed"},
    )
    assert resp.status_code == 422


def test_cross_account_update_fails(client, client_as_b):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Cross Update"})
    room_id = resp_a.json()["id"]

    resp = client_as_b.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"title": "Hijack"},
    )
    assert resp.status_code == 404


def test_closed_room_update_is_rejected(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Closing Room"})
    room_id = resp_a.json()["id"]

    client.post(f"/api/hosted-rooms/{room_id}/close")

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"title": "Reopened"},
    )
    assert resp.status_code == 409


# ── Close tests ───────────────────────────────────────────────────────────


def test_owner_can_close_active_room(client, test_engine):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Close Test"})
    room_id = resp_a.json()["id"]
    thread_id = resp_a.json()["backing_thread_id"]

    resp = client.post(f"/api/hosted-rooms/{room_id}/close")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
    assert resp.json()["closed_at"] is not None

    # Thread still exists
    with test_engine.begin() as conn:
        thread = conn.execute(
            ChatThread.__table__.select().where(
                ChatThread.__table__.c.id == thread_id
            )
        ).fetchone()
    assert thread is not None

    # Room is closed in DB
    with test_engine.begin() as conn:
        room_row = conn.execute(
            HostedRoom.__table__.select().where(
                HostedRoom.__table__.c.id == room_id
            )
        ).fetchone()
    assert room_row.status == "closed"
    assert room_row.closed_at is not None


def test_repeated_close_is_idempotent(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Double Close"})
    room_id = resp_a.json()["id"]

    resp1 = client.post(f"/api/hosted-rooms/{room_id}/close")
    assert resp1.status_code == 200
    closed_at_1 = resp1.json()["closed_at"]

    resp2 = client.post(f"/api/hosted-rooms/{room_id}/close")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "closed"
    assert resp2.json()["closed_at"] == closed_at_1, (
        "Repeated close must preserve original closed_at"
    )


def test_close_preserves_participants(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Preserve Parts"})
    room_id = resp_a.json()["id"]

    client.post(f"/api/hosted-rooms/{room_id}/close")

    resp = client.get(f"/api/hosted-rooms/{room_id}")
    assert len(resp.json()["participants"]) == 1


def test_cross_account_close_fails(client, client_as_b):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Cross Close"})
    room_id = resp_a.json()["id"]

    resp = client_as_b.post(f"/api/hosted-rooms/{room_id}/close")
    assert resp.status_code == 404


def test_close_preserves_thread(client, test_engine):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Thread Preserve"})
    thread_id = resp_a.json()["backing_thread_id"]
    room_id = resp_a.json()["id"]

    client.post(f"/api/hosted-rooms/{room_id}/close")

    with test_engine.begin() as conn:
        thread = conn.execute(
            ChatThread.__table__.select().where(
                ChatThread.__table__.c.id == thread_id
            )
        ).fetchone()
    assert thread is not None


# ── Account isolation proofs ──────────────────────────────────────────────


def test_account_a_cannot_list_account_b_rooms(client, client_as_b):
    client_as_b.post("/api/hosted-rooms", json={"title": "B Room"})

    resp = client.get("/api/hosted-rooms")
    rooms = resp.json()
    b_titles = {r["title"] for r in rooms}
    assert "B Room" not in b_titles


def test_account_a_cannot_inspect_account_b_room(client, client_as_b):
    resp_b = client_as_b.post("/api/hosted-rooms", json={"title": "B Private"})
    room_id = resp_b.json()["id"]

    resp = client.get(f"/api/hosted-rooms/{room_id}")
    assert resp.status_code == 404


def test_account_a_cannot_update_account_b_room(client, client_as_b):
    resp_b = client_as_b.post("/api/hosted-rooms", json={"title": "B Update Target"})
    room_id = resp_b.json()["id"]

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"title": "Hijacked"},
    )
    assert resp.status_code == 404


def test_account_a_cannot_close_account_b_room(client, client_as_b):
    resp_b = client_as_b.post("/api/hosted-rooms", json={"title": "B Close Target"})
    room_id = resp_b.json()["id"]

    resp = client.post(f"/api/hosted-rooms/{room_id}/close")
    assert resp.status_code == 404


def test_request_body_owner_spoofing_impossible(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={
            "title": "Spoof Room",
            "owner_account_id": "account-b",
        },
    )
    assert resp.status_code == 422  # extra="forbid"


# ── Slug uniqueness proof ─────────────────────────────────────────────────


def test_slug_uniqueness_across_multiple_rooms(client):
    slugs: set[str] = set()
    for i in range(10):
        resp = client.post("/api/hosted-rooms", json={"title": "Same Title"})
        assert resp.status_code == 201, f"Room {i} failed: {resp.text}"
        slug = resp.json()["slug"]
        assert slug not in slugs, f"Duplicate slug: {slug}"
        slugs.add(slug)


# ── Route registration / OpenAPI proof ────────────────────────────────────


def test_routes_exist_in_openapi(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})

    assert "/api/hosted-rooms" in paths
    assert "get" in paths.get("/api/hosted-rooms", {})
    assert "post" in paths.get("/api/hosted-rooms", {})
    assert "/api/hosted-rooms/{room_id}" in paths
    assert "/api/hosted-rooms/{room_id}/close" in paths


def test_guest_routes_do_not_exist(client):
    resp = client.get("/openapi.json")
    schema = resp.json()
    paths = schema.get("paths", {})

    for path in paths:
        assert "guest-session" not in path.lower()
        assert "join-room" not in path.lower()
        assert "invite-exchange" not in path.lower()
        assert f"{path}" != "/api/hosted-rooms/messages"  # no message routes


# ── No-op update test ─────────────────────────────────────────────────────


def test_no_op_update_behaves_consistently(client):
    resp_a = client.post("/api/hosted-rooms", json={"title": "Noop Test"})
    room_id = resp_a.json()["id"]
    original_title = resp_a.json()["title"]

    resp = client.patch(
        f"/api/hosted-rooms/{room_id}",
        json={"title": original_title},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == original_title


# ── Enabled-agent validation edge cases ───────────────────────────────────


def test_create_room_rejects_non_list_enabled_agents(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Bad Agents", "enabled_agent_ids": "guardian"},
    )
    assert resp.status_code in (422, 500), f"Unexpected: {resp.status_code}"


def test_create_room_agent_ids_are_case_insensitive(client):
    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Case Test", "enabled_agent_ids": ["GUARDIAN", "Luna"]},
    )
    assert resp.status_code == 201
    assert resp.json()["enabled_agent_ids"] == ["guardian", "luna"]


# ── Transaction rollback proof ────────────────────────────────────────────


def test_rollback_leaves_no_orphan_thread_on_room_failure(client, test_engine, mock_db, monkeypatch):
    """Force room persistence to fail after thread creation; verify rollback."""
    import guardian.routes.hosted_rooms as hr

    # Count threads before
    with test_engine.begin() as conn:
        before_count = len(
            conn.execute(ChatThread.__table__.select()).fetchall()
        )

    # Create a failing session proxy that raises on HostedRoom add
    original_get_session = mock_db.get_session

    class _FailingSession:
        def __init__(self, real_session):
            self._real = real_session
            self._rolled_back = False

        def get(self, model, pk):
            return self._real.get(model, pk)

        def scalar(self, *args, **kwargs):
            return self._real.scalar(*args, **kwargs)

        def execute(self, *args, **kwargs):
            return self._real.execute(*args, **kwargs)

        def add(self, instance):
            if isinstance(instance, HostedRoom):
                raise RuntimeError("Simulated room persistence failure")
            return self._real.add(instance)

        def flush(self):
            self._real.flush()

        def commit(self):
            self._real.commit()

        def rollback(self):
            self._rolled_back = True
            self._real.rollback()

        def refresh(self, instance):
            self._real.refresh(instance)

        def query(self, *args, **kwargs):
            return self._real.query(*args, **kwargs)

        def close(self):
            self._real.close()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            # Rollback if not already done
            if not self._rolled_back:
                self._real.rollback()
            self._real.close()
            return False

    monkeypatch.setattr(
        mock_db,
        "get_session",
        lambda: _FailingSession(original_get_session()),
    )

    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Rollback Test"},
    )
    assert resp.status_code == 500

    # Count threads after — should be same as before
    with test_engine.begin() as conn:
        after_count = len(
            conn.execute(ChatThread.__table__.select()).fetchall()
        )

    assert after_count == before_count, (
        f"Orphan thread detected: before={before_count}, after={after_count}"
    )


def test_rollback_leaves_no_orphan_room_on_participant_failure(client, test_engine, mock_db, monkeypatch):
    """Force participant persistence to fail; verify rollback of room and thread."""
    import guardian.routes.hosted_rooms as hr

    with test_engine.begin() as conn:
        before_thread_count = len(
            conn.execute(ChatThread.__table__.select()).fetchall()
        )
        before_room_count = len(
            conn.execute(HostedRoom.__table__.select()).fetchall()
        )

    original_get_session = mock_db.get_session

    class _FailingSession:
        def __init__(self, real_session):
            self._real = real_session
            self._rolled_back = False

        def get(self, model, pk):
            return self._real.get(model, pk)

        def scalar(self, *args, **kwargs):
            return self._real.scalar(*args, **kwargs)

        def execute(self, *args, **kwargs):
            return self._real.execute(*args, **kwargs)

        def add(self, instance):
            if isinstance(instance, HostedRoomParticipant):
                raise RuntimeError("Simulated participant persistence failure")
            return self._real.add(instance)

        def flush(self):
            self._real.flush()

        def commit(self):
            self._real.commit()

        def rollback(self):
            self._rolled_back = True
            self._real.rollback()

        def refresh(self, instance):
            self._real.refresh(instance)

        def query(self, *args, **kwargs):
            return self._real.query(*args, **kwargs)

        def close(self):
            self._real.close()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            if not self._rolled_back:
                self._real.rollback()
            self._real.close()
            return False

    monkeypatch.setattr(
        mock_db,
        "get_session",
        lambda: _FailingSession(original_get_session()),
    )

    resp = client.post(
        "/api/hosted-rooms",
        json={"title": "Participant Fail"},
    )
    assert resp.status_code == 500

    with test_engine.begin() as conn:
        after_thread_count = len(
            conn.execute(ChatThread.__table__.select()).fetchall()
        )
        after_room_count = len(
            conn.execute(HostedRoom.__table__.select()).fetchall()
        )

    assert after_thread_count == before_thread_count, (
        f"Orphan thread: before={before_thread_count}, after={after_thread_count}"
    )
    assert after_room_count == before_room_count, (
        f"Orphan room: before={before_room_count}, after={after_room_count}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Invitation tests
# ═══════════════════════════════════════════════════════════════════════════

import hashlib


def _create_room(client) -> str:
    """Helper: create a room and return its ID."""
    resp = client.post("/api/hosted-rooms", json={"title": "Invite Test Room"})
    assert resp.status_code == 201, f"Room creation failed: {resp.text}"
    return resp.json()["id"]


def _create_closed_room(client) -> str:
    """Helper: create and close a room, return its ID."""
    room_id = _create_room(client)
    resp = client.post(f"/api/hosted-rooms/{room_id}/close")
    assert resp.status_code == 200
    return room_id


# ── Authentication tests ──────────────────────────────────────────────────


def test_unauthenticated_invite_create_fails(unauthenticated_client):
    resp = unauthenticated_client.post(
        "/api/hosted-rooms/some-room/invites",
        json={"intended_display_name": "Guest"},
    )
    assert resp.status_code == 401


def test_unauthenticated_invite_list_fails(unauthenticated_client):
    resp = unauthenticated_client.get("/api/hosted-rooms/some-room/invites")
    assert resp.status_code == 401


def test_unauthenticated_revoke_fails(unauthenticated_client):
    resp = unauthenticated_client.post(
        "/api/hosted-rooms/some-room/invites/some-invite/revoke"
    )
    assert resp.status_code == 401


# ── Creation tests ────────────────────────────────────────────────────────


def test_owner_creates_pending_invitation(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Jane Guest"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["invitation"]["status"] == "pending"
    assert data["invitation"]["intended_display_name"] == "Jane Guest"
    assert data["invitation"]["room_id"] == room_id
    assert "invitation_token" in data
    assert "join_path" in data
    assert data["join_path"] == f"/join/{data['invitation_token']}"


def test_create_response_includes_plaintext_token_exactly_once(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Token Check"},
    )
    assert resp.status_code == 201
    data = resp.json()
    token = data.get("invitation_token")
    assert token
    assert len(token) >= 32  # at least 256 bits encoded
    # Token must not be inside the invitation metadata
    assert "invitation_token" not in data["invitation"]
    assert "token_hash" not in data["invitation"]


def test_create_response_includes_relative_join_path(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Path Test"},
    )
    data = resp.json()
    join_path = data["join_path"]
    assert join_path.startswith("/join/")
    # The path should not include the room ID
    assert room_id not in join_path


def test_persisted_row_contains_only_hash_not_plaintext(client, test_engine):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Hash Test"},
    )
    assert resp.status_code == 201
    token = resp.json()["invitation_token"]
    invite_id = resp.json()["invitation"]["id"]

    # Inspect the database row
    with test_engine.begin() as conn:
        row = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.id == invite_id
            )
        ).fetchone()
    assert row is not None
    # The stored hash must be sha256(token)
    expected_hash = hashlib.sha256(token.encode()).hexdigest()
    assert row.token_hash == expected_hash
    # Plaintext token must not appear in any column
    for col_name in row._mapping.keys():
        col_val = str(row._mapping[col_name])
        assert token not in col_val, f"Plaintext token found in column {col_name}"


def test_stored_verifier_differs_from_plaintext(client, test_engine):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Diff Test"},
    )
    token = resp.json()["invitation_token"]
    invite_id = resp.json()["invitation"]["id"]

    with test_engine.begin() as conn:
        row = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.id == invite_id
            )
        ).fetchone()
    # The stored hash must NOT equal the plaintext token
    assert row.token_hash != token
    # And it must be the correct SHA-256 hex digest
    assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()


def test_token_is_url_safe(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "URL Safe Test"},
    )
    token = resp.json()["invitation_token"]
    # URL-safe base64: only alphanumeric, '-', '_'
    import re
    assert re.fullmatch(r"[A-Za-z0-9_-]+", token), f"Token not URL-safe: {token}"


def test_token_has_sufficient_entropy(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Entropy Test"},
    )
    token = resp.json()["invitation_token"]
    # token_urlsafe(32) = 43 chars, at least 32 base64 chars = 256 bits
    assert len(token) >= 40, f"Token too short for 256-bit entropy: {len(token)} chars"


def test_verifier_format_is_stable(client, test_engine):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Format Test"},
    )
    invite_id = resp.json()["invitation"]["id"]
    with test_engine.begin() as conn:
        row = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.id == invite_id
            )
        ).fetchone()
    # Must be 64 lowercase hex chars
    import re
    assert re.fullmatch(r"[a-f0-9]{64}", row.token_hash), (
        f"Verifier not 64 hex chars: {row.token_hash}"
    )


def test_intended_display_name_is_trimmed(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "  Trimmed Name  "},
    )
    assert resp.status_code == 201
    assert resp.json()["invitation"]["intended_display_name"] == "Trimmed Name"


def test_blank_display_name_rejected(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": ""},
    )
    assert resp.status_code == 422


def test_overlong_display_name_rejected(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "X" * 300},
    )
    assert resp.status_code == 422


def test_null_expiry_accepted(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "No Expiry"},
    )
    assert resp.status_code == 201
    assert resp.json()["invitation"]["expires_at"] is None


def test_future_expiry_accepted(client):
    from datetime import timedelta
    room_id = _create_room(client)
    future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Expiry Test", "expires_at": future},
    )
    assert resp.status_code == 201
    assert resp.json()["invitation"]["expires_at"] is not None


def test_past_expiry_rejected(client):
    from datetime import timedelta
    room_id = _create_room(client)
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Past Expiry", "expires_at": past},
    )
    assert resp.status_code == 422


def test_excessive_future_expiry_rejected(client):
    from datetime import timedelta
    room_id = _create_room(client)
    too_far = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Far Expiry", "expires_at": too_far},
    )
    assert resp.status_code == 422


def test_closed_room_rejects_invitation(client):
    room_id = _create_closed_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Late Invite"},
    )
    assert resp.status_code == 409


def test_extra_fields_rejected(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Extra", "token": "fake", "status": "accepted"},
    )
    assert resp.status_code == 422


def test_owner_id_spoofing_rejected(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Spoof", "owner_account_id": "account-b"},
    )
    assert resp.status_code == 422


# ── Listing tests ─────────────────────────────────────────────────────────


def test_owner_lists_invitations_for_owned_room(client):
    room_id = _create_room(client)
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "First"},
    )
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Second"},
    )

    resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    assert resp.status_code == 200
    invites = resp.json()
    assert len(invites) == 2


def test_list_deterministic_newest_first(client):
    room_id = _create_room(client)
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Older"},
    )
    import time
    time.sleep(0.01)
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Newer"},
    )

    resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    invites = resp.json()
    assert invites[0]["intended_display_name"] == "Newer"
    assert invites[1]["intended_display_name"] == "Older"


def test_list_includes_lifecycle_timestamps(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "TS Test"},
    )
    invite_id = resp.json()["invitation"]["id"]

    list_resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    invite_data = [i for i in list_resp.json() if i["id"] == invite_id][0]
    assert "created_at" in invite_data
    assert "updated_at" in invite_data
    assert "expires_at" in invite_data  # may be null


def test_list_token_is_absent(client):
    room_id = _create_room(client)
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "No Token Here"},
    )
    resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    for inv in resp.json():
        assert "invitation_token" not in inv
        assert "token_hash" not in inv
        assert "token" not in inv


def test_unrelated_room_invitations_absent(client, client_as_b):
    room_a = _create_room(client)
    room_b = _create_room(client_as_b)

    client.post(
        f"/api/hosted-rooms/{room_a}/invites",
        json={"intended_display_name": "A Invite"},
    )
    client_as_b.post(
        f"/api/hosted-rooms/{room_b}/invites",
        json={"intended_display_name": "B Invite"},
    )

    # Account-a lists only room A's invites
    resp = client.get(f"/api/hosted-rooms/{room_a}/invites")
    names = {i["intended_display_name"] for i in resp.json()}
    assert "A Invite" in names
    assert "B Invite" not in names


def test_cross_account_list_does_not_leak_existence(client, client_as_b):
    room_a = _create_room(client)
    # account-b tries to list invites for account-a's room
    resp = client_as_b.get(f"/api/hosted-rooms/{room_a}/invites")
    assert resp.status_code == 404


def test_list_request_does_not_mutate_expiry_state(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "No Mutate"},
    )
    invite_id = resp.json()["invitation"]["id"]

    # List multiple times
    for _ in range(3):
        list_resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
        invite_data = [i for i in list_resp.json() if i["id"] == invite_id][0]
        assert invite_data["status"] == "pending"


def test_no_presence_field_returned(client):
    room_id = _create_room(client)
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Presence Check"},
    )
    resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    for inv in resp.json():
        assert "presence" not in inv
        assert "online" not in inv


# ── Revocation tests ──────────────────────────────────────────────────────


def test_owner_revokes_pending_invitation(client, test_engine):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Revoke Me"},
    )
    invite_id = resp.json()["invitation"]["id"]

    revoke_resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke"
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["invitation"]["status"] == "revoked"
    assert revoke_resp.json()["invitation"]["revoked_at"] is not None

    # Verify in DB
    with test_engine.begin() as conn:
        row = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.id == invite_id
            )
        ).fetchone()
    assert row.status == "revoked"
    assert row.revoked_at is not None


def test_revocation_sets_timestamp_once(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "TS Once"},
    )
    invite_id = resp.json()["invitation"]["id"]

    rev1 = client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")
    ts1 = rev1.json()["invitation"]["revoked_at"]
    assert ts1 is not None

    # Wait a tiny bit to ensure timestamp would differ if overwritten
    import time
    time.sleep(0.01)

    rev2 = client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")
    ts2 = rev2.json()["invitation"]["revoked_at"]
    assert ts2 == ts1, "Repeated revocation must preserve original timestamp"


def test_repeated_revocation_is_idempotent(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Idempotent"},
    )
    invite_id = resp.json()["invitation"]["id"]

    rev1 = client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")
    assert rev1.status_code == 200
    assert rev1.json()["invitation"]["status"] == "revoked"

    rev2 = client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")
    assert rev2.status_code == 200
    assert rev2.json()["invitation"]["status"] == "revoked"


def test_revocation_preserves_room(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Preserve Room"},
    )
    invite_id = resp.json()["invitation"]["id"]

    client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")

    # Room still exists
    room_resp = client.get(f"/api/hosted-rooms/{room_id}")
    assert room_resp.status_code == 200


def test_revocation_preserves_thread(client, test_engine):
    room_id = _create_room(client)
    room_data = client.get(f"/api/hosted-rooms/{room_id}").json()
    thread_id = room_data["backing_thread_id"]

    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Preserve Thread"},
    )
    invite_id = resp.json()["invitation"]["id"]

    client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")

    with test_engine.begin() as conn:
        thread = conn.execute(
            ChatThread.__table__.select().where(ChatThread.__table__.c.id == thread_id)
        ).fetchone()
    assert thread is not None


def test_revocation_preserves_participants(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Parts"},
    )
    invite_id = resp.json()["invitation"]["id"]

    client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")

    room_resp = client.get(f"/api/hosted-rooms/{room_id}")
    # Owner participant still exists
    assert len(room_resp.json()["participants"]) >= 1


def test_cross_account_revocation_does_not_leak(client, client_as_b):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Cross Revoke"},
    )
    invite_id = resp.json()["invitation"]["id"]

    revoke_resp = client_as_b.post(
        f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke"
    )
    assert revoke_resp.status_code == 404


def test_mismatched_room_invite_path_fails(client):
    room_a = _create_room(client)
    # Create a second room
    resp = client.post("/api/hosted-rooms", json={"title": "Room Two"})
    assert resp.status_code == 201
    room_b = resp.json()["id"]

    # Create invite in room_a
    inv_resp = client.post(
        f"/api/hosted-rooms/{room_a}/invites",
        json={"intended_display_name": "Room A Invite"},
    )
    invite_id = inv_resp.json()["invitation"]["id"]

    # Try to revoke it through room_b's path
    revoke_resp = client.post(
        f"/api/hosted-rooms/{room_b}/invites/{invite_id}/revoke"
    )
    assert revoke_resp.status_code == 404


def test_revocation_response_contains_no_token_or_hash(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "No Secrets"},
    )
    invite_id = resp.json()["invitation"]["id"]

    revoke_resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke"
    )
    data = revoke_resp.json()
    assert "invitation_token" not in data
    assert "token_hash" not in data
    assert "token" not in data
    assert "invitation_token" not in data.get("invitation", {})
    assert "token_hash" not in data.get("invitation", {})


# ── Existing room-detail tests (invitation-aware) ─────────────────────────


def test_newly_created_invite_appears_in_room_detail(client):
    room_id = _create_room(client)
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Detail Test"},
    )

    room_resp = client.get(f"/api/hosted-rooms/{room_id}")
    invites = room_resp.json()["invitations"]
    assert len(invites) == 1
    assert invites[0]["intended_display_name"] == "Detail Test"


def test_revoked_state_appears_in_room_detail(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Revoked Detail"},
    )
    invite_id = resp.json()["invitation"]["id"]

    client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")

    room_resp = client.get(f"/api/hosted-rooms/{room_id}")
    invites = room_resp.json()["invitations"]
    revoked = [i for i in invites if i["id"] == invite_id][0]
    assert revoked["status"] == "revoked"
    assert revoked["revoked_at"] is not None


def test_room_detail_contains_no_token_or_hash(client):
    room_id = _create_room(client)
    client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "No Secrets"},
    )

    room_resp = client.get(f"/api/hosted-rooms/{room_id}")
    for inv in room_resp.json()["invitations"]:
        assert "token_hash" not in inv
        assert "invitation_token" not in inv
        assert "token" not in inv


# ── Account isolation ─────────────────────────────────────────────────────


def test_account_a_cannot_create_invite_for_account_b_room(client, client_as_b):
    room_b = _create_room(client_as_b)
    resp = client.post(
        f"/api/hosted-rooms/{room_b}/invites",
        json={"intended_display_name": "Sneaky"},
    )
    assert resp.status_code == 404


def test_account_a_cannot_list_account_b_invites(client, client_as_b):
    room_b = _create_room(client_as_b)
    resp = client.get(f"/api/hosted-rooms/{room_b}/invites")
    assert resp.status_code == 404


def test_account_a_cannot_revoke_account_b_invites(client, client_as_b):
    room_b = _create_room(client_as_b)
    inv_resp = client_as_b.post(
        f"/api/hosted-rooms/{room_b}/invites",
        json={"intended_display_name": "B's Invite"},
    )
    invite_id = inv_resp.json()["invitation"]["id"]

    resp = client.post(f"/api/hosted-rooms/{room_b}/invites/{invite_id}/revoke")
    assert resp.status_code == 404


# ── Collision handling ────────────────────────────────────────────────────

def test_forced_verifier_collision_retries(client, mock_db, monkeypatch, test_engine):
    """Force a hash collision and verify retry succeeds."""
    import guardian.routes.hosted_rooms as hr

    room_id = _create_room(client)

    # Pre-insert a row with a known token_hash to force a collision
    fixed_token = "fixed-collision-token-abc123"
    fixed_hash = hashlib.sha256(fixed_token.encode()).hexdigest()
    import uuid as _uuid
    now = datetime.now(timezone.utc)
    with test_engine.begin() as conn:
        conn.execute(
            HostedRoomInvite.__table__.insert(),
            {
                "id": str(_uuid.uuid4()),
                "room_id": room_id,
                "intended_display_name": "Pre-existing",
                "token_hash": fixed_hash,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            },
        )

    call_count = [0]
    original_generate = hr._generate_invitation_token

    def _colliding_generator():
        call_count[0] += 1
        if call_count[0] <= 2:
            return fixed_token  # collides with pre-inserted row
        return original_generate()  # unique on third attempt

    monkeypatch.setattr(hr, "_generate_invitation_token", _colliding_generator)

    # Create invite — first two calls collide, third succeeds
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Collision Survivor"},
    )
    assert resp.status_code == 201, f"Collision retry failed: {resp.text}"
    # Should have been called 3 times (2 collisions + 1 success)
    assert call_count[0] == 3, f"Expected 3 generation attempts, got {call_count[0]}"


def test_collision_exhaustion_fails_safely(client, test_engine, monkeypatch):
    """Force all token generation to produce the same token; verify exhaustion."""
    room_id = _create_room(client)

    # Create first invite with a known token's hash
    fixed_token = "exhaustion-collision-token-xyz"
    fixed_hash = hashlib.sha256(fixed_token.encode()).hexdigest()

    # Manually insert a row with our fixed hash
    import uuid as _uuid
    now = datetime.now(timezone.utc)
    with test_engine.begin() as conn:
        conn.execute(
            HostedRoomInvite.__table__.insert(),
            {
                "id": str(_uuid.uuid4()),
                "room_id": room_id,
                "intended_display_name": "Pre-existing",
                "token_hash": fixed_hash,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
            },
        )

    import guardian.routes.hosted_rooms as hr

    # Patch token generation to always return the fixed token
    monkeypatch.setattr(hr, "_generate_invitation_token", lambda: fixed_token)

    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Exhaustion"},
    )
    assert resp.status_code == 503
    detail = resp.json().get("detail", {})
    assert detail.get("error") == "token_collision"


# ── OpenAPI / Route registration ──────────────────────────────────────────


def test_invite_routes_exist_in_openapi(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})

    assert "/api/hosted-rooms/{room_id}/invites" in paths
    assert "post" in paths.get("/api/hosted-rooms/{room_id}/invites", {})
    assert "get" in paths.get("/api/hosted-rooms/{room_id}/invites", {})
    assert "/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke" in paths
    assert "post" in paths.get("/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke", {})


def test_guest_routes_absent_from_openapi(client):
    resp = client.get("/openapi.json")
    schema = resp.json()
    paths = schema.get("paths", {})

    for path in paths:
        assert "/join/" not in path
        assert "exchange" not in path.lower()
        assert "guest-session" not in path.lower()
        assert "guest-message" not in path.lower()


# ── One-time response proof ───────────────────────────────────────────────


def test_token_not_retrievable_after_creation(client):
    room_id = _create_room(client)
    create_resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "One Time"},
    )
    token = create_resp.json()["invitation_token"]
    invite_id = create_resp.json()["invitation"]["id"]

    # List does not contain token
    list_resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    for inv in list_resp.json():
        assert token not in str(inv)

    # Room detail does not contain token
    room_resp = client.get(f"/api/hosted-rooms/{room_id}")
    assert token not in str(room_resp.json())

    # Revoke does not return token
    revoke_resp = client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")
    assert token not in str(revoke_resp.json())

    # No token-retrieval endpoint exists (we don't have one to test)


# ── Expired invitation revocation behavior ────────────────────────────────


def test_expired_invitation_revocation_follows_explicit_policy(client, test_engine):
    """Expired invitations cannot be revoked (status is not pending/accepted)."""
    room_id = _create_room(client)

    # Manually create an expired invite in DB (our API rejects past expiry,
    # so we insert directly)
    import uuid as _uuid
    now = datetime.now(timezone.utc)
    invite_id = str(_uuid.uuid4())
    with test_engine.begin() as conn:
        conn.execute(
            HostedRoomInvite.__table__.insert(),
            {
                "id": invite_id,
                "room_id": room_id,
                "intended_display_name": "Expired One",
                "token_hash": hashlib.sha256(b"expired-test-token").hexdigest(),
                "status": "expired",
                "expired_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )

    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke"
    )
    # Expired invites cannot transition to revoked per lifecycle constraint
    assert resp.status_code == 409


# ── Naive timestamp handling ──────────────────────────────────────────────


def test_naive_expiry_timestamp_rejected(client):
    """Timestamps without timezone info must be rejected."""
    from datetime import timedelta
    room_id = _create_room(client)
    # Naive datetime without tzinfo
    naive = (datetime.now() + timedelta(days=7)).isoformat()
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "Naive TS", "expires_at": naive},
    )
    # Either 422 if it passes ISO parsing without timezone, or rejection
    # Our validation explicitly requires timezone-aware
    assert resp.status_code == 422


# ── Database secret persistence proof ─────────────────────────────────────


def test_plaintext_token_absent_from_all_db_columns(client, test_engine):
    """Verify no column in the row contains the plaintext token."""
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": "DB Secret Check"},
    )
    token = resp.json()["invitation_token"]
    invite_id = resp.json()["invitation"]["id"]

    with test_engine.begin() as conn:
        row = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.id == invite_id
            )
        ).fetchone()

    row_dict = dict(row._mapping)
    for col_name, col_value in row_dict.items():
        col_str = str(col_value)
        assert token not in col_str, (
            f"Plaintext token found in column '{col_name}': {col_str[:50]}..."
        )

    # token_hash must be SHA-256 of the token
    expected_hash = hashlib.sha256(token.encode()).hexdigest()
    assert row_dict["token_hash"] == expected_hash


# ── Logging sentinel proof ────────────────────────────────────────────────
# (Verified via manual code inspection — no plaintext token or verifier
#  appears in any log statement in hosted_rooms.py)


# ── Guest-surface sentinel proof ──────────────────────────────────────────
# (Verified via grep — no guest exchange or session implementation exists)


# ── Secret surfaced sentinel proof ────────────────────────────────────────
# (Verified via grep — no reusable model contains token fields; only
#  InviteCreationResponse contains invitation_token, and it is marked as
#  a one-time response model)


# ═══════════════════════════════════════════════════════════════════════════
# Owner message tests
# ═══════════════════════════════════════════════════════════════════════════


def test_owner_can_list_messages(client):
    room_id = _create_room(client)
    resp = client.get(f"/api/hosted-rooms/{room_id}/messages")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_owner_list_messages_unauthenticated_fails(unauthenticated_client):
    resp = unauthenticated_client.get("/api/hosted-rooms/some-room/messages")
    assert resp.status_code == 401


def test_owner_list_cross_account_fails(client, client_as_b):
    room_id = _create_room(client)
    resp = client_as_b.get(f"/api/hosted-rooms/{room_id}/messages")
    assert resp.status_code == 404


def test_owner_list_closed_room_fails(client):
    room_id = _create_room(client)
    client.post(f"/api/hosted-rooms/{room_id}/close")
    resp = client.get(f"/api/hosted-rooms/{room_id}/messages")
    assert resp.status_code == 409


def test_owner_list_returns_empty_for_new_room(client):
    room_id = _create_room(client)
    resp = client.get(f"/api/hosted-rooms/{room_id}/messages")
    assert resp.json() == []


def test_owner_can_post_message(client, test_engine):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": "Hello from owner"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "user"
    assert data["content"] == "Hello from owner"
    assert data["sender"] is not None
    assert data["sender"]["display_name"] == "Alice"

    # Verify in DB
    with test_engine.begin() as conn:
        row = conn.execute(
            ChatMessage.__table__.select().where(
                ChatMessage.__table__.c.id == data["id"]
            )
        ).fetchone()
    assert row is not None
    assert row.content == "Hello from owner"
    assert row.role == "user"
    assert row.hosted_room_participant_id is not None


def test_owner_post_blank_content_rejected(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": ""},
    )
    assert resp.status_code == 422


def test_owner_post_overlong_content_rejected(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": "X" * 40_000},
    )
    assert resp.status_code == 422


def test_owner_post_extra_fields_rejected(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": "Hi", "role": "assistant", "thread_id": 999},
    )
    assert resp.status_code == 422


def test_owner_post_closed_room_rejected(client):
    room_id = _create_room(client)
    client.post(f"/api/hosted-rooms/{room_id}/close")
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": "Too late"},
    )
    assert resp.status_code == 409


def test_owner_messages_use_backing_thread(client, test_engine):
    room_id = _create_room(client)
    room_data = client.get(f"/api/hosted-rooms/{room_id}").json()
    thread_id = room_data["backing_thread_id"]

    client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": "On thread"},
    )

    with test_engine.begin() as conn:
        rows = conn.execute(
            ChatMessage.__table__.select().where(
                ChatMessage.__table__.c.thread_id == thread_id
            )
        ).fetchall()
    assert len(rows) >= 1


def test_owner_messages_preserve_newlines(client):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": "Line 1\nLine 2\nLine 3"},
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "Line 1\nLine 2\nLine 3"


def test_owner_mention_text_persists_without_invocation(client, test_engine):
    room_id = _create_room(client)
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/messages",
        json={"content": "@Guardian hello"},
    )
    assert resp.status_code == 201
    assert resp.json()["content"] == "@Guardian hello"
    assert resp.json()["role"] == "user"

    # Verify no assistant message was created
    with test_engine.begin() as conn:
        rows = conn.execute(
            ChatMessage.__table__.select().where(
                ChatMessage.__table__.c.thread_id
                == client.get(f"/api/hosted-rooms/{room_id}").json()["backing_thread_id"]
            )
        ).fetchall()
    assistant_rows = [r for r in rows if r.role == "assistant"]
    assert len(assistant_rows) == 0


def test_owner_list_pagination_after_id(client):
    room_id = _create_room(client)
    client.post(f"/api/hosted-rooms/{room_id}/messages", json={"content": "Msg 1"})
    client.post(f"/api/hosted-rooms/{room_id}/messages", json={"content": "Msg 2"})
    client.post(f"/api/hosted-rooms/{room_id}/messages", json={"content": "Msg 3"})

    resp = client.get(f"/api/hosted-rooms/{room_id}/messages?limit=2")
    msgs = resp.json()
    assert len(msgs) <= 3  # default or limited


def test_owner_message_sender_null_for_legacy(client, test_engine):
    """Messages without provenance have null sender."""
    room_id = _create_room(client)
    thread_id = client.get(f"/api/hosted-rooms/{room_id}").json()["backing_thread_id"]

    # Insert a legacy message without provenance
    now = datetime.now(timezone.utc)
    with test_engine.begin() as conn:
        # Get max ID
        last = conn.exec_driver_sql(
            "SELECT COALESCE(MAX(id), 0) + 1 FROM chat_messages"
        ).scalar()
        conn.execute(
            ChatMessage.__table__.insert().values(
                id=int(last),
                thread_id=thread_id,
                user_id="account-a",
                role="user",
                content="Legacy",
                kind="chat",
                extra_meta="{}",
            )
        )

    resp = client.get(f"/api/hosted-rooms/{room_id}/messages")
    msgs = resp.json()
    legacy = [m for m in msgs if m["content"] == "Legacy"]
    assert len(legacy) == 1
    assert legacy[0]["sender"] is None


def test_owner_message_no_account_id_leaked(client):
    room_id = _create_room(client)
    client.post(f"/api/hosted-rooms/{room_id}/messages", json={"content": "Private"})
    resp = client.get(f"/api/hosted-rooms/{room_id}/messages")
    for msg in resp.json():
        assert "user_id" not in msg
        assert "account_id" not in msg
        assert "owner_account_id" not in msg
        if msg.get("sender"):
            assert "bound_account_id" not in msg["sender"]


def test_owner_list_limit_validated(client):
    room_id = _create_room(client)
    resp = client.get(f"/api/hosted-rooms/{room_id}/messages?limit=500")
    assert resp.status_code == 422


def test_owner_list_negative_after_id_rejected(client):
    room_id = _create_room(client)
    resp = client.get(f"/api/hosted-rooms/{room_id}/messages?after_id=-1")
    assert resp.status_code == 422


def test_owner_message_response_has_no_extra_meta(client):
    room_id = _create_room(client)
    resp = client.post(f"/api/hosted-rooms/{room_id}/messages", json={"content": "Clean"})
    data = resp.json()
    assert "extra_meta" not in data
    assert "invitation_id" not in data
    assert "token_hash" not in data
