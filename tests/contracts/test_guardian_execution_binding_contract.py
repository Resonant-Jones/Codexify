"""Guardian execution binding authority contract (Slice 2).

The Guardian Delegation Loop needs a Guardian-owned execution binding before
anything can be dispatched to a coding worker. These cases prove the binding
is minted from *trusted account context*, that a caller cannot widen it, that
the model is pinned rather than substituted, and that the persisted deployment
spec carries a binding the coding worker will accept byte-for-byte.

See ``guardian/core/guardian_execution_binding.py``,
``docs/architecture/guardian-delegation-loop-contract.md``, ADR-094, and
ADR-077.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from typing import Any
from uuid import uuid4

import psycopg
from psycopg import sql

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from guardian.agents.coding_agent_contracts import CodingExecutionBinding
from guardian.agents.execution_credentials import store_api_key
from guardian.agents.store import AgentStore
from guardian.core.guardian_execution_binding import (
    GUARDIAN_CODING_HARNESS_ID,
    GuardianExecutionBindingError,
    GuardianExecutionBindingRequest,
    resolve_guardian_execution_binding,
    resolve_guardian_reasoning_effort,
    validate_guardian_execution_binding,
)
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    Base,
    ChatMessage,
    ChatThread,
    Project,
    User,
)


@contextmanager
def _disposable_postgres_engine() -> Iterator[Engine]:
    """Use the existing TEST_DATABASE_URL authority to isolate each case."""
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        raise RuntimeError("TEST_DATABASE_URL must point to disposable PostgreSQL")
    database_name = f"codexify_guardian_binding_{uuid4().hex[:12]}"
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
    """Credential storage needs an encryption key to be present."""
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


def _seed_account(db: _TestDB, *, user_id: str = "account-1") -> dict[str, Any]:
    with db.get_session() as session:
        session.add(
            User(
                id=user_id,
                username=f"{user_id}-username",
                password_hash="hash",
            )
        )
        project = Project(
            user_id=user_id,
            name=f"project-{user_id}",
            description=None,
            icon=None,
        )
        session.add(project)
        session.flush()
        thread = ChatThread(
            user_id=user_id,
            title="Source thread",
            summary="",
            project_id=project.id,
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
    """Register one account-scoped credential and return its reference."""
    record = store_api_key(
        db,
        owner_scope="account",
        owner_id=user_id,
        provider_id=provider_id,
        api_key="sk-test-guardian-binding",
        funding_route="user_byok",
    )
    return str(record["credential_ref"])


def _request(
    seeded: dict[str, Any],
    *,
    credential_ref: str,
    provider_id: str = "openai",
    model_id: str = "gpt-4o",
    max_attempts: int = 1,
    reasoning_effort: str | None = None,
) -> GuardianExecutionBindingRequest:
    return GuardianExecutionBindingRequest(
        account_id=seeded["user_id"],
        thread_id=str(seeded["thread_id"]),
        source_message_id=str(seeded["source_message_id"]),
        project_id=str(seeded["project_id"]),
        coding_task_id="gct-test-1",
        attempt_id="gat-test-1",
        credential_ref=credential_ref,
        provider_id=provider_id,
        model_id=model_id,
        max_attempts=max_attempts,
        reasoning_effort=reasoning_effort,
    )


def test_binding_mints_from_trusted_account_context(db: _TestDB) -> None:
    """A binding resolves from the account's own registered credential."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    binding = resolve_guardian_execution_binding(
        db, _request(seeded, credential_ref=credential_ref)
    )

    assert binding["harness_id"] == GUARDIAN_CODING_HARNESS_ID
    assert binding["harness_selection_mode"] == "default"
    assert binding["credential_type"] == "api_key"
    assert binding["user_id"] == seeded["user_id"]
    assert binding["thread_id"] == str(seeded["thread_id"])
    assert binding["source_message_id"] == str(seeded["source_message_id"])
    assert binding["project_id"] == str(seeded["project_id"])
    assert binding["coding_task_id"] == "gct-test-1"
    assert binding["attempt_id"] == "gat-test-1"
    assert binding["max_attempts"] == 1


