"""Guardian coding run — canonical liveness classification contract.

Durable ownership says *who* holds a run. The claim-scoped heartbeat says that
the holder was **still reporting**. This contract proves that Guardian can now
read and classify that evidence from canonical PostgreSQL state — and that the
classification stays *observational*.

The distinctions under test:

- never accepted,
- recently observed,
- stale and uncertain,
- missing evidence,
- already resolved,
- already escalated,
- inconsistent evidence.

**What the classifier must never do.** It must not retry, requeue, terminate a
process, revoke a credential, replace an execution binding, transfer
ownership, escalate a run, or change any canonical state. A stale heartbeat is
evidence of uncertainty, not proof that the worker died.
"""

from __future__ import annotations

import importlib.util
import json
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

from guardian.agents.store import AgentStore
from guardian.core import guardian_dispatch
from guardian.core.guardian_dispatch import (
    GuardianDispatchState,
    classify_dispatch_health,
    recover_dispatch,
)
from guardian.db.models import AgentEscalation, AgentRun

try:  # The baseline has no canonical liveness classification.
    from guardian.core.guardian_dispatch import (
        CODING_RUN_HEARTBEAT_INTERVAL_SECONDS,
        CODING_RUN_LIVENESS_STALE_AFTER_SECONDS,
        CodingRunLivenessEvidence,
        classify_coding_run_liveness,
    )
except ImportError:
    CODING_RUN_HEARTBEAT_INTERVAL_SECONDS = 15
    CODING_RUN_LIVENESS_STALE_AFTER_SECONDS = 60

    class CodingRunLivenessEvidence(str, Enum):  # type: ignore[no-redef]
        """The baseline has no liveness vocabulary."""

        NEVER_ACCEPTED = "never_accepted"
        RECENTLY_OBSERVED = "recently_observed"
        STALE_UNCERTAIN = "stale_uncertain"
        MISSING_EVIDENCE = "missing_evidence"
        ALREADY_RESOLVED = "already_resolved"
        ALREADY_ESCALATED = "already_escalated"
        INCONSISTENT = "inconsistent"
        UNOBSERVABLE = "unobservable"

    def classify_coding_run_liveness(  # type: ignore[misc]
        snapshot: Any, **_kwargs: Any
    ) -> Any:
        raise AssertionError(
            "the baseline has no claim-scoped liveness classification: the "
            "canonical ownership and heartbeat evidence is not reachable"
        )

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACTS_DIR = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "_guardian_acceptance_contract",
    _CONTRACTS_DIR / "test_guardian_coding_worker_acceptance_contract.py",
)
assert _spec is not None and _spec.loader is not None
acceptance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(acceptance)

_TestDB = acceptance._TestDB

_INSTANCE_A = "cwi_liveness_worker_a"
_INSTANCE_B = "cwi_liveness_worker_b"
_CLAIM_A = "cwc_liveness_claim_a"
_CLAIM_B = "cwc_liveness_claim_b"

_EVIDENCE = CodingRunLivenessEvidence


# ---------------------------------------------------------------------------
# Fixtures and helpers.
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Iterator[Any]:
    with acceptance._disposable_postgres_engine() as engine:
        acceptance.Base.metadata.create_all(bind=engine)
        yield acceptance._TestDB(engine)


@pytest.fixture(autouse=True)
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


