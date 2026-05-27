from __future__ import annotations

from hashlib import sha256
import json
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import JSON, Integer, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.agents.store import AgentStore
from guardian.core.guardian_delegation_service import (
    GuardianDelegationService,
    GuardianDelegationValidationError,
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
    prior_messages: list[tuple[str, str]] | None = None,
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
        for role, content in prior_messages or []:
            session.add(
                ChatMessage(
                    thread_id=thread.id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    kind="chat",
                    extra_meta={},
                )
            )
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


def _fetch_run(db: _TestDB, run_id: str) -> AgentRun | None:
    with db.get_session() as session:
        return session.query(AgentRun).filter_by(run_id=run_id).first()


def _fetch_deployment_spec_json(
    db: _TestDB, run_id: str
) -> dict[str, Any] | None:
    store = _make_store(db)
    run = store.get_run(run_id)
    if run is None:
        return None
    deployment = store.get_deployment(str(run["deployment_id"]))
    if deployment is None:
        return None
    return dict(deployment.get("spec_json") or {})


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


def _seed_project_generated_document(
    db: _TestDB,
    *,
    project_id: int,
    user_id: str,
    title: str,
    content: str,
    thread_id: int | None = None,
    is_enabled: bool = True,
) -> dict[str, Any]:
    with db.get_session() as session:
        document = GeneratedDocument(
            id=str(uuid4()),
            project_id=project_id,
            thread_id=thread_id,
            user_id=user_id,
            title=title,
            content=content,
            format="md",
            model="test",
        )
        session.add(document)
        session.flush()
        session.add(
            ProjectDocumentLink(
                project_id=project_id,
                document_id=document.id,
                document_type="generated",
                is_enabled=is_enabled,
                attached_by=user_id,
            )
        )
        session.commit()
        return {
            "document_id": document.id,
            "title": title,
            "content": content,
        }


def _seed_personal_fact(
    db: _TestDB,
    *,
    user_id: str,
    key: str,
    value: str,
) -> None:
    with db.get_session() as session:
        session.add(
            PersonalFact(
                id=1,
                user_id=user_id,
                key=key,
                value=value,
                status="verified",
                confidence=1.0,
                is_active=True,
            )
        )
        session.commit()


def test_guardian_delegation_intent_persists_with_lineage(
    db: _TestDB,
    delegation_client: TestClient,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
            "project_id": seeded["project_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["thread_id"] == seeded["thread_id"]
    assert body["source_message_id"] == seeded["source_message_id"]
    assert body["project_id"] == seeded["project_id"]

    row = _fetch_intent(db, body["intent_id"])
    assert row is not None
    assert row.thread_id == seeded["thread_id"]
    assert row.source_message_id == seeded["source_message_id"]
    assert row.project_id == seeded["project_id"]
    assert row.approval_mode == "scoped_auto"
    assert row.context_basis[0]["source_type"] == "selected_turn"


def test_context_basis_selected_turn_only(
    db: _TestDB,
    delegation_client: TestClient,
    auth_headers,
) -> None:
    selected_content = "Refactor the route guard in guardian/agents/store.py."
    seeded = _seed_source_context(
        db,
        selected_content=selected_content,
        prior_messages=[
            ("assistant", "I know your full background and preferences."),
            ("user", "This unrelated prior conversation should stay excluded."),
        ],
    )
    selected_hash = sha256(
        selected_content.encode("utf-8")
    ).hexdigest()

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["context_basis"] == [
        {
            "source_type": "selected_turn",
            "source_id": str(seeded["source_message_id"]),
            "included_fields": [
                "message.role",
                "message.thread_id",
                "message.id",
                "message.content_hash",
                "message.content_length",
            ],
            "reason": "selected authored turn is the explicit task source",
            "confidence": "high",
            "policy_allowed": True,
            "thread_id": seeded["thread_id"],
            "message_role": "user",
            "content_hash": selected_hash,
            "content_length": len(selected_content),
        }
    ]
    serialized_plan = json.dumps(body["plan_summary"], sort_keys=True)
    assert "full background and preferences" not in serialized_plan
    assert "unrelated prior conversation should stay excluded" not in serialized_plan


def test_auto_approve_on_safe_happy_path(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["approval_state"] == "approved"
    assert body["approval_source"] == "auto"


def test_dispatched_run_id_linked_to_intent(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)

    create_response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["run_id"] is not None

    run_row = _fetch_run(db, created["run_id"])
    assert run_row is not None

    get_response = delegation_client.get(
        f"/api/guardian/delegations/{created['intent_id']}",
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["run_id"] == created["run_id"]
    assert fetched["run_status"] == "queued"


def test_plan_summary_does_not_persist_raw_selected_turn(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = (
        "Please patch guardian/routes/guardian_delegations.py to keep the "
        "validation response deterministic."
    )
    seeded = _seed_source_context(db, selected_content=selected_content)

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    serialized_plan = json.dumps(body["plan_summary"], sort_keys=True)
    assert selected_content not in serialized_plan
    assert body["plan_summary"]["standardized_task_prompt"].find(
        "selected_turn_content_hash:"
    ) != -1
    assert body["plan_summary"]["standardized_task_prompt"].find(
        "selected_turn_content_length:"
    ) != -1
    spec_json = _fetch_deployment_spec_json(db, str(body["run_id"]))
    assert spec_json is not None
    serialized_spec = json.dumps(spec_json, sort_keys=True)
    assert selected_content not in serialized_spec


@pytest.mark.parametrize(
    "selected_content",
    [
        "I am going through a divorce and need you to patch guardian/routes.py.",
        "My boss is frustrating me, please fix guardian/agents/store.py.",
        "My client is frustrating me, please fix guardian/core/delegation_service.py.",
        "My relationship is falling apart, and I need you to update guardian/db/models.py.",
    ],
)
def test_selected_turn_personal_context_fails_closed_or_is_excluded(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
    selected_content: str,
) -> None:
    seeded = _seed_source_context(db, selected_content=selected_content)

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "selected_turn_requires_clarification"
    with db.get_session() as session:
        assert session.query(GuardianDelegationIntent).count() == 0
        assert session.query(AgentDeployment).count() == 0
        assert session.query(AgentRun).count() == 0


def test_context_basis_does_not_store_raw_selected_turn_content(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = "Refactor guardian/core/guardian_delegation_service.py."
    seeded = _seed_source_context(db, selected_content=selected_content)

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    serialized_basis = json.dumps(body["context_basis"], sort_keys=True)
    assert selected_content not in serialized_basis
    assert {entry["source_type"] for entry in body["context_basis"]} == {
        "selected_turn"
    }
    assert "message.content" not in body["context_basis"][0]["included_fields"]


def test_agent_run_metadata_does_not_receive_excluded_personal_context(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = (
        "I am going through a divorce and need you to patch "
        "guardian/core/guardian_delegation_service.py."
    )
    seeded = _seed_source_context(db, selected_content=selected_content)

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "selected_turn_requires_clarification"
    with db.get_session() as session:
        assert session.query(AgentDeployment).count() == 0
        assert session.query(AgentRun).count() == 0


def test_project_kb_context_included_when_project_docs_exist(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = (
        "Patch the route guard and keep accepted token handling deterministic."
    )
    seeded = _seed_source_context(
        db,
        selected_content=selected_content,
        prior_messages=[
            ("assistant", "This broad chat history should stay excluded."),
        ],
    )
    _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        thread_id=seeded["thread_id"],
        title="guardian-delegation-implementation-notes.md",
        content=(
            "Route guard updates should keep validation deterministic and "
            "preserve linked run creation."
        ),
    )
    _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="guardian-delegation-architecture-overview.md",
        content=(
            "Architecture guidance: keep route guard changes project-bound "
            "and deterministic."
        ),
    )
    _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="runtime-protocol-token-contract.md",
        content=(
            "Use accepted and accepted_degraded protocol tokens and keep the "
            "projection deterministic."
        ),
    )

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["context_basis"][0]["source_type"] == "selected_turn"
    assert {entry["source_type"] for entry in body["context_basis"][1:]} == {
        "project_kb",
        "architecture_doc",
        "protocol_doc",
    }
    assert all(
        entry["policy_allowed"] is True for entry in body["context_basis"][1:]
    )
    kb_context = body["plan_summary"]["kb_context"]
    assert {entry["source_type"] for entry in kb_context} == {
        "project_kb",
        "architecture_doc",
        "protocol_doc",
    }
    assert all(entry["excerpt_length"] > 0 for entry in kb_context)
    serialized_plan = json.dumps(body["plan_summary"], sort_keys=True)
    assert selected_content not in serialized_plan
    assert "broad chat history should stay excluded" not in serialized_plan


def test_project_kb_context_is_policy_filtered(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = "Patch the route guard and keep the validation deterministic."
    seeded = _seed_source_context(db, selected_content=selected_content)
    safe_doc = _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="guardian-delegation-notes.md",
        content="Route guard validation should remain deterministic.",
    )
    excluded_doc = _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="private-retrospective.md",
        content=(
            "My boss is frustrating me. I am going through a divorce. "
            "Please patch the route guard validation."
        ),
    )

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    kb_source_ids = {
        entry["source_id"] for entry in body["plan_summary"]["kb_context"]
    }
    assert f"generated:{safe_doc['document_id']}" in kb_source_ids
    assert f"generated:{excluded_doc['document_id']}" not in kb_source_ids
    serialized_plan = json.dumps(body["plan_summary"], sort_keys=True)
    serialized_spec = json.dumps(
        _fetch_deployment_spec_json(db, str(body["run_id"])),
        sort_keys=True,
    )
    assert "My boss is frustrating me" not in serialized_plan
    assert "I am going through a divorce" not in serialized_plan
    assert "My boss is frustrating me" not in serialized_spec
    assert "I am going through a divorce" not in serialized_spec


def test_no_github_context_in_phase2b(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(
        db,
        selected_content="Patch the route guard and keep token handling stable.",
    )
    _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="runtime-protocol-token-contract.md",
        content="Protocol tokens should stay stable for route guard patches.",
    )

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    allowed_local_types = {
        "selected_turn",
        "project_kb",
        "architecture_doc",
        "adr",
        "task_file",
        "protocol_doc",
        "linked_document",
    }
    assert {
        entry["source_type"] for entry in body["context_basis"]
    }.issubset(allowed_local_types)
    assert all(
        not entry["source_type"].startswith("github_")
        for entry in body["context_basis"]
    )


def test_no_broad_chat_history_or_personal_facts_in_kb_expansion(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    personal_fact_value = "Prefers purple for every interface."
    seeded = _seed_source_context(
        db,
        selected_content="Patch the route guard and keep run linkage deterministic.",
        prior_messages=[
            ("user", "This prior conversation should not become coding context."),
            ("assistant", "Conversation history should stay out of Phase 2B."),
        ],
    )
    _seed_personal_fact(
        db,
        user_id=seeded["user_id"],
        key="ui_color_preference",
        value=personal_fact_value,
    )
    _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="conversation-history-dump.md",
        content=(
            "Conversation history\n"
            "User: I prefer purple for every interface.\n"
            "Assistant: Noted.\n"
            "Patch the route guard."
        ),
    )
    _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="guardian-delegation-safe-notes.md",
        content="Route guard patches should keep linked run creation deterministic.",
    )

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    spec_json = _fetch_deployment_spec_json(db, str(body["run_id"]))
    assert spec_json is not None
    serialized_body = json.dumps(body, sort_keys=True)
    serialized_spec = json.dumps(spec_json, sort_keys=True)
    assert "Conversation history" not in serialized_body
    assert "User: I prefer purple" not in serialized_body
    assert personal_fact_value not in serialized_body
    assert "Conversation history" not in serialized_spec
    assert "User: I prefer purple" not in serialized_spec
    assert personal_fact_value not in serialized_spec


def test_context_basis_policy_allowed_reflects_filter_result(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(
        db,
        selected_content="Patch the route guard and keep the result deterministic.",
    )
    safe_doc = _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="guardian-delegation-safe-task-notes.md",
        content="Route guard work should keep result handling deterministic.",
    )
    excluded_doc = _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="relationship-retrospective.md",
        content=(
            "My relationship is falling apart. Patch the route guard and "
            "keep the result deterministic."
        ),
    )

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    kb_entries = [
        entry for entry in body["context_basis"] if entry["source_type"] != "selected_turn"
    ]
    assert kb_entries
    assert all(entry["policy_allowed"] is True for entry in kb_entries)
    assert f"generated:{safe_doc['document_id']}" in {
        entry["source_id"] for entry in kb_entries
    }
    assert f"generated:{excluded_doc['document_id']}" not in {
        entry["source_id"] for entry in kb_entries
    }


def test_agent_run_metadata_receives_safe_kb_context_only(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = "Patch the route guard and keep run linkage deterministic."
    seeded = _seed_source_context(db, selected_content=selected_content)
    safe_doc = _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="runtime-protocol-token-contract.md",
        content=(
            "Protocol tokens should stay deterministic for route guard "
            "patches and linked run creation."
        ),
    )
    _seed_project_generated_document(
        db,
        project_id=seeded["project_id"],
        user_id=seeded["user_id"],
        title="private-retrospective.md",
        content=(
            "My client is frustrating me. Patch the route guard and keep "
            "run linkage deterministic."
        ),
    )

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    spec_json = _fetch_deployment_spec_json(db, str(body["run_id"]))
    assert spec_json is not None
    serialized_spec = json.dumps(spec_json, sort_keys=True)
    assert f"generated:{safe_doc['document_id']}" in serialized_spec
    assert "Protocol tokens should stay deterministic" in serialized_spec
    assert "My client is frustrating me" not in serialized_spec
    assert selected_content not in serialized_spec


def test_run_status_projection_all_known_agent_run_statuses() -> None:
    service = GuardianDelegationService()

    assert service.project_run_status(None) == "not_enqueued"
    assert service.project_run_status("queued") == "queued"
    assert service.project_run_status("running") == "running"
    assert service.project_run_status("succeeded") == "completed"
    assert service.project_run_status("failed") == "failed"
    assert service.project_run_status("canceled") == "cancelled"
    assert service.project_run_status("cancelled") == "cancelled"
    assert service.project_run_status("escalated") == "failed"
    with pytest.raises(GuardianDelegationValidationError):
        service.project_run_status("mystery")


def test_reject_intent_without_source_message_id(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={"thread_id": seeded["thread_id"]},
    )

    assert response.status_code == 422


def test_reject_source_message_from_different_thread(
    delegation_client: TestClient,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded_a = _seed_source_context(db, user_id="user-a", project_name="proj-a")
    seeded_b = _seed_source_context(db, user_id="user-b", project_name="proj-b")

    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded_a["thread_id"],
            "source_message_id": seeded_b["source_message_id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "source_message_thread_mismatch"


def test_only_expected_guardian_delegation_routes_registered() -> None:
    routes = {
        (route.path, tuple(sorted((route.methods or set()) - {"HEAD", "OPTIONS"})))
        for route in guardian_delegations.router.routes
    }
    assert routes == {
        ("/api/guardian/delegations", ("POST",)),
        ("/api/guardian/delegations/{intent_id}", ("GET",)),
        ("/api/guardian/delegations/{intent_id}/approve", ("POST",)),
        ("/api/guardian/delegations/{intent_id}/cancel", ("POST",)),
    }


def test_guardian_api_route_is_flagged_off_by_default() -> None:
    from guardian.guardian_api import app

    paths = {route.path for route in app.routes}
    assert "/api/guardian/delegations" not in paths
