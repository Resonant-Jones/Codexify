"""Hosted Room owner lifecycle API.

Authenticated account-owner routes for creating, listing, inspecting,
updating, and closing Hosted Rooms backed by canonical chat threads.

All endpoints require the normal authenticated Codexify account context.
Ownership is derived exclusively from the authenticated account — the
request body cannot supply or override the owner identity.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, func

from guardian.core.db import load_guardian_db_from_env
from guardian.core.default_project import (
    canonicalize_default_project,
    resolve_project_id_or_default,
)
from guardian.core.dependencies import RequestUserScope, get_request_user_scope
from guardian.db.models import (
    ChatThread,
    HostedRoom,
    HostedRoomInvite,
    HostedRoomParticipant,
    User,
    UserProfile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hosted-rooms", tags=["Hosted Rooms"])

# ── V1 enabled-agent domain ──────────────────────────────────────────────
_V1_AGENT_IDS: frozenset[str] = frozenset({"guardian", "luna"})

# ── Title constraints ─────────────────────────────────────────────────────
_MAX_TITLE_LENGTH = 512  # matches hosted_rooms.title column

# ── Display name constraints ──────────────────────────────────────────────
_MAX_DISPLAY_NAME_LENGTH = 255  # matches hosted_room_invites.intended_display_name

# ── Invitation constraints ────────────────────────────────────────────────
_MAX_INVITATION_LIFETIME_DAYS = 30
_INVITATION_TOKEN_ENTROPY_BYTES = 32  # 256 bits
_MAX_TOKEN_GENERATION_ATTEMPTS = 5

# ── Slug generation ───────────────────────────────────────────────────────
_MAX_SLUG_GENERATION_ATTEMPTS = 8
_SLUG_SUFFIX_BYTES = 4  # 6-char base64url suffix


def _normalize_title(raw: Any) -> str:
    """Trim and validate a room title."""
    if raw is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_title", "message": "Title is required"},
        )
    text = str(raw).strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_title", "message": "Title must not be empty"},
        )
    if len(text) > _MAX_TITLE_LENGTH:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_title",
                "message": f"Title must not exceed {_MAX_TITLE_LENGTH} characters",
            },
        )
    return text


def _normalize_enabled_agent_ids(raw: Any) -> list[str]:
    """Validate and deduplicate enabled agent IDs."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_agent_ids",
                "message": "enabled_agent_ids must be a list of strings",
            },
        )
    seen: set[str] = set()
    result: list[str] = []
    for item in raw:
        agent_id = str(item).strip().lower()
        if not agent_id:
            continue
        if agent_id not in _V1_AGENT_IDS:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_agent_id",
                    "message": f"Unknown agent: {agent_id}",
                    "valid_agents": sorted(_V1_AGENT_IDS),
                },
            )
        if agent_id not in seen:
            seen.add(agent_id)
            result.append(agent_id)
    result.sort()
    return result


def _generate_slug(title: str) -> str:
    """Generate a URL-safe unique slug from a title."""
    # Build base from title: lowercase, replace non-alphanumeric with hyphens,
    # collapse multiple hyphens, strip leading/trailing hyphens.
    import re

    base = title.lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = base.strip("-")
    if len(base) > 80:
        base = base[:80].rstrip("-")
    if not base:
        base = "room"
    suffix = secrets.token_urlsafe(_SLUG_SUFFIX_BYTES).rstrip("=")
    return f"{base}-{suffix}"


def _generate_unique_slug(session, title: str) -> str:
    """Generate a slug that is unique in the hosted_rooms table."""
    for _attempt in range(_MAX_SLUG_GENERATION_ATTEMPTS):
        candidate = _generate_slug(title)
        existing = session.scalar(
            select(HostedRoom).where(HostedRoom.slug == candidate)
        )
        if existing is None:
            return candidate
    raise HTTPException(
        status_code=409,
        detail={
            "error": "slug_collision",
            "message": "Unable to generate a unique room slug after multiple attempts",
        },
    )


# ── Invitation token helpers ────────────────────────────────────────────

def _generate_invitation_token() -> str:
    """Generate a high-entropy URL-safe invitation token."""
    return secrets.token_urlsafe(_INVITATION_TOKEN_ENTROPY_BYTES)


