"""Focused backend tests for work-order latest-run readback route."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import coding_work_orders


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")

    # Mock WorkOrderStore
    mock_wo_store = MagicMock()
    monkeypatch.setattr(coding_work_orders, "_store", mock_wo_store)

    # Mock CommandBusStore
    mock_cb_store = MagicMock()
    monkeypatch.setattr(coding_work_orders, "_command_bus_store", mock_cb_store)

    app = FastAPI()
    app.include_router(coding_work_orders.router)
    return TestClient(app), mock_wo_store, mock_cb_store


def _mock_work_order(work_order_id: str = "wo_aaaaaaaaaaaaaaa1", latest_run_id: str | None = None):
    wo = MagicMock()
    wo.work_order_id = work_order_id
    wo.latest_run_id = latest_run_id
    wo.status = "draft"
    wo.title = "Test"
    wo.objective = "Test"
    return wo


def _mock_command_run(run_id: str = "run_0000000000000001"):
    return {
        "run_id": run_id,
        "command_id": "op::health_check",
        "status": "completed",
        "actor_kind": "system",
        "actor_id": "operator",
        "actor_session_id": None,
        "delegated_by": None,
        "auth_subject": "operator",
        "invoke_version": "1.0",
        "idempotency_key": None,
        "args_hash": "abc123",
        "args_redacted": {"path_params": {}, "query": {}, "headers": {}, "body": {}},
        "result_json": {"body": {"ok": True}, "headers": {}, "status_code": 200},
        "error_text": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "started_at": "2026-01-01T00:00:01+00:00",
        "ended_at": "2026-01-01T00:00:02+00:00",
    }


class TestWorkOrderLatestRun:
    def test_returns_linked_command_run(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa1"
        run_id = "run_0000000000000001"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run.return_value = _mock_command_run(run_id)

        resp = client.get(f"/api/coding/work-orders/{wo_id}/latest-run", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["work_order_id"] == wo_id
        assert body["latest_run_id"] == run_id
        run = body["run"]
        assert run["run_id"] == run_id
        assert run["result_json"]["body"]["ok"] is True
        assert run["error_text"] is None
        assert run["status"] == "completed"
        assert "args_redacted" in run
        assert "raw_args" not in run
        assert "events_url" in run

    def test_missing_work_order_returns_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = None

        resp = client.get("/api/coding/work-orders/wo_n0nex1stent0000/latest-run", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_no_latest_run_returns_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa2"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=None)

        resp = client.get(f"/api/coding/work-orders/{wo_id}/latest-run", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "work_order_latest_run_not_found"

    def test_broken_pointer_returns_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa3"
        broken_run_id = "run_brokenpointer0000"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=broken_run_id)
        cb_store.get_run.return_value = None

        resp = client.get(f"/api/coding/work-orders/{wo_id}/latest-run", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "work_order_latest_run_missing"

    def test_readback_does_not_mutate_work_order(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa4"
        wo = _mock_work_order(wo_id, latest_run_id="run_0000000000000001")
        wo_store.get_work_order.return_value = wo
        cb_store.get_run.return_value = _mock_command_run()

        resp = client.get(f"/api/coding/work-orders/{wo_id}/latest-run", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        # Verify store was only read, never mutated
        wo_store.get_work_order.assert_called_with(wo_id)
        assert not hasattr(wo_store, 'create_work_order') or not wo_store.create_work_order.called

    def test_no_auth_returns_401_or_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = None
        resp = client.get("/api/coding/work-orders/wo_n0nex1stent0000/latest-run")
        assert resp.status_code in (401, 403, 404)
