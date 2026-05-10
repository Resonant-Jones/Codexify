"""Durable persistence helpers for worktree lease control-plane state.

This module is intentionally inert: it stores and updates lease metadata only.
It does not create branches/worktrees, mutate filesystems, execute workers, or
expose API routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from guardian.agents.worktree_leases import (
    WORKTREE_LEASE_ACTIVE_STATUSES,
    WorktreeLeaseContract,
    WorktreeLeaseValidationResult,
    is_active_lease_status,
    validate_lease_contract,
    validate_no_shared_mutable_worktree,
)
from guardian.db.models import CodingWorktreeLease

MAX_CLEANUP_ERROR_CHARS = 2048


class WorktreeLeaseStoreError(RuntimeError):
    """Base error for worktree lease store operations."""


class WorktreeLeaseNotFound(WorktreeLeaseStoreError):
    """Raised when a lease_id does not exist."""


class WorktreeLeaseConflict(WorktreeLeaseStoreError):
    """Raised when active lease uniqueness constraints are violated."""

    def __init__(self, *, field: str, value: str) -> None:
        super().__init__(f"active lease conflict on {field}: {value}")
        self.field = field
        self.value = value


class WorktreeLeaseValidationError(WorktreeLeaseStoreError):
    """Raised when lease contract validation fails."""

    def __init__(self, result: WorktreeLeaseValidationResult) -> None:
        message = result.reason or "invalid lease contract"
        super().__init__(message)
        self.reason = result.reason
        self.reason_code = result.reason_code


@dataclass
class WorktreeLeaseStore:
    """Postgres-backed store for lease lifecycle state."""

    db: Any

    def create_lease(
        self, lease: WorktreeLeaseContract
    ) -> WorktreeLeaseContract:
        validation = validate_lease_contract(lease)
        if not validation.ok:
            raise WorktreeLeaseValidationError(validation)

        with self.db.get_session() as session:
            if is_active_lease_status(lease.status):
                self._assert_no_active_conflict(session, lease)

            row = CodingWorktreeLease(
                lease_id=lease.lease_id,
                work_order_id=lease.work_order_id,
                run_id=lease.run_id,
                worker_id=lease.worker_id,
                base_ref=lease.base_ref,
                branch_name=lease.branch_name,
                worktree_path=lease.worktree_path,
                status=lease.status,
                created_at=lease.created_at,
                expires_at=lease.expires_at,
                preserve_on_failure=lease.preserve_on_failure,
                cleanup_policy=lease.cleanup_policy,
                last_heartbeat_at=lease.last_heartbeat_at,
                extra_meta=_extract_extra_meta(lease),
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise self._translate_integrity_error(exc, lease) from exc

            session.refresh(row)
            return self._row_to_contract(row)

    def get_lease(self, lease_id: str) -> WorktreeLeaseContract | None:
        with self.db.get_session() as session:
            row = (
                session.query(CodingWorktreeLease)
                .filter_by(lease_id=lease_id)
                .first()
            )
            if row is None:
                return None
            return self._row_to_contract(row)

    def list_leases_for_work_order(
        self, work_order_id: str
    ) -> list[WorktreeLeaseContract]:
        with self.db.get_session() as session:
            rows = (
                session.query(CodingWorktreeLease)
                .filter_by(work_order_id=work_order_id)
                .order_by(CodingWorktreeLease.created_at.asc())
                .all()
            )
            return [self._row_to_contract(row) for row in rows]

    def list_active_leases(self) -> list[WorktreeLeaseContract]:
        with self.db.get_session() as session:
            rows = (
                session.query(CodingWorktreeLease)
                .filter(
                    CodingWorktreeLease.status.in_(
                        WORKTREE_LEASE_ACTIVE_STATUSES
                    )
                )
                .order_by(CodingWorktreeLease.created_at.asc())
                .all()
            )
            return [self._row_to_contract(row) for row in rows]

    def heartbeat(
        self, lease_id: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        heartbeat_at = at or _utc_now()
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, lease_id)
            row.last_heartbeat_at = heartbeat_at
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def mark_expired(
        self, lease_id: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        expired_at = at or _utc_now()
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, lease_id)
            row.status = "expired"
            row.last_heartbeat_at = expired_at
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def mark_abandoned(
        self, lease_id: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        abandoned_at = at or _utc_now()
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, lease_id)
            row.status = "abandoned"
            row.last_heartbeat_at = abandoned_at
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def release_lease(
        self, lease_id: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        released_at = at or _utc_now()
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, lease_id)
            row.status = "released"
            row.released_at = released_at
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def mark_cleanup_pending(
        self, lease_id: str, reason: str | None = None
    ) -> WorktreeLeaseContract:
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, lease_id)
            row.status = "cleanup_pending"
            if reason:
                metadata = dict(row.extra_meta or {})
                metadata["cleanup_pending_reason"] = str(reason).strip()
                row.extra_meta = metadata
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def mark_cleaned(
        self, lease_id: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        cleaned_at = at or _utc_now()
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, lease_id)
            row.status = "cleaned"
            row.cleanup_completed_at = cleaned_at
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def record_cleanup_error(
        self, lease_id: str, error: str, at: datetime | None = None
    ) -> WorktreeLeaseContract:
        error_at = at or _utc_now()
        bounded_error = _bound_cleanup_error(error)
        with self.db.get_session() as session:
            row = self._get_row_or_raise(session, lease_id)
            row.cleanup_error = bounded_error
            metadata = dict(row.extra_meta or {})
            metadata["cleanup_error_recorded_at"] = error_at.isoformat()
            row.extra_meta = metadata
            session.commit()
            session.refresh(row)
            return self._row_to_contract(row)

    def _assert_no_active_conflict(
        self,
        session: Any,
        candidate_lease: WorktreeLeaseContract,
    ) -> None:
        active_rows = (
            session.query(CodingWorktreeLease)
            .filter(
                CodingWorktreeLease.status.in_(WORKTREE_LEASE_ACTIVE_STATUSES)
            )
            .all()
        )
        active_contracts = [self._row_to_contract(row) for row in active_rows]
        result = validate_no_shared_mutable_worktree(
            [*active_contracts, candidate_lease]
        )
        if result.ok:
            return

        if result.reason_code == "shared_active_worktree_path":
            raise WorktreeLeaseConflict(
                field="worktree_path",
                value=candidate_lease.worktree_path,
            )
        if result.reason_code == "shared_active_branch_name":
            raise WorktreeLeaseConflict(
                field="branch_name",
                value=candidate_lease.branch_name,
            )

        raise WorktreeLeaseValidationError(result)

    def _get_row_or_raise(
        self, session: Any, lease_id: str
    ) -> CodingWorktreeLease:
        row = (
            session.query(CodingWorktreeLease)
            .filter_by(lease_id=lease_id)
            .first()
        )
        if row is None:
            raise WorktreeLeaseNotFound(f"unknown lease_id: {lease_id}")
        return row

    def _translate_integrity_error(
        self,
        error: IntegrityError,
        lease: WorktreeLeaseContract,
    ) -> WorktreeLeaseStoreError:
        message = str(getattr(error, "orig", error)).lower()
        if "active_worktree_path" in message or "worktree_path" in message:
            return WorktreeLeaseConflict(
                field="worktree_path",
                value=lease.worktree_path,
            )
        if "active_branch_name" in message or "branch_name" in message:
            return WorktreeLeaseConflict(
                field="branch_name",
                value=lease.branch_name,
            )
        if "lease_id" in message or "unique" in message:
            return WorktreeLeaseConflict(field="lease_id", value=lease.lease_id)
        return WorktreeLeaseStoreError("unable to persist worktree lease")

    @staticmethod
    def _row_to_contract(row: CodingWorktreeLease) -> WorktreeLeaseContract:
        return WorktreeLeaseContract(
            lease_id=row.lease_id,
            work_order_id=row.work_order_id,
            run_id=row.run_id,
            worker_id=row.worker_id,
            base_ref=row.base_ref,
            branch_name=row.branch_name,
            worktree_path=row.worktree_path,
            status=row.status,
            created_at=_ensure_aware_datetime(row.created_at),
            expires_at=_ensure_aware_datetime(row.expires_at),
            preserve_on_failure=bool(row.preserve_on_failure),
            cleanup_policy=row.cleanup_policy,
            last_heartbeat_at=_ensure_aware_datetime(row.last_heartbeat_at),
        )


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ensure_aware_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value


def _bound_cleanup_error(error: str) -> str:
    text = str(error or "").strip()
    if len(text) <= MAX_CLEANUP_ERROR_CHARS:
        return text
    return text[: MAX_CLEANUP_ERROR_CHARS - 3] + "..."


def _extract_extra_meta(lease: WorktreeLeaseContract) -> dict[str, Any]:
    maybe_meta = getattr(lease, "extra_meta", None)
    if isinstance(maybe_meta, dict):
        return dict(maybe_meta)
    return {}


__all__ = [
    "WorktreeLeaseConflict",
    "WorktreeLeaseNotFound",
    "WorktreeLeaseStore",
    "WorktreeLeaseStoreError",
    "WorktreeLeaseValidationError",
]
