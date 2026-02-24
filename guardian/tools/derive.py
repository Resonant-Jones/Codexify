# guardian/tools/derive.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from guardian.tools.spec import ToolArgSpec, ToolPolicy, ToolSpec


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def default_policy_for_command(cmd: dict[str, Any]) -> ToolPolicy:
    """
    Opinionated defaults:
    - require identity
    - require loopback for command execution (Docker posture)
    - side effects inferred from method (POST/PUT/PATCH/DELETE)
    - network egress default false
    """
    method = (cmd.get("method") or "GET").upper()
    side_effects = method in ("POST", "PUT", "PATCH", "DELETE")

    # You can refine these heuristics later:
    # - tag-based inference
    # - path-based inference
    # - explicit overrides in a registry file
    return ToolPolicy(
        visibility="public",
        require_identity=True,
        side_effects=side_effects,
        network_egress=False,
        egress_domains=[],
        rate_limit=None,
        timeout_seconds=None,
        require_loopback=True,
        allow_in_automations=True,
    )


def derive_tool_id(cmd: dict[str, Any]) -> str:
    # Prefer operation_id if present; else method+path.
    op = cmd.get("operation_id")
    if op:
        return f"tool::{_slugify(op)}"
    method = (cmd.get("method") or "GET").upper()
    path = cmd.get("path_template") or cmd.get("path") or ""
    return f"tool::{_slugify(method)}::{_slugify(path)}"


def derive_title(cmd: dict[str, Any]) -> str:
    # Prefer summary/title; fall back to operation_id.
    return (
        cmd.get("summary")
        or cmd.get("title")
        or cmd.get("operation_id")
        or cmd.get("command_id")
        or "Tool"
    )


def derive_args(cmd: dict[str, Any]) -> ToolArgSpec:
    """
    Keep it minimal at first.
    If your manifest already includes request schema, plumb it through.
    Otherwise use a generic shape used by invoke today.
    """
    schema = cmd.get("arguments_schema") or {
        "type": "object",
        "properties": {
            "path_params": {"type": "object"},
            "query": {"type": "object"},
            "headers": {"type": "object"},
            "body": {},
        },
        "required": ["path_params", "query", "headers"],
    }
    required = schema.get("required", [])
    examples = cmd.get("examples") or []
    return ToolArgSpec(schema=schema, required=required, examples=examples)


def derive_tools_from_manifest(manifest: dict[str, Any]) -> list[ToolSpec]:
    tools: list[ToolSpec] = []
    for cmd in manifest.get("commands", []):
        policy = default_policy_for_command(cmd)
        tools.append(
            ToolSpec(
                tool_id=derive_tool_id(cmd),
                command_id=cmd["command_id"],
                operation_id=cmd.get("operation_id"),
                method=(cmd.get("method") or "GET").upper(),
                path_template=cmd.get("path_template") or cmd.get("path") or "",
                title=derive_title(cmd),
                description=cmd.get("description") or "",
                args=derive_args(cmd),
                policy=policy,
            )
        )
    return tools
