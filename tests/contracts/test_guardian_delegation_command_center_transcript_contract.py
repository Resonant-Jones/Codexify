from __future__ import annotations

from datetime import datetime, timedelta
import json
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import JSON, Integer
from sqlalchemy.dialects.postgresql import JSONB

from guardian.db.models import (
    AgentEvent,
    AgentRun,
    ChatMessage,
    GuardianDelegationIntent,
)
from guardian.routes import guardian_delegations
from tests.contracts.test_guardian_delegation_approval_cancel_contract import (
    _create_manual_intent,
)
from tests.contracts.test_guardian_delegation_phase3_delivery_contract import (
    _TestDB as _Phase3TestDB,
    _create_guardian_intent,
    _fetch_intent,
    _fetch_thread_messages,
    _seed_source_context,
    _store_guardian_result,
)


class _TranscriptTestDB(_Phase3TestDB):
    def __init__(self) -> None:
        super().__init__()
        self._transcript_original_types = {
            AgentEvent.__table__.c.id: AgentEvent.__table__.c.id.type,
            AgentEvent.__table__.c.run_id: AgentEvent.__table__.c.run_id.type,
            AgentEvent.__table__.c.run_step_id: (
                AgentEvent.__table__.c.run_step_id.type
            ),
            AgentEvent.__table__.c.attempt_id: (
                AgentEvent.__table__.c.attempt_id.type
            ),
            AgentEvent.__table__.c.payload: (
                AgentEvent.__table__.c.payload.type
            ),
        }
        self._transcript_original_defaults = {
            AgentEvent.__table__.c.payload: (
                AgentEvent.__table__.c.payload.server_default
            ),
        }
        for column, original in self._transcript_original_types.items():
            if column.name in {"id", "run_id", "run_step_id", "attempt_id"}:
                column.type = Integer()
            elif column.name == "payload":
                column.type = JSON().with_variant(JSONB, "postgresql")
        AgentEvent.__table__.c.payload.server_default = None
        AgentEvent.__table__.create(bind=self._engine, checkfirst=True)

    def close(self) -> None:
        for column, original in self._transcript_original_types.items():
            column.type = original
        for column, original in self._transcript_original_defaults.items():
            column.server_default = original
        super().close()


@pytest.fixture
def db() -> _TranscriptTestDB:
    test_db = _TranscriptTestDB()
    try:
        yield test_db
    finally:
        test_db.close()


@pytest.fixture
def delegation_client(db: _TranscriptTestDB) -> TestClient:
    guardian_delegations.configure_db(db)
    app = FastAPI()
    app.include_router(guardian_delegations.router)
    return TestClient(app)


