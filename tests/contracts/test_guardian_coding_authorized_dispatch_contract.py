"""Guardian authorized coding dispatch contract.

One explicit, authenticated coding request reaches
``GuardianDelegationService.dispatch_delegated_task`` through one canonical,
durable, account-authorized admission path.

The proof uses the real HTTP intake (``POST /api/agents/coding/execute``),
disposable PostgreSQL for every authorization and persistence seam, and an
in-memory queue so no production inference credit is spent proving request
admission.

The cases cover the sixteen properties this integration has to hold:

1.  an authenticated account can explicitly submit an eligible coding request;
2.  Guardian resolves the canonical account from authentication;
3.  an authorized proposal resolves to a persisted, secret-free binding;
4.  the existing delegation dispatch method is reached;
5.  the accepted request produces exactly one correlated run;
6.  the task reaches the existing coding queue;
7.  replaying the same admitted attempt creates no second execution;
8.  concurrent duplicate admission is fenced by the durable authority
    boundary (PostgreSQL), not by a process-local lock;
9.  another account cannot use the original account's thread, message,
    credential, or delegation intent;
10. operator credentials cannot become account authority through fallback;
11. missing or incompatible credential authority rejects before enqueue;
12. missing repository authorization rejects before enqueue;
13. requested permissions cannot exceed their approved scope;
14. cancelled and superseded intents cannot dispatch;
15. queue records, events, and result metadata carry no plaintext credential
    material;
16. the result stays correlated with its original source thread and message.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterator
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import sessionmaker

from guardian.agents.execution_credentials import store_api_key
from guardian.agents.store import AgentStore
from guardian.core import session_store
from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.guardian_delegation_service import (
    GuardianDelegationService,
    GuardianDelegationValidationError,
)
from guardian.db.models import (
    AgentDeployment,
    AgentEvent,
    AgentRun,
    Base,
    ChatMessage,
    ChatThread,
    GuardianDelegationIntent,
    Project,
    RepositoryBinding,
    User,
)
from guardian.queue import redis_queue
from guardian.routes import agent_orchestration as routes

ACCOUNT_A = "authorized-dispatch-a@example.invalid"
ACCOUNT_B = "authorized-dispatch-b@example.invalid"
CREDENTIAL_SECRET = "sk-test-authorized-dispatch-secret"


# ---------------------------------------------------------------------------
# Disposable PostgreSQL authority
# ---------------------------------------------------------------------------


@contextmanager
def _disposable_postgres_engine() -> Iterator[Engine]:
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        raise RuntimeError("TEST_DATABASE_URL must point to disposable PostgreSQL")
    database_name = f"codexify_authorized_dispatch_{uuid4().hex[:12]}"
    admin_url = (
        make_url(base_url)
        .set(drivername="postgresql", database="postgres")
        .render_as_string(hide_password=False)
    )
    database_url = (
        make_url(base_url)
        .set(drivername="postgresql+psycopg", database=database_name)
        .render_as_string(hide_password=False)
    )
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
        connection.exec_driver_sql(
            f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"
        )


@pytest.fixture(scope="module")
def _postgres_engine() -> Iterator[Engine]:
    with _disposable_postgres_engine() as engine:
        Base.metadata.create_all(bind=engine)
        yield engine


@pytest.fixture
def db(_postgres_engine: Engine) -> _TestDB:
    _clear_disposable_tables(_postgres_engine)
    return _TestDB(_postgres_engine)


# ---------------------------------------------------------------------------
# Process-level fixtures
# ---------------------------------------------------------------------------


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
def _account_session_lane(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Authenticate through a signed account session, never a static key.

    The remote auth lane accepts the signed account session and rejects
    static API keys outright, so a request that only carries an operator key
    can never reach an account-scoped body.
    """
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "authorized-dispatch-proof-secret")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    monkeypatch.delenv("CODEXIFY_MULTI_USER_ENABLED", raising=False)
    token_store = session_store.SessionStore(
        redis_client=redis_queue._InMemoryRedis()
    )
    monkeypatch.setattr(session_store, "_SESSION_STORE", token_store)
    yield token_store


