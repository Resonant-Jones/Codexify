from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import JSON, Integer, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.agents.store import AgentStore
from guardian.core.guardian_delegation_service import (
    build_guardian_delegation_result_delivery_key,
)
from guardian.db.models import (
    AgentDeployment,
    AgentRun,
    AgentRunArtifact,
    AgentRunAttempt,
    AgentRunStep,
    Base,
    ChatMessage,
    ChatThread,
    GeneratedDocument,
    GuardianDelegationIntent,
    PersonalFact,
    Project,
    ProjectDocumentLink,
    User,
)
from guardian.routes import guardian_delegations


class _TestDB:
    def __init__(self) -> None:
        self._engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._original_types = {
            AgentDeployment.__table__.c.id: AgentDeployment.__table__.c.id.type,
            AgentRun.__table__.c.id: AgentRun.__table__.c.id.type,
            AgentRunArtifact.__table__.c.id: AgentRunArtifact.__table__.c.id.type,
            AgentRunAttempt.__table__.c.id: AgentRunAttempt.__table__.c.id.type,
            AgentRunStep.__table__.c.id: AgentRunStep.__table__.c.id.type,
            ChatMessage.__table__.c.id: ChatMessage.__table__.c.id.type,
            ChatThread.__table__.c.thread_config: (
                ChatThread.__table__.c.thread_config.type
            ),
            AgentDeployment.__table__.c.spec_json: (
                AgentDeployment.__table__.c.spec_json.type
            ),
            AgentRunArtifact.__table__.c.content_json: (
                AgentRunArtifact.__table__.c.content_json.type
            ),
            AgentRunAttempt.__table__.c.metadata: (
                AgentRunAttempt.__table__.c.metadata.type
            ),
            AgentRunStep.__table__.c.metadata: (
                AgentRunStep.__table__.c.metadata.type
            ),
            ChatMessage.__table__.c.extra_meta: (
                ChatMessage.__table__.c.extra_meta.type
            ),
            GuardianDelegationIntent.__table__.c.plan_summary: (
                GuardianDelegationIntent.__table__.c.plan_summary.type
            ),
            GuardianDelegationIntent.__table__.c.context_basis: (
                GuardianDelegationIntent.__table__.c.context_basis.type
            ),
        }
        self._original_defaults = {
            GuardianDelegationIntent.__table__.c.plan_summary: (
                GuardianDelegationIntent.__table__.c.plan_summary.server_default
            ),
            GuardianDelegationIntent.__table__.c.context_basis: (
                GuardianDelegationIntent.__table__.c.context_basis.server_default
            ),
        }
        for column in self._original_types:
            if column.name == "id" and column.table.name in {
                "agent_deployments",
                "agent_runs",
                "agent_run_artifacts",
                "agent_run_attempts",
                "agent_run_steps",
                "chat_messages",
            }:
                column.type = Integer()
            else:
                column.type = JSON().with_variant(JSONB, "postgresql")
        GuardianDelegationIntent.__table__.c.plan_summary.server_default = None
        GuardianDelegationIntent.__table__.c.context_basis.server_default = None
        Base.metadata.create_all(
            bind=self._engine,
            tables=[
                User.__table__,
                Project.__table__,
                ChatThread.__table__,
                ChatMessage.__table__,
                GeneratedDocument.__table__,
                ProjectDocumentLink.__table__,
                PersonalFact.__table__,
                AgentDeployment.__table__,
                AgentRun.__table__,
                AgentRunStep.__table__,
                AgentRunAttempt.__table__,
                AgentRunArtifact.__table__,
                GuardianDelegationIntent.__table__,
            ],
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def get_session(self):  # noqa: ANN201
        return self._session_factory()

    def close(self) -> None:
        for column, original in self._original_types.items():
            column.type = original
        for column, original in self._original_defaults.items():
            column.server_default = original
        self._engine.dispose()


@pytest.fixture
def db() -> _TestDB:
    test_db = _TestDB()
    try:
        yield test_db
    finally:
        test_db.close()


@pytest.fixture
def delegation_client(db: _TestDB) -> TestClient:
    guardian_delegations.configure_db(db)
    app = FastAPI()
    app.include_router(guardian_delegations.router)
    return TestClient(app)


def _make_store(db: _TestDB) -> AgentStore:
    return AgentStore(db=db)


def _seed_source_context(
    db: _TestDB,
    *,
    user_id: str = "user-1",
    project_name: str = "project-1",
    thread_title: str = "Source thread",
    selected_content: str = "Please patch the return path.",
) -> dict[str, Any]:
    with db.get_session() as session:
        user = User(
            id=user_id,
            username=f"{user_id}-username",
            password_hash="hash",
        )
        session.add(user)
        project = Project(
            user_id=user_id,
            name=f"{project_name}-{user_id}",
            description=None,
            icon=None,
        )
        session.add(project)
        session.flush()
        thread = ChatThread(
            user_id=user_id,
            title=thread_title,
            summary="",
            project_id=project.id,
        )
        session.add(thread)
        session.flush()
        source_message = ChatMessage(
            thread_id=thread.id,
            user_id=user_id,
            role="user",
            content=selected_content,
            kind="chat",
            extra_meta={},
        )
        session.add(source_message)
        session.commit()
        return {
            "user_id": user_id,
            "project_id": project.id,
            "thread_id": thread.id,
            "source_message_id": source_message.id,
        }


def _fetch_intent(db: _TestDB, intent_id: str) -> GuardianDelegationIntent | None:
    with db.get_session() as session:
        return (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=intent_id)
            .first()
        )


