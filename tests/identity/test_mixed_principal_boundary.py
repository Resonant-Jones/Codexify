from __future__ import annotations

import base64
import json
import hashlib
import hmac
import sys

import pytest

from types import SimpleNamespace
from unittest.mock import Mock

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

    monkeypatch.setattr(
        dependencies, "resolve_account_session_subject", resolve_account
    )
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

    monkeypatch.setattr(
        dependencies, "resolve_account_session_subject", resolve_account
    )
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


# Reuse the existing SQLite invitation fixture without changing its source.
from guardian.tests.routes.test_hosted_room_guest import (
    _create_invite,
    _create_room,
    client as _invitation_client,
    mock_db as _invitation_db,
    test_engine as _invitation_engine,
)


invitation_client = _invitation_client
mock_db = _invitation_db
test_engine = _invitation_engine


def _presence_token(payload: bytes, *, jwt: bool = False) -> str:
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    if not jwt:
        return f"{encoded}.unverified"
    signing_input = f"eyJhbGciOiJIUzI1NiJ9.{encoded}"
    signature = hmac.new(
        SECRET.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{signing_input}.{signature_b64}"


@pytest.mark.parametrize(
    "path", ["/account", "/generic-account", "/legacy-account", "/operator"]
)
@pytest.mark.parametrize(
    "jwt_purpose", [ACCOUNT_SESSION_PURPOSE, OPERATOR_SESSION_PURPOSE]
)
def test_jwt_presence_is_mixed_before_any_validation(monkeypatch, path, jwt_purpose):
    _configure_remote(monkeypatch)
    other = (
        OPERATOR_SESSION_PURPOSE
        if jwt_purpose == ACCOUNT_SESSION_PURPOSE
        else ACCOUNT_SESSION_PURPOSE
    )
    native, _ = issue_session_token(subject="other-lane", purpose=other)
    jwt_token = _presence_token(json.dumps({"purpose": jwt_purpose}).encode(), jwt=True)
    forbidden = Mock(side_effect=AssertionError("mixed input must not be validated"))
    monkeypatch.setattr(dependencies, "resolve_account_session_subject", forbidden)
    monkeypatch.setattr(auth, "resolve_account_session_subject", forbidden)
    monkeypatch.setattr(dependencies, "verify_session_token_for_purpose", forbidden)
    response = _client().get(
        path,
        headers={"Authorization": f"Bearer {jwt_token}"},
        cookies={"gc_session": native},
    )
    _assert_mixed(response)
    forbidden.assert_not_called()


@pytest.mark.parametrize("jwt", [False, True], ids=["opaque", "jwt"])
@pytest.mark.parametrize("decoder", ["default", "python"])
@pytest.mark.parametrize(
    "payload",
    [
        b'{"purpose":"account_session","padding":'
        + b"[" * 2500
        + b"0"
        + b"]" * 2500
        + b"}",
        b'{"purpose":"account_session","purpose":"operator_session"}',
        b'{"purpose":[]}',
        b"[]",
        b"null",
        b"\xff",
        b'{"purpose":"account_session","number":' + b"9" * 5000 + b"}",
    ],
    ids=["deep", "duplicate", "nonstring", "list", "null", "utf8", "integer-limit"],
)
def test_malformed_or_deep_presence_payload_is_not_an_account_or_a_500(
    monkeypatch, jwt, payload, decoder
):
    _configure_remote(monkeypatch)
    token = _presence_token(payload, jwt=jwt)
    # Exercise both real stdlib scanners: the Python fallback raises on deep
    # JSON even where the installed C scanner accepts it. Classification never
    # grants authentication. Restore all test-only parser/limit settings.
    if decoder == "python":
        monkeypatch.setattr(json.scanner, "make_scanner", json.scanner.py_make_scanner)
    previous_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(1000)
        purpose = auth._unverified_session_purpose(token)
        if decoder == "default" and b'"padding"' in payload:
            assert purpose in (None, ACCOUNT_SESSION_PURPOSE)
        else:
            assert purpose is None
        with TestClient(_client().app, raise_server_exceptions=False) as client:
            response = client.get(
                "/account", headers={"Authorization": f"Bearer {token}"}
            )
        assert response.status_code == 401
    finally:
        sys.setrecursionlimit(previous_limit)


@pytest.mark.parametrize("token", ["é.bad", "!.bad", "a.b.c.d", "x" * 16385])
def test_undecodable_or_oversized_presence_is_not_a_500(monkeypatch, token):
    _configure_remote(monkeypatch)
    assert auth._unverified_session_purpose(token) is None
    with TestClient(_client().app, raise_server_exceptions=False) as client:
        assert (
            client.get(
                "/account",
                headers={"Authorization": b"Bearer " + token.encode("utf-8")},
            ).status_code
            == 401
        )


@pytest.mark.parametrize(
    "mode,exposure", [("remote", "local_safe"), ("local", "private_preview")]
)
@pytest.mark.parametrize(
    "mix", ["account_operator", "guest_account", "guest_operator"]
)
def test_mixed_invitation_exchange_keeps_the_invitation_unconsumed(
    invitation_client, mock_db, monkeypatch, mode, exposure, mix
):
    from guardian.routes import hosted_room_guest
    from guardian.db.models import HostedRoomInvite, HostedRoomParticipant
    from sqlalchemy import select

    room_id = _create_room(invitation_client)
    invite_id, token = _create_invite(invitation_client, room_id)
    _configure_remote(monkeypatch)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", mode)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", exposure)
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    operator, _ = issue_session_token(
        subject="operator-a", purpose=OPERATOR_SESSION_PURPOSE
    )
    cookies = (
        {"gc_session": operator}
        if mix == "account_operator"
        else {"codexify_hosted_room_session": "malformed-guest"}
    )
    db_access = Mock(wraps=hosted_room_guest._require_db)
    monkeypatch.setattr(hosted_room_guest, "_require_db", db_access)
    response = invitation_client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
        headers={
            "Authorization": f"Bearer {operator if mix == 'guest_operator' else account}"
        },
        cookies=cookies,
    )
    _assert_mixed(response)
    db_access.assert_not_called()
    assert "set-cookie" not in response.headers
    with mock_db.get_session() as session:
        invite = session.get(HostedRoomInvite, invite_id)
        assert invite.status == "pending" and invite.accepted_at is None
        assert (
            session.scalar(
                select(HostedRoomParticipant).where(
                    HostedRoomParticipant.invitation_id == invite_id
                )
            )
            is None
        )
    invitation_client.cookies.clear()
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    accepted = invitation_client.post(
        "/api/hosted-room-invitations/exchange", json={"invitation_token": token}
    )
    assert accepted.status_code == 200, accepted.text
    with mock_db.get_session() as session:
        assert session.get(HostedRoomInvite, invite_id).status == "accepted"


