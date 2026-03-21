from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from guardian.cognition.system_profiles.resolver import ResolvedSystemProfile
from guardian.routes import chat, tools


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


def _resolved_profile(profile_id: str) -> ResolvedSystemProfile:
    return ResolvedSystemProfile(
        profile_id=profile_id,
        active_profile_id=profile_id,
        name="Local Mode",
        mode="local",
        provider_override="local",
        model_override="mlx-community/Llama-3B",
        system_prompt_blocks={"behavior": "Prefer local execution."},
    )


def test_chat_profile_switch_route_success(test_client, monkeypatch):
    fake_db = _FakeChatDB()
    events: list[tuple[str, dict[str, Any]]] = []

    monkeypatch.setattr(chat, "chatlog_db", fake_db)
    monkeypatch.setattr(
        chat,
        "switch_thread_profile",
        lambda thread_id, profile_id, chatlog_db=None: _resolved_profile(
            profile_id
        ),
    )
    monkeypatch.setattr(
        chat,
        "event_bus",
        SimpleNamespace(
            emit_event=lambda topic, payload: events.append((topic, payload))
        ),
    )

    tools_execute = MagicMock()
    monkeypatch.setattr(tools, "tools_execute", tools_execute)

    response = test_client.post(
        "/api/chat/1/profile", json={"profile_id": "local_mode"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["thread_id"] == 1
    assert payload["active_profile_id"] == "local_mode"
    assert payload["profile"]["profile_id"] == "local_mode"

    assert events
    assert events[0][0] == "thread.profile.switched"
    tools_execute.assert_not_called()


def test_chat_profile_switch_route_rejects_missing_profile_id(
    test_client, monkeypatch
):
    fake_db = _FakeChatDB()
    monkeypatch.setattr(chat, "chatlog_db", fake_db)
    monkeypatch.setattr(chat, "switch_thread_profile", MagicMock())

    response = test_client.post("/api/chat/1/profile", json={})

    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"]["error"] == "profile_id_required"
    chat.switch_thread_profile.assert_not_called()


def test_chat_profile_switch_route_handles_switch_errors(
    test_client, monkeypatch
):
    fake_db = _FakeChatDB()
    monkeypatch.setattr(chat, "chatlog_db", fake_db)

    def _raise_error(*_args, **_kwargs):
        raise RuntimeError("chat_db_unavailable")

    monkeypatch.setattr(chat, "switch_thread_profile", _raise_error)

    response = test_client.post(
        "/api/chat/1/profile", json={"profile_id": "local_mode"}
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["detail"]["error"] == "chat_db_unavailable"
