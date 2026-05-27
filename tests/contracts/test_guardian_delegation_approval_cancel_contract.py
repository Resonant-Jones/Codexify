from __future__ import annotations

import json
from typing import Any

from guardian.db.models import AgentRun, GuardianDelegationIntent
from guardian.protocol_tokens import GuardianDelegationApprovalMode
from guardian.routes import guardian_delegations
from tests.contracts.test_guardian_delegation_phase2a_contract import (
    _TestDB,
    _fetch_intent,
    _fetch_thread_messages,
    _make_store,
    _seed_source_context,
    db,
    delegation_client,
)


def _count_runs(db: _TestDB) -> int:
    with db.get_session() as session:
        return int(session.query(AgentRun).count())


def _create_manual_intent(
    delegation_client: Any,
    auth_headers: dict[str, str],
    seeded: dict[str, Any],
) -> dict[str, Any]:
    response = delegation_client.post(
        "/api/guardian/delegations",
        headers=auth_headers,
        json={
            "thread_id": seeded["thread_id"],
            "source_message_id": seeded["source_message_id"],
            "project_id": seeded["project_id"],
            "approval_mode": GuardianDelegationApprovalMode.HUMAN_REQUIRED.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _store_guardian_result(
    db: _TestDB,
    *,
    intent_payload: dict[str, Any],
) -> dict[str, Any]:
    return _make_store(db).store_coding_result(
        run_id=str(intent_payload["run_id"]),
        coding_task_id="task-approval-1",
        attempt_id="attempt-approval-1",
        thread_id=int(intent_payload["thread_id"]),
        source_message_id=int(intent_payload["source_message_id"]),
        result_status="succeeded",
        result_summary="Patched the approval lifecycle path safely.",
        files_changed=["guardian/core/guardian_delegation_service.py"],
    )


def test_manual_approval_intent_does_not_dispatch(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)

    body = _create_manual_intent(delegation_client, auth_headers, seeded)

    assert body["approval_state"] == "pending"
    assert body["approval_source"] == "none"
    assert body["intent_status"] == "awaiting_approval"
    assert body["run_id"] is None
    assert body["run_status"] == "not_enqueued"
    assert body["visibility_status"] == "not_posted"
    row = _fetch_intent(db, body["intent_id"])
    assert row is not None
    assert row.approval_mode == "human_required"
    assert _count_runs(db) == 0


def test_approve_pending_intent_creates_one_run(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    response = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approval_state"] == "approved"
    assert body["approval_source"] == "human"
    assert body["intent_status"] == "accepted"
    assert body["run_id"] is not None
    assert body["run_status"] == "queued"
    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.run_id == body["run_id"]
    assert _count_runs(db) == 1


def test_approve_is_idempotent_for_already_approved_intent(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    first = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )
    second = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]
    assert _count_runs(db) == 1


def test_approve_cancelled_intent_fails_closed(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    cancel = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/cancel",
        headers=auth_headers,
    )
    approve = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )

    assert cancel.status_code == 200
    assert approve.status_code == 409
    assert approve.json()["detail"] == "guardian_delegation_intent_cancelled"
    assert _count_runs(db) == 0


def test_approve_superseded_intent_fails_closed(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        intent = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert intent is not None
        intent.intent_status = "superseded"
        session.commit()

    approve = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )

    assert approve.status_code == 409
    assert approve.json()["detail"] == "guardian_delegation_intent_not_approvable"
    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.run_id is None
    assert _count_runs(db) == 0


def test_approve_failed_intent_fails_closed(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    with db.get_session() as session:
        intent = (
            session.query(GuardianDelegationIntent)
            .filter_by(intent_id=created["intent_id"])
            .first()
        )
        assert intent is not None
        intent.intent_status = "failed"
        session.commit()

    approve = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )

    assert approve.status_code == 409
    assert approve.json()["detail"] == "guardian_delegation_intent_not_approvable"
    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.run_id is None
    assert _count_runs(db) == 0


def test_approve_auto_intent_rejected(
    delegation_client,
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
            "project_id": seeded["project_id"],
        },
    )
    assert response.status_code == 201
    created = response.json()

    approve = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )

    assert approve.status_code == 409
    assert approve.json()["detail"] == "guardian_delegation_approval_not_required"
    body = delegation_client.get(
        f"/api/guardian/delegations/{created['intent_id']}",
        headers=auth_headers,
    ).json()
    assert body["run_id"] == created["run_id"]
    assert _count_runs(db) == 1


