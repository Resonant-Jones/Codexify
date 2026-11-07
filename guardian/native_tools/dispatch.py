"""Dispatch for Guardian's native tool family.

Dispatch consults the explicit command-id registry in
:mod:`guardian.native_tools.command_specs`. An unknown ``native::`` id is
never dispatched, and a native command is never confused with the Codex
Runner bridge's ``internal::`` ids.
"""

from __future__ import annotations

from typing import Any

from guardian.command_bus.contracts import InvokeArguments
from guardian.native_tools.command_specs import (
    NATIVE_COMMAND_IDS,
    NATIVE_READ_FILE_COMMAND_ID,
)
from guardian.native_tools.handlers import read_file as read_file_handler

__all__ = ["execute_native_command", "is_native_command"]


def is_native_command(command_id: str) -> bool:
    """Return whether a command id belongs to the native tool family."""

    return str(command_id or "") in NATIVE_COMMAND_IDS


def execute_native_command(
    *,
    command_id: str,
    arguments: InvokeArguments,
    auth_subject: str | None,
) -> dict[str, Any]:
    """Execute one native command in process."""

    if command_id == NATIVE_READ_FILE_COMMAND_ID:
        return read_file_handler.execute_read_file(
            arguments=arguments,
            auth_subject=auth_subject,
        )
    raise ValueError(f"Unsupported native command: {command_id}")
