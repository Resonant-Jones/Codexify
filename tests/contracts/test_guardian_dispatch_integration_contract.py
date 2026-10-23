"""Guardian delegated-task dispatch integration contract (Slice 3).

These cases exercise the dispatch path end to end against a disposable
PostgreSQL: a Guardian delegation intent is dispatched, and the resulting
coding-execution task is proven to carry the *same* binding that was
persisted into the deployment spec, because the coding worker compares the two
byte-for-byte and rejects a mismatch.

See ``guardian/core/guardian_dispatch.py``,
``guardian/core/guardian_execution_binding.py``, and
``guardian/core/guardian_permission_posture.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import os
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import sql

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from guardian.agents.execution_credentials import store_api_key
from guardian.core.guardian_delegation_service import (
    GuardianDelegationService,
    GuardianDelegationValidationError,
)
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    Base,
    ChatMessage,
    ChatThread,
    CodingExecutionCredential,
    Project,
    User,
)


@contextmanager
def _disposable_postgres_engine() -> Iterator[Engine]:
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        raise RuntimeError("TEST_DATABASE_URL must point to disposable PostgreSQL")
    database_name = f"codexify_guardian_dispatch_{uuid4().hex[:12]}"
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
    """Keep the coding-execution queue in memory for each case."""
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


def _seed_credential(
    db: _TestDB,
    *,
    user_id: str = "account-1",
    provider_id: str = "openai",
) -> str:
    record = store_api_key(
        db,
        owner_scope="account",
        owner_id=user_id,
        provider_id=provider_id,
        api_key="sk-test-guardian-dispatch",
        funding_route="user_byok",
    )
    return str(record["credential_ref"])


def _link_run(service: GuardianDelegationService, seeded: dict[str, Any]) -> dict[str, Any]:
    return service._create_agent_run_link(
        intent_id="gdi-dispatch-1",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        plan_summary={"standardized_task_prompt": "Do the thing."},
        context_basis=[],
    )


def test_dispatch_persists_the_binding_and_enqueues_one_task(
    db: _TestDB,
) -> None:
    """A dispatch persists the binding and enqueues exactly one task."""
    from guardian.queue.redis_queue import dequeue_coding_execution
    from guardian.tasks.types import CodingExecutionTask

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    result = service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )

    # Exactly one task was enqueued.
    payload = dequeue_coding_execution(block=False)
    assert payload is not None
    assert dequeue_coding_execution(block=False) is None

    task = CodingExecutionTask.from_dict(payload)

    # The task's binding is byte-identical to the persisted one. The coding
    # worker compares exactly these two and rejects a mismatch.
    with db.get_session() as session:
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=run["deployment_id"])
            .one_or_none()
        )
    assert deployment is not None
    spec = dict(deployment.spec_json or {})
    persisted_binding = spec.get("execution_binding")
    assert isinstance(persisted_binding, dict)
    assert task.execution_binding == persisted_binding

    # The dispatch receipt names the queued task.
    assert result["dispatch"]["state"] == "dispatched"
    assert result["dispatch"]["task_id"] == payload["task_id"]
    assert result["dispatch"]["dispatch_count"] == 1
    assert result["execution_binding_id"] == persisted_binding["binding_id"]


def test_dispatch_task_carries_the_guardian_lineage(db: _TestDB) -> None:
    """The queued task points back at the source thread and attempt."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )

    payload = dequeue_coding_execution(block=False)
    assert payload is not None

    assert payload["origin"] == "guardian_delegation_intent"
    assert payload["thread_id"] == seeded["thread_id"]
    assert payload["source_message_id"] == seeded["source_message_id"]
    assert payload["source_thread_id"] == seeded["thread_id"]
    assert payload["user_id"] == seeded["user_id"]
    assert payload["attempt_id"] == run["attempt_id"]
    assert payload["coding_task_id"] == run["coding_task_id"]
    assert payload["run_id"] == run["run_id"]
    assert payload["deployment_id"] == run["deployment_id"]


