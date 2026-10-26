"""Guardian coding worker -- claim-fenced terminal result contract.

Durable ownership and the claim-scoped heartbeat proved *who* holds a run and
*that the holder was still reporting*. They did not prove that only the
holder may finish it.

Before this contract, the terminal path wrote in this order:

1. the source-thread result message,
2. the run's terminal status, through an unguarded status write,
3. the coding-result artifact,
4. the terminal task event.

A worker whose claim had been superseded could therefore deliver a result
message and publish a ``task.completed`` event for a run it no longer owned,
and the source-thread result could exist before the terminal decision that
should have authorised it.

This contract proves the repaired behaviour: the terminal decision and the
canonical result writes that belong to it commit together, and only while the
recorded worker instance and claim still own the run.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from guardian.db.models import AgentRun
from guardian.workers import coding_worker

try:  # The baseline has no claim-fenced terminal operation.
    from guardian.agents.store import (
        RUN_TERMINAL_ACCEPTED,
        RUN_TERMINAL_ALREADY_TERMINAL,
        RUN_TERMINAL_REJECTED,
        RUN_TERMINAL_UNAVAILABLE,
        AgentStore,
    )
except ImportError:
    RUN_TERMINAL_ACCEPTED = "terminal_accepted"
    RUN_TERMINAL_ALREADY_TERMINAL = "terminal_already_terminal"
    RUN_TERMINAL_REJECTED = "terminal_rejected"
    RUN_TERMINAL_UNAVAILABLE = "terminal_unavailable"

    from guardian.agents.store import AgentStore

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

_INSTANCE_A = "cwi_terminal_fence_worker_a"
_INSTANCE_B = "cwi_terminal_fence_worker_b"
_CLAIM_A = "cwc_terminal_fence_claim_a"
_CLAIM_B = "cwc_terminal_fence_claim_b"

_ACCEPTED = acceptance._ACCEPTED
_REJECTED = acceptance._REJECTED


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
def _service_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GUARDIAN_API_KEY", acceptance._SERVICE_KEY)
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
    previous_publisher_db = getattr(
        agent_orchestration._event_publisher, "db", None
    )
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
                "version": "0.0.0-terminal-fencing-contract",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PI_CODING_AGENT_PACKAGE_ROOT", str(package_root))
    yield


class _SupersedingAdapter:
    """An adapter that supersedes the run's claim while it is executing.

    It models the stale-worker case: the worker is executing normally, but
    the canonical owner of the run changed underneath it.
    """

    def __init__(self, db: Any, run_id: str) -> None:
        self.db = db
        self.run_id = run_id
        self.calls = 0

    def execute_authorized(self, *_args: Any, **_kwargs: Any) -> Any:
        from guardian.agents.adapters.base import AgentRunEnvelope

        self.calls += 1
        with self.db.get_session() as session:
            row = (
                session.query(AgentRun).filter_by(run_id=self.run_id).one()
            )
            row.coding_worker_claim_id = _CLAIM_B
            session.commit()
        return AgentRunEnvelope(
            status="ok",
            summary="adapter ok",
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
        )


def _claim(
    db: Any,
    task: Any,
    *,
    worker_instance_id: str = _INSTANCE_A,
    claim_id: str = _CLAIM_A,
) -> str:
    """Accept a dispatched run under a known worker instance and claim."""
    return acceptance._claim(
        db,
        task,
        worker_instance_id=worker_instance_id,
        claim_id=claim_id,
    )


def _finalize(
    db: Any,
    task: Any,
    *,
    worker_instance_id: str = _INSTANCE_A,
    claim_id: str = _CLAIM_A,
    result_status: str = "succeeded",
    result_summary: str = "Fenced terminal result.",
) -> dict[str, Any]:
    """Finalize a run under a claim, through the claim-fenced operation."""
    store = AgentStore(db=db)
    return store.finalize_claimed_coding_result(
        run_id=str(task.run_id or ""),
        worker_instance_id=worker_instance_id,
        claim_id=claim_id,
        coding_task_id=str(task.coding_task_id or ""),
        attempt_id=str(task.attempt_id or ""),
        request_id=task.request_id or None,
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status=result_status,
        result_summary=result_summary,
        adapter_kind="pi_codex_runner",
        files_changed=["guardian/agents/store.py"],
    )


def _run_state(db: Any, run_id: str) -> dict[str, Any]:
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return {
            "status": row.status,
            "instance_id": row.coding_worker_instance_id,
            "claim_id": row.coding_worker_claim_id,
            "started_at": row.started_at,
            "ended_at": row.ended_at,
            "error": row.error,
            "heartbeat_at": row.coding_worker_last_heartbeat_at,
        }


def _escalate(db: Any, run_id: str) -> None:
    """Simulate an authoritative disposition that owns the run."""
    store = AgentStore(db=db)
    store.update_run_status(run_id=run_id, status="escalated")


def _assert_nothing_written(
    db: Any,
    task: Any,
    *,
    expected_status: str,
    expected_message_count: int = 0,
) -> None:
    """A rejected terminalization left no trace beyond the canonical row."""
    state = _run_state(db, str(task.run_id))
    assert state["status"] == expected_status
    assert state["ended_at"] is None or expected_status != "running"
    assert acceptance._artifact_count(db, str(task.run_id)) == 0
    assert (
        acceptance._coding_result_message_count(db, task.thread_id)
        == expected_message_count
    )


# ---------------------------------------------------------------------------
# 1-2: the authorized terminal decision.
# ---------------------------------------------------------------------------


def test_an_authorized_claim_finalizes_the_run(db: Any) -> None:
    """The recorded owner may finalize its own accepted run."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    receipt = _finalize(db, task)

    assert receipt["terminal_claim"] == RUN_TERMINAL_ACCEPTED
    assert receipt["terminal_accepted"] is True
    state = _run_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert state["ended_at"] is not None
    assert state["instance_id"] == _INSTANCE_A
    assert state["claim_id"] == _CLAIM_A


