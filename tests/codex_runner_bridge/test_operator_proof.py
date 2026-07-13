from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from guardian.command_bus import invoke as invoke_module
from guardian.codex_runner_bridge import adapter as bridge_adapter
from guardian.codex_runner_bridge import command_bus as bridge_command_bus
from guardian.codex_runner_bridge import contracts as bridge_contracts
from guardian.routes import command_bus as command_bus_routes

PROOF_DOC = Path(
    "docs/architecture/guardian-codex-runner-command-bus-proof.md"
)
PROOF_TEXT = PROOF_DOC.read_text(encoding="utf-8")


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
    actor_id: str = "operator",
    body: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        "/api/guardian/commands/invoke",
        headers={"X-API-Key": "test-key", "X-User-Id": actor_id},
        json={
            "invoke_version": "1.0",
            "command_id": command_id,
            "actor": {"kind": "human", "id": actor_id},
            "arguments": {"body": body},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_proof_document_exists() -> None:
    assert PROOF_DOC.exists()


def test_proof_document_names_both_internal_command_ids() -> None:
    assert bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID in PROOF_TEXT
    assert (
        bridge_command_bus.INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID
        in PROOF_TEXT
    )


def test_proof_document_includes_exact_boundary_label() -> None:
    assert bridge_contracts.BOUNDARY_LABEL in PROOF_TEXT


def test_proof_document_states_controlled_proof_is_not_live_codex_runner_proof() -> None:
    assert "This is a controlled operator proof, not live Codex Runner proof." in PROOF_TEXT


def test_proof_document_states_automated_tests_must_not_execute_real_codexrun() -> None:
    assert "Automated tests must not execute real `codexrun`." in PROOF_TEXT


def test_proof_document_states_no_ui_is_created() -> None:
    assert "- a frontend panel" in PROOF_TEXT
    assert "- a UI trigger" in PROOF_TEXT


def test_proof_document_states_no_new_api_route_is_created() -> None:
    assert "- a new API route" in PROOF_TEXT


def test_proof_document_states_no_write_flags_are_enabled() -> None:
    assert "- write flags" in PROOF_TEXT


def test_proof_document_states_no_pi_loop_invocation_occurs() -> None:
    assert "- Pi Loop invocation" in PROOF_TEXT


def test_proof_document_states_no_source_mutation_occurs() -> None:
    assert "- source mutation" in PROOF_TEXT


def test_proof_document_states_no_codexify_ingestion_occurs() -> None:
    assert "- Codexify ingestion" in PROOF_TEXT


def test_proof_document_includes_validate_example_payload() -> None:
    assert '"command_id": "internal::guardian.codex_runner.validate_plan_pack"' in PROOF_TEXT
    assert '"correlation_id": "guardian-bridge-proof-validate"' in PROOF_TEXT


def test_proof_document_includes_orchestrate_example_payload() -> None:
    assert (
        '"command_id": "internal::guardian.codex_runner.orchestrate_dry_run_preflight"'
        in PROOF_TEXT
    )
    assert (
        '"validation_receipt_path": "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example-validation-receipt.json"'
        in PROOF_TEXT
    )


def test_proof_document_includes_all_required_authority_locks_false() -> None:
    required_lines = (
        "guardian_operational: false",
        "plan_execution_allowed: false",
        "pi_loop_invocation_allowed: false",
        "codexify_ingestion_allowed: false",
        "durable_mutation_allowed: false",
        "provider_execution_allowed: false",
        "patch_application_allowed: false",
        "dispatch_allowed: false",
        "merge_allowed: false",
    )
    for line in required_lines:
        assert line in PROOF_TEXT


def test_controlled_invoke_proof_validate_returns_completed_inline_result_on_pass(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    def fake_run(
        request: bridge_contracts.GuardianBridgeRequest,
    ) -> bridge_contracts.GuardianBridgeResponse:
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="controlled validate pass",
            correlation_id=request.correlation_id,
        )

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    def unexpected_subprocess(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("real codexrun must not execute in controlled proof tests")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)
    monkeypatch.setattr(bridge_adapter.subprocess, "run", unexpected_subprocess)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "operator-proof",
            "correlation_id": "guardian-bridge-proof-validate",
        },
    )

    assert payload["status"] == "completed"
    assert payload["inline_result"]["result"] == "pass"
    assert payload["inline_result"]["reason"] == "controlled validate pass"