def test_dispatch_refuses_without_an_account_credential(db: _TestDB) -> None:
    """A dispatch with no account credential fails closed."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )

    seeded = _seed_account(db)
    # No credential registered for this account.

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError):
        service.dispatch_delegated_task(
            intent_id="gdi-dispatch-1",
            deployment_id=run["deployment_id"],
            run_id=run["run_id"],
            attempt_id=run["attempt_id"],
            coding_task_id=run["coding_task_id"],
            instructions="Do the thing.",
            repo_root="/workspace/project",
            thread_id=seeded["thread_id"],
            source_message_id=seeded["source_message_id"],
            user_id=seeded["user_id"],
            project_id=seeded["project_id"],
        )


def test_dispatch_does_not_enqueue_when_authorization_fails(
    db: _TestDB,
) -> None:
    """A refused dispatch queues nothing."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationValidationError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    # A second dispatch of the same attempt is refused: the persisted
    # binding for an established attempt is immutable, so a re-dispatch
    # cannot silently re-authorize the attempt under a different one.
    service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )
    with pytest.raises(GuardianDelegationValidationError):
        service.dispatch_delegated_task(
            intent_id="gdi-dispatch-1",
            deployment_id=run["deployment_id"],
            run_id=run["run_id"],
            attempt_id=run["attempt_id"],
            coding_task_id=run["coding_task_id"],
            instructions="Do the thing.",
            repo_root="/workspace/project",
            thread_id=seeded["thread_id"],
            source_message_id=seeded["source_message_id"],
            user_id=seeded["user_id"],
            project_id=seeded["project_id"],
        )

    # Exactly one task was queued by the first dispatch; the refused second
    # dispatch queued nothing.
    assert dequeue_coding_execution(block=False) is not None
    assert dequeue_coding_execution(block=False) is None


def test_dispatch_persists_the_binding_before_queueing(db: _TestDB) -> None:
    """The binding is durable before the task is queued.

    A crash between the two leaves a durable, inspectable attempt rather
    than an orphaned task that the worker would reject for a missing binding.
    """
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )

    with db.get_session() as session:
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=run["deployment_id"])
            .one_or_none()
        )
    assert deployment is not None
    spec = dict(deployment.spec_json or {})
    assert spec.get("execution_binding")

    payload = dequeue_coding_execution(block=False)
    assert payload is not None
    assert payload["execution_binding"] == spec["execution_binding"]


def test_dispatch_records_the_attempt_run_linkage(db: _TestDB) -> None:
    """The run link and the dispatch refer to the same attempt."""
    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    result = service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )

    dispatch = result["dispatch"]
    assert dispatch["intent_id"] == "gdi-dispatch-1"
    assert dispatch["deployment_id"] == run["deployment_id"]
    assert dispatch["run_id"] == run["run_id"]
    assert dispatch["attempt_id"] == run["attempt_id"]
    assert dispatch["coding_task_id"] == run["coding_task_id"]

    with db.get_session() as session:
        persisted_run = (
            session.query(AgentRun).filter_by(run_id=run["run_id"]).one_or_none()
        )
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=run["deployment_id"])
            .one_or_none()
        )
    assert persisted_run is not None
    assert deployment is not None
    # The run points at the same deployment the dispatch persisted the binding
    # against. (AgentRun.deployment_id is the numeric FK; the external id
    # lives on AgentDeployment.)
    assert int(persisted_run.deployment_id) == int(deployment.id)


def test_dispatch_refuses_a_binding_rewrite_for_the_same_attempt(
    db: _TestDB,
) -> None:
    """An established attempt authorization cannot be rewritten."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationValidationError,
    )

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    binding = service._resolve_execution_binding(
        db=db,
        intent_id="gdi-dispatch-1",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        coding_task_id=run["coding_task_id"],
        attempt_id=run["attempt_id"],
    )
    service.persist_execution_binding(
        deployment_id=run["deployment_id"],
        execution_binding=binding,
    )

    with pytest.raises(GuardianDelegationValidationError):
        service.persist_execution_binding(
            deployment_id=run["deployment_id"],
            execution_binding={**binding, "model_id": "another-model"},
        )


def test_dispatch_carries_the_guardian_resolved_reasoning_effort(
    db: _TestDB,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The queued task carries the effort Guardian resolved, unchanged.

    The binding is the carrier: Guardian persists it into the deployment
    specification and mirrors it into the queued task, and the two agree
    byte-for-byte. That equality is also what makes a tampered effort
    detectable before the harness runs.
    """
    from guardian.queue.redis_queue import dequeue_coding_execution

    # The lane's model must be the validated one, not an ambient override.
    monkeypatch.delenv("DEEPSEEK_CHAT_MODEL", raising=False)
    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"], provider_id="deepseek")

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )

    payload = dequeue_coding_execution(block=False)
    assert payload is not None

    queued_binding = payload["execution_binding"]
    assert queued_binding["schema_version"] == 2
    assert queued_binding["reasoning_effort"] == "off"

    with db.get_session() as session:
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=run["deployment_id"])
            .one_or_none()
        )
    assert deployment is not None
    spec = dict(deployment.spec_json or {})
    persisted_binding = spec.get("execution_binding")
    assert isinstance(persisted_binding, dict)

    # The persisted specification and the dispatched task agree.
    assert persisted_binding == queued_binding
    assert persisted_binding["reasoning_effort"] == "off"