def _accepted_run(
    db: Any,
    *,
    worker_instance_id: str = _INSTANCE_A,
    claim_id: str = _CLAIM_A,
) -> Any:
    """Dispatch a run and accept it under a known worker instance and claim."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert (
        acceptance._claim(
            db,
            task,
            worker_instance_id=worker_instance_id,
            claim_id=claim_id,
        )
        == acceptance._ACCEPTED
    )
    return task


def _seed_second_thread(db: Any, *, user_id: str = "account-1") -> dict[str, Any]:
    """Add another source thread to an account that is already seeded."""
    from guardian.db.models import ChatMessage, ChatThread, Project

    with db.get_session() as session:
        project = session.query(Project).filter_by(user_id=user_id).one()
        thread = ChatThread(
            user_id=user_id,
            title="Second source thread",
            summary="",
            project_id=project.id,
        )
        session.add(thread)
        session.flush()
        message = ChatMessage(
            thread_id=thread.id,
            user_id=user_id,
            role="user",
            content="Also patch the other path.",
            kind="chat",
            extra_meta={},
        )
        session.add(message)
        session.commit()
        return {
            "user_id": user_id,
            "project_id": project.id,
            "thread_id": thread.id,
            "source_message_id": message.id,
        }


def _dispatch_run(db: Any, seeded: dict[str, Any]) -> Any:
    """Dispatch a second run in an account that is already seeded.

    The acceptance harness seeds the account on every dispatch, so the second
    run of a multi-run case is dispatched through the same service entrypoint
    on a second thread of the same account.
    """
    from guardian.core.guardian_delegation_service import GuardianDelegationService
    from guardian.db.models import AgentDeployment, AgentRun
    from guardian.queue.redis_queue import dequeue_coding_execution
    from guardian.tasks.types import CodingExecutionTask

    service = GuardianDelegationService()
    service.configure_db(db)
    intent = service.create_intent(
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
    )
    intent_id = str(intent["intent_id"])
    run_id = str(intent["run_id"])

    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=run_id).one()
        deployment_row = (
            session.query(AgentDeployment)
            .filter_by(id=run_row.deployment_id)
            .one()
        )
        deployment_id = str(deployment_row.deployment_id)
        spec = dict(deployment_row.spec_json or {})

    service.dispatch_delegated_task(
        intent_id=intent_id,
        deployment_id=deployment_id,
        run_id=run_id,
        attempt_id=str(spec.get("attempt_id") or ""),
        coding_task_id=str(spec.get("coding_task_id") or ""),
        instructions="Do the other thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    payload = dequeue_coding_execution(block=False)
    assert payload is not None
    return CodingExecutionTask.from_dict(payload)


def _accepted_second_run(
    db: Any,
    *,
    worker_instance_id: str = _INSTANCE_B,
    claim_id: str = _CLAIM_B,
) -> Any:
    """Dispatch and accept a second run in the already-seeded account."""
    seeded = _seed_second_thread(db)
    task = _dispatch_run(db, seeded)
    assert (
        acceptance._claim(
            db,
            task,
            worker_instance_id=worker_instance_id,
            claim_id=claim_id,
        )
        == acceptance._ACCEPTED
    )
    return task


def _set_heartbeat(db: Any, run_id: str, value: datetime | None) -> None:
    """Write a heartbeat timestamp directly, for boundary cases."""
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        row.coding_worker_last_heartbeat_at = value
        session.commit()


def _set_timeline(
    db: Any,
    run_id: str,
    *,
    heartbeat_at: datetime,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> None:
    """Write a coherent timeline for a run.

    The acceptance stamps ``started_at`` from the application clock and the
    heartbeat from the database clock, so an artificially old heartbeat has to
    be accompanied by an artificially old start -- otherwise the record would
    contradict itself and the classifier would (correctly) call it
    inconsistent.
    """
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        row.started_at = started_at or (heartbeat_at - timedelta(hours=1))
        row.ended_at = ended_at
        row.coding_worker_last_heartbeat_at = heartbeat_at
        session.commit()


def _set_status(db: Any, run_id: str, status: str) -> None:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        row.status = status
        session.commit()


def _snapshot(
    db: Any,
    run_id: str,
    *,
    observation_instant: datetime | None = None,
) -> dict[str, Any] | None:
    store = AgentStore(db=db)
    return store.get_coding_run_liveness_snapshot(
        run_id,
        observation_instant=observation_instant,
    )


def _classify(
    db: Any,
    run_id: str,
    *,
    observation_instant: datetime | None = None,
) -> Any:
    return classify_coding_run_liveness(
        _snapshot(db, run_id, observation_instant=observation_instant)
    )


def _run_row(db: Any, run_id: str) -> dict[str, Any]:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return {
            "status": row.status,
            "instance_id": row.coding_worker_instance_id,
            "claim_id": row.coding_worker_claim_id,
            "heartbeat_at": row.coding_worker_last_heartbeat_at,
            "started_at": row.started_at,
            "ended_at": row.ended_at,
            "error": row.error,
        }


def _escalation_count(db: Any, run_id: str) -> int:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return (
            session.query(AgentEscalation).filter_by(run_id=row.id).count()
        )


# ---------------------------------------------------------------------------
# 1-2: never accepted, and recently accepted.
# ---------------------------------------------------------------------------


def test_a_queued_run_that_was_never_accepted_is_not_abandoned(db: Any) -> None:
    """A queued run with no claim was never durably accepted."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    verdict = _classify(db, str(task.run_id))

    assert verdict.evidence == _EVIDENCE.NEVER_ACCEPTED.value
    assert verdict.state == GuardianDispatchState.DISPATCHED.value
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_NOT_ACCEPTED
    )
    assert verdict.worker_instance_id is None
    assert verdict.claim_id is None
    assert verdict.evidence_available is False


