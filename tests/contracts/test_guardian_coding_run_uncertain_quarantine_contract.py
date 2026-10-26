"""Guardian coding run — operator-authorized uncertain quarantine contract.

The campaign has proved durable ownership, a claim-scoped heartbeat, and
claim-fenced terminal persistence. What it has **not** proved is that an
operator can dispose of an *unresolved* execution safely: a run whose owning
worker stopped reporting, whose outcome is unknown, and whose external side
effects are unknown.

This contract proves the guarded disposition:

- the operator's authority is **verified**, never asserted,
- the canonical evidence is **revalidated inside the transaction**,
- the run's transition to ``escalated`` and its open escalation evidence
  **commit together**,
- a terminal decision that committed first is never overwritten,
- a duplicate request is idempotent,
- and the disposition grants no retry, requeue, credential, or ownership
  authority.

It is a persistence-and-authorization contract. It does not implement startup
reconciliation, and it does not make a stale heartbeat a death oracle.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from guardian.agents.store import AgentStore
from guardian.core.guardian_delegation_service import (
    GuardianDelegationError,
    GuardianDelegationService,
)
from guardian.core.guardian_dispatch import CodingRunLivenessEvidence
from guardian.db.models import AgentEscalation, AgentRun

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

_INSTANCE_A = "cwi_quarantine_worker_a"
_INSTANCE_B = "cwi_quarantine_worker_b"
_CLAIM_A = "cwc_quarantine_claim_a"
_CLAIM_B = "cwc_quarantine_claim_b"

_REASON_CODE = "guardian_dispatch_liveness_unproven"


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
def _operator_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The established Guardian operator authority: the configured API key."""
    monkeypatch.setenv("GUARDIAN_API_KEY", acceptance._SERVICE_KEY)
    yield


def _accepted_run(
    db: Any,
    *,
    worker_instance_id: str = _INSTANCE_A,
    claim_id: str = _CLAIM_A,
) -> Any:
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


def _service(db: Any) -> GuardianDelegationService:
    service = GuardianDelegationService()
    service.configure_db(db)
    return service


def _account_user_id(db: Any, run_id: str) -> str:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return str(row.account_origin_user_id or "")


def _stale_heartbeat(db: Any, run_id: str, *, seconds: float) -> None:
    """Write a heartbeat that is older than the observation horizon.

    The run's start is moved with it: ``started_at`` is stamped by the
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


def _second_run(db: Any) -> Any:
    """Dispatch and accept a second run in the already-seeded account.

    The acceptance harness seeds the account on every dispatch, so a second
    run in one account is dispatched through the same service entrypoint on a
    second thread of that account.
    """
    from guardian.core.guardian_delegation_service import GuardianDelegationService
    from guardian.db.models import ChatMessage, ChatThread, Project
    from guardian.queue.redis_queue import dequeue_coding_execution
    from guardian.tasks.types import CodingExecutionTask

    with db.get_session() as session:
        project = session.query(Project).filter_by(user_id="account-1").one()
        thread = ChatThread(
            user_id="account-1",
            title="Second source thread",
            summary="",
            project_id=project.id,
        )
        session.add(thread)
        session.flush()
        message = ChatMessage(
            thread_id=thread.id,
            user_id="account-1",
            role="user",
            content="Also patch the other path.",
            kind="chat",
            extra_meta={},
        )
        session.add(message)
        session.commit()
        seeded = {
            "user_id": "account-1",
            "project_id": project.id,
            "thread_id": thread.id,
            "source_message_id": message.id,
        }

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
        from guardian.db.models import AgentDeployment, AgentRun

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
    task = CodingExecutionTask.from_dict(payload)
    assert (
        acceptance._claim(
            db,
            task,
            worker_instance_id=_INSTANCE_B,
            claim_id=_CLAIM_B,
        )
        == acceptance._ACCEPTED
    )
    return task


def _quarantine(
    db: Any,
    task: Any,
    *,
    operator_api_key: str | None = None,
    operator_session_token: str | None = None,
    worker_instance_id: str = _INSTANCE_A,
    claim_id: str = _CLAIM_A,
    account_user_id: str | None = None,
    reason: str = "operator reviewed the unresolved execution",
) -> dict[str, Any]:
    """Invoke the guarded disposition through the operator boundary."""
    service = _service(db)
    return service.quarantine_uncertain_coding_run(
        run_id=str(task.run_id),
        operator_api_key=(
            operator_api_key
            if operator_api_key is not None
            else acceptance._SERVICE_KEY
        ),
        operator_session_token=operator_session_token,
        expected_worker_instance_id=worker_instance_id,
        expected_claim_id=claim_id,
        expected_account_user_id=(
            account_user_id
            if account_user_id is not None
            else _account_user_id(db, str(task.run_id))
        ),
        reason=reason,
    )


def _run_state(db: Any, run_id: str) -> dict[str, Any]:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return {
            "status": row.status,
            "instance_id": row.coding_worker_instance_id,
            "claim_id": row.coding_worker_claim_id,
            "ended_at": row.ended_at,
            "error": row.error,
        }


def _escalations(db: Any, run_id: str) -> list[Any]:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return (
            session.query(AgentEscalation)
            .filter_by(run_id=row.id)
            .order_by(AgentEscalation.id.asc())
            .all()
        )


# ---------------------------------------------------------------------------
# 1-5: the operator authority boundary.
# ---------------------------------------------------------------------------


def test_a_verified_operator_decision_is_required(db: Any) -> None:
    """The disposition needs a verified operator."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    receipt = _quarantine(db, task)

    assert receipt["outcome"] == "quarantined"
    assert receipt["operator_actor"] in {
        "operator-api-key",
        "operator-session",
    }


