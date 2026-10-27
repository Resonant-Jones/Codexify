"""Account-route identity must follow the verified account credential.

ADR-092 and ADR-094 make Guardian the authority for account-scoped work: the
account that authenticated a request is the account that owns the resources it
reads. The account gate admits a stateless HS256 account-session JWT. The
account-user dependency that follows it must resolve that same account, not
the configured single-user fallback.

These tests drive the real authentication dependencies through a real FastAPI
app and observe the identity that reaches a bounded resource-store spy. They
never override a dependency to return the expected identity.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.core import auth, dependencies
from guardian.core.auth import ACCOUNT_SESSION_PURPOSE

ACCOUNT_A = "account-a@example.invalid"
ACCOUNT_B = "account-b@example.invalid"
LOCAL_FALLBACK = "local"
JWT_SECRET = "account-jwt-secret"


def _account_jwt(
    subject: str = ACCOUNT_A,
    *,
    purpose: str | None = ACCOUNT_SESSION_PURPOSE,
    secret: str = JWT_SECRET,
    expires: int | None = None,
) -> str:
    """Build a correctly signed HS256 account-session JWT."""
    jwt = pytest.importorskip("jwt")
    claims = {
        "sub": subject,
        "exp": int(time.time()) + 3600 if expires is None else expires,
    }
    if purpose is not None:
        claims["purpose"] = purpose
    return jwt.encode(claims, secret, algorithm="HS256")


class _SessionStore:
    """Minimal stored-session fake: native tokens only."""

    def __init__(self, mapping: dict[str, str] | None = None) -> None:
        self.mapping = mapping or {}

    def verify(self, token: str) -> str | None:
        return self.mapping.get(token)

    def store(self, token: str, user_id: str, ttl_seconds: int) -> None:
        self.mapping[token] = user_id


class _ResourceStoreSpy:
    """Bounded resource-store spy that records the read identity."""

    def __init__(self, owner: str) -> None:
        self.owner = owner
        self.calls: list[tuple[str, str | None]] = []

    def get_account_run(
        self, run_id: str, *, user_id: str | None
    ) -> dict[str, Any] | None:
        self.calls.append(("get_account_run", user_id))
        if user_id != self.owner:
            return None
        return {"run_id": run_id, "account_id": self.owner}


def _account_app(spy: _ResourceStoreSpy) -> FastAPI:
    """An account-scoped route built on the real authentication dependencies."""
    app = FastAPI()

    @app.get(
        "/account/run/{run_id}",
        dependencies=[Depends(dependencies.require_account_session)],
    )
    async def read_run(
        run_id: str,
        account_id: str = Depends(dependencies.get_account_user),
    ) -> dict[str, Any]:
        run = spy.get_account_run(run_id, user_id=account_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run_not_found")
        return {"ok": True, "run": run}

    return app


def _client(app: FastAPI, headers: dict[str, str] | None = None) -> TestClient:
    """Build a client for one authentication lane.

    The repository TestClient seeds X-API-Key globally, and the remote
    boundary rejects a static key, so each case states its own credential
    lane explicitly.
    """
    merged = {"X-API-Key": ""}
    merged.update(headers or {})
    return TestClient(app, headers=merged)


@pytest.fixture
def remote_boundary(monkeypatch: pytest.MonkeyPatch) -> _SessionStore:
    """Configure the supported remote account boundary."""
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", JWT_SECRET)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    store = _SessionStore()
    monkeypatch.setattr("guardian.core.session_store.get_session_store", lambda: store)
    monkeypatch.setattr(
        "guardian.core.auth_dependencies.get_session_store", lambda: store
    )
    return store


def test_remote_account_jwt_resolves_the_verified_account_subject(
    remote_boundary: _SessionStore,
) -> None:
    """The account gate and the account-user dependency must agree.

    The gate admits the credential, so the account identity it carries must be
    the identity the resource lookup runs under.
    """
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))
    token = _account_jwt(ACCOUNT_A)
    headers = {"Authorization": f"Bearer {token}"}

    # The account-session verifier accepts this credential.
    assert dependencies.verify_account_session(
        None, None, headers["Authorization"], None
    )

    response = client.get("/account/run/run-owned", headers=headers)
    assert response.status_code == 200, response.text

    # The resource lookup ran under the verified account subject.
    assert spy.calls == [("get_account_run", ACCOUNT_A)]
    assert spy.calls[0][1] != dependencies.get_single_user_id()


def test_remote_account_jwt_cannot_read_another_accounts_resource(
    remote_boundary: _SessionStore,
) -> None:
    """A foreign account stays existence-hidden."""
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned",
        headers={"Authorization": f"Bearer {_account_jwt(ACCOUNT_B)}"},
    )
    assert response.status_code == 404, response.text
    # The lookup ran under the caller's own account, so the refusal is the
    # ownership decision rather than an identity failure.
    assert spy.calls == [("get_account_run", ACCOUNT_B)]


def test_remote_account_jwt_never_resolves_to_the_local_fallback(
    remote_boundary: _SessionStore,
) -> None:
    """A verified account subject must not become the configured local user."""
    spy = _ResourceStoreSpy(owner=LOCAL_FALLBACK)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned",
        headers={"Authorization": f"Bearer {_account_jwt(ACCOUNT_A)}"},
    )
    assert response.status_code == 404, response.text
    # The fallback-owned resource was not exposed, and the lookup did not run
    # under the local identity.
    assert spy.calls == [("get_account_run", ACCOUNT_A)]
    assert spy.calls[0][1] != LOCAL_FALLBACK


def test_forged_user_id_header_cannot_replace_the_verified_account_subject(
    remote_boundary: _SessionStore,
) -> None:
    """A caller-supplied identity cannot mint account authority."""
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned",
        headers={
            "Authorization": f"Bearer {_account_jwt(ACCOUNT_A)}",
            "X-User-Id": "attacker@example.invalid",
        },
    )
    assert response.status_code == 200, response.text
    assert spy.calls == [("get_account_run", ACCOUNT_A)]


@pytest.mark.parametrize(
    "label, headers",
    (
        ("no credentials", {}),
        ("empty bearer", {"Authorization": "Bearer "}),
        ("malformed bearer", {"Authorization": "Bearer not-a-token"}),
    ),
)
def test_missing_and_malformed_credentials_fail_closed_before_lookup(
    remote_boundary: _SessionStore,
    label: str,
    headers: dict[str, str],
) -> None:
    """An unusable credential is refused before any resource lookup."""
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))

    response = client.get("/account/run/run-owned", headers=headers)
    assert response.status_code == 401, f"{label}: {response.text}"
    assert spy.calls == []


@pytest.mark.parametrize(
    "label, token",
    (
        ("expired", _account_jwt(ACCOUNT_A, expires=int(time.time()) - 60)),
        ("wrong purpose", _account_jwt(ACCOUNT_A, purpose="operator_session")),
        ("wrong secret", _account_jwt(ACCOUNT_A, secret="not-the-signing-key")),
    ),
)
def test_unusable_account_jwt_fails_closed_before_lookup(
    remote_boundary: _SessionStore,
    label: str,
    token: str,
) -> None:
    """An account credential that cannot be verified never falls back."""
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401, f"{label}: {response.text}"
    assert spy.calls == []


def test_native_account_session_still_resolves_its_account(
    remote_boundary: _SessionStore,
) -> None:
    """A stored native account session keeps resolving its own account."""
    native, _ = auth.issue_session_token(
        subject=ACCOUNT_A,
        ttl_seconds=60,
        purpose=ACCOUNT_SESSION_PURPOSE,
    )
    remote_boundary.store(native, ACCOUNT_A, 60)
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned", headers={"Authorization": f"Bearer {native}"}
    )
    assert response.status_code == 200, response.text
    assert spy.calls == [("get_account_run", ACCOUNT_A)]


def test_private_preview_still_requires_a_stored_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Private Preview keeps its stronger stored-session requirement."""
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", JWT_SECRET)
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", ACCOUNT_A)
    store = _SessionStore()
    monkeypatch.setattr("guardian.core.session_store.get_session_store", lambda: store)
    monkeypatch.setattr(
        "guardian.core.auth_dependencies.get_session_store", lambda: store
    )
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned",
        headers={"Authorization": f"Bearer {_account_jwt(ACCOUNT_A)}"},
    )
    assert response.status_code == 401, response.text
    assert spy.calls == []


