"""Guardian delegation dispatch: durable state and a recovery contract that
does not over-claim.

The Guardian Delegation Loop dispatches a delegated coding task by minting an
execution binding, resolving an enforceable permission posture, persisting
both against the deployment, and enqueueing one coding-execution task.

The recovery contract here is deliberately conservative, because the queue
does not support the guarantees that are easy to assume.

**Four layers, four different guarantees.** They are not the same thing, and a
guarantee on one says nothing about another:

1. *Task delivery* — **at-most-once, and lossy.** The queue is
   ``LPUSH`` + destructive ``BRPOP``/``RPOP`` with no ack, no pending list,
   and no requeue (``guardian/queue/redis_queue.py``). A task is removed
   before the worker processes it, so a worker crash loses it.
2. *Attempt execution* — **unguaranteed.** A ``BRPOP``ped task may still be
   executing. Absence of progress is not proof of loss.
3. *Execution effects* — **not idempotent.** The adapter runs a subprocess with
   write access and may commit. Two concurrent attempts duplicate filesystem
   writes and commits.
4. *Result delivery* — **idempotent** per (intent, run): a duplicate delivery
   recovers without a duplicate source-thread message.

**Therefore: no exactly-once execution claim is made anywhere in this module,
and automated re-dispatch is refused.**

**Uncertain is not lost.** A worker that stopped heartbeating is not a
dead worker. It may be between phases, blocked on a subprocess, or in a long
validation loop. The recovery posture is therefore
**quarantine-and-escalate**: an attempt whose liveness is unproven is marked
*uncertain* and escalated, never silently re-dispatched.

**Fencing is absent.** There is no fencing token, epoch, or monotonic guard in
this runtime, so a superseded attempt's writes cannot be rejected. Without
fencing, re-dispatch is safe against cross-contamination (the worktree lease
refuses two active leases sharing a path or branch) but **not** against
duplicate logical effects. Automated re-dispatch is therefore refused while
fencing is absent; only an explicit operator authorization may re-drive an
attempt, and even then the retry must mint a **new attempt** with a new
binding and a freshly issued credential lease.

This mirrors the existing chat recovery idiom, which also refuses to execute
during recovery: *"recovery never executes the task"* and *"a task's terminal
envelope, not the lock safety margin or worker heartbeat, decides recovery"*
(``guardian/core/chat_completion_service.py``).

See ADR-094, ADR-077, and
``docs/architecture/guardian-delegation-loop-contract.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class GuardianDispatchState(str, Enum):
    """Durable dispatch lifecycle for one delegated attempt."""

    #: The attempt is fully specified and authorized, but nothing is queued.
    PREPARED = "prepared"
    #: The task was accepted by the queue and carries a task id.
    DISPATCHED = "dispatched"
    #: A worker claimed the attempt and is executing it.
    EXECUTING = "executing"
    #: The attempt reached a durable terminal result.
    COMPLETED = "completed"
    #: The attempt failed durably.
    FAILED = "failed"
    #: Liveness is unproven. The attempt may still be executing.
    UNCERTAIN = "uncertain"
    #: Recovery refused to re-drive the attempt. An operator must decide.
    QUARANTINED = "quarantined"
    #: The attempt was cancelled by a human.
    CANCELLED = "cancelled"


#: States from which no further automated action is taken.
GUARDIAN_DISPATCH_TERMINAL_STATES = frozenset(
    {
        GuardianDispatchState.COMPLETED.value,
        GuardianDispatchState.FAILED.value,
        GuardianDispatchState.CANCELLED.value,
    }
)

#: The production cadence of the coding worker's claim-scoped heartbeat, in
#: seconds. It mirrors
#: ``guardian.workers.coding_worker.CODING_RUN_HEARTBEAT_INTERVAL_SECONDS``,
#: which reads the same environment override. The value is restated here
#: rather than imported so that ``guardian.core`` never depends on a worker
#: module; the contract asserts that the two agree.
CODING_RUN_HEARTBEAT_INTERVAL_SECONDS = 15

#: The observational staleness horizon for one coding run's liveness
#: evidence: ``max(60, 3 * production_heartbeat_interval_seconds)``.
#:
#: This is an **observation threshold**, not an execution-lease expiry and not
#: a death oracle. Crossing it means "recent liveness evidence is missing",
#: which is a statement about *evidence*, not about the worker process. No
#: retry, escalation, cancellation, or takeover follows from it.
CODING_RUN_LIVENESS_STALE_AFTER_SECONDS = max(
    60,
    3 * CODING_RUN_HEARTBEAT_INTERVAL_SECONDS,
)

#: How far a heartbeat may sit in the future before the canonical record is
#: treated as inconsistent rather than merely recent.
CODING_RUN_LIVENESS_FUTURE_TOLERANCE_SECONDS = 5

#: How much two timestamps may contradict each other before the record is
#: treated as inconsistent.
#:
#: The run's timeline spans two clocks: ``started_at`` is stamped by the
#: application, while the heartbeat and ``ended_at`` are stamped by the
#: database. Those clocks are not the same clock, and they differ by a few
#: milliseconds -- so a heartbeat written in the same transaction as
#: ``started_at`` legitimately sits a hair *before* it. A comparison that
#: tolerates only that much is not a comparison of the run's timeline.
#:
#: Comparisons that span one clock -- the heartbeat against the observation
#: instant, and the heartbeat against ``ended_at`` -- are exact and are not
#: given this tolerance.
CODING_RUN_LIVENESS_CLOCK_SKEW_TOLERANCE_SECONDS = 5


class CodingRunLivenessEvidence(str, Enum):
    """What the canonical record shows about one coding run's liveness.

    These are *observations*, not decisions. None of them authorises a retry,
    a requeue, a process termination, a credential revocation, an ownership
    transfer, or an escalation.
    """

    #: The run was never durably accepted by a worker.
    NEVER_ACCEPTED = "never_accepted"
    #: The recorded claim renewed liveness inside the observation horizon.
    RECENTLY_OBSERVED = "recently_observed"
    #: The recorded claim's last renewal is older than the horizon.
    STALE_UNCERTAIN = "stale_uncertain"
    #: The record carries too little evidence to classify liveness at all.
    MISSING_EVIDENCE = "missing_evidence"
    #: The run already carries a canonical terminal disposition.
    ALREADY_RESOLVED = "already_resolved"
    #: An authoritative escalation disposition already exists.
    ALREADY_ESCALATED = "already_escalated"
    #: The canonical record is internally inconsistent and needs inspection.
    INCONSISTENT = "inconsistent"
    #: No observation could be made: the record is absent or unreachable.
    UNOBSERVABLE = "unobservable"


#: Canonical reason codes for a coding run's liveness classification.
CODING_RUN_LIVENESS_REASON_NOT_ACCEPTED = "guardian_coding_run_not_accepted"
CODING_RUN_LIVENESS_REASON_RECENT = "guardian_coding_run_liveness_recent"
CODING_RUN_LIVENESS_REASON_STALE = "guardian_coding_run_liveness_stale"
CODING_RUN_LIVENESS_REASON_MISSING = (
    "guardian_coding_run_liveness_evidence_missing"
)
CODING_RUN_LIVENESS_REASON_RESOLVED = "guardian_coding_run_already_resolved"
CODING_RUN_LIVENESS_REASON_ESCALATED = (
    "guardian_coding_run_already_escalated"
)
CODING_RUN_LIVENESS_REASON_INCONSISTENT = (
    "guardian_coding_run_liveness_inconsistent"
)
CODING_RUN_LIVENESS_REASON_UNOBSERVABLE = (
    "guardian_coding_run_liveness_unobservable"
)


class GuardianDispatchError(RuntimeError):
    """Dispatch could not proceed, or recovery refused to proceed.

    ``code`` is a stable, machine-readable reason.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


