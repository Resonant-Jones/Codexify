"""Guardian coding worker — claim-scoped heartbeat contract.

Durable worker ownership says *which* worker instance claimed a run. It does
not say whether that worker is still working. This contract covers the missing
half: a per-run heartbeat, reported by the recorded owner while the execution
is in flight, renewed only by the worker instance and ownership claim that the
database currently records.

**A heartbeat is evidence, not authority.** It never permits execution, retry,
or recovery, and it is never inferred from an empty queue, an elapsed
timestamp, or a missing row. The renewal itself is the database's own
conditional answer, not an optimistic application-level guess.
"""

from __future__ import annotations

import importlib.util
import json
import os
import threading
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from guardian.agents.store import AgentStore
from guardian.db.models import AgentRun
from guardian.workers import coding_worker

try:  # The baseline has no heartbeat contract yet.
    from guardian.agents.store import (
        RUN_HEARTBEAT_NOT_ELIGIBLE,
        RUN_HEARTBEAT_RENEWED,
        RUN_HEARTBEAT_UNAVAILABLE,
    )
except ImportError:  # pragma: no cover - exercised only against the baseline
    RUN_HEARTBEAT_RENEWED = "renewed"
    RUN_HEARTBEAT_NOT_ELIGIBLE = "not_eligible"
    RUN_HEARTBEAT_UNAVAILABLE = "unavailable"

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

_INSTANCE_A = "cwi_heartbeat_contract_worker_a"
_INSTANCE_B = "cwi_heartbeat_contract_worker_b"
_CLAIM_A = "cwc_heartbeat_contract_claim_a"
_CLAIM_B = "cwc_heartbeat_contract_claim_b"

#: A fast cadence so the contract observes renewal without long sleeps. The
#: production cadence is documented on the worker.
_FAST_INTERVAL = 0.2


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


