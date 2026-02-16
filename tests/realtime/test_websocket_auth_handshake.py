from __future__ import annotations

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from guardian.ws.router import router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_ws_auth_rejects_missing_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    client = _build_client()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/ws/rpc") as ws:
            ws.send_json({"type": "auth"})
            ws.receive_json()

    assert exc.value.code == 4401


def test_ws_auth_accepts_query_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    client = _build_client()

    with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
        ws.send_json(
            {"type": "request", "id": "1", "method": "ping", "params": {}}
        )
        response = ws.receive_json()

    assert response["type"] == "response"
    assert response["id"] == "1"
    assert response["result"] == {"ok": True}


def test_ws_auth_accepts_first_message_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    client = _build_client()

    with client.websocket_connect("/api/ws/rpc") as ws:
        ws.send_json({"type": "auth", "api_key": "test-api-key"})
        ws.send_json(
            {"type": "request", "id": "2", "method": "ping", "params": {}}
        )
        response = ws.receive_json()

    assert response["id"] == "2"
    assert response["result"] == {"ok": True}
