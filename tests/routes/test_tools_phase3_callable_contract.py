from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import command_bus, tools


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    monkeypatch.setenv("DEBUG", "1")
    command_bus.configure_db(None)
    tools.JOBS.clear()

    app = FastAPI()

    @app.get("/ping", operation_id="ping_ping_get")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    app.include_router(command_bus.router)
    app.include_router(tools.router)
    app.include_router(tools.api_router)
    return TestClient(app)


def _auth_headers(user_id: str = "local") -> dict[str, str]:
    return {"X-API-Key": "test-key", "X-User-Id": user_id}


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


def test_plan_mode_returns_envelope_and_does_not_dispatch(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "mode": "plan",
            "tool_id": "op::ping_ping_get",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "planned"
    assert payload["normalized_arguments"] == {
        "path_params": {},
        "query": {},
        "headers": {},
        "body": {},
    }
    assert payload["policy"]["decision"] == "allow"
    assert payload.get("run_id") is None
    assert len(captured) == 0


def test_execute_read_tool_returns_completed_run(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "mode": "execute",
            "tool_id": "op::ping_ping_get",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["run_id"]
    assert payload["events_url"]
    assert payload["result"]["status_code"] == 200
    assert len(captured) == 1


def test_execute_write_requires_approval(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    client = _build_client(monkeypatch)

    response = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "mode": "execute",
            "tool_id": "op::write_item",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"body": {"x": 1}},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["approval_required"] is True
    assert isinstance(payload["approval_token"], str)
    assert payload["policy"]["decision"] == "require_confirmation"


def test_approve_executes_and_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    initial = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "mode": "execute",
            "tool_id": "op::write_item",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"body": {"x": 1}},
        },
    )
    assert initial.status_code == 200
    token = initial.json()["approval_token"]
    assert token

    approved_first = client.post(
        "/api/tools/approve",
        headers=_auth_headers(),
        json={"approval_token": token},
    )
    assert approved_first.status_code == 200
    first_payload = approved_first.json()
    assert first_payload["status"] == "completed"
    assert first_payload["run_id"]

    approved_second = client.post(
        "/api/tools/approve",
        headers=_auth_headers(),
        json={"approval_token": token},
    )
    assert approved_second.status_code == 200
    second_payload = approved_second.json()
    assert second_payload["status"] == "completed"
    assert second_payload["run_id"] == first_payload["run_id"]
    assert len(captured) == 1


def test_approve_rejects_tampered_or_mismatched_tokens(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    initial = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "mode": "execute",
            "tool_id": "op::write_item",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"body": {"x": 1}},
        },
    )
    token = initial.json()["approval_token"]
    assert token

    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    tampered_response = client.post(
        "/api/tools/approve",
        headers=_auth_headers(),
        json={"approval_token": tampered},
    )
    assert tampered_response.status_code == 400

    mismatch_response = client.post(
        "/api/tools/approve",
        headers=_auth_headers(user_id="other"),
        json={"approval_token": token},
    )
    assert mismatch_response.status_code == 403


