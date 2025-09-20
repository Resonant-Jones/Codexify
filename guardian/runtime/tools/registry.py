from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import click

# --- Import your roots ---
# Root Click CLI (console script): guardian.cli.memoryos_cli:cli
from guardian.cli.memoryos_cli import cli as root_cli

# Typer conversion helper for compatibility across versions
try:
    from typer.main import get_command as _typer_get_command  # type: ignore
except Exception:  # pragma: no cover
    _typer_get_command = None  # type: ignore


def _to_click(app):
    method = getattr(app, "to_click_command", None)
    if callable(method):
        return method()
    if _typer_get_command is not None:
        return _typer_get_command(app)
    raise RuntimeError(
        "Unable to convert Typer app to Click command; incompatible Typer version."
    )


# Guardian Main (Typer app) at guardian/guardian_main.py
try:
    from guardian.guardian_main import app as guardian_main_app

    gm_click = _to_click(guardian_main_app)
except Exception:
    gm_click = None

# Imprint-Zero (Typer sub-app) at guardian/cli/imprint_zero_cli.py
try:
    from guardian.cli.imprint_zero_cli import app as imprint_zero_app

    iz_click = _to_click(imprint_zero_app)
except Exception:
    iz_click = None

# Prefix → Click root table
ROOTS: List[Tuple[str, click.BaseCommand]] = [("", root_cli)]
if gm_click is not None:
    ROOTS.append(("gm", gm_click))
if iz_click is not None:
    ROOTS.append(("imprint-zero", iz_click))


def _click_type_to_json(p: click.Parameter) -> Dict[str, Any]:
    # Map Click/Typer types → JSON Schema
    t = "string"
    # Flags become boolean
    if getattr(p, "is_flag", False):
        t = "boolean"
    else:
        # Infer numeric types
        pt = getattr(p, "type", None)
        if pt is not None:
            tn = type(pt).__name__.lower()
            if "int" in tn:
                t = "integer"
            elif "float" in tn:
                t = "number"
    schema = {"type": t}
    default = getattr(p, "default", None)
    # Include defaults when present and not None; avoid click internals
    if default is not None:
        schema["default"] = default
    if getattr(p, "multiple", False):
        schema = {"type": "array", "items": {"type": t}}
    return schema


def _command_to_tool_spec(fq_name: str, cmd: click.Command) -> Dict[str, Any]:
    desc = (
        cmd.help
        or cmd.short_help
        or (getattr(cmd.callback, "__doc__", "") if hasattr(cmd, "callback") else "")
        or ""
    ).strip()

    props: Dict[str, Any] = {}
    required: List[str] = []
    for p in cmd.params:
        # Param names are normalized by Click/Typer; options use 'name'
        pname = getattr(p, "name", None)
        if not pname:
            continue
        # Skip hidden/internal params
        if getattr(p, "hidden", False):
            continue
        schema = _click_type_to_json(p)
        props[pname] = schema
        if getattr(p, "required", False):
            required.append(pname)

    spec = {
        "type": "function",
        "function": {
            "name": fq_name,
            "description": desc if desc else f"Run CLI command '{fq_name}'.",
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }
    return spec


def _walk(group: click.BaseCommand, prefix: str) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    if not hasattr(group, "list_commands"):
        # Not a group; if it's a single command, add it directly
        if isinstance(group, click.Command):
            specs.append(_command_to_tool_spec(prefix or group.name or "root", group))
        return specs

    ctx = click.Context(group)  # type: ignore[arg-type]
    for name in group.list_commands(ctx):  # type: ignore[attr-defined]
        sub = group.get_command(ctx, name)  # type: ignore[attr-defined]
        if sub is None:
            continue
        fq = f"{prefix}:{name}" if prefix else name
        if hasattr(sub, "list_commands"):
            specs.extend(_walk(sub, fq))
        elif isinstance(sub, click.Command):
            specs.append(_command_to_tool_spec(fq, sub))
    return specs


def generate_tools_manifest() -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for prefix, root in ROOTS:
        if hasattr(root, "list_commands"):
            tools.extend(_walk(root, prefix))
        elif isinstance(root, click.Command):
            tools.append(_command_to_tool_spec(prefix or root.name or "root", root))
    # Append HTTP-backed tool for Codexify save-entry
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "codexify.save_entry",
                "description": "Preview and optionally export a single note to Google Drive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string", "default": ""},
                        "format": {
                            "type": "string",
                            "enum": ["md", "txt", "html"],
                            "default": "md",
                        },
                        "folder": {"type": "string"},
                        "folder_url": {"type": "string"},
                        "return_links": {"type": "boolean", "default": True},
                        "dry_run": {"type": "boolean", "default": False},
                    },
                    "required": ["title"],
                },
            },
        }
    )
    tools.append(
        {
            "type": "function",
            "function": {
                "name": "codexify.confirm_and_save",
                "description": "Preview a note and, if confirm=true, save it to Google Drive.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string", "default": ""},
                        "format": {
                            "type": "string",
                            "enum": ["md", "txt", "html"],
                            "default": "md",
                        },
                        "folder": {"type": "string"},
                        "folder_url": {"type": "string"},
                        "return_links": {"type": "boolean", "default": True},
                        "confirm": {"type": "boolean", "default": False},
                    },
                    "required": ["title"],
                },
            },
        }
    )
    return tools


def write_tools_manifest(path: str = "guardian/runtime/tools/manifest.json") -> None:
    tools = generate_tools_manifest()
    with open(path, "w") as f:
        json.dump(tools, f, indent=2)
    print(f"Wrote tools manifest to {path} with {len(tools)} tools.")


if __name__ == "__main__":
    write_tools_manifest()
