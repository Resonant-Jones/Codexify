from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import imprint as imprint_routes

AUTH_HEADERS = {"X-API-Key": "test-api-key", "X-User-Id": "u1"}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("DEBUG", "1")


def make_app():
    app = FastAPI()
    app.include_router(imprint_routes.system_prompt_router)
    return app


def test_system_prompt_summary_requires_auth():
    app = make_app()
    client = TestClient(app)

    resp = client.get(
        "/api/system_prompt/summary",
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_system_prompt_summary_rejects_cross_user_thread_scope():
    app = make_app()
    client = TestClient(app)
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda _tid: {"user_id": "u2", "project_id": 12},
        get_project_identity_depth=lambda _pid: "deep",
    )
    try:
        resp = client.get(
            "/api/system_prompt/summary?thread_id=1",
            headers=AUTH_HEADERS,
        )
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403