def _fetch_thread_messages(
    db: _TestDB,
    thread_id: int,
    *,
    kind: str | None = None,
) -> list[ChatMessage]:
    with db.get_session() as session:
        query = session.query(ChatMessage).filter_by(thread_id=thread_id)
        if kind is not None:
            query = query.filter_by(kind=kind)
        return list(query.order_by(ChatMessage.id.asc()).all())


def _create_guardian_intent(
    client: TestClient,
    auth_headers: dict[str, str],
    seeded: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
            "project_id": seeded["project_id"],
        },
    )
    assert response.status_code == 201
    return response.json()


def _store_guardian_result(
    db: _TestDB,
    *,
    intent_payload: dict[str, Any],
    coding_task_id: str = "task-1",
    attempt_id: str = "attempt-1",
    result_status: str = "succeeded",
    result_summary: str = "Patched the Guardian delegation return path.",
    files_changed: list[str] | None = None,
    validation_results: Any | None = None,
    commit_hash: str | None = None,
) -> dict[str, Any]:
    return _make_store(db).store_coding_result(
        run_id=str(intent_payload["run_id"]),
        coding_task_id=coding_task_id,
        attempt_id=attempt_id,
        thread_id=int(intent_payload["thread_id"]),
        source_message_id=int(intent_payload["source_message_id"]),
        result_status=result_status,
        result_summary=result_summary,
        files_changed=files_changed or ["guardian/agents/store.py"],
        validation_results=validation_results,
        commit_hash=commit_hash,
    )


def _create_non_guardian_run(
    db: _TestDB,
    *,
    seeded: dict[str, Any],
    spec_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = _make_store(db)
    spec_json = {
        "source_thread_id": seeded["thread_id"],
        "source_message_id": seeded["source_message_id"],
        "thread_id": seeded["thread_id"],
        "user_id": seeded["user_id"],
        "project_id": seeded["project_id"],
        "adapter_kind": "pi_codex_runner",
    }
    spec_json.update(spec_overrides or {})
    deployment = store.create_deployment(
        flow_id="non_guardian_coding",
        thread_id=seeded["thread_id"],
        spec_json=spec_json,
        spec_hash="non-guardian-spec-hash",
        trust_state="supervised",
    )
    run = store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=seeded["thread_id"],
        runtime_target="container",
        rollback_mode="auto",
        status="queued",
    )
    return {
        "deployment_id": str(deployment["deployment_id"]),
        "run_id": str(run["run_id"]),
    }


def test_guardian_delegation_result_posts_once_to_source_thread(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    delivery = _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path and preserved idempotency.",
        files_changed=["guardian/agents/store.py", "guardian/db/models.py"],
        validation_results={"status": "passed", "command": "pytest -q"},
        commit_hash="abc123def456",
    )

    assert delivery["delivery_ok"] is True
    assert delivery["delivery_status"] == "delivered"
    assert delivery["visibility_status"] == "result_posted"

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    message = messages[0]
    delivery_key = build_guardian_delegation_result_delivery_key(
        intent_id=created["intent_id"],
        run_id=created["run_id"],
    )
    assert message.role == "assistant"
    assert message.extra_meta["guardian_delegation_intent_id"] == created["intent_id"]
    assert message.extra_meta["run_id"] == created["run_id"]
    assert message.extra_meta["thread_id"] == created["thread_id"]
    assert message.extra_meta["source_message_id"] == created["source_message_id"]
    assert message.extra_meta["delivery_key"] == delivery_key
    assert message.extra_meta["delivery_kind"] == "guardian_delegation_result"
    assert message.extra_meta["visibility_status"] == "result_posted"

    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.visibility_status == "result_posted"
    assert row.result_message_id == message.id
    assert row.result_delivery_key == delivery_key
    assert row.result_delivered_at is not None


