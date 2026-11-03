from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import Base, UserSettings
from guardian.routes import iddb as iddb_routes
from guardian.services import iddb_settings_service

AUTH_HEADERS = {"X-API-Key": "test-api-key", "X-User-Id": "u1"}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("DEBUG", "1")


@pytest.fixture()
def settings_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[UserSettings.__table__])
    Session = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    iddb_settings_service._set_session_factory(Session)
    return Session


def make_app():
    app = FastAPI()

    def _test_current_user(request: Request) -> str:
        return request.headers.get("X-User-Id") or "default"

    app.dependency_overrides[iddb_routes.get_current_user] = _test_current_user
    app.include_router(iddb_routes.router)
    return app


def test_settings_round_trip_is_persistent_per_user(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    u1_headers = AUTH_HEADERS
    u2_headers = {"X-API-Key": "test-api-key", "X-User-Id": "u2"}

    initial = client.get("/api/iddb/settings", headers=u1_headers)
    assert initial.status_code == 200
    assert initial.json() == {
        "memory_mode": "deep",
        "diary_requires_unlock": False,
        "allow_sensitive_modeling": False,
    }

    updated = client.post(
        "/api/iddb/settings",
        json={
            "memory_mode": "light",
            "diary_requires_unlock": True,
            "allow_sensitive_modeling": False,
        },
        headers=u1_headers,
    )
    assert updated.status_code == 200
    assert updated.json() == {
        "memory_mode": "light",
        "diary_requires_unlock": True,
        "allow_sensitive_modeling": False,
    }

    repeat = client.get("/api/iddb/settings", headers=u1_headers)
    assert repeat.status_code == 200
    assert repeat.json() == updated.json()

    other_user = client.post(
        "/api/iddb/settings",
        json={"allow_sensitive_modeling": True},
        headers=u2_headers,
    )
    assert other_user.status_code == 200
    assert other_user.json() == {
        "memory_mode": "deep",
        "diary_requires_unlock": False,
        "allow_sensitive_modeling": True,
    }

    assert client.get("/api/iddb/settings", headers=u1_headers).json() == {
        "memory_mode": "light",
        "diary_requires_unlock": True,
        "allow_sensitive_modeling": False,
    }


def test_default_row_is_read_only_fallback(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    Session = settings_session_factory
    with Session() as session:
        session.add(
            UserSettings(
                user_id="default",
                memory_mode="light",
                diary_requires_unlock=True,
                allow_sensitive_modeling=True,
            )
        )
        session.commit()

    response = client.get(
        "/api/iddb/settings",
        headers={"X-API-Key": "test-api-key", "X-User-Id": "u9"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "memory_mode": "light",
        "diary_requires_unlock": True,
        "allow_sensitive_modeling": True,
    }


def test_default_subject_cannot_be_mutated(
    settings_session_factory, monkeypatch
):
    app = make_app()
    client = TestClient(app)
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "default")

    response = client.post(
        "/api/iddb/settings",
        json={"memory_mode": "light"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 403


def test_unauthenticated_write_is_rejected(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    response = client.post(
        "/api/iddb/settings",
        json={"memory_mode": "light"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


# ── Automatic collection consent ──────────────────────────────────────


CONSENT_PATH = "/api/iddb/automatic-memory-suggestions"


def test_consent_defaults_to_unset_and_denies_collection(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    response = client.get(CONSENT_PATH, headers=AUTH_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "unset"
    assert payload["effective"] is False
    assert payload["recorded_by_user_id"] is None
    assert payload["policy_version"] == iddb_settings_service.CONSENT_POLICY_VERSION


def test_consent_round_trip_is_persistent_and_account_scoped(
    settings_session_factory,
):
    app = make_app()
    client = TestClient(app)
    u2_headers = {"X-API-Key": "test-api-key", "X-User-Id": "u2"}

    granted = client.post(
        CONSENT_PATH, json={"state": "enabled"}, headers=AUTH_HEADERS
    )
    assert granted.status_code == 200
    payload = granted.json()
    assert payload["state"] == "enabled"
    assert payload["effective"] is True
    assert payload["recorded_by_user_id"] == "u1"
    assert payload["recorded_at"] is not None
    assert payload["updated_at"] is not None

    repeat = client.get(CONSENT_PATH, headers=AUTH_HEADERS)
    assert repeat.status_code == 200
    assert repeat.json() == payload

    other = client.get(CONSENT_PATH, headers=u2_headers)
    assert other.status_code == 200
    assert other.json()["state"] == "unset"
    assert other.json()["effective"] is False


def test_consent_pause_and_decline_are_recorded(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    for state in ("paused", "declined", "enabled", "unset"):
        response = client.post(
            CONSENT_PATH, json={"state": state}, headers=AUTH_HEADERS
        )
        assert response.status_code == 200, state
        assert response.json()["state"] == state
        assert response.json()["effective"] is (state == "enabled")


def test_consent_post_rejects_forged_server_derived_fields(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    for forged in (
        {"state": "enabled", "user_id": "u2"},
        {"state": "enabled", "actor_user_id": "u2"},
        {"state": "enabled", "recorded_by_user_id": "u2"},
        {"state": "enabled", "consent_recorded_at": "2026-01-01T00:00:00Z"},
        {"state": "enabled", "consent_updated_at": "2026-01-01T00:00:00Z"},
        {"state": "enabled", "consent_policy_version": "99"},
        {"state": "enabled", "automatic_memory_suggestions": "enabled"},
    ):
        response = client.post(CONSENT_PATH, json=forged, headers=AUTH_HEADERS)
        assert response.status_code == 400, forged

    # Nothing was written.
    stored = iddb_settings_service.read_automatic_memory_suggestions_consent("u1")
    assert stored["state"] == "unset"
    assert stored["effective"] is False


def test_consent_post_rejects_an_invalid_or_missing_state(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    invalid = client.post(
        CONSENT_PATH, json={"state": "maybe"}, headers=AUTH_HEADERS
    )
    assert invalid.status_code == 400

    missing = client.post(CONSENT_PATH, json={}, headers=AUTH_HEADERS)
    assert missing.status_code == 400

    not_an_object = client.post(
        CONSENT_PATH, json=["enabled"], headers=AUTH_HEADERS
    )
    # A non-object body is refused by request validation before the handler
    # runs; either rejection status is acceptable, a success is not.
    assert not_an_object.status_code in (400, 422)


def test_consent_default_subject_cannot_be_mutated(
    settings_session_factory, monkeypatch
):
    app = make_app()
    client = TestClient(app)
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", "default")

    response = client.post(
        CONSENT_PATH, json={"state": "enabled"}, headers={"X-API-Key": "test-api-key"}
    )
    assert response.status_code == 403


def test_consent_unauthenticated_write_is_rejected(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    response = client.post(
        CONSENT_PATH,
        json={"state": "enabled"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


def test_identity_settings_cannot_overwrite_consent(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    client.post(CONSENT_PATH, json={"state": "enabled"}, headers=AUTH_HEADERS)

    settings = client.post(
        "/api/iddb/settings",
        json={"memory_mode": "light", "automatic_memory_suggestions": "declined"},
        headers=AUTH_HEADERS,
    )
    assert settings.status_code == 200
    assert settings.json() == {
        "memory_mode": "light",
        "diary_requires_unlock": False,
        "allow_sensitive_modeling": False,
    }

    consent = client.get(CONSENT_PATH, headers=AUTH_HEADERS)
    assert consent.status_code == 200
    assert consent.json()["state"] == "enabled"
    assert consent.json()["effective"] is True


def test_settings_response_shape_is_unchanged(settings_session_factory):
    app = make_app()
    client = TestClient(app)

    client.post(CONSENT_PATH, json={"state": "enabled"}, headers=AUTH_HEADERS)

    response = client.get("/api/iddb/settings", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json() == {
        "memory_mode": "deep",
        "diary_requires_unlock": False,
        "allow_sensitive_modeling": False,
    }
