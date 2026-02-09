from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.ws.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_unknown_method_returns_structured_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    client = _client()

    with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
        ws.send_json(
            {
                "type": "request",
                "id": "unknown-1",
                "method": "no.such.method",
                "params": {},
            }
        )
        response = ws.receive_json()

    assert response["type"] == "response"
    assert response["id"] == "unknown-1"
    assert response["result"] is None
    assert response["error"]["code"] == "unknown_method"
    assert "no.such.method" in response["error"]["message"]


def test_permission_gated_method_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-api-key")
    monkeypatch.setenv("GUARDIAN_ADMIN_TOKEN", "admin-token")
    client = _client()

    with client.websocket_connect("/api/ws/rpc?api_key=test-api-key") as ws:
        ws.send_json(
            {
                "type": "request",
                "id": "perm-1",
                "method": "thread.list",
                "params": {},
            }
        )
        response = ws.receive_json()

    assert response["type"] == "response"
    assert response["id"] == "perm-1"
    assert response["result"] is None
    assert response["error"]["code"] == "permission_denied"
    assert "admin_required" in response["error"]["message"]