@pytest.fixture
def git_workspace(tmp_path: Path) -> Path:
    """A real Git working tree: the repository authority resolves a real root."""
    root = (tmp_path / "authorized-repo").resolve()
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "--quiet", str(root)],
        check=True,
        capture_output=True,
    )
    (root / "README.md").write_text("authorized dispatch proof\n", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


def _seed_account(db: _TestDB, *, user_id: str = ACCOUNT_A) -> dict[str, Any]:
    with db.get_session() as session:
        session.add(
            User(id=user_id, username=f"{user_id}-u", password_hash="inert-hash")
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
            title="Authorized coding source thread",
            summary="",
            project_id=project.id,
        )
        session.add(thread)
        session.flush()
        message = ChatMessage(
            thread_id=thread.id,
            user_id=user_id,
            role="user",
            content="Patch the failing return path and add a regression test.",
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


def _seed_repository_binding(
    db: _TestDB,
    *,
    project_id: int,
    root: Path,
) -> str:
    with db.get_session() as session:
        binding = RepositoryBinding(
            id=str(uuid4()),
            project_id=project_id,
            source_class="external_linked",
            canonical_root=str(root),
            is_active=True,
            provenance={"registration_source": "authorized_dispatch_contract"},
        )
        session.add(binding)
        session.commit()
        return binding.id


def _seed_credential(
    db: _TestDB,
    *,
    user_id: str = ACCOUNT_A,
    provider_id: str = "openai",
) -> str:
    record = store_api_key(
        db,
        owner_scope="account",
        owner_id=user_id,
        provider_id=provider_id,
        api_key=CREDENTIAL_SECRET,
        funding_route="user_byok",
    )
    return str(record["credential_ref"])


def _approved_intent(db: _TestDB, seeded: dict[str, Any]) -> dict[str, Any]:
    """Create the approved delegation intent that already owns the run link."""
    service = GuardianDelegationService()
    service.configure_db(db)
    intent = service.create_intent(
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
        approval_mode="scoped_auto",
    )
    assert intent["approval_state"] == "approved"
    assert intent["run_id"]
    return intent


def _issue_session(subject: str, *, purpose: str = ACCOUNT_SESSION_PURPOSE) -> str:
    token, _ = issue_session_token(subject=subject, purpose=purpose)
    session_store.get_session_store().store(token, subject, ttl=3600)
    return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _intake_payload(
    *,
    seeded: dict[str, Any],
    intent_id: str,
    account_id: str = ACCOUNT_A,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        # Empty identity proposals: the persisted run link owns the attempt.
        "coding_task_id": "",
        "thread_id": str(seeded["thread_id"]),
        "source_message_id": str(seeded["source_message_id"]),
        "attempt_id": "",
        "user_id": account_id,
        "project_id": None,
        "adapter_kind": "pi_codex_runner",
        # An empty instruction asserts nothing: the approved plan is what
        # runs. A non-empty value is a proposal that must match the approved
        # plan, and one that differs is refused.
        "instructions": "",
        "repo_root": None,
        "context_summary": None,
        "permission_policy": {
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": [],
            "max_runtime_seconds": 120,
        },
        "delegation_intent_id": intent_id,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def client(db: _TestDB, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(routes, "_store", AgentStore(db=db))
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


@pytest.fixture
def authorized(db: _TestDB, git_workspace: Path) -> dict[str, Any]:
    """A fully authorized account: thread, message, project, repo, credential."""
    seeded = _seed_account(db)
    _seed_repository_binding(
        db, project_id=seeded["project_id"], root=git_workspace
    )
    credential_ref = _seed_credential(db, user_id=seeded["user_id"])
    intent = _approved_intent(db, seeded)
    return {
        "seeded": seeded,
        "credential_ref": credential_ref,
        "intent": intent,
        "token": _issue_session(ACCOUNT_A),
        "repo_root": str(git_workspace),
    }


def _dequeue() -> dict[str, Any] | None:
    from guardian.queue.redis_queue import dequeue_coding_execution

    return dequeue_coding_execution(block=False)


def _drain() -> list[dict[str, Any]]:
    drained: list[dict[str, Any]] = []
    while True:
        payload = _dequeue()
        if payload is None:
            return drained
        drained.append(payload)


def _runs(db: _TestDB) -> list[Any]:
    with db.get_session() as session:
        return list(session.query(AgentRun).all())


def _deployment_spec(db: _TestDB, deployment_id: str) -> dict[str, Any]:
    with db.get_session() as session:
        row = (
            session.query(AgentDeployment)
            .filter_by(deployment_id=deployment_id)
            .one_or_none()
        )
        assert row is not None
        return dict(row.spec_json or {})


def _deployment_id_for_intent(db: _TestDB, intent: dict[str, Any]) -> str:
    """The deployment the intent's persisted run link owns."""
    with db.get_session() as session:
        run = (
            session.query(AgentRun)
            .filter_by(run_id=str(intent["run_id"]))
            .one_or_none()
        )
        assert run is not None
        deployment = (
            session.query(AgentDeployment)
            .filter_by(id=run.deployment_id)
            .one_or_none()
        )
        assert deployment is not None
        return str(deployment.deployment_id)


# ---------------------------------------------------------------------------
# 1, 2, 4, 5, 6, 16 — the admitted request
# ---------------------------------------------------------------------------


def test_authenticated_account_dispatches_one_authorized_coding_request(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """An authenticated account reaches the existing delegation dispatch."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "accepted"
    assert body["origin"] == "guardian_delegation_intent"

    # The canonical account came from the authenticated principal, and the
    # dispatch reused the intent's own persisted run link.
    assert body["account_id"] == ACCOUNT_A
    assert body["intent_id"] == intent["intent_id"]
    assert body["run_id"] == intent["run_id"]
    assert body["deployment_id"]
    assert body["coding_task_id"]
    assert body["attempt_id"]
    assert body["task_id"]

    # Exactly one correlated run exists, and it is the intent's run.
    runs = _runs(db)
    assert len(runs) == 1
    assert runs[0].run_id == intent["run_id"]
    assert runs[0].account_origin_user_id == ACCOUNT_A

    # Exactly one task reached the existing coding queue.
    queued = _drain()
    assert len(queued) == 1
    task = queued[0]
    assert task["run_id"] == body["run_id"]
    assert task["deployment_id"] == body["deployment_id"]
    assert task["coding_task_id"] == body["coding_task_id"]
    assert task["attempt_id"] == body["attempt_id"]
    assert task["user_id"] == ACCOUNT_A

    # The result stays correlated with its original source thread and message.
    assert task["thread_id"] == seeded["thread_id"]
    assert task["source_thread_id"] == seeded["thread_id"]
    assert task["source_message_id"] == seeded["source_message_id"]
    assert body["source_message_id"] == seeded["source_message_id"]
    assert body["thread_id"] == seeded["thread_id"]


def test_guardian_resolves_the_canonical_account_from_authentication(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """The account is the session subject, and a mismatched claim is refused."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["account_id"] == ACCOUNT_A
    assert len(_drain()) == 1

    # A caller-supplied identity is only a compatibility assertion.
    mismatch = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded, intent_id=intent["intent_id"], account_id=ACCOUNT_B
        ),
        headers=_headers(authorized["token"]),
    )
    assert mismatch.status_code == 403
    assert mismatch.json() == {"detail": "account_identity_mismatch"}
    # The refused request added no execution of its own.
    assert _drain() == []


def test_dispatch_reaches_the_existing_delegation_dispatch_method(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The delegation service's own dispatch method performs the dispatch."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    observed: list[dict[str, Any]] = []
    original = GuardianDelegationService.dispatch_delegated_task

    def spy(self: Any, **kwargs: Any) -> Any:
        observed.append(dict(kwargs))
        return original(self, **kwargs)

    monkeypatch.setattr(
        GuardianDelegationService, "dispatch_delegated_task", spy
    )

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )
    assert response.status_code == 200, response.text

    assert len(observed) == 1
    call = observed[0]
    assert call["intent_id"] == intent["intent_id"]
    assert call["run_id"] == intent["run_id"]
    assert call["user_id"] == ACCOUNT_A
    assert call["thread_id"] == seeded["thread_id"]
    assert call["source_message_id"] == seeded["source_message_id"]
    # The attempt identity is the persisted one, not a fresh one.
    assert call["attempt_id"] == response.json()["attempt_id"]
    assert call["coding_task_id"] == response.json()["coding_task_id"]


# ---------------------------------------------------------------------------
# 3, 15 — the effective binding
# ---------------------------------------------------------------------------


def test_authorized_proposal_resolves_to_a_persisted_secret_free_binding(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """The proposal resolves to a durable binding that carries no secret."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    spec = _deployment_spec(db, body["deployment_id"])
    binding = spec.get("execution_binding")
    assert isinstance(binding, dict)
    assert binding["binding_id"] == body["execution_binding_id"]
    assert binding["user_id"] == ACCOUNT_A
    assert binding["thread_id"] == str(seeded["thread_id"])
    assert binding["source_message_id"] == str(seeded["source_message_id"])
    assert binding["coding_task_id"] == body["coding_task_id"]
    assert binding["attempt_id"] == body["attempt_id"]
    assert binding["credential_ref"] == authorized["credential_ref"]
    assert binding["credential_owner_scope"] == "account"

    # The queued task carries the identical binding, byte for byte.
    queued = _drain()
    assert len(queued) == 1
    assert queued[0]["execution_binding"] == binding


def test_no_plaintext_credential_material_crosses_the_task_boundary(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """No queue record, event, or result metadata carries the secret."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    queued = _drain()
    assert len(queued) == 1
    spec = _deployment_spec(db, body["deployment_id"])

    with db.get_session() as session:
        events = list(session.query(AgentEvent).all())
    event_rows = [dict(row.payload or {}) for row in events]

    surfaces = {
        "response": json.dumps(body),
        "queued_task": json.dumps(queued[0], default=str),
        "deployment_spec": json.dumps(spec, default=str),
        "agent_events": json.dumps(event_rows, default=str),
    }
    for name, surface in surfaces.items():
        assert CREDENTIAL_SECRET not in surface, name

    # The credential is referenced, never carried. The binding may name the
    # credential *type*; it may never carry key material.
    assert authorized["credential_ref"] in surfaces["queued_task"]
    binding = queued[0]["execution_binding"]
    assert "api_key" not in binding
    assert "api_key" not in spec.get("execution_binding", {})
    assert "secret" not in binding
    assert binding["credential_type"] == "api_key"
    assert binding["credential_source_class"] == "account_api_key"


# ---------------------------------------------------------------------------
# 7, 8 — at-most-once admission
# ---------------------------------------------------------------------------


def test_replaying_the_same_admitted_attempt_creates_no_second_execution(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """A replay is refused and never produces an independent execution."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]
    payload = _intake_payload(seeded=seeded, intent_id=intent["intent_id"])

    first = client.post(
        "/api/agents/coding/execute",
        json=payload,
        headers=_headers(authorized["token"]),
    )
    assert first.status_code == 200, first.text

    replay = client.post(
        "/api/agents/coding/execute",
        json=payload,
        headers=_headers(authorized["token"]),
    )
    assert replay.status_code == 409, replay.text
    assert replay.json() == {
        "detail": "guardian_delegation_execution_binding_already_established"
    }

    # One run, one queued task, one execution.
    assert len(_runs(db)) == 1
    assert len(_drain()) == 1


def test_concurrent_duplicate_admission_is_fenced_by_postgresql(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """Two concurrent admissions of one attempt produce one execution.

    The fence is the deployment row lock in PostgreSQL, not a process-local
    lock and not a test double.
    """
    seeded = authorized["seeded"]
    intent = authorized["intent"]
    payload = _intake_payload(seeded=seeded, intent_id=intent["intent_id"])
    headers = _headers(authorized["token"])

    app = FastAPI()
    app.include_router(routes.router)

    def dispatch() -> Any:
        # Each request owns its own client so the two admissions really are
        # concurrent rather than serialized by a shared portal.
        return TestClient(app).post(
            "/api/agents/coding/execute",
            json=payload,
            headers=headers,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _index: dispatch(), range(2)))

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [200, 409], [response.text for response in responses]

    # Exactly one run, exactly one queued task.
    assert len(_runs(db)) == 1
    queued = _drain()
    assert len(queued) == 1
    assert queued[0]["attempt_id"]
    assert queued[0]["run_id"] == intent["run_id"]


# ---------------------------------------------------------------------------
# 9, 10 — cross-account and operator boundaries
# ---------------------------------------------------------------------------


def test_another_account_cannot_use_the_original_accounts_lineage(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """A different account cannot reach another account's intent."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]
    other_token = _issue_session(ACCOUNT_B)

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded, intent_id=intent["intent_id"], account_id=ACCOUNT_B
        ),
        headers=_headers(other_token),
    )

    assert response.status_code == 403, response.text
    assert response.json() == {
        "detail": "guardian_delegation_thread_account_mismatch"
    }
    assert _drain() == []
    assert len(_runs(db)) == 1


def test_operator_credentials_cannot_become_account_authority(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An operator principal never becomes an account for coding admission."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]
    payload = _intake_payload(seeded=seeded, intent_id=intent["intent_id"])

    # An operator session is not an account session.
    operator_token = _issue_session(
        "operator-authorized-dispatch", purpose=OPERATOR_SESSION_PURPOSE
    )
    operator_response = client.post(
        "/api/agents/coding/execute",
        json=payload,
        headers=_headers(operator_token),
    )
    assert operator_response.status_code in (401, 403), operator_response.text

    # A static API key is not an account principal either. The remote auth
    # lane rejects it before the body is read at all.
    monkeypatch.setenv("GUARDIAN_API_KEY", "operator-static-key")
    static_response = client.post(
        "/api/agents/coding/execute",
        json=payload,
        headers={"X-API-Key": "operator-static-key"},
    )
    assert static_response.status_code == 401, static_response.text

    assert _drain() == []
    assert len(_runs(db)) == 1


# ---------------------------------------------------------------------------
# 11, 12 — authority that must exist before enqueue
# ---------------------------------------------------------------------------


def test_missing_credential_authority_rejects_before_enqueue(
    db: _TestDB,
    client: TestClient,
    git_workspace: Path,
) -> None:
    """An account with no usable credential never reaches the queue."""
    seeded = _seed_account(db)
    _seed_repository_binding(
        db, project_id=seeded["project_id"], root=git_workspace
    )
    intent = _approved_intent(db, seeded)

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(_issue_session(ACCOUNT_A)),
    )

    assert response.status_code >= 400, response.text
    assert _drain() == []

    # The refusal happened before the attempt was authorized: no binding was
    # persisted, so nothing claims an authorization that was never granted.
    spec = _deployment_spec(db, _deployment_id_for_intent(db, intent))
    assert "execution_binding" not in spec

    # The intent is not consumed by an unauthorized request: a corrected
    # request may still be admitted against it.
    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=intent["intent_id"])
            .one()
        )
        assert row.intent_status == "accepted"
        assert row.approval_state == "approved"


def test_incompatible_provider_proposal_is_refused_before_enqueue(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """A proposal Guardian cannot authorize is refused, not substituted."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded,
            intent_id=intent["intent_id"],
            provider_id="anthropic",
        ),
        headers=_headers(authorized["token"]),
    )

    assert response.status_code >= 400, response.text
    assert _drain() == []


def test_missing_repository_authorization_rejects_before_enqueue(
    db: _TestDB,
    client: TestClient,
) -> None:
    """Without a project repository binding there is no authorizable workspace."""
    seeded = _seed_account(db)
    _seed_credential(db, user_id=seeded["user_id"])
    intent = _approved_intent(db, seeded)

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(_issue_session(ACCOUNT_A)),
    )

    assert response.status_code == 403, response.text
    assert response.json() == {
        "detail": "guardian_delegation_repository_binding_unavailable"
    }
    assert _drain() == []


# ---------------------------------------------------------------------------
# 13 — permission posture
# ---------------------------------------------------------------------------


def test_requested_permissions_cannot_exceed_the_approved_scope(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """A request may narrow the posture but never widen it."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    # Network access is not an enforceable capability for this lane, so a
    # request for it is refused rather than quietly downgraded.
    widened = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded,
            intent_id=intent["intent_id"],
            permission_policy={
                "allow_shell": True,
                "allow_network": True,
                "allow_write": True,
                "allowed_paths": [],
                "max_runtime_seconds": 120,
            },
        ),
        headers=_headers(authorized["token"]),
    )
    assert widened.status_code == 403, widened.text
    assert widened.json() == {
        "detail": "guardian_permission_allow_network_not_authorized"
    }
    assert _drain() == []

    # A narrower request is honoured exactly.
    narrowed = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded,
            intent_id=intent["intent_id"],
            permission_policy={
                "allow_shell": False,
                "allow_network": False,
                "allow_write": True,
                "allowed_paths": [],
                "max_runtime_seconds": 45,
            },
        ),
        headers=_headers(authorized["token"]),
    )
    assert narrowed.status_code == 200, narrowed.text

    queued = _drain()
    assert len(queued) == 1
    policy = queued[0]["permission_policy"]
    assert policy["allow_shell"] is False
    assert policy["allow_write"] is True
    assert policy["max_runtime_seconds"] == 45
    assert policy["allowed_paths"]


