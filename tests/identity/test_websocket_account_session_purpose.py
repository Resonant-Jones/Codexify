"""WebSocket account credentials require exact purpose before session lookup."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from importlib import import_module
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.routing import APIWebSocketRoute
from fastapi.testclient import TestClient

from guardian.core import auth_dependencies, dependencies
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.routes import websocket as mounted_routes
from guardian.ws import auth as ws_auth

declared_routes = import_module("guardian.ws.router")

SECRET = "websocket-account-purpose-test-secret"
ACCOUNT_ID = "approved@example.com"
OTHER_ID = "other@example.com"
LOCAL_KEY = "websocket-local-test-key"
ROUTERS = (mounted_routes, declared_routes)
TRANSPORTS = ("query_api_key", "query_token", "frame_api_key", "frame_token")
INVALID_PURPOSE_CASES = (
    "legacy",
    "operator",
    "guest",
    "wrong_purpose",
    "malformed",
    "expired",
)


class _Store:
    def __init__(self) -> None:
        self.entries: dict[str, str] = {}
        self.reads: list[str] = []
        self.events: list[str] | None = None

    def verify(self, token: str) -> str | None:
        self.reads.append(token)
        if self.events is not None:
            self.events.append("store")
        return self.entries.get(token)


@pytest.fixture
def boundary(monkeypatch):
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", SECRET)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", ACCOUNT_ID)
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", "")
    monkeypatch.setenv("GUARDIAN_API_KEY", LOCAL_KEY)
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(GUARDIAN_API_KEY=LOCAL_KEY, GUARDIAN_API_KEYS=None),
    )
    store = _Store()
    monkeypatch.setattr(auth_dependencies, "get_session_store", lambda: store)
    return store


def _client(module) -> TestClient:
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def _account_token(
    store: _Store,
    *,
    purpose: str = ACCOUNT_SESSION_PURPOSE,
    subject: str = ACCOUNT_ID,
    stored_as: str | None = ACCOUNT_ID,
    ttl_seconds: int = 60,
) -> str:
    token, _ = issue_session_token(
        subject=subject, purpose=purpose, ttl_seconds=ttl_seconds
    )
    if stored_as is not None:
        store.entries[token] = stored_as
    return token


def _legacy_token(store: _Store) -> str:
    claims = {"subject": ACCOUNT_ID, "nonce": "legacy", "exp": 4_000_000_000}
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(SECRET.encode(), payload, hashlib.sha256).digest()

    def encode(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode().rstrip("=")

    token = f"{encode(payload)}.{encode(signature)}"
    store.entries[token] = ACCOUNT_ID
    return token


def _credential(store: _Store, case: str) -> str:
    if case == "approved":
        return _account_token(store)
    if case == "unmapped":
        return _account_token(store, stored_as=None)
    if case == "mismatched":
        return _account_token(store, stored_as=OTHER_ID)
    if case == "unapproved":
        return _account_token(store, subject=OTHER_ID, stored_as=OTHER_ID)
    if case == "legacy":
        return _legacy_token(store)
    if case == "operator":
        return _account_token(store, purpose=OPERATOR_SESSION_PURPOSE)
    if case == "guest":
        token, _ = issue_guest_session_token(
            room_id="room",
            room_slug="room",
            participant_id="guest",
            invitation_id="invite",
        )
        store.entries[token] = ACCOUNT_ID
        return token
    if case == "wrong_purpose":
        return _account_token(store, purpose="unrelated")
    if case == "malformed":
        store.entries["malformed"] = ACCOUNT_ID
        return "malformed"
    if case == "expired":
        return _account_token(store, ttl_seconds=-60)
    raise AssertionError(case)


def _connect(client: TestClient, transport: str, token: str):
    if transport.startswith("query_"):
        key = transport.removeprefix("query_")
        return client.websocket_connect(f"/api/ws/rpc?{key}={token}")
    return client.websocket_connect("/api/ws/rpc")


def _send_frame(ws, transport: str, token: str) -> None:
    if transport.startswith("frame_"):
        ws.send_json({"type": "auth", transport.removeprefix("frame_"): token})


def test_both_frozen_declarations_use_the_shared_authentication_seam():
    for module in ROUTERS:
        routes = [
            route
            for route in module.router.routes
            if isinstance(route, APIWebSocketRoute)
        ]
        assert len(routes) == 1
        assert routes[0].path == "/api/ws/rpc"
        assert routes[0].endpoint.__name__ == "websocket_rpc"
        assert (
            routes[0].endpoint.__globals__["authenticate_websocket"]
            is ws_auth.authenticate_websocket
        )


@pytest.mark.parametrize("module", ROUTERS, ids=("mounted", "declared"))
@pytest.mark.parametrize("transport", TRANSPORTS)
def test_valid_approved_account_session_authenticates(
    boundary: _Store, module, transport: str
):
    token = _credential(boundary, "approved")
    with _connect(_client(module), transport, token) as ws:
        _send_frame(ws, transport, token)
        ws.send_json({"type": "request", "id": "ping", "method": "ping", "params": {}})
        response = ws.receive_json()
    assert response["result"] == {"ok": True}
    assert boundary.reads == [token]


@pytest.mark.parametrize("module", ROUTERS, ids=("mounted", "declared"))
@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize(
    "case", INVALID_PURPOSE_CASES + ("unmapped", "mismatched", "unapproved")
)
def test_remote_websocket_rejects_invalid_account_authority(
    boundary: _Store, module, transport: str, case: str
):
    token = _credential(boundary, case)
    with pytest.raises(WebSocketDisconnect) as exc:
        with _connect(_client(module), transport, token) as ws:
            _send_frame(ws, transport, token)
            ws.receive_json()
    assert exc.value.code == ws_auth.AUTH_FAILURE_CLOSE_CODE
    if case in INVALID_PURPOSE_CASES:
        assert boundary.reads == []
    else:
        assert boundary.reads == [token]


def test_purpose_precedes_store_and_preview_policy(boundary: _Store, monkeypatch):
    events: list[str] = []
    boundary.events = events
    original_purpose = ws_auth.verify_session_token_for_purpose
    original_policy = ws_auth.role_for_preview_email

    def purpose(token: str, expected: str) -> bool:
        events.append("purpose")
        return original_purpose(token, expected)

    def policy(user_id: str) -> str | None:
        events.append("policy")
        return original_policy(user_id)

    monkeypatch.setattr(ws_auth, "verify_session_token_for_purpose", purpose)
    monkeypatch.setattr(ws_auth, "role_for_preview_email", policy)

    invalid = _credential(boundary, "operator")
    with pytest.raises(ws_auth.WSAuthError):
        ws_auth._validate_api_key(invalid)
    assert events == ["purpose"]

    events.clear()
    valid = _credential(boundary, "approved")
    assert ws_auth._validate_api_key(valid) == valid
    assert events == ["purpose", "store", "policy"]


def test_wrong_purpose_dispatches_no_rpc(boundary: _Store, monkeypatch):
    dispatched: list[str] = []

    async def forbidden_dispatch(method, params, ctx):
        dispatched.append(method)
        return {"unexpected": True}

    monkeypatch.setattr(mounted_routes, "dispatch_rpc_method", forbidden_dispatch)
    token = _credential(boundary, "operator")
    with pytest.raises(WebSocketDisconnect):
        with _connect(_client(mounted_routes), "query_token", token) as ws:
            ws.send_json(
                {"type": "request", "id": "foreign", "method": "ping", "params": {}}
            )
            ws.receive_json()
    assert dispatched == []
    assert boundary.reads == []


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_remote_non_preview_uses_the_same_account_purpose_boundary(
    boundary: _Store, monkeypatch, transport: str
):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    valid = _credential(boundary, "approved")
    with _connect(_client(mounted_routes), transport, valid) as ws:
        _send_frame(ws, transport, valid)
        ws.send_json(
            {"type": "request", "id": "remote", "method": "ping", "params": {}}
        )
        assert ws.receive_json()["result"] == {"ok": True}
    assert boundary.reads == [valid]

    boundary.reads.clear()
    wrong = _credential(boundary, "operator")
    with pytest.raises(WebSocketDisconnect) as exc:
        with _connect(_client(mounted_routes), transport, wrong) as ws:
            _send_frame(ws, transport, wrong)
            ws.receive_json()
    assert exc.value.code == ws_auth.AUTH_FAILURE_CLOSE_CODE
    assert boundary.reads == []

    with pytest.raises(WebSocketDisconnect) as exc:
        with _connect(_client(mounted_routes), transport, LOCAL_KEY) as ws:
            _send_frame(ws, transport, LOCAL_KEY)
            ws.receive_json()
    assert exc.value.code == ws_auth.AUTH_FAILURE_CLOSE_CODE
    assert boundary.reads == []


@pytest.mark.parametrize("module", ROUTERS, ids=("mounted", "declared"))
@pytest.mark.parametrize("transport", TRANSPORTS)
def test_local_api_key_path_remains_available(
    boundary: _Store, monkeypatch, module, transport
):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    with _connect(_client(module), transport, LOCAL_KEY) as ws:
        _send_frame(ws, transport, LOCAL_KEY)
        ws.send_json({"type": "request", "id": "local", "method": "ping", "params": {}})
        response = ws.receive_json()
    assert response["result"] == {"ok": True}
    assert boundary.reads == []
