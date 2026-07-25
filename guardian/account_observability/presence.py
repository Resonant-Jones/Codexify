"""Foreground presence heartbeat service for accounts and guests.

This module implements Slice 3 of the admin account observability contract:
canonical foreground presence heartbeat and deterministic retention cleanup.

Invariants:
- Only an explicit foreground heartbeat creates or refreshes presence.
- Ordinary API traffic must not update presence.
- Message sends, model generations, document access, and request logs
  must not imply presence.
- Heartbeat payloads carry no analytics dimensions.
- Raw and hashed IPs are never persisted.
- Exactly one account or guest subject per presence record.
- Client-supplied account/guest IDs must never override trusted server context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityPresenceSession,
)

from .tokens import (
    PRESENCE_ACTIVE_WINDOW_SECONDS,
    PRESENCE_HEARTBEAT_INTERVAL_SECONDS,
    PRESENCE_IDLE_EXPIRY_SECONDS,
)

logger = logging.getLogger(__name__)


class HeartbeatError(ValueError):
    """A heartbeat request is invalid or cannot be processed."""


class SubjectResolutionError(HeartbeatError):
    """The request subject cannot be resolved or is ambiguous."""


@dataclass(frozen=True)
class HeartbeatResult:
    presence_session_id: str
    subject_kind: str  # "account" or "guest"
    subject_id: str
    is_new: bool
    server_time: datetime
    active_window_seconds: int
    idle_expiry_seconds: int

    @property
    def active(self) -> bool:
        return True


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_account_subject(
    session: Session, user_id: str
) -> tuple[str, str | None]:
    """Resolve an authenticated account as a presence subject.

    Returns (subject_id, None) for accounts.
    The user_id must come from trusted server context (auth dependency).
    """
    if not user_id or not isinstance(user_id, str) or not user_id.strip():
        raise SubjectResolutionError("authenticated account identity is required")
    normalized = user_id.strip()
    return normalized, None


def _resolve_guest_subject(
    session: Session, guest_id: str
) -> tuple[str, str | None]:
    """Resolve a server-issued guest identity as a presence subject.

    The guest_id must come from trusted server context (cookie resolution).
    Client-supplied guest IDs are rejected.
    """
    if not guest_id or not isinstance(guest_id, str) or not guest_id.strip():
        raise SubjectResolutionError("valid server-issued guest identity is required")
    normalized = guest_id.strip()

    # Verify the guest identity exists and is not deleted
    guest = session.scalar(
        select(AccountObservabilityGuestIdentity).where(
            AccountObservabilityGuestIdentity.guest_id == normalized,
            AccountObservabilityGuestIdentity.deleted_at.is_(None),
        )
    )
    if guest is None:
        raise SubjectResolutionError("guest identity not found or has been deleted")
    return normalized, guest.first_invite_id


def _coalesce_account_presence(
    session: Session,
    user_id: str,
    now: datetime,
) -> tuple[AccountObservabilityPresenceSession, bool]:
    """Find or create an active presence session for an account.

    Returns (session_row, is_new).
    An existing active session is refreshed; an expired session triggers
    creation of a new session.
    """
    idle_cutoff = datetime.fromtimestamp(
        now.timestamp() - PRESENCE_IDLE_EXPIRY_SECONDS, tz=timezone.utc
    )

    # Look for an existing active session for this account
    existing = session.scalar(
        select(AccountObservabilityPresenceSession)
        .where(
            AccountObservabilityPresenceSession.user_id == user_id,
            AccountObservabilityPresenceSession.ended_at.is_(None),
        )
        .order_by(
            AccountObservabilityPresenceSession.last_seen_at.desc(),
            AccountObservabilityPresenceSession.started_at.desc(),
        )
        .with_for_update()
    )

    if existing is not None:
        # Normalize last_seen_at for comparison (SQLite strips tz)
        existing_last = existing.last_seen_at
        if existing_last.tzinfo is None:
            existing_last = existing_last.replace(tzinfo=timezone.utc)
        if existing_last >= idle_cutoff:
            # Refresh existing active session
            existing.last_seen_at = now
            existing.updated_at = now
            return existing, False

    # Create a new presence session
    new_session = AccountObservabilityPresenceSession(
        presence_session_id=str(uuid4()),
        user_id=user_id,
        guest_id=None,
        invite_id=None,
        started_at=now,
        last_seen_at=now,
        ended_at=None,
        country_code=None,
        region_code=None,
    )
    session.add(new_session)
    session.flush()
    return new_session, True


def _coalesce_guest_presence(
    session: Session,
    guest_id: str,
    invite_id: str | None,
    now: datetime,
) -> tuple[AccountObservabilityPresenceSession, bool]:
    """Find or create an active presence session for a guest."""
    idle_cutoff = datetime.fromtimestamp(
        now.timestamp() - PRESENCE_IDLE_EXPIRY_SECONDS, tz=timezone.utc
    )

    existing = session.scalar(
        select(AccountObservabilityPresenceSession)
        .where(
            AccountObservabilityPresenceSession.guest_id == guest_id,
            AccountObservabilityPresenceSession.ended_at.is_(None),
        )
        .order_by(
            AccountObservabilityPresenceSession.last_seen_at.desc(),
            AccountObservabilityPresenceSession.started_at.desc(),
        )
        .with_for_update()
    )

    if existing is not None:
        existing_last = existing.last_seen_at
        if existing_last.tzinfo is None:
            existing_last = existing_last.replace(tzinfo=timezone.utc)
        if existing_last >= idle_cutoff:
            existing.last_seen_at = now
            existing.updated_at = now
            return existing, False

    new_session = AccountObservabilityPresenceSession(
        presence_session_id=str(uuid4()),
        user_id=None,
        guest_id=guest_id,
        invite_id=invite_id,
        started_at=now,
        last_seen_at=now,
        ended_at=None,
        country_code=None,
        region_code=None,
    )
    session.add(new_session)
    session.flush()
    return new_session, True


def _update_account_last_seen(
    session: Session,
    user_id: str,
    now: datetime,
) -> None:
    """Update account last_seen_at through canonical presence only."""
    metadata = session.get(AccountObservabilityAccountMetadata, user_id)
    if metadata is not None:
        metadata.last_seen_at = now
        metadata.updated_at = now


def record_heartbeat(
    session: Session,
    *,
    user_id: str | None = None,
    guest_id: str | None = None,
    now: datetime | None = None,
) -> HeartbeatResult:
    """Record one canonical foreground heartbeat.

    Exactly one of user_id or guest_id must be provided.
    Both values must come from trusted server context (auth/cookie deps).
    Client-supplied identity overrides are never accepted here.

    Args:
        session: Active database session.
        user_id: Trusted authenticated account identity (from auth dep).
        guest_id: Trusted server-issued guest identity (from cookie resolution).
        now: Server UTC time (defaults to utcnow).

    Returns:
        HeartbeatResult with session identity and timing metadata.

    Raises:
        SubjectResolutionError: If the subject is absent, ambiguous, or invalid.
    """
    current = _utc_now() if now is None else now
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    has_account = user_id is not None and str(user_id).strip()
    has_guest = guest_id is not None and str(guest_id).strip()

    if not has_account and not has_guest:
        raise SubjectResolutionError("at least one subject must be provided")
    if has_account and has_guest:
        raise SubjectResolutionError(
            "ambiguous subject: exactly one of account or guest identity required"
        )

    if has_account:
        resolved_id, invite_id = _resolve_account_subject(
            session, str(user_id)
        )
        presence_row, is_new = _coalesce_account_presence(
            session, resolved_id, current
        )
        _update_account_last_seen(session, resolved_id, current)
        subject_kind = "account"
        subject_id = resolved_id
    else:
        resolved_id, invite_id = _resolve_guest_subject(
            session, str(guest_id)
        )
        presence_row, is_new = _coalesce_guest_presence(
            session, resolved_id, invite_id, current
        )
        subject_kind = "guest"
        subject_id = resolved_id

    logger.debug(
        "[presence] heartbeat recorded kind=%s subject=%s is_new=%s",
        subject_kind,
        subject_id,
        is_new,
    )

    return HeartbeatResult(
        presence_session_id=presence_row.presence_session_id,
        subject_kind=subject_kind,
        subject_id=subject_id,
        is_new=is_new,
        server_time=current,
        active_window_seconds=PRESENCE_ACTIVE_WINDOW_SECONDS,
        idle_expiry_seconds=PRESENCE_IDLE_EXPIRY_SECONDS,
    )


def end_account_presence(
    session: Session,
    user_id: str,
    *,
    now: datetime | None = None,
) -> int:
    """Best-effort end all active presence sessions for an account.

    Called on logout or session ending. Missed close events remain safe
    because idle expiry is authoritative.

    Returns the number of sessions ended.
    """
    current = _utc_now() if now is None else now
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    result = session.execute(
        update(AccountObservabilityPresenceSession)
        .where(
            AccountObservabilityPresenceSession.user_id == user_id,
            AccountObservabilityPresenceSession.ended_at.is_(None),
        )
        .values(ended_at=current, updated_at=current)
    )
    count = result.rowcount
    if count:
        logger.debug(
            "[presence] ended %s account presence session(s) for %s",
            count,
            user_id,
        )
    return count


def end_guest_presence(
    session: Session,
    guest_id: str,
    *,
    now: datetime | None = None,
) -> int:
    """Best-effort end all active presence sessions for a guest.

    Called on guest reset/deletion. Returns the number of sessions ended.
    """
    current = _utc_now() if now is None else now
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    result = session.execute(
        update(AccountObservabilityPresenceSession)
        .where(
            AccountObservabilityPresenceSession.guest_id == guest_id,
            AccountObservabilityPresenceSession.ended_at.is_(None),
        )
        .values(ended_at=current, updated_at=current)
    )
    count = result.rowcount
    if count:
        logger.debug(
            "[presence] ended %s guest presence session(s) for %s",
            count,
            guest_id,
        )
    return count


__all__ = [
    "HeartbeatError",
    "HeartbeatResult",
    "SubjectResolutionError",
    "end_account_presence",
    "end_guest_presence",
    "record_heartbeat",
]
