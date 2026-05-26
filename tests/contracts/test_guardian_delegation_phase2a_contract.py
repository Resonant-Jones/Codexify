from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

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
    GuardianDelegationIntent,
    Project,
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


def test_phase2a_does_not_post_source_thread_result(
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
    store = _make_store(db)
    result = store.store_coding_result(
        run_id=created["run_id"],
        coding_task_id="coding-task-phase2a",
        attempt_id="attempt-phase2a",
        thread_id=seeded["thread_id"],
        source_message_id=seeded["source_message_id"],
        result_status="ok",
        result_summary="Applied the patch.",
        artifacts=[],
        errors=[],
    )

    assert result["delivery_status"] == "not_requested"
    assert (
        result["delivery_reason_code"]
        == "guardian_delegation_source_thread_delivery_deferred"
    )
    assert result["source_thread_delivery_suppressed"] is True
    run_row = _fetch_run(db, created["run_id"])
    assert run_row is not None
    assert run_row.status == "succeeded"
    assert _fetch_thread_messages(
        db,
        seeded["thread_id"],
        kind="coding_result",
    ) == []


def test_no_approve_or_cancel_routes_registered(
    delegation_client: TestClient,
    auth_headers,
) -> None:
    approve = delegation_client.post(
        "/api/guardian/delegations/intent-123/approve",
        headers=auth_headers,
    )
    cancel = delegation_client.post(
        "/api/guardian/delegations/intent-123/cancel",
        headers=auth_headers,
    )

    assert approve.status_code == 404
    assert cancel.status_code == 404


def test_guardian_api_route_is_flagged_off_by_default() -> None:
    from guardian.guardian_api import app

    paths = {route.path for route in app.routes}
    assert "/api/guardian/delegations" not in paths