def _hash_token(token: str) -> str:
    """Derive a deterministic SHA-256 verifier from a high-entropy token."""
    return hashlib.sha256(token.encode()).hexdigest()


def _normalize_expiry(raw: Any) -> datetime | None:
    """Validate and normalize an optional expiry timestamp."""
    if raw is None:
        return None

    # Accept ISO-8601 strings
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            # Try parsing as ISO datetime
            ts = datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_expiry",
                    "message": "expires_at must be a valid ISO-8601 datetime string",
                },
            )
    elif isinstance(raw, datetime):
        ts = raw
    else:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_expiry",
                "message": "expires_at must be an ISO-8601 datetime string or null",
            },
        )

    # Must be timezone-aware
    if ts.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_expiry",
                "message": "expires_at must include a timezone offset (UTC)",
            },
        )

    now = datetime.now(timezone.utc)

    # Must be in the future
    if ts <= now:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "expiry_in_past",
                "message": "expires_at must be in the future",
            },
        )

    # Must not exceed maximum lifetime
    max_expiry = now + timedelta(days=_MAX_INVITATION_LIFETIME_DAYS)
    if ts > max_expiry:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "expiry_too_far",
                "message": f"Invitation expiry must not exceed {_MAX_INVITATION_LIFETIME_DAYS} days from now",
            },
        )

    return ts


def _normalize_display_name(raw: Any) -> str:
    """Trim and validate an invitation display name."""
    if raw is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_display_name",
                "message": "intended_display_name is required",
            },
        )
    text = str(raw).strip()
    if not text:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_display_name",
                "message": "intended_display_name must not be empty",
            },
        )
    if len(text) > _MAX_DISPLAY_NAME_LENGTH:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_display_name",
                "message": f"intended_display_name must not exceed {_MAX_DISPLAY_NAME_LENGTH} characters",
            },
        )
    return text


def _resolve_owner_display_name(session, account_id: str) -> str:
    """Resolve a safe display name for the owner participant."""
    # Try UserProfile first
    profile = session.scalar(
        select(UserProfile).where(UserProfile.user_id == account_id)
    )
    if profile is not None and profile.display_name:
        return profile.display_name.strip()

    # Fall back to username
    user = session.get(User, account_id)
    if user is not None and user.username:
        return user.username.strip()

    # Neutral fallback
    return "Room Owner"


def _require_db():
    db = load_guardian_db_from_env()
    if db is None:
        raise HTTPException(
            status_code=503,
            detail="Hosted Room database unavailable",
        )
    return db


def _resolve_account_id(scope: RequestUserScope) -> str:
    owner_id = str(scope.user_id or "").strip()
    if not owner_id:
        raise HTTPException(status_code=401, detail="Missing authenticated user")
    return owner_id


def _resolve_default_project_id(db) -> int | None:
    """Resolve the canonical default project for thread creation."""
    try:
        return db.ensure_default_project()
    except Exception:
        return None


# ── Timestamp helpers ─────────────────────────────────────────────────────

def _iso(ts: datetime | None) -> str | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.isoformat()


# ── Response models ───────────────────────────────────────────────────────

class RoomSummary(BaseModel):
    id: str
    slug: str
    title: str
    status: str
    backing_thread_id: int
    enabled_agent_ids: list[str]
    active_participant_count: int
    pending_invitation_count: int
    created_at: str
    updated_at: str
    closed_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class ParticipantSummary(BaseModel):
    id: str
    display_name: str
    kind: str
    role: str
    state: str
    joined_at: str
    removed_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class InvitationSummary(BaseModel):
    id: str
    intended_display_name: str
    status: str
    expires_at: str | None = None
    accepted_at: str | None = None
    revoked_at: str | None = None
    created_at: str
    updated_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class RoomDetail(BaseModel):
    id: str
    slug: str
    title: str
    status: str
    backing_thread_id: int
    enabled_agent_ids: list[str]
    active_participant_count: int
    pending_invitation_count: int
    created_at: str
    updated_at: str
    closed_at: str | None = None
    participants: list[ParticipantSummary]
    invitations: list[InvitationSummary]

    model_config = ConfigDict(extra="forbid")


# ── Request models ────────────────────────────────────────────────────────

class CreateRoomRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=_MAX_TITLE_LENGTH)
    enabled_agent_ids: list[str] | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", mode="before")
    @classmethod
    def _trim_title(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Title is required")
        return str(value).strip()


class UpdateRoomRequest(BaseModel):
    title: str | None = Field(default=None, max_length=_MAX_TITLE_LENGTH)
    enabled_agent_ids: list[str] | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", mode="before")
    @classmethod
    def _trim_title(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip()


# ── Invitation request/response models ───────────────────────────────────

class CreateInviteRequest(BaseModel):
    intended_display_name: str = Field(..., max_length=_MAX_DISPLAY_NAME_LENGTH)
    expires_at: str | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @field_validator("intended_display_name", mode="before")
    @classmethod
    def _trim_display_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("intended_display_name is required")
        return str(value).strip()


class InvitationMetadata(BaseModel):
    """Reusable invitation metadata — never contains token or hash."""
    id: str
    room_id: str
    intended_display_name: str
    status: str
    expires_at: str | None = None
    accepted_at: str | None = None
    revoked_at: str | None = None
    created_at: str
    updated_at: str | None = None

    model_config = ConfigDict(extra="forbid")


class InviteCreationResponse(BaseModel):
    """One-time invitation creation response with the plaintext credential."""
    invitation: InvitationMetadata
    invitation_token: str
    join_path: str

    model_config = ConfigDict(extra="forbid")


class InviteRevocationResponse(BaseModel):
    """Invitation revocation response — metadata only, no credential."""
    invitation: InvitationMetadata

    model_config = ConfigDict(extra="forbid")


# ── Summary helpers ───────────────────────────────────────────────────────

def _room_summary(room: HostedRoom) -> RoomSummary:
    active_participants = sum(
        1 for p in room.participants if p.state == "active"
    )
    pending_invites = sum(
        1 for inv in room.invitations if inv.status == "pending"
    )
    return RoomSummary(
        id=room.id,
        slug=room.slug,
        title=room.title,
        status=room.status,
        backing_thread_id=room.backing_thread_id,
        enabled_agent_ids=sorted(room.enabled_agent_ids),
        active_participant_count=active_participants,
        pending_invitation_count=pending_invites,
        created_at=_iso(room.created_at) or "",
        updated_at=_iso(room.updated_at) or "",
        closed_at=_iso(room.closed_at),
    )


def _room_detail(room: HostedRoom) -> RoomDetail:
    participants = [
        ParticipantSummary(
            id=p.id,
            display_name=p.display_name,
            kind=p.kind,
            role=p.role,
            state=p.state,
            joined_at=_iso(p.joined_at) or "",
            removed_at=_iso(p.removed_at),
        )
        for p in room.participants
    ]
    invitations = [
        InvitationSummary(
            id=inv.id,
            intended_display_name=inv.intended_display_name,
            status=inv.status,
            expires_at=_iso(inv.expires_at),
            accepted_at=_iso(inv.accepted_at),
            revoked_at=_iso(inv.revoked_at),
            created_at=_iso(inv.created_at) or "",
            updated_at=_iso(inv.updated_at),
        )
        for inv in room.invitations
    ]
    summary = _room_summary(room)
    return RoomDetail(
        **summary.model_dump(),
        participants=participants,
        invitations=invitations,
    )


def _require_room_ownership(
    session,
    room_id: str,
    account_id: str,
) -> HostedRoom:
    """Fetch a room and verify it belongs to the authenticated account."""
    room = session.get(HostedRoom, room_id)
    if room is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Room not found"},
        )
    if room.owner_account_id != account_id:
        # Use 404 to avoid leaking room existence
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Room not found"},
        )
    return room


def _invite_metadata(invite: HostedRoomInvite) -> InvitationMetadata:
    """Build invitation metadata — never includes token or hash."""
    return InvitationMetadata(
        id=invite.id,
        room_id=invite.room_id,
        intended_display_name=invite.intended_display_name,
        status=invite.status,
        expires_at=_iso(invite.expires_at),
        accepted_at=_iso(invite.accepted_at),
        revoked_at=_iso(invite.revoked_at),
        created_at=_iso(invite.created_at) or "",
        updated_at=_iso(invite.updated_at),
    )


