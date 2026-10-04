import json
import logging
from uuid import uuid4

import pytest

from guardian.core import scout_qualification as q
from guardian.routes import auth as auth_routes
from guardian.routes import scout_auth
from tests.identity.test_scout_handoff_routes import flow  # noqa: F401
from tests.identity.test_scout_handoff_routes import code_from, create


@pytest.fixture(autouse=True)
def clear_receipts():
    with q._lock:
        q._attempts.clear()
    yield
    with q._lock:
        q._attempts.clear()


def test_ephemeral_bounded_allowlisted_receipt_never_contains_credentials(
    caplog, monkeypatch
):
    from guardian.utils.log_safety import install_safe_logging

    install_safe_logging()
    identity = str(uuid4())
    assert q.begin(identity)
    with caplog.at_level(logging.INFO):
        q.observe(identity, "account_login", "passed", 200)
        q.observe(identity, "account_login", "failed", 401)
        q.observe(identity, "fixture-secret-stage", "passed", 200)
        q.observe("fixture-secret-token", "account_login", "failed", 401)
        q.observe(identity, "native_session", "fixture-secret-status", 200)
    receipt = q.snapshot(identity)
    assert receipt == {
        "attempt_id": identity,
        "stages": {"account_login": {"status": "passed", "http_status": 200}},
    }
    assert identity in caplog.text
    assert "account_login" in caplog.text
    assert "fixture-secret" not in caplog.text + json.dumps(receipt)
    original_expiry = q._attempts[identity][0]
    assert q.begin(identity)
    assert q._attempts[identity][0] == original_expiry
    monkeypatch.setattr(q.time, "monotonic", lambda: original_expiry + 1)
    assert q.snapshot(identity) is None


def test_capacity_and_invalid_inputs_cannot_create_unbounded_retention():
    assert not q.begin("not-an-attempt")
    for _ in range(q.LIMIT):
        assert q.begin(str(uuid4()))
    assert not q.begin(str(uuid4()))
    assert len(q._attempts) == q.LIMIT


def native_headers(identity=None):
    return {
        "Authorization": "Bearer oauth:fixture-ingress",
        **({q.HEADER: identity} if identity else {}),
    }


@pytest.mark.parametrize(
    ("headers", "reason"),
    [
        ({}, "missingAuthorization"),
        ({"Authorization": "Bearer fixture-private-token"}, "unsupportedAuthorization"),
        (
            {
                **native_headers(),
                "X-Guardian-Account-Session": "fixture-private-session",
            },
            "conflictingSelectors",
        ),
        (
            {**native_headers(), "Cookie": "gc_session=fixture-private-cookie"},
            "conflictingSelectors",
        ),
        (
            [
                ("Authorization", "Bearer oauth:fixture-a"),
                ("Authorization", "Bearer oauth:fixture-b"),
            ],
            "ambiguousAuthorization",
        ),
    ],
)
def test_native_rejection_exposes_only_fixed_shape_classification(
    flow, headers, reason
):
    api, _, _ = flow
    identity = str(uuid4())
    response = api.put("/api/auth/scout/qualification/" + identity, headers=headers)
    assert response.status_code == 400
    assert response.json() == {"detail": "Native admission required"}
    assert response.headers["X-Scout-Qualification-Rejection"] == reason
    assert "fixture-" not in response.text + str(response.headers)
    assert q.snapshot(identity) is None


def test_qualification_requires_existing_hosted_admission_but_confers_no_session(
    flow, monkeypatch
):
    api, store, browser = flow
    identity = str(uuid4())
    path = "/api/auth/scout/qualification/" + identity
    assert api.put(path, headers=native_headers()).status_code == 200
    assert api.get(path, headers=native_headers()).json() == {
        "attempt_id": identity,
        "stages": {},
    }
    assert (
        api.get(path, headers={"Authorization": "Bearer " + browser}).status_code == 400
    )
    assert (
        api.get(path, headers={**native_headers(), "X-API-Key": "fixture"}).status_code
        == 400
    )
    assert (
        api.get(
            path, headers={**native_headers(), "Host": "personal.example"}
        ).status_code
        == 400
    )
    monkeypatch.setattr(
        scout_auth,
        "verify_access_assertion",
        lambda _: (_ for _ in ()).throw(ValueError()),
    )
    assert api.get(path, headers=native_headers()).status_code == 401
    assert len(list(store._client().scan_iter("session:*"))) == 1


def test_browser_ready_is_not_account_confirmation_and_callback_preparation_is_distinct(
    flow,
):
    api, _, browser = flow
    identity = str(uuid4())
    path = "/api/auth/scout/qualification/" + identity
    assert api.put(path, headers=native_headers()).status_code == 200
    origin = {"Origin": "https://preview.codexify.space"}
    assert (
        api.post(
            path + "/browser", json={"event": "loaded"}, headers=origin
        ).status_code
        == 200
    )
    assert "account_login" not in q.snapshot(identity)["stages"]
    assert (
        api.post(
            path + "/browser", json={"event": "account_confirmed"}, headers=origin
        ).status_code
        == 401
    )
    assert (
        q.snapshot(identity)["stages"].get("account_login", {}).get("status")
        != "passed"
    )
    assert (
        api.post(
            path + "/browser",
            json={"event": "account_confirmed"},
            headers={**origin, "Authorization": "Bearer " + browser},
        ).status_code
        == 200
    )
    assert q.snapshot(identity)["stages"]["account_login"]["status"] == "passed"
    assert (
        api.post(
            path + "/browser",
            json={"event": "loaded", "token": "fixture-secret"},
            headers=origin,
        ).status_code
        == 400
    )
    assert (
        api.post(
            path + "/browser",
            json={"event": "loaded"},
            headers={"Origin": "https://other.example"},
        ).status_code
        == 400
    )


