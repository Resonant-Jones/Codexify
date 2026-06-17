"""Focused backend tests for CommandRun readback route."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus


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


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)
    _install_fake_loopback(monkeypatch)

    app = FastAPI()
    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]: return {"ok": True}
    app.include_router(command_bus.router)
    return TestClient(app)


def _invoke_health(client: TestClient) -> dict[str, Any]:
    manifest = client.get("/api/guardian/commands/manifest", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
    cmd_id = next(c["command_id"] for c in manifest["commands"] if c["path_template"] == "/health")
    resp = client.post("/api/guardian/commands/invoke", json={
        "command_id": cmd_id, "invoke_version": "1.0",
        "actor": {"kind": "system", "id": "operator"},
        "arguments": {"path_params": {}, "query": {}, "headers": {}},
    }, headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
    return resp.json()


class TestCommandRunReadback:
    def test_returns_200_with_durable_data(self, monkeypatch) -> None:
        client = _build_client(monkeypatch)
        invoke = _invoke_health(client)
        run_id = invoke["run_id"]
        assert run_id is not None

        resp = client.get(f"/api/guardian/commands/runs/{run_id}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["run_id"] == run_id
        assert body["command_id"] == "op::health_check"
        assert body["status"] == "completed"
        assert "result_json" in body
        assert body["result_json"]["body"]["ok"] is True
        assert body["error_text"] is None
        assert body["actor_kind"] == "system"
        assert body["actor_id"] == "operator"
        assert body["auth_subject"] == "operator"
        assert body["args_hash"]
        assert "args_redacted" in body
        assert "events_url" in body
        assert body["events_url"].endswith("/events?after_seq=0")
        assert body["created_at"] is not None

    def test_no_raw_args_exposed(self, monkeypatch) -> None:
        client = _build_client(monkeypatch)
        invoke = _invoke_health(client)
        run_id = invoke["run_id"]
        resp = client.get(f"/api/guardian/commands/runs/{run_id}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        body = resp.json()
        for forbidden in ["raw_args", "args", "unredacted_args", "secret", "password", "token", "api_key"]:
            assert forbidden not in body

    def test_nonexistent_run_returns_404(self, monkeypatch) -> None:
        client = _build_client(monkeypatch)
        resp = client.get("/api/guardian/commands/runs/run_n0nex1stent0000", headers={"X-API-Key": "test-key", "X-User-Id": "operator"})
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == "command_run_not_found"

    def test_no_auth_returns_401_or_404(self, monkeypatch) -> None:
        client = _build_client(monkeypatch)
        resp = client.get("/api/guardian/commands/runs/run_0000000000000000")
        # Without auth, returns 404 (run not found) or 401/403 (auth rejected)
        assert resp.status_code in (401, 403, 404)

    def test_readback_does_not_mutate(self, monkeypatch) -> None:
        client = _build_client(monkeypatch)
        invoke = _invoke_health(client)
        run_id = invoke["run_id"]
        # First read
        r1 = client.get(f"/api/guardian/commands/runs/{run_id}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        # Second read — must be identical
        r2 = client.get(f"/api/guardian/commands/runs/{run_id}", headers={"X-API-Key": "test-key", "X-User-Id": "operator"}).json()
        assert r1["run_id"] == r2["run_id"]
        assert r1["status"] == r2["status"]