def test_an_untrusted_authorization_boolean_is_insufficient(db: Any) -> None:
    """A caller-supplied boolean cannot substitute for authorization."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    service = _service(db)
    with pytest.raises(TypeError):
        # The disposition takes no boolean that could be asserted instead of
        # proven.
        service.quarantine_uncertain_coding_run(
            run_id=str(task.run_id),
            operator_authorized=True,  # type: ignore[call-arg]
            expected_worker_instance_id=_INSTANCE_A,
            expected_claim_id=_CLAIM_A,
            expected_account_user_id=_account_user_id(db, str(task.run_id)),
            reason="asserted authority",
        )

    # Nothing was disposed of.
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_missing_operator_identity_is_rejected(db: Any) -> None:
    """No credential at all is not operator authority."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task, operator_api_key="")

    assert excinfo.value.status_code == 401
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_insufficient_operator_permission_is_rejected(db: Any) -> None:
    """An account credential is never reinterpreted as operator material."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task, operator_api_key="not-the-operator-key")

    assert excinfo.value.status_code == 401
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_cross_account_disposition_is_rejected(db: Any) -> None:
    """A decision aimed at one account cannot disposition another run."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task, account_user_id="some-other-account")

    assert excinfo.value.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


# ---------------------------------------------------------------------------
# 6-12: eligibility.
# ---------------------------------------------------------------------------


def test_a_valid_running_run_is_eligible_for_review(db: Any) -> None:
    """An accepted run with stale evidence can be dispositioned."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    receipt = _quarantine(db, task)

    assert receipt["outcome"] == "quarantined"
    assert receipt["status"] == "escalated"


def test_stale_heartbeat_alone_does_not_cause_quarantine(db: Any) -> None:
    """Staleness is evidence, not a trigger: the operator decides."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    # The run is stale, and nothing has been done to it yet.
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []

    # The disposition happens only because the operator asked for it.
    receipt = _quarantine(db, task)
    assert receipt["outcome"] == "quarantined"


