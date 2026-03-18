"""Canonical provider capability registry and resolver.

This module is the single source of truth for provider/model capability
decisions used by catalog, health, router, and worker code.
"""

from __future__ import annotations

from typing import Any, Iterable, Literal, TypedDict

import requests
from requests import exceptions as req_exc

from guardian.core.config import (
    SUPPORTED_ROUTED_LLM_PROVIDERS,
    LLMConfigError,
    Settings,
    validate_llm_config,
)
from guardian.core.egress import EgressDeniedError, assert_egress_allowed

ProviderGovernanceClassification = Literal[
    "discovery_backed",
    "static_authorized",
    "local_only",
    "disabled",
]


class ProviderGovernanceContract(TypedDict):
    provider: str
    display_name: str
    classification: ProviderGovernanceClassification
    live_discovery_expected: bool
    routing_requires_discovered_inventory: bool
    configured_defaults_allowed_on_discovery_failure: bool
    local_only: bool


PROVIDER_GOVERNANCE: dict[str, ProviderGovernanceContract] = {
    "openai": {
        "provider": "openai",
        "display_name": "OpenAI",
        "classification": "discovery_backed",
        "live_discovery_expected": True,
        "routing_requires_discovered_inventory": True,
        "configured_defaults_allowed_on_discovery_failure": True,
        "local_only": False,
    },
    "anthropic": {
        "provider": "anthropic",
        "display_name": "Anthropic",
        "classification": "disabled",
        "live_discovery_expected": False,
        "routing_requires_discovered_inventory": False,
        "configured_defaults_allowed_on_discovery_failure": False,
        "local_only": False,
    },
    "gemini": {
        "provider": "gemini",
        "display_name": "Gemini",
        "classification": "disabled",
        "live_discovery_expected": False,
        "routing_requires_discovered_inventory": False,
        "configured_defaults_allowed_on_discovery_failure": False,
        "local_only": False,
    },
    "groq": {
        "provider": "groq",
        "display_name": "Groq",
        "classification": "discovery_backed",
        "live_discovery_expected": True,
        "routing_requires_discovered_inventory": True,
        "configured_defaults_allowed_on_discovery_failure": True,
        "local_only": False,
    },
    "alibaba": {
        "provider": "alibaba",
        "display_name": "Alibaba / DashScope",
        "classification": "discovery_backed",
        "live_discovery_expected": True,
        "routing_requires_discovered_inventory": True,
        "configured_defaults_allowed_on_discovery_failure": True,
        "local_only": False,
    },
    "minimax": {
        "provider": "minimax",
        "display_name": "MiniMax",
        "classification": "discovery_backed",
        "live_discovery_expected": True,
        "routing_requires_discovered_inventory": True,
        "configured_defaults_allowed_on_discovery_failure": True,
        "local_only": False,
    },
    "local": {
        "provider": "local",
        "display_name": "Local",
        "classification": "local_only",
        "live_discovery_expected": True,
        "routing_requires_discovered_inventory": True,
        "configured_defaults_allowed_on_discovery_failure": True,
        "local_only": True,
    },
}

PROVIDER_ORDER = tuple(PROVIDER_GOVERNANCE)

PROVIDER_LABELS = {
    provider_id: contract["display_name"]
    for provider_id, contract in PROVIDER_GOVERNANCE.items()
}

DISCOVERY_BACKED_PROVIDERS = frozenset(
    provider_id
    for provider_id, contract in PROVIDER_GOVERNANCE.items()
    if contract["classification"] == "discovery_backed"
)
STATIC_AUTHORIZED_PROVIDERS = frozenset(
    provider_id
    for provider_id, contract in PROVIDER_GOVERNANCE.items()
    if contract["classification"] == "static_authorized"
)
LOCAL_ONLY_PROVIDERS = frozenset(
    provider_id
    for provider_id, contract in PROVIDER_GOVERNANCE.items()
    if contract["classification"] == "local_only"
)
DISABLED_PROVIDERS = frozenset(
    provider_id
    for provider_id, contract in PROVIDER_GOVERNANCE.items()
    if contract["classification"] == "disabled"
)
CLOUD_PROVIDERS = frozenset(
    provider_id
    for provider_id, contract in PROVIDER_GOVERNANCE.items()
    if not contract["local_only"]
)

