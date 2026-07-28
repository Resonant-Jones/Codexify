"""Fail-closed validation for bounded Hosted Room completion context."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterator

from sqlalchemy import func, select

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

HOSTED_ROOM_VALIDATION_FAILURE_CODES = frozenset(
    {
        "hosted_room_not_found",
        "hosted_room_inactive",
        "hosted_room_thread_mismatch",
        "hosted_room_source_message_invalid",
        "hosted_room_actor_invalid",
        "hosted_room_actor_inactive",
        "hosted_room_requester_invalid",
        "hosted_room_authority_revoked",
    }
)


@dataclass(frozen=True)
class ValidatedHostedRoomCompletionContext:
    """Validated identities needed to persist a Guardian completion."""

    room_id: str
    thread_id: int
    source_message_id: int
    actor_participant_id: str
    actor_source: str
    actor_ref: str
    sender_display_name_snapshot: str
    requester_authority: str
    requester_participant_id: str | None


class HostedRoomCompletionValidationError(RuntimeError):
    """Bounded, safe failure emitted when invocation authority is invalid."""

    def __init__(self, code: str) -> None:
        if code not in HOSTED_ROOM_VALIDATION_FAILURE_CODES:
            code = "hosted_room_source_message_invalid"
        self.code = code
        self.metadata = {
            "error": "hosted_room_invocation_invalid",
            "failure_code": code,
            "message": "Hosted Room completion authority validation failed",
        }
        super().__init__(self.metadata["message"])


@contextmanager
def _session_scope(chatlog_db: Any) -> Iterator[Any]:
    """Use the existing database session convention without owning its setup."""

    get_session = getattr(chatlog_db, "get_session", None)
    if callable(get_session):
        session = get_session()
        try:
            yield session
        finally:
            session.close()
        return

    sa_session = getattr(chatlog_db, "_sa_session", None)
    if callable(sa_session):
        with sa_session() as session:
            yield session
        return

    raise RuntimeError("chatlog database does not expose a session boundary")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise HostedRoomCompletionValidationError(code)


def _invite_is_current(
    invite: HostedRoomInvite | None,
    *,
    room_id: str,
) -> bool:
    if invite is None or _clean(invite.room_id) != room_id:
        return False
    if _clean(invite.status) != "accepted":
        return False
    expires_at = invite.expires_at
    if expires_at is None:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc)


def _validate_source_message(
    session: Any,
    *,
    room: HostedRoom,
    source_message_id: int,
    actor_participant_id: str,
) -> ChatMessage:
    source = session.get(ChatMessage, source_message_id)
    if source is None:
        raise HostedRoomCompletionValidationError(
            "hosted_room_source_message_invalid"
        )

    _require(
        source.thread_id == room.backing_thread_id
        and _clean(source.role).lower() == "user"
        and _clean(source.content),
        "hosted_room_source_message_invalid",
    )
    participant_id = _clean(source.hosted_room_participant_id)
    snapshot = _clean(source.sender_display_name_snapshot)
    _require(
        participant_id and snapshot,
        "hosted_room_source_message_invalid",
    )
    _require(
        participant_id != actor_participant_id,
        "hosted_room_source_message_invalid",
    )

    participant = session.get(HostedRoomParticipant, participant_id)
    _require(
        participant is not None
        and _clean(participant.room_id) == _clean(room.id)
        and _clean(participant.kind) == "human"
        and _clean(participant.role) in {"owner", "member"}
        and _clean(participant.state) == "active",
        "hosted_room_source_message_invalid",
    )
    if _clean(participant.role) == "member":
        _require(
            _invite_is_current(
                session.get(HostedRoomInvite, participant.invitation_id),
                room_id=_clean(room.id),
            ),
            "hosted_room_source_message_invalid",
        )
    return source


def _validate_actor(
    session: Any,
    *,
    room: HostedRoom,
    actor_participant_id: str,
    actor_source: str,
    actor_ref: str,
) -> HostedRoomParticipant:
    actor = session.get(HostedRoomParticipant, actor_participant_id)
    _require(
        actor is not None
        and _clean(actor.room_id) == _clean(room.id)
        and _clean(actor.kind) == "agent"
        and _clean(actor.role) == "agent",
        "hosted_room_actor_invalid",
    )
    if _clean(actor.state) != "active":
        raise HostedRoomCompletionValidationError(
            "hosted_room_actor_inactive"
        )
    _require(
        _clean(actor.actor_source) == actor_source == RESIDENT_SOURCE
        and _clean(actor.actor_ref) == actor_ref == GUARDIAN_REF
        and actor.bound_account_id is None
        and actor.invitation_id is None
        and _clean(actor.display_name) == GUARDIAN_DISPLAY,
        "hosted_room_actor_invalid",
    )

    active_guardian_count = session.scalar(
        select(func.count(HostedRoomParticipant.id)).where(
            HostedRoomParticipant.room_id == room.id,
            HostedRoomParticipant.kind == "agent",
            HostedRoomParticipant.role == "agent",
            HostedRoomParticipant.state == "active",
            HostedRoomParticipant.actor_source == RESIDENT_SOURCE,
            HostedRoomParticipant.actor_ref == GUARDIAN_REF,
        )
    )
    _require(
        int(active_guardian_count or 0) == 1,
        "hosted_room_actor_invalid",
    )
    return actor


def _validate_requester(
    session: Any,
    *,
    room: HostedRoom,
    requester_authority: str,
    requester_participant_id: str | None,
    actor_participant_id: str,
) -> None:
    if requester_authority == "owner":
        _require(
            requester_participant_id is None,
            "hosted_room_requester_invalid",
        )
        return

    if requester_authority != "guest" or not requester_participant_id:
        raise HostedRoomCompletionValidationError(
            "hosted_room_requester_invalid"
        )
    _require(
        requester_participant_id != actor_participant_id,
        "hosted_room_requester_invalid",
    )
    requester = session.get(
        HostedRoomParticipant,
        requester_participant_id,
    )
    _require(
        requester is not None
        and _clean(requester.room_id) == _clean(room.id)
        and _clean(requester.kind) == "human"
        and _clean(requester.role) == "member"
        and _clean(requester.state) == "active",
        "hosted_room_requester_invalid",
    )
    if not _invite_is_current(
        session.get(HostedRoomInvite, requester.invitation_id),
        room_id=_clean(room.id),
    ):
        raise HostedRoomCompletionValidationError(
            "hosted_room_authority_revoked"
        )


def validate_hosted_room_completion_context(
    chatlog_db: Any,
    task: Any,
) -> ValidatedHostedRoomCompletionContext:
    """Validate current room, message, actor, and requester state.

    The same function is called before model execution and again immediately
    before assistant persistence, so mutable room authority is not trusted from
    an earlier read.
    """

    metadata = getattr(task, "hosted_room_invocation", None)
    if metadata is None:
        raise ValueError("Hosted Room completion metadata is required")

    room_id = _clean(metadata.room_id)
    source_message_id = metadata.source_message_id
    actor_participant_id = _clean(metadata.actor_participant_id)
    actor_source = _clean(metadata.actor_source)
    actor_ref = _clean(metadata.actor_ref)
    requester_authority = _clean(metadata.requester_authority)
    requester_participant_id = (
        _clean(metadata.requester_participant_id)
        or None
    )

    with _session_scope(chatlog_db) as session:
        room = session.get(HostedRoom, room_id)
        if room is None:
            raise HostedRoomCompletionValidationError(
                "hosted_room_not_found"
            )
        if _clean(room.status) != "active":
            raise HostedRoomCompletionValidationError(
                "hosted_room_inactive"
            )
        if room.backing_thread_id != task.thread_id:
            raise HostedRoomCompletionValidationError(
                "hosted_room_thread_mismatch"
            )
        if session.get(ChatThread, room.backing_thread_id) is None:
            raise HostedRoomCompletionValidationError(
                "hosted_room_thread_mismatch"
            )

        source = _validate_source_message(
            session,
            room=room,
            source_message_id=source_message_id,
            actor_participant_id=actor_participant_id,
        )
        _validate_actor(
            session,
            room=room,
            actor_participant_id=actor_participant_id,
            actor_source=actor_source,
            actor_ref=actor_ref,
        )
        _validate_requester(
            session,
            room=room,
            requester_authority=requester_authority,
            requester_participant_id=requester_participant_id,
            actor_participant_id=actor_participant_id,
        )

        return ValidatedHostedRoomCompletionContext(
            room_id=room_id,
            thread_id=task.thread_id,
            source_message_id=source.id,
            actor_participant_id=actor_participant_id,
            actor_source=actor_source,
            actor_ref=actor_ref,
            sender_display_name_snapshot=GUARDIAN_DISPLAY,
            requester_authority=requester_authority,
            requester_participant_id=requester_participant_id,
        )


__all__ = [
    "HOSTED_ROOM_VALIDATION_FAILURE_CODES",
    "HostedRoomCompletionValidationError",
    "ValidatedHostedRoomCompletionContext",
    "validate_hosted_room_completion_context",
]
