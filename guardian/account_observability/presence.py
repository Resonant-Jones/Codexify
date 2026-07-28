"""Guardian-owned, content-free foreground presence leases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityPresenceSession,
    User,
)

from .tokens import PRESENCE_ACTIVE_WINDOW_SECONDS, PRESENCE_IDLE_EXPIRY_SECONDS


class HeartbeatError(ValueError):
    """The heartbeat subject or operation is invalid."""


class SubjectResolutionError(HeartbeatError):
    """The trusted request context does not resolve to one subject."""


@dataclass(frozen=True)
class HeartbeatResult:
    """Internal heartbeat result; persistence IDs are not serialized by routes."""

    presence_session_id: str
    subject_kind: str
    subject_id: str
    is_new: bool
    server_time: datetime
    active_window_seconds: int = PRESENCE_ACTIVE_WINDOW_SECONDS
    idle_expiry_seconds: int = PRESENCE_IDLE_EXPIRY_SECONDS

    @property
    def active(self) -> bool:
        return True


def _utc_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _idle_cutoff(now: datetime) -> datetime:
    return now - timedelta(seconds=PRESENCE_IDLE_EXPIRY_SECONDS)


def _resolve_account(session: Session, user_id: str) -> User:
    normalized = str(user_id or "").strip()
    if not normalized:
        raise SubjectResolutionError(
            "authenticated account identity is required"
        )
    account = session.get(User, normalized)
    if account is None:
        raise SubjectResolutionError("authenticated account not found")
    return account


def _resolve_guest(
    session: Session, guest_id: str
) -> AccountObservabilityGuestIdentity:
    normalized = str(guest_id or "").strip()
    if not normalized:
        raise SubjectResolutionError(
            "valid server-issued guest identity is required"
        )
    guest = session.scalar(
        select(AccountObservabilityGuestIdentity)
        .where(
            AccountObservabilityGuestIdentity.id == normalized,
            AccountObservabilityGuestIdentity.deleted_at.is_(None),
        )
        .with_for_update()
    )
    if guest is None:
        raise SubjectResolutionError("guest identity not found or deleted")
    return guest


def _active_row(
    session: Session, *, user_id: str | None, guest_id: str | None
) -> AccountObservabilityPresenceSession | None:
    query = select(AccountObservabilityPresenceSession).where(
        AccountObservabilityPresenceSession.ended_at.is_(None)
    )
    if user_id is not None:
        query = query.where(
            AccountObservabilityPresenceSession.user_id == user_id
        )
    else:
        query = query.where(
            AccountObservabilityPresenceSession.guest_id == guest_id
        )
    return session.scalar(
        query.order_by(
            AccountObservabilityPresenceSession.last_seen_at.desc(),
            AccountObservabilityPresenceSession.started_at.desc(),
        ).with_for_update()
    )


def _coalesce_presence(
    session: Session,
    *,
    user_id: str | None,
    guest_id: str | None,
    invite_id: str | None,
    now: datetime,
) -> tuple[AccountObservabilityPresenceSession, bool]:
    row = _active_row(session, user_id=user_id, guest_id=guest_id)
    if row is not None:
        last_seen = _utc_now(row.last_seen_at)
        if last_seen >= _idle_cutoff(now):
            row.last_seen_at = now
            row.updated_at = now
            return row, False
        row.ended_at = now
        row.updated_at = now

    row = AccountObservabilityPresenceSession(
        id=str(uuid4()),
        user_id=user_id,
        guest_id=guest_id,
        invite_id=invite_id,
        started_at=now,
        last_seen_at=now,
        ended_at=None,
        country_code=None,
        region_code=None,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.flush()
    return row, True


def record_heartbeat(
    session: Session,
    *,
    user_id: str | None = None,
    guest_id: str | None = None,
    now: datetime | None = None,
) -> HeartbeatResult:
    """Record exactly one explicit foreground heartbeat."""

    account_supplied = bool(str(user_id or "").strip())
    guest_supplied = bool(str(guest_id or "").strip())
    if account_supplied == guest_supplied:
        raise SubjectResolutionError(
            "exactly one authenticated account or guest identity is required"
        )

    current = _utc_now(now)
    account = _resolve_account(session, user_id) if account_supplied else None
    guest = _resolve_guest(session, guest_id) if guest_supplied else None
    account_id = account.id if account is not None else None
    guest_identity = guest.id if guest is not None else None
    row, is_new = _coalesce_presence(
        session,
        user_id=account_id,
        guest_id=guest_identity,
        invite_id=guest.first_invite_id if guest is not None else None,
        now=current,
    )

    if account is not None:
        metadata = session.get(AccountObservabilityAccountMetadata, account.id)
        if metadata is not None:
            metadata.last_seen_at = current
            metadata.updated_at = current

    return HeartbeatResult(
        presence_session_id=row.id,
        subject_kind="account" if account is not None else "guest",
        subject_id=account_id or guest_identity or "",
        is_new=is_new,
        server_time=current,
    )


def _end_presence(
    session: Session,
    *,
    user_id: str | None = None,
    guest_id: str | None = None,
    now: datetime | None = None,
) -> int:
    current = _utc_now(now)
    query = update(AccountObservabilityPresenceSession).where(
        AccountObservabilityPresenceSession.ended_at.is_(None)
    )
    if user_id is not None:
        query = query.where(
            AccountObservabilityPresenceSession.user_id == user_id
        )
    else:
        query = query.where(
            AccountObservabilityPresenceSession.guest_id == guest_id
        )
    result = session.execute(query.values(ended_at=current, updated_at=current))
    return int(result.rowcount or 0)


def end_account_presence(
    session: Session, user_id: str, *, now: datetime | None = None
) -> int:
    """Best-effort logout hook; lease expiry remains authoritative."""

    return _end_presence(session, user_id=str(user_id or "").strip(), now=now)


def end_guest_presence(
    session: Session, guest_id: str, *, now: datetime | None = None
) -> int:
    """Best-effort guest reset hook; invalid identities cannot heartbeat."""

    return _end_presence(session, guest_id=str(guest_id or "").strip(), now=now)


__all__ = [
    "HeartbeatError",
    "HeartbeatResult",
    "SubjectResolutionError",
    "end_account_presence",
    "end_guest_presence",
    "record_heartbeat",
]