def test_get_pending_manual_intent_returns_awaiting_approval(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    selected_content = (
        "Patch guardian/core/guardian_delegation_service.py and keep "
        "approval lifecycle semantics deterministic."
    )
    seeded = _seed_source_context(db, selected_content=selected_content)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    response = delegation_client.get(
        f"/api/guardian/delegations/{created['intent_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approval_mode"] == "human_required"
    assert body["approval_state"] == "pending"
    assert body["approval_source"] == "none"
    assert body["intent_status"] == "awaiting_approval"
    assert body["run_id"] is None
    assert body["run_status"] == "not_enqueued"
    assert selected_content not in json.dumps(body, sort_keys=True)


def test_cancel_pending_intent_prevents_dispatch(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    cancel = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/cancel",
        headers=auth_headers,
    )

    assert cancel.status_code == 200
    body = cancel.json()
    assert body["intent_status"] == "cancelled"
    assert body["run_id"] is None
    assert body["run_status"] == "not_enqueued"
    assert _count_runs(db) == 0

    fetched = delegation_client.get(
        f"/api/guardian/delegations/{created['intent_id']}",
        headers=auth_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["intent_status"] == "cancelled"


def test_cancel_active_intent_suppresses_future_delivery(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)
    approved = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/approve",
        headers=auth_headers,
    )
    assert approved.status_code == 200
    active = approved.json()

    cancel = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/cancel",
        headers=auth_headers,
    )
    assert cancel.status_code == 200
    assert cancel.json()["intent_status"] == "cancelled"

    delivery = _store_guardian_result(db, intent_payload=active)

    assert delivery["delivery_ok"] is False
    assert delivery["delivery_status"] == "stale_suppressed"
    assert delivery["visibility_status"] == "stale_suppressed"
    assert (
        _fetch_thread_messages(db, active["thread_id"], kind="coding_result")
        == []
    )
    row = _fetch_intent(db, created["intent_id"])
    assert row is not None
    assert row.intent_status == "cancelled"
    assert row.visibility_status == "stale_suppressed"


def test_cancel_is_idempotent(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    first = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/cancel",
        headers=auth_headers,
    )
    second = delegation_client.post(
        f"/api/guardian/delegations/{created['intent_id']}/cancel",
        headers=auth_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["intent_status"] == "cancelled"
    assert second.json()["intent_status"] == "cancelled"
    assert second.json()["run_id"] is None
    assert second.json()["run_status"] == "not_enqueued"
    assert _count_runs(db) == 0


def test_auto_approved_happy_path_unchanged(
    delegation_client,
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
            "project_id": seeded["project_id"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["approval_state"] == "approved"
    assert body["approval_source"] == "auto"
    assert body["run_id"] is not None
    assert body["run_status"] == "queued"
    assert _count_runs(db) == 1


def test_no_command_center_or_github_or_intent_spine_side_effects(
    delegation_client,
    db: _TestDB,
    auth_headers,
) -> None:
    seeded = _seed_source_context(db)
    created = _create_manual_intent(delegation_client, auth_headers, seeded)

    route_paths = {route.path for route in guardian_delegations.router.routes}
    assert route_paths == {
        "/api/guardian/delegations",
        "/api/guardian/delegations/{intent_id}/approve",
        "/api/guardian/delegations/{intent_id}/cancel",
        "/api/guardian/delegations/{intent_id}",
    }
    assert all(
        not str(entry["source_type"]).startswith("github_")
        for entry in created["context_basis"]
    )
