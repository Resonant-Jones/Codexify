"""Policy-aware provider/model catalog for the unified selector UI."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse

import requests

from guardian.core.ai_router import (
    _default_model_for_provider,
    _resolve_local_base,
    describe_local_runtime,
)
from guardian.core.config import Settings, get_settings
from guardian.core.egress import EgressDeniedError, assert_egress_allowed

_PROVIDER_ORDER = (
    "openai",
    "anthropic",
    "gemini",
    "groq",
    "minimax",
    "local",
)
_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "groq": "Groq",
    "minimax": "MiniMax",
    "local": "Local",
}

_STATIC_PROVIDER_MODELS: dict[str, tuple[dict[str, Any], ...]] = {
    "openai": (
        {
            "id": "gpt-4o",
            "displayName": "GPT-4o",
            "contextWindow": 128000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
        },
        {
            "id": "gpt-4.1-mini",
            "displayName": "GPT-4.1 Mini",
            "contextWindow": 128000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
        },
    ),
    "anthropic": (
        {
            "id": "claude-3-5-sonnet-latest",
            "displayName": "Claude 3.5 Sonnet",
            "contextWindow": 200000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
        },
        {
            "id": "claude-3-5-haiku-latest",
            "displayName": "Claude 3.5 Haiku",
            "contextWindow": 200000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
        },
    ),
    "gemini": (
        {
            "id": "gemini-1.5-pro",
            "displayName": "Gemini 1.5 Pro",
            "contextWindow": 1048576,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
        },
        {
            "id": "gemini-1.5-flash",
            "displayName": "Gemini 1.5 Flash",
            "contextWindow": 1048576,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
        },
    ),
    "groq": (
        {
            "id": "moonshotai-kimi-k2-instruct-9050",
            "displayName": "Kimi K2 Instruct",
            "contextWindow": 128000,
            "capabilities": {
                "vision": False,
                "tools": False,
                "streaming": True,
            },
        },
        {
            "id": "llama-3.1-70b-versatile",
            "displayName": "Llama 3.1 70B",
            "contextWindow": 128000,
            "capabilities": {
                "vision": False,
                "tools": False,
                "streaming": True,
            },
        },
    ),
}

_CLOUD_PROVIDERS = {"openai", "anthropic", "gemini", "groq", "minimax"}


def _catalog_timeout_seconds() -> float:
    raw = os.getenv("LLM_CATALOG_REQUEST_TIMEOUT_SECONDS", "1.5").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 1.5
    return max(0.2, value)


def _normalize_reason(message: str) -> str:
    text = str(message or "").strip()
    if "ALLOW_CLOUD_PROVIDERS" in text:
        return "Cloud providers disabled by config"
    if "CODEXIFY_LOCAL_ONLY_MODE=true" in text:
        return "Local-only mode enabled"
    if "CODEXIFY_EGRESS_ALLOWLIST" in text:
        return "Provider blocked by egress policy"
    return text or "Provider unavailable"


def _has_real_api_key(value: str | None) -> bool:
    return bool(value and value.strip())


def _env_secret(*keys: str) -> str:
    for key in keys:
        raw = os.getenv(key)
        if _has_real_api_key(raw):
            return str(raw).strip()
    return ""


def _is_authorized(provider_id: str, settings: Settings) -> bool:
    if provider_id == "local":
        return True
    if provider_id == "openai":
        return _has_real_api_key(
            str(getattr(settings, "OPENAI_API_KEY", "") or "")
        )
    if provider_id == "groq":
        return _has_real_api_key(
            str(getattr(settings, "GROQ_API_KEY", "") or "")
        )
    if provider_id == "minimax":
        has_key = _has_real_api_key(
            str(getattr(settings, "MINIMAX_API_KEY", "") or "")
        ) or _has_real_api_key(_env_secret("MINIMAX_API_KEY"))
        has_base = bool(
            str(getattr(settings, "MINIMAX_API_BASE", "") or "").strip()
            or _env_secret("MINIMAX_API_BASE")
        )
        return has_key and has_base
    if provider_id == "anthropic":
        return _has_real_api_key(_env_secret("ANTHROPIC_API_KEY"))
    if provider_id == "gemini":
        return _has_real_api_key(
            _env_secret("GEMINI_API_KEY", "GENAI_API_KEY", "GOOGLE_API_KEY")
        )
    return False


def _base_model_entry(
    model_id: str,
    display_name: str | None = None,
    context_window: int | None = None,
    capabilities: dict[str, bool] | None = None,
) -> dict[str, Any]:
    clean_id = str(model_id or "").strip()
    clean_name = str(display_name or clean_id).strip() or clean_id
    entry: dict[str, Any] = {
        "id": clean_id,
        "displayName": clean_name,
        # backward compatibility for existing frontend readers
        "label": clean_name,
    }
    if isinstance(context_window, int) and context_window > 0:
        entry["contextWindow"] = context_window
    if capabilities:
        entry["capabilities"] = {
            key: bool(value)
            for key, value in capabilities.items()
            if isinstance(value, bool)
        }
    return entry


def _parse_local_models_payload(payload: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(payload, dict):
        return names

    for key in ("models", "data"):
        candidate = payload.get(key)
        if not isinstance(candidate, list):
            continue
        for item in candidate:
            if isinstance(item, str):
                model_name = item.strip()
            elif isinstance(item, dict):
                model_name = str(
                    item.get("name")
                    or item.get("model")
                    or item.get("id")
                    or ""
                ).strip()
            else:
                model_name = ""
            if model_name:
                names.append(model_name)
    return names


def _fetch_local_models(settings: Settings) -> list[dict[str, Any]]:
    timeout = _catalog_timeout_seconds()
    names: list[str] = []

    try:
        local_base_v1 = _resolve_local_base(settings)
        local_base = (
            local_base_v1[:-3]
            if local_base_v1.endswith("/v1")
            else local_base_v1
        )
        for url in (f"{local_base}/api/tags", f"{local_base_v1}/models"):
            try:
                response = requests.get(url, timeout=timeout)
            except Exception:
                continue
            if not (200 <= response.status_code < 300):
                continue
            try:
                payload = response.json()
            except Exception:
                continue
            names.extend(_parse_local_models_payload(payload))
            if names:
                break
    except Exception:
        pass

    if not names:
        fallback = (
            str(settings.LOCAL_LLM_MODEL or "").strip()
            or str(settings.DEFAULT_LOCAL_MODEL or "").strip()
            or str(settings.LLM_MODEL or "").strip()
        )
        if fallback:
            names = [fallback]

    deduped: list[str] = []
    seen: set[str] = set()
    for model_name in names:
        key = model_name.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    entries: list[dict[str, Any]] = []
    for name in deduped:
        entry = _base_model_entry(name)
        entry["runtime"] = describe_local_runtime(name, settings=settings)
        entries.append(entry)
    return entries


def _cloud_models(provider_id: str, settings: Settings) -> list[dict[str, Any]]:
    static_models = list(_STATIC_PROVIDER_MODELS.get(provider_id, ()))
    try:
        default_model = str(
            _default_model_for_provider(provider_id, settings) or ""
        ).strip()
    except Exception:
        default_model = ""

    existing_model_ids = {
        str(entry.get("id") or "").strip() for entry in static_models
    }
    if default_model and default_model not in existing_model_ids:
        static_models.insert(
            0, {"id": default_model, "displayName": default_model}
        )

    entries: list[dict[str, Any]] = []
    for item in static_models:
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            continue
        entries.append(
            _base_model_entry(
                model_id=model_id,
                display_name=str(item.get("displayName") or model_id).strip(),
                context_window=(
                    int(item["contextWindow"])
                    if isinstance(item.get("contextWindow"), int)
                    else None
                ),
                capabilities=(
                    item.get("capabilities")
                    if isinstance(item.get("capabilities"), dict)
                    else None
                ),
            )
        )
    return entries


def _provider_models(
    provider_id: str, settings: Settings
) -> list[dict[str, Any]]:
    if provider_id == "local":
        return _fetch_local_models(settings)
    if provider_id == "minimax":
        model_id = (
            str(getattr(settings, "MINIMAX_MODEL", "") or "").strip()
            or _env_secret("MINIMAX_MODEL")
            or "minimax-default"
        )
        return [
            _base_model_entry(
                model_id=model_id,
                display_name="MiniMax (default)",
            )
        ]
    return _cloud_models(provider_id, settings)


def _source_label(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.netloc:
        return parsed.netloc
    if parsed.path:
        return parsed.path.rstrip("/")
    return base_url.rstrip("/")


def _provider_source(
    provider_id: str, settings: Settings
) -> dict[str, Any] | None:
    if provider_id != "local":
        return None
    try:
        base_url = _resolve_local_base(settings)
    except Exception:
        return None

    parsed = urlparse(base_url)
    source: dict[str, Any] = {
        "kind": "local",
        "baseUrl": base_url,
        "label": _source_label(base_url),
    }
    if parsed.hostname:
        source["host"] = parsed.hostname
    if parsed.port:
        source["port"] = parsed.port
    return source


def _provider_availability(
    provider_id: str,
    settings: Settings,
    authorized: bool,
) -> tuple[bool, str | None]:
    if provider_id in _CLOUD_PROVIDERS and not authorized:
        return False, "Missing provider credentials"

    if provider_id in _CLOUD_PROVIDERS:
        if not bool(getattr(settings, "ALLOW_CLOUD_PROVIDERS", True)):
            return False, "Cloud providers disabled by config"
        try:
            assert_egress_allowed(provider_id, settings=settings)
        except EgressDeniedError as exc:
            return False, _normalize_reason(str(exc))
        return True, None

    # local provider
    try:
        _resolve_local_base(settings)
    except Exception as exc:
        return False, _normalize_reason(str(exc))
    return True, None


def _provider_entry(
    provider_id: str,
    settings: Settings,
    include_all: bool,
) -> dict[str, Any] | None:
    authorized = _is_authorized(provider_id, settings)
    if not include_all and provider_id != "local" and not authorized:
        return None

    available, disabled_reason = _provider_availability(
        provider_id, settings, authorized
    )
    enabled = bool(available) and bool(authorized)
    if provider_id == "local":
        enabled = bool(available)

    entry: dict[str, Any] = {
        "id": provider_id,
        "displayName": _PROVIDER_LABELS.get(provider_id, provider_id.title()),
        "enabled": enabled,
        # backward compatibility fields used by existing callers
        "label": _PROVIDER_LABELS.get(provider_id, provider_id.title()),
        "authorized": authorized,
        "available": available,
        "models": _provider_models(provider_id, settings),
    }
    source = _provider_source(provider_id, settings)
    if source is not None:
        entry["source"] = source
    if not available and disabled_reason:
        entry["disabled_reason"] = disabled_reason
    return entry


def build_llm_catalog(
    *,
    settings: Settings | None = None,
    include_all: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    resolved = settings or get_settings()
    providers: list[dict[str, Any]] = []
    for provider_id in _PROVIDER_ORDER:
        entry = _provider_entry(provider_id, resolved, include_all)
        if entry is not None:
            providers.append(entry)
    return {"providers": providers}


def resolve_provider_for_model(
    model_id: str | None,
    *,
    settings: Settings | None = None,
) -> str | None:
    candidate = str(model_id or "").strip()
    if not candidate:
        return None

    catalog = build_llm_catalog(settings=settings, include_all=True)
    for provider in catalog.get("providers", []):
        if not provider.get("enabled"):
            continue
        for model in provider.get("models", []):
            if str(model.get("id") or "").strip() == candidate:
                return str(provider.get("id") or "").strip() or None
    return None


def first_enabled_provider(*, settings: Settings | None = None) -> str | None:
    catalog = build_llm_catalog(settings=settings, include_all=True)
    for provider in catalog.get("providers", []):
        if provider.get("enabled"):
            resolved = str(provider.get("id") or "").strip()
            if resolved:
                return resolved
    return None


def first_model_for_provider(
    provider_id: str | None,
    *,
    settings: Settings | None = None,
) -> str | None:
    target = str(provider_id or "").strip().lower()
    if not target:
        return None

    catalog = build_llm_catalog(settings=settings, include_all=True)
    for provider in catalog.get("providers", []):
        if str(provider.get("id") or "").strip().lower() != target:
            continue
        if not provider.get("enabled"):
            return None
        models = provider.get("models")
        if not isinstance(models, list) or not models:
            return None
        first = str(models[0].get("id") or "").strip()
        return first or None
    return None
