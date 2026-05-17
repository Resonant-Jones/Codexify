from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from guardian.command_bus import invoke as invoke_module
from guardian.command_bus.contracts import (
    ActorSpec,
    CommandSpec,
    InvokeArguments,
    InvokeRequest,
)
from guardian.command_bus.store import CommandBusStore


def _command(
    *,
    command_id: str = "cmd.read.health",
    method: str = "GET",
    path_template: str = "/health",
    effect: str = "read",
) -> CommandSpec:
    risk = "read_only" if effect == "read" else "mutating"
    return CommandSpec(
        command_id=command_id,
        method=method,
        path_template=path_template,
        risk=risk,
        effect=effect,
        idempotency="safe",
        approval_mode="none",
    )


def _permission_profile(
    command_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "profile_id": "profile-1",
        "actor_id": "operator",
        "subject_id": "operator",
        "task_id": "task-1",
        "project_id": None,
        "thread_id": None,
        "allowed_command_classes": (),
        "denied_command_classes": (),
        "allowed_command_ids": (command_id,),
        "denied_command_ids": (),
        "filesystem_access": "none",
        "allowed_write_roots": (),
        "shell_allowed": False,
        "shell_read_only": True,
        "allowed_shell_commands": (),
        "network_allowed": False,
        "connector_allowed": False,
        "request_task_id": "task-1",
        "request_project_id": None,
        "request_thread_id": None,
        "request_command_class": None,
        "requested_write_paths": (),
        "uses_shell": False,
        "shell_command": None,
        "shell_mutates": False,
        "uses_network": False,
        "uses_connector": False,
    }
    payload.update(overrides)
    return payload


def _allow_rule(**overrides: Any) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "effect": "allow",
        "connector_name": "github",
        "transport": "https",
        "reason": "allow rule",
    }
    rule.update(overrides)
    return rule


def _deny_rule(**overrides: Any) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "effect": "deny",
        "connector_name": "github",
        "transport": "https",
        "reason": "deny rule",
    }
    rule.update(overrides)
    return rule


async def _invoke(
    monkeypatch: pytest.MonkeyPatch,
    *,
    external_payload: dict[str, Any] | None = None,
    permission_profile: dict[str, Any] | None = None,
    command: CommandSpec | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], CommandBusStore]:
    resolved_command = command or _command()
    manifest = SimpleNamespace(manifest_version="1.0")
    monkeypatch.setattr(
        invoke_module,
        "build_command_index",
        lambda _app: ({resolved_command.command_id: resolved_command}, manifest),
    )

    calls: list[dict[str, Any]] = []

    async def _fake_execute_loopback_request(**kwargs: Any) -> dict[str, Any]:
        calls.append(dict(kwargs))
        return {"status_code": 200, "body": {"ok": True}}

    monkeypatch.setattr(
        invoke_module,
        "execute_loopback_request",
        _fake_execute_loopback_request,
    )
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )

    payload_data: dict[str, Any] = {
        "invoke_version": "1.0",
        "command_id": resolved_command.command_id,
        "actor": ActorSpec(kind="human", id="operator"),
        "arguments": InvokeArguments(),
        "permission_profile": permission_profile,
    }
    if external_payload:
        payload_data.update(external_payload)
    payload = InvokeRequest(**payload_data)

    store = CommandBusStore()
    result = await invoke_module.execute_invoke(
        payload=payload,
        auth_subject="operator",
        inbound_headers={"x-api-key": "test-key", "x-user-id": "operator"},
        store=store,
        app=object(),
        execution_lane="tools",
        allow_write_execution=True,
        confirmation_granted=False,
    )
    return result, calls, store


