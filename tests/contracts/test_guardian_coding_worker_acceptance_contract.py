"""Durable coding-worker acceptance contract.

A Guardian-bound coding execution may not enter a side-effecting path until
its acceptance is durably recorded in canonical PostgreSQL. This contract
proves the acceptance operation, its boundary, and its refusals.

The durable representation is the existing canonical ``agent_runs`` row:

    agent_runs.status     queued -> running
    agent_runs.started_at set exactly once, on first acceptance

No migration, new table, or new protocol token is required: the schema already
permits ``running`` and already carries a nullable ``started_at``.

All cases use synthetic credentials and a stubbed provider adapter. No provider
request is made.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import asyncio
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from uuid import uuid4

from fastapi import HTTPException
import psycopg
from psycopg import sql
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from guardian.agents.adapters import ADAPTERS
from guardian.agents.adapters.base import AgentRunEnvelope
from guardian.agents.execution_credentials import store_api_key
from guardian.agents.store import AgentStore
from guardian.core.guardian_delegation_service import GuardianDelegationService
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    AgentRunArtifact,
    Base,
    ChatMessage,
    ChatThread,
    Project,
    User,
)
from guardian.tasks.types import CodingExecutionTask
from guardian.workers import coding_worker

# The service key the worker presents to Guardian's credential authority.
_SERVICE_KEY = "acceptance-contract-service-key"

# The evaluated worktree is a real git repository, so the worker can resolve a
# repository root without any repository being created by the test.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])

# The durable acceptance outcome vocabulary. These are the contract's values,
# not an import of the implementation's constants: pinning the vocabulary here
# keeps this module executable against the pre-change implementation, where the
# acceptance operation does not exist yet. That is what makes this a
# regression rather than a description of new code. The canonical exported
# names are asserted separately, in
# ``test_the_store_exports_the_canonical_acceptance_outcomes``.
_ACCEPTED = "accepted"
_REJECTED = "rejected"
_UNAVAILABLE = "unavailable"



# ---------------------------------------------------------------------------
# Disposable PostgreSQL.
# ---------------------------------------------------------------------------


@contextmanager
def _disposable_postgres_engine() -> Iterator[Engine]:
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        raise RuntimeError("TEST_DATABASE_URL must point to disposable PostgreSQL")
    database_name = f"codexify_guardian_accept_{uuid4().hex[:12]}"
    admin_url = make_url(base_url).set(
        drivername="postgresql", database="postgres"
    ).render_as_string(hide_password=False)
    database_url = make_url(base_url).set(
        drivername="postgresql+psycopg", database=database_name
    ).render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
        )
    engine = create_engine(database_url, future=True)
    try:
        yield engine
    finally:
        engine.dispose()
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(
                sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
            )


class _TestDB:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def get_session(self):  # noqa: ANN201
        return self._session_factory()


def _clear_disposable_tables(engine: Engine) -> None:
    preparer = engine.dialect.identifier_preparer
    names = ", ".join(preparer.quote(name) for name in Base.metadata.tables)
    with engine.begin() as connection:
        connection.exec_driver_sql(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE")


@pytest.fixture(scope="module")
def _postgres_engine() -> Iterator[Engine]:
    with _disposable_postgres_engine() as engine:
        Base.metadata.create_all(bind=engine)
        yield engine


@pytest.fixture
def db(_postgres_engine: Engine) -> _TestDB:
    _clear_disposable_tables(_postgres_engine)
    return _TestDB(_postgres_engine)


@pytest.fixture(autouse=True)
def _credential_encryption_key() -> Iterator[None]:
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
def _pi_harness_package(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Materialize a Pi harness package root.

    The worker refuses to execute when the Pi harness version cannot be read.
    This fixture supplies the version marker only; no Pi SDK, provider request,
    or network access is involved.
    """
    package_root = tmp_path_factory.mktemp("pi-coding-agent-package")
    (package_root / "package.json").write_text(
        json.dumps(
            {
                "name": "@earendil-works/pi-coding-agent",
                "version": "0.0.0-acceptance-contract",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("PI_CODING_AGENT_PACKAGE_ROOT", str(package_root))
    yield


@pytest.fixture(autouse=True)
def _guardian_service_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Present a static Guardian service key to the credential authority."""
    monkeypatch.setenv("GUARDIAN_API_KEY", _SERVICE_KEY)
    yield


class _InProcessResponse:
    """Minimal stand-in for the object ``urlopen`` returns."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, *_args: Any) -> bytes:
        return self._payload

    def __enter__(self) -> "_InProcessResponse":
        return self

    def __exit__(self, *_exc: Any) -> bool:
        return False


@pytest.fixture(autouse=True)
def _guardian_credential_authority(
    db: _TestDB,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Bind the worker's credential-lease client to the real Guardian route.

    Only the socket is replaced. The request body, the service-key check, the
    deployment and lineage re-validation, the credential authority, the sealed
    lease payload, and the worker-side lease validation are all the production
    code paths. The authority therefore re-validates the *accepted* run: the
    route accepts a run whose status is ``queued`` or ``running``, so a durably
    accepted run remains leaseable.
    """
    from guardian.agents import credential_lease_client
    from guardian.core.dependencies import require_service_api_key
    from guardian.routes import agent_orchestration

    previous_store_db = getattr(agent_orchestration._store, "db", None)
    previous_publisher_db = getattr(agent_orchestration._event_publisher, "db", None)
    agent_orchestration.configure_db(db)

    def _urlopen(request: Any, timeout: Any = None) -> _InProcessResponse:
        payload = json.loads(bytes(request.data).decode("utf-8"))
        body = agent_orchestration.CodingExecutionCredentialLeaseRequest(**payload)
        try:
            require_service_api_key(x_api_key=_SERVICE_KEY)
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
        return _InProcessResponse(json.dumps(result).encode("utf-8"))

    monkeypatch.setattr(credential_lease_client, "urlopen", _urlopen)

    try:
        yield
    finally:
        agent_orchestration._store.db = previous_store_db
        agent_orchestration._event_publisher.db = previous_publisher_db


# ---------------------------------------------------------------------------
# Synthetic context.
# ---------------------------------------------------------------------------


def _seed_account(db: _TestDB, *, user_id: str = "account-1") -> dict[str, Any]:
    with db.get_session() as session:
        session.add(
            User(id=user_id, username=f"{user_id}-u", password_hash="hash")
        )
        project = Project(
            user_id=user_id, name=f"project-{user_id}", description=None, icon=None
        )
        session.add(project)
        session.flush()
        thread = ChatThread(
            user_id=user_id, title="Source thread", summary="", project_id=project.id
        )
        session.add(thread)
        session.flush()
        message = ChatMessage(
            thread_id=thread.id,
            user_id=user_id,
            role="user",
            content="Please patch the return path.",
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


def _seed_credential(db: _TestDB, *, user_id: str = "account-1") -> str:
    record = store_api_key(
        db,
        owner_scope="account",
        owner_id=user_id,
        provider_id="openai",
        api_key="sk-test-guardian-acceptance",
        funding_route="user_byok",
    )
    return str(record["credential_ref"])


def _dispatch_one(db: _TestDB) -> dict[str, Any]:
    """Run one real Guardian delegation and return its run, task and binding.

    The intent is created through the service's own entrypoint so the durable
    Guardian delegation intent, the run, the deployment, the execution binding,
    and the queued task are all authentic.
    """
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

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
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    payload = dequeue_coding_execution(block=False)
    assert payload is not None
    task = CodingExecutionTask.from_dict(payload)
    return {
        "seeded": seeded,
        "intent_id": intent_id,
        "run": {"run_id": run_id, "deployment_id": deployment_id},
        "task": task,
        "payload": payload,
    }


def _read_run(db: _TestDB, run_id: str) -> dict[str, Any]:
    """Read the canonical run row through a fresh database session."""
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=run_id).one_or_none()
        assert row is not None
        return {
            "run_id": row.run_id,
            "deployment_id": row.deployment_id,
            "status": row.status,
            "started_at": row.started_at,
            "ended_at": row.ended_at,
            "error": row.error,
            "thread_id": row.thread_id,
        }


def _artifact_count(db: _TestDB, run_id: str) -> int:
    """Count the durable artifacts attached to a run."""
    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=run_id).one()
        return (
            session.query(AgentRunArtifact).filter_by(run_id=run_row.id).count()
        )


def _coding_result_message_count(db: _TestDB, thread_id: int | None) -> int:
    """Count the source-thread result messages for a thread."""
    with db.get_session() as session:
        return (
            session.query(ChatMessage)
            .filter_by(thread_id=thread_id, kind="coding_result")
            .count()
        )


def _claim(db: _TestDB, task: CodingExecutionTask, **overrides: Any) -> str:
    store = AgentStore(db=db)
    kwargs: dict[str, Any] = {
        "run_id": str(task.run_id or ""),
        "deployment_id": str(task.deployment_id or ""),
        "user_id": (task.execution_binding or {}).get("user_id"),
        "thread_id": task.thread_id,
        "source_message_id": task.source_message_id,
        "attempt_id": str(task.attempt_id or ""),
        "coding_task_id": str(task.coding_task_id or ""),
    }
    kwargs.update(overrides)
    return store.claim_run_for_acceptance(**kwargs)


class _StubAdapter:
    """A provider stub that records the run state observed at adapter entry."""

    def __init__(self, db: _TestDB) -> None:
        self.db = db
        self.run_id = ""
        self.calls = 0
        self.observed_status: list[str | None] = []
        self.observed_started_at: list[Any] = []

    def execute_authorized(
        self,
        request: Any,
        identity: Any,
        credential_material: Any = None,
        read_only: bool = False,
        **kwargs: Any,
    ) -> AgentRunEnvelope:
        self.calls += 1
        state = _read_run(self.db, self.run_id)
        self.observed_status.append(state["status"])
        self.observed_started_at.append(state["started_at"])
        return AgentRunEnvelope(
            status="ok",
            summary="stub adapter ok",
            artifacts=[],
            next_actions=[],
            errors=[],
            metrics={},
        )


@pytest.fixture
def stub_adapter(monkeypatch: pytest.MonkeyPatch, db: _TestDB) -> _StubAdapter:
    adapter = _StubAdapter(db)
    monkeypatch.setitem(ADAPTERS, "pi_codex_runner", adapter)
    return adapter


def _run_worker(
    db: _TestDB,
    task: CodingExecutionTask,
    adapter: _StubAdapter | None = None,
) -> None:
    if adapter is not None:
        adapter.run_id = str(task.run_id)
    worker = coding_worker.CodingWorker(agent_store=AgentStore(db=db))
    worker._process_task(task)


#: The event types the backend treats as terminal for a chat attempt.
_TERMINAL_EVENT_TYPES = ("task.failed", "task.cancelled", "task.completed")


class _EventRecorder:
    """Records the task events the worker publishes."""

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        original = coding_worker.task_events.publish_with_visibility

        def _record(
            task_id: str,
            event_type: str,
            data: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            self.events.append((event_type, dict(data or {})))
            return original(task_id, event_type, data)

        monkeypatch.setattr(
            coding_worker.task_events, "publish_with_visibility", _record
        )

    def terminal_events(self) -> list[str]:
        return [event_type for event_type, _ in self.events if event_type in _TERMINAL_EVENT_TYPES]


# ---------------------------------------------------------------------------
# 1-5: acceptance, persistence, identity, and readback.
# ---------------------------------------------------------------------------


def test_the_store_exports_the_canonical_acceptance_outcomes() -> None:
    """The store publishes the acceptance outcome vocabulary it returns."""
    from guardian.agents import store as agent_store

    assert agent_store.RUN_ACCEPTANCE_ACCEPTED == _ACCEPTED
    assert agent_store.RUN_ACCEPTANCE_REJECTED == _REJECTED
    assert agent_store.RUN_ACCEPTANCE_UNAVAILABLE == _UNAVAILABLE


def test_a_valid_queued_guardian_run_is_accepted(db: _TestDB) -> None:
    """A queued Guardian run with a valid binding is accepted."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task)

    assert outcome == _ACCEPTED


def test_accepted_state_persists_as_running(db: _TestDB) -> None:
    """Acceptance moves the canonical run row to running."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    _claim(db, task)

    state = _read_run(db, str(task.run_id))
    assert state["status"] == "running"


def test_started_at_is_populated_exactly_once(db: _TestDB) -> None:
    """Acceptance stamps started_at, and a later claim does not refresh it."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    _claim(db, task)
    first = _read_run(db, str(task.run_id))
    assert first["started_at"] is not None

    # A duplicate claim must not refresh it.
    outcome = _claim(db, task)
    assert outcome == _REJECTED
    second = _read_run(db, str(task.run_id))
    assert second["started_at"] == first["started_at"]


def test_original_run_and_deployment_identities_are_unchanged(db: _TestDB) -> None:
    """Acceptance does not rewrite the run's identity."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    before = _read_run(db, str(task.run_id))
    _claim(db, task)
    after = _read_run(db, str(task.run_id))

    assert after["run_id"] == before["run_id"]
    assert after["deployment_id"] == before["deployment_id"]
    assert after["thread_id"] == before["thread_id"]
    assert after["ended_at"] == before["ended_at"]
    assert after["error"] == before["error"]


def test_accepted_state_is_readable_through_a_new_session(db: _TestDB) -> None:
    """The accepted state is durable, not session-scoped."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    _claim(db, task)

    # A brand new session (and a brand new store) sees the accepted state.
    fresh_store = AgentStore(db=db)
    with fresh_store.db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        assert row.status == "running"
        assert row.started_at is not None


# ---------------------------------------------------------------------------
# 6-7: the durability boundary precedes side effects.
# ---------------------------------------------------------------------------


def test_acceptance_precedes_worktree_creation(
    db: _TestDB,
    monkeypatch: pytest.MonkeyPatch,
    stub_adapter: _StubAdapter,
) -> None:
    """The isolated worktree is only created after durable acceptance."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]
    task.cwd = _REPO_ROOT

    observed: dict[str, Any] = {}

    def _probe(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        """Stand in for the git worktree mechanics and record what was durable.

        The git mechanics are not under test here; the boundary is. The probe
        reports the durable state exactly as it stands at the moment the
        worker reaches worktree creation, and creates nothing on disk.
        """
        state = _read_run(db, str(task.run_id))
        observed["status"] = state["status"]
        observed["started_at"] = state["started_at"]
        metadata = coding_worker._default_worktree_metadata(enabled=True)
        metadata.update(
            {
                "status": "create_failed",
                "error_code": "WORKTREE_CREATE_FAILED",
                "error_message": "worktree mechanics are not under test",
            }
        )
        return metadata

    monkeypatch.setenv("CODING_WORKER_WORKTREE_ISOLATION", "1")
    monkeypatch.setattr(coding_worker, "_create_isolated_worktree", _probe)
    _run_worker(db, task)

    assert observed, "the isolated worktree path was not reached"
    assert observed["status"] == "running"
    assert observed["started_at"] is not None


def test_acceptance_precedes_adapter_entry(
    db: _TestDB,
    stub_adapter: _StubAdapter,
) -> None:
    """The provider adapter is only entered after durable acceptance."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    _run_worker(db, task, stub_adapter)

    assert stub_adapter.calls == 1
    assert stub_adapter.observed_status == ["running"]
    assert stub_adapter.observed_started_at[0] is not None


# ---------------------------------------------------------------------------
# 8-10: duplicate and terminal protection.
# ---------------------------------------------------------------------------


def test_a_duplicate_claim_does_not_enter_execution(
    db: _TestDB,
    monkeypatch: pytest.MonkeyPatch,
    stub_adapter: _StubAdapter,
) -> None:
    """A duplicate delivery of an accepted task must not execute again."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    recorder = _EventRecorder()
    recorder.install(monkeypatch)

    _run_worker(db, task, stub_adapter)
    assert stub_adapter.calls == 1
    after_first = _read_run(db, str(task.run_id))
    assert after_first["status"] == "succeeded"
    accepted_started_at = after_first["started_at"]
    artifacts_after_first = _artifact_count(db, str(task.run_id))
    messages_after_first = _coding_result_message_count(db, task.thread_id)

    # The same task is delivered again.
    recorder.events.clear()
    _run_worker(db, task, stub_adapter)

    assert stub_adapter.calls == 1, "the duplicate entered the adapter"
    state = _read_run(db, str(task.run_id))
    assert state["status"] == "succeeded", "the duplicate reopened or rewrote the run"
    assert state["started_at"] == accepted_started_at
    assert _artifact_count(db, str(task.run_id)) == artifacts_after_first
    assert _coding_result_message_count(db, task.thread_id) == messages_after_first

    # The duplicate must not publish a terminal outcome for an attempt that
    # already completed successfully. The refusal is observable, but it is not
    # a terminal result.
    assert not recorder.terminal_events(), recorder.terminal_events()
    assert recorder.events, "the duplicate refusal was not observable"
    refusal_type, refusal_data = recorder.events[-1]
    assert refusal_type == "task.event"
    assert refusal_data.get("status") == "acceptance_rejected"
    assert refusal_data.get("error_code")


def test_two_concurrent_claims_cannot_both_succeed(db: _TestDB) -> None:
    """The compare-and-set lets exactly one of two racing claims win."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    def _claim_once() -> str:
        return _claim(db, task)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: _claim_once(), range(2)))

    assert sorted(outcomes) == sorted(
        [_ACCEPTED, _REJECTED]
    )
    state = _read_run(db, str(task.run_id))
    assert state["status"] == "running"
    assert state["started_at"] is not None


def test_a_terminal_run_cannot_be_reaccepted(db: _TestDB) -> None:
    """A succeeded, failed, or canceled run is never reopened."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    store = AgentStore(db=db)
    for terminal in ("succeeded", "failed", "canceled", "escalated"):
        with store.db.get_session() as session:
            row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
            row.status = terminal
            session.commit()

        outcome = _claim(db, task)
        assert outcome == _REJECTED, terminal

        state = _read_run(db, str(task.run_id))
        assert state["status"] == terminal, terminal


# ---------------------------------------------------------------------------
# 11-13: fail-closed refusals.
# ---------------------------------------------------------------------------


def test_a_missing_run_fails_closed(db: _TestDB) -> None:
    """A claim for a run that does not exist is refused."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task, run_id="run-does-not-exist")

    assert outcome == _REJECTED


def test_a_mismatched_deployment_fails_closed(db: _TestDB) -> None:
    """A run must belong to the deployment the claim names."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    outcome = _claim(db, task, deployment_id="dep-not-this-one")

    assert outcome == _REJECTED
    state = _read_run(db, str(task.run_id))
    assert state["status"] == "queued"


def test_a_mismatched_attempt_or_binding_fails_closed(db: _TestDB) -> None:
    """The attempt and coding-task identities must match the durable spec."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    assert _claim(db, task, attempt_id="gat-not-this-one") == (
        _REJECTED
    )
    assert _claim(db, task, coding_task_id="gct-not-this-one") == (
        _REJECTED
    )
    assert _claim(db, task, user_id="someone-else") == _REJECTED
    state = _read_run(db, str(task.run_id))
    assert state["status"] == "queued"


def test_postgresql_failure_prevents_adapter_execution(
    db: _TestDB,
    monkeypatch: pytest.MonkeyPatch,
    stub_adapter: _StubAdapter,
) -> None:
    """Unreachable persistence is never permission to execute."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    def _boom(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("postgresql is unreachable")

    monkeypatch.setattr(coding_worker.AgentStore, "claim_run_for_acceptance", _boom)
    # The worker must observe the failure as a refusal, not as success.
    with pytest.raises(RuntimeError):
        _run_worker(db, task)

    assert stub_adapter.calls == 0, "the adapter was entered without acceptance"

    # The run was never left in a false accepted state.
    state = _read_run(db, str(task.run_id))
    assert state["status"] == "queued"
    assert state["started_at"] is None


def test_unavailable_persistence_is_refused(db: _TestDB) -> None:
    """With no durable store the claim is unavailable, never accepted."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    store = AgentStore(db=None)
    outcome = store.claim_run_for_acceptance(
        run_id=str(task.run_id or ""),
        deployment_id=str(task.deployment_id or ""),
        user_id=(task.execution_binding or {}).get("user_id"),
        thread_id=task.thread_id,
        source_message_id=task.source_message_id,
        attempt_id=str(task.attempt_id or ""),
        coding_task_id=str(task.coding_task_id or ""),
    )

    assert outcome == _UNAVAILABLE


# ---------------------------------------------------------------------------
# 14: survival of a worker disappearance.
# ---------------------------------------------------------------------------


def test_accepted_state_survives_a_worker_disappearance(
    db: _TestDB,
) -> None:
    """After acceptance and an abrupt stop, the run is still durably running."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    _claim(db, task)

    # The worker object disappears without any terminalization.
    state = _read_run(db, str(task.run_id))
    assert state["status"] == "running"
    assert state["started_at"] is not None
    assert state["ended_at"] is None
    assert state["error"] is None

    # A second reader, with a fresh session, sees the same thing.
    with db.get_session() as session:
        row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        assert row.status == "running"
        assert row.started_at == state["started_at"]


# ---------------------------------------------------------------------------
# 15-16: terminal and delivery semantics are unchanged.
# ---------------------------------------------------------------------------


def test_normal_success_still_persists_a_terminal_result(
    db: _TestDB,
    stub_adapter: _StubAdapter,
) -> None:
    """The normal path still reaches the existing terminal persistence."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    _run_worker(db, task, stub_adapter)

    state = _read_run(db, str(task.run_id))
    assert state["status"] == "succeeded"
    assert state["ended_at"] is not None

    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=str(task.run_id)).one()
        artifacts = (
            session.query(AgentRunArtifact).filter_by(run_id=run_row.id).all()
        )
    assert artifacts, "the coding-result artifact was not persisted"


def test_source_thread_result_is_not_duplicated(
    db: _TestDB,
    stub_adapter: _StubAdapter,
) -> None:
    """One attempt delivers exactly one source-thread result message."""
    dispatched = _dispatch_one(db)
    task = dispatched["task"]

    _run_worker(db, task, stub_adapter)

    with db.get_session() as session:
        messages = (
            session.query(ChatMessage)
            .filter_by(thread_id=task.thread_id, kind="coding_result")
            .all()
        )
    assert len(messages) == 1, [m.id for m in messages]
