import fakeredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core import auth, session_store
from guardian.core.scout_handoff import challenge_for
from guardian.routes import scout_auth


def _scout_client(*args, **kwargs):
    client = TestClient(*args, **kwargs)
    # The repository bootstrap injects an operator key by default. Scout tests
    # must exercise only the credential selectors explicitly supplied per call.
    client.headers.pop("X-API-Key", None)
    return client


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
        subject="fixture@example.com",
        ttl_seconds=300,
        purpose=auth.ACCOUNT_SESSION_PURPOSE,
    )
    store.store(token, "fixture@example.com", 300)
    app = FastAPI()
    app.include_router(scout_auth.router)
    api = _scout_client(
        app,
        base_url="https://preview.codexify.space",
        headers={"Cf-Access-Jwt-Assertion": "fixture-assertion"},
    )
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


def test_exchange_issues_independent_exact_purpose_native_session(flow):
    api, store, token = flow
    code = code_from(create(api, token))
    assert token not in create(api, token).json()["callback"]
    assert exchange(api, code, "w" * 43).status_code == 401
    response = exchange(api, code)
    assert response.status_code == 200
    native = response.json()["token"]
    assert native != token
    browser_claims = auth._verified_session_token_claims(token)
    native_claims = auth._verified_session_token_claims(native)
    assert native_claims["nonce"] != browser_claims["nonce"]
    assert native_claims["purpose"] == auth.ACCOUNT_SESSION_PURPOSE
    assert native_claims["subject"] == browser_claims["subject"]
    assert native_claims["exp"] == response.json()["expires_at"]
    assert native_claims["exp"] > browser_claims["exp"]
    assert store.verify(native) == "fixture@example.com"
    assert store._client().ttl(store._key(native)) > 86000
    assert response.json()["user_id"] == "fixture@example.com"
    assert response.headers["cache-control"] == "no-store"
    assert store.verify(token) == "fixture@example.com"
    assert exchange(api, code).status_code == 401


def test_edge_consumed_exchange_requires_handoff_and_canonical_parent(flow):
    api, store, browser = flow
    code = code_from(create(api, browser))
    wrong = api.post(
        "/api/auth/scout/exchange", json={"code": code, "verifier": "w" * 43}
    )
    assert wrong.status_code == 401
    response = api.post(
        "/api/auth/scout/exchange", json={"code": code, "verifier": "v" * 43}
    )
    assert response.status_code == 200
    assert response.headers["X-Scout-Access-Admission"] == "edge-consumed"
    assert response.json()["token"] != browser
    assert (
        auth._verified_session_token_claims(response.json()["token"])["purpose"]
        == auth.ACCOUNT_SESSION_PURPOSE
    )
    assert store.verify(response.json()["token"]) == "fixture@example.com"
    assert (
        api.post(
            "/api/auth/scout/exchange", json={"code": code, "verifier": "v" * 43}
        ).status_code
        == 401
    )


def test_edge_consumed_exchange_never_bypasses_access_or_parent_revocation(flow):
    api, store, browser = flow
    code = code_from(create(api, browser))
    assertion = api.headers.pop("Cf-Access-Jwt-Assertion")
    assert (
        api.post(
            "/api/auth/scout/exchange", json={"code": code, "verifier": "v" * 43}
        ).status_code
        == 401
    )
    api.headers["Cf-Access-Jwt-Assertion"] = assertion
    store.revoke(browser)
    assert (
        api.post(
            "/api/auth/scout/exchange", json={"code": code, "verifier": "v" * 43}
        ).status_code
        == 401
    )


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


def test_browser_revocation_after_exchange_does_not_revoke_native(flow):
    api, store, browser = flow
    native = exchange(api, code_from(create(api, browser))).json()["token"]
    store.revoke(browser)
    assert store.verify(browser) is None
    assert auth.resolve_account_session_subject(native) == "fixture@example.com"
    assert store.verify(native) == "fixture@example.com"


def test_native_revocation_leaves_browser_and_other_native_sessions_live(flow):
    api, store, browser = flow
    first = exchange(api, code_from(create(api, browser))).json()["token"]
    second = exchange(api, code_from(create(api, browser))).json()["token"]
    assert first != second
    store.revoke(first)
    assert store.verify(first) is None
    assert store.verify(browser) == store.verify(second) == "fixture@example.com"


def test_atomic_replay_cannot_create_second_native_session(flow):
    api, store, browser = flow
    code = code_from(create(api, browser))
    first = exchange(api, code)
    assert first.status_code == 200
    assert exchange(api, code).status_code == 401
    assert len(list(store._client().scan_iter("session:*"))) == 2


@pytest.mark.parametrize(
    "extra",
    [
        {"Cookie": "gc_session=synthetic"},
        {"Cookie": "codexify_hosted_room_session=synthetic"},
        {"X-API-Key": "synthetic"},
    ],
)
def test_conflicting_native_exchange_credentials_are_rejected(flow, extra):
    api, _, browser = flow
    code = code_from(create(api, browser))
    response = api.post(
        "/api/auth/scout/exchange",
        json={"code": code, "verifier": "v" * 43},
        headers={"Authorization": "Bearer oauth:fixture-ingress", **extra},
    )
    assert response.status_code == 400
    assert exchange(api, code).status_code == 200


def test_browser_bearer_and_account_cookie_conflict_is_rejected(flow):
    api, _, browser = flow
    response = api.post(
        "/api/auth/scout/handoff",
        json={"state": "s" * 43, "challenge": challenge_for("v" * 43)},
        headers={
            "Origin": "https://preview.codexify.space",
            "Authorization": "Bearer " + browser,
            "Cookie": "gc_session=" + browser,
        },
    )
    assert response.status_code == 400


def test_canonical_logout_revokes_only_native_and_protected_read_denies_it(
    flow, monkeypatch
):
    from contextlib import contextmanager

    from fastapi import Depends

    from guardian.core.dependencies import verify_account_session
    from guardian.routes import auth as auth_routes

    api, store, browser = flow
    native = exchange(api, code_from(create(api, browser))).json()["token"]

    class PresenceDB:
        @contextmanager
        def get_session(self):
            class Session:
                def commit(self):
                    pass

            yield Session()

    monkeypatch.setattr(auth_routes, "_auth_db", lambda: PresenceDB())
    monkeypatch.setattr(auth_routes, "end_account_presence", lambda *_: None)
    api.app.include_router(auth_routes.api_router)

    @api.app.get("/protected")
    def protected(subject=Depends(verify_account_session)):
        return {"ok": True}

    assert (
        api.get("/protected", headers={"Authorization": "Bearer " + native}).status_code
        == 200
    )
    assert (
        api.post(
            "/api/auth/logout", headers={"Authorization": "Bearer " + native}
        ).status_code
        == 200
    )
    assert store.verify(native) is None
    assert (
        api.get("/protected", headers={"Authorization": "Bearer " + native}).status_code
        == 401
    )
    assert (
        api.get(
            "/protected", headers={"Authorization": "Bearer " + browser}
        ).status_code
        == 200
    )


def test_concurrent_redemption_issues_exactly_one_native_session(flow):
    from concurrent.futures import ThreadPoolExecutor

    api, store, browser = flow
    code = code_from(create(api, browser))
    with ThreadPoolExecutor(max_workers=4) as workers:
        statuses = list(
            workers.map(lambda _: exchange(api, code).status_code, range(4))
        )
    assert statuses.count(200) == 1
    assert statuses.count(401) == 3
    assert len(list(store._client().scan_iter("session:*"))) == 2
