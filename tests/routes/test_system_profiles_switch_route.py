from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import system_profiles


class _FakeChatDB:
    def __init__(self) -> None:
        self.thread: dict[str, Any] = {
            "id": 1,
            "metadata": {},
            "active_profile_id": None,
        }

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        if thread_id != self.thread["id"]:
            return None
        return {
            "id": self.thread["id"],
            "metadata": dict(self.thread["metadata"]),
            "active_profile_id": self.thread["active_profile_id"],
        }

    def set_thread_active_profile_id(
        self, thread_id: int, profile_id: str | None
    ) -> bool:
        if thread_id != self.thread["id"]:
            return False
        self.thread["active_profile_id"] = profile_id
        return True


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    app = FastAPI()
    app.include_router(system_profiles.router)
    return TestClient(app)


def test_system_profiles_switch_route_switches_profile(monkeypatch) -> None:
    fake_db = _FakeChatDB()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(system_profiles, "_CHATLOG_DB", fake_db)
    monkeypatch.setattr(
        system_profiles,
        "_EVENT_BUS",
        SimpleNamespace(
            emit_event=lambda topic, payload: events.append((topic, payload))
        ),
    )

    client = _build_client(monkeypatch)
    response = client.post(
        "/api/system-profiles/switch",
        headers={"X-API-Key": "test-key"},
        json={"thread_id": 1, "profile_id": "local_mode"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["active_profile_id"] == "local_mode"
    assert payload["provider_override"] == "local"
    assert fake_db.thread["active_profile_id"] == "local_mode"
    assert events
    assert events[0][0] == "thread.profile.switched"


def test_system_profiles_switch_route_requires_auth(monkeypatch) -> None:
    monkeypatch.setattr(system_profiles, "_CHATLOG_DB", _FakeChatDB())
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/system-profiles/switch",
        headers={"X-API-Key": "bad-key"},
        json={"thread_id": 1, "profile_id": "local_mode"},
    )

    assert response.status_code == 401
