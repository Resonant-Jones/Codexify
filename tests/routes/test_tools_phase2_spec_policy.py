from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus, tools


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    command_bus.configure_db(None)
    tools.JOBS.clear()

    app = FastAPI()

    @app.get("/ping", operation_id="ping_ping_get")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/external/ping", operation_id="external_ping_get")
    def external_ping() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(command_bus.router)
    app.include_router(tools.router)
    app.include_router(tools.api_router)
    return TestClient(app)


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": "test-key", "X-User-Id": "local"}


def _command_id(manifest: dict[str, Any], *, method: str, path: str) -> str:
    for command in manifest.get("commands", []):
        if (
            command.get("method") == method
            and command.get("path_template") == path
        ):
            return str(command["command_id"])
    raise AssertionError(f"missing command for {method} {path}")


def _install_fake_loopback(monkeypatch, captured: list[dict[str, Any]]) -> None:
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
            captured.append(dict(kwargs))
            return _FakeResponse()

    monkeypatch.setattr(
        "guardian.command_bus.loopback_http_adapter.httpx.AsyncClient",
        _FakeAsyncClient,
    )


def test_tools_manifest_derivation_matches_command_manifest(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    command_manifest_response = client.get(
        "/api/guardian/commands/manifest", headers=_auth_headers()
    )
    assert command_manifest_response.status_code == 200
    command_manifest = command_manifest_response.json()

    tools_manifest_response = client.get(
        "/api/tools/manifest", headers=_auth_headers()
    )
    assert tools_manifest_response.status_code == 200
    tools_manifest = tools_manifest_response.json()
    assert tools_manifest["manifest_version"] == command_manifest["manifest_version"]
    assert len(tools_manifest["command_manifest_hash"]) == 64

    commands_by_id = {
        item["command_id"]: item for item in command_manifest.get("commands", [])
    }
    for tool in tools_manifest.get("tools", []):
        command = commands_by_id[tool["command_id"]]
        assert tool["tool_id"] == tool["command_id"]
        assert tool["name"] == tool["command_id"]
        assert tool["risk"] == command["risk"]
        assert tool["effect"] == command["effect"]
        assert tool["idempotency"] == command["idempotency"]

    function_names = {
        item["function"]["name"] for item in tools_manifest.get("openai_tools", [])
    }
    assert function_names == {
        item["name"] for item in tools_manifest.get("tools", [])
    }


def test_policy_blocks_write_when_enforce(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    client = _build_client(monkeypatch)
    command_manifest = client.get(
        "/api/guardian/commands/manifest", headers=_auth_headers()
    ).json()
    write_command_id = _command_id(command_manifest, method="POST", path="/write")

    invoke_response = client.post(
        "/api/guardian/commands/invoke",
        headers=_auth_headers(),
        json={
            "invoke_version": "1.0",
            "command_id": write_command_id,
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"body": {"value": 1}},
        },
    )
    assert invoke_response.status_code == 200
    invoke_payload = invoke_response.json()
    assert invoke_payload["status"] == "blocked"
    assert invoke_payload["error"].startswith("policy_require_confirmation:")
    assert "write_effect" in invoke_payload["error"]

    legacy_response = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={"method": "POST", "path": "/write", "args": {"value": 1}},
    )
    assert legacy_response.status_code == 200
    legacy_payload = legacy_response.json()
    assert legacy_payload["status"] == "blocked"
    assert legacy_payload["error"].startswith("policy_require_confirmation:")


def test_policy_warn_allows_with_warning(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "warn")
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)
    command_manifest = client.get(
        "/api/guardian/commands/manifest", headers=_auth_headers()
    ).json()
    external_command_id = _command_id(
        command_manifest, method="GET", path="/external/ping"
    )

    response = client.post(
        "/api/guardian/commands/invoke",
        headers=_auth_headers(),
        json={
            "invoke_version": "1.0",
            "command_id": external_command_id,
            "actor": {"kind": "human", "id": "local"},
            "arguments": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["policy_warnings"]
    assert payload["policy_warnings"][0]["decision"] == "require_confirmation"
    assert "external_network" in payload["policy_warnings"][0]["reason_codes"]
    assert len(captured) == 1

    events = command_bus._store.list_events_after(
        run_id=payload["run_id"], after_seq=0
    )
    run_created = events[0]
    assert run_created["event_type"] == "run.created"
    assert run_created["payload_json"]["policy"]["warnings"]


def test_api_tools_execute_invokes_ping_with_command_id(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "command_id": "op::ping_ping_get",
            "arguments": {},
            "actor": {"kind": "human", "id": "local"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["command_id"] == "op::ping_ping_get"
    assert payload["run_id"]
    assert payload["job_id"] == payload["run_id"]
    assert len(captured) == 1


def test_loopback_required_for_execution(monkeypatch) -> None:
    monkeypatch.delenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", raising=False)
    monkeypatch.delenv("GUARDIAN_API_BASE", raising=False)
    monkeypatch.delenv("LOCAL_DEV", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")

    client = _build_client(monkeypatch)
    command_manifest = client.get(
        "/api/guardian/commands/manifest", headers=_auth_headers()
    ).json()
    ping_command_id = _command_id(command_manifest, method="GET", path="/ping")

    response = client.post(
        "/api/guardian/commands/invoke",
        headers=_auth_headers(),
        json={
            "invoke_version": "1.0",
            "command_id": ping_command_id,
            "actor": {"kind": "human", "id": "local"},
            "arguments": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["error"].startswith("policy_deny:")
    assert "loopback_base_missing" in payload["error"]
