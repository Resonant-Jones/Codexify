"""
Sandbox posture policy.

The policy layer answers one question before any provider is contacted:
*can the named provider establish every posture this request requires?*

A provider that cannot establish a requested posture is not allowed to
substitute a wider one. The request is denied instead, and the denial is
reported separately from an execution failure.
"""

from __future__ import annotations

import os
from typing import Iterable

from .contracts import (
    KNOWN_POSTURES,
    POSTURE_CPU_LIMIT,
    POSTURE_EGRESS_ALLOWLIST,
    POSTURE_EGRESS_DENY,
    POSTURE_MEMORY_LIMIT,
    POSTURE_READ_ONLY_WORKSPACE,
    POSTURE_SECRET_ISOLATION,
    POSTURE_STORAGE_CEILING,
    POSTURE_TEARDOWN,
    POSTURE_TIMEOUT,
    SandboxPolicyDenied,
    SandboxRequest,
)

#: Postures the hosted sandbox posture requires by default. A request that
#: does not name these is still evaluated against the provider's declared
#: capabilities, but the default posture is what the runtime asks for when it
#: builds a request from an operator policy.
DEFAULT_REQUIRED_POSTURES: tuple[str, ...] = (
    POSTURE_READ_ONLY_WORKSPACE,
    POSTURE_EGRESS_DENY,
    POSTURE_CPU_LIMIT,
    POSTURE_MEMORY_LIMIT,
    POSTURE_STORAGE_CEILING,
    POSTURE_TIMEOUT,
    POSTURE_TEARDOWN,
    POSTURE_SECRET_ISOLATION,
)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def default_resource_posture():
    """Build the default bounded resource posture from the environment."""
    from .contracts import ResourcePosture

    return ResourcePosture(
        timeout_seconds=_env_int("CODEXIFY_SANDBOX_TIMEOUT_SECONDS", 900),
        cpu_millis=_env_int("CODEXIFY_SANDBOX_CPU_MILLIS", 1000),
        memory_mb=_env_int("CODEXIFY_SANDBOX_MEMORY_MB", 2048),
        storage_bytes=_env_int(
            "CODEXIFY_SANDBOX_STORAGE_BYTES", 2 * 1024 * 1024 * 1024
        ),
        output_max_bytes=_env_int("CODEXIFY_SANDBOX_OUTPUT_MAX_BYTES", 1024 * 1024),
    )


def unsupported_postures(
    required: Iterable[str], supported: Iterable[str]
) -> tuple[str, ...]:
    """Return the requested postures the provider cannot establish."""
    supported_set = {str(item) for item in supported}
    missing = []
    for posture in required:
        if posture not in supported_set:
            missing.append(posture)
    return tuple(missing)


def assert_postures_supported(
    request: SandboxRequest,
    supported: Iterable[str],
    *,
    provider: str | None = None,
    extra_required: Iterable[str] = (),
) -> None:
    """
    Deny the request when the provider cannot establish a required posture.

    Raises:
        SandboxPolicyDenied: before any sandbox is allocated.
    """
    required = tuple(request.required_postures()) + tuple(extra_required)
    missing = unsupported_postures(required, supported)
    if not missing:
        return
    raise SandboxPolicyDenied(
        "provider cannot establish the requested sandbox posture: "
        + ", ".join(sorted(missing)),
        provider=provider,
        unsupported=missing,
    )


def validate_known_postures(postures: Iterable[str]) -> None:
    """Raise when a provider declares a posture the contract does not know."""
    unknown = sorted(set(postures) - set(KNOWN_POSTURES))
    if unknown:
        raise ValueError(f"unknown sandbox posture(s): {', '.join(unknown)}")


__all__ = [
    "DEFAULT_REQUIRED_POSTURES",
    "assert_postures_supported",
    "default_resource_posture",
    "unsupported_postures",
    "validate_known_postures",
]
