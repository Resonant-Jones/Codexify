from __future__ import annotations

from datetime import UTC, datetime

from guardian.agents.work_orders import (
    WORK_ORDER_STATUSES,
    WorkOrderContract,
    WorkOrderCreate,
    is_active_work_order_status,
    is_terminal_work_order_status,
    validate_work_order_transition,
)


def test_valid_create_payload_produces_contract() -> None:
    create_payload = WorkOrderCreate.from_dict(
        {
            "campaign_id": "campaign-1",
            "title": "Add task-board foundation",
            "objective": "Create durable work order APIs.",
            "scope": "Backend only",
            "priority": 5,
            "dependency_ids": ["wo-a", "wo-b"],
            "file_scope": ["guardian/routes", "guardian/agents"],
            "validation_command": "pytest -q",
            "adapter_kind": "pi_sdk",
            "max_validation_attempts": 2,
            "require_worktree_lease": True,
            "commit_after_validation": True,
            "require_human_review_before_merge": True,
            "extra_meta": {"ticket": "TASK-005"},
        }
    )

    created_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    contract = WorkOrderContract(
        work_order_id="wo_123",
        campaign_id=create_payload.campaign_id,
        title=create_payload.title,
        objective=create_payload.objective,
        scope=create_payload.scope,
        status="ready",
        priority=create_payload.priority,
        created_by=create_payload.created_by,
        assigned_worker_id=create_payload.assigned_worker_id,
        source_thread_id=create_payload.source_thread_id,
        source_message_id=create_payload.source_message_id,
        dependency_ids=create_payload.dependency_ids,
        file_scope=create_payload.file_scope,
        validation_command=create_payload.validation_command,
        adapter_kind=create_payload.adapter_kind,
        max_validation_attempts=create_payload.max_validation_attempts,
        require_worktree_lease=create_payload.require_worktree_lease,
        commit_after_validation=create_payload.commit_after_validation,
        require_human_review_before_merge=(
            create_payload.require_human_review_before_merge
        ),
        latest_run_id=None,
        latest_lease_id=None,
        latest_receipt_id=None,
        blocked_reason=None,
        extra_meta=create_payload.extra_meta,
        created_at=created_at,
        updated_at=created_at,
        archived_at=None,
    )

    assert contract.work_order_id == "wo_123"
    assert contract.status == "ready"
    assert contract.dependency_ids == ["wo-a", "wo-b"]


def test_invalid_status_fails_transition_validation() -> None:
    result = validate_work_order_transition("ready", "not-a-status")
    assert result.ok is False
    assert result.reason_code == "invalid_work_order_status"


def test_allowed_transition_passes() -> None:
    result = validate_work_order_transition("ready", "leased")
    assert result.ok is True


def test_forbidden_transition_fails() -> None:
    result = validate_work_order_transition("draft", "running")
    assert result.ok is False
    assert result.reason_code == "invalid_work_order_transition"


def test_terminal_and_active_helpers_match_contract() -> None:
    assert is_terminal_work_order_status("failed") is True
    assert is_terminal_work_order_status("merged") is True
    assert is_terminal_work_order_status("ready") is False

    assert is_active_work_order_status("ready") is True
    assert is_active_work_order_status("running") is True
    assert is_active_work_order_status("cancelled") is False


def test_serialization_round_trip_preserves_values() -> None:
    created_at = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    contract = WorkOrderContract(
        work_order_id="wo_serialize",
        campaign_id="campaign-2",
        title="Serialize work-order",
        objective="Verify stable serialization",
        scope="contracts",
        status="draft",
        priority=1,
        created_by="local",
        assigned_worker_id="worker-1",
        source_thread_id="thread-1",
        source_message_id="message-1",
        dependency_ids=["wo-dep-1"],
        file_scope=["guardian/agents/work_orders.py"],
        validation_command="pytest -q",
        adapter_kind="mock",
        max_validation_attempts=1,
        require_worktree_lease=False,
        commit_after_validation=False,
        require_human_review_before_merge=True,
        latest_run_id="run-1",
        latest_lease_id="lease-1",
        latest_receipt_id="receipt-1",
        blocked_reason=None,
        extra_meta={"kind": "contract"},
        created_at=created_at,
        updated_at=created_at,
        archived_at=None,
    )

    serialized = contract.to_dict()
    restored = WorkOrderContract.from_dict(serialized)

    assert restored == contract
    assert restored.to_dict() == serialized


def test_dependency_and_file_scope_defaults_to_empty_lists() -> None:
    payload = WorkOrderCreate.from_dict(
        {
            "title": "Default lists",
            "objective": "Ensure list defaults",
        }
    )

    assert payload.dependency_ids == []
    assert payload.file_scope == []


def test_status_tokens_match_expected_values() -> None:
    assert WORK_ORDER_STATUSES == {
        "draft",
        "ready",
        "leased",
        "running",
        "validating",
        "retrying",
        "passed",
        "failed",
        "blocked",
        "escalated",
        "merge_ready",
        "merged",
        "archived",
        "cancelled",
    }
