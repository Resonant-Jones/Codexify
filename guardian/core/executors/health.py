"""Executor health and introspection for the canonical registry."""

from __future__ import annotations

import os
import shutil
from dataclasses import asdict, dataclass
from typing import Any

from guardian.core.executors.registry import (
    ExecutorRegistryEntry,
    get_executor_registry,
)
from guardian.protocol_tokens import (
    ExecutorAuthState,
    ExecutorAvailabilityState,
)


@dataclass(frozen=True, slots=True)
class ExecutorHealth:
    executor_id: str
    label: str
    release_posture: str
    installed: bool
    binary_path: str | None
    auth_state: str
    availability_state: str
    supports_local_models: bool
    supports_gateway_routing: bool
    supports_direct_provider_config: bool
    supported_auth_modes: tuple[str, ...]
    status_detail: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_binary_path(
    entry: ExecutorRegistryEntry,
) -> tuple[bool, str | None]:
    env_var = entry.binary_env_var
    raw_path = os.getenv(env_var)
    if raw_path:
        path = raw_path.strip()
        if path and shutil.which(path):
            return True, path
        return False, None
    binary_name = entry.install_label.lower().replace(" ", "")
    if shutil.which(binary_name):
        return True, binary_name
    return False, None


def _detect_auth_state(entry: ExecutorRegistryEntry) -> tuple[str, str | None]:
    env_var = entry.binary_env_var
    raw_path = os.getenv(env_var)
    if not raw_path:
        return (
            ExecutorAuthState.UNKNOWN.value,
            "binary path not configured via env var",
        )
    path = raw_path.strip()
    if not path:
        return ExecutorAuthState.UNKNOWN.value, "binary path env var is empty"
    if not shutil.which(path):
        return ExecutorAuthState.UNKNOWN.value, "binary not found on PATH"
    return (
        ExecutorAuthState.UNKNOWN.value,
        "auth state requires runtime probe; cannot determine statically",
    )


def _derive_availability(
    installed: bool,
    auth_state: str,
) -> tuple[str, str | None]:
    if not installed:
        return ExecutorAvailabilityState.NOT_INSTALLED.value, "binary not found"
    if auth_state == ExecutorAuthState.AUTHENTICATED.value:
        return ExecutorAvailabilityState.READY.value, None
    if auth_state == ExecutorAuthState.UNKNOWN.value:
        return (
            ExecutorAvailabilityState.DEGRADED.value,
            "auth state undetermined",
        )
    return (
        ExecutorAvailabilityState.UNAVAILABLE.value,
        "authentication required",
    )


def get_executor_health(entry: ExecutorRegistryEntry) -> ExecutorHealth:
    installed, binary_path = _resolve_binary_path(entry)
    auth_state, auth_detail = _detect_auth_state(entry)
    availability_state, availability_detail = _derive_availability(
        installed, auth_state
    )

    if availability_detail and auth_detail:
        status_detail = "; ".join(
            filter(None, [availability_detail, auth_detail])
        )
    else:
        status_detail = availability_detail or auth_detail

    return ExecutorHealth(
        executor_id=entry.executor_id.value,
        label=entry.install_label,
        release_posture=entry.release_posture.value,
        installed=installed,
        binary_path=binary_path,
        auth_state=auth_state,
        availability_state=availability_state,
        supports_local_models=entry.supports_local_models,
        supports_gateway_routing=entry.supports_gateway_base_url_routing,
        supports_direct_provider_config=entry.supports_direct_provider_config,
        supported_auth_modes=tuple(m.value for m in entry.supported_auth_modes),
        status_detail=status_detail,
    )


def get_all_executor_health() -> list[ExecutorHealth]:
    return [get_executor_health(entry) for entry in get_executor_registry()]


__all__ = [
    "ExecutorHealth",
    "get_executor_health",
    "get_all_executor_health",
]
