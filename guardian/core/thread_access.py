"""Read authorization for canonical chat threads.

Authentication belongs to the caller. Account scopes and decoded Hosted Room
guest principals remain separate credential types; this module checks their
current resource authority without consulting task or event transport state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope, get_single_user_id
from guardian.core.hosted_room_messages import validate_guest_messaging_access
from guardian.core.hosted_room_session import HostedRoomGuestPrincipal
from guardian.db.models import HostedRoom, HostedRoomParticipant


@dataclass(frozen=True)
class ThreadReadAccess:
    thread_id: int
    thread: Mapping[str, Any] | None = None
    room: HostedRoom | None = None
    participant: HostedRoomParticipant | None = None


def _room_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"error": "not_found", "message": "Room not found"},
    )


def _guest_unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"error": "unauthorized", "message": "Authentication required"},
    )


def require_thread_read_access(
    thread_id: int | None,
    principal: RequestUserScope | HostedRoomGuestPrincipal,
    *,
    thread_lookup: Callable[[int], Mapping[str, Any] | None] | None = None,
    thread: Mapping[str, Any] | None = None,
    session: Any | None = None,
    room_id: str | None = None,
) -> ThreadReadAccess:
    """Require current read authority for a thread and return its context.

    ``thread_lookup`` is the canonical chat-thread store used by ordinary chat.
    ``session`` is the canonical Hosted Room database session. ``room_id`` is
    supplied only by an owner room route that already names that room; a guest
    room identity always comes from the decoded, purpose-scoped principal.
    Room routes may pass ``None`` for ``thread_id`` and use the room's durable
    backing thread; task-scoped consumers pass their canonical thread ID.
    """
    if isinstance(principal, HostedRoomGuestPrincipal):
        if session is None:
            raise RuntimeError("Hosted Room read authorization requires a database session")
        room, participant = validate_guest_messaging_access(
            session,
            principal.room_id,
            principal.participant_id,
            principal.invitation_id,
        )
        if thread_id is not None and room.backing_thread_id != thread_id:
            raise _guest_unauthorized()
        return ThreadReadAccess(room.backing_thread_id, room=room, participant=participant)

    if not isinstance(principal, RequestUserScope):
        raise TypeError("Unsupported authenticated thread principal")

    if room_id is not None:
        if session is None:
            raise RuntimeError("Hosted Room read authorization requires a database session")
        room = session.get(HostedRoom, room_id)
        if room is None or (
            thread_id is not None and room.backing_thread_id != thread_id
        ):
            raise _room_not_found()
        # Preserve the owner room route's existing account identity and 404
        # existence-hiding behavior. Room lifecycle is checked by that route.
        account_id = str(principal.user_id or "").strip()
        if not account_id:
            raise HTTPException(status_code=401, detail="Missing authenticated user")
        if room.owner_account_id != account_id:
            raise _room_not_found()
        return ThreadReadAccess(room.backing_thread_id, room=room)

    if thread_id is None:
        raise ValueError("Ordinary thread read authorization requires a thread ID")
    thread_record = thread if thread is not None else (
        thread_lookup(thread_id) if thread_lookup is not None else None
    )
    if thread_record is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if principal.multi_user_enabled:
        account_id = str(principal.account_id or "").strip()
        if not account_id:
            account_id = str(principal.user_id or "").strip() or get_single_user_id()
        owner_id = str(thread_record.get("user_id") or "").strip()
        if owner_id != account_id:
            raise HTTPException(
                status_code=403,
                detail="Thread does not belong to the authenticated account",
            )
    return ThreadReadAccess(thread_id, thread=thread_record)
