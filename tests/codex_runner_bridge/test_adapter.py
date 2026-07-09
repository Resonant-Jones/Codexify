"""Pure adapter tests for guardian.codex_runner_bridge.adapter."""

from __future__ import annotations

import ast
import inspect
import subprocess

import pytest

from guardian.codex_runner_bridge import adapter as a
from guardian.codex_runner_bridge import contracts as c


def _validate_request(
    *,
    operation: str | c.GuardianBridgeOperation,
    plan_pack_path: str = "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
    validation_receipt_path: str | None = "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example.json",
    write_receipt: bool = False,
    write_orchestration_log: bool = False,
    write_orchestration_receipt: bool = False,
    response_mode: str | c.GuardianBridgeResponseMode = "json",
) -> c.GuardianBridgeRequest:
    return c.GuardianBridgeRequest(
        operation=operation,
        plan_pack_path=plan_pack_path,
        validation_receipt_path=validation_receipt_path,
        write_receipt=write_receipt,
        write_orchestration_log=write_orchestration_log,
        write_orchestration_receipt=write_orchestration_receipt,
        response_mode=response_mode,
        requested_by="guardian-ui",
        correlation_id="corr-123",
    )


def test_build_command_for_validate_plan_pack_returns_expected_argv():
    command = a.build_codex_runner_command(
        _validate_request(operation="guardian.validate_plan_pack")
    )
    assert command == [
        "codexrun",
        "guardian",
        "validate-plan-pack",
        "--path",
        "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
        "--json",
    ]


def test_build_command_for_orchestrate_returns_expected_argv():
    command = a.build_codex_runner_command(
        _validate_request(operation="guardian.orchestrate_dry_run_preflight")
    )
    assert command == [
        "codexrun",
        "guardian",
        "orchestrate-dry-run",
        "--plan-pack",
        "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
        "--require-receipt",
        "/Volumes/Dev_SSD/Codex-Runner/.guardian/receipts/example.json",
        "--json",
    ]


def test_command_builder_rejects_text_response_mode():
    with pytest.raises(a.GuardianBridgeUnsupportedOperationError):
        a.build_codex_runner_command(
            _validate_request(
                operation="guardian.validate_plan_pack",
                response_mode="text",
            )
        )


def test_command_builder_rejects_write_receipt():
    with pytest.raises(a.GuardianBridgeUnsupportedOperationError):
        a.build_codex_runner_command(
            _validate_request(
                operation="guardian.validate_plan_pack",
                write_receipt=True,
            )
        )


def test_command_builder_rejects_write_orchestration_log():
    with pytest.raises(a.GuardianBridgeUnsupportedOperationError):
        a.build_codex_runner_command(
            _validate_request(
                operation="guardian.validate_plan_pack",
                write_orchestration_log=True,
            )
        )


def test_command_builder_rejects_write_orchestration_receipt():
    with pytest.raises(a.GuardianBridgeUnsupportedOperationError):
        a.build_codex_runner_command(
            _validate_request(
                operation="guardian.validate_plan_pack",
                write_orchestration_receipt=True,
            )
        )


@pytest.mark.parametrize(
    "operation",
    [
        "guardian.write_validation_receipt",
        "guardian.write_orchestration_evidence",
        "guardian.list_evidence_for_plan_pack",
    ],
)
def test_command_builder_rejects_unsupported_operations(operation: str):
    with pytest.raises(a.GuardianBridgeUnsupportedOperationError):
        a.build_codex_runner_command(_validate_request(operation=operation))


def test_command_builder_requires_validation_receipt_for_orchestrate():
    with pytest.raises(a.GuardianBridgeCommandError):
        a.build_codex_runner_command(
            _validate_request(
                operation="guardian.orchestrate_dry_run_preflight",
                validation_receipt_path=None,
            )
        )


def test_run_codex_runner_json_calls_subprocess_run_with_safe_kwargs(monkeypatch):
    seen: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, '{"reason":"ok"}', "")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    response = a.run_codex_runner_json(
        _validate_request(operation="guardian.validate_plan_pack")
    )

    assert seen["argv"][0] == "codexrun"
    assert seen["cwd"] == c.CODEX_RUNNER_ROOT
    assert seen["capture_output"] is True
    assert seen["text"] is True
    assert seen["check"] is False
    assert seen["shell"] is False
    assert seen["timeout"] == a.DEFAULT_TIMEOUT_SECONDS
    assert response.result == c.GuardianBridgeResult.PASS


