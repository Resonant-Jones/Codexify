"""
Sandbox provider registry.

Providers register themselves here. Guardian runtime semantics never name a
provider: they ask the registry for the configured provider and consume the
result contract. Adding a second provider is a registration, not a change to
runtime code.
"""

from __future__ import annotations

import logging
import os
from typing import Callable

from .contracts import SandboxPolicyDenied, SandboxProvider

logger = logging.getLogger(__name__)

ProviderFactory = Callable[[], SandboxProvider]

_PROVIDERS: dict[str, ProviderFactory] = {}


def _builtin_factories() -> dict[str, ProviderFactory]:
    """Providers that ship with Codexify and need no explicit registration."""
    from .adapters.docker_cloud import DockerCloudSandboxProvider

    return {"docker_cloud": DockerCloudSandboxProvider}


def register_provider(name: str, factory: ProviderFactory) -> None:
    """Register a provider factory under ``name``."""
    key = (name or "").strip().lower()
    if not key:
        raise ValueError("provider name is required")
    _PROVIDERS[key] = factory


def unregister_provider(name: str) -> None:
    """Remove a provider registration (used by tests)."""
    _PROVIDERS.pop((name or "").strip().lower(), None)


def list_providers() -> list[str]:
    """Registered provider names."""
    return sorted(set(_PROVIDERS) | set(_builtin_factories()))


def get_provider(name: str | None = None) -> SandboxProvider:
    """
    Instantiate the named provider.

    Defaults to ``CODEXIFY_SANDBOX_PROVIDER``. Fails closed when the provider
    is unknown or its construction fails -- the runtime never falls back to a
    different provider on its own, because a fallback would silently widen
    the established posture.
    """
    key = (name or os.getenv("CODEXIFY_SANDBOX_PROVIDER") or "").strip().lower()
    if not key:
        raise SandboxPolicyDenied(
            "no sandbox provider configured; set CODEXIFY_SANDBOX_PROVIDER"
        )
    factory = _PROVIDERS.get(key) or _builtin_factories().get(key)
    if factory is None:
        raise SandboxPolicyDenied(
            f"unknown sandbox provider: {key}",
            provider=key,
            unsupported=(),
        )
    return factory()


def provider_postures(name: str | None = None) -> tuple[str, ...]:
    """Postures the named provider declares it can establish."""
    return get_provider(name).supported_postures()


__all__ = [
    "get_provider",
    "list_providers",
    "provider_postures",
    "register_provider",
    "unregister_provider",
]
