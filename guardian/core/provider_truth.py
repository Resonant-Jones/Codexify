"""Shared provider truth helpers for catalog, health, and runtime metadata."""

from __future__ import annotations

from typing import Any

from guardian.core.config import Settings
from guardian.core.provider_registry import (
    normalize_provider,
    resolve_provider_capability,
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
        "discoverable": bool(discoverable),
        "selectable": bool(selectable),
        "attempted": bool(attempted),
        "executed": bool(executed),
        "completed": bool(completed),
    }
