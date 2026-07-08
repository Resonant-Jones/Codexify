"""Pure contract tests for guardian.codex_runner_bridge.contracts."""

from __future__ import annotations

import ast
import inspect

import pytest

from guardian.codex_runner_bridge import contracts as c


def test_allowed_operations_contain_exactly_five_contract_operations():
    assert c.ALLOWED_GUARDIAN_BRIDGE_OPERATIONS == (
        c.GuardianBridgeOperation.VALIDATE_PLAN_PACK,
        c.GuardianBridgeOperation.WRITE_VALIDATION_RECEIPT,
        c.GuardianBridgeOperation.ORCHESTRATE_DRY_RUN_PREFLIGHT,
        c.GuardianBridgeOperation.WRITE_ORCHESTRATION_EVIDENCE,
        c.GuardianBridgeOperation.LIST_EVIDENCE_FOR_PLAN_PACK,
    )


def test_boundary_label_equals_exact_four_line_label():
    assert c.BOUNDARY_LABEL == (
        "PREFLIGHT ONLY\n"
        "NO PI LOOP INVOCATION\n"
        "NO SOURCE MUTATION\n"
        "NO CODEXIFY INGESTION"
    )


def test_default_authority_returns_all_false():
    authority = c.default_authority()
    assert authority.guardian_operational is False
    assert authority.plan_execution_allowed is False
    assert authority.pi_loop_invocation_allowed is False
    assert authority.codexify_ingestion_allowed is False
    assert authority.durable_mutation_allowed is False
    assert authority.provider_execution_allowed is False
    assert authority.patch_application_allowed is False
    assert authority.dispatch_allowed is False
    assert authority.merge_allowed is False


def test_response_adapter_version_defaults_to_contract_only():
    response = c.GuardianBridgeResponse(
        command_kind="validate_plan_pack",
        result=c.GuardianBridgeResult.PASS,
        reason="ok",
        correlation_id="corr-1",
    )
    assert response.adapter_version == "v0-contract-only"


@pytest.mark.parametrize(
    "operation",
    [
        c.GuardianBridgeOperation.VALIDATE_PLAN_PACK,
        c.GuardianBridgeOperation.WRITE_VALIDATION_RECEIPT,
        c.GuardianBridgeOperation.ORCHESTRATE_DRY_RUN_PREFLIGHT,
        c.GuardianBridgeOperation.WRITE_ORCHESTRATION_EVIDENCE,
        c.GuardianBridgeOperation.LIST_EVIDENCE_FOR_PLAN_PACK,
        "guardian.validate_plan_pack",
        "guardian.write_validation_receipt",
        "guardian.orchestrate_dry_run_preflight",
        "guardian.write_orchestration_evidence",
        "guardian.list_evidence_for_plan_pack",
    ],
)
def test_validate_operation_accepts_each_known_operation(operation):
    assert c.validate_operation(operation) in c.ALLOWED_GUARDIAN_BRIDGE_OPERATIONS


def test_validate_operation_rejects_unknown_operation():
    with pytest.raises(ValueError):
        c.validate_operation("guardian.run_everything")


@pytest.mark.parametrize(
    "operation",
    [
        "",
        "codexrun guardian validate-plan-pack",
        "guardian.validate_plan_pack --json",
        "guardian.validate_plan_pack; rm -rf /",
        "guardian.validate_plan_pack | cat",
    ],
)
def test_validate_operation_rejects_shell_like_arbitrary_strings(operation):
    with pytest.raises(ValueError):
        c.validate_operation(operation)


def test_validate_codex_runner_path_accepts_path_inside_runner_root():
    path = c.validate_codex_runner_path("/Volumes/Dev_SSD/Codex-Runner/docs/guardian")
    assert str(path).startswith(str(c.CODEX_RUNNER_ROOT))


def test_validate_codex_runner_path_rejects_codexify_root():
    with pytest.raises(c.GuardianBridgePathError):
        c.validate_codex_runner_path("/Volumes/Dev_SSD/Codexify-main")


def test_validate_codex_runner_path_rejects_archived_core_root():
    with pytest.raises(c.GuardianBridgePathError):
        c.validate_codex_runner_path("/Volumes/Dev_SSD/ResonantConstructs/Codexify-Core")


def test_validate_codex_runner_path_rejects_outside_paths():
    with pytest.raises(c.GuardianBridgePathError):
        c.validate_codex_runner_path("/tmp/not-codex-runner")


def test_validate_validation_receipt_path_returns_none_for_none():
    assert c.validate_validation_receipt_path(None) is None


def test_validate_bridge_request_returns_normalized_request_for_valid_request():
    request = c.GuardianBridgeRequest(
        operation="guardian.validate_plan_pack",
        plan_pack_path="/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
        validation_receipt_path="/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example.json",
        write_receipt=True,
        write_orchestration_log=False,
        write_orchestration_receipt=False,
        response_mode="json",
        requested_by="guardian-ui",
        correlation_id="corr-123",
    )

    validated = c.validate_bridge_request(request)

    assert validated.operation == c.GuardianBridgeOperation.VALIDATE_PLAN_PACK
    assert isinstance(validated.plan_pack_path, c.Path)
    assert isinstance(validated.validation_receipt_path, c.Path)
    assert validated.write_receipt is True
    assert validated.response_mode == c.GuardianBridgeResponseMode.JSON
    assert validated.requested_by == "guardian-ui"
    assert validated.correlation_id == "corr-123"


def test_validate_bridge_request_rejects_invalid_operation():
    request = c.GuardianBridgeRequest(
        operation="guardian.nope",
        plan_pack_path="/Volumes/Dev_SSD/Codex-Runner/docs/guardian",
        response_mode="json",
        requested_by="guardian-ui",
        correlation_id="corr-123",
    )

    with pytest.raises(ValueError):
        c.validate_bridge_request(request)


def test_validate_bridge_request_rejects_invalid_plan_pack_path():
    request = c.GuardianBridgeRequest(
        operation="guardian.validate_plan_pack",
        plan_pack_path="/tmp/not-allowed",
        response_mode="json",
        requested_by="guardian-ui",
        correlation_id="corr-123",
    )

    with pytest.raises(c.GuardianBridgePathError):
        c.validate_bridge_request(request)


def test_module_does_not_import_subprocess():
    source = inspect.getsource(c)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name != "subprocess" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "subprocess"


def test_module_does_not_import_command_bus():
    source = inspect.getsource(c)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("guardian.command_bus")
        elif isinstance(node, ast.ImportFrom):
            assert not ((node.module or "").startswith("guardian.command_bus"))


def test_module_does_not_import_route_modules():
    source = inspect.getsource(c)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("guardian.routes")
        elif isinstance(node, ast.ImportFrom):
            assert not ((node.module or "").startswith("guardian.routes"))


def test_module_does_not_invoke_codexrun():
    source = inspect.getsource(c)
    assert "codexrun" not in source
