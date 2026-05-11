from __future__ import annotations

from contextlib import suppress
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.agents.campaign_runner_store import CampaignRunnerStore
from guardian.db.models import (
    Campaign,
    CampaignExecutionAttempt,
    CampaignGoal,
    CodingWorkOrder,
    CodingWorktreeLease,
)
from guardian.routes import coding_work_orders


class _TestDB:
    def __init__(self) -> None:
        self._engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        CampaignGoal.__table__.create(bind=self._engine)
        Campaign.__table__.create(bind=self._engine)
        CampaignExecutionAttempt.__table__.create(bind=self._engine)
        CodingWorkOrder.__table__.create(bind=self._engine)
        CodingWorktreeLease.__table__.create(bind=self._engine)
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            future=True,
        )

    def get_session(self):  # noqa: ANN201
        return self._session_factory()

    def close(self) -> None:
        with suppress(Exception):
            CampaignExecutionAttempt.__table__.drop(bind=self._engine)
        with suppress(Exception):
            Campaign.__table__.drop(bind=self._engine)
        with suppress(Exception):
            CampaignGoal.__table__.drop(bind=self._engine)
        with suppress(Exception):
            CodingWorkOrder.__table__.drop(bind=self._engine)
        with suppress(Exception):
            CodingWorktreeLease.__table__.drop(bind=self._engine)
        self._engine.dispose()


def _build_client(db: _TestDB) -> TestClient:
    app = FastAPI()
    coding_work_orders.configure_db(db)
    app.include_router(coding_work_orders.router)
    app.include_router(coding_work_orders.campaign_runner_router)
    app.include_router(coding_work_orders.orchestrator_router)
    return TestClient(app)


def _headers() -> dict[str, str]:
    return {"X-API-Key": "test-key"}


def _create_payload(
    *,
    title: str = "Add task-board API",
    campaign_id: str = "campaign-1",
    status: str | None = None,
    dependency_ids: list[str] | None = None,
    file_scope: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaign_id": campaign_id,
        "title": title,
        "objective": "Durable work-order surface",
        "scope": "backend only",
        "priority": 2,
        "dependency_ids": dependency_ids if dependency_ids is not None else [],
        "file_scope": (
            file_scope
            if file_scope is not None
            else ["guardian/routes/coding_work_orders.py"]
        ),
        "validation_command": "pytest -q",
        "adapter_kind": "mock",
        "max_validation_attempts": 1,
        "require_worktree_lease": False,
        "commit_after_validation": False,
        "require_human_review_before_merge": True,
    }
    if status is not None:
        payload["status"] = status
    return payload


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "local")
    monkeypatch.setenv("GUARDIAN_EXPOSURE_MODE", "local_safe")
    db = _TestDB()
    app_client = _build_client(db)
    try:
        yield app_client
    finally:
        db.close()


def test_create_work_order_returns_durable_envelope(client: TestClient) -> None:
    response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(),
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["work_order"]["work_order_id"].startswith("wo_")
    assert payload["work_order"]["status"] == "ready"


def test_create_does_not_enqueue_or_dispatch_worker(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        lambda payload: calls.append(dict(payload)),
    )

    response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="No dispatch side effects"),
        headers=_headers(),
    )

    assert response.status_code == 200
    assert calls == []


def test_list_returns_created_work_order(client: TestClient) -> None:
    create_response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="List me"),
        headers=_headers(),
    )
    created_id = create_response.json()["work_order"]["work_order_id"]

    list_response = client.get("/api/coding/work-orders", headers=_headers())

    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert any(item["work_order_id"] == created_id for item in items)


