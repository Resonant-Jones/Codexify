"""Bounded MiniMax OAuth setup lifecycle tests.

These tests mock all upstream MiniMax network calls and exercise only the
provider-owned start / poll / disconnect / refresh surface. They prove:

* missing node OAuth configuration fails safely;
* start generates PKCE + state + opaque flow metadata;
* poll enforces user-binding, TTL, and cadence;
* successful poll persists the encrypted credential under minimax_oauth;
* plaintext access/refresh tokens never enter persistence;
* encrypted credentials decrypt in the test seam;
* malformed upstream responses fail closed;
* terminal flow state is discarded;
* the refresh helper rotates access tokens and preserves refresh on omission;
* no API-key environment mutation occurs.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import types
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------- helpers ----------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class _FakeDB:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, str, str], dict[str, Any]] = {}

    def upsert_oauth_connection(
        self,
        *,
        user_id: str,
        provider: str,
        mode: str,
        scopes: list[str],
        status: str,
        encrypted_access_token: str | None = None,
        encrypted_refresh_token: str | None = None,
        expires_at: datetime | None = None,
        last_refresh_at: datetime | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        key = (user_id, provider, mode)
        existing = self.rows.get(key, {})
        existing.update(
            {
                "user_id": user_id,
                "provider": provider,
                "mode": mode,
                "scopes": scopes,
                "status": status,
                "encrypted_access_token": encrypted_access_token,
                "encrypted_refresh_token": encrypted_refresh_token,
                "expires_at": expires_at,
                "last_refresh_at": (
                    last_refresh_at if last_refresh_at is not None else existing.get("last_refresh_at")
                ),
                "last_error": last_error,
            }
        )
        self.rows[key] = existing
        return existing

    def get_oauth_connection(
        self, *, user_id: str, provider: str, mode: str
    ) -> dict[str, Any] | None:
        return self.rows.get((user_id, provider, mode))

    def disconnect_oauth_connection(
        self, *, user_id: str, provider: str, mode: str
    ) -> int:
        key = (user_id, provider, mode)
        if key in self.rows:
            self.rows[key]["status"] = "disconnected"
            return 1
        return 0


@contextmanager
def _env(values: dict[str, str]):
    original = {k: os.environ.get(k) for k in values}
    for k, v in values.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        yield
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _load_minimax_module(env: dict[str, str] | None = None):
    """(Re)load the minimax module with the supplied env applied."""

    env = env or {}
    for k in (
        "MINIMAX_OAUTH_CLIENT_ID",
        "MINIMAX_OAUTH_AUTHORIZE_URL",
        "MINIMAX_OAUTH_TOKEN_URL",
        "MINIMAX_OAUTH_ALLOWED_HOSTS",
    ):
        os.environ.pop(k, None)
    for k, v in env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    # Force a fresh module so _node_oauth_config / _flows are clean.
    sys.modules.pop("guardian.connectors.minimax", None)
    return importlib.import_module("guardian.connectors.minimax")


def _install_db_override(mod: types.ModuleType, db: _FakeDB) -> None:
    """Install a fake DB override for minimax module persistence calls."""

    from cryptography.fernet import Fernet

    os.environ.setdefault(
        "GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    monkey_guardian_db = MagicMock()
    monkey_guardian_db.upsert_oauth_connection = (
        lambda **kwargs: db.upsert_oauth_connection(**kwargs)
    )
    monkey_guardian_db.get_oauth_connection = (
        lambda **kwargs: db.get_oauth_connection(**kwargs)
    )
    monkey_guardian_db.disconnect_oauth_connection = (
        lambda **kwargs: db.disconnect_oauth_connection(**kwargs)
    )
    import guardian.core.db as _real_db  # type: ignore

    _real_db.load_guardian_db_from_env = lambda: monkey_guardian_db


# ---------- configuration tests ---------------------------------


def test_node_oauth_not_configured_when_env_missing() -> None:
    mod = _load_minimax_module({})
    assert mod.node_oauth_configured() is False


def test_node_oauth_configured_when_all_required_env_present() -> None:
    mod = _load_minimax_module(
        {
            "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
            "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
            "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
        }
    )
    assert mod.node_oauth_configured() is True


def test_node_oauth_rejects_unallowed_upstream_url() -> None:
    mod = _load_minimax_module(
        {
            "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
            "MINIMAX_OAUTH_AUTHORIZE_URL": "https://attacker.example.com/authorize",
            "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
        }
    )
    assert mod.node_oauth_configured() is False


def test_allowed_hosts_extension_is_accepted() -> None:
    mod = _load_minimax_module(
        {
            "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
            "MINIMAX_OAUTH_AUTHORIZE_URL": "https://minimax.example.test/oauth/authorize",
            "MINIMAX_OAUTH_TOKEN_URL": "https://minimax.example.test/oauth/token",
            "MINIMAX_OAUTH_ALLOWED_HOSTS": "minimax.example.test",
        }
    )
    assert mod.node_oauth_configured() is True


# ---------- start / poll lifecycle -------------------------------


def _build_client(mod: types.ModuleType, db: _FakeDB) -> tuple[TestClient, FastAPI]:
    """Construct a TestClient with the minimax router and a fake DB."""

    # Provide a static Fernet key so encrypt_token/decrypt_token work.
    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode("ascii")
    os.environ["GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY"] = test_key

    # Replace the loader that minimax.py captures per call.
    monkey_guardian_db = MagicMock()
    monkey_guardian_db.upsert_oauth_connection = (
        lambda **kwargs: db.upsert_oauth_connection(**kwargs)
    )
    monkey_guardian_db.get_oauth_connection = (
        lambda **kwargs: db.get_oauth_connection(**kwargs)
    )
    monkey_guardian_db.disconnect_oauth_connection = (
        lambda **kwargs: db.disconnect_oauth_connection(**kwargs)
    )
    import guardian.core.db as _real_db  # type: ignore

    _real_db.load_guardian_db_from_env = lambda: monkey_guardian_db

    # Provide a simple current_user dependency for tests.
    def _stub_user() -> str:
        return "test-user"

    app = FastAPI()
    app.include_router(mod.router)
    app.dependency_overrides[mod.get_current_user] = _stub_user
    return TestClient(app), app


def test_start_returns_only_safe_metadata() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    fake_authorize = {
        "user_code": "ABCD-EFGH",
        "verification_uri": "https://api.minimax.io/activate",
        "interval": 5,
        "expires_in": 600,
    }
    with patch.object(mod.requests, "post", return_value=_fake_response(fake_authorize)):
        response = client.post("/api/connect/minimax/start")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider"] == "minimax_oauth"
    assert payload["flow_id"]
    assert payload["verification_uri"] == "https://api.minimax.io/activate"
    assert payload["user_code"] == "ABCD-EFGH"
    assert payload["poll_interval_seconds"] >= 2
    # PKCE verifier must never be serialized.
    for forbidden in (
        "verifier",
        "code_verifier",
        "code_challenge",
        "pkce",
        "access_token",
        "refresh_token",
    ):
        assert forbidden not in payload
    # flow registry records the verifier server-side, not in payload.
    flow_id = payload["flow_id"]
    assert mod._get_flow(flow_id) is not None
    assert "verifier" in mod._get_flow(flow_id)
    # A pending row was projected so the catalog reads "authenticating".
    row = db.rows.get(("test-user", "minimax_oauth", "node_local"))
    assert row is not None
    assert row["status"] == "pending"


def test_start_generates_pkce_and_state_per_call() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    captured_query: list[dict[str, str]] = []

    def _fake_post(url, data, **kwargs):
        # The authorize call passes params via query string.
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        captured_query.append({k: v[0] for k, v in parse_qs(parsed.query).items()})
        return _fake_response(
            {
                "user_code": "ABCD",
                "verification_uri": "https://api.minimax.io/activate",
                "interval": 5,
                "expires_in": 600,
            }
        )

    with patch.object(mod.requests, "post", side_effect=_fake_post):
        client.post("/api/connect/minimax/start")
        client.post("/api/connect/minimax/start")

    assert len(captured_query) == 2
    first, second = captured_query
    assert first["code_challenge_method"] == "S256"
    assert first["response_type"] == "code"
    assert first["client_id"] == "codexify-minimax-oauth-client"
    assert "code_challenge" in first
    assert first["state"] != second["state"]
    # Different flow_ids and different PKCE challenges are issued.
    assert first["code_challenge"] != second["code_challenge"]


def test_start_fails_closed_on_incomplete_upstream_response() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    # Missing user_code and verification_uri: must fail closed.
    bad = {
        "interval": 5,
        "expires_in": 600,
    }
    with patch.object(mod.requests, "post", return_value=_fake_response(bad)):
        response = client.post("/api/connect/minimax/start")
    assert response.status_code == 502


def test_poll_rejects_cross_user_flow_lookup() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    # Start a flow as test-user; we will then poll under a different user.
    with patch.object(
        mod.requests,
        "post",
        return_value=_fake_response(
            {
                "user_code": "ABCD",
                "verification_uri": "https://api.minimax.io/activate",
                "interval": 1,
                "expires_in": 600,
            }
        ),
    ):
        start_response = client.post("/api/connect/minimax/start")
    flow_id = start_response.json()["flow_id"]

    def _as_other_user() -> str:
        return "other-user"

    app.dependency_overrides[mod.get_current_user] = _as_other_user
    response = client.post("/api/connect/minimax/poll", json={"flow_id": flow_id})
    assert response.status_code == 404
    # flow still belongs to test-user
    assert mod._get_flow(flow_id)["user_id"] == "test-user"


def test_poll_enforces_cadence() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    with patch.object(
        mod.requests,
        "post",
        return_value=_fake_response(
            {
                "user_code": "ABCD",
                "verification_uri": "https://api.minimax.io/activate",
                "interval": 60,
                "expires_in": 600,
            }
        ),
    ):
        start_response = client.post("/api/connect/minimax/start")
    flow_id = start_response.json()["flow_id"]

    # Started_at was just set; an immediate poll MUST fail cadence.
    response = client.post("/api/connect/minimax/poll", json={"flow_id": flow_id})
    assert response.status_code == 429


def test_poll_pending_response_remains_pending() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    with patch.object(
        mod.requests,
        "post",
        side_effect=[
            _fake_response(
                {
                    "user_code": "ABCD",
                    "verification_uri": "https://api.minimax.io/activate",
                    "interval": 1,
                    "expires_in": 600,
                }
            ),
            _fake_response({"error": "authorization_pending"}, status_code=400),
        ],
    ):
        start_response = client.post("/api/connect/minimax/start")
        flow_id = start_response.json()["flow_id"]
        # Patch last_poll so cadence allows the poll.
        flow = mod._get_flow(flow_id)
        flow["last_poll"] = 0.0
        flow["started_at"] = 0.0
        flow["started_at"] = 0.0
        poll_response = client.post(
            "/api/connect/minimax/poll", json={"flow_id": flow_id}
        )
    assert poll_response.status_code == 200
    assert poll_response.json()["status"] == "authenticating"
    assert db.rows[("test-user", "minimax_oauth", "node_local")]["status"] == "pending"


def test_poll_successful_response_persists_encrypted_credentials() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    token_body = {
        "access_token": "plaintext-access-secret-XYZ",
        "refresh_token": "plaintext-refresh-secret-UVW",
        "expires_in": 3600,
        "scope": "chat",
    }
    with patch.object(
        mod.requests,
        "post",
        side_effect=[
            _fake_response(
                {
                    "user_code": "ABCD",
                    "verification_uri": "https://api.minimax.io/activate",
                    "interval": 1,
                    "expires_in": 600,
                }
            ),
            _fake_response(token_body),
        ],
    ):
        start_response = client.post("/api/connect/minimax/start")
        flow_id = start_response.json()["flow_id"]
        mod._get_flow(flow_id)["last_poll"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        poll_response = client.post(
            "/api/connect/minimax/poll", json={"flow_id": flow_id}
        )
    assert poll_response.status_code == 200
    assert poll_response.json()["status"] == "connected"
    # No plaintext values returned in any poll response payload.
    body_text = poll_response.text
    assert "plaintext-access-secret-XYZ" not in body_text
    assert "plaintext-refresh-secret-UVW" not in body_text

    row = db.rows[("test-user", "minimax_oauth", "node_local")]
    assert row["status"] == "connected"
    encrypted_access = row["encrypted_access_token"]
    encrypted_refresh = row["encrypted_refresh_token"]
    assert encrypted_access and encrypted_refresh
    # Plaintext secrets MUST NOT appear in the persisted row.
    assert "plaintext-access-secret-XYZ" not in encrypted_access
    assert "plaintext-refresh-secret-UVW" not in encrypted_refresh
    # Round-trip decryption recovers plaintext in the backend test seam.
    from guardian.connectors.oauth_crypto import decrypt_token

    assert decrypt_token(encrypted_access) == "plaintext-access-secret-XYZ"
    assert decrypt_token(encrypted_refresh) == "plaintext-refresh-secret-UVW"
    # Expires recorded.
    assert isinstance(row["expires_at"], datetime)
    # Flow state is discarded after terminal success.
    assert mod._get_flow(flow_id) is None


def test_poll_malformed_token_response_fails_closed() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    with patch.object(
        mod.requests,
        "post",
        side_effect=[
            _fake_response(
                {
                    "user_code": "ABCD",
                    "verification_uri": "https://api.minimax.io/activate",
                    "interval": 1,
                    "expires_in": 600,
                }
            ),
            # Upstream returned non-JSON garbage.
            _fake_response("not-json", status_code=200),
        ],
    ):
        start_response = client.post("/api/connect/minimax/start")
        flow_id = start_response.json()["flow_id"]
        mod._get_flow(flow_id)["last_poll"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        poll_response = client.post(
            "/api/connect/minimax/poll", json={"flow_id": flow_id}
        )
    assert poll_response.status_code == 502
    assert mod._get_flow(flow_id) is None


def test_poll_provider_error_persists_error_status() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    with patch.object(
        mod.requests,
        "post",
        side_effect=[
            _fake_response(
                {
                    "user_code": "ABCD",
                    "verification_uri": "https://api.minimax.io/activate",
                    "interval": 1,
                    "expires_in": 600,
                }
            ),
            _fake_response({"error": "access_denied"}, status_code=400),
        ],
    ):
        start_response = client.post("/api/connect/minimax/start")
        flow_id = start_response.json()["flow_id"]
        mod._get_flow(flow_id)["last_poll"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        mod._get_flow(flow_id)["started_at"] = 0.0
        poll_response = client.post(
            "/api/connect/minimax/poll", json={"flow_id": flow_id}
        )
    assert poll_response.status_code == 200
    assert poll_response.json()["status"] == "error"
    row = db.rows[("test-user", "minimax_oauth", "node_local")]
    assert row["status"] == "error"
    # Raw upstream error text MUST NOT be persisted verbatim; only the
    # bounded classification survives.
    assert row["last_error"] == "access_denied"
    assert mod._get_flow(flow_id) is None


def test_poll_rejects_expired_flow() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    with patch.object(
        mod.requests,
        "post",
        return_value=_fake_response(
            {
                "user_code": "ABCD",
                "verification_uri": "https://api.minimax.io/activate",
                "interval": 1,
                "expires_in": 600,
            }
        ),
    ):
        start_response = client.post("/api/connect/minimax/start")
        flow_id = start_response.json()["flow_id"]
        # Force the flow past its TTL.
        flow = mod._get_flow(flow_id)
        flow["expires_at"] = _now_utc() - timedelta(seconds=1)
        poll_response = client.post(
            "/api/connect/minimax/poll", json={"flow_id": flow_id}
        )
    assert poll_response.status_code == 410


# ---------- disconnect ------------------------------------------


def test_disconnect_clears_state() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    db.upsert_oauth_connection(
        user_id="test-user",
        provider="minimax_oauth",
        mode="node_local",
        scopes=[],
        status="connected",
        encrypted_access_token="dummy",
        encrypted_refresh_token="dummy",
    )
    response = client.post("/api/connect/minimax/disconnect")
    assert response.status_code == 200
    assert response.json()["disconnected"] == 1
    assert db.rows[("test-user", "minimax_oauth", "node_local")]["status"] == (
        "disconnected"
    )


# ---------- refresh helper --------------------------------------


def test_refresh_helper_rotates_access_and_preserves_refresh_when_omitted() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    _install_db_override(mod, db)

    # Seed an existing connection with an encrypted refresh token.
    from guardian.connectors.oauth_crypto import encrypt_token

    existing_refresh = encrypt_token("original-refresh-token-AAA")
    db.upsert_oauth_connection(
        user_id="test-user",
        provider="minimax_oauth",
        mode="node_local",
        scopes=[],
        status="connected",
        encrypted_access_token=encrypt_token("old-access"),
        encrypted_refresh_token=existing_refresh,
    )

    # Upstream returns ONLY a new access_token (refresh omitted).
    refresh_body = {
        "access_token": "new-access-secret-NEW",
        "expires_in": 1800,
    }
    with patch.object(
        mod.requests, "post", return_value=_fake_response(refresh_body)
    ) as post_mock:
        result = mod.refresh_minimax_oauth(
            user_id="test-user",
            encrypted_refresh_token=existing_refresh,
        )
        # Confirm we hit the token endpoint with refresh grant.
        assert post_mock.called
        kwargs = post_mock.call_args.kwargs
        body = kwargs.get("data") or {}
        assert body.get("grant_type") == "refresh_token"
        assert body.get("client_id") == "codexify-minimax-oauth-client"

    assert result["status"] == "connected"
    row = db.rows[("test-user", "minimax_oauth", "node_local")]
    from guardian.connectors.oauth_crypto import decrypt_token

    assert decrypt_token(row["encrypted_access_token"]) == "new-access-secret-NEW"
    # Refresh token preserved verbatim.
    assert decrypt_token(row["encrypted_refresh_token"]) == "original-refresh-token-AAA"


def test_refresh_helper_accepts_new_refresh_when_supplied() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    _install_db_override(mod, db)

    from guardian.connectors.oauth_crypto import encrypt_token

    existing_refresh = encrypt_token("old-refresh-AAA")
    db.upsert_oauth_connection(
        user_id="test-user",
        provider="minimax_oauth",
        mode="node_local",
        scopes=[],
        status="connected",
        encrypted_access_token=encrypt_token("old-access"),
        encrypted_refresh_token=existing_refresh,
    )

    refresh_body = {
        "access_token": "new-access-NEW",
        "refresh_token": "rotated-refresh-BBB",
        "expires_in": 1800,
    }
    with patch.object(mod.requests, "post", return_value=_fake_response(refresh_body)):
        mod.refresh_minimax_oauth(
            user_id="test-user",
            encrypted_refresh_token=existing_refresh,
        )
    row = db.rows[("test-user", "minimax_oauth", "node_local")]
    from guardian.connectors.oauth_crypto import decrypt_token

    assert decrypt_token(row["encrypted_refresh_token"]) == "rotated-refresh-BBB"


def test_refresh_helper_fails_closed_on_malformed_response() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    _install_db_override(mod, db)

    from guardian.connectors.oauth_crypto import encrypt_token

    existing_refresh = encrypt_token("seed-refresh-AAA")
    db.upsert_oauth_connection(
        user_id="test-user",
        provider="minimax_oauth",
        mode="node_local",
        scopes=[],
        status="connected",
        encrypted_access_token=encrypt_token("old-access"),
        encrypted_refresh_token=existing_refresh,
    )

    # Missing access_token -> helper must raise, row must NOT be mutated.
    with patch.object(
        mod.requests,
        "post",
        return_value=_fake_response({"expires_in": 600}),
    ):
        with pytest.raises(RuntimeError):
            mod.refresh_minimax_oauth(
                user_id="test-user",
                encrypted_refresh_token=existing_refresh,
            )
    row = db.rows[("test-user", "minimax_oauth", "node_local")]
    from guardian.connectors.oauth_crypto import decrypt_token

    assert decrypt_token(row["encrypted_access_token"]) == "old-access"


# ---------- environment invariants ------------------------------


def test_oauth_lifecycle_does_not_mutate_minimax_api_key() -> None:
    env = {
        "MINIMAX_OAUTH_CLIENT_ID": "codexify-minimax-oauth-client",
        "MINIMAX_OAUTH_AUTHORIZE_URL": "https://api.minimax.io/oauth/authorize",
        "MINIMAX_OAUTH_TOKEN_URL": "https://api.minimax.io/oauth/token",
    }
    mod = _load_minimax_module(env)
    db = _FakeDB()
    client, app = _build_client(mod, db)

    with patch.object(
        mod.requests,
        "post",
        return_value=_fake_response(
            {
                "user_code": "ABCD",
                "verification_uri": "https://api.minimax.io/activate",
                "interval": 1,
                "expires_in": 600,
            }
        ),
    ):
        before = dict(os.environ)
        response = client.post("/api/connect/minimax/start")
        after = dict(os.environ)
    assert response.status_code == 200
    # No MINIMAX_API_KEY write occurred during setup.
    assert before.get("MINIMAX_API_KEY") == after.get("MINIMAX_API_KEY")


# ---------- helpers ----------------------------------------------


class _FakeResponse:
    def __init__(self, body: Any, status_code: int = 200) -> None:
        self._body = body
        self.status_code = status_code
        if isinstance(body, (dict, list)):
            text = json.dumps(body)
        else:
            text = str(body)
        self.content = text.encode("utf-8")
        self.text = text

    def json(self) -> Any:
        if isinstance(self._body, (dict, list)):
            return self._body
        return json.loads(self._body)


def _fake_response(body: Any, status_code: int = 200) -> _FakeResponse:
    return _FakeResponse(body, status_code)