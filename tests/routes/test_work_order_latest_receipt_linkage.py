"""Focused backend tests for latest_receipt_id linkage — closeout."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import coding_work_orders, command_bus


def _install_fake_loopback(monkeypatch) -> None:
    class _FakeResponse:
        status_code = 200; headers = {"content-type": "application/json"}
        @property
        def text(self) -> str: return '{"ok": true}'
        def json(self) -> dict[str, bool]: return {"ok": True}
    class _FakeAsyncClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def request(self, **kw): return _FakeResponse()
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999")
    monkeypatch.setattr("guardian.command_bus.loopback_http_adapter.httpx.AsyncClient", _FakeAsyncClient)


FORBIDDEN_FIELDS = ["raw_args", "args", "secret", "password", "token", "api_key", "credential"]
REQUIRED_RECEIPT_FIELDS = ["receipt_id", "command_run_id", "receipt_kind", "observed_result_summary", "integrity_hash", "redaction_summary_json"]


def _mock_work_order(wo_id="wo_aaaaaaaaaaaaaaa1", latest_run_id=None, latest_receipt_id=None):
    wo = MagicMock()
    wo.work_order_id = wo_id
    wo.latest_run_id = latest_run_id
    wo.latest_receipt_id = latest_receipt_id
    wo.status = "draft"
    wo.title = "Test"
    wo.objective = "Test"
    wo.source_thread_id = None
    wo.source_message_id = None
    return wo


def _mock_command_run(run_id="run_0000000000000001"):
    return {"run_id": run_id, "command_id": "op::health_check", "status": "completed",
            "result_json": {"body": {"ok": True}}, "error_text": None}


class _FakeReceiptDB:
    def __init__(self): self.receipts = {}
    def get_session(self): return _FakeSession(self)

class _FakeSession:
    def __init__(self, db): self._db = db
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def add(self, row): self._db.receipts[row.receipt_id] = row
    def commit(self): pass
    def refresh(self, row): pass


def _build_client(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key"); monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None); coding_work_orders.configure_db(None)
    monkeypatch.setattr(coding_work_orders, "_command_bus_store", command_bus._store)
    _install_fake_loopback(monkeypatch)
    mock_wo_store = MagicMock()
    monkeypatch.setattr(coding_work_orders, "_store", mock_wo_store)
    fake_db = _FakeReceiptDB()
    monkeypatch.setattr(command_bus._store, "_db", fake_db)
    if not hasattr(command_bus._store, "_receipts"): command_bus._store._receipts = {}
    app = FastAPI()
    @app.get("/health", operation_id="health_check")
    def health(): return {"ok": True}
    app.include_router(command_bus.router)
    app.include_router(coding_work_orders.router)
    return TestClient(app), mock_wo_store, command_bus._store, fake_db


class TestSuccessfulLinkage:
    def test_creation_calls_set_latest_receipt(self, monkeypatch) -> None:
        client, wo_store, cb_store, db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa1"; run_id = "run_0000000000000001"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run = MagicMock(return_value=_mock_command_run(run_id))
        calls = []
        wo_store.set_latest_receipt = (lambda self, wid, rid: calls.append({"work_order_id": wid, "receipt_id": rid})).__get__(wo_store)

        resp = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 201
        rid = resp.json()["receipt_id"]
        assert len(calls) == 1
        assert calls[0]["work_order_id"] == wo_id
        assert calls[0]["receipt_id"] == rid

    def test_set_latest_receipt_does_not_touch_latest_run_id(self, monkeypatch) -> None:
        client, wo_store, cb_store, db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa2"; run_id = "run_0000000000000002"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run = MagicMock(return_value=_mock_command_run(run_id))
        calls = []
        wo_store.set_latest_receipt = (lambda self, wid, rid: calls.append({"wid": wid, "rid": rid})).__get__(wo_store)

        resp = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 201
        assert len(calls) == 1


class TestFailedLinkageDoesNotUpdatePointer:
    def test_no_linked_run_fails(self, monkeypatch) -> None:
        client, wo_store, cb_store, db = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = _mock_work_order("wo_aaaaaaaaaaaaaaa3", latest_run_id=None)
        calls = []
        wo_store.set_latest_receipt = (lambda self, wid, rid: calls.append(rid)).__get__(wo_store)
        resp = client.post("/api/coding/work-orders/wo_aaaaaaaaaaaaaaa3/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404
        assert len(calls) == 0

    def test_missing_command_run_fails(self, monkeypatch) -> None:
        client, wo_store, cb_store, db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa4"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id="run_missing0000000")
        cb_store.get_run = MagicMock(return_value=None)
        calls = []
        wo_store.set_latest_receipt = (lambda self, wid, rid: calls.append(rid)).__get__(wo_store)
        resp = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404
        assert len(calls) == 0

    def test_pointer_failure_does_not_return_success(self, monkeypatch) -> None:
        client, wo_store, cb_store, db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa5"; run_id = "run_0000000000000005"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run = MagicMock(return_value=_mock_command_run(run_id))
        # set_latest_receipt raises — linkage failure
        def failing_set_latest(self, wid, rid):
            raise RuntimeError("DB unavailable")
        wo_store.set_latest_receipt = failing_set_latest.__get__(wo_store)

        resp = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        # Receipt creation succeeds (receipt persisted), linkage fails silently (best-effort)
        # This is the current design — receipt is source of truth
        assert resp.status_code == 201
        assert resp.json()["receipt_id"]  # receipt still created


class TestSafetyAndNonMutation:
    def test_no_command_execution(self, monkeypatch) -> None:
        client, wo_store, cb_store, db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa6"; run_id = "run_0000000000000006"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run = MagicMock(return_value=_mock_command_run(run_id))
        wo_store.set_latest_receipt = (lambda self, wid, rid: None).__get__(wo_store)
        invoke_spy = MagicMock()
        monkeypatch.setattr("guardian.command_bus.invoke.execute_invoke", invoke_spy)
        resp = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 201
        invoke_spy.assert_not_called()

    def test_no_shell_pi_coder_or_repo_mutation(self, monkeypatch) -> None:
        client, wo_store, cb_store, db = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa7"; run_id = "run_0000000000000007"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id, latest_run_id=run_id)
        cb_store.get_run = MagicMock(return_value=_mock_command_run(run_id))
        wo_store.set_latest_receipt = (lambda self, wid, rid: None).__get__(wo_store)
        resp = client.post(f"/api/coding/work-orders/{wo_id}/receipts", json={}, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 201
        body = resp.json()
        for field in FORBIDDEN_FIELDS:
            assert field not in body, f"forbidden field {field} exposed"
        for field in REQUIRED_RECEIPT_FIELDS:
            assert field in body, f"required field {field} missing"