def test_controlled_invoke_proof_orchestrate_returns_completed_inline_result_on_pass(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    def fake_run(
        request: bridge_contracts.GuardianBridgeRequest,
    ) -> bridge_contracts.GuardianBridgeResponse:
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="controlled orchestrate pass",
            correlation_id=request.correlation_id,
        )

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_ORCHESTRATE_DRY_RUN_PREFLIGHT_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "validation_receipt_path": "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example-validation-receipt.json",
            "requested_by": "operator-proof",
            "correlation_id": "guardian-bridge-proof-orchestrate",
        },
    )

    assert payload["status"] == "completed"
    assert payload["inline_result"]["result"] == "pass"
    assert payload["inline_result"]["reason"] == "controlled orchestrate pass"


def test_controlled_invoke_proof_validate_returns_completed_fail_inline_result(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    def fake_run(
        request: bridge_contracts.GuardianBridgeRequest,
    ) -> bridge_contracts.GuardianBridgeResponse:
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.FAIL,
            reason="controlled validate fail",
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
            "requested_by": "operator-proof",
            "correlation_id": "guardian-bridge-proof-validate-fail",
        },
    )

    assert payload["status"] == "completed"
    assert payload["inline_result"]["result"] == "fail"
    assert payload["inline_result"]["reason"] == "controlled validate fail"


def test_controlled_invoke_proof_adapter_exception_returns_failed_run(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)

    def fake_run(
        request: bridge_contracts.GuardianBridgeRequest,
    ) -> bridge_contracts.GuardianBridgeResponse:
        raise bridge_adapter.GuardianBridgeJsonError("controlled adapter exception")

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "operator-proof",
            "correlation_id": "guardian-bridge-proof-exception",
        },
    )

    assert payload["status"] == "failed"
    assert "controlled adapter exception" in payload["error"]


def test_controlled_proof_never_calls_real_codexrun(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    subprocess_calls = {"count": 0}

    def fake_run(
        request: bridge_contracts.GuardianBridgeRequest,
    ) -> bridge_contracts.GuardianBridgeResponse:
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="controlled validate pass",
            correlation_id=request.correlation_id,
        )

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    def counting_subprocess(*args: Any, **kwargs: Any) -> Any:
        subprocess_calls["count"] += 1
        raise AssertionError("real codexrun must not execute in controlled proof tests")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)
    monkeypatch.setattr(bridge_adapter.subprocess, "run", counting_subprocess)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "operator-proof",
            "correlation_id": "guardian-bridge-proof-no-codexrun",
        },
    )

    assert payload["status"] == "completed"
    assert subprocess_calls["count"] == 0


def test_controlled_proof_does_not_call_loopback_http_for_internal_bridge_commands(
    monkeypatch,
) -> None:
    client = _build_client(monkeypatch)
    loopback_calls = {"count": 0}

    def fake_run(
        request: bridge_contracts.GuardianBridgeRequest,
    ) -> bridge_contracts.GuardianBridgeResponse:
        return _bridge_response(
            command_kind=request.operation.value,
            result=bridge_contracts.GuardianBridgeResult.PASS,
            reason="controlled validate pass",
            correlation_id=request.correlation_id,
        )

    async def unexpected_loopback(*args: Any, **kwargs: Any) -> dict[str, Any]:
        loopback_calls["count"] += 1
        raise AssertionError("loopback HTTP should not run for internal bridge commands")

    monkeypatch.setattr(bridge_command_bus, "run_codex_runner_json", fake_run)
    monkeypatch.setattr(invoke_module, "execute_loopback_request", unexpected_loopback)

    payload = _invoke_bridge_command(
        client,
        command_id=bridge_command_bus.INTERNAL_VALIDATE_PLAN_PACK_COMMAND_ID,
        body={
            "plan_pack_path": "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
            "requested_by": "operator-proof",
            "correlation_id": "guardian-bridge-proof-no-loopback",
        },
    )

    assert payload["status"] == "completed"
    assert loopback_calls["count"] == 0


def test_raw_route_command_behavior_is_not_modified_by_proof_test(
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
