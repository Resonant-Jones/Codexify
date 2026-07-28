"""Hosted Room guest entry and session routes.

Unauthenticated endpoints for invitation exchange, session inspection,
and logout.  These routes use only the Hosted Room guest-session cookie
— normal account authentication is neither required nor accepted as a
substitute.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from guardian.core.db import load_guardian_db_from_env
from guardian.core.hosted_room_session import (
    HostedRoomGuestPrincipal,
    clear_session_cookie,
    decode_guest_session_token,
    decode_principal,
    extract_session_token_from_request,
    issue_guest_session_token,
    set_session_cookie,
)
from guardian.db.models import (
    HostedRoom,
    HostedRoomInvite,
    HostedRoomParticipant,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Hosted Room Guest"])

# ── Constants ────────────────────────────────────────────────────────────

_MAX_TOKEN_LENGTH = 256  # generous upper bound for URL-safe tokens
# Allowed characters in URL-safe base64 tokens
_TOKEN_CHAR_CLASS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
)


# ── Request / Response models ────────────────────────────────────────────


class ExchangeRequest(BaseModel):
    """Request body for invitation exchange."""

    invitation_token: str = Field(..., min_length=1, max_length=_MAX_TOKEN_LENGTH)

    model_config = ConfigDict(extra="forbid")

    @field_validator("invitation_token", mode="before")
    @classmethod
    def _validate_token_chars(cls, value: Any) -> str:
        token = str(value or "").strip()
        if not token:
            raise ValueError("invitation_token must not be empty")
        if len(token) > _MAX_TOKEN_LENGTH:
            raise ValueError(f"invitation_token must not exceed {_MAX_TOKEN_LENGTH} characters")
        # Reject unexpected characters
        invalid = set(token) - _TOKEN_CHAR_CLASS
        if invalid:
            raise ValueError("invitation_token contains invalid characters")
        return token


class RoomMetadata(BaseModel):
    """Safe room metadata for guest responses."""

    id: str
    slug: str
    title: str
    enabled_agent_ids: list[str]
    status: str

    model_config = ConfigDict(extra="forbid")


class GuestParticipantMetadata(BaseModel):
    """Safe participant metadata for guest responses."""

    id: str
    display_name: str
    kind: str
    role: str
    state: str
    joined_at: str

    model_config = ConfigDict(extra="forbid")


class SessionMetadata(BaseModel):
    """Session expiry information."""

    expires_at: str

    model_config = ConfigDict(extra="forbid")


class ExchangeResponse(BaseModel):
    """Successful invitation exchange response."""

    room: RoomMetadata
    participant: GuestParticipantMetadata
    session: SessionMetadata

    model_config = ConfigDict(extra="forbid")


class SessionInspectResponse(BaseModel):
    """Session inspection response."""

    room: RoomMetadata
    participant: GuestParticipantMetadata
    session: SessionMetadata

    model_config = ConfigDict(extra="forbid")


class LogoutResponse(BaseModel):
    """Logout confirmation."""

    ok: bool = True

    model_config = ConfigDict(extra="forbid")


# ── Helpers ──────────────────────────────────────────────────────────────


def _require_db():
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Hosted Room database unavailable",
        )
    return db


def _iso(ts: datetime | None) -> str | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.isoformat()


def _room_metadata(room: HostedRoom) -> RoomMetadata:
    return RoomMetadata(
        id=room.id,
        slug=room.slug,
        title=room.title,
        enabled_agent_ids=sorted(room.enabled_agent_ids),
        status=room.status,
    )


def _participant_metadata(participant: HostedRoomParticipant) -> GuestParticipantMetadata:
    return GuestParticipantMetadata(
        id=participant.id,
        display_name=participant.display_name,
        kind=participant.kind,
        role=participant.role,
        state=participant.state,
        joined_at=_iso(participant.joined_at) or "",
    )


def _session_metadata(expires_at_epoch: int) -> SessionMetadata:
    exp_dt = datetime.fromtimestamp(expires_at_epoch, tz=timezone.utc)
    return SessionMetadata(expires_at=exp_dt.isoformat())


def _invalid_invite() -> HTTPException:
    """Uniform non-disclosing error for all unavailable invitation cases."""
    return HTTPException(
        status_code=404,
        detail={
            "error": "invalid_invitation",
            "message": "Invitation is invalid or unavailable",
        },
    )


def _unauthorized() -> HTTPException:
    """Uniform error for invalid or missing session."""
    return HTTPException(
        status_code=401,
        detail={"error": "unauthorized", "message": "Authentication required"},
    )


def _validate_session_lifecycle(
    session,
    principal: HostedRoomGuestPrincipal,
    room: HostedRoom,
    invite: HostedRoomInvite,
    participant: HostedRoomParticipant,
) -> None:
    """Revalidate room, invitation, and participant lifecycle truth.

    Every authorized request must call this so that revocation, removal,
    closure, and expiry invalidate access immediately.
    """
    # Room must be active
    if room.status != "active":
        raise HTTPException(
            status_code=401,
            detail={"error": "room_not_active", "message": "Room is not active"},
        )

    # Invitation must be accepted
    if invite.status != "accepted":
        raise HTTPException(
            status_code=401,
            detail={"error": "invitation_not_accepted", "message": "Session is no longer valid"},
        )

    # Invitation must not be expired
    if invite.expires_at is not None:
        now = datetime.now(timezone.utc)
        inv_exp = invite.expires_at
        if inv_exp.tzinfo is None:
            inv_exp = inv_exp.replace(tzinfo=timezone.utc)
        if inv_exp < now:
            raise HTTPException(
                status_code=401,
                detail={"error": "invitation_expired", "message": "Session is no longer valid"},
            )

    # Participant must be active
    if participant.state != "active":
        raise HTTPException(
            status_code=401,
            detail={"error": "participant_removed", "message": "Session is no longer valid"},
        )

    # Participant must match the principal's identifiers
    if participant.id != principal.participant_id:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )
    if participant.room_id != principal.room_id:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )
    if participant.invitation_id != principal.invitation_id:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )
    # Guest participants must be human members
    if participant.kind != "human" or participant.role != "member":
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_session", "message": "Invalid session"},
        )


# ── Exchange endpoint ────────────────────────────────────────────────────


@router.post("/api/hosted-room-invitations/exchange", response_model=ExchangeResponse)
def exchange_invitation(
    body: ExchangeRequest = Body(...),
    response: Response = None,  # injected by FastAPI
) -> dict[str, Any]:
    """Exchange a one-time invitation token for a guest session.

    On success, an HTTP-only session cookie is set and safe room/participant
    metadata is returned.  The invitation token is consumed and cannot be
    reused.
    """
    token = body.invitation_token  # already validated by Pydantic

    # Hash the supplied token to look up the invitation
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    db = _require_db()
    with db.get_session() as session:
        try:
            # Look up invitation by token hash (indexed, constant-time after retrieval)
            invite = session.scalar(
                select(HostedRoomInvite).where(
                    HostedRoomInvite.token_hash == token_hash
                )
            )
            if invite is None:
                raise _invalid_invite()

            # Must be pending
            if invite.status != "pending":
                raise _invalid_invite()

            # Must not be expired
            if invite.expires_at is not None:
                now = datetime.now(timezone.utc)
                inv_exp = invite.expires_at
                if inv_exp.tzinfo is None:
                    inv_exp = inv_exp.replace(tzinfo=timezone.utc)
                if inv_exp < now:
                    raise _invalid_invite()

            # Resolve the room
            room = session.get(HostedRoom, invite.room_id)
            if room is None:
                raise _invalid_invite()

            # Room must be active
            if room.status != "active":
                raise _invalid_invite()

            # ── Create participant + accept invitation atomically ───────
            now = datetime.now(timezone.utc)
            participant_id = str(uuid.uuid4())

            participant = HostedRoomParticipant(
                id=participant_id,
                room_id=room.id,
                invitation_id=invite.id,
                bound_account_id=None,
                display_name=invite.intended_display_name,
                kind="human",
                role="member",
                state="active",
                joined_at=now,
                removed_at=None,
                created_at=now,
            )
            session.add(participant)
            session.flush()

            # Mark invitation accepted
            invite.status = "accepted"
            invite.accepted_at = now
            invite.updated_at = now

            session.commit()
            session.refresh(room)
            session.refresh(invite)
            session.refresh(participant)

            # ── Issue session token ──────────────────────────────────
            signed_token, expires_at_epoch = issue_guest_session_token(
                room_id=room.id,
                room_slug=room.slug,
                participant_id=participant.id,
                invitation_id=invite.id,
                invitation_expires_at=invite.expires_at,
            )

            set_session_cookie(response, signed_token, expires_at_epoch)

            return {
                "room": _room_metadata(room).model_dump(mode="json"),
                "participant": _participant_metadata(participant).model_dump(mode="json"),
                "session": _session_metadata(expires_at_epoch).model_dump(mode="json"),
            }

        except HTTPException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            logger.exception("Failed to exchange invitation")
            raise HTTPException(
                status_code=500,
                detail={"error": "exchange_failed", "message": "Invitation exchange failed"},
            )


# ── Session inspection endpoint ──────────────────────────────────────────


@router.get("/api/hosted-room-session", response_model=SessionInspectResponse)
def inspect_session(request: Request) -> dict[str, Any]:
    """Return bounded room and participant metadata for a valid guest session."""
    token = extract_session_token_from_request(request)
    if not token:
        raise _unauthorized()

    principal = decode_principal(token)

    db = _require_db()
    with db.get_session() as session:
        # Resolve all three entities
        room = session.get(HostedRoom, principal.room_id)
        if room is None:
            raise _unauthorized()

        invite = session.get(HostedRoomInvite, principal.invitation_id)
        if invite is None:
            raise _unauthorized()

        participant = session.get(HostedRoomParticipant, principal.participant_id)
        if participant is None:
            raise _unauthorized()

        # Revalidate lifecycle truth
        _validate_session_lifecycle(session, principal, room, invite, participant)

        return {
            "room": _room_metadata(room).model_dump(mode="json"),
            "participant": _participant_metadata(participant).model_dump(mode="json"),
            "session": _session_metadata(principal.expires_at).model_dump(mode="json"),
        }


# ── Logout endpoint ──────────────────────────────────────────────────────


@router.post("/api/hosted-room-session/logout", response_model=LogoutResponse)
def logout(response: Response) -> dict[str, Any]:
    """Clear the Hosted Room session cookie.

    Does not delete the participant, revoke the invitation, close the room,
    or alter any transcript data.
    """
    clear_session_cookie(response)
    return {"ok": True}
