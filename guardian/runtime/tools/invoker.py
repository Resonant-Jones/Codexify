from __future__ import annotations
from typing import Any, Dict, Tuple
import click

from guardian.cli.memoryos_cli import cli as root_cli
from guardian.guardian_main import app as guardian_main_app
from guardian.cli.imprint_zero_cli import app as imprint_zero_app
try:  # Typer conversion to Click command (supports multiple versions)
    from typer.main import get_command as _typer_get_command  # type: ignore
except Exception:  # pragma: no cover
    _typer_get_command = None  # type: ignore


def _to_click(cmd_app):
    method = getattr(cmd_app, "to_click_command", None)
    if callable(method):
        return method()
    if _typer_get_command is not None:
        return _typer_get_command(cmd_app)
    raise RuntimeError("Unable to convert Typer app to Click command; incompatible Typer version.")

ROOTS: Dict[str, click.BaseCommand] = {
    "": root_cli,
    "gm": _to_click(guardian_main_app),
    "imprint-zero": _to_click(imprint_zero_app),
}

def _resolve(fq_name: str) -> Tuple[click.Command, str]:
    """
    Resolve 'prefix:sub:cmd' into a Click command and return (command, canonical_name).
    """
    parts = fq_name.split(":")
    prefix = ""
    root = ROOTS[""]

    # If first segment is a registered prefix, pop it and switch root
    if parts[0] in ROOTS and parts[0] != "":
        prefix = parts.pop(0)
        root = ROOTS[prefix]

    cmd = root
    ctx = click.Context(cmd)
    for i, part in enumerate(parts):
        sub = cmd.get_command(ctx, part) if isinstance(cmd, click.MultiCommand) else None
        if sub is None:
            raise ValueError(f"Unknown command segment: {part} in {fq_name}")
        if i == len(parts) - 1:
            if isinstance(sub, click.Command):
                canonical = f"{prefix + ':' if prefix else ''}{':'.join(parts)}"
                return sub, canonical
            raise ValueError(f"Terminal segment '{part}' is not a command.")
        cmd = sub
        ctx = click.Context(cmd)

    raise ValueError(f"Could not resolve command: {fq_name}")

def invoke_tool(fq_name: str, args: Dict[str, Any]) -> Any:
    """
    Python‑level invocation of the Click/Typer command callback.
    """
    cmd, _ = _resolve(fq_name)
    if not hasattr(cmd, "callback") or cmd.callback is None:
        raise ValueError(f"Command {fq_name} has no callback to invoke.")
    # Match kwargs by parameter names
    return cmd.callback(**{k: v for k, v in args.items() if k in {p.name for p in cmd.params}})