def test_the_terminal_decision_commits_with_its_result_writes(db: Any) -> None:
    """The canonical result writes land with the terminal decision."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    _finalize(db, task)

    assert acceptance._artifact_count(db, str(task.run_id)) == 1
    assert acceptance._coding_result_message_count(db, task.thread_id) == 1


def test_the_terminal_decision_leaves_the_ownership_identities_intact(
    db: Any,
) -> None:
    """Finalizing a run does not reassign it."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    _finalize(db, task)

    state = _run_state(db, str(task.run_id))
    assert state["instance_id"] == _INSTANCE_A
    assert state["claim_id"] == _CLAIM_A


# ---------------------------------------------------------------------------
# 3-8: a stale or ineligible claim cannot finalize anything.
# ---------------------------------------------------------------------------


def test_a_mismatched_worker_instance_cannot_finalize(db: Any) -> None:
    """A different worker instance may not finalize the run."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    receipt = _finalize(db, task, worker_instance_id=_INSTANCE_B)

    assert receipt["terminal_claim"] == RUN_TERMINAL_REJECTED
    _assert_nothing_written(db, task, expected_status="running")


def test_a_mismatched_claim_cannot_finalize(db: Any) -> None:
    """A different claim may not finalize the run, even from the same worker."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    receipt = _finalize(db, task, claim_id=_CLAIM_B)

    assert receipt["terminal_claim"] == RUN_TERMINAL_REJECTED
    _assert_nothing_written(db, task, expected_status="running")


def test_a_missing_claim_cannot_finalize(db: Any) -> None:
    """An absent claim is not an authority."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    receipt = _finalize(db, task, claim_id="")

    assert receipt["terminal_claim"] == RUN_TERMINAL_REJECTED
    _assert_nothing_written(db, task, expected_status="running")


def test_a_missing_worker_instance_cannot_finalize(db: Any) -> None:
    """An absent worker identity is not an authority."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    receipt = _finalize(db, task, worker_instance_id="")

    assert receipt["terminal_claim"] == RUN_TERMINAL_REJECTED
    _assert_nothing_written(db, task, expected_status="running")