@pytest.fixture
def _fast_heartbeat(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(
        coding_worker,
        "CODING_RUN_HEARTBEAT_INTERVAL_SECONDS",
        _FAST_INTERVAL,
        raising=False,
    )
    yield


@pytest.fixture(autouse=True)
def _credential_authority(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Bind the worker's credential-lease client to the real Guardian route."""
    import asyncio
    from urllib.error import HTTPError

    from fastapi import HTTPException

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


@pytest.fixture(autouse=True)
def _pi_harness_package(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    package_root = tmp_path_factory.mktemp("pi-coding-agent-package")
    (package_root / "package.json").write_text(
        json.dumps(
            {
                "name": "@earendil-works/pi-coding-agent",
                "version": "0.0.0-heartbeat-contract",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PI_CODING_AGENT_PACKAGE_ROOT", str(package_root))
    yield


@pytest.fixture(autouse=True)
def _service_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GUARDIAN_API_KEY", acceptance._SERVICE_KEY)
    yield


@pytest.fixture(autouse=True)
def _encryption_key() -> Iterator[None]:
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


def _row(db: Any, run_id: str) -> Any:
    with db.get_session() as session:
        return (
            session.query(AgentRun)
            .filter_by(run_id=run_id)
            .one()
        )


def _heartbeat_state(db: Any, run_id: str) -> dict[str, Any]:
    with db.get_session() as session:
        row = (
            session.query(AgentRun)
            .filter_by(run_id=run_id)
            .one()
        )
        return {
            "status": row.status,
            "started_at": row.started_at,
            "instance_id": row.coding_worker_instance_id,
            "claim_id": row.coding_worker_claim_id,
            # Tolerant of a schema that has no heartbeat column yet, so the
            # contract reports the missing evidence rather than an error.
            "heartbeat_at": getattr(
                row, "coding_worker_last_heartbeat_at", None
            ),
            "ended_at": row.ended_at,
        }


def _claim(
    db: Any,
    task: Any,
    *,
    worker_instance_id: str = _INSTANCE_A,
    claim_id: str = _CLAIM_A,
    **overrides: Any,
) -> str:
    import inspect

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
    if "worker_instance_id" not in inspect.signature(
        store.claim_run_for_acceptance
    ).parameters:
        # The baseline accepts a run without any ownership identity. Keep the
        # contract executable against it so the red is a *behavioural* one:
        # the run is accepted and persisted, and the heartbeat is missing.
        kwargs.pop("worker_instance_id")
        kwargs.pop("claim_id")
    return store.claim_run_for_acceptance(**kwargs)


def _renew(
    db: Any,
    run_id: str,
    *,
    worker_instance_id: str = _INSTANCE_A,
    claim_id: str = _CLAIM_A,
) -> str:
    store = AgentStore(db=db)
    renew = getattr(store, "renew_coding_run_heartbeat", None)
    assert renew is not None, (
        "the agent store has no claim-scoped heartbeat renewal operation"
    )
    return renew(
        run_id=run_id,
        worker_instance_id=worker_instance_id,
        claim_id=claim_id,
    )


class _BlockingAdapter:
    """An adapter that blocks until the test releases it."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def execute_authorized(self, *_args: Any, **_kwargs: Any) -> Any:
        from guardian.agents.adapters.base import AgentRunEnvelope

        self.calls += 1
        self.entered.set()
        # Block until the test lets the execution continue, so the heartbeat
        # has a live execution to report against.
        self.release.wait(timeout=30)
        return AgentRunEnvelope(
            status="ok",
            summary="blocking adapter ok",
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
        )


def _heartbeat_advanced(db: Any, run_id: str, before: Any) -> bool:
    """Whether the run's heartbeat moved forward since ``before``."""
    current = _heartbeat_state(db, run_id)["heartbeat_at"]
    if current is None:
        return False
    return before is None or current > before


def _wait_until(predicate: Any, timeout: float = 10.0) -> bool:
    """Wait for a condition without sleeping on a fixed wall-clock guess."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


# ---------------------------------------------------------------------------
# 1-5: the initial heartbeat is written with the acceptance.
# ---------------------------------------------------------------------------


def test_initial_heartbeat_is_written_with_successful_acceptance(
    db: Any,
) -> None:
    """Acceptance records the first liveness observation atomically."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task)

    assert outcome == acceptance._ACCEPTED
    state = _heartbeat_state(db, str(task.run_id))
    assert state["status"] == "running"
    assert state["heartbeat_at"] is not None


def test_initial_heartbeat_is_absent_after_failed_acceptance(db: Any) -> None:
    """A refused acceptance leaves no liveness evidence behind."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task, attempt_id="attempt-does-not-match")

    assert outcome == acceptance._REJECTED
    state = _heartbeat_state(db, str(task.run_id))
    assert state["status"] == "queued"
    assert state["heartbeat_at"] is None
    assert state["instance_id"] is None
    assert state["claim_id"] is None


def test_worker_identity_is_preserved_with_the_heartbeat(db: Any) -> None:
    """The heartbeat never displaces the recorded owner."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task) == acceptance._ACCEPTED

    state = _heartbeat_state(db, str(task.run_id))
    assert state["instance_id"] == _INSTANCE_A


def test_claim_identity_is_preserved_with_the_heartbeat(db: Any) -> None:
    """The heartbeat never displaces the recorded claim."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task) == acceptance._ACCEPTED

    state = _heartbeat_state(db, str(task.run_id))
    assert state["claim_id"] == _CLAIM_A


def test_heartbeat_timestamp_comes_from_the_database_clock(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The heartbeat uses PostgreSQL's clock, not the worker's wall clock."""
    import guardian.agents.store as store_module

    monkeypatch.setattr(
        store_module,
        "_utc_now",
        lambda: datetime(1999, 1, 1, tzinfo=timezone.utc),
    )

    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task) == acceptance._ACCEPTED

    state = _heartbeat_state(db, str(task.run_id))
    # started_at comes from the patched Python clock ...
    assert state["started_at"].year == 1999
    # ... while the heartbeat comes from the database clock.
    assert state["heartbeat_at"].year != 1999


# ---------------------------------------------------------------------------
# 6-14: the renewal contract.
# ---------------------------------------------------------------------------


def test_valid_owner_renewal_succeeds(db: Any) -> None:
    """The recorded owner may renew its own run's heartbeat."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED

    outcome = _renew(db, str(task.run_id))

    assert outcome == RUN_HEARTBEAT_RENEWED


def test_renewal_advances_the_heartbeat(db: Any) -> None:
    """A successful renewal moves the liveness observation forward."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED
    first = _heartbeat_state(db, str(task.run_id))["heartbeat_at"]

    outcome = _renew(db, str(task.run_id))

    assert outcome == RUN_HEARTBEAT_RENEWED
    second = _heartbeat_state(db, str(task.run_id))["heartbeat_at"]
    assert second is not None
    assert second >= first


def test_incorrect_worker_id_is_rejected(db: Any) -> None:
    """A different worker instance cannot renew someone else's run."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED
    before = _heartbeat_state(db, str(task.run_id))["heartbeat_at"]

    outcome = _renew(db, str(task.run_id), worker_instance_id=_INSTANCE_B)

    assert outcome == RUN_HEARTBEAT_NOT_ELIGIBLE
    after = _heartbeat_state(db, str(task.run_id))["heartbeat_at"]
    assert after == before
    assert _heartbeat_state(db, str(task.run_id))["instance_id"] == _INSTANCE_A


def test_incorrect_claim_id_is_rejected(db: Any) -> None:
    """A different claim cannot renew the run, even for the same worker."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED
    before = _heartbeat_state(db, str(task.run_id))["heartbeat_at"]

    outcome = _renew(db, str(task.run_id), claim_id=_CLAIM_B)

    assert outcome == RUN_HEARTBEAT_NOT_ELIGIBLE
    assert _heartbeat_state(db, str(task.run_id))["heartbeat_at"] == before
    assert _heartbeat_state(db, str(task.run_id))["claim_id"] == _CLAIM_A


def test_missing_claim_is_rejected(db: Any) -> None:
    """A renewal without a claim identity is refused."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED

    outcome = _renew(db, str(task.run_id), claim_id="")

    assert outcome == RUN_HEARTBEAT_NOT_ELIGIBLE


def test_missing_run_is_rejected(db: Any) -> None:
    """There is nothing to renew for a run that does not exist."""
    outcome = _renew(db, "run_does_not_exist")

    assert outcome == RUN_HEARTBEAT_NOT_ELIGIBLE


def test_terminal_run_is_rejected(db: Any) -> None:
    """A completed run cannot be renewed back into liveness."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.status = "succeeded"
        row.ended_at = datetime.now(timezone.utc)
        session.commit()
    before = _heartbeat_state(db, str(task.run_id))["heartbeat_at"]

    outcome = _renew(db, str(task.run_id))

    assert outcome == RUN_HEARTBEAT_NOT_ELIGIBLE
    assert _heartbeat_state(db, str(task.run_id))["heartbeat_at"] == before
    assert _heartbeat_state(db, str(task.run_id))["status"] == "succeeded"


def test_escalated_run_is_rejected(db: Any) -> None:
    """An escalated run is terminal and cannot be renewed."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.status = "escalated"
        row.ended_at = datetime.now(timezone.utc)
        session.commit()

    outcome = _renew(db, str(task.run_id))

    assert outcome == RUN_HEARTBEAT_NOT_ELIGIBLE
    assert _heartbeat_state(db, str(task.run_id))["status"] == "escalated"


def test_persistence_failure_is_observable(db: Any) -> None:
    """Unreachable persistence is reported, never silently treated as renewed."""
    store = AgentStore(db=None)
    renew = getattr(store, "renew_coding_run_heartbeat", None)
    assert renew is not None, (
        "the agent store has no claim-scoped heartbeat renewal operation"
    )

    outcome = renew(
        run_id="run_any",
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
    )

    assert outcome == RUN_HEARTBEAT_UNAVAILABLE


def test_duplicate_acceptance_cannot_refresh_the_heartbeat(db: Any) -> None:
    """A rejected duplicate leaves the original liveness evidence untouched."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED
    before = _heartbeat_state(db, str(task.run_id))["heartbeat_at"]

    outcome = _claim(db, task, claim_id=_CLAIM_B)

    assert outcome == acceptance._REJECTED
    after = _heartbeat_state(db, str(task.run_id))
    assert after["heartbeat_at"] == before
    assert after["claim_id"] == _CLAIM_A


def test_two_workers_cannot_renew_the_same_run_under_different_claims(
    db: Any,
) -> None:
    """Concurrent renewal never transfers ownership."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED
    run_id = str(task.run_id)

    def _attempt(index: int) -> str:
        if index == 0:
            return _renew(db, run_id, worker_instance_id=_INSTANCE_A, claim_id=_CLAIM_A)
        return _renew(db, run_id, worker_instance_id=_INSTANCE_B, claim_id=_CLAIM_B)

    outcomes = [_attempt(0), _attempt(1)]

    assert RUN_HEARTBEAT_RENEWED in outcomes
    assert RUN_HEARTBEAT_NOT_ELIGIBLE in outcomes
    state = _heartbeat_state(db, run_id)
    assert state["instance_id"] == _INSTANCE_A
    assert state["claim_id"] == _CLAIM_A


# ---------------------------------------------------------------------------
# 17-19: the worker's heartbeat lifecycle.
# ---------------------------------------------------------------------------


def test_heartbeat_continues_while_a_synthetic_adapter_is_blocked(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    _fast_heartbeat: None,
) -> None:
    """A blocked synchronous adapter does not suppress liveness reporting."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    adapter = _BlockingAdapter()
    monkeypatch.setitem(acceptance.ADAPTERS, "pi_codex_runner", adapter)

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    holder: dict[str, Any] = {}

    def _process() -> None:
        worker._process_task(task)

    thread = threading.Thread(target=_process, name="blocked-execution")
    thread.start()
    try:
        assert adapter.entered.wait(timeout=15), "the adapter was never entered"

        run_id = str(task.run_id)
        before = _heartbeat_state(db, run_id)["heartbeat_at"]
        advanced = _wait_until(
            lambda: _heartbeat_advanced(db, run_id, before),
            timeout=15,
        )
        assert advanced, "the heartbeat did not advance while the adapter blocked"
    finally:
        adapter.release.set()
        thread.join(timeout=30)

    assert not thread.is_alive()


def test_heartbeat_stops_after_normal_terminalization(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    _fast_heartbeat: None,
) -> None:
    """Once the run is terminal, nothing renews its heartbeat."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    adapter = acceptance._StubAdapter(db)
    adapter.run_id = str(task.run_id)
    monkeypatch.setitem(acceptance.ADAPTERS, "pi_codex_runner", adapter)

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    worker._process_task(task)

    state = _heartbeat_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
    settled = state["heartbeat_at"]
    assert settled is not None

    outcome = _renew(db, str(task.run_id))

    assert outcome == RUN_HEARTBEAT_NOT_ELIGIBLE
    assert _heartbeat_state(db, str(task.run_id))["heartbeat_at"] == settled


def test_no_heartbeat_helper_survives_worker_shutdown(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    _fast_heartbeat: None,
) -> None:
    """The reporter is stopped and joined when the execution ends."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    adapter = acceptance._StubAdapter(db)
    adapter.run_id = str(task.run_id)
    monkeypatch.setitem(acceptance.ADAPTERS, "pi_codex_runner", adapter)

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    worker._process_task(task)

    assert worker._coding_run_heartbeats == {}
    live = [
        thread
        for thread in threading.enumerate()
        if thread.name.startswith("coding-run-heartbeat-")
    ]
    assert live == [], [thread.name for thread in live]


def test_worker_shutdown_stops_and_joins_every_heartbeat_helper(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    _fast_heartbeat: None,
) -> None:
    """A graceful worker shutdown leaves no liveness reporter behind.

    The reporter is stopped and joined while the execution is still in
    flight, so it cannot outlive the worker that owns it. The run itself is
    untouched: a stopped reporter freezes the evidence, it does not resolve
    the run.
    """
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    adapter = _BlockingAdapter()
    monkeypatch.setitem(acceptance.ADAPTERS, "pi_codex_runner", adapter)

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    thread = threading.Thread(
        target=lambda: worker._process_task(task),
        name="blocked-execution",
    )
    thread.start()
    try:
        assert adapter.entered.wait(timeout=15), "the adapter was never entered"
        assert worker._coding_run_heartbeats, "no liveness reporter was started"

        worker.shutdown()

        assert worker._coding_run_heartbeats == {}
        live = [
            alive
            for alive in threading.enumerate()
            if alive.name.startswith("coding-run-heartbeat-")
        ]
        assert live == [], [alive.name for alive in live]
    finally:
        adapter.release.set()
        thread.join(timeout=30)

    # The run keeps its canonical state; only the reporting stopped.
    state = _heartbeat_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert state["instance_id"]
    assert state["claim_id"]


# ---------------------------------------------------------------------------
# 20-22: disappearance, history, and the database constraint.
# ---------------------------------------------------------------------------


def test_worker_disappearance_leaves_the_last_heartbeat_intact(
    db: Any,
) -> None:
    """The final durable heartbeat survives the worker that wrote it."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == acceptance._ACCEPTED
    assert _renew(db, str(task.run_id)) == RUN_HEARTBEAT_RENEWED
    before = _heartbeat_state(db, str(task.run_id))

    # The worker process disappears: nothing further is written.
    after = _heartbeat_state(db, str(task.run_id))

    assert after["status"] == "running"
    assert after["instance_id"] == before["instance_id"]
    assert after["claim_id"] == before["claim_id"]
    assert after["heartbeat_at"] == before["heartbeat_at"]
    assert after["ended_at"] is None


def test_historical_null_heartbeat_remains_valid(db: Any) -> None:
    """A run accepted before heartbeats existed stays readable."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.status = "running"
        row.started_at = datetime.now(timezone.utc)
        row.coding_worker_instance_id = None
        row.coding_worker_claim_id = None
        row.coding_worker_last_heartbeat_at = None
        session.commit()

    state = _heartbeat_state(db, str(task.run_id))

    assert state["status"] == "running"
    assert state["heartbeat_at"] is None
    assert state["instance_id"] is None
    assert state["claim_id"] is None


def test_invalid_partial_ownership_heartbeat_fails_the_constraint(
    db: Any,
) -> None:
    """A heartbeat without a complete ownership record is refused."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_last_heartbeat_at = datetime.now(timezone.utc)
        with pytest.raises(IntegrityError):
            session.commit()


# ---------------------------------------------------------------------------
# 23-24: nothing else moves.
# ---------------------------------------------------------------------------


def test_no_credential_or_model_routing_changes_occur(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Heartbeat reporting does not touch credential or routing authority."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    binding = dict(task.execution_binding or {})

    assert _claim(db, task) == acceptance._ACCEPTED
    assert _renew(db, str(task.run_id)) == RUN_HEARTBEAT_RENEWED

    after = dict(task.execution_binding or {})
    assert after.get("provider_id") == binding.get("provider_id")
    assert after.get("model_id") == binding.get("model_id")
    assert after.get("harness_id") == binding.get("harness_id")
    assert after.get("reasoning_effort") == binding.get("reasoning_effort")
    assert after.get("credential_ref") == binding.get("credential_ref")


def test_no_retry_requeue_or_result_delivery_is_caused_by_heartbeat(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
    _fast_heartbeat: None,
) -> None:
    """Reporting liveness never re-runs, re-queues, or delivers a result."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    adapter = acceptance._StubAdapter(db)
    adapter.run_id = str(task.run_id)
    monkeypatch.setitem(acceptance.ADAPTERS, "pi_codex_runner", adapter)

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    worker._process_task(task)
    messages_after_first = acceptance._coding_result_message_count(
        db, task.thread_id
    )
    calls_after_first = adapter.calls

    # A renewal long after the run is terminal must not produce anything.
    assert _renew(db, str(task.run_id)) == RUN_HEARTBEAT_NOT_ELIGIBLE

    assert adapter.calls == calls_after_first
    assert (
        acceptance._coding_result_message_count(db, task.thread_id)
        == messages_after_first
    )
    assert dequeue_coding_execution(block=False) is None
    state = _heartbeat_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
