"""Read-only, process-local Configuration Inspector endpoint.

This module projects a fixed subset of existing configuration owners. The
evidence strings are local response-schema vocabulary; they are not global
runtime protocol tokens.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from guardian.core.config import SUPPORTED_ROUTED_LLM_PROVIDERS, get_settings
from guardian.core.dependencies import require_operator_auth
from guardian.core.provider_registry import (
    default_model_for_provider,
    normalize_provider,
)

EvidenceClaim = Literal["declared", "resolved", "observed", "unavailable"]

_SAFE_ROUTE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
_SAFE_PROFILE_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,127}\Z")
_SAFE_MODEL_TARGET = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,179}\Z")

_PROFILE_OWNER = "guardian.core.supported_profile"
_ROUTE_OWNER = "guardian.guardian_api._refresh_supported_profile_state"
_PROVIDER_OWNER = "guardian.core.config.Settings+guardian.core.egress"
_LOCAL_TARGET_OWNER = "guardian.core.provider_registry.default_model_for_provider"


class InspectorModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProcessScope(InspectorModel):
    service: Literal["guardian"] = "guardian"
    process_id: int = Field(gt=0)
    scope: Literal["responding_guardian_process"] = "responding_guardian_process"


class SupportedProfileSection(InspectorModel):
    evidence: EvidenceClaim
    owner: Literal["guardian.core.supported_profile"] = _PROFILE_OWNER
    profile_name: str | None = Field(default=None, max_length=128)
    version: int | None = None
    surface_class: str | None = Field(default=None, max_length=128)
    valid: bool | None = None
    unavailable_reason: Literal["supported_profile_state_unavailable"] | None = None


class MountedRoutesSection(InspectorModel):
    evidence: EvidenceClaim
    owner: Literal[
        "guardian.guardian_api._refresh_supported_profile_state"
    ] = _ROUTE_OWNER
    route_families: list[str] | None = None
    interpretation: Literal[
        "mounted_only_not_authorization_health_or_release_support"
    ] = "mounted_only_not_authorization_health_or_release_support"
    unavailable_reason: Literal["mounted_route_inventory_unavailable"] | None = None


class ProviderEgressSection(InspectorModel):
    evidence: EvidenceClaim
    owner: Literal["guardian.core.config.Settings+guardian.core.egress"] = (
        _PROVIDER_OWNER
    )
    configured_provider_class: str | None = Field(default=None, max_length=40)
    local_only_mode: bool | None = None
    cloud_providers_allowed: bool | None = None
    egress_allowlist_configured: bool | None = None
    unavailable_reason: Literal["provider_egress_posture_unavailable"] | None = None


class LocalInferenceSection(InspectorModel):
    evidence: EvidenceClaim
    owner: Literal[
        "guardian.core.provider_registry.default_model_for_provider"
    ] = _LOCAL_TARGET_OWNER
    provider_class: Literal["local"] = "local"
    configured_target: str | None = Field(default=None, max_length=180)
    unavailable_reason: Literal["local_inference_target_unavailable"] | None = None


class ConfigurationSnapshot(InspectorModel):
    schema_version: Literal[1] = 1
    generated_at: datetime
    process: ProcessScope
    supported_profile: SupportedProfileSection
    mounted_routes: MountedRoutesSection
    provider_egress: ProviderEgressSection
    local_inference: LocalInferenceSection


router = APIRouter(
    prefix="/api/operator",
    tags=["operator"],
    dependencies=[Depends(require_operator_auth)],
)


def _safe_profile_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized or not _SAFE_PROFILE_VALUE.fullmatch(normalized):
        return None
    return normalized


def _supported_profile_section(state: object) -> SupportedProfileSection:
    unavailable = SupportedProfileSection(
        evidence="unavailable",
        unavailable_reason="supported_profile_state_unavailable",
    )
    if not isinstance(state, dict):
        return unavailable

    name = _safe_profile_value(state.get("name"))
    surface = _safe_profile_value(state.get("surface"))
    version = state.get("version")
    valid = state.get("valid")
    if (
        name is None
        or surface is None
        or not isinstance(version, int)
        or isinstance(version, bool)
        or version < 1
        or not isinstance(valid, bool)
    ):
        return unavailable

    return SupportedProfileSection(
        evidence="resolved",
        profile_name=name,
        version=version,
        surface_class=surface,
        valid=valid,
    )


def _mounted_routes_section(state: object) -> MountedRoutesSection:
    unavailable = MountedRoutesSection(
        evidence="unavailable",
        unavailable_reason="mounted_route_inventory_unavailable",
    )
    if not isinstance(state, dict):
        return unavailable
    routes = state.get("routes")
    if not isinstance(routes, dict):
        return unavailable
    mounted = routes.get("mounted")
    if not isinstance(mounted, list) or len(mounted) > 128:
        return unavailable

    labels: list[str] = []
    for item in mounted:
        if not isinstance(item, str):
            return unavailable
        label = item.strip()
        if not _SAFE_ROUTE_LABEL.fullmatch(label):
            return unavailable
        labels.append(label)

    return MountedRoutesSection(
        evidence="observed",
        route_families=sorted(set(labels)),
    )


def _provider_egress_section() -> ProviderEgressSection:
    unavailable = ProviderEgressSection(
        evidence="unavailable",
        unavailable_reason="provider_egress_posture_unavailable",
    )
    try:
        settings = get_settings()
        provider = normalize_provider(getattr(settings, "LLM_PROVIDER", None))
        local_only = getattr(settings, "CODEXIFY_LOCAL_ONLY_MODE", None)
        cloud_allowed = getattr(settings, "ALLOW_CLOUD_PROVIDERS", None)
        allowlist = getattr(settings, "CODEXIFY_EGRESS_ALLOWLIST", None)
        if (
            provider not in SUPPORTED_ROUTED_LLM_PROVIDERS
            or not isinstance(local_only, bool)
            or not isinstance(cloud_allowed, bool)
            or not isinstance(allowlist, str)
        ):
            return unavailable
        allowlist_configured = any(
            entry.strip() for entry in allowlist.split(",")
        )
    except Exception:
        return unavailable

    return ProviderEgressSection(
        evidence="resolved",
        configured_provider_class=provider,
        local_only_mode=local_only,
        cloud_providers_allowed=cloud_allowed,
        egress_allowlist_configured=allowlist_configured,
    )


def _safe_model_target(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if (
        not normalized
        or not _SAFE_MODEL_TARGET.fullmatch(normalized)
        or "://" in normalized
        or normalized.startswith(("/", "."))
        or "\\" in normalized
        or ".." in normalized.split("/")
    ):
        return None
    return normalized


def _local_inference_section() -> LocalInferenceSection:
    try:
        settings = get_settings()
        target = _safe_model_target(default_model_for_provider("local", settings))
    except Exception:
        target = None
    if target is None:
        return LocalInferenceSection(
            evidence="unavailable",
            unavailable_reason="local_inference_target_unavailable",
        )
    return LocalInferenceSection(evidence="resolved", configured_target=target)


@router.get("/configuration", response_model=ConfigurationSnapshot)
def get_configuration_snapshot(request: Request) -> ConfigurationSnapshot:
    """Return a bounded snapshot of the responding Guardian process."""
    state = getattr(request.app.state, "supported_profile", None)
    return ConfigurationSnapshot(
        generated_at=datetime.now(timezone.utc),
        process=ProcessScope(process_id=os.getpid()),
        supported_profile=_supported_profile_section(state),
        mounted_routes=_mounted_routes_section(state),
        provider_egress=_provider_egress_section(),
        local_inference=_local_inference_section(),
    )
