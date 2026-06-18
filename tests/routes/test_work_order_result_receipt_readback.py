"""Focused backend tests for work-order result receipt readback routes — hardened."""

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


REQUIRED_FIELDS = [
    "receipt_id", "work_order_id", "command_run_id", "receipt_kind",
    "observed_command_id", "observed_run_status", "observed_result_summary",
    "observed_error_text", "created_at", "created_by", "source_thread_id",
    "source_message_id", "provenance_json", "redaction_summary_json",
    "integrity_hash", "schema_version", "review_state", "operator_note",
]

FORBIDDEN_FIELDS = ["raw_args", "args", "secret", "password", "token", "api_key", "credential"]


class _FakeReceiptRow:
    def __init__(self, receipt_id: str, work_order_id: str, command_run_id: str, summary: str = "Status: ok", created_at: str | None = None, **kwargs):
        self.receipt_id = receipt_id
        self.work_order_id = work_order_id
        self.command_run_id = command_run_id
        self.receipt_kind = "command_run_observation"
        self.observed_command_id = "op::health_check"
        self.observed_run_status = "completed"
        self.observed_result_summary = summary
        self.observed_error_text = None
        self.created_at = created_at
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


class TestSingleReceiptReadback:
    def test_response_includes_all_required_fields(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa1"; rid = "wor_0000000000000001"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id, "run_01")

        body = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        for field in REQUIRED_FIELDS:
            assert field in body, f"missing required field: {field}"
        for field in FORBIDDEN_FIELDS:
            assert field not in body, f"forbidden field exposed: {field}"

    def test_readback_is_read_only_idempotent(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa2"; rid = "wor_0000000000000002"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id, "run_02")
        r1 = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        r2 = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        assert r1["receipt_id"] == r2["receipt_id"]
        assert r1["observed_result_summary"] == r2["observed_result_summary"]


class TestReceiptList:
    def test_list_includes_receipts(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa3"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts["wor_10"] = _FakeReceiptRow("wor_10", wo_id, "run_10", summary="A", created_at="2026-01-01T00:00:00Z")
        cb_store._receipts["wor_20"] = _FakeReceiptRow("wor_20", wo_id, "run_20", summary="B", created_at="2026-01-02T00:00:00Z")

        body = client.get(f"/api/coding/work-orders/{wo_id}/receipts", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        assert body["work_order_id"] == wo_id
        assert len(body["receipts"]) == 2
        for item in body["receipts"]:
            for field in REQUIRED_FIELDS:
                assert field in item, f"list item missing field: {field}"

    def test_list_newest_first_when_dates_present(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa4"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts["wor_a"] = _FakeReceiptRow("wor_a", wo_id, "run_a", created_at="2026-01-01T00:00:00Z")
        cb_store._receipts["wor_b"] = _FakeReceiptRow("wor_b", wo_id, "run_b", created_at="2026-01-02T00:00:00Z")

        body = client.get(f"/api/coding/work-orders/{wo_id}/receipts", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        ids = [r["receipt_id"] for r in body["receipts"]]
        # Newest first: wor_b (Jan 2) before wor_a (Jan 1)
        assert ids == ["wor_b", "wor_a"], f"expected newest-first, got {ids}"


class TestErrorCases:
    def test_nonexistent_receipt_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = _mock_work_order("wo_aaaaaaaaaaaaaaa5")
        resp = client.get("/api/coding/work-orders/wo_aaaaaaaaaaaaaaa5/receipts/wor_n0nex1stent", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_missing_work_order_single_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = None
        resp = client.get("/api/coding/work-orders/wo_n0nex1stent0000/receipts/wor_0000000000000001", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_missing_work_order_list_404(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = None
        resp = client.get("/api/coding/work-orders/wo_n0nex1stent0000/receipts", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_cross_work_order_isolation_single(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = _mock_work_order("wo_aaaaaaaaaaaaaaa6")
        cb_store._receipts["wor_06"] = _FakeReceiptRow("wor_06", "wo_bbbbbbbbbbbbbbb6", "run_06")
        resp = client.get("/api/coding/work-orders/wo_aaaaaaaaaaaaaaa6/receipts/wor_06", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404

    def test_cross_work_order_isolation_list(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_store.get_work_order.return_value = _mock_work_order("wo_aaaaaaaaaaaaaaa7")
        cb_store._receipts["wor_07"] = _FakeReceiptRow("wor_07", "wo_bbbbbbbbbbbbbbb7", "run_07")
        body = client.get("/api/coding/work-orders/wo_aaaaaaaaaaaaaaa7/receipts", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        assert len(body["receipts"]) == 0


class TestSafetyAndNonMutation:
    def test_no_command_execution_during_readback(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa8"; rid = "wor_0000000000000008"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id, "run_08")
        invoke_spy = MagicMock()
        monkeypatch.setattr("guardian.command_bus.invoke.execute_invoke", invoke_spy)
        client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        invoke_spy.assert_not_called()

    def test_no_shell_pi_coder_or_repo_mutation(self, monkeypatch) -> None:
        client, wo_store, cb_store = _build_client(monkeypatch)
        wo_id = "wo_aaaaaaaaaaaaaaa9"; rid = "wor_0000000000000009"
        wo_store.get_work_order.return_value = _mock_work_order(wo_id)
        cb_store._receipts[rid] = _FakeReceiptRow(rid, wo_id, "run_09")
        resp = client.get(f"/api/coding/work-orders/{wo_id}/receipts/{rid}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        for field in FORBIDDEN_FIELDS:
            assert field not in body
        assert body["redaction_summary_json"]["args_redacted"] is True
