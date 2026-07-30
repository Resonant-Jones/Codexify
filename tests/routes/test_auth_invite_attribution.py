from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_observability.invites import create_invite, resolve_invite
from guardian.account_observability.tokens import ATTRIBUTION_COOKIE_NAME
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    Base,
    User,
)


class _AuthDb:
    def __init__(self):
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        tables = [
            User.__table__,
            AccountObservabilityInviteLink.__table__,
            AccountObservabilityGuestIdentity.__table__,
            AccountObservabilityAccountMetadata.__table__,
        ]
        Base.metadata.create_all(self.engine, tables=tables)
        self.factory = sessionmaker(bind=self.engine, future=True)

    @contextmanager
    def get_session(self):
        session = self.factory()
        try:
            yield session
        finally:
            session.close()


def _client(monkeypatch, db: _AuthDb) -> TestClient:
    from guardian.routes import auth

    app = FastAPI()
    app.include_router(auth.router)
    monkeypatch.setattr(auth, "load_guardian_db_from_env", lambda: db)
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-session-secret")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    return TestClient(app)


def _seed_invite_guest(db: _AuthDb) -> tuple[str, str]:
    now = datetime(2026, 7, 24, 16, 0, tzinfo=timezone.utc)
    with db.get_session() as session:
        session.add(
            User(
                id="operator",
                username="operator",
                password_hash="not-used",
                role="admin",
                created_at=now,
            )
        )
        session.commit()
        invite, token = create_invite(
            session,
            created_by_user_id="operator",
            name="Wave",
            now=now,
        )
        session.commit()
        resolution = resolve_invite(
            session, token=token, guest_cookie=None, now=now
        )
        session.commit()
        return resolution.guest_id, invite.invite_id


def test_registration_gate_remains_private_preview_only(monkeypatch):
    db = _AuthDb()
    client = _client(monkeypatch, db)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    response = client.post(
        "/auth/register",
        json={"username": "alice@example.com", "password": "secret"},
    )
    assert response.status_code == 404


def test_eligible_registration_creates_unattributed_metadata(monkeypatch):
    db = _AuthDb()
    client = _client(monkeypatch, db)
    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret"},
    )
    assert response.status_code == 200
    with db.get_session() as session:
        metadata = session.get(AccountObservabilityAccountMetadata, "alice")
        assert metadata is not None
        assert metadata.acquisition_invite_id is None
        assert metadata.attribution_method is None
        assert metadata.attribution_confidence is None


def test_registration_with_guest_lineage_persists_first_touch(monkeypatch):
    db = _AuthDb()
    guest_id, invite_id = _seed_invite_guest(db)
    client = _client(monkeypatch, db)
    client.cookies.set(ATTRIBUTION_COOKIE_NAME, guest_id)

    response = client.post(
        "/auth/register",
        json={"username": "alice", "password": "secret"},
    )
    assert response.status_code == 200
    with db.get_session() as session:
        metadata = session.get(AccountObservabilityAccountMetadata, "alice")
        guest = session.get(AccountObservabilityGuestIdentity, guest_id)
        assert metadata.acquisition_invite_id == invite_id
        assert metadata.prior_guest_id == guest_id
        assert metadata.attribution_method == "first_party_first_touch"
        assert metadata.attribution_confidence == "verified"
        assert guest.converted_at is not None


def test_guest_id_is_not_accepted_from_registration_body(monkeypatch):
    db = _AuthDb()
    client = _client(monkeypatch, db)
    response = client.post(
        "/auth/register",
        json={
            "username": "alice",
            "password": "secret",
            "guest_id": "caller-selected-guest",
        },
    )
    assert response.status_code == 200
    with db.get_session() as session:
        metadata = session.get(AccountObservabilityAccountMetadata, "alice")
        assert metadata.prior_guest_id is None
        assert (
            session.get(
                AccountObservabilityGuestIdentity, "caller-selected-guest"
            )
            is None
        )


def test_attribution_failure_does_not_fail_canonical_registration(monkeypatch):
    db = _AuthDb()
    client = _client(monkeypatch, db)
    from guardian.routes import auth

    with patch.object(
        auth,
        "complete_registration_attribution",
        side_effect=RuntimeError("observability unavailable"),
    ):
        response = client.post(
            "/auth/register",
            json={"username": "alice", "password": "secret"},
        )
    assert response.status_code == 200
    with db.get_session() as session:
        assert session.get(User, "alice") is not None
        assert session.get(AccountObservabilityAccountMetadata, "alice") is None


def test_login_behavior_remains_unchanged_after_registration(monkeypatch):
    db = _AuthDb()
    client = _client(monkeypatch, db)
    assert (
        client.post(
            "/auth/register", json={"username": "alice", "password": "secret"}
        ).status_code
        == 200
    )
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "secret"}
    )
    assert login.status_code == 200
    assert login.json()["user_id"] == "alice"
    assert login.json()["token"]
