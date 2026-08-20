from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.passwords import hash_password, verify_password
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
        patch.object(dependencies, "chatlog_db", mock_chatlog_db),
        patch.object(projects_routes, "chatlog_db", mock_chatlog_db),
        patch.object(chat_routes, "chatlog_db", mock_chatlog_db),
    ):
        app = FastAPI()
        app.include_router(auth_routes.router)
        app.include_router(projects_routes.router)
        client = TestClient(app)

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


def test_remote_registration_creates_a_canonical_guest_email_account(monkeypatch):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "auth-flow-session-secret")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")

    auth_db = _AuthDb()
    email = "tomepenn@gmail.com"
    password = "tester-selected-password"

    from guardian.routes import auth as auth_routes

    with patch.object(
        auth_routes, "load_guardian_db_from_env", return_value=auth_db
    ):
        app = FastAPI()
        app.include_router(auth_routes.router)
        client = TestClient(app)

        registration = client.post(
            "/auth/register", json={"username": email, "password": password}
        )
        login = client.post(
            "/auth/login", json={"username": email, "password": password}
        )

    assert registration.status_code == 200
    assert login.status_code == 200
    assert login.json()["user_id"] == email
    with auth_db.get_session() as session:
        user = session.get(User, email)
        assert user is not None
        assert user.id == email
        assert user.username == email
        assert user.role == "guest"
        assert verify_password(password, user.password_hash)


def test_login_accepts_linked_email_without_mutating_canonical_identity(
    monkeypatch,
):
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "auth-flow-session-secret")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")

    auth_db = _AuthDb()
    canonical_user_id = "legacy-account-id"
    legacy_username = "legacy-username"
    linked_email = "linked@example.com"
    password = "saved-password"
    password_hash = hash_password(password)

    with auth_db.get_session() as session:
        session.add(
            User(
                id=canonical_user_id,
                username=legacy_username,
                email=linked_email,
                password_hash=password_hash,
            )
        )
        session.commit()

    from guardian.routes import auth as auth_routes

    with patch.object(
        auth_routes, "load_guardian_db_from_env", return_value=auth_db
    ):
        app = FastAPI()
        app.include_router(auth_routes.router)
        response = TestClient(app).post(
            "/auth/login",
            json={
                "username": "  Linked@Example.COM  ",
                "password": password,
            },
        )

    assert response.status_code == 200
    assert response.json()["user_id"] == canonical_user_id

    with auth_db.get_session() as session:
        user = session.get(User, canonical_user_id)
        assert user is not None
        assert user.username == legacy_username
        assert user.email == linked_email
        assert user.password_hash == password_hash


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

    from guardian.routes import auth as auth_routes

    with patch.object(
        auth_routes, "load_guardian_db_from_env", return_value=auth_db
    ):
        seeded_user = get_or_create_default_user(auth_db)

        assert seeded_user["id"] == "local"
        assert seeded_user["username"] == "local"
        assert verify_password("operator-secret", seeded_user["password_hash"])

        app = FastAPI()
        app.include_router(auth_routes.router)
        client = TestClient(app)
        login_response = client.post(
            "/auth/login",
            json={"username": "local", "password": "operator-secret"},
        )

    assert login_response.status_code == 200
    assert login_response.json()["user_id"] == "local"