@dataclass(frozen=True)
class GuardianDispatchRecord:
    """Durable, queryable state for one delegated attempt."""

    intent_id: str
    deployment_id: str
    run_id: str
    attempt_id: str
    coding_task_id: str
    state: str
    #: Queue task id, present once the task has been accepted by the queue.
    task_id: str | None = None
    #: Worktree lease id, when the attempt is leased to a worktree.
    lease_id: str | None = None
    #: Last observed liveness signal for the attempt.
    last_heartbeat_at: datetime | None = None
    #: When the attempt's liveness can no longer be established.
    lease_expires_at: datetime | None = None
    #: Why the attempt is uncertain or quarantined.
    reason_code: str | None = None
    #: Whether an operator explicitly authorized recovery of this attempt.
    operator_authorized: bool = False
    #: How many times this attempt has been dispatched.
    dispatch_count: int = 0
    dispatched_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "deployment_id": self.deployment_id,
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "coding_task_id": self.coding_task_id,
            "state": self.state,
            "task_id": self.task_id,
            "lease_id": self.lease_id,
            "last_heartbeat_at": (
                self.last_heartbeat_at.isoformat()
                if self.last_heartbeat_at is not None
                else None
            ),
            "lease_expires_at": (
                self.lease_expires_at.isoformat()
                if self.lease_expires_at is not None
                else None
            ),
            "reason_code": self.reason_code,
            "operator_authorized": self.operator_authorized,
            "dispatch_count": self.dispatch_count,
            "dispatched_at": (
                self.dispatched_at.isoformat()
                if self.dispatched_at is not None
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat() if self.updated_at is not None else None
            ),
        }

    @property
    def is_terminal(self) -> bool:
        return self.state in GUARDIAN_DISPATCH_TERMINAL_STATES


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_dispatch_record(
    *,
    intent_id: str,
    deployment_id: str,
    run_id: str,
    attempt_id: str,
    coding_task_id: str,
    lease_id: str | None = None,
) -> GuardianDispatchRecord:
    """Build the initial ``prepared`` dispatch record for one attempt."""
    if not str(intent_id or "").strip():
        raise GuardianDispatchError("guardian_dispatch_intent_missing")
    if not str(deployment_id or "").strip():
        raise GuardianDispatchError("guardian_dispatch_deployment_missing")
    if not str(run_id or "").strip():
        raise GuardianDispatchError("guardian_dispatch_run_missing")
    if not str(attempt_id or "").strip():
        raise GuardianDispatchError("guardian_dispatch_attempt_missing")
    if not str(coding_task_id or "").strip():
        raise GuardianDispatchError("guardian_dispatch_coding_task_missing")
    now = _now()
    return GuardianDispatchRecord(
        intent_id=str(intent_id),
        deployment_id=str(deployment_id),
        run_id=str(run_id),
        attempt_id=str(attempt_id),
        coding_task_id=str(coding_task_id),
        state=GuardianDispatchState.PREPARED.value,
        lease_id=lease_id,
        dispatch_count=0,
        updated_at=now,
    )