def test_binding_is_secret_free(db: _TestDB) -> None:
    """A binding carries a credential reference, never key material."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    binding = resolve_guardian_execution_binding(
        db, _request(seeded, credential_ref=credential_ref)
    )

    assert binding["credential_ref"]
    assert "api_key" not in binding
    assert "sk-test-guardian-binding" not in str(binding)
    serialized = str(binding)
    assert "encrypted_secret" not in serialized


def test_binding_validates_against_the_worker_gate(db: _TestDB) -> None:
    """The binding satisfies every field the coding worker requires."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    binding = resolve_guardian_execution_binding(
        db, _request(seeded, credential_ref=credential_ref)
    )

    # The worker re-derives the binding with from_dict and compares lineage.
    reparsed = CodingExecutionBinding.from_dict(binding)
    assert reparsed.harness_id == "pi"
    assert reparsed.credential_type == "api_key"
    assert reparsed.harness_selection_mode in {"default", "explicit"}
    assert 1 <= reparsed.max_attempts <= 3
    assert reparsed.coding_task_id == "gct-test-1"
    assert reparsed.attempt_id == "gat-test-1"


def test_binding_rejects_a_credential_from_another_account(db: _TestDB) -> None:
    """A credential the account does not own cannot authorize its binding."""
    seeded = _seed_account(db, user_id="account-1")
    # The credential belongs to a different account.
    other_ref = _seed_credential(db, user_id="account-2")

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(
            db, _request(seeded, credential_ref=other_ref)
        )

    assert excinfo.value.code == "guardian_binding_credential_unauthorized"


def test_binding_rejects_a_provider_the_credential_does_not_carry(
    db: _TestDB,
) -> None:
    """A caller cannot bind a provider the stored credential does not carry."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(
        db, user_id=seeded["user_id"], provider_id="openai"
    )

    # The request proposes a different provider than the stored credential.
    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(
            db,
            _request(
                seeded,
                credential_ref=credential_ref,
                provider_id="deepseek",
            ),
        )

    assert excinfo.value.code == "guardian_binding_credential_unauthorized"


def test_binding_fails_closed_without_an_account_credential(db: _TestDB) -> None:
    """No registered credential means no binding, and an explicit reason."""
    seeded = _seed_account(db)

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(
            db, _request(seeded, credential_ref="ccr_absent")
        )

    assert excinfo.value.code == "guardian_binding_credential_unauthorized"


def test_binding_fails_closed_on_missing_identity(db: _TestDB) -> None:
    """Missing lineage fails closed rather than producing a partial binding."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    request = _request(seeded, credential_ref=credential_ref)
    object.__setattr__(request, "account_id", "")
    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(db, request)

    assert excinfo.value.code == "guardian_binding_account_missing"


def test_binding_fails_closed_on_attempt_limit_out_of_range(db: _TestDB) -> None:
    """The attempt budget stays inside the range the worker accepts."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(
            db,
            _request(seeded, credential_ref=credential_ref, max_attempts=9),
        )

    assert excinfo.value.code == "guardian_binding_attempt_limit_invalid"


def test_binding_pins_exactly_one_model(db: _TestDB) -> None:
    """The model is named explicitly, so substitution is detectable."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    binding = resolve_guardian_execution_binding(
        db, _request(seeded, credential_ref=credential_ref, model_id="gpt-4o-mini")
    )

    assert binding["model_id"] == "gpt-4o-mini"
    # No alternative model may ride along in the binding.
    assert "actual_model_id" not in binding
    assert "model_id" in binding


