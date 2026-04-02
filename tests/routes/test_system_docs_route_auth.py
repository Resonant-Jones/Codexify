from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

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
    app.include_router(imprint_routes.system_docs_router)
    return app


def test_system_docs_requires_auth():
    app = make_app()
    client = TestClient(app)

    resp = client.get("/api/system_docs", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_system_docs_toggle_rejects_cross_user_thread_scope():
    app = make_app()
    client = TestClient(app)
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda _tid: {"user_id": "u2", "project_id": 5},
    )
    try:
        with patch.object(
            imprint_routes.system_doc_store, "set_doc_link", return_value=None
        ) as mock_set:
            resp = client.post(
                "/api/system_docs/toggle",
                json={"doc_id": 5, "enabled": True, "thread_id": 1},
                headers=AUTH_HEADERS,
            )
            mock_set.assert_not_called()
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403