def mark_dispatched(
    record: GuardianDispatchRecord,
    *,
    task_id: str,
) -> GuardianDispatchRecord:
    """Record that the queue accepted the task.

    The queue task id is the dispatch receipt. It is durable evidence that the
    task was enqueued, and it is *not* evidence that the task was consumed.
    """
    if not str(task_id or "").strip():
        raise GuardianDispatchError("guardian_dispatch_task_id_missing")
    now = _now()
    return replace(
        record,
        state=GuardianDispatchState.DISPATCHED.value,
        task_id=str(task_id),
        dispatch_count=record.dispatch_count + 1,
        dispatched_at=now,
        updated_at=now,
    )


def observe_liveness(
    record: GuardianDispatchRecord,
    *,
    last_heartbeat_at: datetime | None = None,
    lease_expires_at: datetime | None = None,
) -> GuardianDispatchRecord:
    """Record an observed liveness signal for the attempt."""
    now = _now()
    return replace(
        record,
        state=(
            GuardianDispatchState.EXECUTING.value
            if record.state
            in {
                GuardianDispatchState.DISPATCHED.value,
                GuardianDispatchState.EXECUTING.value,
            }
            else record.state
        ),
        last_heartbeat_at=last_heartbeat_at or record.last_heartbeat_at,
        lease_expires_at=lease_expires_at or record.lease_expires_at,
        updated_at=now,
    )