def test_real_handoff_and_exchange_correlate_without_exporting_any_auth_material(flow):
    from guardian.core.scout_handoff import challenge_for

    api, store, browser = flow
    identity = str(uuid4())
    path = "/api/auth/scout/qualification/" + identity
    api.put(path, headers=native_headers())
    created = api.post(
        "/api/auth/scout/handoff",
        json={"state": "s" * 43, "challenge": challenge_for("v" * 43)},
        headers={
            "Origin": "https://preview.codexify.space",
            "Authorization": "Bearer " + browser,
            q.HEADER: identity,
        },
    )
    code = code_from(created)
    response = api.post(
        "/api/auth/scout/exchange",
        json={"code": code, "verifier": "v" * 43},
        headers=native_headers(identity),
    )
    assert response.status_code == 200
    assert response.headers["X-Scout-Native-Session-Issued"] == "true"
    assert response.json()["token"] != browser
    receipt_response = api.get(path, headers=native_headers())
    assert receipt_response.headers["Cache-Control"] == "no-store"
    stages = receipt_response.json()["stages"]
    assert stages == {
        name: {"status": "passed", "http_status": 200}
        for name in (
            "account_login",
            "handoff_redirect",
            "handoff_exchange",
            "native_session",
        )
    }
    for sensitive in (
        code,
        browser,
        response.json()["token"],
        "v" * 43,
        "s" * 43,
        "fixture@example.com",
    ):
        assert sensitive not in receipt_response.text


def test_canonical_login_success_and_failure_have_safe_correlation_without_changed_inputs(
    monkeypatch,
):
    from fastapi import HTTPException
    from starlette.requests import Request

    identity = str(uuid4())
    q.begin(identity)
    request = Request(
        {"type": "http", "headers": [(b"x-scout-auth-attempt", identity.encode())]}
    )
    credentials = auth_routes.AuthLoginRequest(
        username="fixture-user", password="fixture-password"
    )
    seen = []

    def rejected(body):
        seen.append(body)
        raise HTTPException(status_code=401, detail="fixture-private-detail")

    monkeypatch.setattr(auth_routes, "_login_user", rejected)
    with pytest.raises(HTTPException):
        auth_routes.login_user(credentials, request)
    assert seen == [credentials]
    assert q.snapshot(identity)["stages"]["account_login"] == {
        "status": "failed",
        "http_status": 401,
    }
    expected = {"token": "fixture-token", "user_id": "fixture-user", "expires_at": 100}
    monkeypatch.setattr(auth_routes, "_login_user", lambda body: expected)
    assert auth_routes.login_user(credentials, request) is expected
    assert q.snapshot(identity)["stages"]["account_login"]["status"] == "passed"
    assert "fixture-" not in json.dumps(q.snapshot(identity))


def test_protected_read_receipt_requires_selected_account_validation_and_actual_response(
    monkeypatch,
):
    from fastapi import HTTPException
    from starlette.responses import JSONResponse
    from starlette.testclient import TestClient

    from guardian.core import scout_account_transport as transport

    identity = str(uuid4())
    q.begin(identity)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setattr(transport, "verify_access_assertion", lambda _: None)
    admitted = []

    def account(scope):
        admitted.append(True)
        if dict(scope["headers"])[b"authorization"] != b"Bearer fixture-account":
            raise HTTPException(status_code=401)

    monkeypatch.setattr(transport, "verify_selected_account", account)

    async def downstream(scope, receive, send):
        await JSONResponse({"threads": []})(scope, receive, send)

    api = TestClient(
        transport.ScoutAccountTransportMiddleware(downstream),
        base_url="https://preview.codexify.space",
    )
    headers = {
        **native_headers(identity),
        "CF-Access-Jwt-Assertion": "fixture-assertion",
        "X-Guardian-Account-Session": "fixture-bad-account",
    }
    assert api.get("/api/chat/threads", headers=headers).status_code == 401
    assert q.snapshot(identity)["stages"]["protected_read"] == {
        "status": "failed",
        "http_status": 401,
    }
    headers["X-Guardian-Account-Session"] = "fixture-account"
    assert api.get("/api/chat/threads", headers=headers).status_code == 200
    assert q.snapshot(identity)["stages"]["protected_read"] == {
        "status": "passed",
        "http_status": 200,
    }
    assert len(admitted) == 2
    assert "fixture-" not in json.dumps(q.snapshot(identity))


def test_bad_callback_exchange_and_store_failure_report_different_stages(
    flow, monkeypatch
):
    api, store, browser = flow
    identity = str(uuid4())
    q.begin(identity)
    invalid = api.post(
        "/api/auth/scout/exchange",
        json={
            "code": "fixture-sensitive-code",
            "verifier": "fixture-sensitive-verifier",
        },
        headers=native_headers(identity),
    )
    assert invalid.status_code == 400
    assert q.snapshot(identity)["stages"]["handoff_exchange"] == {
        "status": "failed",
        "http_status": 400,
    }
    code = code_from(create(api, browser))

    def failed_store(*args):
        raise RuntimeError("fixture-sensitive-store-detail")

    monkeypatch.setattr(type(store), "store", lambda self, *args: failed_store(*args))
    with pytest.raises(RuntimeError):
        api.post(
            "/api/auth/scout/exchange",
            json={"code": code, "verifier": "v" * 43},
            headers=native_headers(identity),
        )
    receipt = q.snapshot(identity)
    assert receipt["stages"]["handoff_exchange"]["status"] == "passed"
    assert receipt["stages"]["native_session"] == {
        "status": "failed",
        "http_status": 500,
    }
    assert "fixture-sensitive" not in json.dumps(receipt)
