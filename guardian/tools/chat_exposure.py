"""Narrow Stage 2I exposure policy for ordinary chat tool visibility.

This module decides only whether one existing Command Bus command may be
shown to a model for one ordinary completion.  It does not execute commands,
alter command authority, or derive a general manifest projection.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from guardian.command_bus.contracts import CommandSpec
from guardian.providers.whooshd_tool_capability import (
    WhooshdToolCapabilityProjection,
)

HEALTH_COMMAND_ID = "op::health_health_get"
_WHOOSHD_VENDOR = "whooshd"
_EMPTY_MODEL_INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "maxProperties": 0,
}


def _normalized(value: str | None) -> str:
    return str(value or "").strip().lower()


def _find_command(
    commands: Iterable[CommandSpec | dict[str, Any]],
) -> CommandSpec | dict[str, Any] | None:
    for command in commands:
        if isinstance(command, CommandSpec):
            command_id = command.command_id
        elif isinstance(command, dict):
            command_id = str(command.get("command_id") or "")
        else:
            continue
        if command_id == HEALTH_COMMAND_ID:
            return command
    return None


def _command_value(command: CommandSpec | dict[str, Any], field: str) -> Any:
    if isinstance(command, CommandSpec):
        return getattr(command, field)
    return command.get(field)


def _requires_no_model_arguments(command: CommandSpec | dict[str, Any]) -> bool:
    input_schema = _command_value(command, "input_schema")
    if not isinstance(input_schema, dict):
        return False
    for bucket in ("path_params", "query", "headers"):
        schema = input_schema.get(bucket)
        if not isinstance(schema, dict):
            return False
        if schema.get("required") not in (None, []):
            return False
        if schema.get("properties") not in (None, {}):
            return False
    body = input_schema.get("body")
    return body in (None, {})


def _is_safe_health_command(command: CommandSpec | dict[str, Any]) -> bool:
    """Defend the fixed allowlist with current-manifest safety facts."""

    return (
        _command_value(command, "command_id") == HEALTH_COMMAND_ID
        and _command_value(command, "method") == "GET"
        and _command_value(command, "path_template") == "/health"
        and _command_value(command, "effect") == "read"
        and _command_value(command, "risk") == "read_only"
        and _command_value(command, "idempotency") == "safe"
        and _command_value(command, "approval_mode") == "none"
        and _requires_no_model_arguments(command)
    )


def _model_tool(command: CommandSpec | dict[str, Any]) -> dict[str, Any]:
    method = str(_command_value(command, "method") or "GET")
    path_template = str(_command_value(command, "path_template") or "/health")
    return {
        "command_id": str(_command_value(command, "command_id")),
        "description": (
            f"Read the current Guardian health status ({method} {path_template})."
        ),
        "input_schema": dict(_EMPTY_MODEL_INPUT_SCHEMA),
    }


def resolve_ordinary_chat_tools(
    *,
    provider: str | None,
    model: str | None,
    provider_vendor: str | None,
    manifest_commands: Iterable[CommandSpec | dict[str, Any]],
    whooshd_capability: WhooshdToolCapabilityProjection | None = None,
) -> list[dict[str, Any]] | None:
    """Return the one Stage 2I tool or no automatic ordinary-chat tools.

    The manifest supplies the canonical command identity and safety facts.  A
    matching Whoosh'd Stage 2G projection is eligibility evidence only; the
    returned list is still the exact subset Stage 1 checks later.
    """

    command = _find_command(manifest_commands)
    if command is None or not _is_safe_health_command(command):
        return None

    normalized_provider = _normalized(provider)
    if normalized_provider == "deepseek":
        return [_model_tool(command)]

    if (
        normalized_provider == "local"
        and _normalized(provider_vendor) == _WHOOSHD_VENDOR
        and whooshd_capability is not None
        and whooshd_capability.outcome == "eligible"
        and whooshd_capability.invocation_model_id == str(model or "").strip()
    ):
        return [_model_tool(command)]

    return None
