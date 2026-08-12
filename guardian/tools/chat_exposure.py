"""Narrow Stage 2I exposure policy for ordinary chat tool visibility.

This module decides only whether one existing Command Bus command may be
shown to a model for one ordinary completion.  It does not execute commands,
alter command authority, or derive a general manifest projection.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from guardian.command_bus.contracts import CommandSpec
from guardian.core.repository_search import (
    MAX_QUERY_CHARACTERS,
    MAX_RETURNED_MATCHES,
)
from guardian.providers.whooshd_tool_capability import (
    WhooshdToolCapabilityProjection,
)

HEALTH_COMMAND_ID = "op::health_health_get"
REPOSITORY_SEARCH_COMMAND_ID = "op::repository.search"
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
    *,
    expected_command_id: str,
) -> CommandSpec | dict[str, Any] | None:
    for command in commands:
        if isinstance(command, CommandSpec):
            candidate_command_id = command.command_id
        elif isinstance(command, dict):
            candidate_command_id = str(command.get("command_id") or "")
        else:
            continue
        if candidate_command_id == expected_command_id:
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


def _health_model_tool(command: CommandSpec | dict[str, Any]) -> dict[str, Any]:
    method = str(_command_value(command, "method") or "GET")
    path_template = str(_command_value(command, "path_template") or "/health")
    return {
        "command_id": str(_command_value(command, "command_id")),
        "description": (
            f"Read the current Guardian health status ({method} {path_template})."
        ),
        "input_schema": dict(_EMPTY_MODEL_INPUT_SCHEMA),
    }


def _has_exact_repository_search_input_schema(
    command: CommandSpec | dict[str, Any],
) -> bool:
    input_schema = _command_value(command, "input_schema")
    if not isinstance(input_schema, dict):
        return False
    path_params = input_schema.get("path_params")
    query = input_schema.get("query")
    if not isinstance(path_params, dict) or not isinstance(query, dict):
        return False
    path_properties = path_params.get("properties")
    query_properties = query.get("properties")
    if not isinstance(path_properties, dict) or not isinstance(query_properties, dict):
        return False
    q_schema = query_properties.get("q")
    limit_schema = query_properties.get("limit")
    return (
        path_params.get("required") == ["project_id"]
        and set(path_properties) == {"project_id"}
        and query.get("required") == ["q"]
        and set(query_properties) == {"q", "limit"}
        and isinstance(q_schema, dict)
        and q_schema.get("type") == "string"
        and q_schema.get("minLength") == 1
        and q_schema.get("maxLength") == MAX_QUERY_CHARACTERS
        and isinstance(limit_schema, dict)
        and limit_schema.get("type") == "integer"
        and limit_schema.get("minimum") == 1
        and limit_schema.get("maximum") == MAX_RETURNED_MATCHES
    )


def _is_safe_repository_search_command(
    command: CommandSpec | dict[str, Any],
) -> bool:
    """Allow only the fixed Stage 2K.4 raw command projection."""

    return (
        _command_value(command, "command_id") == REPOSITORY_SEARCH_COMMAND_ID
        and _command_value(command, "method") == "GET"
        and _command_value(command, "path_template")
        == "/api/projects/{project_id}/repository/search"
        and _command_value(command, "operation_id") == "repository.search"
        and _command_value(command, "effect") == "read"
        and _command_value(command, "risk") == "read_only"
        and _command_value(command, "idempotency") == "safe"
        and _command_value(command, "approval_mode") == "none"
        and _has_exact_repository_search_input_schema(command)
    )


def _repository_search_model_tool() -> dict[str, Any]:
    """Return the fixed model projection; authority fields never cross it."""

    return {
        "command_id": REPOSITORY_SEARCH_COMMAND_ID,
        "description": (
            "Search the current Project's authorized repository for literal text. "
            "Guardian selects the Project and repository."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_QUERY_CHARACTERS,
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_RETURNED_MATCHES,
                },
            },
            "required": ["q"],
            "additionalProperties": False,
        },
    }


def resolve_ordinary_chat_tools(
    *,
    provider: str | None,
    model: str | None,
    provider_vendor: str | None,
    manifest_commands: Iterable[CommandSpec | dict[str, Any]],
    whooshd_capability: WhooshdToolCapabilityProjection | None = None,
    repository_search_eligible: bool = False,
) -> list[dict[str, Any]] | None:
    """Return the fixed ordinary-chat subset or no automatic tools.

    The manifest supplies the canonical command identity and safety facts.  A
    matching Whoosh'd Stage 2G projection is eligibility evidence only; the
    returned list is still the exact subset Stage 1 checks later.
    """

    commands = list(manifest_commands)
    health_command = _find_command(
        commands,
        expected_command_id=HEALTH_COMMAND_ID,
    )
    if health_command is None or not _is_safe_health_command(health_command):
        return None

    normalized_provider = _normalized(provider)
    provider_eligible = normalized_provider == "deepseek"
    if not provider_eligible:
        provider_eligible = (
            normalized_provider == "local"
            and _normalized(provider_vendor) == _WHOOSHD_VENDOR
            and whooshd_capability is not None
            and whooshd_capability.outcome == "eligible"
            and whooshd_capability.invocation_model_id
            == str(model or "").strip()
        )
    if not provider_eligible:
        return None

    tools = [_health_model_tool(health_command)]
    if not repository_search_eligible:
        return tools

    repository_command = _find_command(
        commands,
        expected_command_id=REPOSITORY_SEARCH_COMMAND_ID,
    )
    if repository_command is not None and _is_safe_repository_search_command(
        repository_command
    ):
        tools.append(_repository_search_model_tool())
    return tools


def repository_search_is_advertised(tools: Any) -> bool:
    """Return whether the fixed search command is in an automatic subset."""

    return isinstance(tools, list) and any(
        isinstance(tool, dict)
        and tool.get("command_id") == REPOSITORY_SEARCH_COMMAND_ID
        for tool in tools
    )
