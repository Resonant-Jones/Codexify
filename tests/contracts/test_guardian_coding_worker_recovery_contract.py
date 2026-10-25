"""Guardian coding worker — restart reconciliation contract.

This file is the executable record of the **restart-reconciliation gate**.

The October 23 durable-acceptance slice gave a Guardian coding run a durable
record of ownership: the canonical ``agent_runs`` row moves ``queued`` ->
``running`` and stamps ``started_at`` exactly once, so an accepted execution
survives worker death as an *accepted* run.

That record is necessary but not sufficient. Reconciliation also needs to tell
an **abandoned** accepted run from an **actively owned** one. The gate for that
distinction is the *worker-liveness authority*: durable evidence of which worker
instance owns which run, and whether that owner is still alive.

The gate is evaluated here, and it **still fails** — but now only on its
*liveness* half. Durable worker ownership has since been added, so the
canonical run records the worker instance that accepted it and the unique claim
it made. What the runtime still cannot supply is a signal that the owner is
*gone*: there is no coding-worker heartbeat, no expiry, and no fencing. Every
remaining candidate signal is either a timestamp, Redis emptiness, or a table
that no production code path ever writes.

These tests therefore assert three things, and only these three things:

1. **The gate.** Ownership is now durable, but the durable records that would
   carry *liveness* do not carry it, and the existing recovery contract's own
   semantics leave an attempt with no liveness evidence alone.
2. **The gap.** A worker restart performs no reconciliation: an accepted run
   left behind by a dead worker stays ``running`` with no escalation, no
   artifact, no requeued task, no credential lease, no provider invocation, and
   no source-thread result.
3. **The disposition.** The canonical operator-visible disposition --
   ``agent_runs.status = 'escalated'`` plus one ``agent_escalations`` row --
   already exists and needs no migration. The *only* missing prerequisite is
   the liveness authority, not the representation.

The tripwire at the end of this file marks the desired end-to-end behaviour as
``xfail(strict=True)``. It is the specification for the next task, and it will
fail the suite if the behaviour ever starts happening without the prerequisite
landing.
"""

from __future__ import annotations

import importlib.util
import inspect
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from guardian.agents.store import AgentStore
from guardian.core import guardian_dispatch
from guardian.core.guardian_dispatch import (
    GuardianDispatchRecord,
    GuardianDispatchState,
    classify_dispatch_health,
    observe_liveness,
    recover_dispatch,
)
from guardian.db.models import AgentDeployment, AgentEscalation, AgentRun
from guardian.workers import coding_worker

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GUARDIAN_ROOT = _REPO_ROOT / "guardian"
_CONTRACTS_DIR = Path(__file__).resolve().parent

# The acceptance contract owns the proven disposable-PostgreSQL harness and
# the real Guardian dispatch path. Load it by path so the recovery contract
# does not duplicate it and cannot drift from it.
_spec = importlib.util.spec_from_file_location(
    "_guardian_acceptance_contract",
    _CONTRACTS_DIR / "test_guardian_coding_worker_acceptance_contract.py",
)
assert _spec is not None and _spec.loader is not None
acceptance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(acceptance)

_TestDB = acceptance._TestDB


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 1. The gate: worker-liveness authority.
# ---------------------------------------------------------------------------

_WORKER_OWNERSHIP_TOKENS = (
    "worker",
    "owner",
    "lease",
    "heartbeat",
    "fencing",
    "epoch",
)

#: The dispatch record legitimately carries liveness *inputs*
#: (``lease_id``, ``last_heartbeat_at``, ``lease_expires_at``). What it must not
#: carry is the identity of the worker that owns the attempt.
_WORKER_IDENTITY_TOKENS = (
    "worker",
    "owner",
    "fencing",
    "epoch",
)


def _columns(model: Any) -> set[str]:
    return {str(column.name) for column in model.__table__.columns}