@pytest.mark.parametrize(
    "mode,exposure", [("remote", "local_safe"), ("local", "private_preview")]
)
@pytest.mark.parametrize("selector", ["authorization", "gc_session"])
@pytest.mark.parametrize(
    "credential_kind",
    [
        "account_session",
        "operator_session",
        "account_jwt",
        "operator_jwt",
        "expired_operator",
        "malformed",
    ],
)
def test_guest_bootstrap_rejects_non_guest_selector_before_lookup_and_allows_clean_retry(
    invitation_client, mock_db, monkeypatch, mode, exposure, selector, credential_kind
):
    from guardian.routes import hosted_room_guest
    from guardian.db.models import HostedRoomInvite, HostedRoomParticipant
    from sqlalchemy import select

    room_id = _create_room(invitation_client)
    invite_id, token = _create_invite(invitation_client, room_id)
    _configure_remote(monkeypatch)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", mode)
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", exposure)
    purpose = (
        ACCOUNT_SESSION_PURPOSE
        if credential_kind.startswith("account")
        else OPERATOR_SESSION_PURPOSE
    )
    if credential_kind == "malformed":
        credential = "malformed-session-material"
    elif credential_kind.endswith("jwt"):
        credential = _presence_token(json.dumps({"purpose": purpose}).encode(), jwt=True)
    else:
        credential, _ = issue_session_token(
            subject="bootstrap-test",
            purpose=purpose,
            ttl_seconds=-60 if credential_kind == "expired_operator" else 3600,
        )

    forbidden_validation = Mock(
        side_effect=AssertionError("guest bootstrap must not authenticate other lanes")
    )
    monkeypatch.setattr(auth, "verify_session_token", forbidden_validation)
    monkeypatch.setattr(
        dependencies, "resolve_account_session_subject", forbidden_validation
    )
    monkeypatch.setattr(hosted_room_guest, "decode_principal", forbidden_validation)
    db_access = Mock(wraps=hosted_room_guest._require_db)
    guest_token = Mock(wraps=hosted_room_guest.issue_guest_session_token)
    guest_cookie = Mock(wraps=hosted_room_guest.set_session_cookie)
    monkeypatch.setattr(hosted_room_guest, "_require_db", db_access)
    monkeypatch.setattr(hosted_room_guest, "issue_guest_session_token", guest_token)
    monkeypatch.setattr(hosted_room_guest, "set_session_cookie", guest_cookie)
    invitation_client.cookies.clear()
    headers = (
        {"Authorization": f"Bearer {credential}"}
        if selector == "authorization"
        else {}
    )
    if selector == "gc_session":
        invitation_client.cookies.set("gc_session", credential)
    response = invitation_client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
        headers=headers,
    )

    _assert_mixed(response)
    db_access.assert_not_called()
    forbidden_validation.assert_not_called()
    guest_token.assert_not_called()
    guest_cookie.assert_not_called()
    assert "set-cookie" not in response.headers
    if selector == "gc_session":
        assert invitation_client.cookies.get("gc_session") == credential
    with mock_db.get_session() as session:
        invite = session.get(HostedRoomInvite, invite_id)
        assert invite.status == "pending" and invite.accepted_at is None
        assert (
            session.scalars(
                select(HostedRoomParticipant).where(
                    HostedRoomParticipant.invitation_id == invite_id
                )
            ).all()
            == []
        )

    invitation_client.cookies.clear()
    accepted = invitation_client.post(
        "/api/hosted-room-invitations/exchange", json={"invitation_token": token}
    )
    assert accepted.status_code == 200, accepted.text
    assert "codexify_hosted_room_session=" in accepted.headers["set-cookie"]
    guest_token.assert_called_once()
    guest_cookie.assert_called_once()
    with mock_db.get_session() as session:
        invite = session.get(HostedRoomInvite, invite_id)
        assert invite.status == "accepted" and invite.accepted_at is not None
        participants = session.scalars(
            select(HostedRoomParticipant).where(
                HostedRoomParticipant.invitation_id == invite_id
            )
        ).all()
        assert len(participants) == 1
        assert participants[0].id == accepted.json()["participant"]["id"]


