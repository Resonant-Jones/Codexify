"""Compose a policy-aware LLM provider/model catalog for UI consumption."""

from __future__ import annotations

import os
from typing import Any

import requests

from guardian.core.ai_router import (
    _default_model_for_provider,
    _resolve_local_base,
)
from guardian.core.config import (
    LLMConfigError,
    Settings,
    get_settings,
    validate_llm_config,
)
from guardian.core.egress import EgressDeniedError, assert_egress_allowed

_PROVIDER_ORDER = ("local", "groq", "openai")
_PROVIDER_LABELS = {
    "local": "Local",
    "groq": "Groq",
    "openai": "OpenAI",
}

_STATIC_CLOUD_MODELS: dict[str, tuple[str, ...]] = {
    "groq": ("llama-3.1-70b-versatile", "moonshotai-kimi-k2-instruct-9050"),
    "openai": ("gpt-4o", "gpt-4.1-mini"),
}


def _model_entry(model_id: str) -> dict[str, str]:
    text = str(model_id or "").strip()
    return {"id": text, "label": text}


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
    if "API_KEY" in text and "not configured" in text:
        return "Missing provider credentials"
    return text or "Provider unavailable"


def _is_authorized(provider_id: str, settings: Settings) -> bool:
    if provider_id == "local":
        return True
    if provider_id == "groq":
        return bool(str(settings.GROQ_API_KEY or "").strip())
    if provider_id == "openai":
        return bool(str(settings.OPENAI_API_KEY or "").strip())
    return False


def _parse_local_models_payload(payload: Any) -> list[str]:
    names: list[str] = []
    if isinstance(payload, dict):
        models = payload.get("models")
        if isinstance(models, list):
            for item in models:
                if isinstance(item, str):
                    candidate = item.strip()
                elif isinstance(item, dict):
                    candidate = str(
                        item.get("name") or item.get("model") or ""
                    ).strip()
                else:
                    candidate = ""
                if candidate:
                    names.append(candidate)

        data = payload.get("data")
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                candidate = str(item.get("id") or "").strip()
                if candidate:
                    names.append(candidate)
    return names


def _fetch_local_models(settings: Settings) -> list[dict[str, str]]:
    timeout = _catalog_timeout_seconds()
    names: list[str] = []

    try:
        local_base_v1 = _resolve_local_base(settings)
        base = (
            local_base_v1[:-3]
            if local_base_v1.endswith("/v1")
            else local_base_v1
        )
        for url in (f"{base}/api/tags", f"{local_base_v1}/models"):
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
    return [_model_entry(name) for name in deduped]


def _cloud_models(provider_id: str, settings: Settings) -> list[dict[str, str]]:
    static_models = list(_STATIC_CLOUD_MODELS.get(provider_id, ()))
    default_model = str(
        _default_model_for_provider(provider_id, settings) or ""
    ).strip()
    if default_model and default_model not in static_models:
        static_models.insert(0, default_model)
    return [_model_entry(model_id) for model_id in static_models]


def _provider_models(
    provider_id: str, settings: Settings
) -> list[dict[str, str]]:
    if provider_id == "local":
        return _fetch_local_models(settings)
    return _cloud_models(provider_id, settings)


def _provider_availability(
    provider_id: str, settings: Settings, authorized: bool
) -> tuple[bool, str | None]:
    if provider_id != "local" and not authorized:
        return False, "Missing provider credentials"

    try:
        validate_llm_config(settings, provider_override=provider_id)
    except LLMConfigError as exc:
        return False, _normalize_reason(str(exc))

    if provider_id in {"groq", "openai"}:
        try:
            assert_egress_allowed(provider_id, settings=settings)
        except EgressDeniedError as exc:
            return False, _normalize_reason(str(exc))

    return True, None


def build_llm_catalog(
    *, settings: Settings | None = None, include_all: bool = False
) -> dict[str, list[dict[str, Any]]]:
    resolved = settings or get_settings()
    providers: list[dict[str, Any]] = []

    for provider_id in _PROVIDER_ORDER:
        authorized = _is_authorized(provider_id, resolved)
        if not include_all and provider_id != "local" and not authorized:
            continue

        available, disabled_reason = _provider_availability(
            provider_id, resolved, authorized
        )
        entry: dict[str, Any] = {
            "id": provider_id,
            "label": _PROVIDER_LABELS[provider_id],
            "authorized": authorized,
            "available": available,
            "models": _provider_models(provider_id, resolved),
        }
        if not available and disabled_reason:
            entry["disabled_reason"] = disabled_reason
        providers.append(entry)

    return {"providers": providers}