def test_a_fresh_heartbeat_prevents_quarantine(db: Any) -> None:
    """A worker that is still reporting is not an abandoned run."""
    task = _accepted_run(db)

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task)

    assert excinfo.value.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_canonical_evidence_is_rechecked_inside_the_transaction(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A heartbeat that turns fresh after the review refuses the disposition.

    The operator's review used a snapshot; the commit must not trust it.
    """
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    store = AgentStore(db=db)
    original = store.quarantine_coding_run_as_uncertain

    def _renew_then_dispose(**kwargs: Any) -> dict[str, Any]:
        # The worker resumes reporting between the review and the commit.
        with db.get_session() as session:
            row = session.query(AgentRun).filter_by(
                run_id=str(kwargs["run_id"])
            ).one()
            row.coding_worker_last_heartbeat_at = datetime.now(timezone.utc)
            session.commit()
        return original(**kwargs)

    monkeypatch.setattr(
        store, "quarantine_coding_run_as_uncertain", _renew_then_dispose
    )
    service = _service(db)
    service.agent_store = store

    with pytest.raises(GuardianDelegationError) as excinfo:
        service.quarantine_uncertain_coding_run(
            run_id=str(task.run_id),
            operator_api_key=acceptance._SERVICE_KEY,
            expected_worker_instance_id=_INSTANCE_A,
            expected_claim_id=_CLAIM_A,
            expected_account_user_id=_account_user_id(db, str(task.run_id)),
            reason="reviewed before the worker resumed",
        )

    assert excinfo.value.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_the_expected_worker_and_claim_are_required(db: Any) -> None:
    """Only the expected owner may be dispositioned."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task, worker_instance_id=_INSTANCE_B)

    assert excinfo.value.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_missing_worker_claim_is_rejected(db: Any) -> None:
    """A claim-less decision cannot disposition an owned run."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task, claim_id="")

    assert excinfo.value.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_a_historical_ownership_unknown_run_is_rejected(db: Any) -> None:
    """A historical run without ownership is not a bounded candidate."""
    task = _accepted_run(db)
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_instance_id = None
        row.coding_worker_claim_id = None
        row.coding_worker_last_heartbeat_at = None
        session.commit()

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task)

    assert excinfo.value.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


# ---------------------------------------------------------------------------
# 13-16: the atomic disposition and its evidence.
# ---------------------------------------------------------------------------


def test_the_run_transitions_to_escalated_atomically(db: Any) -> None:
    """The canonical run carries the escalated disposition."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    state = _run_state(db, str(task.run_id))
    assert state["status"] == "escalated"
    assert state["ended_at"] is not None


def test_the_escalation_record_is_created_atomically(db: Any) -> None:
    """Exactly one open escalation record explains the disposition."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    escalations = _escalations(db, str(task.run_id))
    assert len(escalations) == 1
    escalation = escalations[0]
    assert escalation.status == "open"
    assert escalation.reason_code == _REASON_CODE
    assert escalation.severity in {"soft", "hard"}
    assert escalation.payload_json["execution_result"] == "unknown"


def test_the_original_claim_is_preserved(db: Any) -> None:
    """The disposition never reassigns the run."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    state = _run_state(db, str(task.run_id))
    assert state["instance_id"] == _INSTANCE_A
    assert state["claim_id"] == _CLAIM_A
    escalation = _escalations(db, str(task.run_id))[0]
    assert escalation.payload_json["original_worker_instance_id"] == _INSTANCE_A
    assert escalation.payload_json["original_worker_claim_id"] == _CLAIM_A


def test_the_operator_evidence_is_durably_recorded(db: Any) -> None:
    """The escalation records who decided, and on what evidence."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task, reason="operator investigated the stale worker")

    escalation = _escalations(db, str(task.run_id))[0]
    payload = escalation.payload_json
    assert payload["operator_actor"] in {
        "operator-api-key",
        "operator-session",
    }
    assert payload["operator_decision_provenance"]["decision"] == (
        "quarantine_uncertain_coding_run"
    )
    assert payload["liveness_evidence"] == (
        CodingRunLivenessEvidence.STALE_UNCERTAIN.value
    )
    assert payload["original_execution_status"] == "running"
    assert payload["final_disposition"] == "escalated"
    assert payload["run_id"] == str(task.run_id)
    assert payload["last_heartbeat_at"] is not None
    assert payload["observed_at"] is not None
    # No secret or transcript content may enter the evidence.
    text = json.dumps(payload).lower()
    assert acceptance._SERVICE_KEY not in text
    for marker in ("api_key", "sk-", "bearer ", "authorization", "prompt"):
        assert marker not in text


# ---------------------------------------------------------------------------
# 17-18: idempotency and concurrency.
# ---------------------------------------------------------------------------


def test_a_duplicate_quarantine_is_idempotent(db: Any) -> None:
    """A repeated authorized request observes the existing disposition."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    first = _quarantine(db, task)
    ended_at = _run_state(db, str(task.run_id))["ended_at"]
    second = _quarantine(db, task)

    assert first["outcome"] == "quarantined"
    assert second["outcome"] == "already_disposed"
    assert len(_escalations(db, str(task.run_id))) == 1
    assert _run_state(db, str(task.run_id))["ended_at"] == ended_at
    assert _run_state(db, str(task.run_id))["status"] == "escalated"


def test_concurrent_quarantine_calls_produce_one_disposition(db: Any) -> None:
    """Only one disposition can win."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    barrier = threading.Barrier(2)

    def _attempt() -> str:
        barrier.wait(timeout=30)
        try:
            return str(_quarantine(db, task).get("outcome") or "")
        except GuardianDelegationError as exc:
            return f"error:{exc.status_code}"

    outcomes: list[str] = []
    threads = [
        threading.Thread(target=lambda: outcomes.append(_attempt()))
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert len(_escalations(db, str(task.run_id))) == 1
    assert _run_state(db, str(task.run_id))["status"] == "escalated"
    # The loser observes the committed disposition read-only; it never creates
    # a second one.
    assert sorted(outcomes) == sorted(["already_disposed", "quarantined"])


# ---------------------------------------------------------------------------
# 19-22: the races with terminalization.
# ---------------------------------------------------------------------------


def test_a_terminal_decision_that_wins_blocks_the_quarantine(db: Any) -> None:
    """A terminal result committed first is never overwritten."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    # The worker finished the run first.
    AgentStore(db=db).update_run_status(
        run_id=str(task.run_id),
        status="succeeded",
    )

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task)

    assert excinfo.value.status_code == 409
    assert _run_state(db, str(task.run_id))["status"] == "succeeded"
    assert _escalations(db, str(task.run_id)) == []


