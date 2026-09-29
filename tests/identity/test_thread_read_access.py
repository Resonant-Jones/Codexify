"""Canonical thread-read policy for account and Hosted Room guest principals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from guardian.core import dependencies
from guardian.core.auth import issue_session_token
from guardian.core.dependencies import RequestUserScope
from guardian.core.hosted_room_session import (
    decode_principal,
    issue_guest_session_token,
)
from guardian.core.thread_access import require_thread_read_access
from guardian.db.models import HostedRoom, HostedRoomInvite, HostedRoomParticipant


def _account(account_id: str) -> RequestUserScope:
    return RequestUserScope(
        user_id=account_id,
        account_id=account_id,
        multi_user_enabled=True,
    )


def _guest(monkeypatch, *, room_id: str = "room-a", participant_id: str = "guest-a"):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-thread-access-test-secret")
    token, _ = issue_guest_session_token(
        room_id=room_id,
        room_slug=room_id,
        participant_id=participant_id,
        invitation_id="invite-a",
    )
    return decode_principal(token)


class _RoomSession:
    def __init__(
        self,
        *,
        room_status="active",
        participant_state="active",
        invite_status="accepted",
        invite_expires_at=None,
    ):
        self.room = SimpleNamespace(
            id="room-a",
            backing_thread_id=7,
            owner_account_id="account-a",
            status=room_status,
        )
        self.participant = SimpleNamespace(
            id="guest-a",
            room_id="room-a",
            state=participant_state,
            kind="human",
            role="member",
            invitation_id="invite-a",
        )
        self.invite = SimpleNamespace(
            id="invite-a",
            status=invite_status,
            expires_at=invite_expires_at,
        )

    def get(self, model, key):
        records = {
            HostedRoom: self.room,
            HostedRoomParticipant: self.participant,
            HostedRoomInvite: self.invite,
        }
        record = records.get(model)
        return record if record is not None and record.id == key else None


def test_owned_private_thread_is_readable():
    lookup = Mock(return_value={"id": 7, "user_id": "account-a"})
    access = require_thread_read_access(7, _account("account-a"), thread_lookup=lookup)
    assert access.thread_id == 7
    assert access.thread["user_id"] == "account-a"
    lookup.assert_called_once_with(7)


def test_spoofed_user_header_cannot_override_account_principal(monkeypatch):
    monkeypatch.setattr(dependencies, "is_private_preview", lambda: True)
    monkeypatch.setattr(
        dependencies,
        "require_preview_principal",
        lambda _request: SimpleNamespace(email="account-b"),
    )
    request = Request({"type": "http", "headers": []})
    scope = dependencies.get_request_user_scope(
        request=request,
        x_user_id="account-a",
    )
    assert scope.account_id == "account-b"
    with pytest.raises(HTTPException) as denied:
        require_thread_read_access(
            7,
            scope,
            thread_lookup=lambda _: {"id": 7, "user_id": "account-a"},
        )
    assert denied.value.status_code == 403


def test_unknown_thread_fails_closed():
    with pytest.raises(HTTPException) as denied:
        require_thread_read_access(
            404, _account("account-a"), thread_lookup=lambda _: None
        )
    assert denied.value.status_code == 404


def test_single_user_local_thread_semantics_remain_available():
    scope = RequestUserScope(user_id="local", multi_user_enabled=False)
    access = require_thread_read_access(
        7, scope, thread_lookup=lambda _: {"id": 7, "user_id": "historical-user"}
    )
    assert access.thread_id == 7


def test_room_owner_reads_backing_thread_with_existing_room_scope():
    session = _RoomSession()
    access = require_thread_read_access(
        None, _account("account-a"), session=session, room_id="room-a"
    )
    assert access.thread_id == 7
    assert access.room is session.room


def test_unrelated_account_cannot_read_room_thread():
    with pytest.raises(HTTPException) as denied:
        require_thread_read_access(
            7, _account("account-b"), session=_RoomSession(), room_id="room-a"
        )
    assert denied.value.status_code == 404


def test_active_guest_reads_only_its_room_thread_without_becoming_owner(monkeypatch):
    session = _RoomSession()
    principal = _guest(monkeypatch)
    access = require_thread_read_access(7, principal, session=session)
    assert access.room is session.room
    assert access.participant is session.participant
    assert access.room.owner_account_id == "account-a"
    assert principal.participant_id != access.room.owner_account_id


@pytest.mark.parametrize(
    "principal_room,principal_participant,thread_id",
    [
        ("room-a", "guest-a", 8),
        ("room-b", "guest-a", 7),
        ("room-a", "guest-b", 7),
    ],
)
def test_wrong_thread_room_or_participant_is_denied(
    monkeypatch, principal_room, principal_participant, thread_id
):
    principal = _guest(
        monkeypatch, room_id=principal_room, participant_id=principal_participant
    )
    with pytest.raises(HTTPException) as denied:
        require_thread_read_access(thread_id, principal, session=_RoomSession())
    assert denied.value.status_code == 401


@pytest.mark.parametrize(
    "room_status,participant_state,invite_status,invite_expires_at",
    [
        ("closed", "active", "accepted", None),
        ("active", "removed", "accepted", None),
        ("active", "active", "revoked", None),
        (
            "active",
            "active",
            "accepted",
            datetime.now(timezone.utc) - timedelta(minutes=1),
        ),
    ],
)
def test_guest_lifecycle_denials_are_preserved(
    monkeypatch, room_status, participant_state, invite_status, invite_expires_at
):
    principal = _guest(monkeypatch)
    session = _RoomSession(
        room_status=room_status,
        participant_state=participant_state,
        invite_status=invite_status,
        invite_expires_at=invite_expires_at,
    )
    with pytest.raises(HTTPException) as denied:
        require_thread_read_access(7, principal, session=session)
    assert denied.value.status_code == 401


def test_account_session_cannot_become_guest_principal(monkeypatch):
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "inert-thread-access-test-secret")
    account_token, _ = issue_session_token(subject="account-a")
    with pytest.raises(HTTPException) as denied:
        decode_principal(account_token)
    assert denied.value.status_code == 401
