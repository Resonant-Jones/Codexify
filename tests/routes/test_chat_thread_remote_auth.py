from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.protocol_tokens import ACCOUNT_AUTH_FAILURE_HEADER, ErrorCode
from guardian.core import auth_dependencies as auth_dependencies_module
from guardian.core.session_store import SessionStore
from guardian.core import session_store as session_store_module
from guardian.routes import chat


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


class _FakeChatLogDB:
    def get_recent_thread(self, user_id):
        return None

    def create_chat_thread(
        self,
        *,
        user_id,
        title,
        summary,
        project_id=None,
        metadata=None,
        origin_system=None,
    ):
        return {
            "id": 4242,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "metadata": metadata,
            "origin_system": origin_system,
        }

    def write_audit_log(self, *args, **kwargs):
        return None


def _remote_chat_client(monkeypatch) -> tuple[TestClient, SessionStore]:
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "remote-session-secret")
    monkeypatch.setattr(chat, "chatlog_db", _FakeChatLogDB())

    fake_redis = _FakeRedis()
    session_store = SessionStore(redis_client=fake_redis)
    monkeypatch.setattr(
        auth_dependencies_module,
        "get_session_store",
        lambda: session_store,
    )
    monkeypatch.setattr(session_store_module, "get_session_store", lambda: session_store)

    app = FastAPI()
    app.include_router(chat.api_chat_router)
    return TestClient(app), session_store


def test_remote_thread_creation_requires_session_or_jwt(monkeypatch):
    client, _session_store = _remote_chat_client(monkeypatch)

    response = client.post("/api/chat/threads", json={"title": "Remote thread"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Account session required"
    assert response.headers[ACCOUNT_AUTH_FAILURE_HEADER.lower()] == (
        ErrorCode.ACCOUNT_SESSION_INVALID.value
    )


def test_remote_account_failure_classifies_only_account_lane(monkeypatch):
    client, _session_store = _remote_chat_client(monkeypatch)
    operator_token, _expires = issue_session_token(
        subject="operator",
        ttl_seconds=60,
        purpose=OPERATOR_SESSION_PURPOSE,
    )
    expired_account_token, _expires = issue_session_token(
        subject="remote-thread-user",
        ttl_seconds=-60,
        purpose=ACCOUNT_SESSION_PURPOSE,
    )
    guest_token, _expires = issue_guest_session_token(
        room_id="room-1",
        room_slug="room-one",
        participant_id="participant-1",
        invitation_id="invitation-1",
        ttl_seconds=60,
    )
    expired_guest_token, _expires = issue_guest_session_token(
        room_id="room-1",
        room_slug="room-one",
        participant_id="participant-1",
        invitation_id="invitation-2",
        ttl_seconds=-60,
    )

    operator_response = client.post(
        "/api/chat/threads",
        json={"title": "Remote thread"},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    expired_account_response = client.post(
        "/api/chat/threads",
        json={"title": "Remote thread"},
        headers={"Authorization": f"Bearer {expired_account_token}"},
    )
    guest_response = client.post(
        "/api/chat/threads",
        json={"title": "Remote thread"},
        headers={"Authorization": f"Bearer {guest_token}"},
    )
    expired_guest_response = client.post(
        "/api/chat/threads",
        json={"title": "Remote thread"},
        headers={"Authorization": f"Bearer {expired_guest_token}"},
    )

    assert operator_response.status_code == 401
    assert ACCOUNT_AUTH_FAILURE_HEADER.lower() not in operator_response.headers
    assert expired_account_response.status_code == 401
    assert expired_account_response.headers[ACCOUNT_AUTH_FAILURE_HEADER.lower()] == (
        ErrorCode.ACCOUNT_SESSION_INVALID.value
    )
    assert guest_response.status_code == 401
    assert ACCOUNT_AUTH_FAILURE_HEADER.lower() not in guest_response.headers
    assert expired_guest_response.status_code == 401
    assert ACCOUNT_AUTH_FAILURE_HEADER.lower() not in expired_guest_response.headers


def test_remote_thread_creation_accepts_bearer_session(monkeypatch):
    client, session_store = _remote_chat_client(monkeypatch)
    token, _expires = issue_session_token(
        subject="remote-thread-user",
        ttl_seconds=60,
        purpose=ACCOUNT_SESSION_PURPOSE,
    )
    session_store.store(token, "remote-thread-user", 60)

    response = client.post(
        "/api/chat/threads",
        json={"title": "Remote thread"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["id"] == 4242
    assert payload["thread"]["title"] == "Remote thread"
