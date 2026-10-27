"""Guardian coding worker — read-only startup review contract.

A restarted coding worker now performs **one bounded, read-only review** of
the unresolved Guardian coding runs it can see in canonical PostgreSQL state.

This contract proves what that review is, and — just as importantly — what it
is **not**:

- It **observes**. It classifies with the liveness classifier already proven
  for per-run evidence; it does not implement a second classifier.
- It **never acts**. It does not quarantine, retry, requeue, cancel, escalate,
  take ownership, renew a lease, fabricate a result, or terminate a process.
- It **never infers death**. A stale heartbeat is missing evidence, not proof
  that a worker stopped. A worker starting is not evidence about any other
  worker.
- It **never lies about coverage**. A bounded read that stops at its limit is
  reported as *partial*, and an unreachable database is reported as
  *unavailable* — never as an empty inventory.

The distinctions under test:

- never accepted (a queued run is not an abandoned run),
- recently observed (recent activity, **not** proof a process exists),
- stale and uncertain (missing recent activity, **not** proof of death),
- missing evidence (a historical run without ownership or heartbeat),
- already resolved, already escalated (terminal truth stays authoritative),
- inconsistent (a self-contradicting record is reported, not repaired).
"""

from __future__ import annotations

import importlib.util
import json
import signal
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from guardian.agents.store import RUN_TERMINAL_ACCEPTED, AgentStore
from guardian.core.guardian_dispatch import (
    CODING_RUN_LIVENESS_STALE_AFTER_SECONDS,
    CodingRunLivenessEvidence,
)
from guardian.db.models import (
    AgentDeployment,
    AgentEscalation,
    AgentRun,
)
from guardian.workers import coding_worker

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACTS_DIR = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "_guardian_liveness_contract",
    _CONTRACTS_DIR / "test_guardian_coding_run_liveness_contract.py",
)
assert _spec is not None and _spec.loader is not None
liveness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(liveness)
acceptance = liveness.acceptance

_INSTANCE_A = liveness._INSTANCE_A
_INSTANCE_B = liveness._INSTANCE_B
_CLAIM_A = liveness._CLAIM_A
_CLAIM_B = liveness._CLAIM_B

_EVIDENCE = CodingRunLivenessEvidence

#: How long one case may run before it is reported as a failure. Each case
#: creates a disposable PostgreSQL database, so the budget is generous.
_CASE_DEADLINE_SECONDS = 180

try:  # The baseline has no bounded startup review.
    from guardian.agents.store import (
        CODING_RUN_REVIEW_MAX_ROWS,
        CODING_RUN_REVIEW_PARTIAL,
        CODING_RUN_REVIEW_UNAVAILABLE,
    )
    from guardian.workers.coding_worker import CodingRunStartupReview
except ImportError:  # pragma: no cover - the baseline shape
    CODING_RUN_REVIEW_MAX_ROWS = 200
    CODING_RUN_REVIEW_PARTIAL = "guardian_coding_run_review_partial"
    CODING_RUN_REVIEW_UNAVAILABLE = "guardian_coding_run_review_unavailable"
    CodingRunStartupReview = None  # type: ignore[assignment]


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


@pytest.fixture(autouse=True)
def _credential_encryption_key() -> Iterator[None]:
    import os

    previous = os.environ.get("GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY")
    os.environ["GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY"] = (
        "T7xQ9v2Kc4mB8nR3wY6zA1sD5fG0hJ7kL2pX9uV4eC8="
    )
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY", None)
        else:
            os.environ["GUARDIAN_OAUTH_TOKEN_ENCRYPTION_KEY"] = previous


