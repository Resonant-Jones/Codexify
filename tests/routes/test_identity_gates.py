from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import Base, UserSettings
from guardian.routes import imprint as imprint_routes
from guardian.services import iddb_settings_service

AUTH_HEADERS = {"X-API-Key": "test-api-key", "X-User-Id": "u1"}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("DEBUG", "1")


@pytest.fixture(autouse=True)
def _settings_db():
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
    yield


def make_app():
    app = FastAPI()
    app.include_router(imprint_routes.router)
    return app


def test_identity_updates_blocked_when_memory_none():
    app = make_app()
    client = TestClient(app)
    with patch.object(
        imprint_routes.iddb_settings_service,
        "get_user_settings",
        return_value={"memory_mode": "none"},
    ):
        resp = client.post(
            "/api/imprint/proposal", json={}, headers=AUTH_HEADERS
        )
    assert resp.status_code == 403


def test_identity_updates_blocked_when_thread_excludes():
    app = make_app()
    client = TestClient(app)
    thread = {"user_id": "u1", "modeling_excluded": True}
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda tid: thread,
        get_project_identity_depth=lambda _pid: "deep",
    )
    try:
        with (
            patch.object(
                imprint_routes.iddb_settings_service,
                "get_user_settings",
                return_value={"memory_mode": "deep"},
            ),
            patch.object(
                imprint_routes.imprint_store, "save_imprint"
            ) as mock_save,
        ):
            resp = client.post(
                "/api/imprint/proposal",
                json={"thread_id": 1},
                headers=AUTH_HEADERS,
            )
            mock_save.assert_not_called()
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403


def test_identity_updates_blocked_when_thread_in_diary_mode():
    app = make_app()
    client = TestClient(app)
    thread = {"user_id": "u1", "diary_mode": True}
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda tid: thread,
        get_project_identity_depth=lambda _pid: "deep",
    )
    try:
        with (
            patch.object(
                imprint_routes.iddb_settings_service,
                "get_user_settings",
                return_value={"memory_mode": "deep"},
            ),
            patch.object(
                imprint_routes.imprint_store, "save_imprint"
            ) as mock_save,
        ):
            resp = client.post(
                "/api/imprint/proposal",
                json={"thread_id": 1},
                headers=AUTH_HEADERS,
            )
            mock_save.assert_not_called()
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403


def test_identity_updates_allowed_light_mode():
    app = make_app()
    client = TestClient(app)
    thread = {
        "user_id": "u1",
        "modeling_excluded": False,
        "diary_mode": False,
    }
    draft_imprint = SimpleNamespace(
        id=1,
        user_id="u1",
        project_id=None,
        guardian_name="Name",
        preferred_name="friend",
        status="draft",
        heat_score=0.5,
        metrics={"persona_draft": "seed persona"},
    )
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda tid: thread,
        get_project_identity_depth=lambda _pid: "light",
    )
    try:
        with (
            patch.object(
                imprint_routes.iddb_settings_service,
                "get_user_settings",
                return_value={"memory_mode": "light"},
            ),
            patch.object(
                imprint_routes.imprint_store,
                "save_imprint",
                return_value=draft_imprint,
            ),
        ):
            resp = client.post(
                "/api/imprint/proposal",
                json={"thread_id": 1},
                headers=AUTH_HEADERS,
            )
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 200


def test_deep_identity_modeling_blocked_when_project_depth_is_light():
    app = make_app()
    client = TestClient(app)
    thread = {
        "user_id": "u1",
        "project_id": 7,
        "modeling_excluded": False,
        "diary_mode": False,
    }
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda _tid: thread,
        get_project_identity_depth=lambda _pid: "light",
    )
    try:
        with (
            patch.object(
                imprint_routes.iddb_settings_service,
                "get_user_settings",
                return_value={"memory_mode": "deep"},
            ),
            patch.object(
                imprint_routes.imprint_store, "save_imprint"
            ) as mock_save,
        ):
            resp = client.post(
                "/api/imprint/proposal",
                json={"thread_id": 1, "requested_depth": "deep"},
                headers=AUTH_HEADERS,
            )
            mock_save.assert_not_called()
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403


def test_deep_identity_modeling_allowed_when_project_depth_is_deep():
    app = make_app()
    client = TestClient(app)
    thread = {
        "user_id": "u1",
        "project_id": 7,
        "modeling_excluded": False,
        "diary_mode": False,
    }
    draft_imprint = SimpleNamespace(
        id=1,
        user_id="u1",
        project_id=7,
        guardian_name="Name",
        preferred_name="friend",
        status="draft",
        heat_score=0.5,
        metrics={"persona_draft": "seed persona"},
    )
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda _tid: thread,
        get_project_identity_depth=lambda _pid: "deep",
    )
    try:
        with (
            patch.object(
                imprint_routes.iddb_settings_service,
                "get_user_settings",
                return_value={"memory_mode": "deep"},
            ),
            patch.object(
                imprint_routes.imprint_store,
                "save_imprint",
                return_value=draft_imprint,
            ),
        ):
            resp = client.post(
                "/api/imprint/proposal",
                json={"thread_id": 1, "requested_depth": "deep"},
                headers=AUTH_HEADERS,
            )
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 200
