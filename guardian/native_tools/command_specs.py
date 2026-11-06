"""Canonical command specs for Guardian's native tool family.

A native command reuses the command bus's own contract. It is declared with
``layer="internal"`` and ``method="INTERNAL"`` so that it never renders an
HTTP path, and it carries the same safety facts the bus already understands:
``risk``, ``effect``, ``idempotency`` and ``approval_mode``.

Two fields are added to the shared command contract for this family:

``open_world``
    A **declaration** that the command's effect reaches beyond the local
    machine and its files. It is deliberately *not* the ``network_allowed``
    permission: that is a per-execution grant resolved from the effective
    permission profile, and neither axis derives from the other.

``justification``
    A **human-readable rationale** explaining why the command behaves as it
    does. It is deliberately *not* a canonical policy reason code. The reason
    codes emitted by ``guardian.tools.policy`` (``write_effect``, ``risk_high``,
    ``external_network``, ``requires_confirmation``, ``loopback_base_missing``)
    are the stable machine vocabulary that decisions and receipts key on. A
    justification is never emitted as, or collapsed into, a reason code, and a
    reason code is never derived from a justification.
"""

from __future__ import annotations

from typing import Any

from guardian.command_bus.contracts import CommandSpec
from guardian.core.repository_containment import (
    MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS,
)

__all__ = [
    "NATIVE_COMMAND_IDS",
    "NATIVE_READ_FILE_COMMAND_ID",
    "READ_FILE_JUSTIFICATION",
    "build_native_command_specs",
]

NATIVE_READ_FILE_COMMAND_ID = "native::fs::read_file"

READ_FILE_JUSTIFICATION = (
    "Reads one file as text from the authenticated account's own Project, "
    "line-numbered and bounded. It does not modify anything, does not run a "
    "process, and does not use the network."
)

#: The complete set of native command ids. Dispatch consults this registry
#: explicitly rather than matching a prefix, so an unknown ``native::`` id is
#: never dispatched.
NATIVE_COMMAND_IDS: frozenset[str] = frozenset({NATIVE_READ_FILE_COMMAND_ID})


def build_native_command_specs() -> list[CommandSpec]:
    """Return the canonical command specs for the native tool family."""

    return [_build_read_file_command_spec()]


def _build_read_file_command_spec() -> CommandSpec:
    return CommandSpec(
        command_id=NATIVE_READ_FILE_COMMAND_ID,
        aliases=[],
        layer="internal",
        method="INTERNAL",
        path_template="",
        operation_id=None,
        risk="read_only",
        effect="read",
        idempotency="safe",
        approval_mode="none",
        open_world=False,
        justification=READ_FILE_JUSTIFICATION,
        input_schema={
            "path_params": _empty_object_schema(),
            "query": _empty_object_schema(),
            "headers": _empty_object_schema(),
            "body": _read_file_body_schema(),
        },
    )


def _read_file_body_schema() -> dict[str, Any]:
    """Describe the bus-level body contract for ``native::fs::read_file``.

    ``path`` is the only field a model may choose. ``scope`` is the Project
    the read is bound to; it is injected server-side by the tool-turn handler
    and re-verified by the handler against the authenticated account, so a
    forged scope fails closed rather than widening the grant.
    """

    return {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS,
            },
            "scope": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer", "minimum": 1},
                },
                "required": ["project_id"],
                "additionalProperties": False,
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }


def _empty_object_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {},
        "required": [],
    }
