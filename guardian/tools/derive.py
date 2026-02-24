"""Derive model-callable ToolSpec entries from command-bus manifest."""

from __future__ import annotations

import hashlib
from typing import Any

from guardian.tools.spec import ToolSpec, sanitize_openai_identifier


def _derive_aliases(command: dict[str, Any]) -> list[str]:
    aliases: list[str] = []
    for alias in command.get("aliases", []) or []:
        alias_str = str(alias or "").strip()
        if alias_str and alias_str not in aliases:
            aliases.append(alias_str)

    operation_id = str(command.get("operation_id") or "").strip()
    if operation_id:
        for alias in (operation_id, f"op::{operation_id}"):
            if alias not in aliases:
                aliases.append(alias)
    return aliases


def _derive_input_schema(command: dict[str, Any]) -> dict[str, Any]:
    raw_input_schema = command.get("input_schema")
    if not isinstance(raw_input_schema, dict):
        return default_internal_invoke_schema()

    path_params = raw_input_schema.get("path_params")
    query = raw_input_schema.get("query")
    headers = raw_input_schema.get("headers")
    body = raw_input_schema.get("body")

    properties = {
        "path_params": (
            path_params if isinstance(path_params, dict) else {"type": "object"}
        ),
        "query": query if isinstance(query, dict) else {"type": "object"},
        "headers": headers if isinstance(headers, dict) else {"type": "object"},
        "body": body if isinstance(body, dict) else (body or {}),
    }
    required: list[str] = []
    for key in ("path_params", "query", "headers"):
        schema = properties.get(key)
        if isinstance(schema, dict) and schema.get("required"):
            required.append(key)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _derive_requires_confirmation(command: dict[str, Any]) -> bool:
    approval_mode = str(command.get("approval_mode") or "").strip()
    effect = str(command.get("effect") or "").strip()
    return approval_mode not in {"", "none"} or effect == "write"


def _derive_description(command: dict[str, Any]) -> str:
    method = str(command.get("method") or "GET").upper()
    path_template = str(command.get("path_template") or "")
    operation_id = str(command.get("operation_id") or "").strip()
    if operation_id:
        return f"{method} {path_template} ({operation_id})"
    return f"{method} {path_template}"


def _derive_openai_name(tool_id: str, used_names: set[str]) -> str:
    base = sanitize_openai_identifier(tool_id)
    candidate = base[:64]
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    suffix = "_" + hashlib.sha256(tool_id.encode("utf-8")).hexdigest()[:8]
    max_base_len = max(1, 64 - len(suffix))
    candidate = f"{base[:max_base_len]}{suffix}"
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    # Defensive fallback; keeps determinism even in extremely unlikely hash collisions.
    attempt = 1
    while True:
        alt_suffix = (
            "_"
            + hashlib.sha256(f"{tool_id}:{attempt}".encode()).hexdigest()[:8]
        )
        max_base_len = max(1, 64 - len(alt_suffix))
        candidate = f"{base[:max_base_len]}{alt_suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        attempt += 1


def derive_tools_from_command_manifest(
    manifest: dict[str, Any]
) -> list[ToolSpec]:
    """Build canonical ToolSpec list from command bus manifest payload."""

    tools: list[ToolSpec] = []
    used_openai_names: set[str] = set()
    for command in manifest.get("commands", []) or []:
        command_id = str(command.get("command_id") or "").strip()
        if not command_id:
            continue

        method = str(command.get("method") or "GET").upper()
        path_template = str(command.get("path_template") or "").strip() or "/"
        operation_id = str(command.get("operation_id") or "").strip() or None
        tool = ToolSpec(
            tool_id=command_id,
            name=command_id,
            openai_name=_derive_openai_name(command_id, used_openai_names),
            description=_derive_description(command),
            input_schema=_derive_input_schema(command),
            risk=str(command.get("risk") or "unknown"),  # type: ignore[arg-type]
            effect=str(command.get("effect") or "unknown"),  # type: ignore[arg-type]
            idempotency=str(command.get("idempotency") or "unknown"),  # type: ignore[arg-type]
            requires_confirmation=_derive_requires_confirmation(command),
            allow_passthrough_arguments=False,
            tags=[
                "layer:raw",
                f"method:{method.lower()}",
                f"effect:{str(command.get('effect') or 'unknown')}",
            ],
            command_id=command_id,
            operation_id=operation_id,
            method=method,  # type: ignore[arg-type]
            path_template=path_template,
            aliases=_derive_aliases(command),
        )
        tools.append(tool)
    return tools


def derive_tools_from_manifest(manifest: dict[str, Any]) -> list[ToolSpec]:
    """Backward-compatible alias for previous API."""

    return derive_tools_from_command_manifest(manifest)
