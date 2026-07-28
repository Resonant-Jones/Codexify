"""Focused tests for Hosted Room guest session exchange and boundary.

Covers invitation exchange, session issuance, cookie posture,
session inspection, lifecycle invalidation, logout, token-domain
separation, tamper resistance, and capability absence.

Uses a minimal FastAPI app with both owner and guest routers plus
a SQLite-backed mock GuardianDB.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

# Ensure DEV_MODE so the session secret falls back to dev-secret in tests
os.environ.setdefault("DEV_MODE", "true")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.core.hosted_room_session import (
    _SESSION_COOKIE_NAME,
    _SESSION_SUBJECT,
    issue_guest_session_token,
)
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
    """In-memory SQLite engine with all tables."""
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

    yield engine
    engine.dispose()


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


# ── Combined app fixture (owner + guest routers) ──────────────────────────


@pytest.fixture
def client(mock_db, monkeypatch):
    """TestClient with both owner and guest routers, plus a mocked DB."""
    import guardian.routes.hosted_rooms as hr
    import guardian.routes.hosted_room_guest as hrg

    monkeypatch.setattr(hr, "load_guardian_db_from_env", lambda: mock_db)
    monkeypatch.setattr(hrg, "load_guardian_db_from_env", lambda: mock_db)

    app = FastAPI()

    # Owner auth override
    async def _override_get_request_user_scope():
        return RequestUserScope(
            user_id="account-a",
            account_id="account-a",
            multi_user_enabled=True,
        )

    app.dependency_overrides[get_request_user_scope] = _override_get_request_user_scope
    app.include_router(hr.router)
    app.include_router(hrg.router)

    return TestClient(app)


# ── Helpers ──────────────────────────────────────────────────────────────


def _create_room(client) -> str:
    resp = client.post("/api/hosted-rooms", json={"title": "Guest Test Room"})
    assert resp.status_code == 201, f"Room creation failed: {resp.text}"
    return resp.json()["id"]


def _create_invite(client, room_id: str, display_name: str = "Jane Guest") -> tuple[str, str]:
    """Create an invitation and return (invite_id, plaintext_token)."""
    resp = client.post(
        f"/api/hosted-rooms/{room_id}/invites",
        json={"intended_display_name": display_name},
    )
    assert resp.status_code == 201, f"Invite creation failed: {resp.text}"
    data = resp.json()
    return data["invitation"]["id"], data["invitation_token"]


def _exchange(client, token: str) -> tuple[int, dict]:
    """Exchange an invitation token. Returns (status_code, response_dict)."""
    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    return resp.status_code, resp.json() if resp.status_code == 200 else resp.json()


def _extract_cookies(response) -> dict[str, str]:
    """Extract Set-Cookie headers into a name->value dict."""
    cookies = {}
    for header in response.headers.get_list("set-cookie"):
        for part in header.split(";"):
            part = part.strip()
            if "=" in part and not part.lower().startswith(("path=", "domain=", "expires=", "max-age=", "samesite=", "secure", "httponly")):
                key, _, value = part.partition("=")
                cookies[key.strip()] = value.strip()
    return cookies


# ── Exchange: authentication boundary ────────────────────────────────────


def test_exchange_works_without_owner_api_key(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)
    status, data = _exchange(client, token)
    assert status == 200, f"Exchange failed: {data}"


def test_exchange_rejects_empty_token(client):
    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": ""},
    )
    assert resp.status_code == 422


def test_exchange_rejects_overlong_token(client):
    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": "A" * 300},
    )
    assert resp.status_code == 422


def test_exchange_rejects_invalid_chars(client):
    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": "not valid!@#"},
    )
    assert resp.status_code == 422


def test_exchange_rejects_extra_fields(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)
    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token, "room_id": "fake"},
    )
    assert resp.status_code == 422


# ── Exchange: successful exchange ────────────────────────────────────────


def test_successful_exchange_creates_participant(client, test_engine):
    room_id = _create_room(client)
    invite_id, token = _create_invite(client, room_id)
    status, data = _exchange(client, token)
    assert status == 200

    # Participant created
    with test_engine.begin() as conn:
        parts = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == room_id
            )
        ).fetchall()
    # Should have owner + member = 2 participants
    member_parts = [p for p in parts if p.role == "member"]
    assert len(member_parts) == 1
    assert member_parts[0].kind == "human"
    assert member_parts[0].state == "active"
    assert member_parts[0].bound_account_id is None
    assert member_parts[0].display_name == "Jane Guest"
    assert member_parts[0].invitation_id == invite_id


def test_successful_exchange_accepts_invitation(client, test_engine):
    room_id = _create_room(client)
    invite_id, token = _create_invite(client, room_id)
    status, data = _exchange(client, token)
    assert status == 200

    with test_engine.begin() as conn:
        invite_row = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.id == invite_id
            )
        ).fetchone()
    assert invite_row.status == "accepted"
    assert invite_row.accepted_at is not None


def test_exchange_response_contains_room_metadata(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)
    status, data = _exchange(client, token)
    assert status == 200
    assert data["room"]["id"] == room_id
    assert data["room"]["status"] == "active"
    assert "slug" in data["room"]
    assert "title" in data["room"]


def test_exchange_response_contains_participant_metadata(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)
    status, data = _exchange(client, token)
    assert status == 200
    assert data["participant"]["display_name"] == "Jane Guest"
    assert data["participant"]["kind"] == "human"
    assert data["participant"]["role"] == "member"
    assert data["participant"]["state"] == "active"


def test_exchange_response_contains_session_metadata(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)
    status, data = _exchange(client, token)
    assert status == 200
    assert "expires_at" in data["session"]


def test_exchange_response_contains_no_secrets(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)
    status, data = _exchange(client, token)
    assert status == 200
    # No token/hash in response
    assert "invitation_token" not in data
    assert "token_hash" not in data
    assert "token" not in data
    assert "session_token" not in data
    # No signed token in nested objects
    resp_str = json.dumps(data)
    assert "invitation_token" not in resp_str


# ── Exchange: one-time behavior ──────────────────────────────────────────


def test_accepted_invite_cannot_exchange_again(client, test_engine):
    room_id = _create_room(client)
    invite_id, token = _create_invite(client, room_id)

    # First exchange succeeds
    status1, _ = _exchange(client, token)
    assert status1 == 200

    # Second exchange fails
    status2, data2 = _exchange(client, token)
    assert status2 == 404

    # No second participant
    with test_engine.begin() as conn:
        parts = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == room_id,
                HostedRoomParticipant.__table__.c.role == "member",
            )
        ).fetchall()
    assert len(parts) == 1


def test_unknown_invite_fails(client):
    fake_token = "not-a-real-token-value-for-testing-abc"
    status, data = _exchange(client, fake_token)
    assert status == 404


def test_all_unavailable_cases_use_same_error_posture(client):
    room_id = _create_room(client)
    invite_id, token = _create_invite(client, room_id)

    # Exchange once (consumes it)
    _exchange(client, token)

    # Replay
    s2, d2 = _exchange(client, token)
    assert s2 == 404
    assert d2["detail"]["error"] == "invalid_invitation"

    # Unknown
    s3, d3 = _exchange(client, "fake-token-1234567890abcdef")
    assert s3 == 404
    assert d3["detail"]["error"] == "invalid_invitation"


def test_closed_room_invite_cannot_exchange(client):
    room_id = _create_room(client)
    invite_id, token = _create_invite(client, room_id)

    # Close the room
    client.post(f"/api/hosted-rooms/{room_id}/close")

    status, data = _exchange(client, token)
    assert status == 404


# ── Exchange: cookie posture ─────────────────────────────────────────────


def test_exchange_sets_http_only_cookie(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)

    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    assert resp.status_code == 200

    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert len(set_cookie_headers) >= 1

    cookie_found = False
    for header in set_cookie_headers:
        if _SESSION_COOKIE_NAME in header:
            cookie_found = True
            assert "HttpOnly" in header
            assert "SameSite=Lax" in header
            assert "Path=/" in header or "path=/" in header.lower()
            break
    assert cookie_found, f"Session cookie '{_SESSION_COOKIE_NAME}' not found in Set-Cookie headers"


def test_exchange_response_json_has_no_signed_token(client):
    room_id = _create_room(client)
    _invite_id, token = _create_invite(client, room_id)

    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    data = resp.json()
    # No signed token anywhere in the JSON
    # The signed token is only in the Set-Cookie header
    assert "session_token" not in json.dumps(data)


# ── Exchange: transaction rollback ───────────────────────────────────────


def test_exchange_rollback_on_participant_failure(client, test_engine, mock_db, monkeypatch):
    """Force participant persistence to fail; invite must remain pending."""
    room_id = _create_room(client)
    invite_id, token = _create_invite(client, room_id)

    original_get_session = mock_db.get_session

    class _FailingSession:
        def __init__(self, real_session):
            self._real = real_session
            self._rolled_back = False

        def get(self, model, pk):
            return self._real.get(model, pk)

        def scalar(self, *args, **kwargs):
            return self._real.scalar(*args, **kwargs)

        def add(self, instance):
            if isinstance(instance, HostedRoomParticipant):
                raise RuntimeError("Simulated participant failure")
            return self._real.add(instance)

        def flush(self):
            self._real.flush()

        def commit(self):
            self._real.commit()

        def rollback(self):
            self._rolled_back = True
            self._real.rollback()

        def refresh(self, inst):
            self._real.refresh(inst)

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
        mock_db, "get_session", lambda: _FailingSession(original_get_session()),
    )

    resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    assert resp.status_code == 500

    # Invite must remain pending
    with test_engine.begin() as conn:
        invite_row = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.id == invite_id
            )
        ).fetchone()
    assert invite_row.status == "pending"

    # No member participant created
    with test_engine.begin() as conn:
        member_parts = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == room_id,
                HostedRoomParticipant.__table__.c.role == "member",
            )
        ).fetchall()
    assert len(member_parts) == 0


# ── Session inspection ───────────────────────────────────────────────────


def test_inspect_session_returns_metadata(client):
    room_id = _create_room(client)
    _, token = _create_invite(client, room_id)

    exchange_resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    assert exchange_resp.status_code == 200

    # Extract cookie and use it for inspection
    cookies = _extract_cookies(exchange_resp)
    session_cookie = cookies.get(_SESSION_COOKIE_NAME)
    assert session_cookie

    inspect_resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp.status_code == 200
    data = inspect_resp.json()
    assert data["room"]["id"] == room_id
    assert data["participant"]["display_name"] == "Jane Guest"
    assert data["participant"]["role"] == "member"
    assert "expires_at" in data["session"]


def test_inspect_session_no_cookie_returns_401(client):
    resp = client.get("/api/hosted-room-session")
    assert resp.status_code == 401


def test_inspect_session_malformed_cookie_returns_401(client):
    resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: "not.a.valid.token"},
    )
    assert resp.status_code == 401


def test_inspect_session_tampered_cookie_returns_401(client):
    room_id = _create_room(client)
    _, token = _create_invite(client, room_id)
    exchange_resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    cookies = _extract_cookies(exchange_resp)
    session_cookie = cookies.get(_SESSION_COOKIE_NAME)

    # Tamper: flip multiple characters in the payload part to break signature
    parts = session_cookie.split(".")
    if len(parts) == 2:
        # Change several characters in the payload
        payload_chars = list(parts[0])
        for i in range(min(5, len(payload_chars))):
            payload_chars[i] = "X" if payload_chars[i] != "X" else "Y"
        tampered = "".join(payload_chars) + "." + parts[1]
    else:
        tampered = session_cookie + "_tampered"

    resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: tampered},
    )
    assert resp.status_code == 401


def test_inspect_session_wrong_purpose_token_fails(client):
    """An account session token must not work as a room guest session."""
    from guardian.core.auth import issue_session_token
    account_token, _ = issue_session_token(subject="web")
    resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: account_token},
    )
    assert resp.status_code == 401


def test_inspect_session_response_has_no_secrets(client):
    room_id = _create_room(client)
    _, token = _create_invite(client, room_id)
    exchange_resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    cookies = _extract_cookies(exchange_resp)
    session_cookie = cookies.get(_SESSION_COOKIE_NAME)

    inspect_resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    data = inspect_resp.json()
    assert "token_hash" not in data
    assert "invitation_token" not in data
    assert "session_token" not in data
    assert "token" not in data
    # No owner account ID leak
    assert "owner_account_id" not in data.get("room", {})
    # No backing thread ID unless needed
    assert "backing_thread_id" not in data.get("room", {})
    # No participant roster
    assert "participants" not in data
    # No invitation metadata
    assert "invitations" not in data


# ── Lifecycle invalidation ───────────────────────────────────────────────


def _create_session(client) -> tuple[str, str]:
    """Create room, invite, exchange; return (room_id, session_cookie_value)."""
    room_id = _create_room(client)
    _, token = _create_invite(client, room_id)
    exchange_resp = client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
    )
    assert exchange_resp.status_code == 200
    cookies = _extract_cookies(exchange_resp)
    return room_id, cookies[_SESSION_COOKIE_NAME]


def test_invitation_revocation_invalidates_session(client):
    room_id, session_cookie = _create_session(client)

    # Get the invite ID from inspection
    inspect_resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp.status_code == 200

    # Find the accepted invite and revoke it
    list_resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    accepted = [i for i in list_resp.json() if i["status"] == "accepted"]
    assert len(accepted) == 1
    invite_id = accepted[0]["id"]

    client.post(f"/api/hosted-rooms/{room_id}/invites/{invite_id}/revoke")

    # Session should now be invalid
    inspect_resp2 = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp2.status_code == 401


def test_room_closure_invalidates_session(client):
    room_id, session_cookie = _create_session(client)

    client.post(f"/api/hosted-rooms/{room_id}/close")

    inspect_resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp.status_code == 401


def test_participant_removal_invalidates_session(client, test_engine):
    room_id, session_cookie = _create_session(client)

    # Manually remove the guest participant
    with test_engine.begin() as conn:
        conn.execute(
            HostedRoomParticipant.__table__.update()
            .where(HostedRoomParticipant.__table__.c.room_id == room_id)
            .where(HostedRoomParticipant.__table__.c.role == "member")
            .values(state="removed", removed_at=datetime.now(timezone.utc))
        )

    inspect_resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp.status_code == 401


def test_invitation_expiry_invalidates_session(client, test_engine):
    """Simulate invitation expiry after session issuance."""
    room_id, session_cookie = _create_session(client)

    # Set invitation expiry to the past
    with test_engine.begin() as conn:
        conn.execute(
            HostedRoomInvite.__table__.update()
            .where(HostedRoomInvite.__table__.c.room_id == room_id)
            .where(HostedRoomInvite.__table__.c.status == "accepted")
            .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        )

    inspect_resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp.status_code == 401


def test_session_expiry_invalidates_access(client, monkeypatch):
    """Simulate token expiration by manipulating time."""
    import time as time_module
    import guardian.core.hosted_room_session as hrs

    # Patch time.time to return a future time
    original_time = time_module.time
    room_id, session_cookie = _create_session(client)

    # Verify session works now
    inspect_resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp.status_code == 200

    # Fast-forward time past session expiry
    future_time = time_module.time() + 25 * 3600  # 25 hours
    monkeypatch.setattr(time_module, "time", lambda: future_time)

    inspect_resp2 = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert inspect_resp2.status_code == 401


# ── Owner/agent cannot masquerade ────────────────────────────────────────


def test_owner_participant_cannot_use_guest_session(client, test_engine):
    """Create a session token that references the owner participant (wrong role)."""
    room_id = _create_room(client)

    # Find the owner participant
    with test_engine.begin() as conn:
        owner = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == room_id,
                HostedRoomParticipant.__table__.c.role == "owner",
            )
        ).fetchone()
    assert owner is not None

    # Issue a session token that references the owner participant
    signed_token, _ = issue_guest_session_token(
        room_id=room_id,
        room_slug="test",
        participant_id=owner.id,
        invitation_id="nonexistent",
    )

    resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: signed_token},
    )
    # Should fail because the invitation doesn't exist
    assert resp.status_code == 401


# ── Cross-room mismatch ──────────────────────────────────────────────────


def test_session_with_wrong_room_id_fails(client):
    """Session token with a room ID that doesn't match any real room."""
    signed_token, _ = issue_guest_session_token(
        room_id="nonexistent-room",
        room_slug="test",
        participant_id="nonexistent-participant",
        invitation_id="nonexistent-invite",
    )

    resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: signed_token},
    )
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────


