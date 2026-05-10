from __future__ import annotations

from datetime import UTC, datetime, timedelta

from guardian.agents.worktree_leases import (
    WORKTREE_LEASE_CLEANUP_POLICIES,
    WORKTREE_LEASE_STATUSES,
    WorktreeLeaseContract,
    is_active_lease_status,
    is_terminal_lease_status,
    validate_lease_contract,
    validate_no_shared_mutable_worktree,
)


def _sample_lease(**overrides: object) -> WorktreeLeaseContract:
    created_at = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    payload: dict[str, object] = {
        "lease_id": "lease-001",
        "work_order_id": "wo-001",
        "run_id": "run-001",
        "worker_id": "worker-a",
        "base_ref": "origin/main",
        "branch_name": "codex/wo-001",
        "worktree_path": "/tmp/codexify/worktrees/wo-001",
        "status": "active",
        "created_at": created_at,
        "expires_at": created_at + timedelta(hours=1),
        "preserve_on_failure": True,
        "cleanup_policy": "preserve_on_fail",
        "last_heartbeat_at": created_at + timedelta(minutes=5),
    }
    payload.update(overrides)
    return WorktreeLeaseContract(**payload)


def test_valid_lease_contract_passes_validation() -> None:
    result = validate_lease_contract(_sample_lease())
    assert result.ok is True
    assert result.reason is None
    assert result.reason_code is None


def test_invalid_status_fails_validation() -> None:
    lease = _sample_lease(status="queued")
    result = validate_lease_contract(lease)
    assert result.ok is False
    assert result.reason_code == "invalid_lease_status"


def test_invalid_cleanup_policy_fails_validation() -> None:
    lease = _sample_lease(cleanup_policy="always_cleanup")
    result = validate_lease_contract(lease)
    assert result.ok is False
    assert result.reason_code == "invalid_cleanup_policy"


def test_missing_required_string_field_fails_validation() -> None:
    lease = _sample_lease(worktree_path="  ")
    result = validate_lease_contract(lease)
    assert result.ok is False
    assert result.reason_code == "missing_required_string_field"


def test_expires_before_created_fails_validation() -> None:
    created_at = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    lease = _sample_lease(
        created_at=created_at,
        expires_at=created_at - timedelta(seconds=1),
    )
    result = validate_lease_contract(lease)
    assert result.ok is False
    assert result.reason_code == "expires_before_created"


def test_last_heartbeat_before_created_fails_validation() -> None:
    created_at = datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    lease = _sample_lease(
        created_at=created_at,
        last_heartbeat_at=created_at - timedelta(seconds=1),
    )
    result = validate_lease_contract(lease)
    assert result.ok is False
    assert result.reason_code == "heartbeat_before_created"


def test_two_active_leases_same_worktree_path_fails() -> None:
    lease_a = _sample_lease(lease_id="lease-a", branch_name="codex/wo-a")
    lease_b = _sample_lease(
        lease_id="lease-b",
        run_id="run-b",
        worker_id="worker-b",
        branch_name="codex/wo-b",
    )
    result = validate_no_shared_mutable_worktree([lease_a, lease_b])
    assert result.ok is False
    assert result.reason_code == "shared_active_worktree_path"


def test_two_active_leases_same_branch_name_fails() -> None:
    lease_a = _sample_lease(
        lease_id="lease-a",
        branch_name="codex/shared-branch",
        worktree_path="/tmp/codexify/worktrees/a",
    )
    lease_b = _sample_lease(
        lease_id="lease-b",
        run_id="run-b",
        worker_id="worker-b",
        branch_name="codex/shared-branch",
        worktree_path="/tmp/codexify/worktrees/b",
    )
    result = validate_no_shared_mutable_worktree([lease_a, lease_b])
    assert result.ok is False
    assert result.reason_code == "shared_active_branch_name"


def test_terminal_prior_lease_permits_reuse() -> None:
    prior = _sample_lease(
        lease_id="lease-prior",
        status="cleaned",
        branch_name="codex/reusable",
        worktree_path="/tmp/codexify/worktrees/reusable",
    )
    active = _sample_lease(
        lease_id="lease-active",
        run_id="run-active",
        worker_id="worker-active",
        status="active",
        branch_name="codex/reusable",
        worktree_path="/tmp/codexify/worktrees/reusable",
    )
    result = validate_no_shared_mutable_worktree([prior, active])
    assert result.ok is True


def test_serialization_round_trip_preserves_values() -> None:
    lease = _sample_lease()
    serialized = lease.to_dict()
    restored = WorktreeLeaseContract.from_dict(serialized)
    assert restored == lease
    assert restored.to_dict() == serialized


def test_status_helpers_follow_documented_semantics() -> None:
    assert is_active_lease_status("active") is True
    assert is_active_lease_status("cleaned") is False

    assert is_terminal_lease_status("cleaned") is True
    assert is_terminal_lease_status("released") is True
    assert is_terminal_lease_status("failed") is True
    assert is_terminal_lease_status("active") is False


def test_token_sets_match_expected_values() -> None:
    assert WORKTREE_LEASE_STATUSES == {
        "active",
        "expired",
        "released",
        "abandoned",
        "cleanup_pending",
        "cleaned",
        "blocked",
        "failed",
    }
    assert WORKTREE_LEASE_CLEANUP_POLICIES == {
        "cleanup_on_merge",
        "preserve_on_fail",
        "manual_cleanup_required",
    }
