"""Shared Hosted Room message persistence and serialization.

Provides narrow helpers for reading and writing canonical human
ChatMessage rows from Hosted Room participant contexts.  Does not
contain authentication logic — that remains owned by the owner and
guest route modules.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select

from guardian.db.models import (
    ChatMessage,
    ChatThread,
    HostedRoom,
    HostedRoomParticipant,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

_MAX_CONTENT_LENGTH = 32_000
_DEFAULT_PAGE_LIMIT = 100
_MAX_PAGE_LIMIT = 200


# ── Exceptions ───────────────────────────────────────────────────────────


def _room_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"error": "not_found", "message": "Room not found"},
    )


def _room_not_active() -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={"error": "room_not_active", "message": "Room is not active"},
    )


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"error": "unauthorized", "message": "Authentication required"},
    )


# ── Consistency validation ──────────────────────────────────────────────


def validate_room_for_messaging(session, room_id: str) -> HostedRoom:
    """Load an active room for messaging."""
    room = session.get(HostedRoom, room_id)
    if room is None:
        raise _room_not_found()
    if room.status != "active":
        raise _room_not_active()
    return room


def resolve_owner_participant(
    session, room: HostedRoom, account_id: str
) -> HostedRoomParticipant:
    """Resolve the single active owner participant for a room.

    Fails closed if the owner participant is missing, removed,
    duplicated, or belongs to another room.
    """
    participants = (
        session.query(HostedRoomParticipant)
        .where(
            HostedRoomParticipant.room_id == room.id,
            HostedRoomParticipant.kind == "human",
            HostedRoomParticipant.role == "owner",
            HostedRoomParticipant.state == "active",
        )
        .all()
    )

    if len(participants) == 0:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "owner_participant_missing",
                "message": "Room owner participant is missing or removed",
            },
        )
    if len(participants) > 1:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "owner_participant_duplicated",
                "message": "Room has multiple active owner participants",
            },
        )

    owner = participants[0]
    if owner.bound_account_id != account_id:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "owner_participant_mismatch",
                "message": "Room owner participant does not match authenticated account",
            },
        )

    return owner


def validate_guest_messaging_access(
    session,
    room_id: str,
    participant_id: str,
    invitation_id: str,
) -> tuple[HostedRoom, HostedRoomParticipant]:
    """Validate that a guest principal can message in this room.

    Returns (room, participant) on success, raises on failure.
    All failures return 401 to avoid leaking lifecycle details.
    """
    room = session.get(HostedRoom, room_id)
    if room is None:
        raise _unauthorized()
    if room.status != "active":
        raise _unauthorized()

    participant = session.get(HostedRoomParticipant, participant_id)
    if participant is None:
        raise _unauthorized()
    if participant.room_id != room.id:
        raise _unauthorized()
    if participant.state != "active":
        raise _unauthorized()
    if participant.kind != "human":
        raise _unauthorized()
    if participant.role != "member":
        raise _unauthorized()
    if participant.invitation_id != invitation_id:
        raise _unauthorized()

    # Validate invitation lifecycle
    from guardian.db.models import HostedRoomInvite
    invite = session.get(HostedRoomInvite, invitation_id)
    if invite is None:
        raise _unauthorized()
    if invite.status != "accepted":
        raise _unauthorized()
    if invite.expires_at is not None:
        now = datetime.now(timezone.utc)
        inv_exp = invite.expires_at
        if inv_exp.tzinfo is None:
            inv_exp = inv_exp.replace(tzinfo=timezone.utc)
        if inv_exp < now:
            raise _unauthorized()

    return room, participant


# ── Content validation ──────────────────────────────────────────────────


def validate_content(raw: Any) -> str:
    """Validate and normalize message content."""
    if raw is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_content",
                "message": "Content is required",
            },
        )
    if not isinstance(raw, str):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_content",
                "message": "Content must be a string",
            },
        )

    content = raw.strip()
    if not content:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_content",
                "message": "Content must not be blank",
            },
        )

    if len(content) > _MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "content_too_long",
                "message": f"Content must not exceed {_MAX_CONTENT_LENGTH} characters",
            },
        )

    return content


# ── Message listing ─────────────────────────────────────────────────────


def list_room_messages(
    session,
    thread_id: int,
    *,
    after_id: int | None = None,
    limit: int = _DEFAULT_PAGE_LIMIT,
) -> list[ChatMessage]:
    """List messages for a room's backing thread with cursor-based pagination.

    When after_id is supplied, returns messages with id > after_id in
    ascending order, up to limit.  When absent, returns the latest
    limit messages and serializes them in ascending order.
    """
    effective_limit = max(1, min(limit, _MAX_PAGE_LIMIT))

    if after_id is not None:
        rows = (
            session.query(ChatMessage)
            .where(
                ChatMessage.thread_id == thread_id,
                ChatMessage.id > after_id,
            )
            .order_by(ChatMessage.id.asc())
            .limit(effective_limit)
            .all()
        )
    else:
        # Fetch the latest N messages, then sort ascending
        rows = (
            session.query(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.id.desc())
            .limit(effective_limit)
            .all()
        )
        rows.reverse()

    return rows


# ── Message creation ────────────────────────────────────────────────────


def create_human_room_message(
    session,
    *,
    thread_id: int,
    user_id: str,
    content: str,
    participant: HostedRoomParticipant,
) -> ChatMessage:
    """Persist one canonical human room message via raw INSERT.

    Uses raw table insert with explicit ID to avoid SQLite autoincrement
    issues with BigInteger PK columns.
    """
    now = datetime.now(timezone.utc)

    # Resolve next ID manually
    last = session.execute(
        select(ChatMessage.id).order_by(ChatMessage.id.desc()).limit(1)
    ).scalar()
    next_id = (last or 0) + 1

    session.execute(
        ChatMessage.__table__.insert().values(
            id=next_id,
            thread_id=thread_id,
            user_id=user_id,
            role="user",
            content=content,
            kind="chat",
            hosted_room_participant_id=participant.id,
            sender_display_name_snapshot=participant.display_name,
            extra_meta="{}",
        )
    )
    session.flush()

    # Return the ORM object for serialization
    msg = session.get(ChatMessage, next_id)
    if msg is None:
        raise RuntimeError("Failed to retrieve created message")
    return msg


# ── Serialization ───────────────────────────────────────────────────────


def _iso(ts: Any) -> str | None:
    if ts is None:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    return str(ts)


def serialize_message(msg: ChatMessage) -> dict[str, Any]:
    """Serialize one ChatMessage into the Hosted Room projection.

    Never exposes account IDs, invitation IDs, token hashes,
    extra_meta internals, or request/task IDs.
    """
    sender = None
    if msg.hosted_room_participant_id is not None:
        sender = {
            "participant_id": msg.hosted_room_participant_id,
            "display_name": msg.sender_display_name_snapshot,
        }
        # Participant kind/role are NOT loaded from the relationship
        # (lazy='raise') to avoid accidental eager loading.  Future
        # enrichment can join-load the participant explicitly when needed.

    return {
        "id": msg.id,
        "role": msg.role,
        "content": msg.content,
        "created_at": _iso(msg.created_at) or "",
        "sender": sender,
    }


def serialize_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [serialize_message(m) for m in messages]