def test_dispatch_leaves_an_unvalidated_lane_ungoverned(db: _TestDB) -> None:
    """A lane with no validated effort rule keeps the harness default.

    The binding carries no effort for that lane, so the worker forwards no
    value and the harness behaves exactly as it did before the contract.
    """
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )

    payload = dequeue_coding_execution(block=False)
    assert payload is not None

    queued_binding = payload["execution_binding"]
    assert queued_binding["schema_version"] == 1
    assert queued_binding["reasoning_effort"] is None


# ---------------------------------------------------------------------------
# Service-owned credential selection.
#
# A service-owned credential may serve an account invocation when the
# service's own recorded policy authorizes that account, provider, model,
# funding route, and usage policy (ADR-094 sections 12 and 34). These cases
# prove that the delegation path can reach such a credential, that the minted
# binding keeps the credential's real ownership and funding route, and that
# every unauthorized or ambiguous case fails closed before anything is
# enqueued.
# ---------------------------------------------------------------------------


_SERVICE_OWNER = "codexify-service"
_SERVICE_FUNDING_ROUTE = "codexify_metered"
_SERVICE_POLICY = "usage-policy-codexify-metered"
_SERVICE_SECRET = "sk-test-service-guardian-dispatch"
_SERVICE_MODEL = "deepseek-v4-flash"
_SERVICE_PROVIDER = "deepseek"


def _seed_service_credential(
    db: _TestDB,
    *,
    user_id: str = "account-1",
    provider_id: str = _SERVICE_PROVIDER,
    funding_route: str = _SERVICE_FUNDING_ROUTE,
    allowed_account_ids: list[str] | None = None,
    allowed_model_ids: list[str] | None = None,
    usage_policy_ref: str | None = _SERVICE_POLICY,
    owner_id: str = _SERVICE_OWNER,
    api_key: str = _SERVICE_SECRET,
) -> str:
    """Register one service-owned credential and return its reference."""
    record = store_api_key(
        db,
        owner_scope="service",
        owner_id=owner_id,
        provider_id=provider_id,
        api_key=api_key,
        funding_route=funding_route,
        allowed_account_ids=(
            allowed_account_ids if allowed_account_ids is not None else [user_id]
        ),
        allowed_model_ids=(
            allowed_model_ids if allowed_model_ids is not None else [_SERVICE_MODEL]
        ),
        usage_policy_ref=usage_policy_ref,
    )
    return str(record["credential_ref"])


def _dispatch(
    service: GuardianDelegationService,
    seeded: dict[str, Any],
    run: dict[str, Any],
) -> dict[str, Any]:
    """Run one delegated dispatch for the seeded account."""
    return service.dispatch_delegated_task(
        intent_id="gdi-dispatch-1",
        deployment_id=run["deployment_id"],
        run_id=run["run_id"],
        attempt_id=run["attempt_id"],
        coding_task_id=run["coding_task_id"],
        instructions="Do the thing.",
        repo_root="/workspace/project",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        user_id=seeded["user_id"],
        project_id=seeded["project_id"],
    )


def _binding_cause(exc: BaseException):
    """Return the binding error that caused a dispatch failure."""
    from guardian.core.guardian_execution_binding import (
        GuardianExecutionBindingError,
    )

    cause = exc.__cause__
    assert isinstance(cause, GuardianExecutionBindingError), (
        f"expected a GuardianExecutionBindingError cause, got {cause!r}"
    )
    return cause


def _persisted_binding(db: _TestDB, deployment_id: str) -> dict[str, Any]:
    with db.get_session() as session:
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=deployment_id)
            .one_or_none()
        )
    assert deployment is not None
    spec = dict(deployment.spec_json or {})
    binding = spec.get("execution_binding")
    assert isinstance(binding, dict)
    return binding