def test_run_codex_runner_json_returns_pass_response_on_valid_json(monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv,
            0,
            '{"reason":"all preconditions passed","result":"pass"}',
            "",
        )

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    response = a.run_codex_runner_json(
        _validate_request(operation="guardian.validate_plan_pack")
    )

    assert response.command_kind == "guardian.validate_plan_pack"
    assert response.result == c.GuardianBridgeResult.PASS
    assert response.reason == "all preconditions passed"
    assert response.json_payload == {
        "reason": "all preconditions passed",
        "result": "pass",
    }


def test_run_codex_runner_json_returns_fail_response_on_nonzero_returncode(monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(
            argv,
            1,
            '{"reason":"preconditions failed","result":"fail"}',
            "stderr text",
        )

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    response = a.run_codex_runner_json(
        _validate_request(operation="guardian.validate_plan_pack")
    )

    assert response.result == c.GuardianBridgeResult.FAIL
    assert response.reason == "preconditions failed"
    assert response.json_payload == {
        "reason": "preconditions failed",
        "result": "fail",
    }


def test_run_codex_runner_json_raises_on_success_with_invalid_json(monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, "not json", "")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    with pytest.raises(a.GuardianBridgeJsonError):
        a.run_codex_runner_json(
            _validate_request(operation="guardian.validate_plan_pack")
        )


def test_run_codex_runner_json_returns_fail_response_on_timeout(monkeypatch):
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, timeout=5, output="", stderr="")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    response = a.run_codex_runner_json(
        _validate_request(operation="guardian.validate_plan_pack"),
        timeout_seconds=5,
    )

    assert response.result == c.GuardianBridgeResult.FAIL
    assert "timed out" in response.reason.lower()


def test_returned_response_authority_locks_are_all_false(monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, '{"reason":"ok"}', "")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    response = a.run_codex_runner_json(
        _validate_request(operation="guardian.validate_plan_pack")
    )

    assert response.authority.guardian_operational is False
    assert response.authority.plan_execution_allowed is False
    assert response.authority.pi_loop_invocation_allowed is False
    assert response.authority.codexify_ingestion_allowed is False
    assert response.authority.durable_mutation_allowed is False
    assert response.authority.provider_execution_allowed is False
    assert response.authority.patch_application_allowed is False
    assert response.authority.dispatch_allowed is False
    assert response.authority.merge_allowed is False


def test_returned_response_boundary_label_matches_exact_label(monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, '{"reason":"ok"}', "")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    response = a.run_codex_runner_json(
        _validate_request(operation="guardian.validate_plan_pack")
    )
    assert response.boundary_label == c.BOUNDARY_LABEL


def test_returned_response_adapter_version_is_json_preflight_adapter(monkeypatch):
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, '{"reason":"ok"}', "")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    response = a.run_codex_runner_json(
        _validate_request(operation="guardian.validate_plan_pack")
    )
    assert response.adapter_version == "v0-json-preflight-adapter"


def test_adapter_module_does_not_import_routes_or_command_bus_or_workers_or_providers():
    source = inspect.getsource(a)
    tree = ast.parse(source)
    forbidden = (
        "guardian.routes",
        "guardian.command_bus",
        "guardian.workers",
        "guardian.core.ai_router",
        "guardian.core.provider_registry",
        "guardian.core.chat_completion_service",
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


def test_adapter_module_does_not_invoke_shell_true():
    source = inspect.getsource(a)
    assert "shell=True" not in source


def test_adapter_tests_do_not_execute_real_codexrun(monkeypatch):
    called: list[list[str]] = []

    def fake_run(argv, **kwargs):
        called.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"reason":"ok"}', "")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    a.run_codex_runner_json(_validate_request(operation="guardian.validate_plan_pack"))
    assert called == [[
        "codexrun",
        "guardian",
        "validate-plan-pack",
        "--path",
        "/Volumes/Dev_SSD/Codex-Runner/docs/guardian/examples/sample-dry-run-plan-pack",
        "--json",
    ]]


# ---------------------------------------------------------------------------
# Invocation mode tests
# ---------------------------------------------------------------------------


def test_resolve_codexrun_command_prefix_default_binary():
    prefix = a.resolve_codexrun_command_prefix(env={})
    assert prefix == ["codexrun"]


def test_resolve_codexrun_command_prefix_explicit_binary_default_binary():
    prefix = a.resolve_codexrun_command_prefix(env={"CODEXRUN_INVOCATION_MODE": "binary"})
    assert prefix == ["codexrun"]


def test_resolve_codexrun_command_prefix_binary_custom():
    prefix = a.resolve_codexrun_command_prefix(env={
        "CODEXRUN_INVOCATION_MODE": "binary",
        "CODEXRUN_BINARY": "/custom/codexrun",
    })
    assert prefix == ["/custom/codexrun"]