def test_guardian_delegation_result_delivery_is_idempotent(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    first = _store_guardian_result(db, intent_payload=created)
    second = _store_guardian_result(db, intent_payload=created)

    assert first["message_id"] is not None
    assert second["message_id"] == first["message_id"]
    assert second["delivery_ok"] is True
    assert second["delivery_status"] == "delivered"
    assert len(_fetch_thread_messages(db, created["thread_id"], kind="coding_result")) == 1


def test_guardian_delegation_result_delivery_survives_new_session(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    first = _store_guardian_result(
        db,
        intent_payload=created,
        coding_task_id="task-1",
        attempt_id="attempt-1",
    )
    second = _make_store(db).store_coding_result(
        run_id=str(created["run_id"]),
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=int(created["thread_id"]),
        source_message_id=int(created["source_message_id"]),
        result_status="succeeded",
        result_summary="Patched the Guardian delegation return path.",
        files_changed=["guardian/agents/store.py"],
    )

    assert first["message_id"] is not None
    assert second["message_id"] == first["message_id"]
    assert len(_fetch_thread_messages(db, created["thread_id"], kind="coding_result")) == 1


def test_stale_guardian_delegation_run_is_suppressed(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert row is not None
        row.run_id = "run_superseding"
        session.commit()

    delivery = _store_guardian_result(db, intent_payload=created)

    assert delivery["delivery_ok"] is False
    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert delivery["source_thread_delivery_suppressed"] is True
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []

    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.visibility_status == "stale_suppressed"


def test_superseded_guardian_delegation_run_is_suppressed(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert row is not None
        row.intent_status = "superseded"
        session.commit()

    delivery = _store_guardian_result(db, intent_payload=created)

    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []


def test_cancelled_guardian_delegation_run_is_suppressed(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert row is not None
        row.intent_status = "cancelled"
        session.commit()

    delivery = _store_guardian_result(db, intent_payload=created)

    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []


def test_missing_lineage_does_not_post_result(db: _TestDB) -> None:
    seeded = _seed_source_context(db)
    non_intent_run = _create_non_guardian_run(
        db,
        seeded=seeded,
        spec_overrides={
            "guardian_delegation": {
                "ownership": "guardian_delegation_intent",
                "phase": "phase3",
                "suppress_source_thread_delivery": False,
            }
        },
    )

    delivery = _make_store(db).store_coding_result(
        run_id=non_intent_run["run_id"],
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        result_status="succeeded",
        result_summary="Completed the patch.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is False
    assert delivery["delivery_status"] == "degraded"
    assert delivery["delivery_reason_code"] == "guardian_delegation_intent_missing"
    assert _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result") == []


def test_non_guardian_coding_result_delivery_unchanged(db: _TestDB) -> None:
    seeded = _seed_source_context(db)
    run = _create_non_guardian_run(db, seeded=seeded)

    delivery = _make_store(db).store_coding_result(
        run_id=run["run_id"],
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        result_status="succeeded",
        result_summary="Updated the normal coding result path.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is True
    assert delivery["delivery_status"] == "delivered"

    messages = _fetch_thread_messages(db, seeded["thread_id"], kind="coding_result")
    assert len(messages) == 1
    assert messages[0].extra_meta.get("guardian_delegation_intent_id") is None
    assert messages[0].extra_meta.get("delivery_kind") != "guardian_delegation_result"


def test_guardian_result_message_does_not_include_internal_context_or_personal_data(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = "Please patch guardian/agents/store.py."
    seeded = _seed_source_context(db, selected_content=selected_content)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary=(
            "selected_turn_content_hash: abc123 context_basis "
            "project_kb_reference my boss is frustrating me"
        ),
        files_changed=["guardian/agents/store.py"],
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert selected_content not in content
    assert "selected_turn_content_hash" not in content
    assert "context_basis" not in content
    assert "project_kb_reference" not in content
    assert "my boss is frustrating me" not in content
    assert "**Summary**" not in content


def test_get_guardian_delegation_includes_visibility_status(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    delivery = _store_guardian_result(db, intent_payload=created)
    assert delivery["message_id"] is not None

    response = delegation_client.get(
        f"/api/guardian/delegations/{created['intent_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["visibility_status"] == "result_posted"
    assert body["result_message_id"] == delivery["message_id"]
    assert body["result_delivered_at"] is not None


def test_duplicate_delivery_key_recovers_without_duplicate_message(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)
    store = _make_store(db)
    original_commit = store._commit_guardian_delegation_delivery
    collision_raised = {"value": False}

    def commit_with_duplicate_collision(session: Any) -> None:
        original_commit(session)
        if not collision_raised["value"]:
            collision_raised["value"] = True
            raise IntegrityError(
                "UPDATE guardian_delegation_intents",
                {},
                Exception(
                    "duplicate key value violates unique constraint "
                    "'ix_guardian_delegation_intents_result_delivery_key'"
                ),
            )

    monkeypatch.setattr(
        store,
        "_commit_guardian_delegation_delivery",
        commit_with_duplicate_collision,
    )

    delivery = store.store_coding_result(
        run_id=str(created["run_id"]),
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=int(created["thread_id"]),
        source_message_id=int(created["source_message_id"]),
        result_status="succeeded",
        result_summary="Patched the delivery path cleanly.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is True
    assert delivery["delivery_status"] == "delivered"
    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    assert delivery["message_id"] == messages[0].id


def test_late_cancelled_intent_suppresses_before_final_delivery(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)
    store = _make_store(db)

    def cancel_before_finalize(
        *,
        session: Any,
        intent: GuardianDelegationIntent,
        delivery_key: str,
        run_id: str,
    ) -> None:
        intent.intent_status = "cancelled"

    monkeypatch.setattr(
        store,
        "_before_guardian_delegation_delivery_finalize",
        cancel_before_finalize,
    )

    delivery = store.store_coding_result(
        run_id=str(created["run_id"]),
        coding_task_id="task-1",
        attempt_id="attempt-1",
        thread_id=int(created["thread_id"]),
        source_message_id=int(created["source_message_id"]),
        result_status="succeeded",
        result_summary="Patched the delivery path cleanly.",
        files_changed=["guardian/agents/store.py"],
    )

    assert delivery["delivery_ok"] is False
    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert _fetch_thread_messages(db, created["thread_id"], kind="coding_result") == []

    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.intent_status == "cancelled"
    assert row.visibility_status == "stale_suppressed"


def test_validation_results_error_message_is_sanitized(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = "Please patch guardian/agents/store.py."
    seeded = _seed_source_context(db, selected_content=selected_content)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path cleanly.",
        validation_results={
            "status": "failed",
            "error_message": (
                f"{selected_content} context_basis my boss is frustrating me"
            ),
        },
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert selected_content not in content
    assert "context_basis" not in content
    assert "my boss is frustrating me" not in content
    assert "[redacted unsafe validation detail]" in content
    safe_validation = messages[0].extra_meta["validation_results"]
    assert safe_validation["error_message"] == "[redacted unsafe validation detail]"


def test_validation_results_command_is_sanitized(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path cleanly.",
        validation_results={
            "status": "failed",
            "command": (
                "OPENAI_API_KEY=sk-supersecret "
                "/Users/chris/.ssh/id_rsa pytest guardian/agents/store.py"
            ),
        },
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert "OPENAI_API_KEY" not in content
    assert "sk-supersecret" not in content
    assert "/Users/chris/.ssh/id_rsa" not in content
    assert "[redacted unsafe validation detail]" in content
    safe_validation = messages[0].extra_meta["validation_results"]
    assert safe_validation["command"] == "[redacted unsafe validation detail]"


def test_files_changed_paths_are_sanitized(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the delivery path cleanly.",
        files_changed=[
            "guardian/agents/store.py",
            "/home/user/.ssh/id_rsa",
            ".env",
            "/Volumes/Dev_SSD/Codexify-main/guardian/core/guardian_delegation_service.py",
        ],
    )

    messages = _fetch_thread_messages(
        db, created["thread_id"], kind="coding_result"
    )
    assert len(messages) == 1
    content = messages[0].content
    assert "guardian/agents/store.py" in content
    assert "guardian/core/guardian_delegation_service.py" in content
    assert "/home/user/.ssh/id_rsa" not in content
    assert ".env" not in content
    assert "/Volumes/Dev_SSD/Codexify-main/" not in content
    assert "[redacted unsafe path]" in content
    assert messages[0].extra_meta["files_changed"] == [
        "guardian/agents/store.py",
        "guardian/core/guardian_delegation_service.py",
        "[redacted unsafe path]",
    ]