def test_a_recently_accepted_running_run_is_recently_observed(db: Any) -> None:
    """An accepted run whose claim just renewed is recently observed."""
    task = _accepted_run(db)

    verdict = _classify(db, str(task.run_id))

    assert verdict.evidence == _EVIDENCE.RECENTLY_OBSERVED.value
    assert verdict.state == GuardianDispatchState.EXECUTING.value
    assert verdict.worker_instance_id == _INSTANCE_A
    assert verdict.claim_id == _CLAIM_A
    assert verdict.evidence_available is True
    assert verdict.heartbeat_age_seconds is not None
    assert verdict.heartbeat_age_seconds <= CODING_RUN_LIVENESS_STALE_AFTER_SECONDS


def test_a_fresh_heartbeat_is_recently_observed(db: Any) -> None:
    """A heartbeat well inside the horizon is recent activity."""
    task = _accepted_run(db)

    verdict = _classify(db, str(task.run_id))

    assert verdict.evidence == _EVIDENCE.RECENTLY_OBSERVED.value
    assert verdict.last_heartbeat_at is not None
    assert verdict.observed_at is not None


# ---------------------------------------------------------------------------
# 3-5: the staleness boundary.
# ---------------------------------------------------------------------------


def test_a_heartbeat_exactly_at_the_threshold_is_still_recent(db: Any) -> None:
    """A heartbeat exactly at the observation horizon is still recent."""
    task = _accepted_run(db)
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(task.run_id),
        heartbeat_at=observed
        - timedelta(seconds=CODING_RUN_LIVENESS_STALE_AFTER_SECONDS),
    )

    verdict = _classify(
        db,
        str(task.run_id),
        observation_instant=observed,
    )

    assert verdict.heartbeat_age_seconds == CODING_RUN_LIVENESS_STALE_AFTER_SECONDS
    assert verdict.evidence == _EVIDENCE.RECENTLY_OBSERVED.value
    assert verdict.state == GuardianDispatchState.EXECUTING.value


def test_a_heartbeat_just_beyond_the_threshold_is_stale(db: Any) -> None:
    """A heartbeat just beyond the horizon is stale, not dead."""
    task = _accepted_run(db)
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(task.run_id),
        heartbeat_at=observed
        - timedelta(
            seconds=CODING_RUN_LIVENESS_STALE_AFTER_SECONDS + 1
        ),
    )

    verdict = _classify(
        db,
        str(task.run_id),
        observation_instant=observed,
    )

    assert verdict.evidence == _EVIDENCE.STALE_UNCERTAIN.value
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_STALE
    )
    # The claim is still the recorded owner: staleness does not invalidate it.
    assert verdict.worker_instance_id == _INSTANCE_A
    assert verdict.claim_id == _CLAIM_A


# ---------------------------------------------------------------------------
# 6-9: missing evidence.
# ---------------------------------------------------------------------------


def test_a_running_run_without_a_heartbeat_has_missing_evidence(db: Any) -> None:
    """A running run with no heartbeat carries insufficient evidence."""
    task = _accepted_run(db)
    _set_heartbeat(db, str(task.run_id), None)

    verdict = _classify(db, str(task.run_id))

    assert verdict.evidence == _EVIDENCE.MISSING_EVIDENCE.value
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_MISSING
    )