def test_dispatch_persists_a_service_owned_binding_and_enqueues_one_task(
    db: _TestDB,
) -> None:
    """A policy-authorized service credential serves the account invocation."""
    from guardian.queue.redis_queue import dequeue_coding_execution
    from guardian.tasks.types import CodingExecutionTask

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    result = _dispatch(service, seeded, run)

    # Exactly one task was enqueued.
    payload = dequeue_coding_execution(block=False)
    assert payload is not None
    assert dequeue_coding_execution(block=False) is None

    task = CodingExecutionTask.from_dict(payload)
    binding = _persisted_binding(db, run["deployment_id"])

    # The queued binding is byte-identical to the durable one.
    assert task.execution_binding == binding

    # Ownership and funding are the credential's own, not rewritten.
    assert binding["credential_ref"] == credential_ref
    assert binding["credential_owner_scope"] == "service"
    assert binding["credential_owner_id"] == _SERVICE_OWNER
    assert binding["credential_source_class"] == "service_api_key"
    assert binding["credential_type"] == "api_key"
    assert binding["funding_route"] == _SERVICE_FUNDING_ROUTE
    assert binding["usage_policy_ref"] == _SERVICE_POLICY

    # The provider/model lane is the one the credential and runtime pin.
    assert binding["provider_id"] == _SERVICE_PROVIDER
    assert binding["model_id"] == _SERVICE_MODEL

    # The invocation lineage is intact.
    assert binding["user_id"] == seeded["user_id"]
    assert binding["project_id"] == str(seeded["project_id"])
    assert binding["thread_id"] == str(seeded["thread_id"])
    assert binding["source_message_id"] == str(seeded["source_message_id"])
    assert binding["attempt_id"] == run["attempt_id"]
    assert binding["coding_task_id"] == run["coding_task_id"]
    assert binding["authorization_evidence_ref"] == binding["binding_id"]

    # No secret material reaches the durable or the queued payload.
    assert _SERVICE_SECRET not in str(binding)
    assert _SERVICE_SECRET not in str(payload)

    assert result["dispatch"]["state"] == "dispatched"
    assert result["dispatch"]["dispatch_count"] == 1
    assert result["execution_binding_id"] == binding["binding_id"]


def test_dispatch_refuses_a_service_credential_whose_account_policy_denies(
    db: _TestDB,
) -> None:
    """A service credential that does not name this account is not usable."""
    from guardian.agents.execution_credentials import (
        CredentialAuthorityError,
        authorize_credential_selection,
    )
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(
        db, allowed_account_ids=["some-other-account"]
    )

    # The credential authority is the boundary that denies this.
    with pytest.raises(
        CredentialAuthorityError, match="service_account_policy_denied"
    ):
        authorize_credential_selection(
            db,
            credential_ref=credential_ref,
            account_id=seeded["user_id"],
            provider_id=_SERVICE_PROVIDER,
            model_id=_SERVICE_MODEL,
        )

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError):
        _dispatch(service, seeded, run)

    # Nothing was enqueued.
    assert dequeue_coding_execution(block=False) is None


def test_dispatch_refuses_a_service_credential_whose_model_policy_denies(
    db: _TestDB,
) -> None:
    """A service credential may not serve a model outside its allow-list."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_service_credential(
        db, user_id=seeded["user_id"], allowed_model_ids=["deepseek-v4-pro"]
    )

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError) as excinfo:
        _dispatch(service, seeded, run)

    # The credential authority's own denial survives as the cause.
    cause = _binding_cause(excinfo.value)
    assert cause.code == "guardian_binding_credential_unauthorized"
    assert cause.detail == "service_model_policy_denied"

    assert dequeue_coding_execution(block=False) is None


def test_service_credential_registration_requires_a_usage_policy(
    db: _TestDB,
) -> None:
    """A service credential cannot be registered without a usage policy."""
    from guardian.agents.execution_credentials import CredentialAuthorityError

    with pytest.raises(CredentialAuthorityError, match="service_policy_incomplete"):
        store_api_key(
            db,
            owner_scope="service",
            owner_id=_SERVICE_OWNER,
            provider_id=_SERVICE_PROVIDER,
            api_key=_SERVICE_SECRET,
            funding_route=_SERVICE_FUNDING_ROUTE,
            allowed_account_ids=["account-1"],
            allowed_model_ids=[_SERVICE_MODEL],
            usage_policy_ref=None,
        )


def test_dispatch_refuses_a_service_credential_whose_usage_policy_was_removed(
    db: _TestDB,
) -> None:
    """A service credential must still carry its usage policy at selection."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])

    # The registration boundary refuses such a row, so the only way to reach
    # the state is a row whose policy was removed afterwards. The authority
    # must still deny it.
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(credential_ref=credential_ref)
            .one_or_none()
        )
        assert row is not None
        row.usage_policy_ref = None
        session.commit()

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError) as excinfo:
        _dispatch(service, seeded, run)

    cause = _binding_cause(excinfo.value)
    assert cause.code == "guardian_binding_credential_unauthorized"
    assert cause.detail == "service_usage_policy_missing"

    assert dequeue_coding_execution(block=False) is None


