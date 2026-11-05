"""
Provider-neutral sandbox execution.

The public surface of the sandbox subsystem. Guardian runtime semantics never
name a provider: they build a :class:`SandboxRequest`, resolve a provider from
the registry, and consume a :class:`SandboxResult`.
"""

from __future__ import annotations

from .contracts import (
    SANDBOX_CONTRACT_VERSION,
    AttestedPosture,
    SandboxBoundaryError,
    SandboxError,
    SandboxExecutionError,
    SandboxPolicyDenied,
    SandboxProvenance,
    SandboxProvider,
    SandboxRequest,
    SandboxResult,
    SandboxTimeout,
)
from .policy import (
    assert_postures_supported,
    default_resource_posture,
    unsupported_postures,
)
from .registry import (
    get_provider,
    list_providers,
    provider_postures,
    register_provider,
    unregister_provider,
)

__all__ = [
    "AttestedPosture",
    "SANDBOX_CONTRACT_VERSION",
    "SandboxBoundaryError",
    "SandboxError",
    "SandboxExecutionError",
    "SandboxPolicyDenied",
    "SandboxProvenance",
    "SandboxProvider",
    "SandboxRequest",
    "SandboxResult",
    "SandboxTimeout",
    "assert_postures_supported",
    "default_resource_posture",
    "get_provider",
    "list_providers",
    "provider_postures",
    "register_provider",
    "unregister_provider",
    "unsupported_postures",
]