def test_a_running_run_without_a_worker_identity_has_missing_evidence(
    db: Any,
) -> None:
    """A running run with no worker identity carries insufficient evidence."""
    task = _accepted_run(db)
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_instance_id = None
        row.coding_worker_claim_id = None
        row.coding_worker_last_heartbeat_at = None
        session.commit()

    verdict = _classify(db, str(task.run_id))

    assert verdict.evidence == _EVIDENCE.MISSING_EVIDENCE.value
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value


def test_a_running_run_without_a_claim_has_missing_evidence() -> None:
    """A running run with no claim carries insufficient evidence.

    The canonical schema refuses a half-written ownership pair, so this state
    is only reachable in a record that was written outside the acceptance
    contract. The classifier still has to read it conservatively.
    """
    snapshot = {
        "run_id": "run-no-claim",
        "deployment_id": "dep-1",
        "status": "running",
        "started_at": datetime(2026, 10, 26, 11, 0, 0, tzinfo=timezone.utc),
        "ended_at": None,
        "coding_worker_instance_id": _INSTANCE_A,
        "coding_worker_claim_id": None,
        "coding_worker_last_heartbeat_at": None,
        "observed_at": datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
    }

    verdict = classify_coding_run_liveness(snapshot)

    # A half-written ownership pair is inconsistent before it is anything else.
    assert verdict.evidence == _EVIDENCE.INCONSISTENT.value
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value


def test_a_historical_ownership_unknown_run_stays_unknown(db: Any) -> None:
    """A historical row without ownership stays ownership-unknown."""
    task = _accepted_run(db)
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_instance_id = None
        row.coding_worker_claim_id = None
        row.coding_worker_last_heartbeat_at = None
        session.commit()

    verdict = _classify(db, str(task.run_id))

    assert verdict.evidence == _EVIDENCE.MISSING_EVIDENCE.value
    assert verdict.evidence_available is False
    # Nothing is inferred about whether work started or side effects occurred.
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_MISSING
    )


# ---------------------------------------------------------------------------
# 10-13: resolved and escalated runs.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected_state"),
    [
        ("succeeded", GuardianDispatchState.COMPLETED.value),
        ("failed", GuardianDispatchState.FAILED.value),
        ("canceled", GuardianDispatchState.CANCELLED.value),
    ],
)
def test_a_terminal_run_is_already_resolved(
    db: Any,
    status: str,
    expected_state: str,
) -> None:
    """A terminal run keeps its disposition, however old its heartbeat."""
    task = _accepted_run(db)
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(task.run_id),
        heartbeat_at=observed - timedelta(days=7),
        ended_at=observed - timedelta(days=7, hours=-1),
    )
    _set_status(db, str(task.run_id), status)

    verdict = _classify(
        db,
        str(task.run_id),
        observation_instant=observed,
    )

    assert verdict.evidence == _EVIDENCE.ALREADY_RESOLVED.value
    assert verdict.state == expected_state
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_RESOLVED
    )


def test_an_escalated_run_keeps_its_disposition(db: Any) -> None:
    """An escalated run is already disposed of; a classification never repeats it."""
    task = _accepted_run(db)
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(task.run_id),
        heartbeat_at=observed - timedelta(days=7),
        ended_at=observed - timedelta(days=7, hours=-1),
    )
    _set_status(db, str(task.run_id), "escalated")

    verdict = _classify(
        db,
        str(task.run_id),
        observation_instant=observed,
    )

    assert verdict.evidence == _EVIDENCE.ALREADY_ESCALATED.value
    assert verdict.state == GuardianDispatchState.QUARANTINED.value
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_ESCALATED
    )
    assert _escalation_count(db, str(task.run_id)) == 0


# ---------------------------------------------------------------------------
# 14-15: inconsistent evidence.
# ---------------------------------------------------------------------------


def test_impossible_timestamp_ordering_is_inconsistent(db: Any) -> None:
    """A record that contradicts itself is flagged, not repaired."""
    task = _accepted_run(db)
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.started_at = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
        row.ended_at = datetime(2026, 10, 26, 11, 0, 0, tzinfo=timezone.utc)
        session.commit()

    verdict = _classify(db, str(task.run_id))

    assert verdict.evidence == _EVIDENCE.INCONSISTENT.value
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_INCONSISTENT
    )


