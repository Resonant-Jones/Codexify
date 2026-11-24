"""Per-attempt native thinking effort for ordinary Guardian Chat."""

from typing import Any

from fastapi import HTTPException

from guardian.core.config import Settings
from guardian.core.provider_registry import (
    provider_availability,
    resolve_provider_capability,
    supported_profile_posture,
)
from guardian.providers.deepseek_adapter import NATIVE_EFFORT_LEVELS, thinking_enabled


def effort_route_available(
    provider: str,
    model: str | None,
    settings: Settings | None,
    capability: dict[str, Any] | None = None,
    *,
    check_inventory: bool = False,
) -> bool:
    if (
        settings is None
        or provider != "deepseek"
        or model != "deepseek-flash"
        or str(settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com")
        .strip()
        .rstrip("/")
        != "https://api.deepseek.com"
        or settings.CODEXIFY_EGRESS_ALLOWLIST != "deepseek,deepgram"
    ):
        return False
    posture = supported_profile_posture(settings)
    if posture["name"] != "v1-whooshd-deepseek-web" or not posture["valid"]:
        return False
    if capability is None and not check_inventory:
        return provider_availability(provider, settings)[0]
    route = (
        capability
        if capability is not None
        else resolve_provider_capability(provider, settings)
    )
    return bool(
        route["authorized"]
        and route["enabled"]
        and route["model_index"]["state"] == "available"
        and any(
            row["id"] == model and row.get("supports_chat") for row in route["models"]
        )
    )


def validate_effort(
    effort: str | None,
    provider: str,
    model: str | None,
    mode: str | None,
    settings: Settings | None,
    *,
    check_inventory: bool = False,
) -> None:
    if effort is None:
        return
    if (
        effort not in (*NATIVE_EFFORT_LEVELS, "default")
        or not thinking_enabled(mode)
        or not effort_route_available(
            provider, model, settings, check_inventory=check_inventory
        )
    ):
        raise HTTPException(
            status_code=409,
            detail="Thinking effort is unavailable on this route or mode. Select provider default and retry.",
        )