def test_the_canonical_run_record_carries_ownership_but_no_liveness_signal() -> None:
    """``agent_runs`` says who owns a run, but not whether that owner is alive.

    Durable worker ownership has since been added, so the *ownership* half of
    the liveness gate is closed: the canonical run records the worker instance
    that accepted it and the unique claim it made. The *liveness* half is what
    still fails, and it is what keeps reconciliation unimplemented.
    """
    columns = _columns(AgentRun)

    # The ownership half of the gate is closed.
    assert "coding_worker_instance_id" in columns
    assert "coding_worker_claim_id" in columns

    # The liveness half is not: there is no heartbeat, expiry, or lease signal.
    for token in ("heartbeat", "expires", "lease"):
        assert not any(token in column for column in columns), (
            f"agent_runs gained a {token!r} column; the liveness gate must be "
            "re-evaluated against the new authority"
        )

    # The only liveness-adjacent field is the acceptance timestamp, which is a
    # timestamp and therefore not a liveness signal.
    assert "started_at" in columns
    assert "ended_at" in columns


def test_the_deployment_record_carries_no_worker_ownership() -> None:
    """``agent_deployments`` cannot say which worker owns a run either."""
    columns = _columns(AgentDeployment)

    for token in _WORKER_OWNERSHIP_TOKENS:
        assert not any(token in column for column in columns), (
            f"agent_deployments gained a {token!r} column; the liveness gate "
            "must be re-evaluated against the new authority"
        )


def test_the_dispatch_recovery_record_is_not_persisted_and_has_no_worker() -> None:
    """The recovery vocabulary is a value object, not a durable ownership record."""
    fields = set(GuardianDispatchRecord.__dataclass_fields__)

    for token in _WORKER_IDENTITY_TOKENS:
        assert not any(token in field for field in fields), (
            f"GuardianDispatchRecord gained a {token!r} field; the liveness "
            "gate must be re-evaluated against the new authority"
        )

    # It is a frozen in-memory value object. Nothing persists it.
    assert GuardianDispatchRecord.__dataclass_params__.frozen is True
    module_source = inspect.getsource(guardian_dispatch)
    for marker in ("session.add", "INSERT INTO", "commit("):
        assert marker not in module_source, (
            f"guardian_dispatch now touches {marker!r}; the liveness gate must "
            "be re-evaluated against the new authority"
        )


def _production_sources() -> list[Path]:
    """Every Guardian source file that is not a test."""
    sources: list[Path] = []
    for path in sorted(_GUARDIAN_ROOT.rglob("*.py")):
        if "tests" in path.parts or path.name.startswith("test_"):
            continue
        sources.append(path)
    return sources