@pytest.fixture(autouse=True)
def _case_deadline() -> Iterator[None]:
    """Fail a case that hangs instead of wedging the suite.

    A disposable PostgreSQL database is created per case, so each case has a
    real cost; a case that exceeds it is reported as a failure rather than
    spinning forever.
    """

    def _on_alarm(_signum: int, _frame: Any) -> None:
        raise AssertionError(
            "the restart-review case exceeded its deadline"
        )

    try:
        signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(_CASE_DEADLINE_SECONDS)
    except ValueError:  # pragma: no cover - not the main thread
        yield
        return
    try:
        yield
    finally:
        signal.alarm(0)


def _store(db: Any) -> AgentStore:
    return AgentStore(db=db)


def _worker(db: Any, *, instance_id: str | None = None) -> Any:
    return coding_worker.CodingWorker(
        agent_store=_store(db),
        **({"worker_instance_id": instance_id} if instance_id else {}),
    )


def _review(db: Any, *, instance_id: str | None = None, limit: int | None = None):
    worker = _worker(db, instance_id=instance_id)
    if limit is None:
        return worker.review_unresolved_coding_runs()
    return worker.review_unresolved_coding_runs(limit=limit)


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


def _escalations(db: Any, run_id: str) -> list[Any]:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return (
            session.query(AgentEscalation)
            .filter_by(run_id=row.id)
            .all()
        )


def _artifact_count(db: Any, run_id: str) -> int:
    """Count the durable artifacts attached to a run."""
    return acceptance._artifact_count(db, run_id)


def _result_message_count(db: Any, thread_id: int | None) -> int:
    """Count the source-thread result messages for a thread."""
    return acceptance._coding_result_message_count(db, thread_id)


def _attempt_count(db: Any, run_id: str) -> int:
    """Count the attempts recorded against a run.

    Attempts hang off the run's steps rather than off the run directly, so
    the count joins through them.
    """
    from guardian.db.models import AgentRunAttempt, AgentRunStep

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        step_ids = [
            step.id
            for step in session.query(AgentRunStep)
            .filter_by(run_id=row.id)
            .all()
        ]
        if not step_ids:
            return 0
        return (
            session.query(AgentRunAttempt)
            .filter(AgentRunAttempt.run_step_id.in_(step_ids))
            .count()
        )


def _accepted_run(db: Any, *, instance_id: str = _INSTANCE_A, claim_id: str = _CLAIM_A):
    return liveness._accepted_run(
        db,
        worker_instance_id=instance_id,
        claim_id=claim_id,
    )


def _stale_heartbeat(db: Any, run_id: str, *, seconds: float = 600) -> None:
    """Write a heartbeat older than the observation horizon.

    The run's start moves with it: ``started_at`` is stamped by the
    application clock and the heartbeat by the database clock, so an
    artificially old heartbeat next to a fresh start would make the record
    contradict itself.
    """
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        moment = datetime.now(timezone.utc) - timedelta(seconds=seconds)
        row.coding_worker_last_heartbeat_at = moment
        row.started_at = moment - timedelta(hours=1)
        session.commit()


def _strip_ownership(db: Any, run_id: str) -> None:
    """Erase a run's ownership identities and heartbeat, as a historical row may lack them.

    The canonical schema requires that a heartbeat implies an owner, so the
    two are cleared together in one statement.
    """
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        row.coding_worker_instance_id = None
        row.coding_worker_claim_id = None
        row.coding_worker_last_heartbeat_at = None
        session.commit()


def _strip_heartbeat(db: Any, run_id: str) -> None:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        row.coding_worker_last_heartbeat_at = None
        session.commit()


def _set_status(db: Any, run_id: str, status: str) -> None:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        row.status = status
        row.ended_at = datetime.now(timezone.utc)
        session.commit()


