from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core import dependencies as dependency_module
from guardian.core import auth_dependencies as auth_dependencies_module
from guardian.core.auth_dependencies import get_current_user_id
from guardian.core.dependencies import get_request_user_scope, verify_api_key
from guardian.core.passwords import hash_password
from guardian.core.session_store import SessionStore
from guardian.db.models import User
from guardian.routes import auth as auth_routes


class _AuthDb:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        User.__table__.create(engine)
        self._session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    @contextmanager
    def get_session(self):
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    def seed_user(self, *, user_id: str, username: str, password: str) -> None:
        with self.get_session() as session:
            session.add(
                User(
                    id=user_id,
                    username=username,
                    password_hash=hash_password(password),
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()


class _FakeRedis:
    def __init__(self) -> None:
        self._strings: dict[str, bytes] = {}

    @staticmethod
    def _to_bytes(value: object) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        return str(value).encode("utf-8")

    def set(
        self,
        key: str,
        value: object,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        if nx and key in self._strings:
            return None
        self._strings[key] = self._to_bytes(value)
        _ = ex
        return True

    def get(self, key: str) -> bytes | None:
        return self._strings.get(key)

    def delete(self, key: str) -> int:
        return 1 if self._strings.pop(key, None) is not None else 0


@contextmanager
def _build_test_client(auth_db: _AuthDb):
    fake_redis = _FakeRedis()
    session_store = SessionStore(redis_client=fake_redis)

    with (
        patch.object(
            auth_routes,
            "load_guardian_db_from_env",
            return_value=auth_db,
        ),
        patch.object(
            auth_routes,
            "get_session_store",
            return_value=session_store,
        ),
        patch.object(
            auth_dependencies_module,
            "get_session_store",
            return_value=session_store,
        ),
    ):
        app = FastAPI()
        app.include_router(auth_routes.router)

        @app.get("/whoami")
        def whoami(current_user_id: str = Depends(get_current_user_id)):
            return {"user_id": current_user_id}

        @app.get("/scope")
        def scope(request_scope=Depends(get_request_user_scope)):
            return asdict(request_scope)

        with TestClient(app) as client:
            yield client, session_store, fake_redis


def _configure_remote_session_env(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "trusted-remote-session-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "trusted-remote-api-key")
    monkeypatch.delenv("GUARDIAN_JWT_SECRET", raising=False)
    monkeypatch.delenv("CODEXIFY_MULTI_USER_ENABLED", raising=False)


def _login(client: TestClient, *, username: str, password: str) -> dict[str, object]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_session_login_creates_remote_safe_session_without_api_key_exposure(
    monkeypatch,
):
    _configure_remote_session_env(monkeypatch)

    auth_db = _AuthDb()
    canonical_user_id = "acct-remote-1"
    username = "remote.friend@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, session_store, _fake_redis):
        payload = _login(client, username=username, password=password)

    assert set(payload) == {"token", "user_id", "expires_at"}
    assert payload["user_id"] == canonical_user_id
    assert isinstance(payload["token"], str)
    assert isinstance(payload["expires_at"], int)
    assert session_store.verify(payload["token"]) == canonical_user_id


def test_session_authenticated_request_resolves_canonical_subject(
    monkeypatch,
):
    _configure_remote_session_env(monkeypatch)

    auth_db = _AuthDb()
    canonical_user_id = "acct-remote-2"
    username = "display-name@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        response = client.get(
            "/scope",
            headers={"Authorization": f"Bearer {payload['token']}"},
        )

    assert response.status_code == 200
    scope = response.json()
    assert scope["user_id"] == canonical_user_id
    assert scope["subject_id"] == canonical_user_id
    assert scope["account_id"] == canonical_user_id
    assert scope["multi_user_enabled"] is True
    assert scope["user_id"] != username


def test_session_auth_does_not_fall_back_to_single_user_identity(
    monkeypatch,
):
    _configure_remote_session_env(monkeypatch)

    auth_db = _AuthDb()
    canonical_user_id = "acct-remote-3"
    username = "session-only@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        monkeypatch.setattr(
            dependency_module,
            "get_single_user_id",
            lambda: (_ for _ in ()).throw(
                AssertionError("single-user fallback should not be used")
            ),
        )

        response = client.get(
            "/whoami",
            headers={"Authorization": f"Bearer {payload['token']}"},
        )

    assert response.status_code == 200
    assert response.json()["user_id"] == canonical_user_id


def test_logout_revokes_or_clears_session(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _AuthDb()
    canonical_user_id = "acct-remote-4"
    username = "logout@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        token = str(payload["token"])

        assert session_store.verify(token) == canonical_user_id

        logout_response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logout_response.status_code == 200
        assert logout_response.json() == {"ok": True}
        assert session_store.verify(token) is None

        whoami_response = client.get(
            "/whoami",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert whoami_response.status_code == 401
    assert "Invalid or expired session" in whoami_response.json()["detail"]


def test_api_key_fallback_is_separate_from_session_identity(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _AuthDb()
    canonical_user_id = "acct-remote-5"
    username = "separate-path@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        session_token = str(payload["token"])

        resolved_session_token = verify_api_key(
            x_api_key=None,
            authorization=f"Bearer {session_token}",
            gc_session=None,
        )
        assert resolved_session_token == session_token

        monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(
                x_api_key="trusted-remote-api-key",
                authorization=None,
                gc_session=None,
            )
        assert exc_info.value.status_code == 401
        assert "session/JWT" in str(exc_info.value.detail)

        monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
        with patch.object(
            dependency_module,
            "get_settings",
            return_value=SimpleNamespace(
                GUARDIAN_API_KEY="trusted-remote-api-key",
                GUARDIAN_API_KEYS=None,
            ),
        ):
            resolved_api_key = verify_api_key(
                x_api_key="trusted-remote-api-key",
                authorization=None,
                gc_session=None,
            )

    assert resolved_api_key == "trusted-remote-api-key"
