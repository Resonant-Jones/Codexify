from __future__ import annotations

from typing import Any

from guardian.cognition.system_profiles.resolver import (
    list_available_system_profiles,
    persist_flow_profile_override,
    resolve_thread_system_profile,
    switch_thread_profile,
)


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

    def set_thread_profile_overrides(
        self, thread_id: int, overrides: dict[str, Any]
    ) -> bool:
        if thread_id != self.thread["id"]:
            return False
        self.thread["metadata"]["profile_overrides"] = dict(overrides)
        return True


def test_persist_flow_override_sets_active_profile_and_merges_payload():
    db = _FakeChatDB()

    resolved = persist_flow_profile_override(
        1,
        {
            "profile_id": "local_mode",
            "model_override": "mlx-community/Llama-3B-Instruct",
            "system_prompt_blocks": {
                "style": "Use terse bullet points.",
                "behavior": "Prefer local-first execution paths.",
            },
        },
        chatlog_db=db,
    )

    assert db.thread["active_profile_id"] == "local_mode"
    overrides = db.thread["metadata"]["profile_overrides"]
    assert "local_mode" in overrides
    assert resolved.active_profile_id == "local_mode"
    assert resolved.provider_override == "local"
    assert (
        resolved.system_prompt_blocks["behavior"]
        == "Prefer local-first execution paths."
    )


def test_switch_thread_profile_updates_thread_state():
    db = _FakeChatDB()
    switched = switch_thread_profile(1, "local_mode", chatlog_db=db)
    assert db.thread["active_profile_id"] == "local_mode"
    assert switched.active_profile_id == "local_mode"

    resolved = resolve_thread_system_profile(1, chatlog_db=db)
    assert resolved.active_profile_id == "local_mode"
    assert resolved.provider_override == "local"


def test_list_available_profiles_includes_defaults():
    db = _FakeChatDB()

    profiles = list_available_system_profiles(thread_id=1, chatlog_db=db)
    profile_ids = {profile["id"] for profile in profiles}

    assert "default" in profile_ids
    assert "local_mode" in profile_ids
