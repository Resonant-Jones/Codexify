"""OpenAPI-backed raw command manifest generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI

from guardian.command_bus.contracts import (
    CapabilitiesSpec,
    CommandSpec,
    ManifestResponse,
)

_HTTP_METHODS = {"get", "head", "post", "put", "patch", "delete", "options"}


def build_manifest(app: FastAPI) -> ManifestResponse:
    schema = app.openapi()
    components = schema.get("components", {})
    paths = schema.get("paths", {})

    operation_id_counts: dict[str, int] = {}
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if isinstance(operation_id, str) and operation_id:
                operation_id_counts[operation_id] = (
                    operation_id_counts.get(operation_id, 0) + 1
                )

    commands: list[CommandSpec] = []
    for path_template, path_item in sorted(paths.items()):
        if not isinstance(path_item, dict):
            continue
        for method in sorted(path_item.keys()):
            if method.lower() not in _HTTP_METHODS:
                continue
            operation = path_item.get(method) or {}
            if not isinstance(operation, dict):
                continue
            commands.append(
                _build_command_spec(
                    operation=operation,
                    method=method.upper(),
                    path_template=path_template,
                    operation_id_counts=operation_id_counts,
                    components=components,
                )
            )

    generated_at = datetime.now(tz=timezone.utc).isoformat()
    return ManifestResponse(
        generated_at=generated_at,
        capabilities=CapabilitiesSpec(),
        commands=commands,
    )


def build_command_index(
    app: FastAPI,
) -> tuple[dict[str, CommandSpec], ManifestResponse]:
    manifest = build_manifest(app)
    index: dict[str, CommandSpec] = {}
    for command in manifest.commands:
        index[command.command_id] = command
        for alias in command.aliases:
            index.setdefault(alias, command)
    return index, manifest


def _build_command_spec(
    *,
    operation: dict[str, Any],
    method: str,
    path_template: str,
    operation_id_counts: dict[str, int],
    components: dict[str, Any],
) -> CommandSpec:
    operation_id = operation.get("operationId")
    unique_operation_id = (
        isinstance(operation_id, str)
        and operation_id_counts.get(operation_id, 0) == 1
    )

    route_fallback_id = f"route::{method}::{path_template}"
    if unique_operation_id:
        command_id = f"op::{operation_id}"
        aliases = [route_fallback_id]
    else:
        command_id = route_fallback_id
        aliases = []

    effect = "read" if method in {"GET", "HEAD"} else "write"
    risk = "read_only" if effect == "read" else "mutating"
    idempotency = "safe" if effect == "read" else "unsafe"
    approval_mode = "none" if effect == "read" else "blocked_phase1"

    input_schema = _build_input_schema(
        operation=operation, components=components
    )
    return CommandSpec(
        command_id=command_id,
        aliases=aliases,
        layer="raw",
        method=method,
        path_template=path_template,
        operation_id=operation_id if isinstance(operation_id, str) else None,
        risk=risk,
        effect=effect,
        idempotency=idempotency,
        approval_mode=approval_mode,
        input_schema=input_schema,
    )


def _build_input_schema(
    *,
    operation: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    path_params = _parameter_schema(operation, "path", components)
    query = _parameter_schema(operation, "query", components)
    headers = _parameter_schema(operation, "header", components)
    body = _request_body_schema(operation, components)
    return {
        "path_params": path_params,
        "query": query,
        "headers": headers,
        "body": body,
    }


def _parameter_schema(
    operation: dict[str, Any], location: str, components: dict[str, Any]
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for param in operation.get("parameters", []) or []:
        if not isinstance(param, dict):
            continue
        if param.get("in") != location:
            continue
        name = param.get("name")
        if not isinstance(name, str) or not name:
            continue
        schema = _resolve_schema(param.get("schema") or {}, components)
        properties[name] = schema
        if param.get("required") is True:
            required.append(name)
    return {
        "type": "object",
        "properties": properties,
        "required": sorted(required),
    }


def _request_body_schema(
    operation: dict[str, Any], components: dict[str, Any]
) -> dict[str, Any]:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return {}
    content = request_body.get("content") or {}
    if not isinstance(content, dict) or not content:
        return {}
    media_type = (
        "application/json"
        if "application/json" in content
        else next(iter(content.keys()))
    )
    media_obj = content.get(media_type) or {}
    if not isinstance(media_obj, dict):
        return {}
    schema = _resolve_schema(media_obj.get("schema") or {}, components)
    if request_body.get("required") is True and isinstance(schema, dict):
        schema = dict(schema)
        schema.setdefault("required", [])
    return schema


def _resolve_schema(schema: Any, components: dict[str, Any]) -> Any:
    if not isinstance(schema, dict):
        return schema

    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        ref_name = ref.split("/")[-1]
        target = (components.get("schemas") or {}).get(ref_name)
        if isinstance(target, dict):
            return _resolve_schema(target, components)
        return schema

    resolved = dict(schema)
    if "properties" in resolved and isinstance(resolved["properties"], dict):
        resolved["properties"] = {
            key: _resolve_schema(value, components)
            for key, value in resolved["properties"].items()
        }
    if "items" in resolved:
        resolved["items"] = _resolve_schema(resolved["items"], components)
    if "allOf" in resolved and isinstance(resolved["allOf"], list):
        resolved["allOf"] = [
            _resolve_schema(v, components) for v in resolved["allOf"]
        ]
    if "oneOf" in resolved and isinstance(resolved["oneOf"], list):
        resolved["oneOf"] = [
            _resolve_schema(v, components) for v in resolved["oneOf"]
        ]
    if "anyOf" in resolved and isinstance(resolved["anyOf"], list):
        resolved["anyOf"] = [
            _resolve_schema(v, components) for v in resolved["anyOf"]
        ]
    return resolved
