"""Tests for the viewer-aware Guardian dashboard snapshot projection."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core import auth_dependencies as auth_dependencies_module
from guardian.core import dependencies
from guardian.core.auth import issue_session_token
from guardian.core.session_store import SessionStore
from guardian.db.models import User, UserProfile
from guardian.routes import dashboard
from guardian.routes import user_profile as user_profile_routes
from guardian.routes.heartbeat import HeartbeatStatusResponse

_API_KEY = "dashboard-test-key"
_CHRIS_ID = "chris@resonantconstructs.ai"
_ZAC_ID = "maatariki@resonantconstructs.ai"


class _FakeRedis:
    def __init__(self) -> None:
        self._strings: dict[str, bytes] = {}

    def set(
        self,
        key: str,
        value: object,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        if nx and key in self._strings:
            return None
        self._strings[key] = str(value).encode("utf-8")
        _ = ex
        return True

    def get(self, key: str) -> bytes | None:
        return self._strings.get(key)

    def delete(self, key: str) -> int:
        return 1 if self._strings.pop(key, None) is not None else 0


class _DashboardDb:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        User.__table__.create(engine)
        UserProfile.__table__.create(engine)
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

    def seed_user(
        self,
        *,
        user_id: str,
        role: str,
        display_name: str | None = None,
        avatar_url: str | None = None,
        timezone_name: str | None = None,
    ) -> None:
        with self.get_session() as session:
            session.add(
                User(
                    id=user_id,
                    username=user_id,
                    password_hash="non-secret-test-hash",
                    role=role,
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.add(
                UserProfile(
                    user_id=user_id,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    timezone=timezone_name,
                )
            )
            session.commit()

    def profile_for(self, user_id: str) -> UserProfile | None:
        with self.get_session() as session:
            return session.scalar(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )


def _private_preview_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "dashboard-session-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", _CHRIS_ID)
    monkeypatch.setenv("CODEXIFY_PREVIEW_APPROVED_EMAILS", f"{_CHRIS_ID},{_ZAC_ID}")


@contextmanager
def _client(db: _DashboardDb | None = None):
    session_store = SessionStore(redis_client=_FakeRedis())
    with (
        patch.object(
            auth_dependencies_module,
            "get_session_store",
            return_value=session_store,
        ),
        patch.object(
            user_profile_routes,
            "load_guardian_db_from_env",
            return_value=db,
        ),
    ):
        app = FastAPI()
        app.include_router(dashboard.router)
        with TestClient(app) as client:
            yield client, session_store


def _session_cookie(
    session_store: SessionStore, user_id: str
) -> tuple[str, dict[str, str]]:
    token, _ = issue_session_token(subject=user_id, ttl_seconds=60)
    session_store.store(token, user_id, 60)
    return token, {"gc_session": token}


def _stub_dashboard_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dashboard.health_routes,
        "health",
        lambda _request: {"status": "ok", "service": "core"},
    )
    monkeypatch.setattr(
        dashboard.health_routes,
        "health_llm",
        lambda: {"status": "online", "provider": "local", "model": "test-model"},
    )
    monkeypatch.setattr(
        dashboard.health_routes,
        "health_chat",
        lambda: {
            "status": "healthy",
            "worker": {"status": "fresh"},
            "queue": {"status": "progressing"},
        },
    )

    async def heartbeat_fixture():
        return HeartbeatStatusResponse(latest_date="2026-07-16")

    monkeypatch.setattr(dashboard, "heartbeat_status", heartbeat_fixture)
    monkeypatch.setattr(dependencies, "_sensors", None)


def _seed_viewers(db: _DashboardDb) -> None:
    # Deliberately invert persisted roles: private-preview policy, not a stored
    # row or caller-controlled field, owns the returned role in this mode.
    db.seed_user(
        user_id=_CHRIS_ID,
        role="guest",
        display_name="Chris",
        avatar_url="https://example.com/chris.png",
        timezone_name="America/New_York",
    )
    db.seed_user(
        user_id=_ZAC_ID,
        role="admin",
        display_name="Zac",
        timezone_name="Pacific/Auckland",
    )


@pytest.mark.parametrize("headers", [{"X-API-Key": ""}, {"X-API-Key": "wrong-key"}])
def test_dashboard_snapshot_rejects_missing_or_wrong_service_key(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
) -> None:
    _private_preview_env(monkeypatch)
    with _client() as (client, session_store):
        _token, cookies = _session_cookie(session_store, _CHRIS_ID)
        response = client.get(
            "/api/dashboard/snapshot", headers=headers, cookies=cookies
        )

    assert response.status_code == 401, response.text


def test_dashboard_snapshot_rejects_service_key_without_guardian_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_preview_env(monkeypatch)
    with _client() as (client, _session_store):
        response = client.get(
            "/api/dashboard/snapshot", headers={"X-API-Key": _API_KEY}
        )

    assert response.status_code == 401, response.text


def test_dashboard_snapshot_rejects_guardian_session_without_service_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_preview_env(monkeypatch)
    with _client() as (client, session_store):
        _token, cookies = _session_cookie(session_store, _CHRIS_ID)
        response = client.get(
            "/api/dashboard/snapshot",
            headers={"X-API-Key": ""},
            cookies=cookies,
        )

    assert response.status_code == 401, response.text


def test_dashboard_snapshot_projects_chris_as_admin_from_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_preview_env(monkeypatch)
    _stub_dashboard_sources(monkeypatch)
    db = _DashboardDb()
    _seed_viewers(db)

    with _client(db) as (client, session_store):
        token, cookies = _session_cookie(session_store, _CHRIS_ID)
        response = client.get(
            "/api/dashboard/snapshot",
            headers={"X-API-Key": _API_KEY, "X-User-Id": _ZAC_ID},
            cookies=cookies,
        )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "schema_version",
        "generated_at",
        "source",
        "viewer",
        "health",
        "runtime",
        "host",
        "changes",
        "attention",
        "orientation",
    }
    assert payload["schema_version"] == "guardian.dashboard.snapshot.v1"
    assert payload["viewer"] == {
        "user_id": _CHRIS_ID,
        "display_name": "Chris",
        "role": "admin",
        "avatar_url": "https://example.com/chris.png",
        "timezone": "America/New_York",
    }
    assert payload["viewer"]["user_id"] != _ZAC_ID
    assert payload["health"]["llm"]["model"] == "test-model"
    assert payload["health"]["heartbeat"]["latest_date"] == "2026-07-16"
    assert payload["runtime"] == {
        "provider": "local",
        "model": "test-model",
        "chat_status": "healthy",
        "worker_status": "fresh",
        "queue_status": "progressing",
    }
    assert payload["changes"] == []
    assert payload["attention"] == []
    assert payload["orientation"] == {
        "notes": [],
        "presence": [],
        "mentions": [],
    }
    assert payload["host"]["telemetry_source"] == "guardian.sensors.state.Sensors"
    assert token not in response.text
    assert _API_KEY not in response.text
    assert "non-secret-test-hash" not in response.text
    assert "CODEXIFY_PREVIEW_APPROVED_EMAILS" not in response.text


def test_dashboard_snapshot_projects_zac_own_profile_and_guest_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_preview_env(monkeypatch)
    _stub_dashboard_sources(monkeypatch)
    db = _DashboardDb()
    _seed_viewers(db)

    with _client(db) as (client, session_store):
        _token, chris_cookies = _session_cookie(session_store, _CHRIS_ID)
        _token, zac_cookies = _session_cookie(session_store, _ZAC_ID)
        chris_response = client.get(
            "/api/dashboard/snapshot",
            headers={"X-API-Key": _API_KEY},
            cookies=chris_cookies,
        )
        zac_response = client.get(
            "/api/dashboard/snapshot",
            headers={"X-API-Key": _API_KEY},
            cookies=zac_cookies,
        )

    assert chris_response.status_code == 200
    assert zac_response.status_code == 200
    assert zac_response.json()["viewer"] == {
        "user_id": _ZAC_ID,
        "display_name": "Zac",
        "role": "guest",
        "avatar_url": None,
        "timezone": "Pacific/Auckland",
    }
    assert zac_response.json()["viewer"] != chris_response.json()["viewer"]
    assert zac_response.json()["viewer"]["avatar_url"] != (
        chris_response.json()["viewer"]["avatar_url"]
    )


def test_dashboard_snapshot_lazily_creates_only_the_session_viewer_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _private_preview_env(monkeypatch)
    _stub_dashboard_sources(monkeypatch)
    db = _DashboardDb()
    db.seed_user(user_id=_CHRIS_ID, role="guest")

    with _client(db) as (client, session_store):
        _token, cookies = _session_cookie(session_store, _CHRIS_ID)
        response = client.get(
            "/api/dashboard/snapshot",
            headers={"X-API-Key": _API_KEY},
            cookies=cookies,
        )

    assert response.status_code == 200
    assert response.json()["viewer"] == {
        "user_id": _CHRIS_ID,
        "display_name": None,
        "role": "admin",
        "avatar_url": None,
        "timezone": None,
    }
    assert db.profile_for(_CHRIS_ID) is not None
    assert db.profile_for(_ZAC_ID) is None
