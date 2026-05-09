"""Shared provider truth helpers for catalog, health, and runtime metadata."""

from __future__ import annotations

from typing import Any

from guardian.core.config import Settings
from guardian.core.provider_registry import (
    normalize_provider,
    provider_egress_allowed,
    resolve_provider_capability,
    supported_profile_posture,
)


def provider_configured(provider_id: str | None, settings: Settings) -> bool:
    provider = normalize_provider(provider_id)
    if provider == "local":
        return bool(str(getattr(settings, "LOCAL_BASE_URL", "") or "").strip())
    if provider == "openai":
        return bool(str(getattr(settings, "OPENAI_API_KEY", "") or "").strip())
    if provider == "groq":
        return bool(str(getattr(settings, "GROQ_API_KEY", "") or "").strip())
    if provider == "alibaba":
        return bool(
            str(getattr(settings, "ALIBABA_API_KEY", "") or "").strip()
            and str(getattr(settings, "ALIBABA_API_BASE", "") or "").strip()
        )
    if provider == "minimax":
        return bool(
            str(getattr(settings, "MINIMAX_API_KEY", "") or "").strip()
            and str(getattr(settings, "MINIMAX_API_BASE", "") or "").strip()
        )
    if provider == "anthropic":
        return bool(
            str(getattr(settings, "ANTHROPIC_API_KEY", "") or "").strip()
        )
    if provider == "gemini":
        return bool(str(getattr(settings, "GEMINI_API_KEY", "") or "").strip())
    return False


def _cloud_capable_configuration_present(settings: Settings) -> bool:
    """Return true only when a real cloud provider configuration is present.

    Bundled base URL defaults alone do not count as cloud-capable because they
    are part of the local configuration baseline, not an explicit cloud intent.
    """

    return any(
        provider_configured(provider_id, settings)
        for provider_id in ("openai", "groq", "alibaba", "minimax")
    )


def cloud_capable_configuration_present(settings: Settings) -> bool:
    """Public alias for the cloud-capability predicate."""

    return _cloud_capable_configuration_present(settings)


def build_provider_truth(
    provider_id: str | None,
    settings: Settings,
    *,
    capability: dict[str, Any] | None = None,
    discoverable: bool | None = None,
    selectable: bool | None = None,
    attempted: bool = False,
    executed: bool = False,
    completed: bool = False,
) -> dict[str, Any]:
    provider = normalize_provider(provider_id)
    runtime = capability or resolve_provider_capability(provider, settings)
    configured = provider_configured(provider, settings)
    authorized = bool(runtime.get("authorized"))
    posture = supported_profile_posture(settings)
    supported_profile_name = posture.get("name")
    supported_profile_valid = posture.get("valid")
    selected_provider = normalize_provider(posture.get("selected_provider"))
    supported_profile_approved: bool | None
    if supported_profile_name is None:
        supported_profile_approved = None
    else:
        supported_profile_approved = bool(
            supported_profile_valid and provider == selected_provider
        )
    if discoverable is None:
        if provider == "local":
            discoverable = configured
        else:
            discoverable = (
                str(
                    (runtime.get("model_index") or {}).get("state") or ""
                ).strip()
                == "available"
            )
    if selectable is None:
        selectable = bool(runtime.get("enabled"))
    return {
        "configured": configured,
        "authorized": authorized,
        "discovered_inventory": bool(discoverable),
        "discoverable": bool(discoverable),
        "selectable": bool(selectable),
        "executable": bool(runtime.get("enabled")),
        "egress_allowed": provider_egress_allowed(provider, settings),
        "supported_profile_name": supported_profile_name,
        "supported_profile_valid": supported_profile_valid,
        "supported_profile_mismatches": list(posture.get("mismatches") or []),
        "supported_profile_approved": supported_profile_approved,
        "cloud_capable_configuration_present": bool(
            posture.get("cloud_capable_configuration_present")
        ),
        "attempted": bool(attempted),
        "executed": bool(executed),
        "completed": bool(completed),
    }
