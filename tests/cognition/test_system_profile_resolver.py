from __future__ import annotations

from typing import Any

import pytest

from guardian.cognition.system_profiles.resolver import (
    ProfileResolutionError,
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
            "active_profile_revision": None,
        }

    def get_chat_thread(self, thread_id: int) -> dict[str, Any] | None:
        if thread_id != self.thread["id"]:
            return None
        return {
            "id": self.thread["id"],
            "metadata": dict(self.thread["metadata"]),
            "active_profile_id": self.thread["active_profile_id"],
            "active_profile_revision": self.thread["active_profile_revision"],
            "user_id": self.thread.get("user_id"),
        }

    def set_thread_active_profile_id(
        self,
        thread_id: int,
        profile_id: str | None,
        *,
        profile_revision: int | None = None,
    ) -> bool:
        if thread_id != self.thread["id"]:
            return False
        self.thread["active_profile_id"] = profile_id
        self.thread["active_profile_revision"] = profile_revision
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


@pytest.fixture
def persona_profiles():
    from guardian.cognition.system_profiles import store
    from guardian.tests.test_persona_profile_runtime import _persona_profile_session

    with _persona_profile_session():
        store.create_persona_profile(
            account_id="account-a",
            profile_id="axis",
            name="Axis One",
            system_prompt="Original instructions.",
            model_provider="openai",
            model_id="original-model",
            temperature=0.2,
        )
        yield store


def test_exact_revision_survives_edit_and_reselection(persona_profiles):
    db = _FakeChatDB()
    db.thread["user_id"] = "account-a"
    selected = switch_thread_profile(1, "axis", chatlog_db=db)
    assert selected.active_profile_revision == 1
    assert db.thread["active_profile_revision"] == 1
    persona_profiles.update_persona_profile(
        "axis",
        account_id="account-a",
        name="Axis Two",
        system_prompt="New instructions.",
        model_provider="anthropic",
        model_id="new-model",
        temperature=0.7,
    )
    resolved = resolve_thread_system_profile(1, chatlog_db=db)
    assert resolved.model_dump() == selected.model_dump()
    assert (
        resolved.name,
        resolved.system_prompt,
        resolved.provider_override,
        resolved.model_override,
        resolved.temperature_override,
    ) == (
        "Axis One",
        "Original instructions.",
        "openai",
        "original-model",
        0.2,
    )
    assert resolved.source == "persona_profile_revision"
    advanced = switch_thread_profile(1, "axis", chatlog_db=db)
    assert db.thread["active_profile_revision"] == 2
    assert (
        advanced.name,
        advanced.system_prompt,
        advanced.provider_override,
        advanced.model_override,
        advanced.temperature_override,
    ) == (
        "Axis Two",
        "New instructions.",
        "anthropic",
        "new-model",
        0.7,
    )


@pytest.mark.parametrize("revision", [None, 99, 0, -1, True, "1", 1.0])
def test_unresolvable_persona_pin_never_falls_forward(persona_profiles, revision):
    db = _FakeChatDB()
    db.thread.update(
        user_id="account-a", active_profile_id="axis", active_profile_revision=revision
    )
    with pytest.raises(ProfileResolutionError, match=ProfileResolutionError.code):
        resolve_thread_system_profile(1, chatlog_db=db)
    assert db.thread["active_profile_revision"] == revision


@pytest.mark.parametrize("owner", ["account-b", None])
def test_exact_revision_requires_canonical_thread_owner(persona_profiles, owner):
    db = _FakeChatDB()
    db.thread.update(user_id=owner, active_profile_id="axis", active_profile_revision=1)
    db.thread["metadata"]["user_id"] = "account-a"
    with pytest.raises(ProfileResolutionError):
        resolve_thread_system_profile(1, chatlog_db=db)
    with pytest.raises(ValueError, match="unknown_profile_id"):
        switch_thread_profile(1, "axis", chatlog_db=db)


def test_builtin_and_flow_activation_clear_pin(persona_profiles, monkeypatch):
    db = _FakeChatDB()
    db.thread["user_id"] = "account-a"
    switch_thread_profile(1, "axis", chatlog_db=db)
    for profile_id in ("default", "local_mode", "cloud_mode", "env-profile"):
        monkeypatch.setenv(
            "GUARDIAN_SYSTEM_PROFILES_JSON",
            '[{"profile_id":"env-profile","provider_override":"local"}]',
        )
        switch_thread_profile(1, profile_id, chatlog_db=db)
        assert db.thread["active_profile_revision"] is None
        assert (
            resolve_thread_system_profile(1, chatlog_db=db).active_profile_revision
            is None
        )
        switch_thread_profile(1, "axis", chatlog_db=db)
    flow = persist_flow_profile_override(
        1,
        {
            "profile_id": "flow-only",
            "provider_override": "local",
            "system_prompt": "Flow instructions.",
        },
        chatlog_db=db,
    )
    assert db.thread["active_profile_revision"] is None
    assert flow.source == "flow_override"
    assert flow.system_prompt == "Flow instructions."


def test_pinned_revision_ignores_colliding_flow_metadata(persona_profiles):
    db = _FakeChatDB()
    db.thread.update(
        user_id="account-a", active_profile_id="axis", active_profile_revision=1
    )
    db.thread["metadata"]["profile_overrides"] = {
        "axis": {"profile_id": "axis", "system_prompt": "Unselected override."}
    }
    assert (
        resolve_thread_system_profile(1, chatlog_db=db).system_prompt
        == "Original instructions."
    )
    activated = persist_flow_profile_override(
        1,
        {
            "profile_id": "axis",
            "provider_override": "local",
            "system_prompt": "Selected flow.",
        },
        chatlog_db=db,
    )
    assert activated.active_profile_revision is None
    assert activated.system_prompt == "Selected flow."


def test_store_exact_read_rejects_corrupt_manifest(persona_profiles):
    from guardian.db.models import PersonaProfileRevision

    with persona_profiles._get_session_factory().begin() as session:
        row = session.get(PersonaProfileRevision, ("axis", 1))
        row.manifest_json = {**row.manifest_json, "revision": 2}
    db = _FakeChatDB()
    db.thread.update(
        user_id="account-a", active_profile_id="axis", active_profile_revision=1
    )
    with pytest.raises(ProfileResolutionError):
        resolve_thread_system_profile(1, chatlog_db=db)
    assert (
        persona_profiles.get_persona_profile_revision_manifest(
            "axis",
            account_id="account-b",
            revision=1,
        )
        is None
    )