def test_a_missing_run_cannot_be_finalized(db: Any) -> None:
    """A run that does not exist cannot be finalized."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    store = AgentStore(db=db)
    receipt = store.finalize_claimed_coding_result(
        run_id="run-that-does-not-exist",
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
        coding_task_id=str(task.coding_task_id or ""),
        attempt_id=str(task.attempt_id or ""),
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status="succeeded",
        result_summary="No such run.",
    )

    assert receipt["terminal_claim"] == RUN_TERMINAL_REJECTED
    assert receipt["terminal_accepted"] is False


@pytest.mark.parametrize(
    "terminal_status",
    ["succeeded", "failed", "canceled"],
)
def test_a_terminal_run_cannot_be_finalized_again(
    db: Any,
    terminal_status: str,
) -> None:
    """A run that already carries a terminal status is not reopened."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED
    AgentStore(db=db).update_run_status(
        run_id=str(task.run_id),
        status=terminal_status,
    )

    receipt = _finalize(db, task)

    assert receipt["terminal_claim"] == RUN_TERMINAL_ALREADY_TERMINAL
    assert receipt["terminal_accepted"] is False
    state = _run_state(db, str(task.run_id))
    assert state["status"] == terminal_status


def test_an_escalated_run_is_not_overwritten_by_a_late_worker(db: Any) -> None:
    """An authoritative disposition wins over a late worker completion."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    # The run is disposed of authoritatively while the worker is still
    # executing.
    _escalate(db, str(task.run_id))
    escalated = _run_state(db, str(task.run_id))
    assert escalated["status"] == "escalated"

    # The worker now returns success and tries to finalize.
    receipt = _finalize(db, task)

    assert receipt["terminal_claim"] == RUN_TERMINAL_REJECTED
    assert receipt["terminal_accepted"] is False
    state = _run_state(db, str(task.run_id))
    assert state["status"] == "escalated"
    assert state["instance_id"] == _INSTANCE_A
    assert state["claim_id"] == _CLAIM_A
    assert acceptance._artifact_count(db, str(task.run_id)) == 0
    assert acceptance._coding_result_message_count(db, task.thread_id) == 0


def test_a_contradictory_deployment_lineage_cannot_finalize(db: Any) -> None:
    """A deployment that contradicts the persisted run is not an authority."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    # Rewrite the deployment so its lineage contradicts the run it accepted.
    with db.get_session() as session:
        from guardian.db.models import AgentDeployment

        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=str(task.deployment_id or ""))
            .one()
        )
        spec = dict(deployment.spec_json or {})
        spec["source_thread_id"] = int(task.thread_id or 0) + 987
        deployment.spec_json = spec
        session.commit()

    receipt = _finalize(db, task)

    assert receipt["terminal_claim"] == RUN_TERMINAL_REJECTED
    _assert_nothing_written(db, task, expected_status="running")


