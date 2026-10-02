from __future__ import annotations

import base64
import hashlib
import hmac
import json
from http.cookies import SimpleCookie
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
    verify_session_token_for_purpose,
)
from guardian.core.dependencies import require_operator_auth
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.db.models import User


class _AuthDb:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        User.__table__.create(engine)
        self._session_factory = sessionmaker(bind=engine, future=True)

    @contextmanager
    def get_session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()


class _MemorySessionStore:
    def __init__(self) -> None:
        self.entries: dict[str, str] = {}

    def store(self, token: str, user_id: str, ttl: int) -> None:
        self.entries[token] = user_id


def _decode_claims(token: str) -> dict[str, object]:
    payload = token.split(".", 1)[0]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))


def _sign_claims(claims: dict[str, object], secret: str) -> str:
    payload = json.dumps(
        claims, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    return f"{encode(payload)}.{encode(signature)}"


def _continuity_app() -> FastAPI:
    from guardian.routes.continuity_operator import router

    app = FastAPI()
    app.include_router(router)
    return app


def _valid_payload() -> dict[str, object]:
    return {
        "action_id": "operator-session-test",
        "actor_id": "operator-test",
        "packet_id": "packet-test",
        "created_at": "2026-09-26T00:00:00Z",
        "summary": "Operator session boundary test",
        "payload": {"test": True},
        "project_id": "project-test",
    }


def _mock_receipt():
    from guardian.continuity.write_actions import ContinuityWriteReceipt

    return ContinuityWriteReceipt(
        action_id="operator-session-test",
        action_kind="create_reality_stamp",
        success=True,
        created_packet_ids=("packet-created",),
        created_at="2026-09-26T00:00:00Z",
    )


def test_issuer_requires_explicit_purpose_and_signs_canonical_claims(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "operator-boundary-secret")
    with pytest.raises(TypeError):
        issue_session_token(subject="account-a")  # type: ignore[call-arg]

    token, expires_at = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE, ttl_seconds=60
    )
    claims = _decode_claims(token)
    assert claims["subject"] == "account-a"
    assert claims["purpose"] == ACCOUNT_SESSION_PURPOSE
    assert claims["nonce"]
    assert claims["exp"] == expires_at
    assert verify_session_token_for_purpose(token, ACCOUNT_SESSION_PURPOSE)
    assert not verify_session_token_for_purpose(token, OPERATOR_SESSION_PURPOSE)