def test_no_production_code_path_creates_a_worktree_lease() -> None:
    """The lease table has the right shape, but nothing in production writes it."""
    offenders: list[str] = []
    for path in _production_sources():
        source = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\.create_lease\s*\(", source):
            offenders.append(str(path.relative_to(_REPO_ROOT)))

    assert not offenders, (
        "a production code path now creates a worktree lease: "
        f"{offenders}. Re-evaluate the liveness gate against it."
    )


def test_the_coding_worker_publishes_no_heartbeat() -> None:
    """The coding worker has no liveness signal; the chat and voice workers do."""
    coding_source = (
        _GUARDIAN_ROOT / "workers" / "coding_worker.py"
    ).read_text(encoding="utf-8", errors="replace")

    # A worker *liveness* heartbeat. The worktree-lease heartbeat is a
    # different thing: it refreshes a lease that the control plane created,
    # and the Guardian path has no lease.
    assert "WORKER_HEARTBEAT" not in coding_source.upper(), (
        "the coding worker now publishes a worker heartbeat; re-evaluate the "
        "liveness gate against it"
    )
    assert "codexify:worker:coding" not in coding_source, (
        "the coding worker now owns a worker heartbeat key; re-evaluate the "
        "liveness gate against it"
    )

    # Contrast: the runtime does have an established heartbeat pattern for
    # other workers. It is the shape the prerequisite should follow.
    chat_source = (_GUARDIAN_ROOT / "workers" / "chat_worker.py").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "WORKER_HEARTBEAT_KEY" in chat_source
    assert "codexify:worker:chat:heartbeat" in chat_source

    voice_source = (_GUARDIAN_ROOT / "voice" / "runtime.py").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "VOICE_HEARTBEAT_KEY" in voice_source


def test_the_worktree_lease_contract_cannot_carry_a_guardian_run() -> None:
    """A lease is a worktree claim, so it cannot own a non-isolated Guardian run."""
    from guardian.agents.worktree_leases import (
        WorktreeLeaseContract,
        validate_lease_contract,
    )

    moment = datetime.now(timezone.utc)
    lease = WorktreeLeaseContract(
        lease_id="lease-1",
        work_order_id="",  # a Guardian delegation has no work order
        run_id="run-1",
        worker_id="worker-1",
        base_ref="",
        branch_name="",  # no branch without worktree isolation
        worktree_path="",  # no worktree path without worktree isolation
        status="active",
        created_at=moment,
        expires_at=moment,
        preserve_on_failure=False,
        cleanup_policy="cleanup_on_merge",
    )

    result = validate_lease_contract(lease)

    assert not result.ok
    assert result.reason_code == "missing_required_string_field"


def test_the_existing_classifier_leaves_an_attempt_without_evidence_alone() -> None:
    """The existing contract's own rule: absence of evidence is not loss."""
    record = GuardianDispatchRecord(
        intent_id="gdi-1",
        deployment_id="dep-1",
        run_id="run-1",
        attempt_id="attempt-1",
        coding_task_id="coding-task-1",
        state=GuardianDispatchState.DISPATCHED.value,
    )

    classified = classify_dispatch_health(record)

    assert classified.state == GuardianDispatchState.DISPATCHED.value
    assert classified.reason_code is None


def test_the_existing_contract_quarantines_rather_than_re_dispatching() -> None:
    """Recovery refuses to re-drive an attempt; it escalates to a human."""
    record = GuardianDispatchRecord(
        intent_id="gdi-1",
        deployment_id="dep-1",
        run_id="run-1",
        attempt_id="attempt-1",
        coding_task_id="coding-task-1",
        state=GuardianDispatchState.UNCERTAIN.value,
        reason_code="guardian_dispatch_liveness_unproven",
    )

    recovered = recover_dispatch(record)

    assert recovered.state == GuardianDispatchState.QUARANTINED.value
    assert recovered.reason_code == "guardian_dispatch_recovery_requires_fencing"
    assert recovered.operator_authorized is False


def test_the_existing_classifier_marks_stale_evidence_uncertain() -> None:
    """With liveness evidence supplied, the existing contract does classify."""
    from datetime import datetime, timedelta, timezone

    stale = datetime.now(timezone.utc) - timedelta(hours=2)
    record = observe_liveness(
        GuardianDispatchRecord(
            intent_id="gdi-1",
            deployment_id="dep-1",
            run_id="run-1",
            attempt_id="attempt-1",
            coding_task_id="coding-task-1",
            state=GuardianDispatchState.DISPATCHED.value,
        ),
        last_heartbeat_at=stale,
    )

    classified = classify_dispatch_health(record)

    assert classified.state == GuardianDispatchState.UNCERTAIN.value
    assert classified.reason_code == "guardian_dispatch_liveness_unproven"


# ---------------------------------------------------------------------------
# 2. The gap: a restart reconciles nothing.
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Iterator[Any]:
    with acceptance._disposable_postgres_engine() as engine:
        acceptance.Base.metadata.create_all(bind=engine)
        yield acceptance._TestDB(engine)


@pytest.fixture
def _isolated_queue() -> Iterator[None]:
    from guardian.queue import redis_queue

    previous_client = redis_queue._CLIENT
    previous_queue_client = redis_queue._QUEUE_CLIENT
    redis_queue._CLIENT = redis_queue._InMemoryRedis()
    redis_queue._QUEUE_CLIENT = redis_queue._InMemoryRedis()
    try:
        yield
    finally:
        redis_queue._CLIENT = previous_client
        redis_queue._QUEUE_CLIENT = previous_queue_client


def _abandoned_accepted_run(db: Any) -> dict[str, Any]:
    """Leave a run in exactly the state an interrupted worker leaves behind.

    A worker that durably accepted a run and then died leaves the canonical
    row ``running`` with ``started_at`` stamped, no ``ended_at``, no error, and
    no escalation. The controlled SIGKILL proof recorded in the receipt
    observes exactly this state.
    """
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    outcome = acceptance._claim(db, task)
    assert outcome == acceptance._ACCEPTED

    state = acceptance._read_run(db, str(task.run_id))
    assert state["status"] == "running"
    assert state["started_at"] is not None
    assert state["ended_at"] is None
    return dispatched


def _run_worker_restart(db: Any) -> None:
    """Run the coding worker's real startup sequence against the durable state."""
    previous_store = coding_worker._store
    original_resolve = coding_worker._resolve_guardian_db
    coding_worker._resolve_guardian_db = lambda: db  # type: ignore[assignment]
    try:
        coding_worker._initialize_worker()
        worker = coding_worker.CodingWorker()
        worker.poll_once()
    finally:
        coding_worker._resolve_guardian_db = original_resolve  # type: ignore[assignment]
        coding_worker._store = previous_store


def test_a_restarted_worker_performs_no_reconciliation_of_an_abandoned_run(
    db: Any,
) -> None:
    """The gap, stated directly: a restart classifies nothing."""
    dispatched = _abandoned_accepted_run(db)
    run_id = str(dispatched["task"].run_id)

    _run_worker_restart(db)

    state = acceptance._read_run(db, run_id)
    assert state["status"] == "running", "the restart changed the canonical status"
    assert state["ended_at"] is None

    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=run_id).one()
        escalations = (
            session.query(AgentEscalation)
            .filter_by(run_id=run_row.id)
            .all()
        )
    assert escalations == [], "a restart created an escalation record"


