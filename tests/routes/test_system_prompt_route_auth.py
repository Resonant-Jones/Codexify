from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from guardian.routes import imprint as imprint_routes

AUTH_HEADERS = {"X-API-Key": "test-api-key", "X-User-Id": "u1"}


@pytest.fixture(autouse=True)
def _auth_env(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("DEBUG", "1")


def make_app():
    app = FastAPI()

    def _test_current_user(request: Request) -> str:
        return request.headers.get("X-User-Id") or "default"

    app.dependency_overrides[
        imprint_routes.get_current_user
    ] = _test_current_user
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


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_inspect_requires_auth(headers):
    client = TestClient(make_app())
    client.headers.clear()  # Undo the shared test harness's automatic API key.
    assert client.get("/api/system_prompt/inspect", headers=headers).status_code == 401


@pytest.mark.parametrize(
    "thread,projects,params,expected",
    [
        ({"user_id": "u2", "project_id": 7}, [], {"thread_id": 1}, 403),
        ({"user_id": "u1", "project_id": 7}, [], {"thread_id": 1, "project_id": 8}, 403),
        (None, [], {"thread_id": 1}, 404),
        (None, [{"id": 7, "user_id": "u2"}], {"project_id": 7}, 403),
        (None, [{"id": 7}], {"project_id": 7}, 403),
        (None, [], {"project_id": 7}, 404),
    ],
)
def test_inspect_scope_failure_is_not_partial_success(monkeypatch, thread, projects, params, expected):
    from unittest.mock import Mock
    monkeypatch.setattr(imprint_routes, "chatlog_db", SimpleNamespace(
        get_chat_thread=lambda _id: thread, list_projects=lambda: projects,
    ))
    projection = Mock(side_effect=AssertionError("scope must fail before inspection"))
    monkeypatch.setattr(imprint_routes, "build_guardian_system_prompt_inspection_metadata", projection)
    response = TestClient(make_app()).get(
        "/api/system_prompt/inspect", params=params, headers=AUTH_HEADERS
    )
    assert response.status_code == expected
    projection.assert_not_called()