def _require_invite_in_room(
    session,
    room_id: str,
    invite_id: str,
    account_id: str,
) -> HostedRoomInvite:
    """Fetch an invitation scoped to an owned room."""
    _require_room_ownership(session, room_id, account_id)
    invite = session.get(HostedRoomInvite, invite_id)
    if invite is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Invitation not found"},
        )
    if invite.room_id != room_id:
        # Invite exists but not for this room — don't leak that info
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Invitation not found"},
        )
    return invite


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("", response_model=RoomDetail, status_code=201)
def create_room(
    body: CreateRoomRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _resolve_account_id(request_user_scope)
    title = _normalize_title(body.title)
    enabled_agent_ids = _normalize_enabled_agent_ids(body.enabled_agent_ids)
    display_name = "Room Owner"  # resolved inside session

    db = _require_db()
    default_project_id = _resolve_default_project_id(db)

    with db.get_session() as session:
        try:
            # Verify user exists
            user = session.get(User, account_id)
            if user is None:
                raise HTTPException(
                    status_code=404,
                    detail={"error": "user_not_found", "message": "Authenticated user not found"},
                )

            # Resolve display name
            display_name = _resolve_owner_display_name(session, account_id)

            # 1. Create the canonical chat thread
            thread = ChatThread(
                user_id=account_id,
                title=title,
                summary="",
                project_id=default_project_id,
            )
            session.add(thread)
            session.flush()  # assign thread.id

            # 2. Generate a unique slug
            slug = _generate_unique_slug(session, title)

            # 3. Create the Hosted Room
            room_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            room = HostedRoom(
                id=room_id,
                owner_account_id=account_id,
                backing_thread_id=thread.id,
                title=title,
                slug=slug,
                status="active",
                enabled_agent_ids=enabled_agent_ids,
                created_at=now,
                updated_at=now,
                closed_at=None,
            )
            session.add(room)
            session.flush()

            # 4. Create the owner participant
            participant = HostedRoomParticipant(
                id=str(uuid.uuid4()),
                room_id=room_id,
                invitation_id=None,
                bound_account_id=account_id,
                display_name=display_name,
                kind="human",
                role="owner",
                state="active",
                joined_at=now,
                removed_at=None,
                created_at=now,
            )
            session.add(participant)

            session.commit()

            # Refresh to load relationships
            session.refresh(room)

            return _room_detail(room).model_dump(mode="json")

        except HTTPException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            logger.exception("Failed to create hosted room")
            raise HTTPException(
                status_code=500,
                detail={"error": "creation_failed", "message": "Failed to create room"},
            )


@router.get("", response_model=list[RoomSummary])
def list_rooms(
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> list[dict[str, Any]]:
    account_id = _resolve_account_id(request_user_scope)
    db = _require_db()
    with db.get_session() as session:
        rooms = (
            session.query(HostedRoom)
            .where(HostedRoom.owner_account_id == account_id)
            .order_by(HostedRoom.created_at.desc())
            .all()
        )
        return [_room_summary(r).model_dump(mode="json") for r in rooms]


@router.get("/{room_id}", response_model=RoomDetail)
def get_room(
    room_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _resolve_account_id(request_user_scope)
    db = _require_db()
    with db.get_session() as session:
        room = _require_room_ownership(session, room_id, account_id)
        return _room_detail(room).model_dump(mode="json")


@router.patch("/{room_id}", response_model=RoomDetail)
def update_room(
    room_id: str,
    body: UpdateRoomRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _resolve_account_id(request_user_scope)

    # Validate title if provided
    if body.title is not None:
        _normalize_title(body.title)

    # Validate agent IDs if provided
    if body.enabled_agent_ids is not None:
        _normalize_enabled_agent_ids(body.enabled_agent_ids)

    db = _require_db()
    with db.get_session() as session:
        room = _require_room_ownership(session, room_id, account_id)

        if room.status == "closed":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "room_closed",
                    "message": "Cannot update a closed room",
                },
            )

        changed = False
        if body.title is not None and body.title.strip() != room.title:
            room.title = _normalize_title(body.title)
            changed = True

        if body.enabled_agent_ids is not None:
            normalized = _normalize_enabled_agent_ids(body.enabled_agent_ids)
            if normalized != sorted(room.enabled_agent_ids):
                room.enabled_agent_ids = normalized
                changed = True

        if changed:
            room.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(room)
        else:
            # No-op: still refresh relationships for consistent response
            session.refresh(room)

        return _room_detail(room).model_dump(mode="json")


@router.post("/{room_id}/close", response_model=RoomDetail)
def close_room(
    room_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _resolve_account_id(request_user_scope)
    db = _require_db()
    with db.get_session() as session:
        room = _require_room_ownership(session, room_id, account_id)

        if room.status == "closed":
            # Idempotent: return existing closed state; do not overwrite closed_at
            session.refresh(room)
            return _room_detail(room).model_dump(mode="json")

        now = datetime.now(timezone.utc)
        room.status = "closed"
        room.closed_at = now
        room.updated_at = now
        session.commit()
        session.refresh(room)
        return _room_detail(room).model_dump(mode="json")


# ── Invitation endpoints ────────────────────────────────────────────────

@router.post("/{room_id}/invites", response_model=InviteCreationResponse, status_code=201)
def create_invite(
    room_id: str,
    body: CreateInviteRequest = Body(...),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _resolve_account_id(request_user_scope)
    display_name = _normalize_display_name(body.intended_display_name)
    expires_at = _normalize_expiry(body.expires_at)

    db = _require_db()
    with db.get_session() as session:
        try:
            room = _require_room_ownership(session, room_id, account_id)

            if room.status == "closed":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "room_closed",
                        "message": "Cannot create invitations for a closed room",
                    },
                )

            # Generate token and hash with collision retry
            token = ""
            token_hash = ""
            for _attempt in range(_MAX_TOKEN_GENERATION_ATTEMPTS):
                token = _generate_invitation_token()
                token_hash = _hash_token(token)
                existing = session.scalar(
                    select(HostedRoomInvite).where(
                        HostedRoomInvite.token_hash == token_hash
                    )
                )
                if existing is None:
                    break
            else:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "token_collision",
                        "message": "Unable to generate a unique invitation token",
                    },
                )

            # Persist invitation
            now = datetime.now(timezone.utc)
            invite_id = str(uuid.uuid4())
            invite = HostedRoomInvite(
                id=invite_id,
                room_id=room_id,
                intended_display_name=display_name,
                token_hash=token_hash,
                status="pending",
                expires_at=expires_at,
                accepted_at=None,
                revoked_at=None,
                expired_at=None,
                created_at=now,
                updated_at=now,
            )
            session.add(invite)
            session.commit()
            session.refresh(invite)

            metadata = _invite_metadata(invite)
            return {
                "invitation": metadata.model_dump(mode="json"),
                "invitation_token": token,
                "join_path": f"/join/{token}",
            }

        except HTTPException:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            logger.exception("Failed to create invitation")
            raise HTTPException(
                status_code=500,
                detail={"error": "creation_failed", "message": "Failed to create invitation"},
            )