def test_quarantine_winning_blocks_a_late_terminal_success(db: Any) -> None:
    """An escalated run cannot be reopened by a late worker."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    # The stale worker now tries to finalize with its old claim.
    store = AgentStore(db=db)
    outcome = store.finalize_claimed_coding_result(
        run_id=str(task.run_id),
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
        coding_task_id=str(task.coding_task_id),
        attempt_id=str(task.attempt_id),
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status="succeeded",
        result_summary="A late result.",
    )

    assert outcome["terminal_accepted"] is False
    assert outcome["terminal_claim"] == "terminal_rejected"
    assert _run_state(db, str(task.run_id))["status"] == "escalated"
    assert len(_escalations(db, str(task.run_id))) == 1
    assert acceptance._artifact_count(db, str(task.run_id)) == 0
    assert acceptance._coding_result_message_count(db, task.thread_id) == 0


@pytest.mark.parametrize("terminal_status", ["succeeded", "failed", "canceled"])
def test_existing_terminal_runs_remain_unchanged(
    db: Any,
    terminal_status: str,
) -> None:
    """A run that already finished is not dispositioned."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)
    AgentStore(db=db).update_run_status(
        run_id=str(task.run_id),
        status=terminal_status,
    )

    with pytest.raises(GuardianDelegationError):
        _quarantine(db, task)

    assert _run_state(db, str(task.run_id))["status"] == terminal_status
    assert _escalations(db, str(task.run_id)) == []


def test_an_existing_escalated_run_remains_unchanged(db: Any) -> None:
    """A run already escalated by another authority is not rewritten."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    # A different disposition already exists.
    AgentStore(db=db).add_escalation(
        run_id=str(task.run_id),
        step_index=None,
        severity="hard",
        reason_code="some_other_reason",
        reason="A different disposition.",
        preserved_worktree=False,
        payload={"operator_actor": "someone-else"},
    )
    AgentStore(db=db).update_run_status(
        run_id=str(task.run_id),
        status="escalated",
    )

    with pytest.raises(GuardianDelegationError) as excinfo:
        _quarantine(db, task)

    assert excinfo.value.status_code == 409
    escalations = _escalations(db, str(task.run_id))
    assert len(escalations) == 1
    assert escalations[0].reason_code == "some_other_reason"


# ---------------------------------------------------------------------------
# 23-27: nothing else happens.
# ---------------------------------------------------------------------------


def test_no_source_thread_result_is_fabricated(db: Any) -> None:
    """A quarantine delivers no result."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    assert acceptance._coding_result_message_count(db, task.thread_id) == 0


def test_no_coding_result_artifact_is_fabricated(db: Any) -> None:
    """A quarantine creates no coding-result artifact."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    assert acceptance._artifact_count(db, str(task.run_id)) == 0


def test_no_queue_mutation_occurs(db: Any) -> None:
    """A quarantine enqueues and dequeues nothing."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    assert dequeue_coding_execution(block=False) is None


def test_no_credential_lease_is_issued(db: Any) -> None:
    """A quarantine issues no credential lease."""
    from guardian.db.models import CodingWorktreeLease

    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    _quarantine(db, task)

    with db.get_session() as session:
        assert session.query(CodingWorktreeLease).count() == 0


