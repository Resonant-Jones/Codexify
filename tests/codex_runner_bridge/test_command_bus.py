from __future__ import annotations

import ast
import json
import inspect
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from guardian.command_bus import invoke as invoke_module
from guardian.command_bus.contracts import InvokeArguments
from guardian.codex_runner_bridge import command_bus as bridge_command_bus
from guardian.codex_runner_bridge import adapter as bridge_adapter
from guardian.codex_runner_bridge import contracts as bridge_contracts
from guardian.routes import command_bus as command_bus_routes


def _build_client(monkeypatch) -> TestClient:
    monkeypatch.setenv("GUARDIAN_API_KEY", "test-key")
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    command_bus_routes.configure_db(None)

    app = FastAPI()

    @app.get("/health", operation_id="health_check")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/write", operation_id="write_item")
    def write(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "payload": payload}

    def _current_user(request: Request) -> str:
        return request.headers.get("X-User-Id", "operator")

    app.dependency_overrides[command_bus_routes.get_current_user] = _current_user
    app.include_router(command_bus_routes.router)
    return TestClient(app)


def _bridge_response(
    *,
    command_kind: str,
    result: bridge_contracts.GuardianBridgeResult,
    reason: str,
    correlation_id: str,
) -> bridge_contracts.GuardianBridgeResponse:
    return bridge_contracts.GuardianBridgeResponse(
        command_kind=command_kind,
        result=result,
        reason=reason,
        correlation_id=correlation_id,
        json_payload={
            "command_kind": command_kind,
            "result": result.value,
            "reason": reason,
            "correlation_id": correlation_id,
        },
    )


def _invoke_bridge_command(
    client: TestClient,
    *,
    command_id: str,
    body: dict[str, Any],
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "invoke_version": "1.0",
        "command_id": command_id,
        "actor": {"kind": "human", "id": body.get("requested_by", "operator")},
        "arguments": {"body": body},
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": body.get("requested_by", "operator")},
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def test_build_guardian_bridge_command_specs_returns_two_internal_specs() -> None:
    specs = bridge_command_bus.build_guardian_bridge_command_specs()

    assert len(specs) == 2
    assert [spec.command_id for spec in specs] == [
        bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        bridge_command_bus.INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID,
    ]
    for spec in specs:
        assert spec.layer == "internal"
        assert spec.method == "INTERNAL"
        assert spec.path_template == ""
        assert spec.risk == "read_only"
        assert spec.effect == "read"
        assert spec.idempotency == "safe"
        assert spec.approval_mode == "none"
        assert spec.aliases == []
        assert spec.operation_id is None
        body_schema = spec.input_schema["body"]
        assert set(body_schema["properties"]) == {
            "plan_pack_path",
            "validation_receipt_path",
            "requested_by",
            "correlation_id",
        }
        assert set(body_schema["required"]) == {
            "plan_pack_path",
            "requested_by",
            "correlation_id",
        }


def test_execute_guardian_bridge_command_maps_validate_command_body_to_request(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(request: bridge_contracts.GuardianBridgeRequest) -> bridge_contracts.GuardianBridgeResponse:
        captured["request"] = request
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="ok",
            correlation_id=request.correlation_id,
        )

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)

    result = bridge_command_bus.execute_guardian_bridge_command(
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        arguments=InvokeArguments(
            body={
                "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
                "validation_receipt_path": "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example.json",
                "requested_by": "guardian-ui",
                "correlation_id": "corr-123",
            }
        ),
    )

    request = captured["request"]
    assert request.operation == bridge_contracts.GuardianBridgeOperation.VALIDATE_PLAN_PACK
    assert str(request.plan_pack_path) == (
        "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack"
    )
    assert str(request.validation_receipt_path) == (
        "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example.json"
    )
    assert request.requested_by == "guardian-ui"
    assert request.correlation_id == "corr-123"
    assert request.response_mode == bridge_contracts.GuardianBridgeResponseMode.JSON
    assert request.write_receipt is False
    assert request.write_orchestration_log is False
    assert request.write_orchestration_receipt is False
    assert result["result"] == "pass"
    assert json.dumps(result)


def test_execute_guardian_bridge_command_maps_orchestrate_command_body_to_request(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(request: bridge_contracts.GuardianBridgeRequest) -> bridge_contracts.GuardianBridgeResponse:
        captured["request"] = request
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.FAIL,
            reason="missing preflight evidence",
            correlation_id=request.correlation_id,
        )

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)

    result = bridge_command_bus.execute_guardian_bridge_command(
        command_id=bridge_command_bus.INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID,
        arguments=InvokeArguments(
            body={
                "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
                "validation_receipt_path": "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example.json",
                "requested_by": "guardian-ui",
                "correlation_id": "corr-456",
            }
        ),
    )

    request = captured["request"]
    assert request.operation == bridge_contracts.GuardianBridgeOperation.ORCHESTRATE_DRY_RUN_PREFLIGHT
    assert str(request.plan_pack_path) == (
        "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack"
    )
    assert str(request.validation_receipt_path) == (
        "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example.json"
    )
    assert request.requested_by == "guardian-ui"
    assert request.correlation_id == "corr-456"
    assert request.response_mode == bridge_contracts.GuardianBridgeResponseMode.JSON
    assert request.write_receipt is False
    assert request.write_orchestration_log is False
    assert request.write_orchestration_receipt is False
    assert result["result"] == "fail"