def test_a_requested_path_outside_the_authorized_scope_is_refused(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """A path outside the bound working tree is a widening, not a narrowing."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    widened = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded,
            intent_id=intent["intent_id"],
            permission_policy={
                "allow_shell": True,
                "allow_network": False,
                "allow_write": True,
                "allowed_paths": ["/etc"],
                "max_runtime_seconds": 120,
            },
        ),
        headers=_headers(authorized["token"]),
    )
    assert widened.status_code == 403, widened.text
    assert widened.json() == {
        "detail": "guardian_permission_allowed_paths_not_authorized"
    }
    assert _drain() == []

    # A relative path inside the bound working tree is a genuine narrowing.
    narrowed = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded,
            intent_id=intent["intent_id"],
            permission_policy={
                "allow_shell": True,
                "allow_network": False,
                "allow_write": True,
                "allowed_paths": ["src"],
                "max_runtime_seconds": 120,
            },
        ),
        headers=_headers(authorized["token"]),
    )
    assert narrowed.status_code == 200, narrowed.text
    queued = _drain()
    assert len(queued) == 1
    assert queued[0]["permission_policy"]["allowed_paths"] == ["src"]


# ---------------------------------------------------------------------------
# 14 — intent state
# ---------------------------------------------------------------------------


def test_cancelled_and_superseded_intents_cannot_dispatch(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """A cancelled or superseded intent is not a dispatch authority."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    service = GuardianDelegationService()
    service.configure_db(db)
    service.cancel_intent(intent["intent_id"])

    cancelled = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )
    assert cancelled.status_code == 409, cancelled.text
    assert cancelled.json() == {
        "detail": "guardian_delegation_intent_not_dispatchable"
    }
    assert _drain() == []

    superseded_intent = _approved_intent(db, seeded)
    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=superseded_intent["intent_id"])
            .one()
        )
        row.intent_status = "superseded"
        session.commit()

    superseded = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded, intent_id=superseded_intent["intent_id"]
        ),
        headers=_headers(authorized["token"]),
    )
    assert superseded.status_code == 409, superseded.text
    assert superseded.json() == {
        "detail": "guardian_delegation_intent_not_dispatchable"
    }
    assert _drain() == []


