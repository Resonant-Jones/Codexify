from __future__ import annotations

from importlib import import_module

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.ws.rate_limiter import TokenBucketRateLimiter

ws_router_module = import_module("guardian.ws.router")


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(ws_router_module.router)
    return TestClient(app)


def test_ws_rate_limit_blocks_excess_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setattr(
        ws_router_module,
        "rate_limiter",
        TokenBucketRateLimiter(
            capacity=1,
            refill_per_second=0.01,
            namespace="test:ws:rate-limit",
        ),
    )

    client = _client()
    with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
        ws.send_json(
            {"type": "request", "id": "ok-1", "method": "ping", "params": {}}
        )
        first = ws.receive_json()
        assert first["result"] == {"ok": True}
        assert first["error"] is None

        ws.send_json(
            {"type": "request", "id": "limited-1", "method": "ping", "params": {}}
        )
        second = ws.receive_json()
        assert second["result"] is None
        assert second["error"]["code"] == "rate_limited"