_AUTO_MODEL_SENTINELS = {"", "auto"}
_VALIDATED_PROVIDER_SET = frozenset(SUPPORTED_ROUTED_LLM_PROVIDERS)
_DYNAMIC_MODEL_PROVIDERS = {"alibaba", "minimax"}
_MODEL_INDEX_NON_CHAT_HINTS = (
    "audio",
    "asr",
    "embedding",
    "embeddings",
    "image",
    "moderation",
    "music",
    "rerank",
    "speech",
    "transcription",
    "tts",
    "video",
)

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
            "id": "moonshotai/kimi-k2-instruct-0905",
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


def normalize_provider(provider: str | None) -> str:
    normalized = (provider or "").strip().lower()
    if normalized in {"", "auto"}:
        return "local"
    return normalized


def normalize_model_id(model_id: str | None) -> str:
    normalized = str(model_id or "").strip()
    if normalized.lower() in _AUTO_MODEL_SENTINELS:
        return ""
    return normalized


def _provider_governance(
    provider_id: str | None,
) -> ProviderGovernanceContract | None:
    return PROVIDER_GOVERNANCE.get(normalize_provider(provider_id))


def get_provider_governance(
    provider_id: str | None,
) -> ProviderGovernanceContract | None:
    contract = _provider_governance(provider_id)
    if contract is None:
        return None
    return dict(contract)


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


def _coerce_positive_timeout(raw: Any, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = float(default)
    return max(0.2, value)


def default_model_for_provider(provider_id: str, settings: Settings) -> str:
    provider = normalize_provider(provider_id)

    if provider == "local":
        candidates = (
            getattr(settings, "LOCAL_LLM_MODEL", None),
            getattr(settings, "LOCAL_CHAT_MODEL", None),
            getattr(settings, "DEFAULT_LOCAL_MODEL", None),
            getattr(settings, "LLM_MODEL", None),
        )
    elif provider == "groq":
        candidates = (
            getattr(settings, "GROQ_MODEL", None),
            getattr(settings, "DEFAULT_GROQ_MODEL", None),
        )
    elif provider == "openai":
        candidates = (
            getattr(settings, "OPENAI_MODEL", None),
            getattr(settings, "DEFAULT_OPENAI_MODEL", None),
        )
    elif provider == "alibaba":
        candidates = (getattr(settings, "ALIBABA_MODEL", None),)
    elif provider == "minimax":
        candidates = (getattr(settings, "MINIMAX_MODEL", None),)
    else:
        candidates = ()

    for candidate in candidates:
        normalized = normalize_model_id(candidate)
        if normalized:
            return normalized
    return ""


def _provider_model_index_timeout(
    provider_id: str,
    settings: Settings,
) -> float:
    provider = normalize_provider(provider_id)
    if provider == "alibaba":
        raw = getattr(settings, "ALIBABA_MODEL_DISCOVERY_TIMEOUT_SECONDS", 3.0)
    elif provider == "minimax":
        raw = getattr(settings, "MINIMAX_MODEL_DISCOVERY_TIMEOUT_SECONDS", 3.0)
    else:
        raw = 3.0
    return _coerce_positive_timeout(raw, 3.0)


def _provider_model_index_url(provider_id: str, settings: Settings) -> str:
    provider = normalize_provider(provider_id)
    override = ""
    base_url = ""

    if provider == "alibaba":
        override = str(
            getattr(settings, "ALIBABA_MODEL_DISCOVERY_URL", "") or ""
        ).strip()
        base_url = str(getattr(settings, "ALIBABA_API_BASE", "") or "").strip()
    elif provider == "minimax":
        override = str(
            getattr(settings, "MINIMAX_MODEL_DISCOVERY_URL", "") or ""
        ).strip()
        base_url = str(getattr(settings, "MINIMAX_API_BASE", "") or "").strip()

    if override:
        return override.rstrip("/")

    clean_base = base_url.rstrip("/")
    if not clean_base:
        return ""
    if clean_base.endswith("/models"):
        return clean_base
    if clean_base.endswith("/v1"):
        return f"{clean_base}/models"
    return f"{clean_base}/v1/models"


def _provider_model_index_headers(
    provider_id: str,
    settings: Settings,
) -> dict[str, str]:
    provider = normalize_provider(provider_id)
    headers = {"Accept": "application/json"}
    if provider == "alibaba":
        headers[
            "Authorization"
        ] = f"Bearer {str(getattr(settings, 'ALIBABA_API_KEY', '') or '').strip()}"
        return headers
    if provider == "minimax":
        api_key = str(getattr(settings, "MINIMAX_API_KEY", "") or "").strip()
        api_flavor = (
            str(getattr(settings, "MINIMAX_API_FLAVOR", "openai") or "")
            .strip()
            .lower()
            or "openai"
        )
        if api_flavor == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = (
                str(
                    getattr(settings, "MINIMAX_ANTHROPIC_VERSION", "2023-06-01")
                    or ""
                ).strip()
                or "2023-06-01"
            )
            return headers
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _model_index_metadata(
    state: str,
    *,
    endpoint: str | None = None,
    reason: str | None = None,
    model_count: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source": "live",
        "state": state,
    }
    if endpoint:
        payload["endpoint"] = endpoint
    if reason:
        payload["reason"] = reason
    if model_count is not None:
        payload["model_count"] = int(model_count)
    return payload


def _extract_model_index_collections(payload: Any) -> list[list[Any]]:
    if isinstance(payload, list):
        return [payload]
    if not isinstance(payload, dict):
        return []

    collections: list[list[Any]] = []
    for key in (
        "data",
        "models",
        "items",
        "list",
        "result",
        "results",
        "model_list",
    ):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            collections.append(candidate)
        elif isinstance(candidate, dict):
            collections.extend(_extract_model_index_collections(candidate))
    return collections


def _model_id_from_index_item(item: Any) -> str:
    if isinstance(item, str):
        return normalize_model_id(item)
    if not isinstance(item, dict):
        return ""
    for key in ("id", "model", "name", "model_id", "modelId"):
        candidate = normalize_model_id(item.get(key))
        if candidate:
            return candidate
    return ""


def _model_index_hint_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "type",
        "model_type",
        "category",
        "task",
        "tasks",
        "modality",
        "modalities",
        "endpoint",
        "endpoints",
        "ability",
        "abilities",
        "capability",
        "capabilities",
        "features",
        "feature_set",
    ):
        value = item.get(key)
        if isinstance(value, str):
            clean = value.strip()
            if clean:
                parts.append(clean)
        elif isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, bool) and nested_value:
                    parts.append(str(nested_key))
                elif isinstance(nested_value, str):
                    clean = nested_value.strip()
                    if clean:
                        parts.append(clean)
        elif isinstance(value, (list, tuple, set)):
            for nested_value in value:
                if isinstance(nested_value, str):
                    clean = nested_value.strip()
                    if clean:
                        parts.append(clean)
    return " ".join(parts).lower()