def test_local_invitation_exchange_preserves_existing_supplemental_credentials(
    invitation_client, monkeypatch
):
    room_id = _create_room(invitation_client)
    _, token = _create_invite(invitation_client, room_id)
    _configure_remote(monkeypatch)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    operator, _ = issue_session_token(
        subject="operator", purpose=OPERATOR_SESSION_PURPOSE
    )
    response = invitation_client.post(
        "/api/hosted-room-invitations/exchange",
        json={"invitation_token": token},
        headers={"Authorization": "Bearer supplemental-local-material"},
        cookies={
            "gc_session": operator,
            "codexify_hosted_room_session": "stale-local-selector",
        },
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("purpose", [ACCOUNT_SESSION_PURPOSE, OPERATOR_SESSION_PURPOSE])
def test_jwt_presence_alone_does_not_grant_a_principal(monkeypatch, purpose):
    _configure_remote(monkeypatch)
    token = _presence_token(json.dumps({"purpose": purpose}).encode(), jwt=True)
    assert auth._unverified_session_purpose(token) == purpose
    for path in ["/account", "/operator"]:
        response = _client().get(
            path, headers={"Authorization": f"Bearer {token}", "X-API-Key": ""}
        )
        assert response.status_code == 401


def test_account_jwt_and_raw_operator_key_are_mixed_before_verification(monkeypatch):
    _configure_remote(monkeypatch)
    token = _presence_token(
        json.dumps({"purpose": ACCOUNT_SESSION_PURPOSE, "exp": 0}).encode(), jwt=True
    )
    validation = Mock(
        side_effect=AssertionError("mixed credentials must not be verified")
    )
    monkeypatch.setattr(dependencies, "verify_session_token_for_purpose", validation)
    response = _client().get(
        "/operator", headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY}
    )
    _assert_mixed(response)
    validation.assert_not_called()


def test_account_cookie_and_bearer_operator_key_are_mixed_before_verification(
    monkeypatch,
):
    _configure_remote(monkeypatch)
    account, _ = issue_session_token(
        subject="account-a", purpose=ACCOUNT_SESSION_PURPOSE
    )
    validation = Mock(
        side_effect=AssertionError("mixed credentials must not be verified")
    )
    monkeypatch.setattr(dependencies, "verify_session_token_for_purpose", validation)
    response = _client().get(
        "/operator",
        headers={"Authorization": f"Bearer {API_KEY}"},
        cookies={"gc_session": account},
    )

    _assert_mixed(response)
    validation.assert_not_called()