def test_lineage_validation_rejects_a_redirected_binding(db: _TestDB) -> None:
    """A binding that claims a different attempt is refused."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])
    binding = resolve_guardian_execution_binding(
        db, _request(seeded, credential_ref=credential_ref)
    )

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        validate_guardian_execution_binding(
            binding,
            expected_thread_id=str(seeded["thread_id"]),
            expected_source_message_id=str(seeded["source_message_id"]),
            expected_coding_task_id="gct-test-1",
            expected_attempt_id="gat-other",
        )

    assert excinfo.value.code == "guardian_binding_attempt_id_mismatch"


def test_lineage_validation_accepts_the_minted_binding(db: _TestDB) -> None:
    """The minted binding satisfies the lineage it claims."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])
    binding = resolve_guardian_execution_binding(
        db, _request(seeded, credential_ref=credential_ref)
    )

    validate_guardian_execution_binding(
        binding,
        expected_thread_id=str(seeded["thread_id"]),
        expected_source_message_id=str(seeded["source_message_id"]),
        expected_coding_task_id="gct-test-1",
        expected_attempt_id="gat-test-1",
    )


def test_intent_creation_does_not_require_a_credential(
    db: _TestDB,
) -> None:
    """Creating a delegation intent must not depend on credential state.

    The execution binding is a dispatch-time authorization: it names the
    provider, model, and credential one concrete attempt will use. Minting it
    during intent creation would make intent creation depend on the account
    having a usable credential, and would bind an attempt that may never be
    dispatched.
    """
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationService,
    )

    seeded = _seed_account(db)
    # Deliberately no credential is registered for this account.

    service = GuardianDelegationService()
    service.configure_db(db)

    run = service._create_agent_run_link(
        intent_id="gdi-no-credential",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        plan_summary={"standardized_task_prompt": "Do the thing."},
        context_basis=[],
    )

    with db.get_session() as session:
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=run["deployment_id"])
            .one_or_none()
        )
    assert deployment is not None
    spec = dict(deployment.spec_json or {})

    # No binding is claimed, because none was established.
    assert "execution_binding" not in spec
    # The dispatch identifiers the binding will be minted against are present.
    assert spec["coding_task_id"] == run["coding_task_id"]
    assert spec["attempt_id"] == run["attempt_id"]


def test_dispatch_persists_a_worker_acceptable_binding(db: _TestDB) -> None:
    """The persisted deployment spec carries the binding the worker reads.

    The coding worker compares the task payload binding to the persisted
    deployment spec binding byte-for-byte, so the two must be identical.
    """
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationService,
    )

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)

    run = service._create_agent_run_link(
        intent_id="gdi-test-1",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        plan_summary={"standardized_task_prompt": "Do the thing."},
        context_basis=[],
    )

    binding = service._resolve_execution_binding(
        db=db,
        intent_id="gdi-test-1",
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

    with db.get_session() as session:
        deployment = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=run["deployment_id"])
            .one_or_none()
        )
        persisted_run = (
            session.query(AgentRun).filter_by(run_id=run["run_id"]).one_or_none()
        )

    assert deployment is not None
    assert persisted_run is not None
    spec = dict(deployment.spec_json or {})

    # The binding is persisted in the deployment spec.
    persisted_binding = spec.get("execution_binding")
    assert isinstance(persisted_binding, dict)
    assert persisted_binding == binding

    # It satisfies the worker's binding gate.
    reparsed = CodingExecutionBinding.from_dict(persisted_binding)
    assert reparsed.harness_id == "pi"
    assert reparsed.credential_type == "api_key"
    assert reparsed.thread_id == str(seeded["thread_id"])
    assert reparsed.source_message_id == str(seeded["source_message_id"])
    assert reparsed.user_id == seeded["user_id"]
    assert 1 <= reparsed.max_attempts <= 3

    # The binding is minted against the dispatch identifiers recorded in the
    # spec, so a later task payload can mirror the persisted binding exactly.
    assert spec["coding_task_id"] == run["coding_task_id"]
    assert spec["attempt_id"] == run["attempt_id"]
    assert reparsed.coding_task_id == run["coding_task_id"]
    assert reparsed.attempt_id == run["attempt_id"]