def _is_chat_model_index_item(item: dict[str, Any]) -> bool:
    hint_text = _model_index_hint_text(item)
    if not hint_text:
        return True
    return not any(hint in hint_text for hint in _MODEL_INDEX_NON_CHAT_HINTS)


def _extract_context_window(item: dict[str, Any]) -> int | None:
    for key in (
        "contextWindow",
        "context_window",
        "max_context_tokens",
        "maxContextTokens",
        "context_length",
        "contextLength",
    ):
        raw = item.get(key)
        if isinstance(raw, bool):
            continue
        if isinstance(raw, int):
            if raw > 0:
                return raw
            continue
        if isinstance(raw, float):
            if raw > 0:
                return int(raw)
            continue
        if isinstance(raw, str) and raw.strip().isdigit():
            return int(raw.strip())
    return None


def _extract_capabilities(item: dict[str, Any]) -> dict[str, bool] | None:
    raw = item.get("capabilities")
    if not isinstance(raw, dict):
        return None
    capabilities = {
        str(key): bool(value)
        for key, value in raw.items()
        if isinstance(value, bool)
    }
    return capabilities or None


def _parse_dynamic_model_descriptors(
    payload: Any,
) -> tuple[list[dict[str, Any]], bool]:
    collections = _extract_model_index_collections(payload)
    if not collections:
        return [], False

    models: list[dict[str, Any]] = []
    seen: set[str] = set()

    for collection in collections:
        for item in collection:
            model_id = _model_id_from_index_item(item)
            if not model_id or model_id in seen:
                continue
            if isinstance(item, dict) and not _is_chat_model_index_item(item):
                continue

            descriptor: dict[str, Any] = {
                "id": model_id,
                "displayName": (
                    str(
                        item.get("displayName") or item.get("name") or model_id
                    ).strip()
                    if isinstance(item, dict)
                    else model_id
                ),
            }
            if isinstance(item, dict):
                context_window = _extract_context_window(item)
                if context_window is not None:
                    descriptor["contextWindow"] = context_window
                capabilities = _extract_capabilities(item)
                if capabilities:
                    descriptor["capabilities"] = capabilities

            seen.add(model_id)
            models.append(descriptor)

    return models, True


