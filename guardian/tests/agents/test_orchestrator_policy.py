from __future__ import annotations

from datetime import UTC, datetime, timedelta

from guardian.agents.orchestrator_policy import select_next_work_orders
from guardian.agents.work_orders import WorkOrderContract
from guardian.agents.worktree_leases import WorktreeLeaseContract


def _work_order(
    *,
    work_order_id: str,
    status: str = "ready",
    priority: int = 0,
    created_at: datetime | None = None,
    dependency_ids: list[str] | None = None,
    file_scope: list[str] | None = None,
    require_human_review_before_merge: bool = True,
    latest_lease_id: str | None = None,
) -> WorkOrderContract:
    ts = created_at or datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    return WorkOrderContract(
        work_order_id=work_order_id,
        campaign_id="campaign-1",
        title=f"Work order {work_order_id}",
        objective="Test orchestrator policy.",
        scope="backend",
        status=status,
        priority=priority,
        created_by="test",
        assigned_worker_id=None,
        source_thread_id=None,
        source_message_id=None,
        dependency_ids=list(dependency_ids or []),
        file_scope=list(file_scope or []),
        validation_command="pytest -q",
        adapter_kind="mock",
        max_validation_attempts=1,
        require_worktree_lease=False,
        commit_after_validation=False,
        require_human_review_before_merge=require_human_review_before_merge,
        latest_run_id=None,
        latest_lease_id=latest_lease_id,
        latest_receipt_id=None,
        blocked_reason=None,
        extra_meta={},
        created_at=ts,
        updated_at=ts,
        archived_at=None,
    )


def _active_lease(
    *,
    lease_id: str,
    work_order_id: str,
    branch_name: str = "codex/lease",
    worktree_path: str = "/tmp/codexify/worktrees/lease",
) -> WorktreeLeaseContract:
    created_at = datetime(2026, 5, 10, 13, 0, tzinfo=UTC)
    return WorktreeLeaseContract(
        lease_id=lease_id,
        work_order_id=work_order_id,
        run_id=f"run-{lease_id}",
        worker_id="worker-1",
        base_ref="origin/main",
        branch_name=branch_name,
        worktree_path=worktree_path,
        status="active",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=1),
        preserve_on_failure=False,
        cleanup_policy="cleanup_on_merge",
        last_heartbeat_at=created_at + timedelta(minutes=5),
    )


def test_ready_task_is_recommended() -> None:
    ready = _work_order(work_order_id="wo-ready")

    result = select_next_work_orders([ready], limit=5)

    assert len(result.recommendations) == 1
    assert result.recommendations[0].work_order_id == "wo-ready"
    assert result.recommendations[0].decision == "recommendation_only"
    assert "READY_FOR_DISPATCH" in result.recommendations[0].reason_codes


def test_non_ready_task_is_skipped_with_status_not_ready() -> None:
    running = _work_order(work_order_id="wo-running", status="running")

    result = select_next_work_orders([running], limit=5)

    assert result.recommendations == []
    assert len(result.skipped) == 1
    assert result.skipped[0].work_order_id == "wo-running"
    assert result.skipped[0].reason_code == "STATUS_NOT_READY"


def test_higher_priority_ranks_first() -> None:
    low = _work_order(work_order_id="wo-low", priority=1)
    high = _work_order(work_order_id="wo-high", priority=10)

    result = select_next_work_orders([low, high], limit=5)

    assert [item.work_order_id for item in result.recommendations] == [
        "wo-high",
        "wo-low",
    ]


def test_tie_breaks_by_created_at_then_work_order_id() -> None:
    base_time = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    older = _work_order(
        work_order_id="wo-older",
        priority=5,
        created_at=base_time,
    )
    newer = _work_order(
        work_order_id="wo-newer",
        priority=5,
        created_at=base_time + timedelta(minutes=1),
    )
    same_time_b = _work_order(
        work_order_id="wo-b",
        priority=5,
        created_at=base_time,
    )
    same_time_a = _work_order(
        work_order_id="wo-a",
        priority=5,
        created_at=base_time,
    )

    result = select_next_work_orders(
        [newer, older, same_time_b, same_time_a],
        limit=10,
    )

    assert [item.work_order_id for item in result.recommendations] == [
        "wo-a",
        "wo-b",
        "wo-older",
        "wo-newer",
    ]


def test_hard_dependency_not_satisfied_skips() -> None:
    dependency = _work_order(work_order_id="wo-dep", status="running")
    candidate = _work_order(
        work_order_id="wo-candidate",
        dependency_ids=["wo-dep"],
    )

    result = select_next_work_orders([dependency, candidate], limit=5)

    assert result.recommendations == []
    skip = next(
        item for item in result.skipped if item.work_order_id == "wo-candidate"
    )
    assert skip.reason_code == "DEPENDENCY_NOT_SATISFIED"


def test_missing_dependency_skips_with_ambiguous_state() -> None:
    candidate = _work_order(
        work_order_id="wo-candidate",
        dependency_ids=["wo-missing"],
    )

    result = select_next_work_orders([candidate], limit=5)

    assert result.recommendations == []
    assert len(result.skipped) == 1
    assert result.skipped[0].reason_code == "AMBIGUOUS_STATE"


def test_satisfied_dependency_allows_recommendation() -> None:
    dependency = _work_order(work_order_id="wo-dep", status="merged")
    candidate = _work_order(
        work_order_id="wo-candidate",
        dependency_ids=["wo-dep"],
    )

    result = select_next_work_orders([dependency, candidate], limit=5)

    assert [item.work_order_id for item in result.recommendations] == [
        "wo-candidate"
    ]


def test_active_file_scope_conflict_skips() -> None:
    active = _work_order(
        work_order_id="wo-active",
        status="running",
        file_scope=["guardian/workers/coding_worker.py"],
    )
    candidate = _work_order(
        work_order_id="wo-candidate",
        file_scope=["guardian/workers/coding_worker.py"],
    )

    result = select_next_work_orders([active, candidate], limit=5)

    assert result.recommendations == []
    skip = next(
        item for item in result.skipped if item.work_order_id == "wo-candidate"
    )
    assert skip.reason_code == "FILE_SCOPE_CONFLICT"


def test_active_lease_conflict_skips() -> None:
    candidate = _work_order(
        work_order_id="wo-candidate",
        latest_lease_id="lease-123",
    )
    active_lease = _active_lease(
        lease_id="lease-123",
        work_order_id="wo-other",
    )

    result = select_next_work_orders(
        [candidate],
        active_leases=[active_lease],
        limit=5,
    )

    assert result.recommendations == []
    assert len(result.skipped) == 1
    assert result.skipped[0].reason_code == "ACTIVE_LEASE_CONFLICT"


def test_limit_bounds_recommendation_count() -> None:
    work_orders = [
        _work_order(work_order_id=f"wo-{index}", priority=index)
        for index in range(5)
    ]

    result = select_next_work_orders(work_orders, limit=2)

    assert len(result.recommendations) == 2


def test_selector_does_not_mutate_input_objects() -> None:
    work_orders = [
        _work_order(work_order_id="wo-1", file_scope=["a.py"]),
        _work_order(work_order_id="wo-2", file_scope=["b.py"]),
    ]
    original_payloads = [item.to_dict() for item in work_orders]

    select_next_work_orders(work_orders, limit=5)

    assert [item.to_dict() for item in work_orders] == original_payloads