def classify_dispatch_health(
    record: GuardianDispatchRecord,
    *,
    now: datetime | None = None,
) -> GuardianDispatchRecord:
    """Classify an attempt's liveness without assuming it is lost.

    The rules, in order:

    - A terminal attempt is left alone.
    - An attempt with **no liveness evidence at all** is left alone. A
      freshly dispatched attempt has no heartbeat yet and may not have a
      lease; that is not staleness, and absence of evidence is not evidence
      of loss.
    - An attempt whose lease is still within its expiry is **healthy** — even
      if no progress has been observed. A worker between phases or blocked on
      a subprocess looks exactly like this.
    - An attempt whose lease has expired *and* whose heartbeat is stale is
      **uncertain**, not lost. The attempt may still be executing.
    - Nothing is ever inferred from absence of a record.
    """
    if record.is_terminal:
        return record

    moment = now or _now()

    # No liveness evidence yet: the attempt may simply not have been claimed.
    if record.last_heartbeat_at is None and record.lease_expires_at is None:
        return record

    # A live lease is proof of liveness, whatever the heartbeat says.
    if (
        record.lease_expires_at is not None
        and record.lease_expires_at > moment
    ):
        return record

    # Evidence of staleness: the lease has expired, or the heartbeat is old
    # enough that liveness can no longer be established.
    reason = "guardian_dispatch_liveness_unproven"
    return replace(
        record,
        state=GuardianDispatchState.UNCERTAIN.value,
        reason_code=reason,
        updated_at=moment,
    )


def recover_dispatch(
    record: GuardianDispatchRecord,
    *,
    operator_authorized: bool = False,
    fencing_available: bool = False,
) -> GuardianDispatchRecord:
    """Decide what recovery does with an uncertain attempt.

    **Automated re-dispatch is refused unless fencing exists.** Without
    fencing, a superseded attempt's writes cannot be rejected, and execution
    effects are not idempotent, so re-dispatching could duplicate filesystem
    writes and commits. Isolation alone (the worktree lease refusing two
    active leases on the same path or branch) bounds cross-contamination but
    not duplication.

    With no operator authorization and no fencing, the attempt is
    **quarantined**: durable, inspectable, and escalated to a human. It is
    never silently re-driven, and it is never declared lost.
    """
    if record.is_terminal:
        return record

    if fencing_available and operator_authorized:
        # A recovery attempt is a *new* attempt: it needs a new attempt id, a
        # new binding, and a freshly issued credential lease. The record is
        # handed back marked prepared so the caller mints those.
        now = _now()
        return replace(
            record,
            state=GuardianDispatchState.PREPARED.value,
            reason_code=None,
            operator_authorized=True,
            updated_at=now,
        )

    reason = (
        "guardian_dispatch_recovery_requires_fencing"
        if not fencing_available
        else "guardian_dispatch_recovery_requires_operator_authorization"
    )
    now = _now()
    return replace(
        record,
        state=GuardianDispatchState.QUARANTINED.value,
        reason_code=reason,
        operator_authorized=operator_authorized,
        updated_at=now,
    )