def _discover_dynamic_provider_models(
    provider_id: str,
    settings: Settings,
    *,
    available: bool,
    disabled_reason: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    provider = normalize_provider(provider_id)
    endpoint = _provider_model_index_url(provider, settings)

    if not available:
        return [], _model_index_metadata(
            "unavailable",
            endpoint=endpoint or None,
            reason=disabled_reason or "Provider unavailable",
        )

    if not endpoint:
        return [], _model_index_metadata(
            "unavailable",
            reason="Provider model index URL is not configured",
        )

    try:
        response = requests.get(
            endpoint,
            headers=_provider_model_index_headers(provider, settings),
            timeout=_provider_model_index_timeout(provider, settings),
        )
    except req_exc.Timeout:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason="Provider model index request timed out",
        )
    except req_exc.RequestException as exc:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason=f"Provider model index request failed: {type(exc).__name__}",
        )

    if not (200 <= response.status_code < 300):
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason=(
                "Provider model index request failed "
                f"(HTTP {response.status_code})"
            ),
        )

    try:
        payload = response.json()
    except ValueError:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason="Provider model index returned invalid JSON",
        )

    models, recognized_payload = _parse_dynamic_model_descriptors(payload)
    if not recognized_payload:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason="Provider model index payload was invalid",
        )
    if not models:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason="Provider model index returned no chat-capable models",
            model_count=0,
        )
    return models, _model_index_metadata(
        "available",
        endpoint=endpoint,
        model_count=len(models),
    )


def provider_authorized(provider_id: str, settings: Settings) -> bool:
    provider = normalize_provider(provider_id)
    if provider == "local":
        return True
    if provider == "openai":
        return _has_real_api_key(
            str(getattr(settings, "OPENAI_API_KEY", "") or "")
        )
    if provider == "groq":
        return _has_real_api_key(
            str(getattr(settings, "GROQ_API_KEY", "") or "")
        )
    if provider == "alibaba":
        has_key = _has_real_api_key(
            str(getattr(settings, "ALIBABA_API_KEY", "") or "")
        )
        has_base = bool(
            str(getattr(settings, "ALIBABA_API_BASE", "") or "").strip()
        )
        return has_key and has_base
    if provider == "minimax":
        has_key = _has_real_api_key(
            str(getattr(settings, "MINIMAX_API_KEY", "") or "")
        )
        has_base = bool(
            str(getattr(settings, "MINIMAX_API_BASE", "") or "").strip()
        )
        return has_key and has_base
    if provider == "anthropic":
        return _has_real_api_key(
            str(getattr(settings, "ANTHROPIC_API_KEY", "") or "")
        )
    if provider == "gemini":
        return _has_real_api_key(
            str(getattr(settings, "GEMINI_API_KEY", "") or "")
        )
    return False


def provider_availability(
    provider_id: str,
    settings: Settings,
    *,
    authorized: bool | None = None,
) -> tuple[bool, str | None]:
    provider = normalize_provider(provider_id)
    contract = _provider_governance(provider)
    if contract is None:
        return False, "Unsupported provider"

    authorized_value = (
        provider_authorized(provider, settings)
        if authorized is None
        else bool(authorized)
    )

    if provider in CLOUD_PROVIDERS and not authorized_value:
        return False, "Missing provider credentials"

    if contract["classification"] == "disabled":
        return False, "Unsupported provider"

    try:
        if provider in _VALIDATED_PROVIDER_SET:
            validate_llm_config(settings, provider_override=provider)
    except LLMConfigError as exc:
        return False, _normalize_reason(str(exc))

    if provider in CLOUD_PROVIDERS:
        try:
            assert_egress_allowed(provider, settings=settings)
        except EgressDeniedError as exc:
            return False, _normalize_reason(str(exc))

    return True, None


def provider_status(provider_id: str, settings: Settings) -> dict[str, Any]:
    capability = resolve_provider_capability(provider_id, settings)
    return {
        "id": capability["id"],
        "authorized": capability["authorized"],
        "available": capability["available"],
        "enabled": capability["enabled"],
        "disabled_reason": capability["disabled_reason"],
        "default_model": capability["default_model"],
        "model_index": dict(capability["model_index"]),
    }