def test_execute_guardian_bridge_command_requires_receipt_for_orchestrate(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        bridge_command_bus,
        "run_codex_runner_json",
        lambda request: _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="ok",
            correlation_id=request.correlation_id,
        ),
    )

    with pytest.raises(ValueError, match="validation_receipt_path is required"):
        bridge_command_bus.execute_guardian_bridge_command(
            command_id=bridge_command_bus.INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID,
            arguments=InvokeArguments(
                body={
                    "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
                    "requested_by": "guardian-ui",
                    "correlation_id": "corr-456",
                }
            ),
        )


def test_execute_guardian_bridge_command_rejects_unknown_command_id(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        bridge_command_bus,
        "run_codex_runner_json",
        lambda request: _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="ok",
            correlation_id=request.correlation_id,
        ),
    )

    with pytest.raises(ValueError, match="Unsupported bridge command"):
        bridge_command_bus.execute_guardian_bridge_command(
            command_id="internal::guardian.codex_runner.nope",
            arguments=InvokeArguments(body={}),
        )


def test_command_bus_invoke_completes_internal_validate_command_on_pass(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)
    bridge_calls: list[bridge_contracts.GuardianBridgeRequest] = []

    def fake_run(request: bridge_contracts.GuardianBridgeRequest) -> bridge_contracts.GuardianBridgeResponse:
        bridge_calls.append(request)
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="ok",
            correlation_id=request.correlation_id,
        )

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "guardian-ui",
            "correlation_id": "corr-777",
        },
    )

    assert payload["status"] == "completed"
    assert payload["inline_result"]["result"] == "pass"
    assert bridge_calls
    events = command_bus_routes._store.list_events_after(
        run_id=payload["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.started",
        "run.completed",
    ]


def test_command_bus_invoke_completes_internal_validate_command_on_fail(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    def fake_run(request: bridge_contracts.GuardianBridgeRequest) -> bridge_contracts.GuardianBridgeResponse:
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.FAIL,
            reason="validation failed",
            correlation_id=request.correlation_id,
        )

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "guardian-ui",
            "correlation_id": "corr-778",
        },
    )

    assert payload["status"] == "completed"
    assert payload["inline_result"]["result"] == "fail"
    assert payload["inline_result"]["reason"] == "validation failed"
    events = command_bus_routes._store.list_events_after(
        run_id=payload["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.started",
        "run.completed",
    ]


def test_command_bus_invoke_marks_internal_command_failed_on_adapter_exception(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    def fake_run(request: bridge_contracts.GuardianBridgeRequest) -> bridge_contracts.GuardianBridgeResponse:
        raise bridge_adapter.GuardianBridgeJsonError("adapter exploded")

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "guardian-ui",
            "correlation_id": "corr-779",
        },
    )

    assert payload["status"] == "failed"
    assert "adapter exploded" in payload["error"]
    events = command_bus_routes._store.list_events_after(
        run_id=payload["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.started",
        "run.failed",
    ]


def test_command_bus_invoke_skips_loopback_http_for_internal_bridge_commands(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    def fake_run(request: bridge_contracts.GuardianBridgeRequest) -> bridge_contracts.GuardianBridgeResponse:
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="ok",
            correlation_id=request.correlation_id,
        )

    called = {"loopback": 0}

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        called["loopback"] += 1
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "guardian-ui",
            "correlation_id": "corr-780",
        },
    )

    assert payload["status"] == "completed"
    assert called["loopback"] == 0


def test_command_bus_invoke_still_uses_loopback_http_for_raw_route_commands(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)
    captured: list[dict[str, Any]] = []

    async def fake_loopback(**kwargs: Any) -> dict[str, Any]:
        captured.append(dict(kwargs))
        return {"status_code": 200, "body": {"ok": True}}

    monkeypatch.setattr(invoke_module, "execute_loopback_request", fake_loopback)

    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": "operator"},
        json={
            "invoke_version": "1.0",
            "command_id": "op::health_check",
            "actor": {"kind": "human", "id": "operator"},
            "arguments": {"query": {"check": "true"}},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["inline_result"]["body"] == {"ok": True}
    assert len(captured) == 1
    assert captured[0]["method"] == "GET"
    assert captured[0]["path_template"] == "/health"


def test_command_bus_invoke_preserves_idempotency_for_internal_bridge_commands(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)
    bridge_calls: list[bridge_contracts.GuardianBridgeRequest] = []

    def fake_run(request: bridge_contracts.GuardianBridgeRequest) -> bridge_contracts.GuardianBridgeResponse:
        bridge_calls.append(request)
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="ok",
            correlation_id=request.correlation_id,
        )

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    body = {
        "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
        "requested_by": "guardian-ui",
        "correlation_id": "corr-781",
    }
    first = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body=body,
        idempotency_key="idem-bridge-1",
    )
    second = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body=body,
        idempotency_key="idem-bridge-1",
    )

    assert first["run_id"] == second["run_id"]
    assert len(bridge_calls) == 1
    events = command_bus_routes._store.list_events_after(
        run_id=first["run_id"],
        after_seq=0,
    )
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.started",
        "run.completed",
    ]


def test_bridge_command_bus_module_does_not_import_routes_frontend_or_runtime_modules():
    source = inspect.getsource(bridge_command_bus)
    tree = ast.parse(source)
    forbidden = (
        "guardian.routes",
        "frontend",
        "guardian.core.ai_router",
        "guardian.core.provider_registry",
        "guardian.workers",
        "guardian.pi",
        "guardian.memory_graph",
        "guardian.db.models",
        "guardian.agents",
    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not any(
                    alias.name == prefix or alias.name.startswith(prefix + ".")
                    for prefix in forbidden
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not any(
                module == prefix or module.startswith(prefix + ".")
                for prefix in forbidden
            )
