from __future__ import annotations

from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from guardian.core import auth, dependencies
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.protocol_tokens import ACCOUNT_AUTH_FAILURE_HEADER, ErrorCode

SECRET = "mixed-principal-boundary-test-secret"
API_KEY = "mixed-principal-operator-key"


def _client() -> TestClient:
    app = FastAPI()

    @app.get("/account")
    def account(_credential: str = Depends(dependencies.require_account_session)):
        return {"ok": True}

    @app.get("/generic-account")
    def generic_account(_credential: str = Depends(dependencies.require_api_key)):
        return {"ok": True}

    @app.get("/legacy-account")
    def legacy_account(_credential: str = Depends(auth.require_auth)):
        return {"ok": True}

    @app.get("/operator")
    def operator(_credential: str = Depends(dependencies.require_operator_auth)):
        return {"ok": True}

    return TestClient(app)


def _assert_mixed(response) -> None:
    assert response.status_code == 400
    assert ACCOUNT_AUTH_FAILURE_HEADER.lower() not in response.headers
    assert response.json()["detail"] == {
        "error": ErrorCode.MIXED_PRINCIPAL_CREDENTIALS.value,
        "message": "Conflicting authentication contexts",
    }


def _configure_remote(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", SECRET)
    monkeypatch.setenv("GUARDIAN_API_KEY", API_KEY)
    monkeypatch.delenv("GUARDIAN_API_KEYS", raising=False)
    monkeypatch.setattr(
        dependencies,
        "get_settings",
        lambda: SimpleNamespace(GUARDIAN_API_KEY=API_KEY, GUARDIAN_API_KEYS=None),
    )


def test_account_and_expired_operator_session_are_rejected_before_validation(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    expired_operator, _ = issue_session_token(
        subject="operator-a", purpose=OPERATOR_SESSION_PURPOSE, ttl_seconds=-60
    )
    validation_calls: list[str] = []

    def resolve_account(_token):
        validation_calls.append("account")
        raise AssertionError("credential validation must not run for mixed input")

    monkeypatch.setattr(dependencies, "resolve_account_session_subject", resolve_account)
    response = _client().get(
        "/account",
        headers={"Authorization": f"Bearer {account}"},
        cookies={"gc_session": expired_operator},
    )

    _assert_mixed(response)
    assert validation_calls == []


def test_account_session_and_guest_selector_are_rejected_before_validation(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    validation_calls: list[str] = []

    def resolve_account(_token):
        validation_calls.append("account")
        raise AssertionError("credential validation must not run for mixed input")

    monkeypatch.setattr(dependencies, "resolve_account_session_subject", resolve_account)
    response = _client().get(
        "/account",
        headers={"Authorization": f"Bearer {account}"},
        cookies={"codexify_hosted_room_session": "unvalidated-guest"},
    )

    _assert_mixed(response)
    assert validation_calls == []


def test_generic_account_dependency_rejects_mixed_lanes_before_session_lookup(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    operator, _ = issue_session_token(
        subject="operator-a", purpose=OPERATOR_SESSION_PURPOSE
    )
    lookups: list[str] = []

    def resolve_session(_authorization, _gc_session):
        lookups.append("session-store")
        raise AssertionError("session lookup must not run for mixed input")

    monkeypatch.setattr(dependencies, "resolve_session_user_id", resolve_session)
    response = _client().get(
        "/generic-account",
        headers={"Authorization": f"Bearer {account}"},
        cookies={"gc_session": operator},
    )

    _assert_mixed(response)
    assert lookups == []


def test_legacy_account_dependency_rejects_mixed_lanes_before_validation(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    operator, _ = issue_session_token(
        subject="operator-a", purpose=OPERATOR_SESSION_PURPOSE
    )
    validation_calls: list[str] = []

    def resolve_account(_token):
        validation_calls.append("account")
        raise AssertionError("credential validation must not run for mixed input")

    monkeypatch.setattr(auth, "resolve_account_session_subject", resolve_account)
    response = _client().get(
        "/legacy-account",
        headers={"Authorization": f"Bearer {account}"},
        cookies={"gc_session": operator},
    )

    _assert_mixed(response)
    assert validation_calls == []


def test_operator_key_and_account_session_are_rejected_before_operator_validation(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    validation_calls: list[str] = []
    original = dependencies.verify_session_token_for_purpose

    def track_validation(token, purpose):
        validation_calls.append(purpose)
        return original(token, purpose)

    monkeypatch.setattr(
        dependencies, "verify_session_token_for_purpose", track_validation
    )
    response = _client().get(
        "/operator",
        headers={
            "Authorization": f"Bearer {account}",
            "X-API-Key": API_KEY,
        },
    )

    _assert_mixed(response)
    assert validation_calls == []


def test_guest_selector_and_malformed_authorization_are_rejected_before_guest_decode(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    from guardian.routes import hosted_room_guest

    calls: list[str] = []

    def fail_decode(_token):
        calls.append("decode")
        raise AssertionError("guest token decoding must not run for mixed input")

    def fail_db():
        calls.append("database")
        raise AssertionError("resource lookup must not run for mixed input")

    monkeypatch.setattr(hosted_room_guest, "decode_principal", fail_decode)
    monkeypatch.setattr(hosted_room_guest, "_require_db", fail_db)
    app = FastAPI()
    app.include_router(hosted_room_guest.router)

    response = TestClient(app).get(
        "/api/hosted-room-session",
        headers={"Authorization": "Bearer malformed-token"},
        cookies={"codexify_hosted_room_session": "malformed-guest-token"},
    )

    _assert_mixed(response)
    assert calls == []


def test_guest_selector_and_operator_api_key_are_rejected_at_operator_seam(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    response = _client().get(
        "/operator",
        headers={"X-API-Key": API_KEY},
        cookies={"codexify_hosted_room_session": "not-validated-here"},
    )
    _assert_mixed(response)


def test_two_operator_selectors_remain_one_principal_lane(monkeypatch):
    _configure_remote(monkeypatch)
    operator, _ = issue_session_token(
        subject="operator-a", purpose=OPERATOR_SESSION_PURPOSE
    )
    response = _client().get(
        "/operator",
        headers={
            "Authorization": f"Bearer {operator}",
            "X-API-Key": API_KEY,
        },
    )
    assert response.status_code == 200, response.text


def test_local_operator_api_key_behavior_is_outside_remote_mixed_rule(monkeypatch):
    _configure_remote(monkeypatch)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    response = _client().get(
        "/operator",
        headers={"X-API-Key": API_KEY},
        cookies={"codexify_hosted_room_session": "unused-local-cookie"},
    )
    assert response.status_code == 200, response.text
