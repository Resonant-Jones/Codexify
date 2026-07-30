from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from guardian.core.completion_terminal import successful_non_stream_terminal
from guardian.core.hosted_room_completion_context import (
    HostedRoomCompletionValidationError,
    ValidatedHostedRoomCompletionContext,
    validate_hosted_room_completion_context,
)
from guardian.core.config import Settings
from guardian.db.models import (
    ChatMessage,
    ChatThread,
    HostedRoom,
    HostedRoomInvite,
    HostedRoomParticipant,
)
from guardian.hosted_rooms.actor_tokens import (
    GUARDIAN_DISPLAY,
    GUARDIAN_REF,
    RESIDENT_SOURCE,
)
from guardian.tasks.types import (
    ChatCompletionTask,
    HostedRoomInvocationMetadata,
)
from guardian.workers import chat_worker


class _FakeSession:
    def __init__(self, rows: dict[tuple[type, object], object], count: int = 1):
        self.rows = rows
        self.count = count

    def get(self, model: type, identifier: object):
        return self.rows.get((model, identifier))

    def scalar(self, _statement):
        return self.count

    def close(self):
        return None


class _FakeDB:
    def __init__(self, session: _FakeSession):
        self.session = session

    def get_session(self):
        return self.session


def _metadata(*, authority: str = "owner", requester: str | None = None):
    return HostedRoomInvocationMetadata(
        room_id="room-1",
        source_message_id=42,
        actor_participant_id="guardian-1",
        actor_source=RESIDENT_SOURCE,
        actor_ref=GUARDIAN_REF,
        requester_authority=authority,
        requester_participant_id=requester,
    )


def _task(*, authority: str = "owner", requester: str | None = None):
    return ChatCompletionTask(
        user_id="local",
        thread_id=7,
        provider="local",
        model="qwen3.5:27b",
        selection_source="explicit",
        provider_pinned=True,
        hosted_room_invocation=(
            _metadata(authority=authority, requester=requester)
        ),
    )


def _valid_db(
    *,
    room_status: str = "active",
    source_role: str = "user",
    source_content: str = "Guardian:\n@Guardian\nhello",
    source_participant_id: str | None = "human-1",
    source_snapshot: str | None = "Guest",
    source_participant_state: str = "active",
    actor_state: str = "active",
    actor_display: str = GUARDIAN_DISPLAY,
    actor_source: str = RESIDENT_SOURCE,
    actor_ref: str = GUARDIAN_REF,
    actor_bound_account: str | None = None,
    actor_invitation: str | None = None,
    active_guardian_count: int = 1,
    requester: bool = False,
    requester_state: str = "active",
    requester_invitation: str | None = "invite-2",
    requester_invite_status: str = "accepted",
    invite_status: str = "accepted",
    invite_expires_at: datetime | None = None,
):
    room = SimpleNamespace(
        id="room-1",
        status=room_status,
        backing_thread_id=7,
    )
    source = SimpleNamespace(
        id=42,
        thread_id=7,
        role=source_role,
        content=source_content,
        hosted_room_participant_id=source_participant_id,
        sender_display_name_snapshot=source_snapshot,
    )
    human = SimpleNamespace(
        id="human-1",
        room_id="room-1",
        kind="human",
        role="member",
        state=source_participant_state,
        invitation_id="invite-1",
    )
    actor = SimpleNamespace(
        id="guardian-1",
        room_id="room-1",
        kind="agent",
        role="agent",
        state=actor_state,
        actor_source=actor_source,
        actor_ref=actor_ref,
        bound_account_id=actor_bound_account,
        invitation_id=actor_invitation,
        display_name=actor_display,
    )
    invite = SimpleNamespace(
        id="invite-1",
        room_id="room-1",
        status=invite_status,
        expires_at=invite_expires_at,
    )
    rows: dict[tuple[type, object], object] = {
        (ChatThread, 7): SimpleNamespace(id=7),
        (HostedRoom, "room-1"): room,
        (ChatMessage, 42): source,
        (HostedRoomParticipant, "human-1"): human,
        (HostedRoomParticipant, "guardian-1"): actor,
        (HostedRoomInvite, "invite-1"): invite,
    }
    if requester:
        rows[(HostedRoomParticipant, "requester-1")] = SimpleNamespace(
            id="requester-1",
            room_id="room-1",
            kind="human",
            role="member",
            state=requester_state,
            invitation_id=requester_invitation,
        )
        rows[(HostedRoomInvite, "invite-2")] = SimpleNamespace(
            id="invite-2",
            room_id="room-1",
            status=requester_invite_status,
            expires_at=invite_expires_at,
        )
    return _FakeDB(_FakeSession(rows, count=active_guardian_count))


