from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.auth import issue_session_token
from guardian.core.session_store import get_session_store


def _session_headers(email: str) -> dict[str, str]:
    token, _ = issue_session_token(subject=email, ttl_seconds=60)
    get_session_store().store(token, email, 60)
    return {"Authorization": f"Bearer {token}"}


def _preview_env(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "private_preview")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "preview-test-secret")
    monkeypatch.setenv("CODEXIFY_PREVIEW_ADMIN_EMAILS", "admin@example.com")
    monkeypatch.setenv(
        "CODEXIFY_PREVIEW_APPROVED_EMAILS",
        "admin@example.com,guest@example.com",
    )


def test_private_preview_admin_route_requires_server_mapped_admin(monkeypatch):
    _preview_env(monkeypatch)

    from guardian.routes import admin

    app = FastAPI()
    app.include_router(admin.router)
    client = TestClient(app)

    guest = client.get("/debug/config", headers=_session_headers("guest@example.com"))
    assert guest.status_code == 403

    operator = client.get("/debug/config", headers=_session_headers("admin@example.com"))
    assert operator.status_code == 200


def test_private_preview_projects_are_filtered_to_authenticated_email(monkeypatch):
    _preview_env(monkeypatch)

    from guardian.routes import projects

    db = MagicMock()
    db.list_projects.return_value = [
        {"id": 1, "name": "Guest", "user_id": "guest@example.com"},
        {"id": 2, "name": "Admin", "user_id": "admin@example.com"},
    ]

    app = FastAPI()
    app.include_router(projects.api_router)
    with patch.object(projects, "chatlog_db", db):
        response = TestClient(app).get(
            "/api/projects", headers=_session_headers("guest@example.com")
        )

    assert response.status_code == 200
    assert [project["id"] for project in response.json()] == [1]
    assert response.json()[0]["user_id"] == "guest@example.com"


def test_private_preview_registration_is_not_available(monkeypatch):
    _preview_env(monkeypatch)

    from guardian.routes import auth

    app = FastAPI()
    app.include_router(auth.router)
    response = TestClient(app).post(
        "/auth/register",
        json={"username": "guest@example.com", "password": "not-a-real-password"},
    )

    assert response.status_code == 404