def test_openai_name_mapping_is_stable_and_reversible(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    first = client.get("/api/tools/manifest", headers=_auth_headers()).json()
    second = client.get("/api/tools/manifest", headers=_auth_headers()).json()

    name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
    first_mapping: dict[str, str] = {}
    for item in first["openai_tools"]:
        function = item["function"]
        name = function["name"]
        tool_id = function["x_codexify_tool_id"]
        assert name_pattern.match(name)
        assert item["x_codexify_tool_id"] == tool_id
        assert name not in first_mapping
        first_mapping[name] = tool_id

    for tool in first["tools"]:
        assert tool["openai_name"] in first_mapping
        assert first_mapping[tool["openai_name"]] == tool["tool_id"]

    second_mapping = {
        item["function"]["name"]: item["function"]["x_codexify_tool_id"]
        for item in second["openai_tools"]
    }
    assert first_mapping == second_mapping


def test_unknown_args_rejected_unless_passthrough_enabled(monkeypatch) -> None:
    client = _build_client(monkeypatch)

    rejected = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "mode": "plan",
            "tool_id": "op::ping_ping_get",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"unexpected": "value"},
        },
    )
    assert rejected.status_code == 400
    assert rejected.json()["detail"]["error"] == "unknown_argument_keys"

    original_get_tool_maps = tools._get_tool_maps

    def _patched_get_tool_maps(manifest_payload):
        (
            tools_list,
            tools_by_tool_id,
            tools_by_command_id,
            tools_by_openai_name,
        ) = original_get_tool_maps(manifest_payload)
        patched_tools_list = []
        patched_by_tool_id = {}
        patched_by_command_id = {}
        patched_by_openai_name = {}
        for tool in tools_list:
            patched = tool
            if tool.tool_id == "op::ping_ping_get":
                patched = tool.model_copy(
                    update={"allow_passthrough_arguments": True}
                )
            patched_tools_list.append(patched)
            patched_by_tool_id[patched.tool_id] = patched
            patched_by_command_id[patched.command_id] = patched
            patched_by_openai_name[patched.openai_name] = patched
        return (
            patched_tools_list,
            patched_by_tool_id,
            patched_by_command_id,
            patched_by_openai_name,
        )

    monkeypatch.setattr(tools, "_get_tool_maps", _patched_get_tool_maps)

    accepted = client.post(
        "/api/tools/execute",
        headers=_auth_headers(),
        json={
            "mode": "plan",
            "tool_id": "op::ping_ping_get",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"unexpected": "value"},
        },
    )
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["status"] == "planned"
    assert payload["normalized_arguments"]["query"] == {"unexpected": "value"}


def test_legacy_response_adapter_for_execute_and_approve(monkeypatch) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    captured: list[dict[str, Any]] = []
    _install_fake_loopback(monkeypatch, captured)
    client = _build_client(monkeypatch)

    execute_legacy = client.post(
        "/api/tools/execute?legacy=1",
        headers=_auth_headers(),
        json={
            "mode": "execute",
            "tool_id": "op::ping_ping_get",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {},
        },
    )
    assert execute_legacy.status_code == 200
    legacy_payload = execute_legacy.json()
    assert "job_id" in legacy_payload
    assert "result" in legacy_payload
    assert "policy_warnings" in legacy_payload

    blocked = client.post(
        "/api/tools/execute?legacy=1",
        headers=_auth_headers(),
        json={
            "mode": "execute",
            "tool_id": "op::write_item",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"body": {"x": 1}},
        },
    )
    assert blocked.status_code == 200
    blocked_payload = blocked.json()
    assert blocked_payload["status"] == "blocked"
    assert blocked_payload["approval_required"] is True

    approved_legacy = client.post(
        "/api/tools/approve?legacy=1",
        headers=_auth_headers(),
        json={"approval_token": blocked_payload["approval_token"]},
    )
    assert approved_legacy.status_code == 200
    approved_payload = approved_legacy.json()
    assert "job_id" in approved_payload
    assert approved_payload["status"] == "completed"


def test_raw_command_bus_lane_cannot_unlock_write_execution(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CODEXIFY_POLICY_MODE", "enforce")
    client = _build_client(monkeypatch)

    blocked = client.post(
        "/api/guardian/commands/invoke",
        headers=_auth_headers(),
        json={
            "invoke_version": "1.0",
            "command_id": "op::write_item",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"body": {"x": 1}},
        },
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"

    rejected_extra = client.post(
        "/api/guardian/commands/invoke",
        headers=_auth_headers(),
        json={
            "invoke_version": "1.0",
            "command_id": "op::write_item",
            "actor": {"kind": "human", "id": "local"},
            "arguments": {"body": {"x": 1}},
            "execution_lane": "tools",
            "allow_write_execution": True,
        },
    )
    assert rejected_extra.status_code == 422
