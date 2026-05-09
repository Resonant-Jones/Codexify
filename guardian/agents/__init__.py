"""Guardian agent-domain contract exports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .worktree_leases import (
    WORKTREE_LEASE_ACTIVE_STATUSES,
    WORKTREE_LEASE_CLEANUP_POLICIES,
    WORKTREE_LEASE_STATUSES,
    WORKTREE_LEASE_TERMINAL_STATUSES,
    WorktreeLeaseCleanupPolicy,
    WorktreeLeaseContract,
    WorktreeLeaseRequest,
    WorktreeLeaseStatus,
    WorktreeLeaseValidationResult,
    is_active_lease_status,
    is_terminal_lease_status,
    validate_lease_contract,
    validate_no_shared_mutable_worktree,
)

if TYPE_CHECKING:
    from .worktree_lease_store import (
        WorktreeLeaseConflict,
        WorktreeLeaseNotFound,
        WorktreeLeaseStore,
        WorktreeLeaseStoreError,
        WorktreeLeaseValidationError,
    )

__all__ = [
    "WorktreeLeaseCleanupPolicy",
    "WorktreeLeaseContract",
    "WorktreeLeaseRequest",
    "WorktreeLeaseStatus",
    "WorktreeLeaseValidationResult",
    "WORKTREE_LEASE_ACTIVE_STATUSES",
    "WORKTREE_LEASE_CLEANUP_POLICIES",
    "WORKTREE_LEASE_STATUSES",
    "WORKTREE_LEASE_TERMINAL_STATUSES",
    "is_active_lease_status",
    "is_terminal_lease_status",
    "validate_lease_contract",
    "validate_no_shared_mutable_worktree",
    "WorktreeLeaseStore",
    "WorktreeLeaseStoreError",
    "WorktreeLeaseNotFound",
    "WorktreeLeaseConflict",
    "WorktreeLeaseValidationError",
]


def __getattr__(name: str) -> Any:
    if name in {
        "WorktreeLeaseStore",
        "WorktreeLeaseStoreError",
        "WorktreeLeaseNotFound",
        "WorktreeLeaseConflict",
        "WorktreeLeaseValidationError",
    }:
        from .worktree_lease_store import (
            WorktreeLeaseConflict,
            WorktreeLeaseNotFound,
            WorktreeLeaseStore,
            WorktreeLeaseStoreError,
            WorktreeLeaseValidationError,
        )

        mapping = {
            "WorktreeLeaseStore": WorktreeLeaseStore,
            "WorktreeLeaseStoreError": WorktreeLeaseStoreError,
            "WorktreeLeaseNotFound": WorktreeLeaseNotFound,
            "WorktreeLeaseConflict": WorktreeLeaseConflict,
            "WorktreeLeaseValidationError": WorktreeLeaseValidationError,
        }
        return mapping[name]
    raise AttributeError(name)
