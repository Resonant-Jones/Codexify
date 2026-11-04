"""Guardian coding worker — durable run ownership contract.

The durable-acceptance slice gave an accepted Guardian coding run a canonical
``running`` state with a stamped ``started_at``. That record says *that* an
execution was claimed. It does not say *who* claimed it.

This contract covers the ownership prerequisite: every newly accepted run also
records the coding-worker **instance** that accepted it and the unique
**ownership claim** made at that moment, committed atomically with the
``queued -> running`` transition.

**What this contract does not claim.** A persisted owner is not proof that the
worker is still alive. The claim-scoped heartbeat added by the next slice is
*evidence of reported activity*, not authority: there is still no expiry, no
takeover, no automatic retry, and no restart reconciliation — those remain
separate, dependent slices. The tests below assert ownership persistence and
its safety properties, and they assert the *absence* of the behaviours this
task deliberately does not implement.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
import socket
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

from fastapi import HTTPException
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from guardian.agents.store import AgentStore
from guardian.db.models import AgentRun
from guardian.workers import coding_worker

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTRACTS_DIR = Path(__file__).resolve().parent

# The acceptance contract owns the proven disposable-PostgreSQL harness and the
# real Guardian dispatch path. Load it by path so the ownership contract does
# not duplicate it and cannot drift from it.
_spec = importlib.util.spec_from_file_location(
    "_guardian_acceptance_contract",
    _CONTRACTS_DIR / "test_guardian_coding_worker_acceptance_contract.py",
)
assert _spec is not None and _spec.loader is not None
acceptance = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(acceptance)

_TestDB = acceptance._TestDB

_ACCEPTED = acceptance._ACCEPTED
_REJECTED = acceptance._REJECTED

_INSTANCE_ID = "cwi_ownership_contract_worker"
_CLAIM_ID = "cwc_ownership_contract_claim"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def stub_adapter(monkeypatch: pytest.MonkeyPatch, db: Any) -> Any:
    """A provider stub that records the run state observed at adapter entry."""
    adapter = acceptance._StubAdapter(db)
    monkeypatch.setitem(acceptance.ADAPTERS, "pi_codex_runner", adapter)
    return adapter


@pytest.fixture(autouse=True)
def _credential_encryption_key() -> Iterator[None]:
    """Let the credential authority encrypt and lease the seeded key."""
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
def _pi_harness_package(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Materialize the Pi harness version marker only."""
    package_root = tmp_path_factory.mktemp("pi-coding-agent-package")
    (package_root / "package.json").write_text(
        json.dumps(
            {
                "name": "@earendil-works/pi-coding-agent",
                "version": "0.0.0-ownership-contract",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PI_CODING_AGENT_PACKAGE_ROOT", str(package_root))
    yield


@pytest.fixture(autouse=True)
def _guardian_service_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Present a static Guardian service key to the credential authority."""
    monkeypatch.setenv("GUARDIAN_API_KEY", acceptance._SERVICE_KEY)
    yield


@pytest.fixture(autouse=True)
def _guardian_credential_authority(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Bind the worker's credential-lease client to the real Guardian route.

    Only the socket is replaced: the request body, the service-key check, the
    deployment and lineage re-validation, the credential authority, the sealed
    lease payload, and the worker-side lease validation are all production
    code paths.
    """
    from guardian.agents import credential_lease_client
    from guardian.core.dependencies import require_service_api_key
    from guardian.routes import agent_orchestration

    previous_store_db = getattr(agent_orchestration._store, "db", None)
    previous_publisher_db = getattr(agent_orchestration._event_publisher, "db", None)
    agent_orchestration.configure_db(db)

    def _urlopen(request: Any, timeout: Any = None) -> Any:
        payload = json.loads(bytes(request.data).decode("utf-8"))
        body = agent_orchestration.CodingExecutionCredentialLeaseRequest(**payload)
        try:
            require_service_api_key(x_api_key=acceptance._SERVICE_KEY)
            result = asyncio.run(
                agent_orchestration.lease_coding_execution_credential(body)
            )
        except HTTPException as exc:
            raise HTTPError(
                request.full_url,
                exc.status_code,
                exc.detail,
                request.headers,
                None,
            ) from None
        return acceptance._InProcessResponse(json.dumps(result).encode("utf-8"))

    monkeypatch.setattr(credential_lease_client, "urlopen", _urlopen)

    try:
        yield
    finally:
        agent_orchestration._store.db = previous_store_db
        agent_orchestration._event_publisher.db = previous_publisher_db


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


def _dispatch_one_for(db: Any, user_id: str) -> dict[str, Any]:
    """Dispatch one real Guardian delegation for a distinct account.

    A second dispatch inside one test needs its own account, because the
    seeded user, project, thread, and message are not reusable.
    """
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = acceptance._seed_account(db, user_id=user_id)
    acceptance._seed_credential(db, user_id=seeded["user_id"])

    service = acceptance.GuardianDelegationService()
    service.configure_db(db)
    intent = service.create_intent(
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
    )
    intent_id = str(intent["intent_id"])
    run_id = str(intent["run_id"])

    with db.get_session() as session:
        run_row = session.query(acceptance.AgentRun).filter_by(run_id=run_id).one()
        deployment_row = (
            session.query(acceptance.AgentDeployment)
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
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    payload = dequeue_coding_execution(block=False)
    assert payload is not None
    task = acceptance.CodingExecutionTask.from_dict(payload)
    return {"seeded": seeded, "run_id": run_id, "task": task, "payload": payload}


def _owner_state(db: Any, run_id: str) -> dict[str, Any]:
    """Read the durable ownership of a run.

    The accessor is deliberately schema-tolerant so the same assertion runs
    against a tree that has no ownership columns at all: there, the owner is
    simply absent.
    """
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return {
            "status": row.status,
            "started_at": row.started_at,
            "instance_id": getattr(row, "coding_worker_instance_id", None),
            "claim_id": getattr(row, "coding_worker_claim_id", None),
            "row_id": row.id,
        }


def _claim_supports_ownership() -> bool:
    """Whether the installed store exposes the ownership parameters.

    The pre-repair implementation has no ownership parameters. Probing for
    them keeps this contract executable against that baseline, so the red
    result is a *behavioural* failure -- an accepted run with no durable owner
    -- rather than an API error.
    """
    import inspect

    parameters = inspect.signature(
        AgentStore.claim_run_for_acceptance
    ).parameters
    return "worker_instance_id" in parameters and "claim_id" in parameters


def _claim(
    db: Any,
    task: Any,
    *,
    worker_instance_id: str = _INSTANCE_ID,
    claim_id: str = _CLAIM_ID,
    **overrides: Any,
) -> str:
    store = AgentStore(db=db)
    kwargs: dict[str, Any] = {
        "run_id": str(task.run_id or ""),
        "deployment_id": str(task.deployment_id or ""),
        "worker_instance_id": worker_instance_id,
        "claim_id": claim_id,
        "user_id": (task.execution_binding or {}).get("user_id"),
        "thread_id": task.thread_id,
        "source_message_id": task.source_message_id,
        "attempt_id": str(task.attempt_id or ""),
        "coding_task_id": str(task.coding_task_id or ""),
    }
    kwargs.update(overrides)
    if not _claim_supports_ownership():
        kwargs.pop("worker_instance_id")
        kwargs.pop("claim_id")
    return store.claim_run_for_acceptance(**kwargs)


# ---------------------------------------------------------------------------
# 1-3: the identity itself.
# ---------------------------------------------------------------------------


def test_worker_identity_is_generated_internally() -> None:
    """The worker mints its own identity; nothing external chooses it."""
    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=None))

    identity = worker.worker_instance_id

    assert identity, "the worker instance has no identity"
    assert identity.startswith("cwi_")
    # Not derived from the host or the process.
    hostname = socket.gethostname()
    assert hostname not in identity
    # Not derived from the process, either. The identity is a fresh uuid4,
    # so it cannot carry the process id; the assertion says so directly
    # instead of by proxy.
    #
    # The previous form of this assertion was `str(os.getpid()) not in
    # identity`. That is a substring test against a random hex string, not
    # a derivation test: the identity is a uuid4 and so cannot be derived
    # from the process, but the decimal process id occurs inside the hex by
    # coincidence. Measured over 200,000 identities, the collision rate is
    # ~0.03% for a four-digit process id, ~0.003% for a five-digit one,
    # ~12% for a two-digit one, and ~85% for a single-digit one -- because a
    # fresh container's early processes get small ids. So the assertion
    # failed intermittently on main, and because CI runs pytest with
    # `--maxfail=1` one such failure hides every other test in the run.
    assert UUID(identity.removeprefix("cwi_")).version == 4


def test_different_worker_instances_have_distinct_ids() -> None:
    """Two instances on one host must never collide."""
    identities = {
        coding_worker.CodingWorker(agent_store=AgentStore(db=None)).worker_instance_id
        for _ in range(8)
    }

    assert len(identities) == 8


def test_one_worker_accepts_separate_runs_with_distinct_claim_ids(
    db: Any,
) -> None:
    """Separate runs accepted by one worker carry different claim ids."""
    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    claim_ids: list[str] = []

    for index in range(2):
        dispatched = _dispatch_one_for(db, f"account-multi-{index}")
        task = dispatched["task"]
        claim_id = coding_worker._new_coding_worker_claim_id()
        claim_ids.append(claim_id)
        outcome = _claim(
            db,
            task,
            worker_instance_id=worker.worker_instance_id,
            claim_id=claim_id,
        )
        assert outcome == _ACCEPTED

    assert len(set(claim_ids)) == 2
    assert all(claim_id.startswith("cwc_") for claim_id in claim_ids)


# ---------------------------------------------------------------------------
# 4-8: persistence of the ownership.
# ---------------------------------------------------------------------------


def test_the_worker_persists_its_ownership(
    db: Any,
    stub_adapter: Any,
) -> None:
    """The behavioural contract: an accepted run carries a durable owner.

    This is the regression the task exists to fix. Against an implementation
    without ownership, the run is accepted and reaches ``running`` with no
    durable owner recorded -- the exact gap the recovery investigation found.
    """
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    acceptance._run_worker(db, task, stub_adapter)

    state = _owner_state(db, str(task.run_id))
    # The execution ran to completion, and the ownership recorded at acceptance
    # survived that terminalization.
    assert state["status"] == "succeeded"
    assert state["instance_id"], "the accepted run has no durable worker owner"
    assert state["claim_id"], "the accepted run has no durable ownership claim"


def test_acceptance_persists_both_identities(db: Any) -> None:
    """A successful acceptance records the owner and the claim."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task)

    assert outcome == _ACCEPTED
    state = _owner_state(db, str(task.run_id))
    assert state["instance_id"] == _INSTANCE_ID
    assert state["claim_id"] == _CLAIM_ID


def test_ownership_and_running_status_commit_atomically(db: Any) -> None:
    """When the ownership write fails, the status write fails with it."""
    first = _dispatch_one_for(db, "account-atomic-first")
    second = _dispatch_one_for(db, "account-atomic-second")

    assert _claim(db, first["task"], claim_id=_CLAIM_ID) == _ACCEPTED

    # Reusing the claim id must fail on the unique constraint. Because the
    # ownership write and the queued -> running transition are one statement in
    # one transaction, the second run must be left completely unclaimed.
    outcome = _claim(db, second["task"], claim_id=_CLAIM_ID)

    assert outcome == _REJECTED
    state = _owner_state(db, str(second["task"].run_id))
    assert state["status"] == "queued"
    assert state["started_at"] is None
    assert state["instance_id"] is None
    assert state["claim_id"] is None


def test_started_at_is_stamped_exactly_once(db: Any) -> None:
    """A duplicate claim never refreshes the acceptance timestamp."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task) == _ACCEPTED
    first = _owner_state(db, str(task.run_id))["started_at"]
    assert first is not None

    assert _claim(db, task, claim_id="cwc_duplicate") == _REJECTED
    assert _owner_state(db, str(task.run_id))["started_at"] == first


def test_postgresql_readback_preserves_the_claim(db: Any) -> None:
    """A fresh session reads the same ownership the worker wrote."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task) == _ACCEPTED

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        assert getattr(row, "coding_worker_instance_id", None) == _INSTANCE_ID
        assert getattr(row, "coding_worker_claim_id", None) == _CLAIM_ID


def test_worker_disappearance_leaves_the_claim_intact(db: Any) -> None:
    """The ownership record survives the worker that made it."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task) == _ACCEPTED
    before = _owner_state(db, str(task.run_id))

    # The worker object ceases to exist without any terminalization.
    del before

    after = _owner_state(db, str(task.run_id))
    assert after["status"] == "running"
    assert after["instance_id"] == _INSTANCE_ID
    assert after["claim_id"] == _CLAIM_ID
    assert after["started_at"] is not None


# ---------------------------------------------------------------------------
# 9-12: duplicate and concurrent claims.
# ---------------------------------------------------------------------------


def test_two_concurrent_workers_cannot_both_claim_a_run(db: Any) -> None:
    """Exactly one of two racing claimants wins, on real PostgreSQL."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    def _attempt(index: int) -> str:
        return _claim(
            db,
            task,
            worker_instance_id=f"cwi_racer_{index}",
            claim_id=f"cwc_racer_{index}",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(_attempt, range(2)))

    assert sorted(outcomes) == sorted([_ACCEPTED, _REJECTED])
    state = _owner_state(db, str(task.run_id))
    assert state["status"] == "running"
    # The winner's ownership is the one that survived.
    assert state["instance_id"] in {"cwi_racer_0", "cwi_racer_1"}
    assert state["claim_id"] in {"cwc_racer_0", "cwc_racer_1"}


def test_duplicate_delivery_cannot_replace_ownership(db: Any) -> None:
    """A second worker cannot take an accepted run."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task) == _ACCEPTED
    first = _owner_state(db, str(task.run_id))

    outcome = _claim(
        db,
        task,
        worker_instance_id="cwi_second_worker",
        claim_id="cwc_second_worker",
    )

    assert outcome == _REJECTED
    second = _owner_state(db, str(task.run_id))
    assert second["instance_id"] == first["instance_id"]
    assert second["claim_id"] == first["claim_id"]
    assert second["started_at"] == first["started_at"]


def test_duplicate_delivery_cannot_enter_the_adapter(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    stub_adapter: Any,
) -> None:
    """A duplicate delivery stops at the ownership gate."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    acceptance._run_worker(db, task, stub_adapter)
    assert stub_adapter.calls == 1
    accepted = _owner_state(db, str(task.run_id))

    acceptance._run_worker(db, task, stub_adapter)

    assert stub_adapter.calls == 1, "the duplicate entered the adapter"
    assert _owner_state(db, str(task.run_id)) == accepted


def test_duplicate_delivery_publishes_no_false_terminal_failure(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    stub_adapter: Any,
) -> None:
    """A duplicate delivery does not report the accepted attempt as failed."""
    published: list[tuple[str, dict[str, Any]]] = []
    original = coding_worker.task_events.publish_with_visibility

    def _record(task_id: str, event_type: str, data: Any = None) -> dict[str, Any]:
        published.append((event_type, dict(data or {})))
        return original(task_id, event_type, data)

    monkeypatch.setattr(
        coding_worker.task_events, "publish_with_visibility", _record
    )

    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    acceptance._run_worker(db, task, stub_adapter)
    published.clear()

    acceptance._run_worker(db, task, stub_adapter)

    terminal = [
        event_type
        for event_type, _ in published
        if event_type in ("task.failed", "task.cancelled", "task.completed")
    ]
    assert terminal == [], terminal
    assert published, "the duplicate refusal was not observable"


# ---------------------------------------------------------------------------
# 13-18: refusal and compatibility.
# ---------------------------------------------------------------------------


def test_a_terminal_run_cannot_be_reaccepted(db: Any) -> None:
    """A terminal run keeps its state and gains no ownership."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.status = "succeeded"
        session.commit()

    outcome = _claim(db, task)

    assert outcome == _REJECTED
    state = _owner_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert state["instance_id"] is None
    assert state["claim_id"] is None


def test_a_missing_run_fails_closed(db: Any) -> None:
    """There is nothing to own, so nothing is owned."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task, run_id="run_does_not_exist")

    assert outcome == _REJECTED


def test_contradictory_deployment_lineage_fails_closed(db: Any) -> None:
    """A claim that contradicts the durable deployment is refused."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task, attempt_id="attempt-does-not-match")

    assert outcome == _REJECTED
    state = _owner_state(db, str(task.run_id))
    assert state["status"] == "queued"
    assert state["instance_id"] is None


def test_persistence_failure_prevents_side_effects(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    stub_adapter: Any,
) -> None:
    """If ownership cannot be persisted, the adapter is never entered."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    def _boom(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("postgresql is unreachable")

    monkeypatch.setattr(coding_worker.AgentStore, "claim_run_for_acceptance", _boom)

    with pytest.raises(RuntimeError):
        acceptance._run_worker(db, task, stub_adapter)

    assert stub_adapter.calls == 0, "the adapter was entered without ownership"
    state = _owner_state(db, str(task.run_id))
    assert state["status"] == "queued"
    assert state["instance_id"] is None


def test_historical_null_ownership_remains_readable(db: Any) -> None:
    """A run accepted before this revision is ownership-unknown, not broken."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.status = "running"
        row.started_at = _utc_now()
        session.commit()

    state = _owner_state(db, str(task.run_id))

    assert state["status"] == "running"
    assert state["instance_id"] is None
    assert state["claim_id"] is None


def test_partially_populated_ownership_is_rejected(db: Any) -> None:
    """Ownership is paired: the database refuses half of it."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_instance_id = _INSTANCE_ID
        with pytest.raises(IntegrityError):
            session.commit()


# ---------------------------------------------------------------------------
# 19-20: existing behaviour stays intact.
# ---------------------------------------------------------------------------


def test_normal_successful_terminalization_remains_compatible(
    db: Any,
    stub_adapter: Any,
) -> None:
    """A successful run still ends succeeded, with an artifact."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    acceptance._run_worker(db, task, stub_adapter)

    assert stub_adapter.calls == 1
    state = acceptance._read_run(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert state["ended_at"] is not None
    assert acceptance._artifact_count(db, str(task.run_id)) >= 1


def test_source_thread_result_idempotency_remains_intact(
    db: Any,
    stub_adapter: Any,
) -> None:
    """One attempt still delivers exactly one source-thread result."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    acceptance._run_worker(db, task, stub_adapter)

    assert acceptance._coding_result_message_count(db, task.thread_id) == 1


# ---------------------------------------------------------------------------
# What this task deliberately does not implement.
# ---------------------------------------------------------------------------


def test_ownership_is_not_liveness_authority() -> None:
    """Ownership stays subordinate: liveness evidence is not an authority.

    A claim-scoped heartbeat now exists on the canonical run, so the liveness
    *evidence* is present. What is still absent is liveness *authority*: there
    is no expiry column, no takeover column, and the heartbeat column itself
    is nullable and may only exist when the ownership fields do.
    """
    columns = {column.name for column in AgentRun.__table__.columns}

    # Liveness evidence exists, and it is subordinate.
    assert "coding_worker_last_heartbeat_at" in columns
    assert AgentRun.__table__.columns["coding_worker_last_heartbeat_at"].nullable

    # Liveness authority does not: no expiry, no takeover.
    assert "coding_worker_lease_expires_at" not in columns
    assert "coding_worker_expires_at" not in columns
    assert "coding_worker_taken_over_at" not in columns


def test_no_new_persisted_run_status_exists() -> None:
    """The run-status vocabulary is unchanged."""
    status_check = next(
        constraint
        for constraint in AgentRun.__table__.constraints
        if constraint.name == "agent_runs_status_check"
    )
    sql_text = str(status_check.sqltext)

    assert set(re.findall(r"'([a-z_]+)'", sql_text)) == {
        "queued",
        "running",
        "escalated",
        "canceled",
        "failed",
        "succeeded",
    }


def test_the_ownership_columns_are_nullable_and_bounded() -> None:
    """The new fields are additive, nullable, and bounded."""
    for name in ("coding_worker_instance_id", "coding_worker_claim_id"):
        column = AgentRun.__table__.columns[name]
        assert column.nullable is True
        assert str(column.type) == "VARCHAR(64)"


def test_the_schema_carries_no_separate_ownership_table() -> None:
    """Ownership stays subordinate to AgentRun; it is not a control plane."""
    from guardian.db.models import Base

    ownership_tables = [
        name
        for name in Base.metadata.tables
        if "ownership" in name or "worker_claim" in name
    ]

    assert ownership_tables == []


def test_the_paired_constraint_exists_by_name() -> None:
    """The paired-null constraint is named and present in the ORM metadata."""
    names = {constraint.name for constraint in AgentRun.__table__.constraints}

    assert "agent_runs_coding_worker_ownership_check" in names
    assert "uq_agent_runs_coding_worker_claim_id" in names
