"""The five human-admin observability routes have one account principal."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.account_observability.invites import create_invite
from guardian.core import auth_dependencies, dependencies
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AccountObservabilityPresenceSession,
    Base,
    User,
)
from guardian.routes import account_observability as routes
from guardian.routes.admin import require_admin

SECRET = "account-observability-test-session-secret"
CAPABILITY = "account-observability-test-service-key"
ADMIN_ID = "admin@example.com"
GUEST_ID = "guest@example.com"
BASE = "/api/operator/account-observability"
TARGETS = (
    ("create_operator_invite", "POST", f"{BASE}/invites"),
    ("list_operator_invites", "GET", f"{BASE}/invites"),
    (
        "disable_operator_invite",
        "POST",
        f"{BASE}/invites/{{invite_id}}/disable",
    ),
    (
        "revoke_operator_invite",
        "POST",
        f"{BASE}/invites/{{invite_id}}/revoke",
    ),
    ("trigger_retention_cleanup", "POST", f"{BASE}/retention/cleanup"),
)


class _Db:
    def __init__(self) -> None:
        self.events: list[str] | None = None
        self.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                AccountObservabilityInviteLink.__table__,
                AccountObservabilityGuestIdentity.__table__,
                AccountObservabilityAccountMetadata.__table__,
                AccountObservabilityPresenceSession.__table__,
            ],
        )
        self.factory = sessionmaker(bind=self.engine, future=True)

    @contextmanager
    def get_session(self):
        if self.events is not None:
            self.events.append("database")
        session = self.factory()
        try:
            yield session
        finally:
            session.close()


class _SessionStore:
    def __init__(self) -> None:
        self.entries: dict[str, str] = {}
        self.reads: list[str] = []
        self.events: list[str] | None = None

    def store(self, token: str, user_id: str) -> None:
        self.entries[token] = user_id

    def verify(self, token: str) -> str | None:
        self.reads.append(token)
        if self.events is not None:
            self.events.append("session_store")
        return self.entries.get(token)


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", SECRET)
    monkeypatch.setenv("GUARDIAN_API_KEY", CAPABILITY)
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    monkeypatch.delenv("GUARDIAN_API_KEYS", raising=False)
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(GUARDIAN_API_KEY=CAPABILITY, GUARDIAN_API_KEYS=None),
    )
    store = _SessionStore()
    monkeypatch.setattr(auth_dependencies, "get_session_store", lambda: store)
    db = _Db()
    with db.get_session() as session:
        session.add_all(
            [
                User(
                    id=ADMIN_ID,
                    username=ADMIN_ID,
                    email=ADMIN_ID,
                    password_hash="unused",
                    role="admin",
                ),
                User(
                    id=GUEST_ID,
                    username=GUEST_ID,
                    email=GUEST_ID,
                    password_hash="unused",
                    role="guest",
                ),
            ]
        )
        session.flush()
        row, _ = create_invite(session, created_by_user_id=ADMIN_ID, name="Seed")
        invite_id = row.invite_id
        session.commit()
    monkeypatch.setattr(routes, "_db", None)
    monkeypatch.setattr(routes, "load_guardian_db_from_env", lambda: db)
    app = FastAPI()
    app.include_router(routes.router)
    # The repository TestClient can seed a key globally; each case must name it.
    client = TestClient(app, headers={"X-API-Key": ""})
    yield SimpleNamespace(
        app=app, client=client, db=db, store=store, invite_id=invite_id
    )
    db.engine.dispose()


def _account_token(
    boundary,
    account_id: str,
    *,
    purpose: str = ACCOUNT_SESSION_PURPOSE,
    ttl_seconds: int = 60,
) -> str:
    token, _ = issue_session_token(
        subject=account_id, purpose=purpose, ttl_seconds=ttl_seconds
    )
    # Deliberately store wrong-purpose and expired tokens too: a store hit may
    # never repair their credential class or expiry.
    boundary.store.store(token, account_id)
    return token


def _legacy_token(boundary) -> str:
    claims = {
        "subject": ADMIN_ID,
        "nonce": "legacy-nonce",
        "exp": 4_000_000_000,
    }
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(SECRET.encode(), payload, hashlib.sha256).digest()
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    token = f"{encode(payload)}.{encode(signature)}"
    boundary.store.store(token, ADMIN_ID)
    return token


def _request(boundary, target, *, headers=None, cookies=None):
    _name, method, path = target
    path = path.format(invite_id=boundary.invite_id)
    kwargs = {"headers": headers or {}, "cookies": cookies or {}}
    if target[0] == "create_operator_invite":
        kwargs["json"] = {"name": "Qualified invite"}
    if target[0] == "trigger_retention_cleanup":
        kwargs["params"] = {"dry_run": "true"}
    return boundary.client.request(method, path, **kwargs)


def _dependency_calls(route: APIRoute) -> set[object]:
    calls: set[object] = set()

    def visit(node):
        for child in node.dependencies:
            calls.add(child.call)
            visit(child)

    visit(route.dependant)
    return calls


def test_exactly_five_routes_use_the_account_admin_capability_boundary():
    expected = {(method, path, name) for name, method, path in TARGETS}
    actual = set()
    for route in routes.router.routes:
        if not isinstance(route, APIRoute):
            continue
        calls = _dependency_calls(route)
        if routes._account_admin_capability_dependencies not in calls:
            continue
        actual.update(
            (method, route.path, route.endpoint.__name__) for method in route.methods
        )
        assert routes._require_account_admin in calls
        assert dependencies.require_service_capability in calls
        assert dependencies.require_service_api_key in calls
        assert dependencies.require_api_key not in calls
        assert dependencies.require_operator_auth not in calls
        assert dependencies.get_current_user not in calls
        assert require_admin not in calls
    assert actual == expected


def test_service_capability_is_non_principal_and_header_only(boundary):
    app = FastAPI()

    @app.get("/capability")
    def check_capability(
        result: None = Depends(dependencies.require_service_capability),
    ):
        return {"principal": result}

    client = TestClient(app, headers={"X-API-Key": ""})
    assert client.get("/capability", headers={"X-API-Key": CAPABILITY}).json() == {
        "principal": None
    }
    assert boundary.store.reads == []
    assert client.get("/capability").status_code == 401
    assert client.get("/capability", headers={"X-API-Key": "wrong"}).status_code == 401

    account = _account_token(boundary, ADMIN_ID)
    operator = _account_token(boundary, ADMIN_ID, purpose=OPERATOR_SESSION_PURPOSE)
    guest, _ = issue_guest_session_token(
        room_id="room", room_slug="room", participant_id="guest", invitation_id="invite"
    )
    for signed in (account, operator, guest):
        assert (
            client.get("/capability", headers={"X-API-Key": signed}).status_code == 401
        )
        assert (
            client.get(
                "/capability", headers={"Authorization": f"Bearer {signed}"}
            ).status_code
            == 401
        )
    assert boundary.store.reads == []


@pytest.mark.parametrize("target", TARGETS, ids=lambda item: item[0])
def test_admin_account_with_capability_reaches_each_operation(boundary, target):
    token = _account_token(boundary, ADMIN_ID)
    response = _request(
        boundary,
        target,
        headers={"Authorization": f"Bearer {token}", "X-API-Key": CAPABILITY},
    )
    assert response.status_code == (
        201 if target[0] == "create_operator_invite" else 200
    ), response.text
    if target[0] == "create_operator_invite":
        assert response.json()["created_by_user_id"] == ADMIN_ID


DENIED_CASES = (
    ("non_admin", 403),
    ("admin_missing_capability", 401),
    ("admin_invalid_capability", 401),
    ("capability_only", 401),
    ("operator_only", 401),
    ("operator_with_capability", 401),
    ("admin_token_only", 401),
    ("admin_token_with_capability", 401),
    ("debug_bypass_with_capability", 401),
    ("guest_cookie_with_capability", 401),
    ("guest_bearer_with_capability", 401),
    ("legacy_with_capability", 401),
    ("wrong_purpose_with_capability", 401),
    ("malformed_with_capability", 401),
    ("expired_with_capability", 401),
)


@pytest.mark.parametrize("target", TARGETS, ids=lambda item: item[0])
@pytest.mark.parametrize(
    "case,expected_status", DENIED_CASES, ids=lambda item: str(item)
)
def test_every_operation_denies_missing_or_wrong_authority(
    boundary, monkeypatch, target, case, expected_status
):
    headers: dict[str, str] = {}
    cookies: dict[str, str] = {}
    if case in {"admin_missing_capability", "admin_invalid_capability", "non_admin"}:
        user = GUEST_ID if case == "non_admin" else ADMIN_ID
        token = _account_token(boundary, user)
        headers["Authorization"] = f"Bearer {token}"
    if case == "operator_only" or case == "operator_with_capability":
        token = _account_token(boundary, ADMIN_ID, purpose=OPERATOR_SESSION_PURPOSE)
        headers["Authorization"] = f"Bearer {token}"
    if case.startswith("admin_token"):
        monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "admin-token")
        headers["X-Admin-Token"] = "admin-token"
    if case == "debug_bypass_with_capability":
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("GUARDIAN_DEV_MODE", "true")
        monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    if case.startswith("guest_"):
        guest, _ = issue_guest_session_token(
            room_id="room",
            room_slug="room",
            participant_id="guest",
            invitation_id="invite",
        )
        if case == "guest_cookie_with_capability":
            cookies["codexify_hosted_room_session"] = guest
        else:
            headers["Authorization"] = f"Bearer {guest}"
    if case == "legacy_with_capability":
        headers["Authorization"] = f"Bearer {_legacy_token(boundary)}"
    if case == "wrong_purpose_with_capability":
        wrong = _account_token(boundary, ADMIN_ID, purpose="unrelated_purpose")
        headers["Authorization"] = f"Bearer {wrong}"
    if case == "malformed_with_capability":
        headers["Authorization"] = "Bearer malformed"
    if case == "expired_with_capability":
        expired = _account_token(boundary, ADMIN_ID, ttl_seconds=-60)
        headers["Authorization"] = f"Bearer {expired}"
    if case not in {"admin_missing_capability", "operator_only", "admin_token_only"}:
        headers["X-API-Key"] = (
            "invalid-capability" if case == "admin_invalid_capability" else CAPABILITY
        )
    response = _request(boundary, target, headers=headers, cookies=cookies)
    assert response.status_code == expected_status, (case, target[0], response.text)
    if case in {
        "capability_only",
        "operator_only",
        "operator_with_capability",
        "admin_token_only",
        "admin_token_with_capability",
        "debug_bypass_with_capability",
        "guest_cookie_with_capability",
        "guest_bearer_with_capability",
        "legacy_with_capability",
        "wrong_purpose_with_capability",
        "malformed_with_capability",
        "expired_with_capability",
    }:
        assert boundary.store.reads == []


def test_gate_order_precedes_business_logic(boundary, monkeypatch):
    events: list[str] = []
    boundary.store.events = events
    boundary.db.events = events
    original_purpose_check = routes.verify_session_token_for_purpose
    original_settings = dependencies.get_settings

    def check_purpose(token, purpose):
        events.append("purpose")
        return original_purpose_check(token, purpose)

    def settings():
        events.append("capability")
        return original_settings()

    def list_business(session):
        events.append("business")
        return []

    monkeypatch.setattr(routes, "verify_session_token_for_purpose", check_purpose)
    monkeypatch.setattr(dependencies, "get_settings", settings)
    monkeypatch.setattr(routes, "list_invites", list_business)
    admin = _account_token(boundary, ADMIN_ID)
    response = _request(
        boundary,
        TARGETS[1],
        headers={"Authorization": f"Bearer {admin}", "X-API-Key": CAPABILITY},
    )
    assert response.status_code == 200
    assert events.index("purpose") < events.index("session_store")
    assert events.index("session_store") < events.index("database")
    assert events.index("database") < events.index("capability")
    assert events.index("capability") < events.index("business")

    events.clear()
    non_admin = _account_token(boundary, GUEST_ID)
    assert (
        _request(
            boundary,
            TARGETS[1],
            headers={"Authorization": f"Bearer {non_admin}", "X-API-Key": CAPABILITY},
        ).status_code
        == 403
    )
    assert "capability" not in events and "business" not in events

    events.clear()
    assert (
        _request(boundary, TARGETS[1], headers={"X-API-Key": CAPABILITY}).status_code
        == 401
    )
    assert "session_store" not in events and "capability" not in events
    assert "business" not in events


def test_invite_audit_actor_is_the_canonical_human_account(boundary, monkeypatch):
    actors: list[str] = []

    def capture_audit(session, **kwargs):
        actors.append(kwargs["actor_id"])

    monkeypatch.setattr(routes, "record_invite_audit", capture_audit)
    admin = _account_token(boundary, ADMIN_ID)
    response = _request(
        boundary,
        TARGETS[0],
        headers={
            "Authorization": f"Bearer {admin}",
            "X-API-Key": CAPABILITY,
            "X-User-Id": GUEST_ID,
        },
    )
    assert response.status_code == 201
    assert response.json()["created_by_user_id"] == ADMIN_ID
    assert actors == [ADMIN_ID]


def test_cookie_session_and_current_preview_admin_policy(boundary, monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", ADMIN_ID)
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", f"{ADMIN_ID},{GUEST_ID}")
    admin = _account_token(boundary, ADMIN_ID)
    response = _request(
        boundary,
        TARGETS[1],
        headers={"X-API-Key": CAPABILITY},
        cookies={"gc_session": admin},
    )
    assert response.status_code == 200

    # A current allowlist removal revokes the preview admin permission even
    # while the account row and approved session are still present.
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", "")
    assert (
        _request(
            boundary,
            TARGETS[1],
            headers={"X-API-Key": CAPABILITY},
            cookies={"gc_session": admin},
        ).status_code
        == 403
    )
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", GUEST_ID)
    assert (
        _request(
            boundary,
            TARGETS[1],
            headers={"X-API-Key": CAPABILITY},
            cookies={"gc_session": admin},
        ).status_code
        == 401
    )

    # The preview email policy cannot elevate a canonical guest account.
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", GUEST_ID)
    guest = _account_token(boundary, GUEST_ID)
    assert (
        _request(
            boundary,
            TARGETS[1],
            headers={"X-API-Key": CAPABILITY},
            cookies={"gc_session": guest},
        ).status_code
        == 403
    )


def test_session_store_mapping_cannot_change_signed_account_subject(boundary):
    admin = _account_token(boundary, ADMIN_ID)
    boundary.store.store(admin, GUEST_ID)
    response = _request(
        boundary,
        TARGETS[1],
        headers={"Authorization": f"Bearer {admin}", "X-API-Key": CAPABILITY},
    )
    assert response.status_code == 401


def test_retention_reaches_service_only_after_human_admin_and_capability(
    boundary, monkeypatch
):
    from guardian.account_observability.retention import CleanupReceipt

    calls: list[bool] = []
    now = datetime.now(timezone.utc)

    def cleanup(session, *, dry_run):
        calls.append(dry_run)
        return CleanupReceipt(
            execution_timestamp=now,
            cutoff_presence_30d=now,
            cutoff_idle_30m=now,
            cutoff_guest_lineage_90d=now,
            dry_run=dry_run,
        )

    monkeypatch.setattr(routes, "run_cleanup", cleanup)
    admin = _account_token(boundary, ADMIN_ID)
    valid = {"Authorization": f"Bearer {admin}", "X-API-Key": CAPABILITY}
    assert _request(boundary, TARGETS[4], headers=valid).status_code == 200
    assert calls == [True]
    assert (
        _request(boundary, TARGETS[4], headers={"X-API-Key": CAPABILITY}).status_code
        == 401
    )
    assert calls == [True]
