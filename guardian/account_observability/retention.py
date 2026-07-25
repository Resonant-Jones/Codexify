"""Deterministic retention cleanup for presence sessions and guest lineage.

This module implements the Slice 3 cleanup contract:
- Expire idle sessions (30 minutes without heartbeat).
- Delete presence rows older than 30 days.
- Delete eligible guest identities older than 90 days (only when safe).
- Preserve converted-account attribution.
- Never delete invite definitions.
- Idempotent and batch-safe.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AccountObservabilityPresenceSession,
)

from .tokens import (
    GUEST_LINEAGE_RETENTION_DAYS,
    PRESENCE_IDLE_EXPIRY_SECONDS,
    PRESENCE_ROW_RETENTION_DAYS,
)

logger = logging.getLogger(__name__)

CLEANUP_BATCH_SIZE = 500


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CleanupReceipt:
    execution_timestamp: datetime
    cutoff_presence_30d: datetime
    cutoff_idle_30m: datetime
    cutoff_guest_lineage_90d: datetime | None = None
    expired_session_count: int = 0
    deleted_presence_count: int = 0
    deleted_guest_count: int | None = None
    deferred_guest_count: int | None = None
    deferred_guest_reason: str | None = None
    dry_run: bool = False

    def as_dict(self) -> dict:
        return {
            "execution_timestamp": self.execution_timestamp.isoformat(),
            "cutoff_presence_30d": self.cutoff_presence_30d.isoformat(),
            "cutoff_idle_30m": self.cutoff_idle_30m.isoformat(),
            "cutoff_guest_lineage_90d": (
                self.cutoff_guest_lineage_90d.isoformat()
                if self.cutoff_guest_lineage_90d
                else None
            ),
            "expired_session_count": self.expired_session_count,
            "deleted_presence_count": self.deleted_presence_count,
            "deleted_guest_count": self.deleted_guest_count,
            "deferred_guest_count": self.deferred_guest_count,
            "deferred_guest_reason": self.deferred_guest_reason,
            "dry_run": self.dry_run,
        }


def _expire_idle_sessions(
    session: Session,
    idle_cutoff: datetime,
    now: datetime,
    *,
    dry_run: bool = False,
) -> int:
    """End sessions that have not received a heartbeat within the idle window."""
    if dry_run:
        result = session.execute(
            select(AccountObservabilityPresenceSession).where(
                AccountObservabilityPresenceSession.ended_at.is_(None),
                AccountObservabilityPresenceSession.last_seen_at < idle_cutoff,
            )
        )
        return len(result.scalars().all())

    result = session.execute(
        update(AccountObservabilityPresenceSession)
        .where(
            AccountObservabilityPresenceSession.ended_at.is_(None),
            AccountObservabilityPresenceSession.last_seen_at < idle_cutoff,
        )
        .values(ended_at=now, updated_at=now)
    )
    return result.rowcount


def _delete_old_presence_rows(
    session: Session,
    presence_cutoff: datetime,
    *,
    dry_run: bool = False,
) -> int:
    """Delete presence rows older than the retention window."""
    total = 0
    while True:
        if dry_run:
            batch = session.execute(
                select(
                    AccountObservabilityPresenceSession.presence_session_id
                ).where(
                    AccountObservabilityPresenceSession.created_at < presence_cutoff
                ).limit(CLEANUP_BATCH_SIZE)
            )
            count = len(batch.scalars().all())
            total += count
            if count < CLEANUP_BATCH_SIZE:
                break
        else:
            result = session.execute(
                delete(AccountObservabilityPresenceSession)
                .where(
                    AccountObservabilityPresenceSession.created_at < presence_cutoff
                )
                .execution_options(synchronize_session="fetch")
            )
            total += result.rowcount
            if result.rowcount < CLEANUP_BATCH_SIZE:
                break
            session.flush()
    return total


def _guest_lineage_deletion_is_safe(
    session: Session,
    guest: AccountObservabilityGuestIdentity,
) -> bool:
    """A guest is safe to delete only when no account-metadata row references it.

    If the guest has been converted (converted_at is set) and an
    AccountObservabilityAccountMetadata row references its guest_id as
    prior_guest_id, deletion would lose attribution evidence.
    """
    if guest.converted_at is not None:
        # Check if any account metadata still references this guest
        ref = session.scalar(
            select(AccountObservabilityAccountMetadata).where(
                AccountObservabilityAccountMetadata.prior_guest_id == guest.guest_id,
            )
        )
        if ref is not None:
            return False
    return True


def _delete_eligible_guest_lineage(
    session: Session,
    guest_cutoff: datetime,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Delete guest identities older than the retention window.

    Returns (deleted_count, deferred_count).
    Guest identities with converted-account references are deferred.
    """
    eligible_query = select(AccountObservabilityGuestIdentity).where(
        AccountObservabilityGuestIdentity.created_at < guest_cutoff,
        AccountObservabilityGuestIdentity.deleted_at.is_(None),
    )

    all_old = session.execute(eligible_query).scalars().all()
    safe_to_delete: list[AccountObservabilityGuestIdentity] = []
    deferred: list[AccountObservabilityGuestIdentity] = []

    for guest in all_old:
        if _guest_lineage_deletion_is_safe(session, guest):
            safe_to_delete.append(guest)
        else:
            deferred.append(guest)

    if dry_run:
        return len(safe_to_delete), len(deferred)

    for guest in safe_to_delete:
        # Soft-delete: set deleted_at, don't physically remove the row
        # (preserves FK integrity for any remaining references)
        guest.deleted_at = datetime.now(timezone.utc)
        guest.updated_at = datetime.now(timezone.utc)

    session.flush()
    return len(safe_to_delete), len(deferred)