def test_valid_owner_context_revalidates_room_source_actor_and_authority():
    context = validate_hosted_room_completion_context(
        _valid_db(),
        _task(),
    )

    assert context == ValidatedHostedRoomCompletionContext(
        room_id="room-1",
        thread_id=7,
        source_message_id=42,
        actor_participant_id="guardian-1",
        actor_source=RESIDENT_SOURCE,
        actor_ref=GUARDIAN_REF,
        sender_display_name_snapshot=GUARDIAN_DISPLAY,
        requester_authority="owner",
        requester_participant_id=None,
    )


def test_valid_guest_context_requires_current_invitation_lineage():
    context = validate_hosted_room_completion_context(
        _valid_db(requester=True),
        _task(authority="guest", requester="requester-1"),
    )

    assert context.requester_participant_id == "requester-1"


def test_missing_room_and_backing_thread_fail_closed():
    missing_room = _valid_db()
    missing_room.session.rows.pop((HostedRoom, "room-1"))
    with pytest.raises(HostedRoomCompletionValidationError) as room_error:
        validate_hosted_room_completion_context(missing_room, _task())
    assert room_error.value.code == "hosted_room_not_found"

    missing_thread = _valid_db()
    missing_thread.session.rows.pop((ChatThread, 7))
    with pytest.raises(HostedRoomCompletionValidationError) as thread_error:
        validate_hosted_room_completion_context(missing_thread, _task())
    assert thread_error.value.code == "hosted_room_thread_mismatch"


@pytest.mark.parametrize(
    ("db_kwargs", "expected_code"),
    [
        ({"room_status": "closed"}, "hosted_room_inactive"),
        ({"source_role": "assistant"}, "hosted_room_source_message_invalid"),
        ({"source_content": "   "}, "hosted_room_source_message_invalid"),
        ({"source_participant_id": None}, "hosted_room_source_message_invalid"),
        ({"source_snapshot": "   "}, "hosted_room_source_message_invalid"),
        ({"source_participant_state": "removed"}, "hosted_room_source_message_invalid"),
        ({"actor_state": "removed"}, "hosted_room_actor_inactive"),
        ({"actor_display": "Not Guardian"}, "hosted_room_actor_invalid"),
        ({"actor_bound_account": "user-1"}, "hosted_room_actor_invalid"),
        ({"actor_invitation": "invite-3"}, "hosted_room_actor_invalid"),
        ({"active_guardian_count": 2}, "hosted_room_actor_invalid"),
        ({"invite_status": "revoked"}, "hosted_room_source_message_invalid"),
        (
            {"requester": True, "requester_state": "removed"},
            "hosted_room_requester_invalid",
        ),
        (
            {
                "requester": True,
                "requester_invite_status": "revoked",
            },
            "hosted_room_authority_revoked",
        ),
    ],
)
def test_invalid_context_fails_closed_without_partial_persistence(
    db_kwargs, expected_code
):
    with pytest.raises(HostedRoomCompletionValidationError) as exc_info:
        validate_hosted_room_completion_context(
            _valid_db(**db_kwargs),
            _task(
                authority="guest" if db_kwargs.get("requester") else "owner",
                requester="requester-1" if db_kwargs.get("requester") else None,
            ),
        )

    assert exc_info.value.code == expected_code
    assert exc_info.value.metadata["failure_code"] == expected_code


def _stub_local_completion(monkeypatch, db):
    monkeypatch.setattr(chat_worker.dependencies, "chatlog_db", db)
    monkeypatch.setattr(chat_worker.event_bus, "emit_event", lambda *a, **k: None)
    monkeypatch.setattr(chat_worker, "_embed_message", lambda *a, **k: None)

    async def _build_messages(_task):
        return (
            [{"role": "user", "content": "source"}],
            "local",
            "qwen3.5:27b",
            {},
            None,
            None,
            {},
        )

    monkeypatch.setattr(chat_worker, "_build_messages_for_llm", _build_messages)
    monkeypatch.setattr(
        chat_worker,
        "get_settings",
        lambda: Settings(
            LLM_PROVIDER="local",
            ALLOW_CLOUD_PROVIDERS=True,
            CODEXIFY_LOCAL_ONLY_MODE=False,
            CODEXIFY_EGRESS_ALLOWLIST="groq,openai,minimax",
            LOCAL_LLM_MODEL="qwen3.5:27b",
            DEFAULT_LOCAL_MODEL="qwen3.5:27b",
            LLM_MODEL="qwen3.5:27b",
        ),
    )
    monkeypatch.setattr(
        chat_worker,
        "chat_with_ai",
        lambda *_a, **_k: "Guardian:\n@Guardian\nreply",
    )
    monkeypatch.setattr(
        chat_worker._chat_completion_service,
        "_execute_bounded_tool_turn_completion",
        lambda *_a, **_k: {
            "assistant_text": "Guardian:\n@Guardian\nreply",
            "terminal_evidence": successful_non_stream_terminal(
                provider="local", model="qwen3.5:27b"
            ).as_dict(),
        },
    )