@router.get("/{room_id}/invites", response_model=list[InvitationMetadata])
def list_invites(
    room_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> list[dict[str, Any]]:
    account_id = _resolve_account_id(request_user_scope)
    db = _require_db()
    with db.get_session() as session:
        _require_room_ownership(session, room_id, account_id)
        invites = (
            session.query(HostedRoomInvite)
            .where(HostedRoomInvite.room_id == room_id)
            .order_by(HostedRoomInvite.created_at.desc())
            .all()
        )
        return [_invite_metadata(inv).model_dump(mode="json") for inv in invites]


@router.post("/{room_id}/invites/{invite_id}/revoke", response_model=InviteRevocationResponse)
def revoke_invite(
    room_id: str,
    invite_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
) -> dict[str, Any]:
    account_id = _resolve_account_id(request_user_scope)
    db = _require_db()
    with db.get_session() as session:
        invite = _require_invite_in_room(session, room_id, invite_id, account_id)

        if invite.status == "revoked":
            # Idempotent: return existing revoked state; preserve original timestamp
            session.refresh(invite)
            return {
                "invitation": _invite_metadata(invite).model_dump(mode="json")
            }

        # Revocation is allowed for pending or accepted invites
        if invite.status not in ("pending", "accepted"):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "invalid_state",
                    "message": f"Cannot revoke an invitation with status '{invite.status}'",
                },
            )

        now = datetime.now(timezone.utc)
        invite.status = "revoked"
        invite.revoked_at = now
        invite.updated_at = now
        session.commit()
        session.refresh(invite)
        return {
            "invitation": _invite_metadata(invite).model_dump(mode="json")
        }
