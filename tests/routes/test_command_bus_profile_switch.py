from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus, system_profiles


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)

    app = FastAPI()

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(system_profiles.router)
    app.include_router(command_bus.router)
    return TestClient(app)


def _get_manifest(client: TestClient) -> dict[str, Any]:
    response = client.get(
        "/api/guardian/commands/manifest",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
    )
    assert response.status_code == 200
    return response.json()


def _command_id(manifest: dict[str, Any], *, method: str, path: str) -> str:
    for command in manifest.get("commands", []):
        if (
            command.get("method") == method
            and command.get("path_template") == path
        ):
            return str(command["command_id"])
    raise AssertionError(f"missing command for {method} {path}")


def test_command_bus_allows_profile_switch_only(monkeypatch) -> None:
    captured: list[dict[str, Any]] = []

    async def _fake_execute_loopback_request(**kwargs: Any) -> dict[str, Any]:
        captured.append(dict(kwargs))
        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"ok": True, "active_profile_id": "local_mode"},
        }

    monkeypatch.setattr(
        "guardian.command_bus.invoke.execute_loopback_request",
        _fake_execute_loopback_request,
    )

    client = _build_client(monkeypatch)
    manifest = _get_manifest(client)
    switch_command_id = _command_id(
        manifest, method="POST", path="/api/system-profiles/switch"
    )
    write_command_id = _command_id(manifest, method="POST", path="/write")

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": switch_command_id,
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {"body": {"thread_id": 1, "profile_id": "local_mode"}},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["inline_result"]["status_code"] == 200
    assert captured
    assert captured[0]["method"] == "POST"
    assert captured[0]["path_template"] == "/api/system-profiles/switch"
    assert "/tools/execute" not in captured[0]["path_template"]

    blocked = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": write_command_id,
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {"body": {"value": 1}},
        },
    )
    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert blocked_payload["status"] == "blocked"
    assert blocked_payload["error"] in {
        "phase1_write_blocked",
        "policy_require_confirmation:write_effect,risk_high",
    }
    assert len(captured) == 1
