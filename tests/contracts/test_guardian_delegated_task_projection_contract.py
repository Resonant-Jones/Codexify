"""Thread-scoped, inspection-safe Delegated Task read projection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

from guardian.db.models import AgentRun, GuardianDelegationIntent, PersonalFact
from guardian.routes import guardian_delegations
from guardian.protocol_tokens import GuardianDelegationApprovalMode
from tests.contracts.test_guardian_delegation_phase2a_contract import (
    _TestDB,
    _fetch_thread_messages,
    _seed_source_context,
)


@pytest.fixture
def db():
    # The shared SQLite fixture predates this PersonalFact JSONB column.
    column = PersonalFact.__table__.c.guardrail_metadata
    original_type = column.type
    column.type = JSON().with_variant(JSONB, "postgresql")
    test_db = None
    try:
        test_db = _TestDB()
        yield test_db
    finally:
        if test_db is not None:
            test_db.close()
        column.type = original_type


@pytest.fixture
def delegation_client(db):
    guardian_delegations.configure_db(db)
    app = FastAPI()
    app.include_router(guardian_delegations.router)
    return TestClient(app)


def _create_manual(client, headers, seeded):
    response = client.post(
        "/api/guardian/delegations",
        headers=headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
            "project_id": seeded["project_id"],
            "approval_mode": GuardianDelegationApprovalMode.HUMAN_REQUIRED.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_thread_list_is_scoped_ordered_and_inspection_safe(
    delegation_client, db: _TestDB, auth_headers
) -> None:
    source = _seed_source_context(
        db, user_id="source-owner", selected_content="private selected source"
    )
    other = _seed_source_context(db, user_id="other-owner")
    older = _create_manual(delegation_client, auth_headers, source)
    newer = _create_manual(delegation_client, auth_headers, source)
    _create_manual(delegation_client, auth_headers, other)
    with db.get_session() as session:
        old_row = session.query(GuardianDelegationIntent).filter_by(
            intent_id=older["intent_id"]
        ).one()
        new_row = session.query(GuardianDelegationIntent).filter_by(
            intent_id=newer["intent_id"]
        ).one()
        old_row.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        new_row.created_at = old_row.created_at + timedelta(days=1)
        old_row.plan_summary = {"standardized_task_prompt": "secret task prompt"}
        old_row.context_basis = [{"secret": "private context"}]
        session.commit()
    before_messages = len(_fetch_thread_messages(db, source["thread_id"]))

    response = delegation_client.get(
        "/api/guardian/delegations",
        headers=auth_headers,
        params={"thread_id": source["thread_id"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == source["thread_id"]
    assert body["count"] == 2
    assert [task["intent_id"] for task in body["delegated_tasks"]] == [
        newer["intent_id"], older["intent_id"]
    ]
    for task in body["delegated_tasks"]:
        assert task["thread_id"] == source["thread_id"]
        assert task["source_message_id"] == source["source_message_id"]
        assert task["project_id"] == source["project_id"]
        assert task["intent_status"] == "awaiting_approval"
        assert task["run_status"] == "not_enqueued"
        assert task["approval_state"] == "pending"
        assert task["approval_source"] == "none"
        assert task["visibility_status"] == "not_posted"
        assert task["run_id"] is None
        assert task["transcript_url"] == (
            f"/api/guardian/delegations/{task['intent_id']}/transcript"
        )
        assert task["created_at"] and task["updated_at"]
        assert "context_basis" not in task
        assert "plan_summary" not in task
    assert "secret task prompt" not in response.text
    assert "private context" not in response.text
    assert "private selected source" not in response.text
    assert len(_fetch_thread_messages(db, source["thread_id"])) == before_messages


def test_list_projects_current_run_status_without_combining_axes(
    delegation_client, db: _TestDB, auth_headers
) -> None:
    source = _seed_source_context(db)
    created = _create_manual(delegation_client, auth_headers, source)
    approved = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    with db.get_session() as session:
        session.query(AgentRun).filter_by(run_id=approved.json()["run_id"]).one().status = "running"
        session.commit()

    response = delegation_client.get(
        "/api/guardian/delegations",
        headers=auth_headers,
        params={"thread_id": source["thread_id"]},
    )

    assert response.status_code == 200
    task = response.json()["delegated_tasks"][0]
    assert task["intent_id"] == created["intent_id"]
    assert task["run_id"] == approved.json()["run_id"]
    assert task["run_status"] == "running"
    assert task["approval_state"] == "approved"
    assert task["approval_source"] == "human"
    assert "status" not in task


def test_empty_missing_and_invalid_thread(delegation_client, db: _TestDB, auth_headers) -> None:
    source = _seed_source_context(db)
    response = delegation_client.get(
        "/api/guardian/delegations",
        headers=auth_headers,
        params={"thread_id": source["thread_id"]},
    )
    assert response.status_code == 200
    assert response.json() == {
        "thread_id": source["thread_id"], "delegated_tasks": [], "count": 0
    }
    missing = delegation_client.get(
        "/api/guardian/delegations",
        headers=auth_headers,
        params={"thread_id": source["thread_id"] + 999},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "thread_not_found"
    for params in ({}, {"thread_id": 0}, {"thread_id": -1}):
        assert delegation_client.get(
            "/api/guardian/delegations", headers=auth_headers, params=params
        ).status_code == 422
