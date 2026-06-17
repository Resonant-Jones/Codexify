"""Focused backend tests for work-order result receipt readback routes."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import coding_work_orders, command_bus


def _install_fake_loopback(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}
        @property
        def text(self) -> str: return '{"ok": true}'
        def json(self) -> dict[str, bool]: return {"ok": True}
    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None: _ = args, kwargs
        async def __aenter__(self) -> "_FakeAsyncClient": return self
        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None: _ = exc_type, exc, tb
        async def request(self, **kwargs: Any) -> _FakeResponse: return _FakeResponse()
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999")
    monkeypatch.setattr("guardian.command_bus.loopback_http_adapter.httpx.AsyncClient", _FakeAsyncClient)


def _mock_work_order(wo_id: str = "wo_aaaaaaaaaaaaaaa1", latest_run_id: str | None = None):
    wo = MagicMock()
    wo.work_order_id = wo_id
    wo.latest_run_id = latest_run_id
    wo.status = "draft"
    wo.title = "Test"
    wo.objective = "Test"
    wo.source_thread_id = None
    wo.source_message_id = None
    return wo


def _mock_command_run(run_id: str = "run_0000000000000001"):
    return {
        "run_id": run_id, "command_id": "op::health_check", "status": "completed",
        "result_json": {"body": {"ok": True, "status": "ok"}},
        "error_text": None,
    }


class _FakeReceiptRow:
    """Simulates a WorkOrderResultReceipt row stored in-memory."""
    def __init__(self, receipt_id: str, work_order_id: str, command_run_id: str, summary: str = "Status: ok", **kwargs):
        self.receipt_id = receipt_id
        self.work_order_id = work_order_id
        self.command_run_id = command_run_id
        self.receipt_kind = "command_run_observation"
        self.observed_command_id = "op::health_check"
        self.observed_run_status = "completed"
        self.observed_result_summary = summary
        self.observed_error_text = None
        self.created_at = None
        self.created_by = "system"
        self.source_thread_id = None
        self.source_message_id = None
        self.provenance_json = {}
        self.redaction_summary_json = {"args_redacted": True}
        self.integrity_hash = "abc123"
        self.schema_version = 1
        self.review_state = "unreviewed"
        self.operator_note = None
        for k, v in kwargs.items():
            setattr(self, k, v)


def _build_client(monkeypatch) -> tuple[TestClient, Any, Any]:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)
    coding_work_orders.configure_db(None)
    monkeypatch.setattr(coding_work_orders, "_command_bus_store", command_bus._store)
    _install_fake_loopback(monkeypatch)
    mock_wo_store = MagicMock()
    monkeypatch.setattr(coding_work_orders, "_store", mock_wo_store)
    if not hasattr(command_bus._store, "_receipts"):
        command_bus._store._receipts = {}
    app = FastAPI()
    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]: return {"ok": True}
    app.include_router(command_bus.router)
    app.include_router(coding_work_orders.router)
    return TestClient(app), mock_wo_store, command_bus._store


class TestReceiptReadback:
    def test_get_receipt_by_id(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa1"
        rid = "wor_0000000000000001"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id, "run_0000000000000001")

        resp = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["receipt_id"] == rid
        assert body["work_order_id"] == wo_id
        assert body["receipt_kind"] == "command_run_observation"
        assert body["observed_result_summary"] == "Status: ok"

    def test_list_receipts(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa2"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts["wor_01"] = _FakeReceiptRow("wor_01", wo_id, "run_01", summary="First")
        cb_store._receipts["wor_02"] = _FakeReceiptRow("wor_02", wo_id, "run_02", summary="Second")

        resp = client.get(f"/api/coding/work-orders/{wo_id}/receipts", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["work_order_id"] == wo_id
        assert len(body["receipts"]) == 2

    def test_get_nonexistent_receipt_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = _mock_work_order("wo_aaaaaaaaaaaaaaa3")
        resp = client.get("/api/coding/work-orders/wo_aaaaaaaaaaaaaaa3/receipts/wor_n0nex1stent", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_get_receipt_wrong_work_order_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id_a = "wo_aaaaaaaaaaaaaaa4"
        wo_id_b = "wo_bbbbbbbbbbbbbbb4"
        rid = "wor_0000000000000004"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id_a)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id_b, "run_04")

        resp = client.get(f"/api/coding/work-orders/{wo_id_a}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_readback_is_read_only(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa5"
        rid = "wor_0000000000000005"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id, "run_05")
        # Read twice — must return same data
        r1 = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        r2 = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        assert r1["receipt_id"] == r2["receipt_id"]
        assert r1["observed_result_summary"] == r2["observed_result_summary"]

    def test_no_raw_args_exposed(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa6"
        rid = "wor_0000000000000006"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id, "run_06")
        resp = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        body = resp.json()
        for forbidden in ["raw_args", "args", "secret", "password", "token"]:
            assert forbidden not in body
