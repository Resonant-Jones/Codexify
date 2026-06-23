from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core import auth_dependencies as auth_dependencies_module
from guardian.core import dependencies as dependency_module
from guardian.core.passwords import hash_password
from guardian.core.session_store import SessionStore
from guardian.db.models import PersonaProfile, User, UserProfile
from guardian.routes import auth as auth_routes
from guardian.routes import user_profile as user_profile_routes


class _ProfileAuthDb:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        User.__table__.create(engine)
        UserProfile.__table__.create(engine)
        PersonaProfile.__table__.create(engine)
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

    def seed_user(self, *, user_id: str, username: str, password: str) -> None:
        with self.get_session() as session:
            session.add(
                User(
                    id=user_id,
                    username=username,
                    password_hash=hash_password(password),
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def seed_persona_profile(self, *, profile_id: str) -> None:
        with self.get_session() as session:
            session.add(
                PersonaProfile(
                    id=profile_id,
                    name="Persona Seed",
                    system_prompt="Persona seed prompt",
                    model_provider="openai",
                    model_id="gpt-4o",
                    temperature=0.7,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def get_user_profile(self, user_id: str) -> UserProfile | None:
        with self.get_session() as session:
            return session.scalar(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )

    def get_persona_profile(self, profile_id: str) -> PersonaProfile | None:
        with self.get_session() as session:
            return session.get(PersonaProfile, profile_id)


class _FakeRedis:
    def __init__(self) -> None:
        self._strings: dict[str, bytes] = {}

    @staticmethod
    def _to_bytes(value: object) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)
        return str(value).encode("utf-8")

    def set(
        self,
        key: str,
        value: object,
        ex: int | None = None,
        nx: bool = False,
    ) -> bool | None:
        if nx and key in self._strings:
            return None
        self._strings[key] = self._to_bytes(value)
        _ = ex
        return True

    def get(self, key: str) -> bytes | None:
        return self._strings.get(key)

    def delete(self, key: str) -> int:
        return 1 if self._strings.pop(key, None) is not None else 0


@contextmanager
def _build_test_client(auth_db: _ProfileAuthDb):
    fake_redis = _FakeRedis()
    session_store = SessionStore(redis_client=fake_redis)

    with (
        patch.object(
            auth_routes,
            "load_guardian_db_from_env",
            return_value=auth_db,
        ),
        patch.object(
            user_profile_routes,
            "load_guardian_db_from_env",
            return_value=auth_db,
        ),
        patch.object(
            auth_routes,
            "get_session_store",
            return_value=session_store,
        ),
        patch.object(
            auth_dependencies_module,
            "get_session_store",
            return_value=session_store,
        ),
    ):
        app = FastAPI()
        app.include_router(auth_routes.router)
        app.include_router(user_profile_routes.router)

        with TestClient(app) as client:
            yield client, session_store, fake_redis


def _configure_remote_session_env(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "trusted-remote-session-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "trusted-remote-api-key")
    monkeypatch.delenv("GUARDIAN_JWT_SECRET", raising=False)
    monkeypatch.delenv("CODEXIFY_MULTI_USER_ENABLED", raising=False)


def _login(client: TestClient, *, username: str, password: str) -> dict[str, object]:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def _assert_profile_row(
    auth_db: _ProfileAuthDb,
    *,
    user_id: str,
    display_name: str | None,
    avatar_url: str | None,
    timezone: str | None,
) -> None:
    row = auth_db.get_user_profile(user_id)
    assert row is not None
    assert row.user_id == user_id
    assert row.display_name == display_name
    assert row.avatar_url == avatar_url
    assert row.timezone == timezone


def _disable_single_user_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        dependency_module,
        "get_single_user_id",
        lambda: (_ for _ in ()).throw(
            AssertionError("single-user fallback should not be used")
        ),
    )


def test_session_user_can_read_default_profile(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _ProfileAuthDb()
    canonical_user_id = "acct-profile-1"
    username = "reader@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        _disable_single_user_fallback(monkeypatch)

        response = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload['token']}"},
        )

    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["user_id"] == canonical_user_id
    assert profile["display_name"] is None
    assert profile["avatar_url"] is None
    assert profile["timezone"] is None
    _assert_profile_row(
        auth_db,
        user_id=canonical_user_id,
        display_name=None,
        avatar_url=None,
        timezone=None,
    )


def test_session_user_can_update_profile_metadata(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _ProfileAuthDb()
    canonical_user_id = "acct-profile-2"
    username = "editor@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        _disable_single_user_fallback(monkeypatch)

        response = client.patch(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload['token']}"},
            json={
                "display_name": "Atlas",
                "avatar_url": "https://example.com/avatar.png",
                "timezone": "America/New_York",
            },
        )

    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["user_id"] == canonical_user_id
    assert profile["display_name"] == "Atlas"
    assert profile["avatar_url"] == "https://example.com/avatar.png"
    assert profile["timezone"] == "America/New_York"
    _assert_profile_row(
        auth_db,
        user_id=canonical_user_id,
        display_name="Atlas",
        avatar_url="https://example.com/avatar.png",
        timezone="America/New_York",
    )


def test_profile_update_cannot_change_canonical_user_id(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _ProfileAuthDb()
    canonical_user_id = "acct-profile-3"
    username = "ownership@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        _disable_single_user_fallback(monkeypatch)

        initial_response = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload['token']}"},
        )
        assert initial_response.status_code == 200

        response = client.patch(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload['token']}"},
            json={
                "display_name": "Updated",
                "user_id": "intruder-account",
                "canonical_user_id": "intruder-account",
            },
        )

    assert response.status_code == 422
    _assert_profile_row(
        auth_db,
        user_id=canonical_user_id,
        display_name=None,
        avatar_url=None,
        timezone=None,
    )