def test_a_future_heartbeat_is_inconsistent(db: Any) -> None:
    """A heartbeat beyond the observation instant cannot be taken at face value."""
    task = _accepted_run(db)
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(task.run_id),
        heartbeat_at=observed + timedelta(minutes=5),
    )

    verdict = _classify(
        db,
        str(task.run_id),
        observation_instant=observed,
    )

    assert verdict.evidence == _EVIDENCE.INCONSISTENT.value
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value


def test_partial_ownership_metadata_is_inconsistent() -> None:
    """A half-written ownership pair is inconsistent, wherever it came from."""
    snapshot = {
        "run_id": "run-partial",
        "deployment_id": "dep-1",
        "status": "running",
        "started_at": datetime(2026, 10, 26, 11, 0, 0, tzinfo=timezone.utc),
        "ended_at": None,
        "coding_worker_instance_id": _INSTANCE_A,
        "coding_worker_claim_id": None,
        "coding_worker_last_heartbeat_at": datetime(
            2026, 10, 26, 11, 30, 0, tzinfo=timezone.utc
        ),
        "observed_at": datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
    }

    verdict = classify_coding_run_liveness(snapshot)

    assert verdict.evidence == _EVIDENCE.INCONSISTENT.value
    assert verdict.state == GuardianDispatchState.UNCERTAIN.value


def test_a_queued_run_with_ownership_metadata_is_inconsistent() -> None:
    """A queued run with accepted ownership contradicts the acceptance contract."""
    snapshot = {
        "run_id": "run-queued-owned",
        "deployment_id": "dep-1",
        "status": "queued",
        "started_at": None,
        "ended_at": None,
        "coding_worker_instance_id": _INSTANCE_A,
        "coding_worker_claim_id": _CLAIM_A,
        "coding_worker_last_heartbeat_at": None,
        "observed_at": datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc),
    }

    verdict = classify_coding_run_liveness(snapshot)

    assert verdict.evidence == _EVIDENCE.INCONSISTENT.value


# ---------------------------------------------------------------------------
# 16-17: cross-worker isolation.
# ---------------------------------------------------------------------------


def test_two_workers_are_classified_independently(db: Any) -> None:
    """One worker's silence never makes another worker's run look unhealthy."""
    task_a = _accepted_run(
        db,
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
    )
    task_b = _accepted_second_run(
        db,
        worker_instance_id=_INSTANCE_B,
        claim_id=_CLAIM_B,
    )
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(task_a.run_id),
        heartbeat_at=observed - timedelta(days=1),
    )
    _set_timeline(
        db,
        str(task_b.run_id),
        heartbeat_at=observed - timedelta(seconds=1),
    )

    verdict_a = _classify(
        db,
        str(task_a.run_id),
        observation_instant=observed,
    )
    verdict_b = _classify(
        db,
        str(task_b.run_id),
        observation_instant=observed,
    )

    assert verdict_a.evidence == _EVIDENCE.STALE_UNCERTAIN.value
    assert verdict_b.evidence == _EVIDENCE.RECENTLY_OBSERVED.value
    assert verdict_a.worker_instance_id == _INSTANCE_A
    assert verdict_b.worker_instance_id == _INSTANCE_B


def test_one_worker_owning_two_runs_is_classified_per_run(db: Any) -> None:
    """A worker with two runs is not one global liveness signal."""
    first = _accepted_run(db)
    # One worker instance, two runs: each run carries its own claim, because a
    # claim id identifies exactly one acceptance.
    second = _accepted_second_run(
        db,
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_B,
    )
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(first.run_id),
        heartbeat_at=observed - timedelta(days=1),
    )
    _set_timeline(
        db,
        str(second.run_id),
        heartbeat_at=observed - timedelta(seconds=1),
    )

    verdict_first = _classify(
        db,
        str(first.run_id),
        observation_instant=observed,
    )
    verdict_second = _classify(
        db,
        str(second.run_id),
        observation_instant=observed,
    )

    assert verdict_first.evidence == _EVIDENCE.STALE_UNCERTAIN.value
    assert verdict_second.evidence == _EVIDENCE.RECENTLY_OBSERVED.value
    assert verdict_first.run_id != verdict_second.run_id


