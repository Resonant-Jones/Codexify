from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.ws.manager import WSConnectionManager
from guardian.ws.rate_limiter import TokenBucketRateLimiter


class _FakeSession:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def add(self, obj: Any) -> None:
        self._rows.append(obj)

    def commit(self) -> None:
        return

    def rollback(self) -> None:
        return

    def close(self) -> None:
        return


class _FakeDB:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    def SessionLocal(self) -> _FakeSession:
        return _FakeSession(self.rows)


def _build_client(
    monkeypatch: pytest.MonkeyPatch, fake_db: _FakeDB
) -> TestClient:
    ws_routes = import_module("guardian.routes.websocket")
    monkeypatch.setattr(ws_routes, "manager", WSConnectionManager())
    monkeypatch.setattr(
        ws_routes,
        "rate_limiter",
        TokenBucketRateLimiter(
            capacity=100,
            refill_per_second=100.0,
            namespace="test:ws-route-audit",
        ),
    )
    monkeypatch.setattr(ws_routes.settings, "WS_RPC_IDLE_TIMEOUT_SECONDS", 5.0)
    monkeypatch.setattr(ws_routes.settings, "WS_RPC_MAX_CONNECTIONS", 100)
    ws_routes.configure_db(fake_db)

    app = FastAPI()
    app.include_router(ws_routes.router)
    return TestClient(app)


def test_ws_route_writes_audit_row_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    fake_db = _FakeDB()
    client = _build_client(monkeypatch, fake_db)

    with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
        ws.send_json(
            {"type": "request", "id": "1", "method": "ping", "params": {}}
        )
        response = ws.receive_json()

    assert response["error"] is None
    assert response["result"] == {"ok": True}
    assert len(fake_db.rows) == 1
    row = fake_db.rows[0]
    assert row.status == "ok"
    assert row.method == "ping"
    assert isinstance(row.params_hash, str)
    assert len(row.params_hash) == 64


def test_ws_route_writes_audit_row_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    fake_db = _FakeDB()
    client = _build_client(monkeypatch, fake_db)

    with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
        ws.send_json(
            {
                "type": "request",
                "id": "2",
                "method": "no.such.method",
                "params": {},
            }
        )
        response = ws.receive_json()

    assert response["error"]["code"] == "unknown_method"
    assert len(fake_db.rows) == 1
    row = fake_db.rows[0]
    assert row.status == "error"
    assert row.method == "no.such.method"
