from __future__ import annotations

from contextlib import suppress
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import CodingWorkOrder
from guardian.routes import coding_work_orders


class _TestDB:
    def __init__(self) -> None:
        self._engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        CodingWorkOrder.__table__.create(bind=self._engine)
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
            CodingWorkOrder.__table__.drop(bind=self._engine)
        self._engine.dispose()


def _build_client(db: _TestDB) -> TestClient:
    app = FastAPI()
    coding_work_orders.configure_db(db)
    app.include_router(coding_work_orders.router)
    return TestClient(app)


def _headers() -> dict[str, str]:
    return {"X-API-Key": "test-key"}


def _create_payload(
    *,
    title: str = "Add task-board API",
    campaign_id: str = "campaign-1",
    status: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "campaign_id": campaign_id,
        "title": title,
        "objective": "Durable work-order surface",
        "scope": "backend only",
        "priority": 2,
        "dependency_ids": ["wo-pre-1"],
        "file_scope": ["guardian/routes/coding_work_orders.py"],
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
