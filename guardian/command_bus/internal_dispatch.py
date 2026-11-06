"""Dispatch for every internal (non-HTTP) command-bus command.

The command bus has two kinds of internal command:

* the Codex Runner preflight bridge (``internal::guardian.codex_runner.*``),
  which exists to drive an external preflight binary; and
* the native tool family (``native::*``), which executes in process.

Both are dispatched here so that :mod:`guardian.command_bus.invoke` keeps a
single internal branch and one set of run bookkeeping.
"""

from __future__ import annotations

from typing import Any

from guardian.codex_runner_bridge.command_bus import execute_guardian_bridge_command
from guardian.command_bus.contracts import InvokeArguments
from guardian.native_tools.dispatch import execute_native_command, is_native_command

__all__ = ["execute_internal_command"]


def execute_internal_command(
    *,
    command_id: str,
    arguments: InvokeArguments,
    auth_subject: str | None,
) -> dict[str, Any]:
    """Execute one internal command, in process, by family."""

    if is_native_command(command_id):
        return execute_native_command(
            command_id=command_id,
            arguments=arguments,
            auth_subject=auth_subject,
        )
    return execute_guardian_bridge_command(
        command_id=command_id,
        arguments=arguments,
    )
