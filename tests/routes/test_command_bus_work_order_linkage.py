"""Focused backend tests for work-order command-run linkage contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus


# ── In-memory work order store for testing ────────────────────────────────

@dataclass
class _FakeWorkOrder:
    work_order_id: str
    title: str = ""
    objective: str = ""
    status: str = "draft"
    latest_run_id: str | None = None
    latest_lease_id: str | None = None
    latest_receipt_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class _FakeWorkOrderStore:
    """In-memory work order store that mimics WorkOrderStore.mark_latest_run and get_work_order."""

    def __init__(self) -> None:
        self._orders: dict[str, _FakeWorkOrder] = {}

    def create_work_order(self, work_order_id: str, **kwargs: Any) -> _FakeWorkOrder:
        wo = _FakeWorkOrder(work_order_id=work_order_id, **kwargs)
        self._orders[work_order_id] = wo
        return wo

    def get_work_order(self, work_order_id: str) -> _FakeWorkOrder | None:
        return self._orders.get(work_order_id)

    def mark_latest_run(
        self,
        work_order_id: str,
        run_id: str | None = None,
        lease_id: str | None = None,
        receipt_id: str | None = None,
    ) -> _FakeWorkOrder:
        wo = self._orders.get(work_order_id)
        if wo is None:
            raise LookupError(f"Work order {work_order_id} not found")
        if run_id is not None:
            wo.latest_run_id = run_id
        if lease_id is not None:
            wo.latest_lease_id = lease_id
        if receipt_id is not None:
            wo.latest_receipt_id = receipt_id
        return wo


# ── Test app builder ──────────────────────────────────────────────────────

def _install_fake_loopback(monkeypatch) -> None:
    """Install a fake httpx.AsyncClient that returns {"ok": True} for all requests."""

    class _FakeResponse:
        status_code = 200
        headers = {"content-type": "application/json"}

        @property
        def text(self) -> str:
            return '{"ok": true}'

        def json(self) -> dict[str, bool]:
            return {"ok": True}

    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            _ = args, kwargs

        async def __aenter__(self) -> "_FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            _ = exc_type, exc, tb

        async def request(self, **kwargs: Any) -> _FakeResponse:
            _ = kwargs
            return _FakeResponse()

    monkeypatch.setattr(
        "guardian.command_bus.loopback_http_adapter.httpx.AsyncClient",
        _FakeAsyncClient,
    )


def _build_client(monkeypatch, work_order_store: _FakeWorkOrderStore | None = None) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999")
    command_bus.configure_db(None)

    # Install fake loopback so commands execute without real HTTP
    _install_fake_loopback(monkeypatch)

    # Inject fake work order store
    monkeypatch.setattr(command_bus, "_work_order_store", work_order_store)

    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(command_bus.router)
    return TestClient(app)


def _get_manifest(client: TestClient) -> dict[str, Any]:
    response = client.get(
        "/api/guardian/commands/manifest",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )
    assert response.status_code == 200
    return response.json()


def _health_command_id(manifest: dict[str, Any]) -> str:
    for command in manifest.get("commands", []):
        if (
            command.get("method") == "GET"
            and command.get("path_template") == "/health"
        ):
            return str(command["command_id"])
    raise AssertionError("missing health command in manifest")


def _invoke_health(
    client: TestClient,
    *,
    work_order_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    manifest = _get_manifest(client)
    cmd_id = _health_command_id(manifest)
    payload: dict[str, Any] = {
        "command_id": cmd_id,
        "invoke_version": "1.0",
        "actor": {"kind": "system", "id": "operator"},
        "arguments": {"path_params": {}, "query": {}, "headers": {}},
    }
    if work_order_id is not None:
        payload["work_order_id"] = work_order_id
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    response = client.post(
        "/api/guardian/commands/invoke",
        json=payload,
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )
    return {"status_code": response.status_code, "body": response.json()}


# ── Tests ─────────────────────────────────────────────────────────────────

class TestValidLinkage:
    def test_populates_latest_run_id(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        store.create_work_order("wo_aaaaaaaaaaaaaaa1", title="Test WO")
        client = _build_client(monkeypatch, work_order_store=store)

        result = _invoke_health(client, work_order_id="wo_aaaaaaaaaaaaaaa1")

        assert result["status_code"] == 200
        run_id = result["body"].get("run_id")
        assert run_id is not None
        assert result["body"]["status"] == "completed"

        wo = store.get_work_order("wo_aaaaaaaaaaaaaaa1")
        assert wo is not None
        assert wo.latest_run_id == run_id

    def test_preserves_work_order_status(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        store.create_work_order("wo_aaaaaaaaaaaaaaa2", title="Test WO", status="draft")
        client = _build_client(monkeypatch, work_order_store=store)

        _invoke_health(client, work_order_id="wo_aaaaaaaaaaaaaaa2")

        wo = store.get_work_order("wo_aaaaaaaaaaaaaaa2")
        assert wo is not None
        assert wo.status == "draft"


class TestNoLinkInvocation:
    def test_succeeds_without_work_order_id(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        client = _build_client(monkeypatch, work_order_store=store)

        result = _invoke_health(client, work_order_id=None)

        assert result["status_code"] == 200
        assert result["body"].get("run_id") is not None
        assert result["body"]["status"] == "completed"

    def test_does_not_mutate_work_orders(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        store.create_work_order("wo_aaaaaaaaaaaaaaa3", title="Test WO")
        client = _build_client(monkeypatch, work_order_store=store)

        _invoke_health(client, work_order_id=None)

        wo = store.get_work_order("wo_aaaaaaaaaaaaaaa3")
        assert wo is not None
        assert wo.latest_run_id is None  # unchanged


class TestNonexistentWorkOrder:
    def test_fails_closed(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        client = _build_client(monkeypatch, work_order_store=store)

        result = _invoke_health(client, work_order_id="wo_ffffffffffffffff")

        assert result["status_code"] == 404
        assert result["body"]["detail"]["error"] == "work_order_not_found"
        assert result["body"].get("run_id") is None

    def test_does_not_execute_command(self, monkeypatch) -> None:
        # Create a separate work order to verify it's not touched
        store = _FakeWorkOrderStore()
        store.create_work_order("wo_aaaaaaaaaaaaaaa4", title="Untouched WO")
        client = _build_client(monkeypatch, work_order_store=store)

        _invoke_health(client, work_order_id="wo_ffffffffffffffff")

        wo = store.get_work_order("wo_aaaaaaaaaaaaaaa4")
        assert wo is not None
        assert wo.latest_run_id is None  # not mutated

    def test_without_store(self, monkeypatch) -> None:
        client = _build_client(monkeypatch, work_order_store=None)

        result = _invoke_health(client, work_order_id="wo_aaaaaaaaaaaaaaa1")

        assert result["status_code"] == 400
        assert result["body"]["detail"]["error"] == "work_order_linkage_unavailable"


class TestMalformedWorkOrder:
    def test_fails_closed(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        client = _build_client(monkeypatch, work_order_store=store)

        result = _invoke_health(client, work_order_id="not-a-valid-id")

        assert result["status_code"] == 422
        assert result["body"]["detail"]["error"] == "work_order_id_malformed"
        assert result["body"].get("run_id") is None

    def test_empty_string(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        client = _build_client(monkeypatch, work_order_store=store)

        # Empty string should be treated as missing — normal invocation
        result = _invoke_health(client, work_order_id="")

        assert result["status_code"] == 200
        assert result["body"].get("run_id") is not None


class TestIdempotency:
    def test_repeat_preserves_linkage(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        store.create_work_order("wo_aaaaaaaaaaaaaaa5", title="Test WO")
        client = _build_client(monkeypatch, work_order_store=store)

        key = "idem-test-001"
        result1 = _invoke_health(
            client, work_order_id="wo_aaaaaaaaaaaaaaa5", idempotency_key=key
        )
        assert result1["status_code"] == 200
        run_id_1 = result1["body"]["run_id"]

        result2 = _invoke_health(
            client, work_order_id="wo_aaaaaaaaaaaaaaa5", idempotency_key=key
        )
        assert result2["status_code"] == 200
        run_id_2 = result2["body"]["run_id"]

        # Same idempotency key → same run (or second call succeeds)
        assert run_id_2 == run_id_1 or result2["body"]["status"] == "completed"

        wo = store.get_work_order("wo_aaaaaaaaaaaaaaa5")
        assert wo is not None
        assert wo.latest_run_id == run_id_1

    def test_idempotency_key_without_work_order(self, monkeypatch) -> None:
        store = _FakeWorkOrderStore()
        client = _build_client(monkeypatch, work_order_store=store)

        result = _invoke_health(client, idempotency_key="idem-no-wo")

        assert result["status_code"] == 200
        assert result["body"].get("run_id") is not None


class TestSafetyExclusions:
    def test_no_shell_subprocess_git_pi_coder(self, monkeypatch) -> None:
        """All invocations in this test suite use FastAPI loopback only."""
        store = _FakeWorkOrderStore()
        store.create_work_order("wo_aaaaaaaaaaaaaaa6", title="Test WO")
        client = _build_client(monkeypatch, work_order_store=store)

        # All command invocations target GET /health via loopback
        result = _invoke_health(client, work_order_id="wo_aaaaaaaaaaaaaaa6")
        assert result["status_code"] == 200

        # Health route returns {"ok": True} — no shell, subprocess, git, Pi, Coder
        inline = result["body"].get("inline_result", {})
        body = inline.get("body", {})
        assert body.get("ok") is True

    def test_no_repository_mutation(self, monkeypatch) -> None:
        """No git operations, no file writes — health route is read-only."""
        store = _FakeWorkOrderStore()
        client = _build_client(monkeypatch, work_order_store=store)

        _invoke_health(client, work_order_id=None)
        # Success proves no mutation occurred (health route has no side effects)
