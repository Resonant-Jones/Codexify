"""Guardian agent-domain contract exports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .commit_gate import CommitGateError, CommitGateResult, commit_after_green
from .orchestrator_policy import (
    OrchestratorDecision,
    OrchestratorPolicyInput,
    OrchestratorPolicyResult,
    OrchestratorRecommendation,
    OrchestratorSkipReason,
    select_next_work_orders,
)
from .work_orders import (
    WORK_ORDER_ACTIVE_STATUSES,
    WORK_ORDER_ALLOWED_TRANSITIONS,
    WORK_ORDER_STATUSES,
    WORK_ORDER_TERMINAL_STATUSES,
    WorkOrderContract,
    WorkOrderCreate,
    WorkOrderStatus,
    WorkOrderUpdate,
    WorkOrderValidationResult,
    is_active_work_order_status,
    is_terminal_work_order_status,
    validate_work_order_transition,
)
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
    from .work_order_store import (
        WorkOrderNotFound,
        WorkOrderStore,
        WorkOrderStoreError,
        WorkOrderTransitionError,
        WorkOrderValidationError,
    )
    from .worktree_lease_store import (
        WorktreeLeaseConflict,
        WorktreeLeaseNotFound,
        WorktreeLeaseStore,
        WorktreeLeaseStoreError,
        WorktreeLeaseValidationError,
    )

__all__ = [
    "WorkOrderStatus",
    "WorkOrderCreate",
    "WorkOrderUpdate",
    "WorkOrderContract",
    "WorkOrderValidationResult",
    "WORK_ORDER_STATUSES",
    "WORK_ORDER_TERMINAL_STATUSES",
    "WORK_ORDER_ACTIVE_STATUSES",
    "WORK_ORDER_ALLOWED_TRANSITIONS",
    "is_terminal_work_order_status",
    "is_active_work_order_status",
    "validate_work_order_transition",
    "OrchestratorDecision",
    "OrchestratorPolicyInput",
    "OrchestratorPolicyResult",
    "OrchestratorRecommendation",
    "OrchestratorSkipReason",
    "select_next_work_orders",
    "WorkOrderStore",
    "WorkOrderStoreError",
    "WorkOrderNotFound",
    "WorkOrderValidationError",
    "WorkOrderTransitionError",
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
    "CommitGateError",
    "CommitGateResult",
    "commit_after_green",
]


def __getattr__(name: str) -> Any:
    if name in {
        "WorkOrderStore",
        "WorkOrderStoreError",
        "WorkOrderNotFound",
        "WorkOrderValidationError",
        "WorkOrderTransitionError",
    }:
        from .work_order_store import (
            WorkOrderNotFound,
            WorkOrderStore,
            WorkOrderStoreError,
            WorkOrderTransitionError,
            WorkOrderValidationError,
        )

        mapping = {
            "WorkOrderStore": WorkOrderStore,
            "WorkOrderStoreError": WorkOrderStoreError,
            "WorkOrderNotFound": WorkOrderNotFound,
            "WorkOrderValidationError": WorkOrderValidationError,
            "WorkOrderTransitionError": WorkOrderTransitionError,
        }
        return mapping[name]

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
