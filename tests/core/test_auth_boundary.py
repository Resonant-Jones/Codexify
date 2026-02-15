import time

import pytest
from fastapi import HTTPException

from guardian.core.auth import issue_session_token
from guardian.core.dependencies import verify_api_key


def test_local_mode_accepts_static_api_key(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_API_KEY", "local-test-key")

    token = verify_api_key(
        x_api_key="local-test-key",
        authorization=None,
        gc_session=None,
    )

    assert token == "local-test-key"


def test_public_allowlist_exposure_forces_remote_and_rejects_api_key(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "public_allowlist")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_API_KEY", "local-test-key")

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(
            x_api_key="local-test-key",
            authorization=None,
            gc_session=None,
        )

    assert exc_info.value.status_code == 401
    assert "session/jwt" in str(exc_info.value.detail).lower()


def test_local_safe_exposure_allows_static_api_key(monkeypatch):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_API_KEY", "local-test-key")

    token = verify_api_key(
        x_api_key="local-test-key",
        authorization=None,
        gc_session=None,
    )

    assert token == "local-test-key"


def test_remote_mode_rejects_static_api_key(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "remote-session-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "local-test-key")

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(
            x_api_key="local-test-key",
            authorization=None,
            gc_session=None,
        )

    assert exc_info.value.status_code == 401
    assert "session/jwt" in str(exc_info.value.detail).lower()


def test_remote_mode_rejects_bearer_api_key(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "remote-session-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "local-test-key")

    with pytest.raises(HTTPException) as exc_info:
        verify_api_key(
            x_api_key=None,
            authorization="Bearer local-test-key",
            gc_session=None,
        )

    assert exc_info.value.status_code == 401
    assert "session/jwt" in str(exc_info.value.detail).lower()


def test_remote_mode_accepts_bearer_session_token(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "remote-session-secret")
    monkeypatch.delenv("GUARDIAN_JWT_SECRET", raising=False)

    session_token, _expires = issue_session_token(
        subject="boundary-test-user",
        ttl_seconds=60,
    )

    token = verify_api_key(
        x_api_key=None,
        authorization=f"Bearer {session_token}",
        gc_session=None,
    )

    assert token == session_token


def test_remote_mode_accepts_session_cookie(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "remote-session-secret")

    session_token, _expires = issue_session_token(
        subject="boundary-test-cookie",
        ttl_seconds=60,
    )

    token = verify_api_key(
        x_api_key=None,
        authorization=None,
        gc_session=session_token,
    )

    assert token == session_token


def test_remote_mode_accepts_jwt_bearer(monkeypatch):
    jwt = pytest.importorskip("jwt")

    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_JWT_SECRET", "remote-jwt-secret")
    monkeypatch.delenv("GUARDIAN_SESSION_SECRET", raising=False)

    jwt_token = jwt.encode(
        {"sub": "jwt-user", "exp": int(time.time()) + 60},
        "remote-jwt-secret",
        algorithm="HS256",
    )

    token = verify_api_key(
        x_api_key=None,
        authorization=f"Bearer {jwt_token}",
        gc_session=None,
    )

    assert token == jwt_token


def test_public_allowlist_exposure_accepts_bearer_when_auth_mode_misset(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "public_allowlist")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "remote-session-secret")

    session_token, _expires = issue_session_token(
        subject="boundary-test-exposure-bearer",
        ttl_seconds=60,
    )

    token = verify_api_key(
        x_api_key=None,
        authorization=f"Bearer {session_token}",
        gc_session=None,
    )

    assert token == session_token