def _base_external_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "external_transport": "https",
        "external_connector_name": "github",
        "external_policy_rules": (_allow_rule(),),
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_no_external_metadata_preserves_existing_invoke_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(monkeypatch)
    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_matching_allow_policy_permits_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(),
    )
    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_empty_rules_denies_before_dispatch_with_no_allow_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(external_policy_rules=()),
    )
    assert result["status"] == "blocked"
    assert result["error"] == "external_transport_policy_denied:no_allow_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_missing_rules_when_triggered_denies_with_no_allow_rule(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload={
            "external_transport": "https",
            "external_connector_name": "github",
        },
    )
    assert result["status"] == "blocked"
    assert result["error"] == "external_transport_policy_denied:no_allow_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_deny_rule_overrides_allow_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_policy_rules=(
                _allow_rule(reason="allow-first"),
                _deny_rule(reason="explicit-deny"),
            )
        ),
    )
    assert result["status"] == "blocked"
    assert result["error"] == "external_transport_policy_denied:denied_by_rule"
    assert result["external_transport_policy"]["reason"] == "explicit-deny"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_unknown_transport_denies_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_transport="ftp",
            external_policy_rules=(_allow_rule(transport="ftp"),),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "unsupported_transport"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_malformed_target_url_denies_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_target_url="http://[::1",
            external_policy_rules=(
                _allow_rule(url_host_pattern="api.example.com"),
            ),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "malformed_url"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_connector_name_mismatch_denies_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_policy_rules=(
                _allow_rule(connector_name="not-github"),
            ),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "no_allow_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_exact_url_host_match_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_target_url="https://api.example.com/v1/repos",
            external_policy_rules=(
                _allow_rule(
                    url_host_pattern="api.example.com",
                    url_scheme="https",
                ),
            ),
        ),
    )
    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_wildcard_host_match_allows_valid_subdomain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_target_url="https://api.example.com/resource",
            external_policy_rules=(_allow_rule(url_host_pattern="*.example.com"),),
        ),
    )
    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_wildcard_host_rejects_boundary_unsafe_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_target_url="https://badexample.com/resource",
            external_policy_rules=(_allow_rule(url_host_pattern="*.example.com"),),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "no_allow_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_command_tuple_mismatch_denies_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_command_namespace="repos",
            external_command_name="write",
            external_policy_rules=(
                _allow_rule(
                    command_namespace="repos",
                    command_name="read",
                ),
            ),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "no_allow_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_project_scope_mismatch_denies_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_project_id="project-b",
            external_policy_rules=(_allow_rule(project_id="project-a"),),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "no_allow_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_thread_scope_mismatch_denies_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_thread_id="thread-b",
            external_policy_rules=(_allow_rule(thread_id="thread-a"),),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "no_allow_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_denial_result_includes_evaluator_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_policy_rules=(_deny_rule(reason="blocked"),),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["code"] == "denied_by_rule"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_denial_result_includes_evaluator_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_policy_rules=(_deny_rule(reason="blocked-for-reason"),),
        ),
    )
    assert result["status"] == "blocked"
    assert (
        result["external_transport_policy"]["reason"] == "blocked-for-reason"
    )
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_denial_result_includes_blocked_before_dispatch_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_policy_rules=(_deny_rule(reason="blocked-marker"),),
        ),
    )
    assert result["status"] == "blocked"
    assert result["external_transport_policy"]["blocked_before_dispatch"] is True
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_blocked_path_does_not_call_underlying_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_policy_rules=(_deny_rule(reason="stop"),),
        ),
    )
    assert result["status"] == "blocked"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_allowed_path_calls_underlying_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(),
    )
    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_permission_and_external_allow_both_continue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(),
        permission_profile=_permission_profile(command.command_id),
        command=command,
    )
    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_permission_denies_while_external_allows_blocks_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(),
        permission_profile=_permission_profile(
            command.command_id,
            denied_command_ids=(command.command_id,),
        ),
        command=command,
    )
    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:command_id_denied"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_permission_allows_while_external_denies_blocks_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    result, calls, _store = await _invoke(
        monkeypatch,
        external_payload=_base_external_payload(
            external_policy_rules=(_deny_rule(reason="external-stop"),),
        ),
        permission_profile=_permission_profile(command.command_id),
        command=command,
    )
    assert result["status"] == "blocked"
    assert result["error"] == "external_transport_policy_denied:denied_by_rule"
    assert result["external_transport_policy"]["reason"] == "external-stop"
    assert len(calls) == 0