def test_local_api_key_keeps_the_bounded_single_user_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local operator lane keeps its bounded single-user compatibility."""
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    spy = _ResourceStoreSpy(owner=LOCAL_FALLBACK)
    client = _client(_account_app(spy))

    response = client.get("/account/run/run-owned", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200, response.text
    assert spy.calls == [("get_account_run", LOCAL_FALLBACK)]


def test_multi_user_mode_binds_the_mapped_account_not_the_raw_subject(
    remote_boundary: _SessionStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In multi-user mode the subject maps to a stable account id.

    The subject and the account id are distinct identities, so the resource
    lookup must use the mapped account. The principal mapping is isolated at
    its own seam here, because the durable mapping table needs PostgreSQL;
    the mapping contract itself is covered by the request-user scope suite.
    """
    monkeypatch.setattr(
        dependencies.get_core_settings(), "CODEXIFY_MULTI_USER_ENABLED", True
    )
    mapped_account = "acct-mapped-42"
    monkeypatch.setattr(
        dependencies,
        "_resolve_account_id_for_subject",
        lambda _subject_id: mapped_account,
    )
    spy = _ResourceStoreSpy(owner=mapped_account)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned",
        headers={"Authorization": f"Bearer {_account_jwt(ACCOUNT_A)}"},
    )
    assert response.status_code == 200, response.text
    assert spy.calls == [("get_account_run", mapped_account)]
    assert spy.calls[0][1] != ACCOUNT_A


def test_multi_user_mode_without_a_stable_mapping_fails_closed(
    remote_boundary: _SessionStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without a stable account mapping the read is refused, not downgraded."""
    monkeypatch.setattr(
        dependencies.get_core_settings(), "CODEXIFY_MULTI_USER_ENABLED", True
    )
    monkeypatch.setattr(
        dependencies,
        "_resolve_account_id_for_subject",
        lambda _subject_id: None,
    )
    spy = _ResourceStoreSpy(owner=ACCOUNT_A)
    client = _client(_account_app(spy))

    response = client.get(
        "/account/run/run-owned",
        headers={"Authorization": f"Bearer {_account_jwt(ACCOUNT_A)}"},
    )
    assert response.status_code == 401, response.text
    assert spy.calls == []
