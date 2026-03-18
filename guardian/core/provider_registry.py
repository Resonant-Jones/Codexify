"""Canonical provider capability registry and resolver.

This module is the single source of truth for provider/model capability
decisions used by catalog, health, router, and worker code.
"""

from __future__ import annotations

from typing import Any, Iterable, Literal, TypedDict

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
    provider = normalize_provider(provider_id)
    authorized = provider_authorized(provider, settings)
    available, disabled_reason = provider_availability(
        provider,
        settings,
        authorized=authorized,
    )
    enabled = bool(available) and (provider == "local" or bool(authorized))
    return {
        "id": provider,
        "authorized": authorized,
        "available": available,
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "default_model": default_model_for_provider(provider, settings),
    }


def get_provider_model_descriptors(
    provider_id: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    provider = normalize_provider(provider_id)

    if provider == "local":
        return []
    if provider == "alibaba":
        model_id = normalize_model_id(getattr(settings, "ALIBABA_MODEL", None))
        if not model_id:
            return []
        return [{"id": model_id, "displayName": model_id}]
    if provider == "minimax":
        model_id = normalize_model_id(
            getattr(settings, "MINIMAX_MODEL", None) or "minimax-default"
        )
        return [{"id": model_id, "displayName": "MiniMax (default)"}]

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
        status = provider_status(provider_id, settings)
        if enabled_only and not status["enabled"]:
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
    status = provider_status(provider, settings)
    if not status["enabled"]:
        return False, str(status["disabled_reason"] or "Provider unavailable")

    model = normalize_model_id(model_id)
    if not model:
        if status["default_model"]:
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
        normalize_model_id(item.get("id"))
        for item in get_provider_model_descriptors(provider, settings)
    }
    if model not in provider_model_ids:
        return (
            False,
            f"Requested model '{model}' is not available for provider '{provider}'",
        )
    return True, None