def test_persisted_binding_cannot_be_rewritten(db: _TestDB) -> None:
    """An established attempt authorization is immutable.

    A retry must mint a new attempt rather than rewrite an existing one, or
    the credential-lease authority and the coding worker could disagree
    about which authorization an attempt is running under.
    """
    from guardian.core.guardian_delegation_service import (
        GuardianDelegationService,
        GuardianDelegationValidationError,
    )

    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])

    service = GuardianDelegationService()
    service.configure_db(db)

    run = service._create_agent_run_link(
        intent_id="gdi-immutable",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        plan_summary={"standardized_task_prompt": "Do the thing."},
        context_basis=[],
    )

    binding = service._resolve_execution_binding(
        db=db,
        intent_id="gdi-immutable",
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

    # Writing the identical binding again is idempotent.
    service.persist_execution_binding(
        deployment_id=run["deployment_id"],
        execution_binding=binding,
    )

    # Writing a *different* binding for the same attempt is refused.
    redirected = {**binding, "model_id": "some-other-model"}
    with pytest.raises(GuardianDelegationValidationError) as excinfo:
        service.persist_execution_binding(
            deployment_id=run["deployment_id"],
            execution_binding=redirected,
        )
    assert (
        excinfo.value.detail
        == "guardian_delegation_execution_binding_already_established"
    )


# ---------------------------------------------------------------------------
# Guardian-owned reasoning effort.
#
# The binding is the authoritative carrier of the invocation options Guardian
# resolved. The effort reaches the worker only through it, so a worker task can
# never choose its own level and a caller-supplied task field can never widen
# the grant.
# ---------------------------------------------------------------------------


def test_binding_resolves_the_validated_deepseek_effort(db: _TestDB) -> None:
    """Guardian selects the validated DeepSeek default under its own authority."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(
        db, user_id=seeded["user_id"], provider_id="deepseek"
    )

    binding = resolve_guardian_execution_binding(
        db,
        _request(
            seeded,
            credential_ref=credential_ref,
            provider_id="deepseek",
            model_id="deepseek-v4-flash",
        ),
    )

    assert binding["reasoning_effort"] == "off"
    assert binding["schema_version"] == 2
    # The effort is carried by the binding, so it travels with the binding.
    assert CodingExecutionBinding.from_dict(binding).reasoning_effort == "off"


def test_binding_preserves_an_explicitly_selected_compatible_effort(
    db: _TestDB,
) -> None:
    """A separately authorized compatible effort is carried unmodified."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(
        db, user_id=seeded["user_id"], provider_id="deepseek"
    )

    binding = resolve_guardian_execution_binding(
        db,
        _request(
            seeded,
            credential_ref=credential_ref,
            provider_id="deepseek",
            model_id="deepseek-v4-flash",
            reasoning_effort="high",
        ),
    )

    assert binding["reasoning_effort"] == "high"


def test_binding_fails_closed_on_an_invalid_effort_token(db: _TestDB) -> None:
    """An effort the harness does not accept is refused, not repaired."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(
        db, user_id=seeded["user_id"], provider_id="deepseek"
    )

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(
            db,
            _request(
                seeded,
                credential_ref=credential_ref,
                provider_id="deepseek",
                model_id="deepseek-v4-flash",
                reasoning_effort="bogus",
            ),
        )

    assert excinfo.value.code == "guardian_binding_reasoning_effort_invalid"


def test_binding_fails_closed_instead_of_downgrading_a_positive_effort(
    db: _TestDB,
) -> None:
    """A positive effort is never silently downgraded to the lane default."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(
        db, user_id=seeded["user_id"], provider_id="deepseek"
    )

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(
            db,
            _request(
                seeded,
                credential_ref=credential_ref,
                provider_id="deepseek",
                model_id="deepseek-v4-flash",
                reasoning_effort="medium",
            ),
        )

    assert excinfo.value.code == "guardian_binding_reasoning_effort_unsupported"


