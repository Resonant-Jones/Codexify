from __future__ import annotations

import pytest
from fastapi import FastAPI
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