def _make_non_guardian_run(db: Any) -> str:
    """Create a running AgentRun whose deployment is not Guardian-owned.

    It shares the table with a Guardian coding run but carries no Guardian
    delegation ownership, so it is not part of the reviewed population.
    """
    import uuid

    with db.get_session() as session:
        deployment = AgentDeployment(
            deployment_id=f"dep_plain_{uuid.uuid4().hex[:12]}",
            flow_id="plain_flow",
            spec_json={"kind": "not_guardian"},
            spec_hash="hash",
            trust_state="supervised",
        )
        session.add(deployment)
        session.flush()
        run = AgentRun(
            run_id=f"run_plain_{uuid.uuid4().hex[:12]}",
            deployment_id=deployment.id,
            status="running",
            started_at=datetime.now(timezone.utc),
            coding_worker_instance_id="cwi_plain_worker",
            coding_worker_claim_id="cwc_plain_claim",
            coding_worker_last_heartbeat_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.commit()
        return str(run.run_id)


# ---------------------------------------------------------------------------
# 1-3: the startup boundary, the clock, and the population.
# ---------------------------------------------------------------------------


def test_the_startup_review_runs_before_destructive_dequeue(
    db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The review happens at startup, before the queue is consumed."""
    events: list[str] = []

    class _StopLoop(BaseException):
        """Escape the worker's poll loop.

        It derives from ``BaseException`` on purpose: the poll loop catches
        ``Exception`` around ``poll_once()``, so a plain ``Exception``
        sentinel would be swallowed and the loop would never end.
        """

    def _fake_review(self: Any) -> Any:
        events.append("review")
        return coding_worker.CodingRunStartupReview(
            reviewed_count=0, review_complete=True
        )

    def _fake_poll(self: Any) -> bool:
        events.append("dequeue")
        raise _StopLoop()

    monkeypatch.setattr(
        coding_worker.CodingWorker,
        "review_unresolved_coding_runs",
        _fake_review,
    )
    monkeypatch.setattr(coding_worker.CodingWorker, "poll_once", _fake_poll)
    monkeypatch.setattr(
        coding_worker, "_resolve_guardian_db", lambda: db
    )

    with pytest.raises(_StopLoop):
        coding_worker.run_worker_loop()

    assert events == ["review", "dequeue"], (
        "the startup review must complete before the first destructive dequeue"
    )


def test_the_review_uses_the_database_observation_clock(db: Any) -> None:
    """The observation instant comes from the database, not the host clock."""
    task = _accepted_run(db)
    run_id = str(task.run_id)

    inventory = _store(db).list_unresolved_guardian_coding_runs()
    assert inventory["complete"] is True
    assert inventory["error_code"] is None
    assert len(inventory["runs"]) == 1
    observed_at = inventory["runs"][0]["observed_at"]
    assert isinstance(observed_at, datetime)
    assert observed_at.tzinfo is not None

    # The observation instant is at least as late as the run's heartbeat, and
    # it is a database value: it tracks the same clock the heartbeat is
    # written from.
    row = _run_row(db, run_id)
    assert observed_at >= row["heartbeat_at"]


def test_only_guardian_bound_coding_runs_are_inspected(db: Any) -> None:
    """A running AgentRun that is not Guardian-owned is not in the population."""
    plain_run_id = _make_non_guardian_run(db)
    task = _accepted_run(db)

    inventory = _store(db).list_unresolved_guardian_coding_runs()
    inspected = {str(row["run_id"]) for row in inventory["runs"]}

    assert str(task.run_id) in inspected
    assert plain_run_id not in inspected, (
        "a run that merely shares the table is not a Guardian coding run"
    )


def test_a_running_accepted_run_is_discovered(db: Any) -> None:
    """An accepted, unresolved run is found."""
    task = _accepted_run(db)

    review = _review(db)

    assert review.reviewed_count == 1
    assert str(task.run_id) in review.run_ids
    assert review.review_complete is True
    assert review.review_error_code is None


def test_a_queued_never_accepted_run_is_not_treated_as_abandoned(db: Any) -> None:
    """A queued run was never accepted; it is not an abandoned run."""
    dispatched = acceptance._dispatch_one(db)
    queued_run_id = str(dispatched["task"].run_id)

    review = _review(db)

    assert queued_run_id not in review.run_ids
    assert review.stale_uncertain_count == 0
    assert review.missing_evidence_count == 0
    assert review.reviewed_count == 0

    state = acceptance._read_run(db, queued_run_id)
    assert state["status"] == "queued"


# ---------------------------------------------------------------------------
# 6-9: the classification distinctions.
# ---------------------------------------------------------------------------


def test_a_fresh_heartbeat_is_classified_conservatively(db: Any) -> None:
    """Recent activity is observed. It is not proof that a process exists."""
    task = _accepted_run(db)

    review = _review(db)

    assert review.recently_observed_count == 1
    assert review.stale_uncertain_count == 0
    assert review.missing_evidence_count == 0
    assert review.inconsistent_count == 0


def test_a_stale_heartbeat_remains_uncertain(db: Any) -> None:
    """A stale heartbeat is missing evidence, not proof that the worker died."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id))

    review = _review(db)

    assert review.stale_uncertain_count == 1
    assert review.recently_observed_count == 0
    assert str(task.run_id) in review.stale_uncertain_run_ids

    # The classification used the established observation horizon.
    row = _run_row(db, str(task.run_id))
    age = (
        datetime.now(timezone.utc) - row["heartbeat_at"]
    ).total_seconds()
    assert age > CODING_RUN_LIVENESS_STALE_AFTER_SECONDS


def test_historical_missing_ownership_remains_unknown(db: Any) -> None:
    """A historical run without ownership evidence is not backfilled."""
    task = _accepted_run(db)
    _strip_ownership(db, str(task.run_id))

    review = _review(db)

    assert review.missing_evidence_count == 1
    assert review.recently_observed_count == 0
    assert review.stale_uncertain_count == 0

    row = _run_row(db, str(task.run_id))
    assert row["instance_id"] is None
    assert row["claim_id"] is None, "the review must not backfill identity"


def test_a_missing_heartbeat_remains_unknown(db: Any) -> None:
    """A run with no heartbeat evidence is not declared lost."""
    task = _accepted_run(db)
    _strip_heartbeat(db, str(task.run_id))

    review = _review(db)

    assert review.missing_evidence_count == 1
    assert review.recently_observed_count == 0
    assert review.stale_uncertain_count == 0

    row = _run_row(db, str(task.run_id))
    assert row["heartbeat_at"] is None, (
        "the review must not manufacture an initial heartbeat"
    )


def test_an_inconsistent_record_is_reported_and_not_repaired(db: Any) -> None:
    """A self-contradicting record is surfaced, never repaired."""
    task = _accepted_run(db)
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        # A heartbeat in the future contradicts the observation instant.
        row.coding_worker_last_heartbeat_at = datetime.now(
            timezone.utc
        ) + timedelta(hours=1)
        session.commit()

    review = _review(db)

    assert review.inconsistent_count == 1
    assert review.recently_observed_count == 0
    assert review.stale_uncertain_count == 0


# ---------------------------------------------------------------------------
# 10-13: terminal truth stays authoritative.
# ---------------------------------------------------------------------------


def test_a_terminal_success_is_preserved(db: Any) -> None:
    """A terminal run is not a recovery candidate."""
    task = _accepted_run(db)
    _set_status(db, str(task.run_id), "succeeded")
    before = _run_row(db, str(task.run_id))

    review = _review(db)

    assert str(task.run_id) not in review.run_ids
    assert review.reviewed_count == 0
    assert _run_row(db, str(task.run_id)) == before


def test_a_terminal_failure_is_preserved(db: Any) -> None:
    """A failed run is not a recovery candidate."""
    task = _accepted_run(db)
    _set_status(db, str(task.run_id), "failed")
    before = _run_row(db, str(task.run_id))

    review = _review(db)

    assert str(task.run_id) not in review.run_ids
    assert _run_row(db, str(task.run_id)) == before


def test_a_canceled_execution_is_preserved(db: Any) -> None:
    """A canceled run is not a recovery candidate."""
    task = _accepted_run(db)
    _set_status(db, str(task.run_id), "canceled")
    before = _run_row(db, str(task.run_id))

    review = _review(db)

    assert str(task.run_id) not in review.run_ids
    assert _run_row(db, str(task.run_id)) == before


def test_an_escalated_execution_is_preserved(db: Any) -> None:
    """An escalated run keeps its authoritative disposition."""
    task = _accepted_run(db)
    run_id = str(task.run_id)
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        row.status = "escalated"
        row.ended_at = datetime.now(timezone.utc)
        session.add(
            AgentEscalation(
                run_id=row.id,
                severity="hard",
                reason_code="guardian_dispatch_liveness_unproven",
                reason="already escalated by an operator",
                status="open",
                preserved_worktree=True,
                payload_json={"execution_result": "unknown"},
            )
        )
        session.commit()
    before = _run_row(db, run_id)

    review = _review(db)

    assert run_id not in review.run_ids
    assert len(_escalations(db, run_id)) == 1, (
        "the review must not duplicate an existing escalation"
    )
    assert _run_row(db, run_id) == before


# ---------------------------------------------------------------------------
# 14-16: active worker safety.
# ---------------------------------------------------------------------------


def test_a_completed_run_keeps_its_result_authoritative(
    db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that really completed keeps its result, even after its worker disappears.

    This is the completed-run truth the slice requires: Worker A completes
    Run A through the real claim-fenced terminalization -- which commits the
    terminal decision, the coding-result artifact, and the source-thread
    result together -- and then disappears. The startup review must not turn
    that terminal run into a recovery candidate, and it must not disturb the
    result the run already owns. The missing queue acknowledgement does not
    override canonical terminal evidence.
    """
    from guardian.queue import task_events

    published: list[Any] = []
    original_publish = task_events.publish_with_visibility

    def _capture(*args: Any, **kwargs: Any) -> Any:
        published.append(args)
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(task_events, "publish_with_visibility", _capture)

    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    run_id = str(task.run_id)
    assert acceptance._claim(
        db,
        task,
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
    ) == acceptance._ACCEPTED

    # The real completion: terminal decision, result artifact, and
    # source-thread result committed together under the claim.
    receipt = AgentStore(db=db).finalize_claimed_coding_result(
        run_id=run_id,
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
        coding_task_id=str(task.coding_task_id or ""),
        attempt_id=str(task.attempt_id or ""),
        request_id=task.request_id or None,
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status="succeeded",
        result_summary="Completed before the worker disappeared.",
        adapter_kind="pi_codex_runner",
        files_changed=["guardian/agents/store.py"],
    )
    assert receipt["terminal_accepted"] is True

    # Worker A has now disappeared. The queue carries no acknowledgement of
    # the completion; the canonical record does.
    state_before = _run_row(db, run_id)
    artifacts_before = _artifact_count(db, run_id)
    messages_before = _result_message_count(db, task.thread_id)
    attempts_before = _attempt_count(db, run_id)
    published_before = len(published)

    assert artifacts_before >= 1, "the completion must leave a result artifact"
    assert messages_before >= 1, "the completion must leave a source-thread result"

    # Worker B starts and reviews.
    review = _review(db, instance_id="cwi_other_worker")

    assert run_id not in review.run_ids
    assert review.reviewed_count == 0
    assert review.stale_uncertain_count == 0

    assert _run_row(db, run_id) == state_before
    assert _artifact_count(db, run_id) == artifacts_before
    assert _result_message_count(db, task.thread_id) == messages_before
    assert _attempt_count(db, run_id) == attempts_before
    assert len(published) == published_before, (
        "the review must not emit a duplicate terminal event"
    )


def test_an_active_peer_worker_remains_untouched(db: Any) -> None:
    """A running peer is classified on its own evidence and left alone."""
    first = _accepted_run(db, instance_id=_INSTANCE_A, claim_id=_CLAIM_A)
    peer = liveness._accepted_second_run(
        db,
        worker_instance_id=_INSTANCE_B,
        claim_id=_CLAIM_B,
    )
    _stale_heartbeat(db, str(first.run_id))
    peer_before = _run_row(db, str(peer.run_id))

    review = _review(db, instance_id="cwi_review_worker")

    assert review.reviewed_count == 2
    assert review.stale_uncertain_count == 1
    assert review.recently_observed_count == 1
    assert str(peer.run_id) in review.run_ids

    peer_after = _run_row(db, str(peer.run_id))
    assert peer_after["status"] == peer_before["status"] == "running"
    assert peer_after["instance_id"] == _INSTANCE_B
    assert peer_after["claim_id"] == _CLAIM_B
    assert _escalations(db, str(peer.run_id)) == []


def test_a_second_worker_cannot_claim_a_reviewed_run(db: Any) -> None:
    """Reviewing a run does not transfer its ownership."""
    task = _accepted_run(db, instance_id=_INSTANCE_A, claim_id=_CLAIM_A)
    _stale_heartbeat(db, str(task.run_id))
    before = _run_row(db, str(task.run_id))

    _review(db, instance_id="cwi_other_worker")

    after = _run_row(db, str(task.run_id))
    assert after["instance_id"] == _INSTANCE_A
    assert after["claim_id"] == _CLAIM_A
    assert after == before


def test_multiple_runs_of_one_worker_remain_independent(db: Any) -> None:
    """Two runs of the same worker are reviewed independently."""
    first = _accepted_run(db, instance_id=_INSTANCE_A, claim_id=_CLAIM_A)
    second = liveness._accepted_second_run(
        db,
        worker_instance_id=_INSTANCE_A,
        claim_id="cwc_liveness_claim_c",
    )
    _stale_heartbeat(db, str(first.run_id))

    review = _review(db, instance_id="cwi_other_worker")

    assert review.reviewed_count == 2
    assert review.stale_uncertain_count == 1
    assert review.recently_observed_count == 1
    assert str(first.run_id) in review.stale_uncertain_run_ids
    assert str(second.run_id) not in review.stale_uncertain_run_ids


# ---------------------------------------------------------------------------
# 17-20: bounded coverage, honestly reported.
# ---------------------------------------------------------------------------


def test_cross_account_execution_data_is_not_publicly_exposed(db: Any) -> None:
    """The review is an internal diagnostic, not an account read resource."""
    task = _accepted_run(db)
    review = _review(db)

    payload = json.dumps(review.to_dict(), default=str)
    assert "account-1" not in payload
    assert "@" not in payload
    assert "api_key" not in payload.lower()
    assert "bearer" not in payload.lower()
    assert "sk-" not in payload.lower()

    # The result carries identifiers and counts, never an account's content.
    assert set(review.to_dict()) >= {
        "reviewed_count",
        "recently_observed_count",
        "stale_uncertain_count",
        "missing_evidence_count",
        "already_resolved_count",
        "already_escalated_count",
        "review_complete",
        "review_error_code",
    }


def test_the_review_pagination_is_bounded(db: Any) -> None:
    """The read is bounded and deterministic."""
    _accepted_run(db)
    for index in range(3):
        liveness._accepted_second_run(
            db,
            worker_instance_id=f"cwi_page_{index}",
            claim_id=f"cwc_page_{index}",
        )

    inventory = _store(db).list_unresolved_guardian_coding_runs(limit=2)

    assert len(inventory["runs"]) == 2
    assert inventory["complete"] is False
    assert inventory["error_code"] is None, (
        "a truncated read is not a failed read"
    )
    assert inventory["cursor"] is not None

    # The keyset continues deterministically from the cursor.
    rest = _store(db).list_unresolved_guardian_coding_runs(
        limit=2, after_id=inventory["cursor"]
    )
    first_ids = [str(row["run_id"]) for row in inventory["runs"]]
    rest_ids = [str(row["run_id"]) for row in rest["runs"]]
    assert not set(first_ids) & set(rest_ids)
    assert rest["complete"] is True


def test_a_partial_review_is_reported_as_partial(db: Any) -> None:
    """A bounded read that stops at its limit is never a complete inventory."""
    _accepted_run(db)
    for index in range(3):
        liveness._accepted_second_run(
            db,
            worker_instance_id=f"cwi_partial_{index}",
            claim_id=f"cwc_partial_{index}",
        )

    review = _review(db, limit=2)

    assert review.reviewed_count == 2
    assert review.review_complete is False
    assert review.review_error_code == CODING_RUN_REVIEW_PARTIAL
    assert review.review_error_code != CODING_RUN_REVIEW_UNAVAILABLE


def test_database_unavailability_is_not_an_empty_inventory(db: Any) -> None:
    """An unreachable store is *unavailable*, never "no unresolved runs"."""

    class _BrokenDB:
        def get_session(self) -> Any:
            raise RuntimeError("canonical persistence is unreachable")

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=_BrokenDB()))

    review = worker.review_unresolved_coding_runs()

    assert review.review_complete is False
    assert review.review_error_code == CODING_RUN_REVIEW_UNAVAILABLE
    assert review.reviewed_count == 0
    assert review.stale_uncertain_count == 0
    assert review.run_ids == ()


def test_an_unreachable_store_stops_the_worker_before_it_consumes(
    db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A worker that cannot reach canonical persistence consumes nothing."""
    consumed: list[str] = []

    class _StopLoop(BaseException):
        """Escape the worker's poll loop.

        It derives from ``BaseException`` on purpose: the poll loop catches
        ``Exception`` around ``poll_once()``, so a plain ``Exception``
        sentinel would be swallowed and the loop would never end.
        """

    class _BrokenDB:
        def get_session(self) -> Any:
            raise RuntimeError("canonical persistence is unreachable")

    def _fake_configure_db(_db: Any) -> None:
        coding_worker._store = AgentStore(db=_BrokenDB())

    def _fake_poll(self: Any) -> bool:
        consumed.append("dequeue")
        raise _StopLoop()

    monkeypatch.setattr(coding_worker, "_resolve_guardian_db", lambda: db)
    monkeypatch.setattr(coding_worker, "configure_db", _fake_configure_db)
    monkeypatch.setattr(coding_worker.CodingWorker, "poll_once", _fake_poll)

    with pytest.raises(RuntimeError):
        coding_worker.run_worker_loop()

    assert consumed == [], (
        "a worker without canonical persistence must not consume coding tasks"
    )


# ---------------------------------------------------------------------------
# 21-28: the review changes nothing.
# ---------------------------------------------------------------------------


def test_no_agent_run_mutation_occurs(db: Any) -> None:
    """The review reads the canonical row; it does not write it."""
    task = _accepted_run(db)
    run_id = str(task.run_id)
    _stale_heartbeat(db, run_id)
    before = _run_row(db, run_id)

    _review(db, instance_id="cwi_other_worker")

    assert _run_row(db, run_id) == before


def test_no_agent_escalation_is_created(db: Any) -> None:
    """A stale accepted run does not become an escalation."""
    task = _accepted_run(db)
    run_id = str(task.run_id)
    _stale_heartbeat(db, run_id)

    _review(db, instance_id="cwi_other_worker")

    assert _escalations(db, run_id) == []


def test_no_retry_or_requeue_occurs(db: Any) -> None:
    """The review neither republishes nor requeues a task."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    task = _accepted_run(db)
    run_id = str(task.run_id)
    _stale_heartbeat(db, run_id)

    _review(db, instance_id="cwi_other_worker")

    assert dequeue_coding_execution(block=False) is None


def test_no_credential_lease_is_issued(db: Any) -> None:
    """The review does not mint or renew an execution credential."""
    from guardian.db.models import CodingWorktreeLease

    task = _accepted_run(db)
    run_id = str(task.run_id)
    _stale_heartbeat(db, run_id)

    _review(db, instance_id="cwi_other_worker")

    with db.get_session() as session:
        assert session.query(CodingWorktreeLease).count() == 0


def test_no_new_adapter_invocation_occurs(
    db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The review never reaches the adapter."""
    lookups: list[str] = []

    class _RecordingAdapters(dict):
        def get(self, key: str, default: Any = None) -> Any:
            lookups.append(str(key))
            return dict.get(self, key, default)

    monkeypatch.setattr(
        coding_worker,
        "ADAPTERS",
        _RecordingAdapters(coding_worker.ADAPTERS),
    )

    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id))
    _review(db, instance_id="cwi_other_worker")

    assert lookups == [], "the startup review must not reach an adapter"


def test_no_source_thread_result_is_fabricated(db: Any) -> None:
    """The review delivers nothing to the originating thread."""
    task = _accepted_run(db)
    run_id = str(task.run_id)
    _stale_heartbeat(db, run_id)
    thread_id = int(task.thread_id) if task.thread_id else None

    before = _result_message_count(db, thread_id) if thread_id else 0
    _review(db, instance_id="cwi_other_worker")
    after = _result_message_count(db, thread_id) if thread_id else 0

    assert after == before


def test_no_coding_result_artifact_is_fabricated(db: Any) -> None:
    """The review creates no result artifact."""
    task = _accepted_run(db)
    run_id = str(task.run_id)
    _stale_heartbeat(db, run_id)

    _review(db, instance_id="cwi_other_worker")

    assert _artifact_count(db, run_id) == 0


def test_no_terminal_task_event_is_fabricated(
    db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The review publishes no terminal event."""
    from guardian.queue import task_events

    published: list[Any] = []
    original = task_events.publish_with_visibility

    def _capture(*args: Any, **kwargs: Any) -> Any:
        published.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(task_events, "publish_with_visibility", _capture)

    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id))
    _review(db, instance_id="cwi_other_worker")

    assert published == [], "the startup review must not publish a task event"


# ---------------------------------------------------------------------------
# 29-30: the surrounding contracts still hold.
# ---------------------------------------------------------------------------


def test_existing_normal_worker_execution_remains_functional(db: Any) -> None:
    """The review is additive: the worker still accepts and terminalizes."""
    task = _accepted_run(db)
    run_id = str(task.run_id)

    # The review observes the accepted run.
    review = _review(db, instance_id="cwi_other_worker")
    assert review.reviewed_count == 1
    assert review.recently_observed_count == 1

    # The owning worker still holds the claim and can terminalize.
    state = acceptance._read_run(db, run_id)
    assert state["status"] == "running"
    outcome = AgentStore(db=db).finalize_claimed_run_status(
        run_id=run_id,
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
        status="succeeded",
    )
    assert outcome == RUN_TERMINAL_ACCEPTED
    assert acceptance._read_run(db, run_id)["status"] == "succeeded"


def test_the_restart_reconciliation_tripwire_remains_unresolved(db: Any) -> None:
    """Read-only observation does not satisfy the escalation tripwire."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert acceptance._claim(db, task) == acceptance._ACCEPTED
    run_id = str(task.run_id)
    _stale_heartbeat(db, run_id)

    review = _review(db, instance_id="cwi_other_worker")

    assert review.stale_uncertain_count == 1
    # The tripwire asserts an *escalation*. A read-only review creates none.
    state = acceptance._read_run(db, run_id)
    assert state["status"] == "running"
    assert state["ended_at"] is None
    assert _escalations(db, run_id) == []
