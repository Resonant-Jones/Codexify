from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from guardian.routes import tools


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


def test_tools_execute_switches_profile_and_emits_event(monkeypatch):
    fake_db = _FakeChatDB()
    events: list[tuple[str, dict[str, Any]]] = []

    monkeypatch.setattr(tools, "chatlog_db", fake_db)
    monkeypatch.setattr(
        tools,
        "event_bus",
        SimpleNamespace(
            emit_event=lambda topic, payload: events.append((topic, payload))
        ),
    )
    tools.JOBS.clear()

    response = tools.tools_execute(
        tools.ToolRequest(
            name="guardian.profile.switch",
            args={"thread_id": 1, "profile_id": "local_mode"},
        ),
        api_key="test",
    )
    job_id = response["job_id"]
    result = tools.JOBS[job_id]["result"]

    assert result["ok"] is True
    assert result["active_profile_id"] == "local_mode"
    assert result["provider_override"] == "local"
    assert events
    assert events[0][0] == "thread.profile.switched"