def test_binding_fails_closed_on_an_effort_for_an_unvalidated_lane(
    db: _TestDB,
) -> None:
    """An unvalidated lane cannot authorize an effort it never validated."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    with pytest.raises(GuardianExecutionBindingError) as excinfo:
        resolve_guardian_execution_binding(
            db,
            _request(
                seeded,
                credential_ref=credential_ref,
                reasoning_effort="high",
            ),
        )

    assert excinfo.value.code == "guardian_binding_reasoning_effort_unsupported"


def test_binding_leaves_an_unrelated_lane_ungoverned(db: _TestDB) -> None:
    """An unvalidated lane keeps the harness default exactly as before."""
    seeded = _seed_account(db)
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])

    binding = resolve_guardian_execution_binding(
        db, _request(seeded, credential_ref=credential_ref)
    )

    assert binding["reasoning_effort"] is None
    assert binding["schema_version"] == 1


def test_effort_resolution_is_bounded_to_the_validated_lane() -> None:
    """Only the validated lane governs an effort; every other lane is ungoverned."""
    assert (
        resolve_guardian_reasoning_effort(
            provider_id="deepseek", model_id="deepseek-v4-flash"
        )
        == "off"
    )
    assert (
        resolve_guardian_reasoning_effort(
            provider_id="deepseek", model_id="deepseek-v4-flash", requested="high"
        )
        == "high"
    )
    assert (
        resolve_guardian_reasoning_effort(
            provider_id="deepseek", model_id="deepseek-chat"
        )
        is None
    )
    assert (
        resolve_guardian_reasoning_effort(
            provider_id="openai", model_id="gpt-4o"
        )
        is None
    )


def _governed_binding_payload(**overrides: Any) -> dict[str, Any]:
    """One schema-version-2 binding payload for the DeepSeek lane."""
    payload = {
        "binding_id": "xeb-effort-1",
        "schema_version": 2,
        "harness_id": "pi",
        "harness_selection_mode": "default",
        "provider_id": "deepseek",
        "model_id": "deepseek-v4-flash",
        "funding_route": "user_byok",
        "placement": "container",
        "credential_ref": "ccr-effort-1",
        "credential_owner_scope": "account",
        "credential_owner_id": "account-1",
        "credential_type": "api_key",
        "credential_source_class": "account_api_key",
        "usage_policy_ref": None,
        "user_id": "account-1",
        "project_id": None,
        "thread_id": "thread-1",
        "source_message_id": "message-1",
        "coding_task_id": "coding-task-1",
        "attempt_id": "attempt-1",
        "max_attempts": 1,
        "authorization_evidence_ref": "xeb-effort-1",
        "reasoning_effort": "off",
    }
    payload.update(overrides)
    return payload


def test_a_governing_binding_requires_its_effort() -> None:
    """A governing binding can never be persisted without the effort."""
    payload = _governed_binding_payload()
    payload.pop("reasoning_effort")

    with pytest.raises(ValueError) as excinfo:
        CodingExecutionBinding.from_dict(payload)

    assert str(excinfo.value) == "execution_binding_reasoning_effort_missing"


def test_a_governing_binding_rejects_an_unvalidated_level() -> None:
    """A level the lane never validated cannot ride in a governing binding."""
    with pytest.raises(ValueError) as excinfo:
        CodingExecutionBinding.from_dict(
            _governed_binding_payload(reasoning_effort="medium")
        )

    assert str(excinfo.value) == "execution_binding_reasoning_effort_unsupported"


def test_a_governing_binding_rejects_a_level_for_another_lane() -> None:
    """The effort is bound to the lane the binding pins."""
    with pytest.raises(ValueError) as excinfo:
        CodingExecutionBinding.from_dict(
            _governed_binding_payload(model_id="gpt-4o")
        )

    assert str(excinfo.value) == "execution_binding_reasoning_effort_unsupported"


def test_a_legacy_binding_is_never_reinterpreted_as_governing() -> None:
    """A version 1 binding keeps the harness default, even if one is present."""
    payload = _governed_binding_payload(schema_version=1)

    binding = CodingExecutionBinding.from_dict(payload)

    assert binding.schema_version == 1
    assert binding.reasoning_effort is None


# ---------------------------------------------------------------------------
# Service-owned credential binding truthfulness.
#
# A binding minted from a service-owned credential must carry that
# credential's real ownership and funding route, and the execution-time
# revalidation must accept it as such. Relabelling a service credential as
# account-owned, rerouting its funding, or pointing it at a foreign usage
# policy is refused.
# ---------------------------------------------------------------------------


_SERVICE_BINDING_OWNER = "codexify-service"
_SERVICE_BINDING_ROUTE = "codexify_metered"
_SERVICE_BINDING_POLICY = "usage-policy-codexify-metered"
_SERVICE_BINDING_SECRET = "sk-test-service-guardian-binding"
_SERVICE_BINDING_MODEL = "deepseek-v4-flash"


def _seed_service_credential(
    db: _TestDB,
    *,
    user_id: str = "account-1",
    provider_id: str = "deepseek",
    allowed_account_ids: list[str] | None = None,
    allowed_model_ids: list[str] | None = None,
    usage_policy_ref: str | None = _SERVICE_BINDING_POLICY,
) -> str:
    """Register one service-owned credential and return its reference."""
    record = store_api_key(
        db,
        owner_scope="service",
        owner_id=_SERVICE_BINDING_OWNER,
        provider_id=provider_id,
        api_key=_SERVICE_BINDING_SECRET,
        funding_route=_SERVICE_BINDING_ROUTE,
        allowed_account_ids=(
            allowed_account_ids if allowed_account_ids is not None else [user_id]
        ),
        allowed_model_ids=(
            allowed_model_ids
            if allowed_model_ids is not None
            else [_SERVICE_BINDING_MODEL]
        ),
        usage_policy_ref=usage_policy_ref,
    )
    return str(record["credential_ref"])


def test_service_owned_binding_keeps_its_ownership_and_funding_route(
    db: _TestDB,
) -> None:
    """A service credential's binding is not relabelled as account-owned."""
    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])

    binding = resolve_guardian_execution_binding(
        db,
        _request(
            seeded,
            credential_ref=credential_ref,
            provider_id="deepseek",
            model_id=_SERVICE_BINDING_MODEL,
        ),
    )

    assert binding["credential_ref"] == credential_ref
    assert binding["credential_owner_scope"] == "service"
    assert binding["credential_owner_id"] == _SERVICE_BINDING_OWNER
    assert binding["credential_source_class"] == "service_api_key"
    assert binding["credential_type"] == "api_key"
    assert binding["funding_route"] == _SERVICE_BINDING_ROUTE
    assert binding["usage_policy_ref"] == _SERVICE_BINDING_POLICY
    assert binding["provider_id"] == "deepseek"
    assert binding["model_id"] == _SERVICE_BINDING_MODEL

    # The binding stays secret-free.
    assert _SERVICE_BINDING_SECRET not in str(binding)

    # The binding round-trips through the validator the worker applies.
    round_tripped = CodingExecutionBinding.from_dict(binding)
    assert round_tripped.credential_owner_scope == "service"
    assert round_tripped.funding_route == _SERVICE_BINDING_ROUTE