@dataclass(frozen=True)
class CodingRunLivenessVerdict:
    """A read-only classification of one coding run's liveness evidence.

    The verdict is **evidence for a later Guardian-owned decision**. It does
    not make that decision: it never retries, requeues, terminates a process,
    revokes a credential, replaces a binding, transfers ownership, or escalates
    a run.
    """

    #: The canonical run this verdict describes.
    run_id: str | None
    #: The canonical deployment the run belongs to.
    deployment_id: str | None
    #: The canonical run status observed.
    status: str | None
    #: The dispatch verdict, reusing the accepted vocabulary. ``None`` when no
    #: canonical verdict can be reached (the run could not be observed).
    state: str | None
    #: What the canonical record shows.
    evidence: str
    #: Why the evidence is what it is, or why it is uncertain.
    reason_code: str | None
    #: The worker instance that owns the run, when the record carries one.
    worker_instance_id: str | None
    #: The ownership claim, when the record carries one.
    claim_id: str | None
    #: The last claim-scoped heartbeat renewal.
    last_heartbeat_at: datetime | None
    #: When the evidence was observed, from the database clock.
    observed_at: datetime | None
    #: How old the heartbeat was at the observation instant.
    heartbeat_age_seconds: float | None
    #: The observation horizon this verdict was measured against.
    stale_after_seconds: int
    #: Whether the record carried usable liveness evidence at all.
    evidence_available: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "deployment_id": self.deployment_id,
            "status": self.status,
            "state": self.state,
            "evidence": self.evidence,
            "reason_code": self.reason_code,
            "worker_instance_id": self.worker_instance_id,
            "claim_id": self.claim_id,
            "last_heartbeat_at": (
                self.last_heartbeat_at.isoformat()
                if self.last_heartbeat_at is not None
                else None
            ),
            "observed_at": (
                self.observed_at.isoformat()
                if self.observed_at is not None
                else None
            ),
            "heartbeat_age_seconds": self.heartbeat_age_seconds,
            "stale_after_seconds": self.stale_after_seconds,
            "evidence_available": self.evidence_available,
        }


