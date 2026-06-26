from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.auth import issue_session_token
from guardian.core import auth_dependencies as auth_dependencies_module
from guardian.core.session_store import SessionStore
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
    ):
        return {
            "id": 4242,
            "user_id": user_id,
            "title": title,
            "summary": summary,
            "project_id": project_id,
            "metadata": metadata,
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

    app = FastAPI()
    app.include_router(chat.api_chat_router)
    return TestClient(app), session_store


def test_remote_thread_creation_requires_session_or_jwt(monkeypatch):
    client, _session_store = _remote_chat_client(monkeypatch)

    response = client.post("/api/chat/threads", json={"title": "Remote thread"})

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Remote mode requires session/JWT auth; X-API-Key is local-only"
    )


def test_remote_thread_creation_accepts_bearer_session(monkeypatch):
    client, session_store = _remote_chat_client(monkeypatch)
    token, _expires = issue_session_token(
        subject="remote-thread-user",
        ttl_seconds=60,
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
