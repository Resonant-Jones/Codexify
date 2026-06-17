"""Focused backend tests for work-order result receipt creation."""

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
        "result_json": {"body": {"ok": True, "status": "ok"}, "headers": {}, "status_code": 200},
        "error_text": None,
    }


class _FakeReceiptDB:
    """Simulates a DB session for receipt persistence."""
    def __init__(self):
        self.receipts: dict[str, Any] = {}
    def get_session(self):
        return _FakeSession(self)
    def add(self, row): pass
    def commit(self): pass
    def refresh(self, row): pass

class _FakeSession:
    def __init__(self, db: _FakeReceiptDB):
        self._db = db
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def add(self, row):
        self._db.receipts[row.receipt_id] = row
    def commit(self): pass
    def refresh(self, row): pass


def _build_client(monkeypatch) -> tuple[TestClient, Any, Any, _FakeReceiptDB]:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)
    coding_work_orders.configure_db(None)
    monkeypatch.setattr(coding_work_orders, "_command_bus_store", command_bus._store)
    _install_fake_loopback(monkeypatch)

    mock_wo_store = MagicMock()
    monkeypatch.setattr(coding_work_orders, "_store", mock_wo_store)

    fake_db = _FakeReceiptDB()
    monkeypatch.setattr(command_bus._store, "_db", fake_db)
    if not hasattr(command_bus._store, "_receipts"):
        command_bus._store._receipts = {}

    app = FastAPI()
    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]: return {"ok": True}
    app.include_router(command_bus.router)
    app.include_router(coding_work_orders.router)
    return TestClient(app), mock_wo_store, command_bus._store, fake_db


class TestWorkOrderResultReceipts:
    def test_creates_receipt_with_observed_fields(self, monkeypatch) -> None:
        client, wo_store, cb_store, fake_db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa1"
        run_id = "run_0000000000000001"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run = MagicMock(return_value=_mock_command_run(run_id))

        resp = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["receipt_id"].startswith("wor_")
        assert body["work_order_id"] == wo_id
        assert body["command_run_id"] == run_id
        assert body["receipt_kind"] == "command_run_observation"
        assert body["observed_run_status"] == "completed"
        assert "ok" in body["observed_result_summary"].lower()
        assert body["integrity_hash"]
        assert body["schema_version"] == 1
        assert body["review_state"] == "unreviewed"
        assert "provenance_json" in body
        assert "redaction_summary_json" in body
        # No raw args
        for forbidden in ["raw_args", "args", "secret", "password"]:
            assert forbidden not in body

    def test_no_linked_run_fails(self, monkeypatch) -> None:
        client, wo_store, cb_store, fake_db = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = _mock_work_order("wo_aaaaaaaaaaaaaaa2", latest_run_id=None)
        resp = client.post("/api/coding/work-orders/wo_aaaaaaaaaaaaaaa2/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_missing_work_order_fails(self, monkeypatch) -> None:
        client, wo_store, cb_store, fake_db = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = None
        resp = client.post("/api/coding/work-orders/wo_n0nex1stent0000/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_duplicate_receipt_idempotent_or_conflict(self, monkeypatch) -> None:
        client, wo_store, cb_store, fake_db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa3"
        run_id = "run_0000000000000003"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run = MagicMock(return_value=_mock_command_run(run_id))
        # First receipt
        r1 = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert r1.status_code == 201
        # Second receipt — should succeed (new receipt) or conflict depending on uniqueness
        r2 = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        # With in-memory fallback, duplicates are allowed (no unique constraint enforcement)
        # With real DB, the unique constraint would block duplicates
        assert r2.status_code in (201, 409)