def test_an_unapproved_intent_cannot_dispatch(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """An approval decision is required before a dispatch is authorized."""
    seeded = authorized["seeded"]
    service = GuardianDelegationService()
    service.configure_db(db)
    pending = service.create_intent(
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        project_id=seeded["project_id"],
        approval_mode="human_required",
    )
    assert pending["approval_state"] == "pending"

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=pending["intent_id"]),
        headers=_headers(authorized["token"]),
    )

    assert response.status_code == 409, response.text
    assert response.json() == {"detail": "guardian_delegation_intent_not_approved"}
    assert _drain() == []


def test_the_admission_path_dispatches_the_named_intent_it_resolves(
    db: _TestDB,
    authorized: dict[str, Any],
) -> None:
    """The admitted attempt is the named intent's own persisted attempt."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]
    service = GuardianDelegationService()
    service.configure_db(db)

    receipt = service.dispatch_authorized_coding_request(
        account_id=ACCOUNT_A,
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        intent_id=intent["intent_id"],
        project_id=seeded["project_id"],
        instructions="",
        requested_permission_policy={
            "allow_shell": True,
            "allow_network": False,
            "allow_write": True,
            "allowed_paths": [],
            "max_runtime_seconds": 120,
        },
    )

    assert receipt["intent_id"] == intent["intent_id"]
    assert receipt["run_id"] == intent["run_id"]
    assert receipt["coding_task_id"]
    assert receipt["attempt_id"]
    assert receipt["task_id"]

    # One intent, one run, one queued task: the named intent's own lineage.
    with db.get_session() as session:
        intents = list(session.query(GuardianDelegationIntent).all())
    assert len(intents) == 1
    assert intents[0].intent_id == intent["intent_id"]
    assert len(_runs(db)) == 1

    queued = _drain()
    assert len(queued) == 1
    assert queued[0]["attempt_id"] == receipt["attempt_id"]
    assert queued[0]["user_id"] == ACCOUNT_A
    # The executed instructions are the approved plan's own instructions.
    assert queued[0]["instructions"] == intent["plan_summary"][
        "standardized_task_prompt"
    ]


def test_an_unsuccessful_enqueue_is_recorded_on_the_intent_axis(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An authorized attempt whose enqueue fails is failed, never succeeded.

    The intent axis owns the execution outcome, so a dispatch failure sets
    `intent_status` to `failed` and closes the linked run as terminal. The
    acceptance axis is untouched: the request was admitted, and admitting it
    did not fail.
    """
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    def failing_enqueue(_payload: dict[str, Any]) -> str:
        raise RuntimeError("queue is unavailable")

    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        failing_enqueue,
    )

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )

    assert response.status_code >= 400, response.text
    assert _drain() == []

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=intent["intent_id"])
            .one()
        )
        assert row.intent_status == "failed"
        assert row.acceptance_status == "accepted"

    runs = _runs(db)
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].error


