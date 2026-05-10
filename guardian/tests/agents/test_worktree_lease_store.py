from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.agents.worktree_lease_store import (
    MAX_CLEANUP_ERROR_CHARS,
    WorktreeLeaseConflict,
    WorktreeLeaseNotFound,
    WorktreeLeaseStore,
    WorktreeLeaseValidationError,
)
from guardian.agents.worktree_leases import WorktreeLeaseContract
from guardian.db.models import CodingWorktreeLease


class _TestDB:
    def __init__(self) -> None:
        self._engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        CodingWorktreeLease.__table__.create(bind=self._engine)
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
            CodingWorktreeLease.__table__.drop(bind=self._engine)
        self._engine.dispose()


@pytest.fixture
def store() -> WorktreeLeaseStore:
    db = _TestDB()
    try:
        yield WorktreeLeaseStore(db=db)
    finally:
        db.close()


def _sample_lease(
    *,
    suffix: str = "001",
    status: str = "active",
    work_order_id: str = "wo-001",
    branch_name: str | None = None,
    worktree_path: str | None = None,
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
    cleanup_policy: str = "cleanup_on_merge",
    preserve_on_failure: bool = False,
    last_heartbeat_at: datetime | None = None,
) -> WorktreeLeaseContract:
    created = created_at or datetime(2026, 5, 9, 12, 0, tzinfo=UTC)
    expires = expires_at or (created + timedelta(hours=1))
    return WorktreeLeaseContract(
        lease_id=f"lease-{suffix}",
        work_order_id=work_order_id,
        run_id=f"run-{suffix}",
        worker_id=f"worker-{suffix}",
        base_ref="origin/main",
        branch_name=branch_name or f"codex/wo-{suffix}",
        worktree_path=worktree_path or f"/tmp/codexify/worktrees/wo-{suffix}",
        status=status,
        created_at=created,
        expires_at=expires,
        preserve_on_failure=preserve_on_failure,
        cleanup_policy=cleanup_policy,
        last_heartbeat_at=last_heartbeat_at,
    )


def _get_row(store: WorktreeLeaseStore, lease_id: str) -> CodingWorktreeLease:
    with store.db.get_session() as session:
        row = (
            session.query(CodingWorktreeLease)
            .filter_by(lease_id=lease_id)
            .first()
        )
        assert row is not None
        return row


def test_creates_and_reads_lease(store: WorktreeLeaseStore) -> None:
    lease = _sample_lease()
    created = store.create_lease(lease)
    fetched = store.get_lease(lease.lease_id)

    assert created == lease
    assert fetched == lease
    assert isinstance(created, WorktreeLeaseContract)


def test_lists_leases_for_work_order(store: WorktreeLeaseStore) -> None:
    lease_a = _sample_lease(suffix="a", work_order_id="wo-shared")
    lease_b = _sample_lease(suffix="b", work_order_id="wo-shared")
    lease_c = _sample_lease(suffix="c", work_order_id="wo-other")
    store.create_lease(lease_a)
    store.create_lease(lease_b)
    store.create_lease(lease_c)

    leases = store.list_leases_for_work_order("wo-shared")
    assert [item.lease_id for item in leases] == [
        lease_a.lease_id,
        lease_b.lease_id,
    ]


def test_lists_active_leases(store: WorktreeLeaseStore) -> None:
    active = _sample_lease(suffix="active", status="active")
    released = _sample_lease(suffix="released", status="released")
    store.create_lease(active)
    store.create_lease(released)

    active_leases = store.list_active_leases()
    assert [item.lease_id for item in active_leases] == [active.lease_id]


def test_rejects_duplicate_active_worktree_path(
    store: WorktreeLeaseStore,
) -> None:
    first = _sample_lease(
        suffix="one",
        branch_name="codex/one",
        worktree_path="/tmp/codexify/worktrees/shared",
    )
    second = _sample_lease(
        suffix="two",
        branch_name="codex/two",
        worktree_path="/tmp/codexify/worktrees/shared",
    )
    store.create_lease(first)

    with pytest.raises(WorktreeLeaseConflict) as exc:
        store.create_lease(second)

    assert exc.value.field == "worktree_path"


def test_rejects_duplicate_active_branch_name(
    store: WorktreeLeaseStore,
) -> None:
    first = _sample_lease(
        suffix="one",
        branch_name="codex/shared",
        worktree_path="/tmp/codexify/worktrees/one",
    )
    second = _sample_lease(
        suffix="two",
        branch_name="codex/shared",
        worktree_path="/tmp/codexify/worktrees/two",
    )
    store.create_lease(first)

    with pytest.raises(WorktreeLeaseConflict) as exc:
        store.create_lease(second)

    assert exc.value.field == "branch_name"


