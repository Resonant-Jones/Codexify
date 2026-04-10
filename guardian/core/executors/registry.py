"""Canonical registry for supported coding-agent executors."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from guardian.protocol_tokens import ExecutorAuthMode as _ExecutorAuthMode
from guardian.protocol_tokens import ExecutorId as _ExecutorId
from guardian.protocol_tokens import (
    ExecutorReleasePosture as _ExecutorReleasePosture,
)

ExecutorId = _ExecutorId
ExecutorReleasePosture = _ExecutorReleasePosture
ExecutorAuthMode = _ExecutorAuthMode


def _normalize_executor_id(raw: ExecutorId | str) -> ExecutorId:
    if isinstance(raw, ExecutorId):
        return raw
    candidate = (
        str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    )
    if not candidate:
        raise KeyError("unknown executor: <empty>")
    try:
        return ExecutorId(candidate)
    except ValueError as exc:
        raise KeyError(f"unknown executor: {candidate}") from exc


def _normalize_release_posture(
    raw: ExecutorReleasePosture | str,
) -> ExecutorReleasePosture:
    if isinstance(raw, ExecutorReleasePosture):
        return raw
    candidate = (
        str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    )
    if not candidate:
        raise ValueError("release_posture must be non-empty")
    try:
        return ExecutorReleasePosture(candidate)
    except ValueError as exc:
        raise ValueError(f"invalid release posture: {candidate}") from exc


def _normalize_auth_mode(raw: ExecutorAuthMode | str) -> ExecutorAuthMode:
    if isinstance(raw, ExecutorAuthMode):
        return raw
    candidate = (
        str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    )
    if not candidate:
        raise ValueError("supported_auth_modes must not contain empty values")
    try:
        return ExecutorAuthMode(candidate)
    except ValueError as exc:
        raise ValueError(f"invalid executor auth mode: {candidate}") from exc


def _normalize_auth_modes(
    raw: Iterable[ExecutorAuthMode | str],
) -> tuple[ExecutorAuthMode, ...]:
    normalized: list[ExecutorAuthMode] = []
    for mode in raw:
        candidate = _normalize_auth_mode(mode)
        if candidate not in normalized:
            normalized.append(candidate)
    return tuple(normalized)


def _normalize_text(raw: Any) -> str:
    return str(raw or "").strip()


@dataclass(frozen=True, slots=True)
class ExecutorCapability:
    supports_direct_provider_config: bool
    supports_local_models: bool
    supports_gateway_base_url_routing: bool
    supports_structured_escalations: bool

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ExecutorRegistryEntry:
    executor_id: ExecutorId
    install_label: str
    binary_env_var: str
    supported_auth_modes: tuple[ExecutorAuthMode, ...] = field(
        default_factory=tuple
    )
    release_posture: ExecutorReleasePosture = ExecutorReleasePosture.OPTIONAL
    supports_direct_provider_config: bool = False
    supports_local_models: bool = False
    supports_gateway_base_url_routing: bool = False
    supports_structured_escalations: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "executor_id", _normalize_executor_id(self.executor_id)
        )
        install_label = _normalize_text(self.install_label)
        if not install_label:
            raise ValueError("install_label must be non-empty")
        object.__setattr__(self, "install_label", install_label)

        binary_env_var = _normalize_text(self.binary_env_var)
        if not binary_env_var:
            raise ValueError("binary_env_var must be non-empty")
        object.__setattr__(self, "binary_env_var", binary_env_var)

        supported_auth_modes = _normalize_auth_modes(self.supported_auth_modes)
        if not supported_auth_modes:
            raise ValueError("supported_auth_modes must not be empty")
        object.__setattr__(self, "supported_auth_modes", supported_auth_modes)
        object.__setattr__(
            self,
            "release_posture",
            _normalize_release_posture(self.release_posture),
        )
        object.__setattr__(
            self,
            "supports_direct_provider_config",
            bool(self.supports_direct_provider_config),
        )
        object.__setattr__(
            self,
            "supports_local_models",
            bool(self.supports_local_models),
        )
        object.__setattr__(
            self,
            "supports_gateway_base_url_routing",
            bool(self.supports_gateway_base_url_routing),
        )
        object.__setattr__(
            self,
            "supports_structured_escalations",
            bool(self.supports_structured_escalations),
        )

    @property
    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            supports_direct_provider_config=self.supports_direct_provider_config,
            supports_local_models=self.supports_local_models,
            supports_gateway_base_url_routing=self.supports_gateway_base_url_routing,
            supports_structured_escalations=self.supports_structured_escalations,
        )

    @property
    def capabilities(self) -> ExecutorCapability:
        """Backward-compatible alias for the capability aggregate."""
        return self.capability

    def to_dict(self) -> dict[str, Any]:
        return {
            "executor_id": self.executor_id.value,
            "install_label": self.install_label,
            "binary_env_var": self.binary_env_var,
            "supported_auth_modes": [
                mode.value for mode in self.supported_auth_modes
            ],
            "release_posture": self.release_posture.value,
            "supports_direct_provider_config": self.supports_direct_provider_config,
            "supports_local_models": self.supports_local_models,
            "supports_gateway_base_url_routing": (
                self.supports_gateway_base_url_routing
            ),
            "supports_structured_escalations": (
                self.supports_structured_escalations
            ),
            "capability": self.capability.to_dict(),
        }


_EXECUTOR_REGISTRY: tuple[ExecutorRegistryEntry, ...] = (
    ExecutorRegistryEntry(
        executor_id=ExecutorId.CODEX,
        install_label="Codex CLI",
        binary_env_var="CODEXIFY_CODEX_BIN",
        supported_auth_modes=(
            ExecutorAuthMode.DIRECT_PROVIDER,
            ExecutorAuthMode.GATEWAY_BASE_URL,
        ),
        release_posture=ExecutorReleasePosture.OFFICIAL,
        supports_direct_provider_config=True,
        supports_local_models=False,
        supports_gateway_base_url_routing=True,
        supports_structured_escalations=True,
    ),
    ExecutorRegistryEntry(
        executor_id=ExecutorId.CLAUDE_CODE,
        install_label="Claude Code",
        binary_env_var="CODEXIFY_CLAUDE_CODE_BIN",
        supported_auth_modes=(
            ExecutorAuthMode.DIRECT_PROVIDER,
            ExecutorAuthMode.GATEWAY_BASE_URL,
        ),
        release_posture=ExecutorReleasePosture.OPTIONAL,
        supports_direct_provider_config=True,
        supports_local_models=False,
        supports_gateway_base_url_routing=True,
        supports_structured_escalations=True,
    ),
    ExecutorRegistryEntry(
        executor_id=ExecutorId.OPENCODE,
        install_label="OpenCode",
        binary_env_var="CODEXIFY_OPENCODE_BIN",
        supported_auth_modes=(
            ExecutorAuthMode.DIRECT_PROVIDER,
            ExecutorAuthMode.LOCAL_MODEL,
            ExecutorAuthMode.GATEWAY_BASE_URL,
        ),
        release_posture=ExecutorReleasePosture.OPTIONAL,
        supports_direct_provider_config=True,
        supports_local_models=True,
        supports_gateway_base_url_routing=True,
        supports_structured_escalations=True,
    ),
)

_EXECUTOR_REGISTRY_BY_ID = {
    entry.executor_id: entry for entry in _EXECUTOR_REGISTRY
}


def get_executor_registry() -> tuple[ExecutorRegistryEntry, ...]:
    return _EXECUTOR_REGISTRY


def get_executor_entry(executor_id: ExecutorId | str) -> ExecutorRegistryEntry:
    normalized = _normalize_executor_id(executor_id)
    try:
        return _EXECUTOR_REGISTRY_BY_ID[normalized]
    except KeyError as exc:
        raise KeyError(f"unknown executor: {normalized.value}") from exc


def is_supported_executor(executor_id: ExecutorId | str) -> bool:
    try:
        get_executor_entry(executor_id)
    except KeyError:
        return False
    return True


__all__ = [
    "ExecutorId",
    "ExecutorReleasePosture",
    "ExecutorAuthMode",
    "ExecutorCapability",
    "ExecutorRegistryEntry",
    "get_executor_registry",
    "get_executor_entry",
    "is_supported_executor",
]