def test_no_replacement_execution_attempt_is_created(db: Any) -> None:
    """A quarantine creates no new attempt."""
    from guardian.db.models import AgentRunAttempt

    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    with db.get_session() as session:
        before = session.query(AgentRunAttempt).count()

    _quarantine(db, task)

    with db.get_session() as session:
        assert session.query(AgentRunAttempt).count() == before


# ---------------------------------------------------------------------------
# 28-30: failures and compatibility.
# ---------------------------------------------------------------------------


def test_a_transaction_failure_rolls_back_cleanly(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure during the escalation insert leaves nothing behind."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    store = AgentStore(db=db)

    def _failing_insert(**kwargs: Any) -> Any:
        raise RuntimeError("injected escalation failure")

    monkeypatch.setattr(store, "_insert_escalation", _failing_insert)
    service = _service(db)
    service.agent_store = store

    with pytest.raises(RuntimeError):
        service.quarantine_uncertain_coding_run(
            run_id=str(task.run_id),
            operator_api_key=acceptance._SERVICE_KEY,
            expected_worker_instance_id=_INSTANCE_A,
            expected_claim_id=_CLAIM_A,
            expected_account_user_id=_account_user_id(db, str(task.run_id)),
            reason="the insert will fail",
        )

    monkeypatch.undo()
    # No partial escalation, and no escalated run without its evidence.
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_persistence_unavailability_fails_closed(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unreachable persistence is never permission to quarantine."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    store = AgentStore(db=db)
    monkeypatch.setattr(store, "_has_db", lambda: False)
    service = _service(db)
    service.agent_store = store

    with pytest.raises(GuardianDelegationError) as excinfo:
        service.quarantine_uncertain_coding_run(
            run_id=str(task.run_id),
            operator_api_key=acceptance._SERVICE_KEY,
            expected_worker_instance_id=_INSTANCE_A,
            expected_claim_id=_CLAIM_A,
            expected_account_user_id=_account_user_id(db, str(task.run_id)),
            reason="no persistence",
        )

    assert excinfo.value.status_code == 503
    assert _run_state(db, str(task.run_id))["status"] == "running"
    assert _escalations(db, str(task.run_id)) == []


def test_the_existing_terminal_fencing_contract_remains_valid(db: Any) -> None:
    """The claim-fenced terminal boundary is untouched by this slice."""
    task = _accepted_run(db)

    store = AgentStore(db=db)
    accepted = store.finalize_claimed_coding_result(
        run_id=str(task.run_id),
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
        coding_task_id=str(task.coding_task_id),
        attempt_id=str(task.attempt_id),
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status="succeeded",
        result_summary="Still fenced.",
    )
    assert accepted["terminal_accepted"] is True

    # A different claim cannot finalize the same run.
    rejected = store.finalize_claimed_coding_result(
        run_id=str(task.run_id),
        worker_instance_id=_INSTANCE_B,
        claim_id=_CLAIM_B,
        coding_task_id=str(task.coding_task_id),
        attempt_id=str(task.attempt_id),
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status="succeeded",
        result_summary="Not the owner.",
    )
    assert rejected["terminal_accepted"] is False


# ---------------------------------------------------------------------------
# The active-peer and operator-isolation guarantees.
# ---------------------------------------------------------------------------


def test_an_active_peer_worker_is_unaffected(db: Any) -> None:
    """Disposing one run never touches the peer's run."""
    first = _accepted_run(db)
    peer_task = _second_run(db)
    _stale_heartbeat(db, str(first.run_id), seconds=600)

    peer_before = _run_state(db, str(peer_task.run_id))
    peer_heartbeat_before = peer_before["status"]

    _quarantine(db, first)

    peer_after = _run_state(db, str(peer_task.run_id))
    assert peer_after["status"] == peer_heartbeat_before == "running"
    assert peer_after["instance_id"] == _INSTANCE_B
    assert peer_after["claim_id"] == _CLAIM_B
    assert _escalations(db, str(peer_task.run_id)) == []


def test_the_operator_actor_is_distinct_from_the_actors_of_the_run(
    db: Any,
) -> None:
    """The operator is not the account owner, the worker, or the claim."""
    task = _accepted_run(db)
    _stale_heartbeat(db, str(task.run_id), seconds=600)

    receipt = _quarantine(db, task)

    actor = str(receipt["operator_actor"])
    assert actor not in {_INSTANCE_A, _CLAIM_A}
    assert actor != _account_user_id(db, str(task.run_id))
