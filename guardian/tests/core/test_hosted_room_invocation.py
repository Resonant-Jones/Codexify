from __future__ import annotations

from types import SimpleNamespace

import pytest

from guardian.core.hosted_room_invocation import (
    HostedRoomInvocationPreparationError,
    prepare_hosted_room_guardian_invocation,
)
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


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows, *, active_guardian_count=1, guardian_rows=None):
        self._rows = rows
        self._active_guardian_count = active_guardian_count
        self._guardian_rows = guardian_rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
        return False

    def get(self, model, identifier):
        return self._rows.get((model, identifier))

    def scalar(self, _statement):
        return self._active_guardian_count

    def scalars(self, _statement):
        return _ScalarRows(self._guardian_rows or [])

    def close(self):
        return None


class _FakeDB:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    def get_session(self):
        return self._session_factory()


def _valid_db(
    *,
    guest: bool = False,
    active_guardian_count: int = 1,
    guardian_rows=None,
):
    room = SimpleNamespace(
        id="room-1",
        owner_account_id="account-owner",
        status="active",
        backing_thread_id=7,
    )
    actor = SimpleNamespace(
        id="guardian-1",
        room_id="room-1",
        kind="agent",
        role="agent",
        state="active",
        actor_source=RESIDENT_SOURCE,
        actor_ref=GUARDIAN_REF,
        bound_account_id=None,
        invitation_id=None,
        display_name=GUARDIAN_DISPLAY,
    )
    source_participant = SimpleNamespace(
        id="guest-1" if guest else "owner-1",
        room_id="room-1",
        kind="human",
        role="member" if guest else "owner",
        state="active",
        invitation_id="invite-1" if guest else None,
    )
    source = SimpleNamespace(
        id=42,
        thread_id=7,
        role="user",
        content="A human room message",
        hosted_room_participant_id=source_participant.id,
        sender_display_name_snapshot="Guest" if guest else "Owner",
    )
    rows = {
        (HostedRoom, "room-1"): room,
        (ChatThread, 7): SimpleNamespace(id=7),
        (ChatMessage, 42): source,
        (HostedRoomParticipant, source_participant.id): source_participant,
        (HostedRoomParticipant, "guardian-1"): actor,
    }
    if guest:
        rows[(HostedRoomInvite, "invite-1")] = SimpleNamespace(
            id="invite-1",
            room_id="room-1",
            status="accepted",
            expires_at=None,
        )
    guardian_rows = guardian_rows if guardian_rows is not None else [actor]

    def session_factory():
        return _FakeSession(
            rows,
            active_guardian_count=active_guardian_count,
            guardian_rows=guardian_rows,
        )

    return _FakeDB(session_factory)


def test_owner_preparation_builds_canonical_explicit_invocation_task():
    prepared = prepare_hosted_room_guardian_invocation(
        _valid_db(),
        room_id="room-1",
        source_message_id=42,
        actor_participant_id="guardian-1",
        requester_authority="owner",
        requester_participant_id=None,
        request_id="request-9f",
    )

    task = prepared.task
    metadata = task.hosted_room_invocation
    assert prepared.request_id == "request-9f"
    assert prepared.room_id == "room-1"
    assert prepared.thread_id == 7
    assert prepared.source_message_id == 42
    assert prepared.guardian_participant_id == "guardian-1"
    assert task.user_id == "account-owner"
    assert task.thread_id == 7
    assert task.latest_turn_message_id == 42
    assert task.provider is None
    assert task.model is None
    assert task.selection_source is None
    assert task.provider_pinned is False
    assert metadata is not None
    assert metadata.requester_authority == "owner"
    assert metadata.requester_participant_id is None
    assert metadata.actor_source == RESIDENT_SOURCE
    assert metadata.actor_ref == GUARDIAN_REF
    assert metadata.source_message_id == 42
    assert f"turn_id={prepared.turn_id}" in task.origin


def test_guest_preparation_preserves_requester_lineage_without_credentials():
    prepared = prepare_hosted_room_guardian_invocation(
        _valid_db(guest=True),
        room_id="room-1",
        source_message_id=42,
        actor_participant_id="guardian-1",
        requester_authority="guest",
        requester_participant_id="guest-1",
        request_id="request-guest",
    )

    metadata = prepared.task.hosted_room_invocation
    assert metadata is not None
    assert metadata.requester_authority == "guest"
    assert metadata.requester_participant_id == "guest-1"
    assert "token" not in prepared.task.to_dict()
    assert "credential" not in prepared.task.to_dict()


@pytest.mark.parametrize(
    ("db_kwargs", "actor_id", "expected_code"),
    [
        ({"guardian_rows": []}, "guardian-1", "hosted_room_actor_invalid"),
        ({"active_guardian_count": 2}, "guardian-1", "hosted_room_actor_invalid"),
        ({}, "wrong-actor", "hosted_room_actor_invalid"),
    ],
)
def test_preparation_rejects_noncanonical_or_ambiguous_guardian(
    db_kwargs, actor_id, expected_code
):
    with pytest.raises(HostedRoomInvocationPreparationError) as exc_info:
        prepare_hosted_room_guardian_invocation(
            _valid_db(**db_kwargs),
            room_id="room-1",
            source_message_id=42,
            actor_participant_id=actor_id,
            requester_authority="owner",
            requester_participant_id=None,
            request_id="request-9f",
        )

    assert exc_info.value.code == expected_code
