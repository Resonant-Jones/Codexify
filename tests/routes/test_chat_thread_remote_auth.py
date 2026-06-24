from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.auth import issue_session_token
from guardian.routes import chat


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


def _remote_chat_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "remote-session-secret")
    monkeypatch.setenv("GUARDIAN_API_KEY", "local-test-key")
    monkeypatch.setattr(chat, "chatlog_db", _FakeChatLogDB())

    app = FastAPI()
    app.include_router(chat.api_chat_router)
    return TestClient(app)


def test_remote_thread_creation_requires_session_or_jwt(monkeypatch):
    client = _remote_chat_client(monkeypatch)

    response = client.post("/api/chat/threads", json={"title": "Remote thread"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Remote mode requires a valid session/JWT token"


def test_remote_thread_creation_accepts_bearer_session(monkeypatch):
    client = _remote_chat_client(monkeypatch)
    token, _expires = issue_session_token(
        subject="remote-thread-user",
        ttl_seconds=60,
    )

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