def test_dispatch_cannot_substitute_different_work_under_an_approved_intent(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """An approved intent authorizes its own plan, and nothing else.

    Task A is approved. A request that tries to dispatch task B under the
    same intent is refused before the binding is persisted and before
    anything is enqueued.
    """
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    substituted = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded,
            intent_id=intent["intent_id"],
            instructions=(
                "Delete every file in the repository and commit the result."
            ),
        ),
        headers=_headers(authorized["token"]),
    )

    assert substituted.status_code == 409, substituted.text
    assert substituted.json() == {
        "detail": "guardian_delegation_instructions_not_bound_to_approved_plan"
    }

    # Nothing was authorized and nothing was queued.
    assert _drain() == []
    spec = _deployment_spec(db, _deployment_id_for_intent(db, intent))
    assert "execution_binding" not in spec

    # The intent itself is untouched: the refusal happened at admission,
    # before any dispatch was attempted.
    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=intent["intent_id"])
            .one()
        )
        assert row.intent_status == "accepted"
        assert row.approval_state == "approved"

    # The approved plan still dispatches exactly as approved.
    accepted = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(seeded=seeded, intent_id=intent["intent_id"]),
        headers=_headers(authorized["token"]),
    )
    assert accepted.status_code == 200, accepted.text
    queued = _drain()
    assert len(queued) == 1
    assert queued[0]["instructions"] == intent["plan_summary"][
        "standardized_task_prompt"
    ]