def _as_utc(value: Any) -> datetime | None:
    """Normalize a timestamp to an aware UTC instant, or ``None``."""
    if value is None:
        return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def classify_coding_run_liveness(
    snapshot: Mapping[str, Any] | None,
    *,
    stale_after_seconds: int = CODING_RUN_LIVENESS_STALE_AFTER_SECONDS,
) -> CodingRunLivenessVerdict:
    """Classify one coding run's canonical liveness evidence.

    The classification is deterministic and read-only. It reads the canonical
    run status, the recorded ownership identities, and the claim-scoped
    heartbeat, and it compares the heartbeat against the **database** clock
    recorded with the observation.

    The distinctions it draws, in the order they are decided:

    - **Never accepted** -- ``queued`` with no accepted claim. The execution was
      never durably accepted. This is not an abandoned execution.
    - **Already resolved** -- ``succeeded``, ``failed`` or ``canceled``. The run
      already has a canonical disposition; it is never reconsidered as
      abandoned because its heartbeat is old.
    - **Already escalated** -- ``escalated``. An authoritative disposition
      already exists and is never duplicated by a classification.
    - **Inconsistent** -- the record contradicts itself: a queued run with
      accepted ownership, a partial ownership pair, impossible timestamp
      ordering, or a heartbeat in the future. It requires inspection, and it
      is never repaired automatically.
    - **Missing evidence** -- a running run without a usable owner, claim, or
      heartbeat. Insufficient evidence; nothing is inferred about whether the
      work started or whether side effects occurred.
    - **Recently observed** -- a running run whose claim renewed liveness
      inside the horizon. This is evidence of recent activity, *not* proof
      that a process currently exists.
    - **Stale and uncertain** -- a running run whose last renewal is older
      than the horizon. Recent liveness evidence is missing; the execution
      outcome is uncertain. This is **not** a determination that the worker
      died.

    A stale classification never authorises a retry, an escalation, a
    cancellation, an ownership transfer, or a credential revocation. It is
    evidence for a Guardian-owned decision that this module does not make.
    """
    horizon = max(0, int(stale_after_seconds))

    if not isinstance(snapshot, Mapping) or not snapshot:
        return CodingRunLivenessVerdict(
            run_id=None,
            deployment_id=None,
            status=None,
            state=None,
            evidence=CodingRunLivenessEvidence.UNOBSERVABLE.value,
            reason_code=CODING_RUN_LIVENESS_REASON_UNOBSERVABLE,
            worker_instance_id=None,
            claim_id=None,
            last_heartbeat_at=None,
            observed_at=None,
            heartbeat_age_seconds=None,
            stale_after_seconds=horizon,
            evidence_available=False,
        )

    run_id = str(snapshot.get("run_id") or "") or None
    deployment_id = str(snapshot.get("deployment_id") or "") or None
    status = str(snapshot.get("status") or "").strip().lower() or None
    worker_instance_id = (
        str(snapshot.get("coding_worker_instance_id") or "").strip() or None
    )
    claim_id = str(snapshot.get("coding_worker_claim_id") or "").strip() or None
    heartbeat = _as_utc(snapshot.get("coding_worker_last_heartbeat_at"))
    started_at = _as_utc(snapshot.get("started_at"))
    ended_at = _as_utc(snapshot.get("ended_at"))
    observed_at = _as_utc(snapshot.get("observed_at"))

    age: float | None = None
    if heartbeat is not None and observed_at is not None:
        age = (observed_at - heartbeat).total_seconds()
    # A comparison that spans the application clock and the database clock
    # tolerates their difference; one that spans a single clock does not.
    skew = timedelta(
        seconds=CODING_RUN_LIVENESS_CLOCK_SKEW_TOLERANCE_SECONDS
    )

    def _verdict(
        *,
        state: str | None,
        evidence: CodingRunLivenessEvidence,
        reason_code: str | None,
        evidence_available: bool,
    ) -> CodingRunLivenessVerdict:
        return CodingRunLivenessVerdict(
            run_id=run_id,
            deployment_id=deployment_id,
            status=status,
            state=state,
            evidence=evidence.value,
            reason_code=reason_code,
            worker_instance_id=worker_instance_id,
            claim_id=claim_id,
            last_heartbeat_at=heartbeat,
            observed_at=observed_at,
            heartbeat_age_seconds=age,
            stale_after_seconds=horizon,
            evidence_available=evidence_available,
        )

    # The record must not contradict itself before anything else is decided.
    if worker_instance_id is not None and claim_id is None:
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )
    if claim_id is not None and worker_instance_id is None:
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )
    if status == "queued" and worker_instance_id is not None:
        # A queued run with accepted ownership contradicts the acceptance
        # contract, which transitions queued -> running atomically.
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )
    if (
        started_at is not None
        and ended_at is not None
        and ended_at < started_at - skew
    ):
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )
    if (
        started_at is not None
        and heartbeat is not None
        and heartbeat < started_at - skew
    ):
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )
    if (
        ended_at is not None
        and heartbeat is not None
        and heartbeat > ended_at
    ):
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )
    if age is not None and age < -CODING_RUN_LIVENESS_FUTURE_TOLERANCE_SECONDS:
        # The heartbeat is in the future: the record cannot be taken at face
        # value.
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )

    if status == "queued":
        # Never durably accepted. This is not an abandoned execution.
        return _verdict(
            state=GuardianDispatchState.DISPATCHED.value,
            evidence=CodingRunLivenessEvidence.NEVER_ACCEPTED,
            reason_code=CODING_RUN_LIVENESS_REASON_NOT_ACCEPTED,
            evidence_available=False,
        )

    if status in {"succeeded", "failed", "canceled", "cancelled"}:
        resolved_state = {
            "succeeded": GuardianDispatchState.COMPLETED.value,
            "failed": GuardianDispatchState.FAILED.value,
            "canceled": GuardianDispatchState.CANCELLED.value,
            "cancelled": GuardianDispatchState.CANCELLED.value,
        }[status]
        return _verdict(
            state=resolved_state,
            evidence=CodingRunLivenessEvidence.ALREADY_RESOLVED,
            reason_code=CODING_RUN_LIVENESS_REASON_RESOLVED,
            evidence_available=heartbeat is not None,
        )

    if status == "escalated":
        # An authoritative disposition already exists. A classification never
        # creates another one.
        return _verdict(
            state=GuardianDispatchState.QUARANTINED.value,
            evidence=CodingRunLivenessEvidence.ALREADY_ESCALATED,
            reason_code=CODING_RUN_LIVENESS_REASON_ESCALATED,
            evidence_available=heartbeat is not None,
        )

    if status != "running":
        # A status the liveness contract does not interpret.
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.INCONSISTENT,
            reason_code=CODING_RUN_LIVENESS_REASON_INCONSISTENT,
            evidence_available=False,
        )

    if worker_instance_id is None or claim_id is None or heartbeat is None:
        # Insufficient evidence: a running run with no usable owner, claim, or
        # heartbeat. Nothing is inferred about whether work started, or whether
        # external side effects occurred.
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.MISSING_EVIDENCE,
            reason_code=CODING_RUN_LIVENESS_REASON_MISSING,
            evidence_available=False,
        )

    if age is None:
        # The observation instant was not comparable with the heartbeat.
        return _verdict(
            state=GuardianDispatchState.UNCERTAIN.value,
            evidence=CodingRunLivenessEvidence.MISSING_EVIDENCE,
            reason_code=CODING_RUN_LIVENESS_REASON_MISSING,
            evidence_available=False,
        )

    if age <= horizon:
        # Evidence of recent activity -- not proof that a process exists.
        return _verdict(
            state=GuardianDispatchState.EXECUTING.value,
            evidence=CodingRunLivenessEvidence.RECENTLY_OBSERVED,
            reason_code=CODING_RUN_LIVENESS_REASON_RECENT,
            evidence_available=True,
        )

    # Recent liveness evidence is missing. The outcome is uncertain: the
    # worker may be between phases, blocked on a subprocess, or gone.
    return _verdict(
        state=GuardianDispatchState.UNCERTAIN.value,
        evidence=CodingRunLivenessEvidence.STALE_UNCERTAIN,
        reason_code=CODING_RUN_LIVENESS_REASON_STALE,
        evidence_available=True,
    )


