from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import imprint as imprint_routes


def make_app():
    app = FastAPI()
    app.include_router(imprint_routes.router)
    return app


def test_identity_updates_blocked_when_memory_none():
    app = make_app()
    client = TestClient(app)
    with patch.object(
        imprint_routes.user_settings_store,
        "get_user_settings",
        return_value={"memory_mode": "none"},
    ):
        resp = client.post("/api/imprint/proposal", json={})
    assert resp.status_code == 403


def test_identity_updates_blocked_when_thread_excludes():
    app = make_app()
    client = TestClient(app)
    thread = {"user_id": "u1", "exclude_from_identity": True}
    original = imprint_routes.chatlog_db
    imprint_routes.chatlog_db = SimpleNamespace(
        get_chat_thread=lambda tid: thread
    )
    try:
        with patch.object(
            imprint_routes.user_settings_store,
            "get_user_settings",
            return_value={"memory_mode": "deep"},
        ):
            resp = client.post("/api/imprint/proposal", json={"thread_id": 1})
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 403


def test_identity_updates_allowed_light_mode():
    app = make_app()
    client = TestClient(app)
    thread = {
        "user_id": "u1",
        "exclude_from_identity": False,
        "is_diary": False,
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
        get_chat_thread=lambda tid: thread
    )
    try:
        with patch.object(
            imprint_routes.user_settings_store,
            "get_user_settings",
            return_value={"memory_mode": "light"},
        ), patch.object(
            imprint_routes.imprint_store,
            "save_imprint",
            return_value=draft_imprint,
        ):
            resp = client.post("/api/imprint/proposal", json={"thread_id": 1})
    finally:
        imprint_routes.chatlog_db = original
    assert resp.status_code == 200
