"""Bounded error-code registry and the adapter's exception type.

Every failure surfaced by this package maps onto exactly one code from
:data:`ERROR_CODES`. Codes are part of the MCP-facing contract, so this
registry is deliberately closed: adding a code is a deliberate contract
change, not an implementation detail.

Error messages are written to be safe to show to a local operator and to an
MCP client. They never embed credentials, connection strings, stack traces, or
memory content.
"""

from __future__ import annotations

from typing import Final

# --- Configuration / request shape -----------------------------------------
INVALID_CONFIGURATION: Final = "invalid_configuration"
INVALID_REQUEST: Final = "invalid_request"
UNSUPPORTED_OPERATION: Final = "unsupported_operation"

# --- Upstream reachability / identity -------------------------------------
GUARDIAN_UNREACHABLE: Final = "guardian_unreachable"
WRONG_UPSTREAM: Final = "wrong_upstream"
GUARDIAN_TIMEOUT: Final = "guardian_timeout"
UPSTREAM_ERROR: Final = "upstream_error"
UPSTREAM_RATE_LIMITED: Final = "upstream_rate_limited"

# --- Authorization ---------------------------------------------------------
AUTH_REQUIRED: Final = "auth_required"
ACCESS_DENIED: Final = "access_denied"

# --- Data / route state ----------------------------------------------------
NOT_FOUND: Final = "not_found"
ROUTE_UNAVAILABLE: Final = "route_unavailable"
CONFLICT: Final = "conflict"

ERROR_CODES: Final[frozenset[str]] = frozenset(
    {
        INVALID_CONFIGURATION,
        INVALID_REQUEST,
        UNSUPPORTED_OPERATION,
        GUARDIAN_UNREACHABLE,
        WRONG_UPSTREAM,
        GUARDIAN_TIMEOUT,
        UPSTREAM_ERROR,
        UPSTREAM_RATE_LIMITED,
        AUTH_REQUIRED,
        ACCESS_DENIED,
        NOT_FOUND,
        ROUTE_UNAVAILABLE,
        CONFLICT,
    }
)


class CodexifyMCPError(Exception):
    """A structured, client-safe adapter failure.

    Handlers convert this into the ``ok=False`` response envelope rather than
    raising out of a tool call. Under MCP v2 an exception escaping a tool
    handler surfaces as a JSON-RPC protocol error, which would hide the
    structured ``code`` an MCP client needs in order to react sensibly.
    """

    __slots__ = ("code", "message", "warnings")

    def __init__(
        self,
        code: str,
        message: str,
        *,
        warnings: list[str] | None = None,
    ) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"undeclared error code: {code!r}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.warnings = list(warnings or [])

    def to_error(self) -> dict[str, str]:
        """Render the ``error`` half of the response envelope."""
        return {"code": self.code, "message": self.message}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"CodexifyMCPError(code={self.code!r}, message={self.message!r})"


class ConfigurationError(CodexifyMCPError):
    """Raised at startup for an unusable environment."""

    def __init__(self, message: str) -> None:
        super().__init__(INVALID_CONFIGURATION, message)


__all__ = [
    "ACCESS_DENIED",
    "AUTH_REQUIRED",
    "CONFLICT",
    "ConfigurationError",
    "CodexifyMCPError",
    "ERROR_CODES",
    "GUARDIAN_TIMEOUT",
    "GUARDIAN_UNREACHABLE",
    "INVALID_CONFIGURATION",
    "INVALID_REQUEST",
    "NOT_FOUND",
    "ROUTE_UNAVAILABLE",
    "UNSUPPORTED_OPERATION",
    "UPSTREAM_ERROR",
    "UPSTREAM_RATE_LIMITED",
    "WRONG_UPSTREAM",
]