def test_the_accepted_run_survives_the_worker_disappearance(db: Any) -> None:
    """The acceptance record is the substrate recovery would need, and it is stable."""
    dispatched = _abandoned_accepted_run(db)
    run_id = str(dispatched["task"].run_id)
    before = acceptance._read_run(db, run_id)

    _run_worker_restart(db)
    _run_worker_restart(db)

    after = acceptance._read_run(db, run_id)
    assert after["status"] == "running"
    assert after["started_at"] == before["started_at"]


def test_a_restart_reinserts_no_queue_task(db: Any) -> None:
    """Recovery must not restore an accepted task to the queue."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    _abandoned_accepted_run(db)

    _run_worker_restart(db)

    assert dequeue_coding_execution(block=False) is None


def test_a_restart_fabricates_no_source_thread_result(db: Any) -> None:
    """An unresolved attempt gets no result message."""
    dispatched = _abandoned_accepted_run(db)
    thread_id = dispatched["task"].thread_id

    _run_worker_restart(db)

    assert acceptance._coding_result_message_count(db, thread_id) == 0


def test_a_restart_produces_no_result_artifact(db: Any) -> None:
    """An unresolved attempt gets no artifact."""
    dispatched = _abandoned_accepted_run(db)
    run_id = str(dispatched["task"].run_id)

    _run_worker_restart(db)

    assert acceptance._artifact_count(db, run_id) == 0


def test_a_terminal_run_is_untouched_by_a_restart(db: Any) -> None:
    """A durable terminal result is authoritative and stays authoritative."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        run_row.status = "succeeded"
        run_row.ended_at = _utc_now()
        session.commit()

    _run_worker_restart(db)

    state = acceptance._read_run(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert state["ended_at"] is not None
    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        escalations = (
            session.query(AgentEscalation)
            .filter_by(run_id=run_row.id)
            .all()
        )
    assert escalations == []


def test_repeated_restarts_leave_the_canonical_state_unchanged(db: Any) -> None:
    """Reconciliation is idempotent by construction: it does not happen at all."""
    dispatched = _abandoned_accepted_run(db)
    run_id = str(dispatched["task"].run_id)
    before = acceptance._read_run(db, run_id)

    for _ in range(3):
        _run_worker_restart(db)

    assert acceptance._read_run(db, run_id) == before


# ---------------------------------------------------------------------------
# 3. The disposition: the representation already exists.
# ---------------------------------------------------------------------------


def test_the_canonical_escalated_disposition_requires_no_migration(db: Any) -> None:
    """The operator-visible disposition fits the existing schema exactly."""
    dispatched = _abandoned_accepted_run(db)
    run_id = str(dispatched["task"].run_id)
    store = AgentStore(db=db)

    escalation = store.add_escalation(
        run_id=run_id,
        step_index=None,
        severity="hard",
        reason_code="guardian_dispatch_liveness_unproven",
        reason="the owning worker is gone; the execution outcome is unknown",
        preserved_worktree=True,
        payload={
            "recovery_classification": "uncertain",
            "canonical_disposition": "escalated",
            "execution_result": "unknown",
            "attempt_id": dispatched["task"].attempt_id,
            "coding_task_id": dispatched["task"].coding_task_id,
            "reconciled_at": _utc_now().isoformat(),
        },
    )

    assert escalation["status"] == "open"
    assert escalation["reason_code"] == "guardian_dispatch_liveness_unproven"
    assert escalation["preserved_worktree"] is True

    store.update_run_status(run_id=run_id, status="escalated")
    state = acceptance._read_run(db, run_id)
    assert state["status"] == "escalated"
    assert state["ended_at"] is not None

    recorded = store.list_escalations(run_id=run_id)
    assert len(recorded) == 1
    assert recorded[0]["reason_code"] == "guardian_dispatch_liveness_unproven"


def test_the_escalated_disposition_preserves_the_original_lineage(db: Any) -> None:
    """Escalating a run does not rewrite its identity."""
    dispatched = _abandoned_accepted_run(db)
    task = dispatched["task"]
    run_id = str(task.run_id)
    store = AgentStore(db=db)

    before = acceptance._read_run(db, run_id)
    store.add_escalation(
        run_id=run_id,
        step_index=None,
        severity="hard",
        reason_code="guardian_dispatch_liveness_unproven",
        reason="unresolved",
        preserved_worktree=True,
        payload={"attempt_id": str(task.attempt_id)},
    )
    store.update_run_status(run_id=run_id, status="escalated")

    after = acceptance._read_run(db, run_id)
    assert after["run_id"] == before["run_id"]
    assert after["started_at"] == before["started_at"]
    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=run_id).one()
        assert run_row.deployment_id is not None
        assert run_row.thread_id == before["thread_id"]