# ---------------------------------------------------------------------------
# 18-19: nothing to observe.
# ---------------------------------------------------------------------------


def test_a_missing_run_is_unobservable(db: Any) -> None:
    """A run that does not exist cannot be classified."""
    verdict = _classify(db, "run-that-does-not-exist")

    assert verdict.evidence == _EVIDENCE.UNOBSERVABLE.value
    assert verdict.state is None
    assert verdict.evidence_available is False


def test_an_unreachable_database_is_unobservable(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unreachable persistence fails closed into an explicit observation gap."""
    store = AgentStore(db=db)
    monkeypatch.setattr(store, "_has_db", lambda: False)

    assert store.get_coding_run_liveness_snapshot("run-1") is None
    verdict = classify_coding_run_liveness(None)

    assert verdict.evidence == _EVIDENCE.UNOBSERVABLE.value
    assert verdict.reason_code == (
        guardian_dispatch.CODING_RUN_LIVENESS_REASON_UNOBSERVABLE
    )


# ---------------------------------------------------------------------------
# 20-25: the classification changes nothing.
# ---------------------------------------------------------------------------


def test_classification_does_not_change_the_run_status(db: Any) -> None:
    """Observing a run leaves its canonical row untouched."""
    task = _accepted_run(db)
    before = _run_row(db, str(task.run_id))

    for _ in range(3):
        _classify(db, str(task.run_id))

    after = _run_row(db, str(task.run_id))
    assert after["status"] == before["status"] == "running"
    assert after["ended_at"] is None
    assert after["error"] == before["error"]
    assert after["instance_id"] == before["instance_id"]
    assert after["claim_id"] == before["claim_id"]
    assert after["heartbeat_at"] == before["heartbeat_at"]


def test_classification_creates_no_escalation(db: Any) -> None:
    """A stale classification never creates an escalation."""
    task = _accepted_run(db)
    observed = datetime(2026, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    _set_timeline(
        db,
        str(task.run_id),
        heartbeat_at=observed - timedelta(days=1),
    )

    verdict = _classify(
        db,
        str(task.run_id),
        observation_instant=observed,
    )

    assert verdict.evidence == _EVIDENCE.STALE_UNCERTAIN.value
    assert _escalation_count(db, str(task.run_id)) == 0
    assert _run_row(db, str(task.run_id))["status"] == "running"


def test_classification_does_not_touch_the_queue(db: Any) -> None:
    """Observing a run never enqueues or dequeues a task."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    task = _accepted_run(db)

    _classify(db, str(task.run_id))
    _classify(db, str(task.run_id))

    assert dequeue_coding_execution(block=False) is None


def test_classification_does_not_touch_a_credential_lease(db: Any) -> None:
    """Observing a run never creates or touches an execution lease."""
    from guardian.db.models import CodingWorktreeLease

    task = _accepted_run(db)

    _classify(db, str(task.run_id))

    with db.get_session() as session:
        leases = session.query(CodingWorktreeLease).count()
    assert leases == 0
    assert _run_row(db, str(task.run_id))["status"] == "running"


def test_classification_creates_no_terminal_artifact(db: Any) -> None:
    """Observing a run never creates a coding-result artifact."""
    task = _accepted_run(db)

    _classify(db, str(task.run_id))

    assert acceptance._artifact_count(db, str(task.run_id)) == 0


def test_classification_delivers_no_source_thread_result(db: Any) -> None:
    """Observing a run never delivers a source-thread result."""
    task = _accepted_run(db)

    _classify(db, str(task.run_id))

    assert acceptance._coding_result_message_count(db, task.thread_id) == 0


# ---------------------------------------------------------------------------
# 26-29: compatibility and the boundaries of the policy.
# ---------------------------------------------------------------------------


def test_the_existing_dispatch_classifier_is_unchanged(db: Any) -> None:
    """The established dispatch contract keeps its own semantics."""
    record = guardian_dispatch.GuardianDispatchRecord(
        intent_id="gdi-1",
        deployment_id="dep-1",
        run_id="run-1",
        attempt_id="attempt-1",
        coding_task_id="coding-task-1",
        state=GuardianDispatchState.DISPATCHED.value,
    )

    # No liveness evidence at all: the established rule leaves it alone.
    assert classify_dispatch_health(record).state == (
        GuardianDispatchState.DISPATCHED.value
    )

    # A live lease is proof of liveness, whatever the heartbeat says.
    from datetime import datetime as _datetime

    now = _datetime.now(timezone.utc)
    leased = guardian_dispatch.GuardianDispatchRecord(
        intent_id="gdi-1",
        deployment_id="dep-1",
        run_id="run-1",
        attempt_id="attempt-1",
        coding_task_id="coding-task-1",
        state=GuardianDispatchState.EXECUTING.value,
        last_heartbeat_at=now - timedelta(hours=1),
        lease_expires_at=now + timedelta(minutes=5),
    )
    assert classify_dispatch_health(leased, now=now).state == (
        GuardianDispatchState.EXECUTING.value
    )

    # Stale evidence without a lease is uncertain, not lost.
    stale = guardian_dispatch.GuardianDispatchRecord(
        intent_id="gdi-1",
        deployment_id="dep-1",
        run_id="run-1",
        attempt_id="attempt-1",
        coding_task_id="coding-task-1",
        state=GuardianDispatchState.EXECUTING.value,
        last_heartbeat_at=now - timedelta(hours=1),
    )
    classified = classify_dispatch_health(stale, now=now)
    assert classified.state == GuardianDispatchState.UNCERTAIN.value
    assert classified.reason_code == "guardian_dispatch_liveness_unproven"

    # Recovery still quarantines rather than re-dispatching.
    recovered = recover_dispatch(classified)
    assert recovered.state == GuardianDispatchState.QUARANTINED.value
    assert recovered.reason_code == (
        "guardian_dispatch_recovery_requires_fencing"
    )


def test_historical_null_ownership_remains_readable(db: Any) -> None:
    """A historical ownership-unknown row stays readable and unknown."""
    task = _accepted_run(db)
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_instance_id = None
        row.coding_worker_claim_id = None
        row.coding_worker_last_heartbeat_at = None
        session.commit()

    snapshot = _snapshot(db, str(task.run_id))

    assert snapshot is not None
    assert snapshot["coding_worker_instance_id"] is None
    assert snapshot["coding_worker_claim_id"] is None
    assert snapshot["coding_worker_last_heartbeat_at"] is None
    assert snapshot["observed_at"] is not None
    assert snapshot["status"] == "running"


def test_the_staleness_horizon_follows_the_production_cadence() -> None:
    """The horizon is derived from the cadence the worker actually implements."""
    from guardian.workers import coding_worker

    assert coding_worker.CODING_RUN_HEARTBEAT_INTERVAL_SECONDS == (
        CODING_RUN_HEARTBEAT_INTERVAL_SECONDS
    )
    assert CODING_RUN_LIVENESS_STALE_AFTER_SECONDS == max(
        60,
        3 * CODING_RUN_HEARTBEAT_INTERVAL_SECONDS,
    )
    # It is an observation threshold, not a persisted expiry.
    for forbidden in (
        "worker_dead_at",
        "ownership_expires_at",
        "automatic_takeover_at",
    ):
        assert not hasattr(guardian_dispatch, forbidden)
        assert forbidden not in json.dumps(
            guardian_dispatch.CodingRunLivenessVerdict(
                run_id=None,
                deployment_id=None,
                status=None,
                state=None,
                evidence="x",
                reason_code=None,
                worker_instance_id=None,
                claim_id=None,
                last_heartbeat_at=None,
                observed_at=None,
                heartbeat_age_seconds=None,
                stale_after_seconds=0,
                evidence_available=False,
            ).to_dict()
        )


def test_the_restart_reconciliation_tripwire_remains_unresolved() -> None:
    """The strict-xfail restart tripwire is still in place, still failing."""
    source = (
        _CONTRACTS_DIR / "test_guardian_coding_worker_recovery_contract.py"
    ).read_text(encoding="utf-8")

    assert "test_a_restarted_worker_reconciles_an_abandoned_accepted_run" in source
    assert "strict=True" in source
    assert "xfail" in source
