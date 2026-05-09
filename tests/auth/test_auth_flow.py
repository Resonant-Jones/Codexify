from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.passwords import verify_password
from guardian.core.user_manager import get_or_create_default_user
from guardian.db.models import User


class _AuthDb:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        User.__table__.create(engine)
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


def _build_mock_chatlog_db(expected_user_id: str) -> MagicMock:
    mock = MagicMock()
    mock.list_projects.return_value = [
        {"id": 1, "name": "Owned", "user_id": expected_user_id},
        {"id": 2, "name": "Other", "user_id": "other-user"},
    ]
    mock.create_project.return_value = 11
    mock.get_recent_thread.return_value = None
    mock.list_chat_threads.return_value = []
    mock.get_chat_thread.return_value = None
    return mock


def test_login_and_authenticated_request(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "auth-flow-session-secret")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")

    auth_db = _AuthDb()

    from guardian import guardian_api
    from guardian.core import dependencies
    from guardian.routes import auth as auth_routes
    from guardian.routes import chat as chat_routes
    from guardian.routes import projects as projects_routes

    expected_user_id = "alice"
    mock_chatlog_db = _build_mock_chatlog_db(expected_user_id)

    with (
        patch.object(
            auth_routes, "load_guardian_db_from_env", return_value=auth_db
        ),
        patch.object(guardian_api, "chatlog_db", mock_chatlog_db),
        patch.object(dependencies, "chatlog_db", mock_chatlog_db),
        patch.object(projects_routes, "chatlog_db", mock_chatlog_db),
        patch.object(chat_routes, "chatlog_db", mock_chatlog_db),
    ):
        client = TestClient(guardian_api.app)

        register_response = client.post(
            "/auth/register",
            json={"username": expected_user_id, "password": "s3cret"},
        )
        assert register_response.status_code == 200
        assert register_response.json()["user_id"] == expected_user_id

        login_response = client.post(
            "/auth/login",
            json={"username": expected_user_id, "password": "s3cret"},
        )
        assert login_response.status_code == 200
        login_payload = login_response.json()
        token = login_payload["token"]
        assert login_payload["user_id"] == expected_user_id
        assert token

        auth_headers = {"Authorization": f"Bearer {token}"}

        projects_response = client.get("/projects", headers=auth_headers)
        assert projects_response.status_code == 200
        projects_payload = projects_response.json()
        assert all(
            project["user_id"] == expected_user_id
            for project in projects_payload
        )

        create_response = client.post(
            "/projects",
            headers=auth_headers,
            json={"name": "Owned Project", "description": "auth-seeded"},
        )
        assert create_response.status_code == 200
        assert mock_chatlog_db.create_project.call_args is not None
        assert (
            mock_chatlog_db.create_project.call_args.kwargs["user_id"]
            == expected_user_id
        )


def test_default_user_bootstrap_does_not_seed_known_password(monkeypatch):
    from guardian.core import user_manager as user_manager_module

    monkeypatch.setattr(
        user_manager_module,
        "load_guardian_db_from_env",
        lambda: None,
    )

    user = get_or_create_default_user()

    assert user["id"] == "local"
    assert user["username"] == "local"
    assert not verify_password("local", user["password_hash"])


def test_default_local_bootstrap_is_canonical_but_not_guessable(monkeypatch):
    monkeypatch.delenv("GUARDIAN_BOOTSTRAP_PASSWORD", raising=False)
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "auth-flow-session-secret")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")

    auth_db = _AuthDb()

    from guardian.routes import auth as auth_routes

    with patch.object(
        auth_routes, "load_guardian_db_from_env", return_value=auth_db
    ):
        seeded_user = get_or_create_default_user(auth_db)

        assert seeded_user["id"] == "local"
        assert seeded_user["username"] == "local"
        assert verify_password("local", seeded_user["password_hash"]) is False

        app = FastAPI()
        app.include_router(auth_routes.router)
        client = TestClient(app)
        login_response = client.post(
            "/auth/login",
            json={"username": "local", "password": "local"},
        )

    assert login_response.status_code == 401


def test_local_bootstrap_uses_operator_secret_when_provided(monkeypatch):
    monkeypatch.setenv("GUARDIAN_BOOTSTRAP_PASSWORD", "operator-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "auth-flow-session-secret")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")

    auth_db = _AuthDb()

    from guardian import guardian_api
    from guardian.routes import auth as auth_routes

    with patch.object(
        auth_routes, "load_guardian_db_from_env", return_value=auth_db
    ):
        seeded_user = get_or_create_default_user(auth_db)

        assert seeded_user["id"] == "local"
        assert seeded_user["username"] == "local"
        assert verify_password("operator-secret", seeded_user["password_hash"])

        client = TestClient(guardian_api.app)
        login_response = client.post(
            "/auth/login",
            json={"username": "local", "password": "operator-secret"},
        )

    assert login_response.status_code == 200
    assert login_response.json()["user_id"] == "local"
