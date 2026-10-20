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

from dataclasses import dataclass, replace
from datetime import datetime, timezone
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
