from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    Base,
    User,
)


class _TestDb:
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


def _app(monkeypatch, db: _TestDb) -> tuple[FastAPI, TestClient]:
    from guardian.routes import account_observability as routes

    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes._operator_dependencies] = lambda: (
        "service",
        "admin_token",
        "operator",
    )
    monkeypatch.setattr(routes, "load_guardian_db_from_env", lambda: db)
    monkeypatch.setattr(routes, "_session_cookie_secure_flag", lambda: True)
    return app, TestClient(app)


def _auth_user(db: _TestDb) -> None:
    with db.get_session() as session:
        session.add(
            User(
                id="operator",
                username="operator",
                password_hash="not-used",
                role="admin",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()


def test_operator_authorization_is_required(monkeypatch):
    from guardian.core.dependencies import require_api_key
    from guardian.routes import account_observability as routes

    monkeypatch.setenv("GUARDIAN_API_KEY", "service-key")
    monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "admin-key")
    monkeypatch.setenv("DEBUG", "false")
    db = _TestDb()
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[require_api_key] = lambda: "service-key"
    monkeypatch.setattr(routes, "load_guardian_db_from_env", lambda: db)

    response = TestClient(app).get(
        "/api/operator/account-observability/invites",
        headers={"X-API-Key": "service-key"},
    )
    assert response.status_code == 403


def test_service_credential_alone_cannot_impersonate_operator(monkeypatch):
    from guardian.core.dependencies import require_api_key
    from guardian.routes import account_observability as routes

    monkeypatch.setenv("GUARDIAN_API_KEY", "service-key")
    monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "admin-key")
    monkeypatch.setenv("DEBUG", "false")
    db = _TestDb()
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[require_api_key] = lambda: "service-key"
    monkeypatch.setattr(routes, "load_guardian_db_from_env", lambda: db)

    response = TestClient(app).post(
        "/api/operator/account-observability/invites",
        headers={"X-API-Key": "service-key"},
        json={"name": "Wave"},
    )
    assert response.status_code == 403


def test_creation_returns_raw_token_once_and_list_redacts_it(monkeypatch):
    db = _TestDb()
    _auth_user(db)
    _, client = _app(monkeypatch, db)

    created = client.post(
        "/api/operator/account-observability/invites",
        json={"name": "Wave", "campaign_label": "summer"},
    )
    assert created.status_code == 201
    payload = created.json()
    raw_token = payload["raw_token"]
    assert raw_token
    assert payload["invite_fragment"] == f"#invite={raw_token}"
    assert "token_hash" not in payload

    listed = client.get("/api/operator/account-observability/invites")
    assert listed.status_code == 200
    listed_text = listed.text
    assert raw_token not in listed_text
    assert "token_hash" not in listed_text


def test_disable_and_revoke_enforce_lifecycle_transitions(monkeypatch):
    db = _TestDb()
    _auth_user(db)
    _, client = _app(monkeypatch, db)
    created = client.post(
        "/api/operator/account-observability/invites", json={"name": "Wave"}
    ).json()
    invite_id = created["invite_id"]

    disabled = client.post(
        f"/api/operator/account-observability/invites/{invite_id}/disable"
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "disabled"

    revoked = client.post(
        f"/api/operator/account-observability/invites/{invite_id}/revoke"
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    repeated = client.post(
        f"/api/operator/account-observability/invites/{invite_id}/revoke"
    )
    assert repeated.status_code == 409


def test_public_resolver_is_json_post_only_and_sets_host_cookie(monkeypatch):
    db = _TestDb()
    _auth_user(db)
    _, client = _app(monkeypatch, db)
    created = client.post(
        "/api/operator/account-observability/invites", json={"name": "Wave"}
    ).json()
    token = created["raw_token"]

    resolved = client.post(
        "/api/account-observability/invites/resolve", json={"token": token}
    )
    assert resolved.status_code == 200
    assert resolved.json() == {"result": "attributed", "error": None}
    cookie = resolved.headers["set-cookie"]
    assert "codexify_guest_attribution=" in cookie
    assert "Max-Age=7776000" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert "Secure" in cookie
    assert "Domain=" not in cookie

    get_routes = {
        route.path
        for route in client.app.routes
        if "GET" in getattr(route, "methods", set())
    }
    assert "/api/account-observability/invites/resolve" not in get_routes
    assert (
        client.get(
            f"/api/account-observability/invites/resolve?token={token}"
        ).status_code
        == 405
    )


def test_public_unavailable_results_are_generic_and_create_no_guest(
    monkeypatch,
):
    db = _TestDb()
    _auth_user(db)
    _, client = _app(monkeypatch, db)
    created = client.post(
        "/api/operator/account-observability/invites", json={"name": "Wave"}
    ).json()
    token = created["raw_token"]
    invite_id = created["invite_id"]

    invalid = client.post(
        "/api/account-observability/invites/resolve", json={"token": "unknown"}
    )
    assert invalid.status_code == 404
    assert invalid.json() == {"error": "invite_unavailable"}

    disabled = client.post(
        f"/api/operator/account-observability/invites/{invite_id}/disable"
    )
    assert disabled.status_code == 200
    disabled_result = client.post(
        "/api/account-observability/invites/resolve", json={"token": token}
    )
    assert disabled_result.status_code == invalid.status_code
    assert disabled_result.json() == invalid.json()

    second_created = client.post(
        "/api/operator/account-observability/invites", json={"name": "Second"}
    ).json()
    second_token = second_created["raw_token"]
    second_id = second_created["invite_id"]
    assert (
        client.post(
            f"/api/operator/account-observability/invites/{second_id}/revoke"
        ).status_code
        == 200
    )
    revoked_result = client.post(
        "/api/account-observability/invites/resolve",
        json={"token": second_token},
    )
    assert revoked_result.status_code == invalid.status_code
    assert revoked_result.json() == invalid.json()

    with db.get_session() as session:
        row = session.get(AccountObservabilityInviteLink, invite_id)
        row.status = "active"
        row.disabled_at = None
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    expired_result = client.post(
        "/api/account-observability/invites/resolve", json={"token": token}
    )
    assert expired_result.status_code == invalid.status_code
    assert expired_result.json() == invalid.json()
    with db.get_session() as session:
        assert session.query(AccountObservabilityGuestIdentity).count() == 0


def test_raw_token_does_not_appear_in_logs_or_audit_warning(
    monkeypatch, caplog
):
    db = _TestDb()
    _auth_user(db)
    _, client = _app(monkeypatch, db)
    with caplog.at_level("WARNING"):
        created = client.post(
            "/api/operator/account-observability/invites", json={"name": "Wave"}
        ).json()
    raw_token = created["raw_token"]
    assert all(
        raw_token not in record.getMessage() for record in caplog.records
    )
    assert (
        raw_token
        not in client.get("/api/operator/account-observability/invites").text
    )
