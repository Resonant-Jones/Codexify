from __future__ import annotations

from guardian.cognition.system_profiles.resolver import ResolvedSystemProfile
from guardian.routes import chat


class _FakeChatDB:
    def get_chat_thread(self, thread_id: int):
        if thread_id != 1:
            return None
        return {"id": 1, "active_profile_id": "local_mode", "metadata": {}}


def test_chat_get_thread_profile_returns_resolved_and_catalog(monkeypatch):
    monkeypatch.setattr(chat, "chatlog_db", _FakeChatDB())
    monkeypatch.setattr(
        chat,
        "resolve_thread_system_profile",
        lambda thread_id, chatlog_db=None: ResolvedSystemProfile(
            profile_id="local_mode",
            active_profile_id="local_mode",
            name="Local Mode",
            mode="local",
            provider_override="local",
            model_override="mlx-community/Llama-3B",
            system_prompt_blocks={"behavior": "Prefer local execution."},
        ),
    )
    monkeypatch.setattr(
        chat,
        "list_available_system_profiles",
        lambda thread_id, chatlog_db=None: [
            {"id": "default", "name": "Default", "mode": "cloud"},
            {"id": "local_mode", "name": "Local Mode", "mode": "local"},
        ],
    )

    payload = chat.chat_get_thread_profile(1, api_key="test")

    assert payload["ok"] is True
    assert payload["thread_id"] == 1
    assert payload["profile"]["active_profile_id"] == "local_mode"
    assert payload["profile"]["provider_override"] == "local"
    assert len(payload["profiles"]) == 2
    assert payload["profiles"][1]["id"] == "local_mode"