def test_service_owned_binding_is_authorized_at_the_execution_time_boundary(
    db: _TestDB,
) -> None:
    """The execution-time revalidation accepts the service binding as bound."""
    from guardian.agents.execution_credentials import authorize_binding_credential

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])
    binding = resolve_guardian_execution_binding(
        db,
        _request(
            seeded,
            credential_ref=credential_ref,
            provider_id="deepseek",
            model_id=_SERVICE_BINDING_MODEL,
        ),
    )

    authorized = authorize_binding_credential(
        db, binding=binding, account_id=seeded["user_id"]
    )
    assert authorized["owner_scope"] == "service"
    assert authorized["owner_id"] == _SERVICE_BINDING_OWNER
    assert authorized["funding_route"] == _SERVICE_BINDING_ROUTE
    assert authorized["usage_policy_ref"] == _SERVICE_BINDING_POLICY


def test_relabelling_service_ownership_or_funding_is_refused(
    db: _TestDB,
) -> None:
    """A service credential may not be presented as account-owned."""
    from guardian.agents.execution_credentials import (
        CredentialAuthorityError,
        authorize_binding_credential,
    )

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])
    binding = resolve_guardian_execution_binding(
        db,
        _request(
            seeded,
            credential_ref=credential_ref,
            provider_id="deepseek",
            model_id=_SERVICE_BINDING_MODEL,
        ),
    )

    relabelled = {**binding, "credential_owner_scope": "account"}
    with pytest.raises(
        CredentialAuthorityError, match="credential_owner_scope_mismatch"
    ):
        authorize_binding_credential(
            db, binding=relabelled, account_id=seeded["user_id"]
        )

    rerouted = {**binding, "funding_route": "user_byok"}
    with pytest.raises(
        CredentialAuthorityError, match="credential_funding_route_mismatch"
    ):
        authorize_binding_credential(
            db, binding=rerouted, account_id=seeded["user_id"]
        )

    reowned = {**binding, "credential_owner_id": seeded["user_id"]}
    with pytest.raises(
        CredentialAuthorityError, match="credential_owner_mismatch"
    ):
        authorize_binding_credential(
            db, binding=reowned, account_id=seeded["user_id"]
        )