def run_cleanup(
    session: Session,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> CleanupReceipt:
    """Execute deterministic retention cleanup.

    Steps:
    1. End presence sessions idle beyond 30 minutes.
    2. Delete presence rows older than 30 days.
    3. Delete eligible guest lineage older than 90 days (safe only).

    Args:
        session: Active database session.
        now: Server UTC time (defaults to utcnow).
        dry_run: When True, count affected rows without mutating.

    Returns:
        CleanupReceipt with counts and cutoff timestamps.
    """
    current = _utc_now() if now is None else now
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    idle_cutoff = datetime.fromtimestamp(
        current.timestamp() - PRESENCE_IDLE_EXPIRY_SECONDS, tz=timezone.utc
    )
    presence_cutoff = datetime.fromtimestamp(
        current.timestamp() - (PRESENCE_ROW_RETENTION_DAYS * 86400),
        tz=timezone.utc,
    )
    guest_cutoff = datetime.fromtimestamp(
        current.timestamp() - (GUEST_LINEAGE_RETENTION_DAYS * 86400),
        tz=timezone.utc,
    )

    logger.info(
        "[retention] cleanup starting dry_run=%s idle_cutoff=%s presence_cutoff=%s guest_cutoff=%s",
        dry_run,
        idle_cutoff.isoformat(),
        presence_cutoff.isoformat(),
        guest_cutoff.isoformat(),
    )

    expired = _expire_idle_sessions(session, idle_cutoff, current, dry_run=dry_run)
    deleted_presence = _delete_old_presence_rows(
        session, presence_cutoff, dry_run=dry_run
    )

    # Guest lineage deletion: we may have ambiguous cases where a converted
    # guest has active account-metadata references. We delete only safe rows
    # and record the deferred count explicitly.
    deleted_guests, deferred_guests = _delete_eligible_guest_lineage(
        session, guest_cutoff, dry_run=dry_run
    )

    deferred_reason = None
    if deferred_guests > 0:
        deferred_reason = (
            "guest_lineage_deletion_deferred: "
            f"{deferred_guests} guest(s) have converted-account "
            "attribution references that must be preserved"
        )

    receipt = CleanupReceipt(
        execution_timestamp=current,
        cutoff_presence_30d=presence_cutoff,
        cutoff_idle_30m=idle_cutoff,
        cutoff_guest_lineage_90d=guest_cutoff,
        expired_session_count=expired,
        deleted_presence_count=deleted_presence,
        deleted_guest_count=deleted_guests,
        deferred_guest_count=deferred_guests,
        deferred_guest_reason=deferred_reason,
        dry_run=dry_run,
    )

    logger.info(
        "[retention] cleanup complete expired=%s deleted_presence=%s "
        "deleted_guests=%s deferred_guests=%s dry_run=%s",
        expired,
        deleted_presence,
        deleted_guests,
        deferred_guests,
        dry_run,
    )

    return receipt


__all__ = ["CleanupReceipt", "run_cleanup"]