def test_profile_update_rejects_or_ignores_auth_and_secret_fields(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _ProfileAuthDb()
    canonical_user_id = "acct-profile-4"
    username = "security@example.com"
    password = "s3cret"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        _disable_single_user_fallback(monkeypatch)

        before_response = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload['token']}"},
        )
        assert before_response.status_code == 200

        response = client.patch(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload['token']}"},
            json={
                "display_name": "Updated",
                "api_key": "secret-key",
                "session_token": "session-token",
                "password": "password",
                "authenticated_principal_id": "principal-1",
                "persona_profile_id": "persona-1",
            },
        )

    assert response.status_code == 422
    _assert_profile_row(
        auth_db,
        user_id=canonical_user_id,
        display_name=None,
        avatar_url=None,
        timezone=None,
    )


def test_profile_surface_does_not_mutate_persona_profiles(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _ProfileAuthDb()
    canonical_user_id = "acct-profile-5"
    username = "persona-guard@example.com"
    password = "s3cret"
    persona_profile_id = "persona-profile-1"
    auth_db.seed_user(
        user_id=canonical_user_id,
        username=username,
        password=password,
    )
    auth_db.seed_persona_profile(profile_id=persona_profile_id)

    before_persona = auth_db.get_persona_profile(persona_profile_id)
    assert before_persona is not None
    before_snapshot = {
        "name": before_persona.name,
        "system_prompt": before_persona.system_prompt,
        "model_provider": before_persona.model_provider,
        "model_id": before_persona.model_id,
        "temperature": before_persona.temperature,
    }

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload = _login(client, username=username, password=password)
        _disable_single_user_fallback(monkeypatch)

        response = client.patch(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload['token']}"},
            json={
                "display_name": "Persona Separator",
                "avatar_url": "https://example.com/avatar.png",
                "timezone": "UTC",
            },
        )

    assert response.status_code == 200
    after_persona = auth_db.get_persona_profile(persona_profile_id)
    assert after_persona is not None
    assert {
        "name": after_persona.name,
        "system_prompt": after_persona.system_prompt,
        "model_provider": after_persona.model_provider,
        "model_id": after_persona.model_id,
        "temperature": after_persona.temperature,
    } == before_snapshot
    _assert_profile_row(
        auth_db,
        user_id=canonical_user_id,
        display_name="Persona Separator",
        avatar_url="https://example.com/avatar.png",
        timezone="UTC",
    )


def test_distinct_session_users_receive_distinct_profiles(monkeypatch):
    _configure_remote_session_env(monkeypatch)

    auth_db = _ProfileAuthDb()
    user_a_id = "acct-profile-6a"
    user_b_id = "acct-profile-6b"
    auth_db.seed_user(
        user_id=user_a_id,
        username="alpha@example.com",
        password="s3cret",
    )
    auth_db.seed_user(
        user_id=user_b_id,
        username="beta@example.com",
        password="s3cret",
    )

    with _build_test_client(auth_db) as (client, _session_store, _fake_redis):
        payload_a = _login(client, username="alpha@example.com", password="s3cret")
        payload_b = _login(client, username="beta@example.com", password="s3cret")
        _disable_single_user_fallback(monkeypatch)

        response_a = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload_a['token']}"},
        )
        response_b = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload_b['token']}"},
        )
        assert response_a.status_code == 200
        assert response_b.status_code == 200

        patch_a = client.patch(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload_a['token']}"},
            json={"display_name": "Alpha"},
        )

        read_a = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload_a['token']}"},
        )
        read_b = client.get(
            "/api/user/profile",
            headers={"Authorization": f"Bearer {payload_b['token']}"},
        )

    assert patch_a.status_code == 200
    assert response_a.json()["profile"]["user_id"] == user_a_id
    assert response_b.json()["profile"]["user_id"] == user_b_id
    assert read_a.json()["profile"]["display_name"] == "Alpha"
    assert read_b.json()["profile"]["display_name"] is None
    assert read_a.json()["profile"]["user_id"] == user_a_id
    assert read_b.json()["profile"]["user_id"] == user_b_id
    _assert_profile_row(
        auth_db,
        user_id=user_a_id,
        display_name="Alpha",
        avatar_url=None,
        timezone=None,
    )
    _assert_profile_row(
        auth_db,
        user_id=user_b_id,
        display_name=None,
        avatar_url=None,
        timezone=None,
    )
