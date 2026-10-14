from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from guardian.core.dependencies import (
    RequestUserScope,
    get_account_user_scope,
    require_account_session,
)
from guardian.routes import onboarding


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(onboarding.router)
    app.dependency_overrides[require_account_session] = lambda: "session"
    app.dependency_overrides[get_account_user_scope] = lambda: RequestUserScope(
        user_id="a"
    )
    return TestClient(app)


@pytest.mark.parametrize(
    "payload",
    [
        {"user_id": "b"},
        {"owner_id": "b"},
        {"status": "done"},
        {"status": None},
        {"last_step_key": "../../identity"},
        {"last_step_key": "1"},
        {"last_step_key": ""},
        {"onboarding_version": 0},
        {"onboarding_version": 2},
        {"onboarding_version": True},
        {"contextual_tips_enabled": "false"},
        {"desktop_tour_completed": None},
    ],
)
def test_fail_closed_validation(client, payload):
    assert client.patch("/api/onboarding", json=payload).status_code == 422


def test_partial_patch_only_supplied_fields(client, monkeypatch):
    from contextlib import nullcontext

    class Database:
        def get_session(self):
            return nullcontext(object())

    monkeypatch.setattr(onboarding, "database", lambda: Database())
    calls = []
    monkeypatch.setattr(
        onboarding.service,
        "patch_state",
        lambda session, owner, changes: calls.append((owner, changes)) or changes,
    )
    assert (
        client.patch("/api/onboarding", json={"status": "skipped"}).status_code == 200
    )
    assert calls == [("a", {"status": "skipped"})]


def test_unauthenticated_rejected(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    app = FastAPI()
    app.include_router(onboarding.router)
    response = TestClient(app).get("/api/onboarding")
    assert response.status_code in (401, 403)


@pytest.mark.parametrize(
    "purpose", [None, "operator_session", "hosted_room_guest_session", "unrelated"]
)
def test_wrong_purpose_rejected_before_store_and_database(monkeypatch, purpose):
    import base64
    import hashlib
    import hmac
    import json
    import time

    claims = {
        "subject": "account-a",
        "exp": int(time.time()) + 3600,
        "nonce": "onboarding-test",
    }
    if purpose is not None:
        claims["purpose"] = purpose
    payload = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.new(b"test-session-secret", payload, hashlib.sha256).digest()
    token = ".".join(
        base64.urlsafe_b64encode(value).decode().rstrip("=")
        for value in (payload, signature)
    )
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)

    def forbidden():
        raise AssertionError("Wrong-purpose request must not reach persistence")

    monkeypatch.setattr("guardian.core.auth_dependencies.get_session_store", forbidden)
    monkeypatch.setattr(onboarding, "database", forbidden)
    app = FastAPI()
    app.include_router(onboarding.router)
    response = TestClient(app).get(
        "/api/onboarding", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "name, messaging",
    [("v1-local-core-web-mcp", "quarantined"), ("v1-friends-family-web", "enabled")],
)
def test_independent_onboarding_admission(name, messaging):
    from guardian.core.supported_profile import load_supported_profile

    profile = load_supported_profile(name)
    assert profile.route_status("onboarding") == "enabled"
    assert profile.route_status("direct_messages") == messaging