def test_the_recovery_evidence_row_carries_no_credential_material(db: Any) -> None:
    """Recovery evidence is a curated payload, not a provider transcript."""
    dispatched = _abandoned_accepted_run(db)
    run_id = str(dispatched["task"].run_id)
    store = AgentStore(db=db)

    store.add_escalation(
        run_id=run_id,
        step_index=None,
        severity="hard",
        reason_code="guardian_dispatch_liveness_unproven",
        reason="unresolved",
        preserved_worktree=True,
        payload={"execution_result": "unknown"},
    )

    with db.get_session() as session:
        row = (
            session.query(AgentEscalation)
            .join(AgentRun, AgentRun.id == AgentEscalation.run_id)
            .filter(AgentRun.run_id == run_id)
            .one()
        )
        payload_text = str(row.payload_json or {})

    for secret_marker in ("api_key", "sk-", "Bearer", "authorization", "secret"):
        assert secret_marker.lower() not in payload_text.lower()


# ---------------------------------------------------------------------------
# 4. The tripwire for the next task.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "blocked on durable worker-ownership/fencing authority: the runtime has "
        "no per-run worker ownership and no coding-worker liveness signal, so a "
        "restart cannot distinguish an abandoned accepted run from an actively "
        "owned one. See the receipt for the liveness gate."
    ),
)
def test_a_restarted_worker_reconciles_an_abandoned_accepted_run(db: Any) -> None:
    """The desired end-to-end behaviour, which the liveness prerequisite unlocks."""
    dispatched = _abandoned_accepted_run(db)
    run_id = str(dispatched["task"].run_id)

    _run_worker_restart(db)

    state = acceptance._read_run(db, run_id)
    assert state["status"] == "escalated"
    assert state["ended_at"] is not None

    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=run_id).one()
        escalations = (
            session.query(AgentEscalation)
            .filter_by(run_id=run_row.id)
            .all()
        )
    assert len(escalations) == 1
    assert escalations[0].status == "open"
    assert escalations[0].reason_code == "guardian_dispatch_liveness_unproven"
    assert escalations[0].payload_json["execution_result"] == "unknown"
