"""Private metadata projection; never mounts routes or modifies public OpenAPI."""

from fastapi.openapi.utils import get_openapi

from guardian.command_bus.manifest import _build_command_spec, _register_command
from guardian.connections.chat_pilot import COMMANDS, project_tools


def private_knowledge_commands():
    # Reuse provider-owned route metadata, without an app, request or execution.
    from guardian.connections.github.router import operations_router as github
    from guardian.connections.notion.router import operations_router as notion

    schema = get_openapi(
        title="Private accepted Knowledge metadata",
        version="1.0",
        routes=[*github.routes, *notion.routes],
    )
    commands = []
    for command_id, (provider, path, _, _) in COMMANDS.items():
        operation = schema.get("paths", {}).get(path, {}).get("get")
        operation_id = command_id.removeprefix("op::")
        if not operation or operation.get("operationId") != operation_id:
            raise ValueError("accepted_knowledge_manifest_unavailable")
        command = _build_command_spec(
            operation=operation,
            method="GET",
            path_template=path,
            operation_id_counts={operation_id: 1},
            components=schema.get("components", {}),
        )
        if not project_tools([command], frozenset({provider})):
            raise ValueError("accepted_knowledge_manifest_unavailable")
        commands.append(command)
    return commands


def with_private_knowledge_commands(index):
    """Only the verified private dispatch branch uses this detached index."""
    result = dict(index)
    for command in private_knowledge_commands():
        if command.command_id in result:
            # Existing entries remain subject to the exact private policy check.
            continue
        _register_command(result, command)
    return result