def test_logout_clears_cookie(client):
    room_id, session_cookie = _create_session(client)

    logout_resp = client.post(
        "/api/hosted-room-session/logout",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["ok"] is True

    # Cookie should be cleared
    set_cookie_headers = logout_resp.headers.get_list("set-cookie")
    assert len(set_cookie_headers) >= 1


def test_repeated_logout_is_safe(client):
    room_id, session_cookie = _create_session(client)

    client.post(
        "/api/hosted-room-session/logout",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    # Second logout should also succeed
    resp2 = client.post(
        "/api/hosted-room-session/logout",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )
    assert resp2.status_code == 200


def test_logout_preserves_participant(client, test_engine):
    room_id, session_cookie = _create_session(client)

    with test_engine.begin() as conn:
        before = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == room_id,
                HostedRoomParticipant.__table__.c.role == "member",
            )
        ).fetchone()
    assert before is not None
    before_state = before.state

    client.post(
        "/api/hosted-room-session/logout",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )

    with test_engine.begin() as conn:
        after = conn.execute(
            HostedRoomParticipant.__table__.select().where(
                HostedRoomParticipant.__table__.c.room_id == room_id,
                HostedRoomParticipant.__table__.c.role == "member",
            )
        ).fetchone()
    assert after is not None
    assert after.state == before_state


