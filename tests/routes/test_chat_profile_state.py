from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from guardian.cognition.system_profiles.resolver import ResolvedSystemProfile
from guardian.core.dependencies import RequestUserScope
from guardian.routes import chat
from tests.cognition.test_system_profile_resolver import _FakeChatDB as BindingChatDB
from tests.cognition.test_system_profile_resolver import (
    persona_profiles as persona_profiles,  # noqa: PLC0414
)


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

    payload = chat.chat_get_thread_profile(
        1,
        api_key="test",
        request_user_scope=RequestUserScope(
            user_id="local",
            subject_id="local",
            account_id="local",
            multi_user_enabled=False,
        ),
    )

    assert payload["ok"] is True
    assert payload["thread_id"] == 1
    assert payload["profile"]["active_profile_id"] == "local_mode"
    assert payload["profile"]["provider_override"] == "local"
    assert len(payload["profiles"]) == 2
    assert payload["profiles"][1]["id"] == "local_mode"


def _scope(account_id="account-a"):
    return RequestUserScope(
        user_id=account_id,
        subject_id=account_id,
        account_id=account_id,
        multi_user_enabled=True,
    )


def test_profile_routes_pin_reselect_clear_and_report_revision(
    persona_profiles, monkeypatch
):
    db = BindingChatDB()
    db.thread["user_id"] = "account-a"
    monkeypatch.setattr(chat, "chatlog_db", db)
    monkeypatch.setattr(chat.event_bus, "emit_event", lambda *args, **kwargs: None)

    def switch(profile_id):
        return chat.api_chat_switch_thread_profile(
            1,
            chat.ThreadProfileSwitchRequest(profile_id=profile_id),
            api_key="test",
            request_user_scope=_scope(),
        )

    selected = switch("axis")
    assert selected["ok"] is True
    assert selected["active_profile_revision"] == 1
    persona_profiles.update_persona_profile(
        "axis", account_id="account-a", system_prompt="Revision two."
    )
    state = chat.chat_get_thread_profile(1, api_key="test", request_user_scope=_scope())
    assert state["profile"]["active_profile_revision"] == 1
    assert state["profile"]["system_prompt"] == "Original instructions."
    assert state["profile"]["source"] == "persona_profile_revision"
    assert switch("axis")["active_profile_revision"] == 2
    cleared = switch("local_mode")
    assert cleared["active_profile_revision"] is None
    assert cleared["profile"]["active_profile_revision"] is None
    assert db.thread["active_profile_revision"] is None
    assert switch("axis")["active_profile_revision"] == 2


def test_profile_selection_rejects_foreign_profile_and_thread(
    persona_profiles, monkeypatch
):
    db = BindingChatDB()
    db.thread["user_id"] = "account-b"
    monkeypatch.setattr(chat, "chatlog_db", db)
    body = chat.ThreadProfileSwitchRequest(profile_id="axis")
    rejected = chat.api_chat_switch_thread_profile(
        1,
        body,
        api_key="test",
        request_user_scope=_scope("account-b"),
    )
    assert rejected["ok"] is False
    assert "account-a" not in str(rejected)
    assert db.thread["active_profile_revision"] is None
    with pytest.raises(HTTPException) as exc:
        chat.api_chat_switch_thread_profile(
            1, body, api_key="test", request_user_scope=_scope()
        )
    assert exc.value.status_code == 403


def test_profile_state_reports_unavailable_pin_without_success(
    persona_profiles, monkeypatch
):
    db = BindingChatDB()
    db.thread.update(
        user_id="account-a", active_profile_id="axis", active_profile_revision=99
    )
    monkeypatch.setattr(chat, "chatlog_db", db)
    state = chat.chat_get_thread_profile(1, api_key="test", request_user_scope=_scope())
    assert state["ok"] is False
    assert state["error"] == "system_profile_resolution_unavailable"
    assert state["profile"]["active_profile_revision"] == 99
    assert state["profile"]["source"] == "unavailable"
    assert db.thread["active_profile_revision"] == 99


@pytest.mark.parametrize(
    "field", ["revision", "active_profile_revision", "profile_revision"]
)
def test_profile_switch_does_not_accept_client_revisions(field):
    with pytest.raises(ValidationError):
        chat.ThreadProfileSwitchRequest.model_validate({"profile_id": "axis", field: 1})