def test_resolve_codexrun_command_prefix_binary_rejects_whitespace():
    with pytest.raises(a.GuardianBridgeInvocationConfigError):
        a.resolve_codexrun_command_prefix(env={
            "CODEXRUN_INVOCATION_MODE": "binary",
            "CODEXRUN_BINARY": "codexrun --flag",
        })


def test_resolve_codexrun_command_prefix_module_default():
    prefix = a.resolve_codexrun_command_prefix(env={"CODEXRUN_INVOCATION_MODE": "module"})
    assert prefix == ["python", "-m", "codex_runner"]


def test_resolve_codexrun_command_prefix_module_custom_python():
    prefix = a.resolve_codexrun_command_prefix(env={
        "CODEXRUN_INVOCATION_MODE": "module",
        "CODEXRUN_PYTHON_BINARY": "/usr/bin/python3",
    })
    assert prefix == ["/usr/bin/python3", "-m", "codex_runner"]


def test_resolve_codexrun_command_prefix_module_custom_module():
    prefix = a.resolve_codexrun_command_prefix(env={
        "CODEXRUN_INVOCATION_MODE": "module",
        "CODEXRUN_MODULE": "codex_runner",
    })
    assert prefix == ["python", "-m", "codex_runner"]


def test_resolve_codexrun_command_prefix_module_rejects_whitespace_python():
    with pytest.raises(a.GuardianBridgeInvocationConfigError):
        a.resolve_codexrun_command_prefix(env={
            "CODEXRUN_INVOCATION_MODE": "module",
            "CODEXRUN_PYTHON_BINARY": "python -u",
        })


def test_resolve_codexrun_command_prefix_module_rejects_whitespace_module():
    with pytest.raises(a.GuardianBridgeInvocationConfigError):
        a.resolve_codexrun_command_prefix(env={
            "CODEXRUN_INVOCATION_MODE": "module",
            "CODEXRUN_MODULE": "codex runner",
        })


def test_resolve_codexrun_command_prefix_unsupported_mode():
    with pytest.raises(a.GuardianBridgeInvocationModeError):
        a.resolve_codexrun_command_prefix(env={"CODEXRUN_INVOCATION_MODE": "unknown"})


# --- Invocation mode integration with build_codex_runner_command ---


def _mock_env(monkeypatch, **kwargs):
    monkeypatch.setattr(a, "resolve_codexrun_command_prefix", lambda env=None: list(kwargs.get("prefix", ["codexrun"])))


def test_build_command_uses_binary_prefix_by_default(monkeypatch):
    _mock_env(monkeypatch, prefix=["codexrun"])
    command = a.build_codex_runner_command(
        _validate_request(operation="guardian.validate_plan_pack")
    )
    assert command[0] == "codexrun"


def test_build_command_uses_module_prefix_when_module_mode(monkeypatch):
    _mock_env(monkeypatch, prefix=["python", "-m", "codex_runner"])
    command = a.build_codex_runner_command(
        _validate_request(operation="guardian.validate_plan_pack")
    )
    assert command[:3] == ["python", "-m", "codex_runner"]
    assert command[3] == "guardian"


def test_build_command_in_module_mode_still_json_only(monkeypatch):
    _mock_env(monkeypatch, prefix=["python", "-m", "codex_runner"])
    command = a.build_codex_runner_command(
        _validate_request(operation="guardian.validate_plan_pack")
    )
    assert "--json" in command


def test_build_command_module_mode_still_rejects_write_flags(monkeypatch):
    _mock_env(monkeypatch, prefix=["python", "-m", "codex_runner"])
    with pytest.raises(a.GuardianBridgeUnsupportedOperationError):
        a.build_codex_runner_command(
            _validate_request(
                operation="guardian.validate_plan_pack",
                write_receipt=True,
            )
        )


def test_build_command_module_mode_orchestrate_still_requires_receipt(monkeypatch):
    _mock_env(monkeypatch, prefix=["python", "-m", "codex_runner"])
    with pytest.raises(a.GuardianBridgeCommandError):
        a.build_codex_runner_command(
            _validate_request(
                operation="guardian.orchestrate_dry_run_preflight",
                validation_receipt_path=None,
            )
        )


def test_subprocess_never_uses_shell_true(monkeypatch):
    seen: dict[str, object] = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        seen.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, '{"reason":"ok"}', "")

    monkeypatch.setattr(a.subprocess, "run", fake_run)
    a.run_codex_runner_json(_validate_request(operation="guardian.validate_plan_pack"))
    assert seen["shell"] is False
