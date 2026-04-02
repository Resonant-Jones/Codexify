from __future__ import annotations

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


def test_imprint_proposal_requires_auth():
    app = make_app()
    client = TestClient(app)

    resp = client.post(
        "/api/imprint/proposal",
        json={},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_imprint_proposal_rejects_thread_scope_mismatch():
    app = make_app()
    client = TestClient(app)
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda _tid: {"user_id": "u2", "project_id": 9},
        get_project_identity_depth=lambda _pid: "deep",
    )
    try:
        with patch.object(
            imprint_routes.imprint_store, "save_imprint"
        ) as mock_save:
            resp = client.post(
                "/api/imprint/proposal",
                json={"thread_id": 1},
                headers=AUTH_HEADERS,
            )
            mock_save.assert_not_called()
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403


def test_accept_reject_require_owner_scope():
    app = make_app()
    client = TestClient(app)
    draft = SimpleNamespace(id=7, user_id="u2", project_id=None)

    with patch.object(
        imprint_routes.imprint_store,
        "get_imprint_by_id",
        return_value=draft,
    ):
        resp = client.post(
            "/api/imprint/accept",
            json={"imprint_id": 7},
            headers=AUTH_HEADERS,
        )
    assert resp.status_code == 403

    with patch.object(
        imprint_routes.imprint_store,
        "get_imprint_by_id",
        return_value=draft,
    ):
        resp = client.post(
            "/api/imprint/reject",
            json={"imprint_id": 7},
            headers=AUTH_HEADERS,
        )
    assert resp.status_code == 403


def test_persona_update_rejects_cross_user_thread_scope():
    app = make_app()
    client = TestClient(app)
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda _tid: {"user_id": "u2", "project_id": 3},
        get_project_identity_depth=lambda _pid: "deep",
    )
    try:
        resp = client.post(
            "/api/imprint/persona",
            json={"body": "persona", "thread_id": 1},
            headers=AUTH_HEADERS,
        )
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403
