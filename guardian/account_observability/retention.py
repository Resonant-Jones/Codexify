"""Deterministic bounded cleanup for account-observability retention."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, exists, select, update
from sqlalchemy.orm import Session

from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityPresenceSession,
)

from .tokens import (
    GUEST_LINEAGE_RETENTION_DAYS,
    PRESENCE_IDLE_EXPIRY_SECONDS,
    PRESENCE_ROW_RETENTION_DAYS,
)

CLEANUP_BATCH_SIZE = 500


@dataclass(frozen=True)
class CleanupReceipt:
    execution_timestamp: datetime
    cutoff_presence_30d: datetime
    cutoff_idle_30m: datetime
    expired_session_count: int
    deleted_presence_count: int
    cutoff_guest_lineage_90d: datetime
    deleted_guest_count: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "execution_timestamp": self.execution_timestamp.isoformat(),
            "cutoff_presence_30d": self.cutoff_presence_30d.isoformat(),
            "cutoff_idle_30m": self.cutoff_idle_30m.isoformat(),
            "cutoff_guest_lineage_90d": self.cutoff_guest_lineage_90d.isoformat(),
            "expired_session_count": self.expired_session_count,
            "deleted_presence_count": self.deleted_presence_count,
            "deleted_guest_count": self.deleted_guest_count,
        }


def _utc_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _expire_idle_sessions(
    session: Session, cutoff: datetime, now: datetime
) -> int:
    result = session.execute(
        update(AccountObservabilityPresenceSession)
        .where(
            AccountObservabilityPresenceSession.ended_at.is_(None),
            AccountObservabilityPresenceSession.last_seen_at < cutoff,
        )
        .values(ended_at=now, updated_at=now)
    )
    return int(result.rowcount or 0)


def _delete_old_presence_rows(session: Session, cutoff: datetime) -> int:
    total = 0
    while True:
        ids = list(
            session.scalars(
                select(AccountObservabilityPresenceSession.id)
                .where(AccountObservabilityPresenceSession.created_at < cutoff)
                .order_by(AccountObservabilityPresenceSession.created_at)
                .limit(CLEANUP_BATCH_SIZE)
            ).all()
        )
        if not ids:
            return total
        result = session.execute(
            delete(AccountObservabilityPresenceSession).where(
                AccountObservabilityPresenceSession.id.in_(ids)
            )
        )
        total += int(result.rowcount or 0)
        session.flush()
        if len(ids) < CLEANUP_BATCH_SIZE:
            return total


def _delete_old_unconverted_guests(session: Session, cutoff: datetime) -> int:
    total = 0
    referenced = exists(
        select(AccountObservabilityAccountMetadata.user_id).where(
            AccountObservabilityAccountMetadata.prior_guest_id
            == AccountObservabilityGuestIdentity.id
        )
    )
    while True:
        ids = list(
            session.scalars(
                select(AccountObservabilityGuestIdentity.id)
                .where(
                    AccountObservabilityGuestIdentity.created_at < cutoff,
                    AccountObservabilityGuestIdentity.converted_at.is_(None),
                    ~referenced,
                )
                .order_by(AccountObservabilityGuestIdentity.created_at)
                .limit(CLEANUP_BATCH_SIZE)
            ).all()
        )
        if not ids:
            return total
        result = session.execute(
            delete(AccountObservabilityGuestIdentity).where(
                AccountObservabilityGuestIdentity.id.in_(ids)
            )
        )
        total += int(result.rowcount or 0)
        session.flush()
        if len(ids) < CLEANUP_BATCH_SIZE:
            return total


def run_cleanup(
    session: Session, *, now: datetime | None = None
) -> CleanupReceipt:
    """Expire idle leases, then apply bounded row and guest retention."""

    current = _utc_now(now)
    idle_cutoff = current - timedelta(seconds=PRESENCE_IDLE_EXPIRY_SECONDS)
    presence_cutoff = current - timedelta(days=PRESENCE_ROW_RETENTION_DAYS)
    guest_cutoff = current - timedelta(days=GUEST_LINEAGE_RETENTION_DAYS)
    expired = _expire_idle_sessions(session, idle_cutoff, current)
    deleted_presence = _delete_old_presence_rows(session, presence_cutoff)
    deleted_guests = _delete_old_unconverted_guests(session, guest_cutoff)
    return CleanupReceipt(
        execution_timestamp=current,
        cutoff_presence_30d=presence_cutoff,
        cutoff_idle_30m=idle_cutoff,
        cutoff_guest_lineage_90d=guest_cutoff,
        expired_session_count=expired,
        deleted_presence_count=deleted_presence,
        deleted_guest_count=deleted_guests,
    )


__all__ = ["CLEANUP_BATCH_SIZE", "CleanupReceipt", "run_cleanup"]