def test_canonical_login_emits_account_session_and_stores_account_mapping(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "operator-boundary-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "operator-boundary-api-key")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    auth_db = _AuthDb()
    store = _MemorySessionStore()

    from guardian.routes import auth as auth_routes

    app = FastAPI()
    app.include_router(auth_routes.router)
    with (
        patch.object(auth_routes, "load_guardian_db_from_env", return_value=auth_db),
        patch.object(auth_routes, "get_session_store", return_value=store),
    ):
        client = TestClient(app)
        registered = client.post(
            "/auth/register",
            json={"username": "account-a", "password": "test-password"},
        )
        assert registered.status_code == 200, registered.text
        response = client.post(
            "/auth/login",
            json={"username": "account-a", "password": "test-password"},
        )

    assert response.status_code == 200, response.text
    token = response.json()["token"]
    claims = _decode_claims(token)
    assert claims["subject"] == response.json()["user_id"]
    assert claims["purpose"] == ACCOUNT_SESSION_PURPOSE
    assert store.entries == {token: response.json()["user_id"]}


def test_admin_exchange_issues_operator_session_without_account_mapping(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "operator-boundary-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "operator-boundary-api-key")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")

    from guardian.routes import admin as admin_routes

    app = FastAPI()
    app.include_router(admin_routes.router)
    client = TestClient(app)
    response = client.post(
        "/auth/session",
        headers={"X-API-Key": "operator-boundary-api-key"},
        json={"ttl_seconds": 60},
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    claims = _decode_claims(token)
    assert claims["subject"] == "web"
    assert claims["purpose"] == OPERATOR_SESSION_PURPOSE
    assert verify_session_token_for_purpose(token, OPERATOR_SESSION_PURPOSE)

    cookie_response = client.post(
        "/auth/session/cookie",
        headers={"X-API-Key": "operator-boundary-api-key"},
        json={"ttl_seconds": 60},
    )
    assert cookie_response.status_code == 200, cookie_response.text
    parsed_cookie = SimpleCookie()
    parsed_cookie.load(cookie_response.headers["set-cookie"])
    cookie_token = parsed_cookie["gc_session"].value
    assert _decode_claims(cookie_token)["purpose"] == OPERATOR_SESSION_PURPOSE

    # API-key exchange emits operator capability only; it does not write the
    # account login session store used by the canonical login route.
    from guardian.core.session_store import SessionStore

    redis = MagicMock()
    redis.get.return_value = None
    assert SessionStore(redis_client=redis).verify(token) is None
    redis.set.assert_not_called()


def test_operator_dependency_rejects_account_guest_missing_and_other_purposes(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "operator-boundary-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "configured-key")
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    guest, _ = issue_guest_session_token(
        room_id="room-a",
        room_slug="room-a",
        participant_id="guest-a",
        invitation_id="invite-a",
    )
    missing_purpose = _sign_claims(
        {"subject": "legacy", "exp": 4_000_000_000, "nonce": "legacy-nonce"},
        "operator-boundary-secret",
    )
    unrelated, _ = issue_session_token(
        subject="other", purpose="unrelated_test_purpose"
    )
    expired, _ = issue_session_token(
        subject="expired",
        purpose=OPERATOR_SESSION_PURPOSE,
        ttl_seconds=-60,
    )

    for token in (account, guest, missing_purpose, unrelated, expired, "broken"):
        with pytest.raises(HTTPException) as exc:
            require_operator_auth(
                x_api_key=None,
                authorization=f"Bearer {token}",
                gc_session=None,
            )
        assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc:
        require_operator_auth(
            x_api_key="configured-key",
            authorization=f"Bearer {account}",
            gc_session=None,
        )
    assert exc.value.status_code == 401


def test_raw_key_and_operator_session_access_continuity_route(monkeypatch):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "operator-boundary-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "operator-boundary-api-key")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    raw_result = require_operator_auth(
        x_api_key="operator-boundary-api-key",
        authorization=None,
        gc_session=None,
    )
    assert raw_result == "operator-api-key"
    bearer_key_result = require_operator_auth(
        x_api_key=None,
        authorization="Bearer operator-boundary-api-key",
        gc_session=None,
    )
    assert bearer_key_result == "operator-api-key"

    from guardian.routes import admin as admin_routes
    from guardian.routes import continuity_operator

    app = _continuity_app()
    app.include_router(admin_routes.router)
    client = TestClient(app)
    exchange = client.post(
        "/auth/session",
        headers={"X-API-Key": "operator-boundary-api-key"},
        json={"ttl_seconds": 60},
    )
    assert exchange.status_code == 200, exchange.text
    operator_token = exchange.json()["token"]
    cookie_exchange = client.post(
        "/auth/session/cookie",
        headers={"X-API-Key": "operator-boundary-api-key"},
        json={"ttl_seconds": 60},
    )
    parsed_cookie = SimpleCookie()
    parsed_cookie.load(cookie_exchange.headers["set-cookie"])
    cookie_token = parsed_cookie["gc_session"].value

    with (
        patch.object(
            continuity_operator,
            "get_database_dsn",
            return_value="sqlite+pysqlite:///:memory:",
        ),
        patch(
            "guardian.continuity.write_actions.ContinuityWriteActionService.create_reality_stamp",
            return_value=_mock_receipt(),
        ),
    ):
        operator_response = client.post(
            "/api/operator/continuity/reality-stamp",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=_valid_payload(),
        )
        raw_response = client.post(
            "/api/operator/continuity/reality-stamp",
            headers={"X-API-Key": "operator-boundary-api-key"},
            json=_valid_payload(),
        )
        cookie_operator_response = client.post(
            "/api/operator/continuity/reality-stamp",
            cookies={"gc_session": cookie_token},
            json=_valid_payload(),
        )
    assert operator_response.status_code == 200, operator_response.text
    assert raw_response.status_code == 200, raw_response.text
    assert cookie_operator_response.status_code == 200, cookie_operator_response.text


def test_continuity_route_denies_account_and_guest_credentials(monkeypatch):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "operator-boundary-secret")
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    guest, _ = issue_guest_session_token(
        room_id="room-a",
        room_slug="room-a",
        participant_id="guest-a",
        invitation_id="invite-a",
    )
    client = TestClient(_continuity_app())

    for token in (account, guest):
        response = client.post(
            "/api/operator/continuity/reality-stamp",
            headers={"Authorization": f"Bearer {token}"},
            json=_valid_payload(),
        )
        assert response.status_code == 401