def assert_dispatch_ready(
    record: GuardianDispatchRecord,
    *,
    execution_binding: dict[str, Any],
    permission_policy: dict[str, Any],
) -> None:
    """Assert an attempt is authorized and specified before it is enqueued.

    A dispatch is refused unless the attempt carries a binding and a posture.
    A missing or empty binding is the exact condition the coding worker
    rejects at dequeue, so it is caught here instead — before anything is
    queued.
    """
    if not isinstance(execution_binding, dict) or not execution_binding:
        raise GuardianDispatchError("guardian_dispatch_binding_missing")
    if not str(execution_binding.get("binding_id") or "").strip():
        raise GuardianDispatchError("guardian_dispatch_binding_invalid")
    if not isinstance(permission_policy, dict) or not permission_policy:
        raise GuardianDispatchError("guardian_dispatch_posture_missing")
    if permission_policy.get("allow_write") and not permission_policy.get(
        "allowed_paths"
    ):
        raise GuardianDispatchError("guardian_dispatch_posture_write_scope_missing")
    if record.state != GuardianDispatchState.PREPARED.value:
        raise GuardianDispatchError(
            f"guardian_dispatch_state_{record.state}"
        )
    # The binding must describe this exact attempt.
    if str(execution_binding.get("attempt_id") or "") != record.attempt_id:
        raise GuardianDispatchError("guardian_dispatch_binding_attempt_mismatch")
    if (
        str(execution_binding.get("coding_task_id") or "")
        != record.coding_task_id
    ):
        raise GuardianDispatchError("guardian_dispatch_binding_task_mismatch")