def test_unavailable_persistence_fails_closed(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When persistence is unreachable, nothing is finalized."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    store = AgentStore(db=db)
    monkeypatch.setattr(store, "_has_db", lambda: False)

    receipt = store.finalize_claimed_coding_result(
        run_id=str(task.run_id or ""),
        worker_instance_id=_INSTANCE_A,
        claim_id=_CLAIM_A,
        coding_task_id=str(task.coding_task_id or ""),
        attempt_id=str(task.attempt_id or ""),
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status="succeeded",
        result_summary="No persistence.",
    )

    assert receipt["terminal_claim"] == RUN_TERMINAL_UNAVAILABLE
    assert receipt["terminal_accepted"] is False


# ---------------------------------------------------------------------------
# 9-10: the worker fences its own terminal paths.
# ---------------------------------------------------------------------------


def test_the_worker_does_not_publish_a_terminal_event_for_a_rejected_claim(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale worker's terminal failure produces no terminal event."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    published: list[tuple[str, str]] = []
    monkeypatch.setattr(
        coding_worker.task_events,
        "publish_with_visibility",
        lambda run_id, event_type, payload, *args, **kwargs: published.append(
            (str(run_id), str(event_type))
        ),
    )

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    worker._coding_run_claims[str(task.run_id or "")] = _CLAIM_A
    # The claim was superseded while the worker was executing.
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_claim_id = _CLAIM_B
        session.commit()

    worker._emit_failure(
        task,
        adapter_kind="pi_codex_runner",
        error_message="the adapter failed",
        error_code="ADAPTER_FAILED",
    )

    event_types = [event_type for _, event_type in published]
    assert "task.failed" not in event_types
    assert "task.event" in event_types
    state = _run_state(db, str(task.run_id))
    assert state["status"] == "running"


def test_the_worker_reports_ownership_loss_for_a_rejected_claim(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The refusal uses the canonical non-terminal ownership-lost reason."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    published: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        coding_worker.task_events,
        "publish_with_visibility",
        lambda run_id, event_type, payload, *args, **kwargs: published.append(
            (str(event_type), dict(payload))
        ),
    )

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    worker._coding_run_claims[str(task.run_id or "")] = _CLAIM_A
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        row.coding_worker_instance_id = _INSTANCE_B
        session.commit()

    worker._emit_failure(
        task,
        adapter_kind="pi_codex_runner",
        error_message="the adapter failed",
        error_code="ADAPTER_FAILED",
    )

    ownership_events = [
        payload
        for event_type, payload in published
        if payload.get("error_code") == "EXECUTION_OWNERSHIP_LOST"
    ]
    assert ownership_events, published
    assert all(
        event_type != "task.failed" for event_type, _ in published
    )


# ---------------------------------------------------------------------------
# 11: concurrent finalization.
# ---------------------------------------------------------------------------


def test_two_concurrent_finalizations_resolve_to_one_outcome(db: Any) -> None:
    """Only one terminal decision wins; the loser writes nothing."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    barrier = threading.Barrier(2)

    def _finalize_once() -> str:
        barrier.wait(timeout=30)
        return str(
            _finalize(db, task).get("terminal_claim") or ""
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: _finalize_once(), range(2)))

    assert sorted(outcomes) == sorted(
        [RUN_TERMINAL_ACCEPTED, RUN_TERMINAL_ALREADY_TERMINAL]
    )
    state = _run_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert acceptance._artifact_count(db, str(task.run_id)) == 1
    assert acceptance._coding_result_message_count(db, task.thread_id) == 1


def test_a_stale_claim_racing_the_owner_cannot_win(db: Any) -> None:
    """An invalid claim racing the owner never wins the terminal decision."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    barrier = threading.Barrier(2)

    def _owner() -> str:
        barrier.wait(timeout=30)
        return str(_finalize(db, task).get("terminal_claim") or "")

    def _stale() -> str:
        barrier.wait(timeout=30)
        return str(
            _finalize(db, task, claim_id=_CLAIM_B).get("terminal_claim") or ""
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        owner_future = pool.submit(_owner)
        stale_future = pool.submit(_stale)
        owner_outcome = owner_future.result()
        stale_outcome = stale_future.result()

    assert owner_outcome == RUN_TERMINAL_ACCEPTED
    assert stale_outcome in (
        RUN_TERMINAL_REJECTED,
        RUN_TERMINAL_ALREADY_TERMINAL,
    )
    state = _run_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert acceptance._artifact_count(db, str(task.run_id)) == 1


# ---------------------------------------------------------------------------
# 12-13: idempotency and rollback.
# ---------------------------------------------------------------------------


def test_a_duplicate_finalization_does_not_duplicate_the_result(
    db: Any,
) -> None:
    """A repeated finalization observes the committed result read-only."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    first = _finalize(db, task)
    ended_at = _run_state(db, str(task.run_id))["ended_at"]
    second = _finalize(db, task)

    assert first["terminal_claim"] == RUN_TERMINAL_ACCEPTED
    assert second["terminal_claim"] == RUN_TERMINAL_ALREADY_TERMINAL
    assert acceptance._artifact_count(db, str(task.run_id)) == 1
    assert acceptance._coding_result_message_count(db, task.thread_id) == 1
    assert _run_state(db, str(task.run_id))["ended_at"] == ended_at


def test_a_persistence_failure_rolls_back_the_terminal_decision(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failure inside the result writes leaves the run running."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]
    assert _claim(db, task) == _ACCEPTED

    store = AgentStore(db=db)

    def _failing_add_artifact(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("injected artifact failure")

    monkeypatch.setattr(AgentStore, "add_artifact", _failing_add_artifact)

    with pytest.raises(RuntimeError):
        _finalize(db, task)

    monkeypatch.undo()
    state = _run_state(db, str(task.run_id))
    assert state["status"] == "running"
    assert acceptance._artifact_count(db, str(task.run_id)) == 0
    assert acceptance._coding_result_message_count(db, task.thread_id) == 0


# ---------------------------------------------------------------------------
# 15: the behavioural reds. These run against the unmodified baseline too, so
# the failure they show is a behaviour, not a missing method.
# ---------------------------------------------------------------------------


def test_a_superseded_claim_produces_no_terminal_outcome(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale worker cannot finish a run it no longer owns.

    The worker accepts the run, the canonical owner changes while it is
    executing, and it then returns success. The repaired runtime refuses the
    terminalization: no terminal status, no artifact, no source-thread result
    and no terminal event.
    """
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    published: list[str] = []
    monkeypatch.setattr(
        coding_worker.task_events,
        "publish_with_visibility",
        lambda run_id, event_type, payload, *args, **kwargs: published.append(
            str(event_type)
        ),
    )
    monkeypatch.setitem(
        acceptance.ADAPTERS,
        "pi_codex_runner",
        _SupersedingAdapter(db, str(task.run_id)),
    )

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    try:
        worker._process_task(task)
    finally:
        # This contract drives the task directly, so it owns the cleanup the
        # worker's poll loop would otherwise do.
        worker.shutdown()

    state = _run_state(db, str(task.run_id))
    assert state["status"] == "running"
    assert acceptance._artifact_count(db, str(task.run_id)) == 0
    assert acceptance._coding_result_message_count(db, task.thread_id) == 0
    assert "task.completed" not in published
    assert "task.failed" not in published


def test_a_failed_result_write_leaves_no_source_thread_result(
    db: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A result-side effect cannot outlive a failed terminal write.

    The delivery and the artifact are part of one terminal decision. When the
    canonical result writes fail, the source-thread result must not remain
    behind: the earlier ordering delivered the message first and committed it
    on its own, so a later failure left a delivered result for a run that
    never reached a terminal outcome.
    """
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    monkeypatch.setitem(
        acceptance.ADAPTERS,
        "pi_codex_runner",
        _SupersedingAdapter(db, str(task.run_id)),
    )

    def _failing_add_artifact(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("injected artifact failure")

    monkeypatch.setattr(AgentStore, "add_artifact", _failing_add_artifact)

    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    try:
        worker._process_task(task)
    except RuntimeError:
        # The injected failure propagates out of the terminal write. What
        # matters is what it left behind.
        pass
    finally:
        worker.shutdown()

    monkeypatch.undo()
    assert acceptance._coding_result_message_count(db, task.thread_id) == 0
    assert acceptance._artifact_count(db, str(task.run_id)) == 0
    assert _run_state(db, str(task.run_id))["status"] == "running"


# ---------------------------------------------------------------------------
# 14: legacy compatibility.
# ---------------------------------------------------------------------------


def test_a_run_that_was_never_accepted_keeps_its_legacy_behaviour(
    db: Any,
) -> None:
    """A run outside the claim-fenced path is unchanged."""
    dispatched = acceptance._dispatch_one(db)
    task = dispatched["task"]

    store = AgentStore(db=db)
    receipt = store.store_coding_result(
        run_id=str(task.run_id or ""),
        coding_task_id=str(task.coding_task_id or ""),
        attempt_id=str(task.attempt_id or ""),
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        result_status="succeeded",
        result_summary="Legacy result.",
    )

    assert receipt.get("terminal_claim") is None
    state = _run_state(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert acceptance._artifact_count(db, str(task.run_id)) == 1
