from __future__ import annotations

from importlib import import_module

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from guardian.ws.rate_limiter import TokenBucketRateLimiter

ws_router_module = import_module("guardian.ws.router")


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(ws_router_module.router)
    return TestClient(app)


def test_ws_idle_timeout_disconnects_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setattr(
        ws_router_module.settings,
        "WS_RPC_IDLE_TIMEOUT_SECONDS",
        0.05,
    )
    monkeypatch.setattr(
        ws_router_module,
        "rate_limiter",
        TokenBucketRateLimiter(
            capacity=100,
            refill_per_second=100.0,
            namespace="test:ws:idle-timeout",
        ),
    )

    client = _client()
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
            ws.receive_json()

    assert exc.value.code == ws_router_module.IDLE_TIMEOUT_CLOSE_CODE
