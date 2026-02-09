from __future__ import annotations

import json

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from guardian.ws.router import router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_ws_rejects_malformed_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    client = _build_client()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
            ws.send_json({"id": "1", "method": "ping", "params": {}})
            ws.receive_json()

    assert exc.value.code == 4400


def test_ws_rejects_oversized_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    client = _build_client()

    payload = {
        "type": "request",
        "id": "1",
        "method": "ping",
        "params": {"blob": "x" * 70000},
    }

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
            ws.send_text(json.dumps(payload))
            ws.receive_json()

    assert exc.value.code == 4409