def test_worker_persists_guardian_provenance_atomically_without_prefix(
    monkeypatch,
):
    db = MagicMock()
    db.create_message.return_value = 321
    db.write_audit_log = MagicMock()
    _stub_local_completion(monkeypatch, db)
    context = ValidatedHostedRoomCompletionContext(
        room_id="room-1",
        thread_id=7,
        source_message_id=42,
        actor_participant_id="guardian-1",
        actor_source=RESIDENT_SOURCE,
        actor_ref=GUARDIAN_REF,
        sender_display_name_snapshot=GUARDIAN_DISPLAY,
        requester_authority="owner",
        requester_participant_id=None,
    )
    validations: list[object] = []

    def _validate(_db, _task):
        validations.append(True)
        return context

    monkeypatch.setattr(
        chat_worker,
        "validate_hosted_room_completion_context",
        _validate,
    )

    result = chat_worker._run_chat_completion_task_compat(_task())

    assert result["message_id"] == 321
    assert len(validations) == 2
    assert db.create_message.call_args.args == (
        7,
        "assistant",
        "Guardian:\n@Guardian\nreply",
    )
    assert db.create_message.call_args.kwargs == {
        "hosted_room_participant_id": "guardian-1",
        "sender_display_name_snapshot": "Guardian",
    }
    db.create_message.assert_called_once()
    assert not db.update.called


def test_ordinary_worker_path_bypasses_hosted_room_validation_and_kwargs(
    monkeypatch,
):
    db = MagicMock()
    db.create_message.return_value = 322
    db.write_audit_log = MagicMock()
    _stub_local_completion(monkeypatch, db)

    def _unexpected_validation(*_args, **_kwargs):
        raise AssertionError("ordinary task queried Hosted Room state")

    monkeypatch.setattr(
        chat_worker,
        "validate_hosted_room_completion_context",
        _unexpected_validation,
    )

    chat_worker._run_chat_completion_task_compat(
        ChatCompletionTask(
            user_id="local",
            thread_id=7,
            provider="local",
            model="qwen3.5:27b",
            selection_source="explicit",
            provider_pinned=True,
        )
    )

    assert db.create_message.call_args.args == (
        7,
        "assistant",
        "Guardian:\n@Guardian\nreply",
    )
    assert db.create_message.call_args.kwargs == {}


def test_final_revalidation_failure_prevents_assistant_insert(monkeypatch):
    db = MagicMock()
    _stub_local_completion(monkeypatch, db)
    context = ValidatedHostedRoomCompletionContext(
        room_id="room-1",
        thread_id=7,
        source_message_id=42,
        actor_participant_id="guardian-1",
        actor_source=RESIDENT_SOURCE,
        actor_ref=GUARDIAN_REF,
        sender_display_name_snapshot=GUARDIAN_DISPLAY,
        requester_authority="owner",
        requester_participant_id=None,
    )
    calls = iter(
        [
            context,
            HostedRoomCompletionValidationError("hosted_room_authority_revoked"),
        ]
    )
    def _validate(_db, _task):
        value = next(calls)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(
        chat_worker,
        "validate_hosted_room_completion_context",
        _validate,
    )

    with pytest.raises(HostedRoomCompletionValidationError):
        chat_worker._run_chat_completion_task_compat(_task())

    db.create_message.assert_not_called()


def test_worker_emits_bounded_failure_code_for_invalid_invocation(monkeypatch):
    published: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        chat_worker,
        "_safe_publish",
        lambda _task_id, event_type, payload: published.append(
            (event_type, dict(payload or {}))
        ),
    )
    monkeypatch.setattr(chat_worker, "_safe_emit_live_event", lambda *a, **k: None)
    monkeypatch.setattr(chat_worker, "is_cancelled", lambda *_args: False)
    monkeypatch.setattr(chat_worker, "release_turn_lock", lambda *_args: True)
    monkeypatch.setattr(
        chat_worker,
        "validate_hosted_room_completion_context",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HostedRoomCompletionValidationError("hosted_room_actor_inactive")
        ),
    )
    monkeypatch.setattr(chat_worker, "dependencies", SimpleNamespace(chatlog_db=None))

    chat_worker._run_chat_task(_task())

    failed = next(payload for event, payload in published if event == "task.failed")
    assert failed["failure_code"] == "hosted_room_actor_inactive"
    assert failed["error"] == "Hosted Room completion authority validation failed"
