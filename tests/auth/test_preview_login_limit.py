"""Exercise the real Lua policy with fakeredis, or an isolated Redis URL."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import fakeredis
import pytest
import redis
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from guardian.core import preview_login_limit as limiter
from guardian.routes import auth


@pytest.fixture
def store(monkeypatch):
    # Only supply this URL for a disposable test Redis. Never use Preview Redis.
    url = os.getenv("CODEXIFY_TEST_LOGIN_REDIS_URL")
    # Root conftest replaces Redis.from_url; use an explicit pool for this
    # opt-in integration run so it actually exercises the disposable server.
    client = (
        redis.Redis(connection_pool=redis.ConnectionPool.from_url(url))
        if url
        else fakeredis.FakeRedis()
    )
    prefix = "test:{preview-login}:" + uuid4().hex + ":"
    monkeypatch.setattr(limiter, "PREFIX", prefix)
    monkeypatch.setattr(limiter, "get_redis_client", lambda: client)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "synthetic-login-test-secret")
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", "")
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "fixture@example.com")
    yield client
    keys = list(client.scan_iter(prefix + "*"))
    if keys:
        client.delete(*keys)
    client.close()


def request(peer="192.0.2.1"):
    return Request({"type": "http", "headers": [], "client": (peer, 1234)})


def admit(email="fixture@example.com", peer="192.0.2.1"):
    try:
        limiter.enforce_preview_login_limit(email, request(peer))
        return 200
    except HTTPException as exc:
        return exc.status_code


def api():
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(auth.api_router)
    return TestClient(app)


def test_aliases_normalization_and_spoofed_headers_share_identity_budget(
    store, monkeypatch
):
    calls = []

    def rejected(body):
        calls.append(body)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    monkeypatch.setattr(auth, "_login_user", rejected)
    client = api()
    for index in range(12):
        response = client.post(
            "/api/auth/login" if index % 2 else "/auth/login",
            json={"username": "  FIXTURE@Example.COM  ", "password": "wrong"},
            headers={
                "X-Forwarded-For": f"198.51.100.{index}",
                "CF-Connecting-IP": f"203.0.113.{index}",
            },
        )
        assert response.status_code == (401 if index < 10 else 429)
    assert len(calls) == 10
    assert 1 <= int(response.headers["Retry-After"]) <= 300
    assert response.headers["Cache-Control"] == "no-store"
    assert "fixture" not in response.text.lower()
    assert int(store.get(limiter.PREFIX + "global")) == 10
    keys = list(store.scan_iter(limiter.PREFIX + "*"))
    assert len(keys) == 3
    assert all(b"@" not in key and b"192.0.2" not in key for key in keys)


def test_identity_budget_survives_changing_source(store):
    assert [admit(peer=f"192.0.2.{i}") for i in range(11)] == [200] * 10 + [429]


def test_source_budget_bounds_varying_identities(store):
    assert [admit(email=f"user{i}@example.com") for i in range(31)] == [200] * 30 + [
        429
    ]


def test_global_budget_bounds_changing_identities_sources_and_key_allocation(store):
    results = [admit(f"user{i}@example.com", f"192.0.2.{i}") for i in range(140)]
    assert results == [200] * 120 + [429] * 20
    assert len(list(store.scan_iter(limiter.PREFIX + "*"))) == 241


def test_concurrent_workers_cannot_over_admit(store):
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: admit(), range(40)))
    assert results.count(200) == 10
    assert results.count(429) == 30
    assert int(store.get(limiter.PREFIX + "global")) == 10


def test_denial_does_not_extend_cooldown_and_expiry_allows_retry(store, monkeypatch):
    monkeypatch.setattr(limiter, "LIMITS", ((2, 1), (1, 1), (2, 1)))
    assert admit() == 200
    keys = list(store.scan_iter(limiter.PREFIX + "*"))
    # Shorten existing windows to exercise actual Redis expiry without a long wait.
    for key in keys:
        store.pexpire(key, 100)
    assert admit() == 429
    assert all(0 < store.pttl(key) <= 100 for key in keys)
    time.sleep(0.15)
    assert admit() == 200


@pytest.mark.parametrize("invalid", [b"garbage", b"-1", b"1.5"])
def test_corrupt_counter_fails_closed(store, invalid):
    store.set(limiter.PREFIX + "global", invalid, ex=60)
    assert admit() == 503
    assert len(list(store.scan_iter(limiter.PREFIX + "*"))) == 1


def test_counter_without_expiry_fails_closed(store):
    store.set(limiter.PREFIX + "global", 1)
    assert admit() == 503


@pytest.mark.parametrize("reply", [None, False, "0", [], -1])
def test_malformed_backend_reply_fails_closed(store, monkeypatch, reply):
    monkeypatch.setattr(store, "eval", lambda *args: reply)
    assert admit() == 503


@pytest.mark.parametrize("path", ["/auth/login", "/api/auth/login"])
def test_redis_failure_prevents_database_and_password_work(store, monkeypatch, path):
    def unavailable(*args):
        raise redis.ConnectionError("sensitive backend connection detail")

    def forbidden(*args):
        pytest.fail("account lookup/password work ran after admission failure")

    monkeypatch.setattr(store, "eval", unavailable)
    monkeypatch.setattr(auth, "_auth_db", forbidden)
    monkeypatch.setattr(auth, "verify_password", forbidden)
    response = api().post(
        path, json={"username": "fixture@example.com", "password": "wrong"}
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Login temporarily unavailable"}
    assert response.headers["Retry-After"] == "5"


def test_missing_secret_fails_closed(store, monkeypatch):
    monkeypatch.delenv("GUARDIAN_SESSION_SECRET")
    assert admit() == 503
    assert not list(store.scan_iter(limiter.PREFIX + "*"))


def test_unknown_accounts_are_throttled_before_database_lookup(store, monkeypatch):
    monkeypatch.setattr(
        auth, "_auth_db", lambda: pytest.fail("unknown account reached DB")
    )
    client = api()
    statuses = [
        client.post(
            "/auth/login", json={"username": "unknown@example.com", "password": "wrong"}
        ).status_code
        for _ in range(11)
    ]
    assert statuses == [401] * 10 + [429]


def test_real_password_login_keeps_canonical_identity_session_and_budget(
    store, monkeypatch
):
    from guardian.core.auth import (
        ACCOUNT_SESSION_PURPOSE,
        _verified_session_token_claims,
    )
    from guardian.core.passwords import hash_password
    from guardian.core.session_store import get_session_store
    from guardian.db.models import User
    from tests.auth.test_auth_flow import _AuthDb

    db = _AuthDb()
    with db.get_session() as session:
        session.add(
            User(
                id="canonical-fixture",
                username="legacy-fixture",
                email="fixture@example.com",
                password_hash=hash_password("fixture-password"),
            )
        )
        session.commit()
    monkeypatch.setattr(auth, "_auth_db", lambda: db)
    client = api()
    # The success at the last permitted attempt must not reset the bucket.
    for _ in range(9):
        assert admit(peer="testclient") == 200
    response = client.post(
        "/api/auth/login",
        json={"username": " FIXTURE@example.com ", "password": "fixture-password"},
    )
    assert response.status_code == 200
    token = response.json()["token"]
    assert response.json()["user_id"] == "canonical-fixture"
    assert _verified_session_token_claims(token)["purpose"] == ACCOUNT_SESSION_PURPOSE
    assert get_session_store().verify(token) == "canonical-fixture"
    assert (
        client.post(
            "/auth/login",
            json={"username": "fixture@example.com", "password": "fixture-password"},
        ).status_code
        == 429
    )


def test_other_exposure_modes_keep_existing_login_behavior(monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setattr(
        auth,
        "enforce_preview_login_limit",
        lambda *args: pytest.fail("Preview policy applied outside Preview"),
    )
    monkeypatch.setattr(auth, "_login_user", lambda body: {"user_id": "local-fixture"})
    assert (
        api()
        .post("/auth/login", json={"username": "local", "password": "fixture"})
        .status_code
        == 200
    )
