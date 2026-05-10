from __future__ import annotations

from contextlib import suppress

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.agents.work_order_store import (
    WorkOrderNotFound,
    WorkOrderStore,
    WorkOrderTransitionError,
    WorkOrderValidationError,
)
from guardian.agents.work_orders import (
    WorkOrderContract,
    WorkOrderCreate,
    WorkOrderUpdate,
)
from guardian.db.models import CodingWorkOrder


class _TestDB:
    def __init__(self) -> None:
        self._engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        CodingWorkOrder.__table__.create(bind=self._engine)
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            future=True,
        )

    def get_session(self):  # noqa: ANN201
        return self._session_factory()

    def close(self) -> None:
        with suppress(Exception):
            CodingWorkOrder.__table__.drop(bind=self._engine)
        self._engine.dispose()


@pytest.fixture
def store() -> WorkOrderStore:
    db = _TestDB()
    try:
        yield WorkOrderStore(db=db)
    finally:
        db.close()


def _sample_create(
    *,
    campaign_id: str | None = "campaign-a",
    title: str = "Phase 5 work order",
    objective: str = "Add durable task-board API",
    status: str | None = None,
) -> WorkOrderCreate:
    return WorkOrderCreate.from_dict(
        {
            "campaign_id": campaign_id,
            "title": title,
            "objective": objective,
            "scope": "backend only",
            "status": status,
            "priority": 1,
            "dependency_ids": ["wo-pre-1"],
            "file_scope": ["guardian/routes/coding_work_orders.py"],
            "validation_command": "pytest -q",
            "adapter_kind": "mock",
            "max_validation_attempts": 1,
            "require_worktree_lease": False,
            "commit_after_validation": False,
            "require_human_review_before_merge": True,
        }
    )


def test_create_and_read_work_order(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())
    fetched = store.get_work_order(created.work_order_id)

    assert isinstance(created, WorkOrderContract)
    assert fetched is not None
    assert fetched.work_order_id == created.work_order_id
    assert fetched.title == "Phase 5 work order"
    assert fetched.status == "ready"


def test_list_by_status(store: WorkOrderStore) -> None:
    ready = store.create_work_order(_sample_create(title="Ready work"))
    draft = store.create_work_order(
        _sample_create(title="Draft work", status="draft")
    )

    ready_items = store.list_work_orders(status="ready")
    draft_items = store.list_work_orders(status="draft")

    assert [item.work_order_id for item in ready_items] == [ready.work_order_id]
    assert [item.work_order_id for item in draft_items] == [draft.work_order_id]


def test_list_by_campaign_id(store: WorkOrderStore) -> None:
    first = store.create_work_order(_sample_create(campaign_id="campaign-a"))
    store.create_work_order(_sample_create(campaign_id="campaign-b"))

    items = store.list_work_orders(campaign_id="campaign-a")

    assert [item.work_order_id for item in items] == [first.work_order_id]


def test_update_mutable_fields(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())

    updated = store.update_work_order(
        created.work_order_id,
        WorkOrderUpdate.from_dict(
            {
                "title": "Updated title",
                "objective": "Updated objective",
                "scope": "narrow scope",
                "priority": 7,
                "file_scope": ["guardian/agents/work_order_store.py"],
                "dependency_ids": ["wo-dep-a", "wo-dep-b"],
            }
        ),
    )

    assert updated.title == "Updated title"
    assert updated.objective == "Updated objective"
    assert updated.scope == "narrow scope"
    assert updated.priority == 7
    assert updated.file_scope == ["guardian/agents/work_order_store.py"]
    assert updated.dependency_ids == ["wo-dep-a", "wo-dep-b"]


def test_transition_allowed_state(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())

    transitioned = store.transition_work_order(created.work_order_id, "leased")

    assert transitioned.status == "leased"


def test_reject_forbidden_transition(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())

    with pytest.raises(WorkOrderTransitionError):
        store.transition_work_order(created.work_order_id, "merged")


def test_cancel_work_order(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())

    cancelled = store.cancel_work_order(
        created.work_order_id, reason="operator"
    )

    assert cancelled.status == "cancelled"
    assert cancelled.blocked_reason == "operator"


def test_archive_work_order(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())
    cancelled = store.cancel_work_order(created.work_order_id)

    archived = store.archive_work_order(cancelled.work_order_id)

    assert archived.status == "archived"
    assert archived.archived_at is not None


def test_mark_latest_run_lease_and_receipt(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())

    updated = store.mark_latest_run(
        created.work_order_id,
        run_id="run-001",
        lease_id="lease-001",
        receipt_id="receipt-001",
    )

    assert updated.latest_run_id == "run-001"
    assert updated.latest_lease_id == "lease-001"
    assert updated.latest_receipt_id == "receipt-001"


def test_unknown_work_order_raises_not_found(store: WorkOrderStore) -> None:
    with pytest.raises(WorkOrderNotFound):
        store.cancel_work_order("wo_missing")


def test_invalid_status_raises_validation_or_transition_error(
    store: WorkOrderStore,
) -> None:
    with pytest.raises(WorkOrderValidationError):
        store.create_work_order(_sample_create(status="invalid-status"))

    created = store.create_work_order(_sample_create())
    with pytest.raises(WorkOrderValidationError):
        store.transition_work_order(created.work_order_id, "also-invalid")


def test_returned_contract_serializes_safely(store: WorkOrderStore) -> None:
    created = store.create_work_order(_sample_create())

    assert isinstance(created, WorkOrderContract)
    serialized = created.to_dict()

    assert serialized["work_order_id"] == created.work_order_id
    assert serialized["title"] == created.title
    assert serialized["status"] == created.status