def test_dispatch_refuses_ambiguous_service_credentials(db: _TestDB) -> None:
    """Two authorized service credentials are not resolved by guessing."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_service_credential(
        db, user_id=seeded["user_id"], owner_id="codexify-service-a"
    )
    _seed_service_credential(
        db, user_id=seeded["user_id"], owner_id="codexify-service-b"
    )

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError) as excinfo:
        _dispatch(service, seeded, run)

    cause = _binding_cause(excinfo.value)
    assert cause.code == "guardian_binding_credential_selection_ambiguous"

    assert dequeue_coding_execution(block=False) is None


def test_dispatch_keeps_the_account_credential_when_the_account_owns_one(
    db: _TestDB,
) -> None:
    """An account that brings its own key keeps it, even if a service one exists."""
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"], provider_id="openai")
    _seed_service_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    _dispatch(service, seeded, run)
    binding = _persisted_binding(db, run["deployment_id"])

    # The account lane wins: its own ownership, funding route, and lane.
    assert binding["credential_owner_scope"] == "account"
    assert binding["credential_owner_id"] == seeded["user_id"]
    assert binding["funding_route"] == "user_byok"
    assert binding["provider_id"] == "openai"
    assert binding["model_id"] == "gpt-4o"

    assert dequeue_coding_execution(block=False) is not None


def test_dispatch_does_not_fall_back_to_service_after_a_rejected_account_credential(
    db: _TestDB,
) -> None:
    """A rejected account credential is not silently replaced by a service one."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    account_ref = _seed_credential(
        db, user_id=seeded["user_id"], provider_id="openai"
    )
    # The account credential is expired, so the authority rejects it.
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(credential_ref=account_ref)
            .one_or_none()
        )
        assert row is not None
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()

    # A service credential that *would* authorize is present and must not be
    # used to paper over the rejected account credential.
    _seed_service_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError) as excinfo:
        _dispatch(service, seeded, run)

    cause = _binding_cause(excinfo.value)
    assert cause.code == "guardian_binding_credential_unauthorized"
    assert cause.detail == "credential_expired"

    assert dequeue_coding_execution(block=False) is None


def test_delegation_entrypoint_exposes_no_credential_reference_override() -> None:
    """A caller cannot point the delegation at a credential of its choosing."""
    import inspect

    parameters = inspect.signature(
        GuardianDelegationService.dispatch_delegated_task
    ).parameters
    assert "credential_ref" not in parameters
    assert "credential_owner_scope" not in parameters
    assert "credential_owner_id" not in parameters
    assert "funding_route" not in parameters


def test_dispatch_never_falls_back_to_an_operator_credential(db: _TestDB) -> None:
    """An operator-owned credential is not an account fallback."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    # An operator credential exists. The credential authority refuses it for
    # account work outright, and the delegation path must never reach for it.
    store_api_key(
        db,
        owner_scope="operator",
        owner_id="operator-local",
        provider_id=_SERVICE_PROVIDER,
        api_key="sk-test-operator-fallback",
        funding_route="local_self_hosted",
    )

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError):
        _dispatch(service, seeded, run)

    assert dequeue_coding_execution(block=False) is None


def test_dispatch_refuses_a_revoked_service_credential(db: _TestDB) -> None:
    """A revoked service credential authorizes nothing."""
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationDispatchError,
    )
    from guardian.queue.redis_queue import dequeue_coding_execution

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])

    # Revocation destroys the at-rest secret, so the row is both revoked and
    # unusable.
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(credential_ref=credential_ref)
            .one_or_none()
        )
        assert row is not None
        row.status = "revoked"
        row.encrypted_secret = None
        session.commit()

    service = GuardianDelegationService()
    service.configure_db(db)
    run = _link_run(service, seeded)

    with pytest.raises(GuardianDelegationDispatchError) as excinfo:
        _dispatch(service, seeded, run)

    cause = _binding_cause(excinfo.value)
    assert cause.code == "guardian_binding_credential_unauthorized"
    assert cause.detail == "credential_revoked_or_missing"

    assert dequeue_coding_execution(block=False) is None
