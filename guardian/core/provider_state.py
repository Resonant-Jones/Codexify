"""Provider state sync helpers for inference provider control-plane rows."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from guardian.db.models import InferenceProvider, InferenceProviderRuntime

LAUNCH_PROVIDER_IDS: tuple[str, ...] = (
    "openai",
    "anthropic",
    "gemini",
    "groq",
    "alibaba",
    "local",
)

_DISPLAY_NAMES: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "groq": "Groq",
    "alibaba": "Alibaba / DashScope",
    "local": "Local",
}

# Lower values are higher priority.
_PROVIDER_PRIORITY: dict[str, int] = {
    "groq": 10,
    "local": 20,
    "openai": 30,
    "anthropic": 40,
    "gemini": 50,
    "alibaba": 60,
}


def _provider_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    providers = catalog.get("providers")
    if not isinstance(providers, list):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for raw in providers:
        if not isinstance(raw, dict):
            continue
        provider_id = str(raw.get("id") or "").strip().lower()
        if not provider_id:
            continue
        result[provider_id] = raw
    return result


def _first_model_id(provider: dict[str, Any]) -> str | None:
    models = provider.get("models")
    if not isinstance(models, list):
        return None
    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = str(model.get("id") or "").strip()
        if model_id:
            return model_id
    return None


def _provider_capabilities(provider: dict[str, Any]) -> dict[str, bool]:
    models = provider.get("models")
    if not isinstance(models, list):
        return {}

    capabilities: dict[str, bool] = {}
    for model in models:
        if not isinstance(model, dict):
            continue
        caps = model.get("capabilities")
        if not isinstance(caps, dict):
            continue
        for key, value in caps.items():
            if not isinstance(value, bool):
                continue
            existing = capabilities.get(str(key), False)
            capabilities[str(key)] = bool(existing or value)
    return capabilities


def _provider_metadata(provider: dict[str, Any]) -> dict[str, Any] | None:
    metadata: dict[str, Any] = {}

    if "authorized" in provider:
        metadata["authorized"] = bool(provider.get("authorized"))
    if "available" in provider:
        metadata["available"] = bool(provider.get("available"))

    disabled_reason = str(provider.get("disabled_reason") or "").strip()
    if disabled_reason:
        metadata["disabled_reason"] = disabled_reason

    return metadata or None


def provider_seed_rows_from_catalog(
    catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build deterministic provider seed rows from /api/llm/catalog payload.

    Only launch-scope providers are considered for this campaign.
    """
    providers = _provider_map(catalog)
    rows: list[dict[str, Any]] = []

    for provider_id in LAUNCH_PROVIDER_IDS:
        source = providers.get(provider_id, {})
        display_name = str(
            source.get("displayName")
            or source.get("label")
            or _DISPLAY_NAMES.get(provider_id, provider_id.title())
        ).strip()
        if not display_name:
            display_name = _DISPLAY_NAMES.get(provider_id, provider_id.title())

        rows.append(
            {
                "provider_id": provider_id,
                "display_name": display_name,
                "provider_type": provider_id,
                "enabled": bool(source.get("enabled", False)),
                "priority": int(_PROVIDER_PRIORITY.get(provider_id, 100)),
                "default_model_id": _first_model_id(source),
                "capabilities": _provider_capabilities(source),
                "metadata": _provider_metadata(source),
            }
        )

    return rows


def sync_inference_provider_rows(
    session: Session,
    rows: list[dict[str, Any]],
) -> dict[str, int]:
    """
    Upsert provider config rows and ensure runtime rows exist.

    Runtime status is only initialized on first insert and is not reset on
    subsequent syncs.
    """
    providers_created = 0
    providers_updated = 0
    runtime_created = 0

    for row in rows:
        provider_id = str(row.get("provider_id") or "").strip().lower()
        if not provider_id:
            continue

        provider = session.get(InferenceProvider, provider_id)
        if provider is None:
            provider = InferenceProvider(
                provider_id=provider_id,
                display_name=str(row.get("display_name") or provider_id),
                provider_type=str(row.get("provider_type") or provider_id),
                enabled=bool(row.get("enabled", False)),
                priority=int(row.get("priority", 100)),
                default_model_id=row.get("default_model_id"),
                capabilities=dict(row.get("capabilities") or {}),
                provider_metadata=row.get("metadata"),
            )
            session.add(provider)
            providers_created += 1
        else:
            provider.display_name = str(
                row.get("display_name") or provider.display_name or provider_id
            )
            provider.provider_type = str(
                row.get("provider_type")
                or provider.provider_type
                or provider_id
            )
            provider.enabled = bool(row.get("enabled", False))
            provider.priority = int(
                row.get("priority", provider.priority or 100)
            )
            provider.default_model_id = row.get("default_model_id")
            provider.capabilities = dict(row.get("capabilities") or {})
            provider.provider_metadata = row.get("metadata")
            providers_updated += 1

        runtime = session.get(InferenceProviderRuntime, provider_id)
        if runtime is None:
            session.add(
                InferenceProviderRuntime(
                    provider_id=provider_id,
                    health_status="unknown",
                    consecutive_failures=0,
                )
            )
            runtime_created += 1

    session.flush()

    return {
        "provider_rows": len(rows),
        "providers_created": providers_created,
        "providers_updated": providers_updated,
        "runtime_created": runtime_created,
    }
