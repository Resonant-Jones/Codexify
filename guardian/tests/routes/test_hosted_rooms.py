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