def _static_provider_models(
    provider_id: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    provider = normalize_provider(provider_id)
    static_models = [
        dict(item) for item in _STATIC_PROVIDER_MODELS.get(provider, ())
    ]
    default_model = default_model_for_provider(provider, settings)
    existing_ids = {
        str(item.get("id") or "").strip()
        for item in static_models
        if str(item.get("id") or "").strip()
    }
    if default_model and default_model not in existing_ids:
        static_models.insert(
            0,
            {"id": default_model, "displayName": default_model},
        )
    return static_models


def resolve_provider_capability(
    provider_id: str,
    settings: Settings,
) -> dict[str, Any]:
    provider = normalize_provider(provider_id)
    authorized = provider_authorized(provider, settings)
    available, disabled_reason = provider_availability(
        provider,
        settings,
        authorized=authorized,
    )
    default_model = default_model_for_provider(provider, settings)

    if provider == "local":
        models: list[dict[str, Any]] = []
        model_index = {
            "source": "local",
            "state": "available",
        }
    elif provider in _DYNAMIC_MODEL_PROVIDERS:
        models, model_index = _discover_dynamic_provider_models(
            provider,
            settings,
            available=available,
            disabled_reason=disabled_reason,
        )
        if model_index["state"] != "available" and not default_model:
            available = False
            disabled_reason = (
                str(
                    disabled_reason
                    or model_index.get("reason")
                    or "Provider model index unavailable"
                ).strip()
                or "Provider model index unavailable"
            )
    else:
        models = _static_provider_models(provider, settings)
        model_index = {
            "source": "static",
            "state": "available",
            "model_count": len(models),
        }

    enabled = bool(available) and (provider == "local" or bool(authorized))
    return {
        "id": provider,
        "authorized": authorized,
        "available": available,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "default_model": default_model,
        "models": [dict(item) for item in models],
        "model_index": dict(model_index),
    }


def get_provider_model_descriptors(
    provider_id: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    provider = normalize_provider(provider_id)
    capability = resolve_provider_capability(provider, settings)
    models = [dict(item) for item in capability["models"]]
    if models:
        return models

    contract = _provider_governance(provider)
    if contract is None:
        return []

    default_model = normalize_model_id(capability["default_model"])
    model_index_state = str(
        capability["model_index"].get("state") or ""
    ).strip()
    if (
        contract["configured_defaults_allowed_on_discovery_failure"]
        and default_model
        and model_index_state != "available"
    ):
        return [{"id": default_model, "displayName": default_model}]
    return []


def resolve_provider_for_model(
    model_id: str | None,
    *,
    settings: Settings,
    local_model_ids: Iterable[str] | None = None,
    enabled_only: bool = True,
) -> str | None:
    candidate = normalize_model_id(model_id)
    if not candidate:
        return None

    local_ids = {
        normalize_model_id(item) for item in (local_model_ids or []) if item
    }
    if candidate in local_ids:
        local_status = provider_status("local", settings)
        if local_status["enabled"] or not enabled_only:
            return "local"

    for provider_id in PROVIDER_ORDER:
        if provider_id == "local":
            continue
        capability = resolve_provider_capability(provider_id, settings)
        if enabled_only and not capability["enabled"]:
            continue
        for model in get_provider_model_descriptors(provider_id, settings):
            if normalize_model_id(model.get("id")) == candidate:
                return provider_id
    return None


def validate_provider_model_selection(
    *,
    provider_id: str,
    model_id: str | None,
    settings: Settings,
    local_model_ids: Iterable[str] | None = None,
) -> tuple[bool, str | None]:
    provider = normalize_provider(provider_id)
    capability = resolve_provider_capability(provider, settings)
    if not capability["enabled"]:
        return False, str(
            capability["disabled_reason"] or "Provider unavailable"
        )

    model = normalize_model_id(model_id)
    if not model:
        if capability["default_model"]:
            return True, None
        return False, "No model configured for provider"

    if provider == "local":
        local_ids = {
            normalize_model_id(item) for item in (local_model_ids or []) if item
        }
        if local_ids and model not in local_ids:
            return False, f"Requested model '{model}' is not available"
        return True, None

    provider_model_ids = {
        normalize_model_id(item.get("id")) for item in capability["models"]
    }
    if model not in provider_model_ids:
        model_index = capability["model_index"]
        if (
            provider in _DYNAMIC_MODEL_PROVIDERS
            and normalize_model_id(capability["default_model"]) == model
            and str(model_index.get("state") or "").strip() != "available"
        ):
            return True, None
        return (
            False,
            f"Requested model '{model}' is not available for provider '{provider}'",
        )
    return True, None