def _seed_agent_event(
    db: _TranscriptTestDB,
    *,
    run_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> None:
    with db.get_session() as session:
        run_row = session.query(AgentRun).filter_by(run_id=run_id).first()
        assert run_row is not None
        session.add(
            AgentEvent(
                run_id=int(run_row.id),
                event_type=event_type,
                payload_json=payload or {},
                created_at=created_at or datetime(2026, 5, 27, 12, 0, 0),
            )
        )
        session.commit()


def _get_transcript(
    delegation_client: TestClient,
    auth_headers: dict[str, str],
    intent_id: str,
) -> dict[str, Any]:
    response = delegation_client.get(
        f"/api/guardian/delegations/{intent_id}/transcript",
        headers=auth_headers,
    )
    assert response.status_code == 200
    return response.json()


def test_transcript_projection_for_pending_manual_intent(
    delegation_client: TestClient,
    db: _TranscriptTestDB,
    auth_headers,
) -> None:
    selected_content = (
        "Patch guardian/core/guardian_delegation_service.py and keep the "
        "approval boundary deterministic."
    )
    seeded = _seed_source_context(db, selected_content=selected_content)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    body = _get_transcript(
        delegation_client,
        auth_headers,
        created["intent_id"],
    )

    assert body["inspection_only"] is True
    assert body["run_id"] is None
    assert body["run_status"] == "not_enqueued"
    assert body["source_thread_reference"] == {
        "thread_id": created["thread_id"],
        "source_message_id": created["source_message_id"],
    }
    kinds = [item["kind"] for item in body["transcript_items"]]
    assert kinds == [
        "intent_created",
        "plan_prepared",
        "approval_state",
    ]
    assert json.dumps(body, sort_keys=True).find(selected_content) == -1


def test_transcript_projection_for_approved_running_intent(
    delegation_client: TestClient,
    db: _TranscriptTestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)
    approved = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    approved_body = approved.json()

    with db.get_session() as session:
        run_row = (
            session.query(AgentRun)
            .filter_by(run_id=approved_body["run_id"])
            .first()
        )
        assert run_row is not None
        run_row.status = "running"
        session.commit()

    created_at = datetime(2026, 5, 27, 12, 0, 0)
    _seed_agent_event(
        db,
        run_id=approved_body["run_id"],
        event_type="run.started",
        payload={"step_index": 1, "status": "running"},
        created_at=created_at,
    )
    _seed_agent_event(
        db,
        run_id=approved_body["run_id"],
        event_type="validation.started",
        payload={"step_index": 2, "attempt_index": 1, "status": "running"},
        created_at=created_at + timedelta(seconds=5),
    )

    body = _get_transcript(
        delegation_client,
        auth_headers,
        created["intent_id"],
    )

    assert body["run_id"] == approved_body["run_id"]
    assert body["run_status"] == "running"
    event_items = [
        item for item in body["transcript_items"] if item["kind"] == "agent_run_event"
    ]
    assert [item["metadata"]["event_type"] for item in event_items] == [
        "run.started",
        "validation.started",
    ]
    run_linked = next(
        item for item in body["transcript_items"] if item["kind"] == "run_linked"
    )
    run_status = next(
        item for item in body["transcript_items"] if item["kind"] == "run_status"
    )
    assert run_linked["metadata"]["intent_id"] == created["intent_id"]
    assert run_linked["metadata"]["run_id"] == approved_body["run_id"]
    assert run_linked["metadata"]["thread_id"] == created["thread_id"]
    assert run_linked["metadata"]["source_message_id"] == created["source_message_id"]
    assert run_status["metadata"]["run_id"] == approved_body["run_id"]


def test_transcript_projection_for_delivered_result(
    delegation_client: TestClient,
    db: _TranscriptTestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    delivery = _store_guardian_result(
        db,
        intent_payload=created,
        result_summary="Patched the thread delivery path safely.",
        files_changed=["guardian/agents/store.py"],
        validation_results={"status": "passed", "command": "pytest -q"},
        commit_hash="abc123def456",
    )
    assert delivery["delivery_ok"] is True

    body = _get_transcript(
        delegation_client,
        auth_headers,
        created["intent_id"],
    )

    assert body["result_message_id"] is not None
    assert body["source_thread_reference"] == {
        "thread_id": created["thread_id"],
        "source_message_id": created["source_message_id"],
    }
    delivery_item = next(
        item
        for item in body["transcript_items"]
        if item["kind"] == "delivery_result"
    )
    assert delivery_item["metadata"]["result_message_id"] == body["result_message_id"]
    assert delivery_item["metadata"]["delivery_key"] == _fetch_intent(
        db, created["intent_id"]
    ).result_delivery_key
    assert delivery_item["metadata"]["visibility_status"] == "result_posted"


def test_transcript_projection_for_cancelled_intent(
    delegation_client: TestClient,
    db: _TranscriptTestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    cancel = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/cancel",
        headers=auth_headers,
    )
    assert cancel.status_code == 200

    body = _get_transcript(
        delegation_client,
        auth_headers,
        created["intent_id"],
    )

    assert body["intent_status"] == "cancelled"
    assert body["run_status"] == "not_enqueued"
    cancel_item = next(
        item
        for item in body["transcript_items"]
        if item["kind"] == "intent_cancelled"
    )
    assert cancel_item["metadata"]["intent_status"] == "cancelled"
    assert cancel_item["metadata"]["visibility_status"] == body["visibility_status"]


def test_transcript_projection_sanitizes_internal_context(
    delegation_client: TestClient,
    db: _TranscriptTestDB,
    auth_headers,
) -> None:
    selected_content = "Patch guardian/routes/guardian_delegations.py safely."
    seeded = _seed_source_context(db, selected_content=selected_content)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        row = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert row is not None
        plan_summary = dict(row.plan_summary or {})
        plan_summary["standardized_task_prompt"] = (
            f"{selected_content} hidden prompt context_basis "
            "project_kb_reference sk-secret-1234567890"
        )
        row.plan_summary = plan_summary
        row.context_basis = [
            {
                "source_type": "selected_turn",
                "source_id": str(created["source_message_id"]),
                "included_fields": ["message.content", "context_basis"],
                "reason": "unsafe test payload",
                "confidence": "high",
                "policy_allowed": True,
                "message_role": "user",
                "raw_content": (
                    "My boss is frustrating me and here is sk-secret-1234567890"
                ),
            }
        ]
        session.commit()

    _store_guardian_result(
        db,
        intent_payload=created,
        result_summary=(
            f"{selected_content} hidden prompt context_basis "
            "project_kb_reference sk-secret-1234567890"
        ),
        files_changed=[
            "guardian/routes/guardian_delegations.py",
            "/home/user/.ssh/id_rsa",
            ".env",
        ],
        validation_results={
            "status": "failed",
            "command": "API_KEY=sk-secret-1234567890 pytest /home/user/.ssh/id_rsa",
            "error_message": (
                "My boss is frustrating me. hidden prompt context_basis "
                "project_kb_reference"
            ),
        },
        commit_hash="abc123def456",
    )

    body = _get_transcript(
        delegation_client,
        auth_headers,
        created["intent_id"],
    )

    serialized = json.dumps(body, sort_keys=True)
    assert selected_content not in serialized
    assert "hidden prompt" not in serialized
    assert "context_basis" not in serialized
    assert "project_kb_reference" not in serialized
    assert "My boss is frustrating me" not in serialized
    assert "sk-secret-1234567890" not in serialized
    assert "/home/user/.ssh/id_rsa" not in serialized
    assert ".env" not in serialized
    assert "[redacted unsafe path]" in serialized


def test_transcript_endpoint_is_read_only(
    delegation_client: TestClient,
    db: _TranscriptTestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_guardian_intent(delegation_client, auth_headers, seeded)
    _store_guardian_result(db, intent_payload=created)

    with db.get_session() as session:
        before_counts = {
            "intents": session.query(GuardianDelegationIntent).count(),
            "runs": session.query(AgentRun).count(),
            "messages": session.query(ChatMessage).count(),
        }
        before_intent = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert before_intent is not None
        before_snapshot = {
            "visibility_status": before_intent.visibility_status,
            "result_message_id": before_intent.result_message_id,
            "result_delivered_at": before_intent.result_delivered_at,
            "result_delivery_key": before_intent.result_delivery_key,
            "updated_at": before_intent.updated_at,
        }

    _get_transcript(delegation_client, auth_headers, created["intent_id"])

    with db.get_session() as session:
        after_counts = {
            "intents": session.query(GuardianDelegationIntent).count(),
            "runs": session.query(AgentRun).count(),
            "messages": session.query(ChatMessage).count(),
        }
        after_intent = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert after_intent is not None
        after_snapshot = {
            "visibility_status": after_intent.visibility_status,
            "result_message_id": after_intent.result_message_id,
            "result_delivered_at": after_intent.result_delivered_at,
            "result_delivery_key": after_intent.result_delivery_key,
            "updated_at": after_intent.updated_at,
        }

    assert after_counts == before_counts
    assert after_snapshot == before_snapshot


def test_transcript_endpoint_flagged_off_by_default() -> None:
    from guardian.guardian_api import app

    paths = {route.path for route in app.routes}
    assert "/api/guardian/delegations/{intent_id}/transcript" not in paths


def test_no_command_center_ui_or_extra_routes_added() -> None:
    route_paths = {route.path for route in guardian_delegations.router.routes}
    assert route_paths == {
        "/api/guardian/delegations",
        "/api/guardian/delegations/{intent_id}",
        "/api/guardian/delegations/{intent_id}/approve",
        "/api/guardian/delegations/{intent_id}/cancel",
        "/api/guardian/delegations/{intent_id}/transcript",
    }
    assert all("command-center" not in path for path in route_paths)
