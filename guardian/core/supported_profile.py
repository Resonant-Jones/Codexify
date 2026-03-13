"""Supported runtime profile loader and validation helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

SUPPORTED_PROFILE_ENV = "CODEXIFY_SUPPORTED_PROFILE"
SUPPORTED_PROFILE_DIR_ENV = "CODEXIFY_SUPPORTED_PROFILE_DIR"
DEFAULT_SUPPORTED_PROFILE_NAME = "v1-local-core-web-mcp"
DEFAULT_SUPPORTED_PROFILE_DIR = "config/supported_profiles"


class SupportedProfileError(ValueError):
    """Raised when a supported profile is invalid or mismatched."""


@dataclass(frozen=True)
class SupportedProfileManifest:
    name: str
    version: int
    surface: str
    required_services: tuple[str, ...]
    optional_services: tuple[str, ...]
    public_extensions: tuple[str, ...]
    internal_extensions: tuple[str, ...]
    enabled_routes: tuple[str, ...]
    internal_only_routes: tuple[str, ...]
    quarantined_routes: tuple[str, ...]
    provider_contract: dict[str, Any]
    criticality: dict[str, dict[str, tuple[str, ...]]]

    def route_status(self, label: str) -> str:
        normalized = str(label or "").strip()
        if normalized in self.quarantined_routes:
            return "quarantined"
        if normalized in self.internal_only_routes:
            return "internal_only"
        if normalized in self.enabled_routes:
            return "enabled"
        return "quarantined"

    def allows_route(self, label: str) -> bool:
        return self.route_status(label) != "quarantined"

    def route_summary(self) -> dict[str, str]:
        labels = (
            list(self.enabled_routes)
            + list(self.internal_only_routes)
            + list(self.quarantined_routes)
        )
        return {label: self.route_status(label) for label in labels}


def get_requested_supported_profile_name() -> str | None:
    raw = (os.getenv(SUPPORTED_PROFILE_ENV) or "").strip()
    return raw or None


def _resolve_profiles_dir(profiles_dir: str | None = None) -> Path:
    raw = (
        str(profiles_dir or os.getenv(SUPPORTED_PROFILE_DIR_ENV) or "").strip()
        or DEFAULT_SUPPORTED_PROFILE_DIR
    )
    path = Path(raw)
    if path.is_absolute():
        return path
    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / path


def _normalize_str_sequence(raw: Any, label: str) -> tuple[str, ...]:
    if raw is None:
        return tuple()
    if not isinstance(raw, list):
        raise SupportedProfileError(f"{label} must be a list")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise SupportedProfileError(
                f"{label} entries must be non-empty strings"
            )
        values.append(item.strip())
    return tuple(values)


def _normalize_criticality(raw: Any) -> dict[str, dict[str, tuple[str, ...]]]:
    if not isinstance(raw, dict):
        raise SupportedProfileError("criticality must be a mapping")
    normalized: dict[str, dict[str, tuple[str, ...]]] = {}
    for tier_name, payload in raw.items():
        if not isinstance(tier_name, str) or not tier_name.strip():
            raise SupportedProfileError(
                "criticality tier names must be strings"
            )
        if not isinstance(payload, dict):
            raise SupportedProfileError(
                f"criticality tier {tier_name!r} must be a mapping"
            )
        normalized[tier_name.strip()] = {
            "services": _normalize_str_sequence(
                payload.get("services"), f"criticality.{tier_name}.services"
            ),
            "routes": _normalize_str_sequence(
                payload.get("routes"), f"criticality.{tier_name}.routes"
            ),
        }
    return normalized


def _coerce_provider_contract(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SupportedProfileError("provider_contract must be a mapping")
    normalized: dict[str, Any] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise SupportedProfileError(
                "provider_contract keys must be non-empty strings"
            )
        normalized[key.strip()] = value
    return normalized


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SupportedProfileError(f"supported profile file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise SupportedProfileError("supported profile root must be a mapping")
    return payload


def _manifest_from_payload(payload: dict[str, Any]) -> SupportedProfileManifest:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise SupportedProfileError("name is required")
    version = payload.get("version")
    if not isinstance(version, int) or version < 1:
        raise SupportedProfileError("version must be a positive integer")
    surface = str(payload.get("surface") or "").strip()
    if not surface:
        raise SupportedProfileError("surface is required")

    extension_posture = payload.get("extension_posture")
    if not isinstance(extension_posture, dict):
        raise SupportedProfileError("extension_posture must be a mapping")

    route_posture = payload.get("route_posture")
    if not isinstance(route_posture, dict):
        raise SupportedProfileError("route_posture must be a mapping")

    enabled_routes = _normalize_str_sequence(
        route_posture.get("enabled"), "route_posture.enabled"
    )
    internal_only_routes = _normalize_str_sequence(
        route_posture.get("internal_only"), "route_posture.internal_only"
    )
    quarantined_routes = _normalize_str_sequence(
        route_posture.get("quarantined"), "route_posture.quarantined"
    )

    overlap = (
        set(enabled_routes) & set(internal_only_routes)
        or set(enabled_routes) & set(quarantined_routes)
        or set(internal_only_routes) & set(quarantined_routes)
    )
    if overlap:
        raise SupportedProfileError(
            f"route_posture contains overlapping labels: {sorted(overlap)!r}"
        )

    return SupportedProfileManifest(
        name=name,
        version=version,
        surface=surface,
        required_services=_normalize_str_sequence(
            payload.get("required_services"), "required_services"
        ),
        optional_services=_normalize_str_sequence(
            payload.get("optional_services"), "optional_services"
        ),
        public_extensions=_normalize_str_sequence(
            extension_posture.get("public"), "extension_posture.public"
        ),
        internal_extensions=_normalize_str_sequence(
            extension_posture.get("internal"), "extension_posture.internal"
        ),
        enabled_routes=enabled_routes,
        internal_only_routes=internal_only_routes,
        quarantined_routes=quarantined_routes,
        provider_contract=_coerce_provider_contract(
            payload.get("provider_contract")
        ),
        criticality=_normalize_criticality(payload.get("criticality")),
    )


@lru_cache(maxsize=16)
def load_supported_profile(
    profile_name: str,
    *,
    profiles_dir: str | None = None,
) -> SupportedProfileManifest:
    normalized_name = str(profile_name or "").strip()
    if not normalized_name:
        raise SupportedProfileError("profile_name is required")
    directory = _resolve_profiles_dir(profiles_dir)
    return _manifest_from_payload(
        _load_yaml(directory / f"{normalized_name}.yaml")
    )


def get_active_supported_profile() -> SupportedProfileManifest | None:
    profile_name = get_requested_supported_profile_name()
    if not profile_name:
        return None
    return load_supported_profile(profile_name)


def _normalize_expected(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return bool(value)
    return value


def supported_profile_actual_provider_contract(
    settings: Any,
) -> dict[str, Any]:
    local_chat_model = (
        str(getattr(settings, "LOCAL_CHAT_MODEL", "") or "").strip()
        or (os.getenv("LOCAL_CHAT_MODEL") or "").strip()
    )
    return {
        "LLM_PROVIDER": str(
            getattr(settings, "LLM_PROVIDER", "") or ""
        ).strip(),
        "ALLOW_CLOUD_PROVIDERS": bool(
            getattr(settings, "ALLOW_CLOUD_PROVIDERS", False)
        ),
        "CODEXIFY_LOCAL_ONLY_MODE": bool(
            getattr(settings, "CODEXIFY_LOCAL_ONLY_MODE", False)
        ),
        "CODEXIFY_EGRESS_ALLOWLIST": str(
            getattr(settings, "CODEXIFY_EGRESS_ALLOWLIST", "") or ""
        ).strip(),
        "LOCAL_BASE_URL": str(
            getattr(settings, "LOCAL_BASE_URL", "") or ""
        ).strip(),
        "LOCAL_API_KEY": str(
            getattr(settings, "LOCAL_API_KEY", "") or ""
        ).strip(),
        "LOCAL_LLM_MODEL": str(
            getattr(settings, "LOCAL_LLM_MODEL", "") or ""
        ).strip(),
        "LOCAL_CHAT_MODEL": local_chat_model
        or str(getattr(settings, "LOCAL_LLM_MODEL", "") or "").strip(),
    }


def validate_supported_profile_runtime(
    manifest: SupportedProfileManifest,
    *,
    settings: Any,
    enabled_routes: set[str] | None = None,
) -> list[str]:
    mismatches: list[str] = []
    actual_contract = supported_profile_actual_provider_contract(settings)
    for key, expected in manifest.provider_contract.items():
        actual = actual_contract.get(key)
        if _normalize_expected(actual) != _normalize_expected(expected):
            mismatches.append(
                f"{key} expected {expected!r} but found {actual!r}"
            )

    route_set = {
        str(label).strip()
        for label in (enabled_routes or set())
        if str(label).strip()
    }
    if route_set:
        for label in manifest.enabled_routes + manifest.internal_only_routes:
            if label not in route_set:
                mismatches.append(f"required route {label!r} is not mounted")
        for label in manifest.quarantined_routes:
            if label in route_set:
                mismatches.append(f"quarantined route {label!r} is mounted")

    return mismatches


def build_supported_profile_runtime_state(
    manifest: SupportedProfileManifest,
    *,
    settings: Any,
    enabled_routes: set[str] | None = None,
) -> dict[str, Any]:
    actual_contract = supported_profile_actual_provider_contract(settings)
    route_set = {
        str(label).strip()
        for label in (enabled_routes or set())
        if str(label).strip()
    }
    mismatches = validate_supported_profile_runtime(
        manifest, settings=settings, enabled_routes=route_set
    )
    route_summary = manifest.route_summary()
    mounted_routes = sorted(route_set) if route_set else []
    return {
        "name": manifest.name,
        "version": manifest.version,
        "surface": manifest.surface,
        "public_extensions": list(manifest.public_extensions),
        "internal_extensions": list(manifest.internal_extensions),
        "provider_contract": {
            "expected": dict(manifest.provider_contract),
            "actual": actual_contract,
        },
        "criticality": {
            tier: {
                "services": list(payload.get("services", ())),
                "routes": list(payload.get("routes", ())),
            }
            for tier, payload in manifest.criticality.items()
        },
        "routes": {
            "declared": route_summary,
            "mounted": mounted_routes,
        },
        "valid": len(mismatches) == 0,
        "mismatches": mismatches,
    }
