from __future__ import annotations

from pathlib import Path
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


async def _invoke(
    monkeypatch: pytest.MonkeyPatch,
    *,
    permission_profile: dict[str, Any] | None,
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

    payload = InvokeRequest(
        invoke_version="1.0",
        command_id=resolved_command.command_id,
        actor=ActorSpec(kind="human", id="operator"),
        arguments=InvokeArguments(),
        permission_profile=permission_profile,
    )
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


@pytest.mark.asyncio
async def test_no_profile_preserves_existing_invoke_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=None,
    )

    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_supplied_profile_allow_continues_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        allowed_command_ids=(command.command_id,),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_supplied_profile_denied_command_id_blocks_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        denied_command_ids=(command.command_id,),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:command_id_denied"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_supplied_profile_denied_command_class_blocks_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        denied_command_classes=("read",),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:command_class_denied"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_actor_mismatch_blocks_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(command.command_id, actor_id="different-actor")

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:actor_mismatch"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_subject_mismatch_blocks_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        subject_id="different-subject",
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:subject_mismatch"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_task_mismatch_blocks_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        task_id="task-a",
        request_task_id="task-b",
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:task_mismatch"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_project_scope_mismatch_blocks_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        project_id="project-a",
        request_project_id="project-b",
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:project_scope_mismatch"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_thread_scope_mismatch_blocks_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        thread_id="thread-a",
        request_thread_id="thread-b",
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:thread_scope_mismatch"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_denial_result_includes_decision_code_and_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        denied_command_ids=(command.command_id,),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["permission_profile"]["code"] == "command_id_denied"
    assert (
        result["permission_profile"]["reason"]
        == "command_id is denied by profile"
    )
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_denial_result_includes_decision_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        denied_command_ids=(command.command_id,),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["permission_profile"]["code"] == "command_id_denied"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_denial_result_includes_decision_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        denied_command_ids=(command.command_id,),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert (
        result["permission_profile"]["reason"]
        == "command_id is denied by profile"
    )
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_denial_result_marks_blocked_before_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        denied_command_ids=(command.command_id,),
    )

    result, calls, store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["permission_profile"]["blocked_before_dispatch"] is True
    assert len(calls) == 0

    events = store.list_events_after(run_id=result["run_id"], after_seq=0)
    assert [event["event_type"] for event in events] == [
        "run.created",
        "run.blocked",
    ]


@pytest.mark.asyncio
async def test_allowed_path_calls_underlying_execution_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        allowed_command_ids=(command.command_id,),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "completed"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_explicit_write_path_metadata_out_of_scope_blocks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    command = _command()
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    profile = _permission_profile(
        command.command_id,
        filesystem_access="write_scoped",
        allowed_write_roots=(str(allowed_root),),
        requested_write_paths=("../escape.txt",),
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:path_out_of_scope"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_explicit_shell_metadata_denial_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        uses_shell=True,
        shell_command="touch x",
        shell_allowed=False,
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:shell_denied"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_explicit_network_metadata_denial_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        uses_network=True,
        network_allowed=False,
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:network_denied"
    assert len(calls) == 0


@pytest.mark.asyncio
async def test_explicit_connector_metadata_denial_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command = _command()
    profile = _permission_profile(
        command.command_id,
        uses_connector=True,
        connector_allowed=False,
    )

    result, calls, _store = await _invoke(
        monkeypatch,
        permission_profile=profile,
        command=command,
    )

    assert result["status"] == "blocked"
    assert result["error"] == "permission_profile_denied:connector_denied"
    assert len(calls) == 0
