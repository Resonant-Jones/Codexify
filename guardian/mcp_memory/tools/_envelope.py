"""Shared response-envelope helpers for the memory MCP tools.

Source fields are passed through with their meaning intact. This module never
rewrites lifecycle, review posture, persona attribution, provenance, or
candidate status, and never invents a confidence value.
"""

from __future__ import annotations

from typing import Any

from ..errors import CodexifyMCPError


def envelope(
    data: Any,
    *,
    source: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Build a successful response envelope."""
    return {
        "ok": True,
        "data": data,
        "error": None,
        "_meta": {"source": source, "warnings": list(warnings or [])},
    }


def error_envelope(error: CodexifyMCPError, *, source: str) -> dict[str, Any]:
    """Build a failed response envelope from a structured adapter error."""
    return {
        "ok": False,
        "data": None,
        "error": error.to_error(),
        "_meta": {"source": source, "warnings": list(error.warnings)},
    }


async def run_tool(source: str, call):
    """Execute an async tool body, converting structured errors into envelopes.

    Keeping this in one place guarantees that no tool can accidentally raise a
    raw exception into the MCP transport, which would take the process's
    tool surface down with it.
    """
    try:
        data, warnings = await call()
    except CodexifyMCPError as exc:
        return error_envelope(exc, source=source)
    return envelope(data, source=source, warnings=warnings)


__all__ = ["envelope", "error_envelope", "run_tool"]