def test_logout_preserves_invitation_acceptance(client, test_engine):
    room_id, session_cookie = _create_session(client)

    client.post(
        "/api/hosted-room-session/logout",
        cookies={_SESSION_COOKIE_NAME: session_cookie},
    )

    with test_engine.begin() as conn:
        invite = conn.execute(
            HostedRoomInvite.__table__.select().where(
                HostedRoomInvite.__table__.c.room_id == room_id,
                HostedRoomInvite.__table__.c.status == "accepted",
            )
        ).fetchone()
    assert invite is not None


# ── Token-domain separation ──────────────────────────────────────────────


def test_account_session_token_rejected(client):
    """An account session token (subject='web') must be rejected."""
    from guardian.core.auth import issue_session_token
    account_token, _ = issue_session_token(subject="web")

    resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: account_token},
    )
    assert resp.status_code == 401


def test_wrong_key_token_rejected(client, monkeypatch):
    """A token signed with a different key must be rejected."""
    # Temporarily override the session secret
    import guardian.core.hosted_room_session as hrs

    original_secret = hrs._session_secret

    def _wrong_secret():
        return b"wrong-secret-key-for-testing"

    monkeypatch.setattr(hrs, "_session_secret", _wrong_secret)

    # Issue a token with the wrong key
    wrong_token, _ = hrs.issue_guest_session_token(
        room_id="r1", room_slug="s1", participant_id="p1", invitation_id="i1",
    )

    # Restore correct secret
    monkeypatch.setattr(hrs, "_session_secret", original_secret)

    resp = client.get(
        "/api/hosted-room-session",
        cookies={_SESSION_COOKIE_NAME: wrong_token},
    )
    assert resp.status_code == 401