def test_terminal_prior_lease_permits_reuse(store: WorktreeLeaseStore) -> None:
    shared_branch = "codex/reusable"
    shared_path = "/tmp/codexify/worktrees/reusable"
    first = _sample_lease(
        suffix="one",
        branch_name=shared_branch,
        worktree_path=shared_path,
    )
    store.create_lease(first)
    store.release_lease(first.lease_id)

    second = _sample_lease(
        suffix="two",
        branch_name=shared_branch,
        worktree_path=shared_path,
    )
    created = store.create_lease(second)

    assert created.lease_id == second.lease_id


def test_heartbeat_updates_last_heartbeat_at(store: WorktreeLeaseStore) -> None:
    lease = _sample_lease(suffix="hb")
    store.create_lease(lease)
    heartbeat_at = lease.created_at + timedelta(minutes=15)

    updated = store.heartbeat(lease.lease_id, at=heartbeat_at)

    assert updated.last_heartbeat_at == heartbeat_at


def test_mark_expired_updates_status(store: WorktreeLeaseStore) -> None:
    lease = _sample_lease(suffix="expired")
    store.create_lease(lease)

    updated = store.mark_expired(lease.lease_id)

    assert updated.status == "expired"


def test_mark_abandoned_updates_status(store: WorktreeLeaseStore) -> None:
    lease = _sample_lease(suffix="abandoned")
    store.create_lease(lease)

    updated = store.mark_abandoned(lease.lease_id)

    assert updated.status == "abandoned"


def test_release_lease_updates_status_and_released_at(
    store: WorktreeLeaseStore,
) -> None:
    lease = _sample_lease(suffix="release")
    store.create_lease(lease)

    updated = store.release_lease(lease.lease_id)
    row = _get_row(store, lease.lease_id)

    assert updated.status == "released"
    assert row.released_at is not None


def test_mark_cleanup_pending_updates_status(store: WorktreeLeaseStore) -> None:
    lease = _sample_lease(suffix="cleanup-pending")
    store.create_lease(lease)

    updated = store.mark_cleanup_pending(lease.lease_id, reason="operator")
    row = _get_row(store, lease.lease_id)

    assert updated.status == "cleanup_pending"
    assert isinstance(row.extra_meta, dict)
    assert row.extra_meta.get("cleanup_pending_reason") == "operator"


def test_mark_cleaned_updates_status_and_cleanup_completed_at(
    store: WorktreeLeaseStore,
) -> None:
    lease = _sample_lease(suffix="cleaned")
    store.create_lease(lease)

    updated = store.mark_cleaned(lease.lease_id)
    row = _get_row(store, lease.lease_id)

    assert updated.status == "cleaned"
    assert row.cleanup_completed_at is not None


def test_record_cleanup_error_is_bounded_and_persists(
    store: WorktreeLeaseStore,
) -> None:
    lease = _sample_lease(suffix="cleanup-error")
    created = store.create_lease(lease)

    very_long_error = "x" * (MAX_CLEANUP_ERROR_CHARS + 100)
    updated = store.record_cleanup_error(lease.lease_id, error=very_long_error)
    row = _get_row(store, lease.lease_id)

    assert updated.status == created.status
    assert row.cleanup_error is not None
    assert len(row.cleanup_error) == MAX_CLEANUP_ERROR_CHARS
    assert isinstance(row.extra_meta, dict)
    assert "cleanup_error_recorded_at" in row.extra_meta


def test_unknown_lease_id_raises_not_found(store: WorktreeLeaseStore) -> None:
    with pytest.raises(WorktreeLeaseNotFound):
        store.release_lease("missing-lease")


def test_invalid_contract_raises_validation_error(
    store: WorktreeLeaseStore,
) -> None:
    lease = _sample_lease(status="not_a_real_status")

    with pytest.raises(WorktreeLeaseValidationError) as exc:
        store.create_lease(lease)

    assert exc.value.reason_code == "invalid_lease_status"


def test_returned_contract_serializes_to_dict(
    store: WorktreeLeaseStore,
) -> None:
    lease = _sample_lease(suffix="serialize")

    created = store.create_lease(lease)
    payload = created.to_dict()

    assert isinstance(created, WorktreeLeaseContract)
    assert payload["lease_id"] == lease.lease_id
    assert payload["status"] == "active"