def test_service_binding_with_a_foreign_usage_policy_is_refused(
    db: _TestDB,
) -> None:
    """A service binding may not point at another usage policy."""
    from guardian.agents.execution_credentials import (
        CredentialAuthorityError,
        authorize_binding_credential,
    )

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])
    binding = resolve_guardian_execution_binding(
        db,
        _request(
            seeded,
            credential_ref=credential_ref,
            provider_id="deepseek",
            model_id=_SERVICE_BINDING_MODEL,
        ),
    )

    with pytest.raises(
        CredentialAuthorityError, match="service_usage_policy_mismatch"
    ):
        authorize_binding_credential(
            db,
            binding={**binding, "usage_policy_ref": "other-policy"},
            account_id=seeded["user_id"],
        )


def test_service_credential_with_an_incompatible_funding_route_is_refused(
    db: _TestDB,
) -> None:
    """A service credential may not carry a route that is not a service route."""
    from guardian.agents.execution_credentials import (
        CredentialAuthorityError,
        authorize_credential_selection,
    )
    from guardian.db.models import CodingExecutionCredential

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])

    # The registration boundary refuses a non-service route for a service
    # credential, so the only way to reach the state is a row whose route was
    # changed afterwards. The authority must still deny it.
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(credential_ref=credential_ref)
            .one_or_none()
        )
        assert row is not None
        row.funding_route = "user_byok"
        session.commit()

    with pytest.raises(
        CredentialAuthorityError, match="service_funding_route_invalid"
    ):
        authorize_credential_selection(
            db,
            credential_ref=credential_ref,
            account_id=seeded["user_id"],
            provider_id="deepseek",
            model_id=_SERVICE_BINDING_MODEL,
        )


def test_service_credential_with_a_provider_mismatch_is_refused(
    db: _TestDB,
) -> None:
    """A service credential may not be used for a provider it does not carry."""
    from guardian.agents.execution_credentials import (
        CredentialAuthorityError,
        authorize_credential_selection,
    )

    seeded = _seed_account(db)
    credential_ref = _seed_service_credential(db, user_id=seeded["user_id"])

    with pytest.raises(
        CredentialAuthorityError, match="credential_provider_mismatch"
    ):
        authorize_credential_selection(
            db,
            credential_ref=credential_ref,
            account_id=seeded["user_id"],
            provider_id="openai",
            model_id=_SERVICE_BINDING_MODEL,
        )