def test_list_filters_by_status(client: TestClient) -> None:
    client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Ready item"),
        headers=_headers(),
    )
    client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Draft item", status="draft"),
        headers=_headers(),
    )

    response = client.get(
        "/api/coding/work-orders",
        params={"status": "draft"},
        headers=_headers(),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "draft"


def test_list_filters_by_campaign_id(client: TestClient) -> None:
    client.post(
        "/api/coding/work-orders",
        json=_create_payload(campaign_id="campaign-a", title="Campaign A"),
        headers=_headers(),
    )
    client.post(
        "/api/coding/work-orders",
        json=_create_payload(campaign_id="campaign-b", title="Campaign B"),
        headers=_headers(),
    )

    response = client.get(
        "/api/coding/work-orders",
        params={"campaign_id": "campaign-a"},
        headers=_headers(),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["campaign_id"] == "campaign-a"


def test_detail_returns_one_work_order(client: TestClient) -> None:
    create_response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Detail item"),
        headers=_headers(),
    )
    work_order_id = create_response.json()["work_order"]["work_order_id"]

    response = client.get(
        f"/api/coding/work-orders/{work_order_id}",
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["work_order"]["work_order_id"] == work_order_id


def test_missing_work_order_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/coding/work-orders/wo_missing",
        headers=_headers(),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "WORK_ORDER_NOT_FOUND"


def test_cancel_transitions_to_cancelled(client: TestClient) -> None:
    create_response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Cancel item"),
        headers=_headers(),
    )
    work_order_id = create_response.json()["work_order"]["work_order_id"]

    response = client.post(
        f"/api/coding/work-orders/{work_order_id}/cancel",
        json={"reason": "operator_cancel"},
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()["work_order"]
    assert payload["status"] == "cancelled"
    assert payload["blocked_reason"] == "operator_cancel"


def test_invalid_status_filter_returns_400(client: TestClient) -> None:
    response = client.get(
        "/api/coding/work-orders",
        params={"status": "invalid"},
        headers=_headers(),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "WORK_ORDER_INVALID_STATUS"


def test_auth_is_required(client: TestClient) -> None:
    response = client.get(
        "/api/coding/work-orders",
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 401


def test_orchestrator_next_returns_recommendation_for_ready_work_order(
    client: TestClient,
) -> None:
    create_response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Recommend me"),
        headers=_headers(),
    )
    created_id = create_response.json()["work_order"]["work_order_id"]

    response = client.get(
        "/api/coding/orchestrator/next",
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["recommendations"]
    recommendation = payload["recommendations"][0]
    assert recommendation["work_order_id"] == created_id
    assert recommendation["status"] == "ready"
    assert "READY_FOR_DISPATCH" in recommendation["reason_codes"]


def test_orchestrator_next_respects_campaign_filter(client: TestClient) -> None:
    response_a = client.post(
        "/api/coding/work-orders",
        json=_create_payload(campaign_id="campaign-a", title="Campaign A"),
        headers=_headers(),
    )
    campaign_a_work_order_id = response_a.json()["work_order"]["work_order_id"]
    client.post(
        "/api/coding/work-orders",
        json=_create_payload(campaign_id="campaign-b", title="Campaign B"),
        headers=_headers(),
    )

    response = client.get(
        "/api/coding/orchestrator/next",
        params={"campaign_id": "campaign-a"},
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"] == "campaign-a"
    assert payload["recommendations"]
    assert {item["work_order_id"] for item in payload["recommendations"]} == {
        campaign_a_work_order_id
    }


def test_orchestrator_next_respects_limit(client: TestClient) -> None:
    for index in range(3):
        client.post(
            "/api/coding/work-orders",
            json=_create_payload(title=f"Limit item {index}"),
            headers=_headers(),
        )

    response = client.get(
        "/api/coding/orchestrator/next",
        params={"limit": 2},
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert len(payload["recommendations"]) == 2


def test_orchestrator_next_includes_skip_reasons(client: TestClient) -> None:
    client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Ready item"),
        headers=_headers(),
    )
    draft_response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Draft item", status="draft"),
        headers=_headers(),
    )
    draft_id = draft_response.json()["work_order"]["work_order_id"]

    response = client.get(
        "/api/coding/orchestrator/next",
        headers=_headers(),
    )

    assert response.status_code == 200
    skipped = response.json()["skipped"]
    draft_skips = [
        item
        for item in skipped
        if item["work_order_id"] == draft_id
        and item["reason_code"] == "STATUS_NOT_READY"
    ]
    assert draft_skips


def test_orchestrator_next_does_not_dispatch_or_create_lease(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueue_calls: list[dict[str, Any]] = []
    lease_create_calls: list[dict[str, Any]] = []

    monkeypatch.setattr(
        "guardian.queue.redis_queue.enqueue_coding_execution",
        lambda payload: enqueue_calls.append(dict(payload)),
    )
    monkeypatch.setattr(
        "guardian.agents.worktree_lease_store.WorktreeLeaseStore.create_lease",
        lambda *_args, **_kwargs: lease_create_calls.append({}),
    )

    client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="No side-effect item"),
        headers=_headers(),
    )
    response = client.get(
        "/api/coding/orchestrator/next",
        headers=_headers(),
    )

    assert response.status_code == 200
    assert enqueue_calls == []
    assert lease_create_calls == []


def test_orchestrator_next_invalid_auth_returns_401(client: TestClient) -> None:
    response = client.get(
        "/api/coding/orchestrator/next",
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 401


def test_orchestrator_next_output_is_json_safe_and_stable(
    client: TestClient,
) -> None:
    client.post(
        "/api/coding/work-orders",
        json=_create_payload(title="Stable output item"),
        headers=_headers(),
    )

    response_one = client.get(
        "/api/coding/orchestrator/next",
        headers=_headers(),
    )
    response_two = client.get(
        "/api/coding/orchestrator/next",
        headers=_headers(),
    )

    assert response_one.status_code == 200
    assert response_two.status_code == 200
    payload_one = response_one.json()
    payload_two = response_two.json()

    assert isinstance(payload_one["generated_at"], str)
    assert isinstance(payload_two["generated_at"], str)
    assert isinstance(payload_one["recommendations"], list)
    assert isinstance(payload_one["skipped"], list)
    assert isinstance(payload_one["decision_reasons"], list)

    comparable_one = dict(payload_one)
    comparable_two = dict(payload_two)
    comparable_one.pop("generated_at", None)
    comparable_two.pop("generated_at", None)
    assert comparable_one == comparable_two


def test_campaign_runner_goal_and_campaign_routes(client: TestClient) -> None:
    goal_response = client.post(
        "/api/coding/campaign-runner/goals",
        json={
            "title": "Ship Campaign Runner MVP",
            "summary": "Operator-owned build desk loop",
            "source_thread_id": "42",
            "source_message_id": "99",
        },
        headers=_headers(),
    )
    assert goal_response.status_code == 200
    goal_payload = goal_response.json()
    assert goal_payload["ok"] is True
    goal_id = goal_payload["goal"]["goal_id"]

    campaign_response = client.post(
        "/api/coding/campaign-runner/campaigns",
        json={
            "goal_id": goal_id,
            "title": "Campaign Runner Control Plane",
            "summary": "MVP spine for goal -> work order -> attempts",
        },
        headers=_headers(),
    )
    assert campaign_response.status_code == 200
    campaign_payload = campaign_response.json()
    assert campaign_payload["ok"] is True
    campaign_id = campaign_payload["campaign"]["campaign_id"]

    work_order_response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(
            campaign_id=campaign_id,
            title="Add durable campaign attempt ledger",
        ),
        headers=_headers(),
    )
    assert work_order_response.status_code == 200
    work_order_id = work_order_response.json()["work_order"]["work_order_id"]

    detail_response = client.get(
        f"/api/coding/campaign-runner/campaigns/{campaign_id}",
        headers=_headers(),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["ok"] is True
    assert detail_payload["campaign"]["campaign_id"] == campaign_id
    assert detail_payload["goal"]["goal_id"] == goal_id
    assert detail_payload["current_work_order_id"] == work_order_id
    assert detail_payload["next_recommended_work_order"]["work_order_id"] == (
        work_order_id
    )


def test_campaign_runner_detail_includes_latest_attempt_ledger(
    client: TestClient,
) -> None:
    goal_response = client.post(
        "/api/coding/campaign-runner/goals",
        json={"title": "Goal with execution evidence"},
        headers=_headers(),
    )
    goal_id = goal_response.json()["goal"]["goal_id"]
    campaign_response = client.post(
        "/api/coding/campaign-runner/campaigns",
        json={"goal_id": goal_id, "title": "Evidence campaign"},
        headers=_headers(),
    )
    campaign_id = campaign_response.json()["campaign"]["campaign_id"]
    work_order_response = client.post(
        "/api/coding/work-orders",
        json=_create_payload(
            campaign_id=campaign_id, title="Evidence work order"
        ),
        headers=_headers(),
    )
    work_order_id = work_order_response.json()["work_order"]["work_order_id"]

    store = CampaignRunnerStore(db=coding_work_orders._campaign_runner_store.db)
    store.record_execution_attempt(
        run_id="run-123",
        attempt_id="attempt-1",
        status="failed",
        campaign_id=campaign_id,
        goal_id=goal_id,
        work_order_id=work_order_id,
        coding_task_id="coding-task-123",
        adapter_kind="codex",
        runtime_target="container",
        error_code="VALIDATION_FAILED",
        error_message="validation failed",
        validation_summary={
            "validation_attempt_count": 1,
            "final_validation_status": "failed",
        },
        commit_hash=None,
        delivery_ok=False,
        delivered_message_id=None,
        delivery_reason="result_status_not_persisted_as_assistant_message",
        source_thread_id=42,
        source_message_id=99,
        evidence_json={"summary": "validation failed"},
    )

    detail_response = client.get(
        f"/api/coding/campaign-runner/campaigns/{campaign_id}",
        headers=_headers(),
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert len(detail_payload["attempts"]) == 1
    latest = detail_payload["latest_attempts_by_work_order"][work_order_id]
    assert latest["status"] == "failed"
    assert latest["work_order_id"] == work_order_id
    assert latest["validation_summary"]["final_validation_status"] == "failed"
    assert latest["error_code"] == "VALIDATION_FAILED"