def test_dispatch_accepts_the_approved_plan_as_its_instruction_proposal(
    db: _TestDB,
    client: TestClient,
    authorized: dict[str, Any],
) -> None:
    """Echoing the approved plan back is accepted, not refused."""
    seeded = authorized["seeded"]
    intent = authorized["intent"]

    response = client.post(
        "/api/agents/coding/execute",
        json=_intake_payload(
            seeded=seeded,
            intent_id=intent["intent_id"],
            instructions=intent["plan_summary"]["standardized_task_prompt"],
        ),
        headers=_headers(authorized["token"]),
    )

    assert response.status_code == 200, response.text
    queued = _drain()
    assert len(queued) == 1
    assert queued[0]["instructions"] == intent["plan_summary"][
        "standardized_task_prompt"
    ]


def test_an_unnamed_request_never_forks_a_new_execution_lineage(
    db: _TestDB,
    authorized: dict[str, Any],
) -> None:
    """A dispatch must name its intent, so a duplicate cannot fork a lineage.

    An implicit intent would mint a fresh run, a fresh deployment, and a
    fresh queue submission on every duplicate request. The admission path
    refuses instead, so a duplicate request cannot produce independent
    execution authority.
    """
    seeded = authorized["seeded"]
    service = GuardianDelegationService()
    service.configure_db(db)

    with db.get_session() as session:
        intents_before = list(session.query(GuardianDelegationIntent).all())
    runs_before = len(_runs(db))

    with pytest.raises(GuardianDelegationValidationError) as excinfo:
        service.dispatch_authorized_coding_request(
            account_id=ACCOUNT_A,
            thread_id=seeded["thread_id"],
            source_message_id=seeded["source_message_id"],
            project_id=seeded["project_id"],
            instructions="Patch the failing return path.",
        )

    assert excinfo.value.detail == "guardian_delegation_intent_required"

    # No intent, no run, and no queue submission was created.
    with db.get_session() as session:
        intents_after = list(session.query(GuardianDelegationIntent).all())
    assert len(intents_after) == len(intents_before)
    assert len(_runs(db)) == runs_before
    assert _drain() == []


def test_concurrent_unnamed_admissions_create_no_execution_at_all(
    db: _TestDB,
    authorized: dict[str, Any],
) -> None:
    """Two concurrent unnamed admissions are both refused, and fork nothing."""
    seeded = authorized["seeded"]
    service = GuardianDelegationService()
    service.configure_db(db)

    with db.get_session() as session:
        intents_before = len(session.query(GuardianDelegationIntent).all())
    runs_before = len(_runs(db))

    def admit() -> str:
        try:
            service.dispatch_authorized_coding_request(
                account_id=ACCOUNT_A,
                thread_id=seeded["thread_id"],
                source_message_id=seeded["source_message_id"],
                project_id=seeded["project_id"],
                instructions="Patch the failing return path.",
            )
        except GuardianDelegationValidationError as exc:
            return str(exc.detail)
        return "admitted"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: admit(), range(2)))

    assert outcomes == [
        "guardian_delegation_intent_required",
        "guardian_delegation_intent_required",
    ]
    with db.get_session() as session:
        intents_after = len(session.query(GuardianDelegationIntent).all())
    assert intents_after == intents_before
    assert len(_runs(db)) == runs_before
    assert _drain() == []