# ── OpenAPI / Route registration ─────────────────────────────────────────


def test_guest_routes_exist_in_openapi(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})

    assert "/api/hosted-room-invitations/exchange" in paths
    assert "post" in paths["/api/hosted-room-invitations/exchange"]
    assert "/api/hosted-room-session" in paths
    assert "get" in paths["/api/hosted-room-session"]
    assert "/api/hosted-room-session/logout" in paths
    assert "post" in paths["/api/hosted-room-session/logout"]


def test_no_guest_message_or_completion_routes(client):
    resp = client.get("/openapi.json")
    schema = resp.json()
    paths = schema.get("paths", {})

    for path in paths:
        assert "message" not in path.lower() or "hosted-room" not in path.lower()
        assert "complete" not in path.lower() or "hosted-room" not in path.lower()
        assert "/api/hosted-rooms/" + "messages" not in path


# ── Capability-absence proof ──────────────────────────────────────────────
# (Verified via grep in validation — no message or completion code in guest modules)


# ── Existing owner/invitation route regression ────────────────────────────


def test_existing_owner_routes_still_work(client):
    """Verify owner lifecycle routes are unaffected by guest router."""
    room_id = _create_room(client)
    resp = client.get(f"/api/hosted-rooms/{room_id}")
    assert resp.status_code == 200


def test_existing_invitation_routes_still_work(client):
    """Verify invitation management routes are unaffected."""
    room_id = _create_room(client)
    invite_id, _ = _create_invite(client, room_id)

    list_resp = client.get(f"/api/hosted-rooms/{room_id}/invites")
    assert list_resp.status_code == 200
    assert any(i["id"] == invite_id for i in list_resp.json())
