import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core import auth, session_store
from guardian.core.scout_handoff import challenge_for
from guardian.routes import scout_auth


@pytest.fixture
def flow(monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv(
        "GUARDIAN_SESSION_SECRET", "synthetic-route-test-signing-fixture"
    )
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", "fixture@example.com")
    monkeypatch.setattr(scout_auth, "verify_access_assertion", lambda _: None)
    client = fakeredis.FakeRedis()
    store = session_store.SessionStore(client)
    monkeypatch.setattr(session_store, "_SESSION_STORE", store)
    token, _ = auth.issue_session_token(
        subject="fixture@example.com", purpose=auth.ACCOUNT_SESSION_PURPOSE
    )
    store.store(token, "fixture@example.com", 3600)
    app = FastAPI()
    app.include_router(scout_auth.router)
    api = TestClient(app, base_url="https://preview.codexify.space")
    return api, store, token


def create(api, token):
    return api.post(
        "/api/auth/scout/handoff",
        json={"state": "s" * 43, "challenge": challenge_for("v" * 43)},
        headers={
            "Origin": "https://preview.codexify.space",
            "Authorization": "Bearer " + token,
        },
    )


def code_from(response):
    from urllib.parse import parse_qs, urlsplit

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    callback = urlsplit(response.json()["callback"])
    assert callback.scheme == "ai.resonantconstructs.codexify.scout"
    assert callback.netloc == "access-callback"
    query = parse_qs(callback.query)
    assert set(query) == {"code", "state"}
    assert query["state"] == ["s" * 43]
    return query["code"][0]


def exchange(api, code, verifier="v" * 43):
    return api.post(
        "/api/auth/scout/exchange",
        json={"code": code, "verifier": verifier},
        headers={"Authorization": "Bearer oauth:fixture-ingress"},
    )


def test_canonical_session_transfers_once_without_reissuing(flow):
    api, store, token = flow
    code = code_from(create(api, token))
    assert token not in create(api, token).json()["callback"]
    assert exchange(api, code, "w" * 43).status_code == 401
    response = exchange(api, code)
    assert response.status_code == 200
    assert response.json()["token"] == token
    assert response.json()["user_id"] == "fixture@example.com"
    assert response.headers["cache-control"] == "no-store"
    assert store.verify(token) == "fixture@example.com"
    assert exchange(api, code).status_code == 401


def test_revocation_between_confirmation_and_exchange_is_authoritative(flow):
    api, store, token = flow
    code = code_from(create(api, token))
    store.revoke(token)
    assert exchange(api, code).status_code == 401


def test_wrong_origin_and_nonaccount_purpose_cannot_create_grant(flow):
    api, _, token = flow
    body = {"state": "s" * 43, "challenge": challenge_for("v" * 43)}
    assert (
        api.post(
            "/api/auth/scout/handoff",
            json=body,
            headers={
                "Authorization": "Bearer " + token,
                "Origin": "https://other.example",
            },
        ).status_code
        == 400
    )
    operator, _ = auth.issue_session_token(
        subject="fixture@example.com", purpose=auth.OPERATOR_SESSION_PURPOSE
    )
    assert create(api, operator).status_code == 401
    assert create(api, "fixture-invalid").status_code == 401


def test_expired_grant_and_wrong_host_cannot_exchange(flow):
    api, store, token = flow
    code = code_from(create(api, token))
    for key in store._client().scan_iter("scout:handoff:*"):
        store._client().delete(key)
    assert exchange(api, code).status_code == 401
    response = api.post(
        "/api/auth/scout/exchange",
        json={"code": code, "verifier": "v" * 43},
        headers={
            "Host": "personal.example",
            "Authorization": "Bearer oauth:fixture-ingress",
        },
    )
    assert response.status_code == 400


def test_validation_errors_never_echo_handoff_material(flow):
    api, _, _ = flow
    response = api.post(
        "/api/auth/scout/exchange",
        json={
            "code": "fixture-sensitive-malformed-code",
            "verifier": "fixture-sensitive-malformed-verifier",
        },
        headers={"Authorization": "Bearer oauth:fixture-ingress"},
    )
    assert response.status_code == 400
    assert "fixture-sensitive" not in response.text
    assert response.headers["cache-control"] == "no-store"
