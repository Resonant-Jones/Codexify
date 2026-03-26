"""Canonical provider capability registry and resolver.

This module is the single source of truth for provider/model capability
decisions used by catalog, health, router, and worker code.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ProviderGovernanceRule:
    provider: str
    label: str
    governance_classification: ProviderGovernanceClassification
    live_discovery_expected: bool
    routing_validate_discovered_inventory: bool
    configured_defaults_allowed_during_degraded_discovery: bool
    local_only: bool

    @property
    def classification(self) -> ProviderGovernanceClassification:
        """Backward-compatible alias for the governance classification field."""
        return self.governance_classification

    @property
    def configured_defaults_allowed_on_discovery_failure(self) -> bool:
        """Backward-compatible alias for the degraded discovery flag."""
        return self.configured_defaults_allowed_during_degraded_discovery

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "governance_classification": self.governance_classification,
            "live_discovery_expected": self.live_discovery_expected,
            "routing_validate_discovered_inventory": (
                self.routing_validate_discovered_inventory
            ),
            "configured_defaults_allowed_during_degraded_discovery": (
                self.configured_defaults_allowed_during_degraded_discovery
            ),
            "local_only": self.local_only,
        }


_PROVIDER_GOVERNANCE_RULES: tuple[ProviderGovernanceRule, ...] = (
    ProviderGovernanceRule(
        provider="openai",
        label="OpenAI",
        governance_classification="static_authorized",
        live_discovery_expected=False,
        routing_validate_discovered_inventory=False,
        configured_defaults_allowed_during_degraded_discovery=False,
        local_only=False,
    ),
    ProviderGovernanceRule(
        provider="anthropic",
        label="Anthropic",
        governance_classification="disabled",
        live_discovery_expected=False,
        routing_validate_discovered_inventory=False,
        configured_defaults_allowed_during_degraded_discovery=False,
        local_only=False,
    ),
    ProviderGovernanceRule(
        provider="gemini",
        label="Gemini",
        governance_classification="disabled",
        live_discovery_expected=False,
        routing_validate_discovered_inventory=False,
        configured_defaults_allowed_during_degraded_discovery=False,
        local_only=False,
    ),
    ProviderGovernanceRule(
        provider="groq",
        label="Groq",
        governance_classification="discovery_backed",
        live_discovery_expected=True,
        routing_validate_discovered_inventory=True,
        configured_defaults_allowed_during_degraded_discovery=True,
        local_only=False,
    ),
    ProviderGovernanceRule(
        provider="alibaba",
        label="Alibaba / DashScope",
        governance_classification="discovery_backed",
        live_discovery_expected=True,
        routing_validate_discovered_inventory=True,
        configured_defaults_allowed_during_degraded_discovery=True,
        local_only=False,
    ),
    ProviderGovernanceRule(
        provider="minimax",
        label="MiniMax",
        governance_classification="discovery_backed",
        live_discovery_expected=True,
        routing_validate_discovered_inventory=True,
        configured_defaults_allowed_during_degraded_discovery=True,
        local_only=False,
    ),
    ProviderGovernanceRule(
        provider="local",
        label="Local",
        governance_classification="local_only",
        live_discovery_expected=False,
        routing_validate_discovered_inventory=False,
        configured_defaults_allowed_during_degraded_discovery=False,
        local_only=True,
    ),
)

_PROVIDER_GOVERNANCE_BY_ID = {
    rule.provider: rule for rule in _PROVIDER_GOVERNANCE_RULES
}

PROVIDER_ORDER = tuple(rule.provider for rule in _PROVIDER_GOVERNANCE_RULES)

PROVIDER_LABELS = {
    rule.provider: rule.label for rule in _PROVIDER_GOVERNANCE_RULES
}

CLOUD_PROVIDERS = {
    rule.provider for rule in _PROVIDER_GOVERNANCE_RULES if not rule.local_only
}

# Audit views derived from the canonical governance tuple. Keep them read-only;
# runtime behavior should continue to derive from _PROVIDER_GOVERNANCE_RULES.
DISCOVERY_BACKED_PROVIDERS = frozenset(
    rule.provider
    for rule in _PROVIDER_GOVERNANCE_RULES
    if rule.governance_classification == "discovery_backed"
)
STATIC_AUTHORIZED_PROVIDERS = frozenset(
    rule.provider
    for rule in _PROVIDER_GOVERNANCE_RULES
    if rule.governance_classification == "static_authorized"
)
LOCAL_ONLY_PROVIDERS = frozenset(
    rule.provider
    for rule in _PROVIDER_GOVERNANCE_RULES
    if rule.governance_classification == "local_only"
)
DISABLED_PROVIDERS = frozenset(
    rule.provider
    for rule in _PROVIDER_GOVERNANCE_RULES
    if rule.governance_classification == "disabled"
)

_VALIDATED_PROVIDER_SET = frozenset(SUPPORTED_ROUTED_LLM_PROVIDERS)


class _AvailabilityReason(str):
    """String-compatible reason that preserves legacy equality checks."""

    def __new__(cls, value: str, *, legacy_alias: str | None = None):
        obj = super().__new__(cls, value)
        obj._legacy_alias = legacy_alias  # type: ignore[attr-defined]
        return obj

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str) and str.__eq__(self, other):
            return True
        legacy_alias = getattr(self, "_legacy_alias", None)
        if isinstance(other, str) and legacy_alias is not None:
            return other == legacy_alias
        return str.__eq__(self, other)  # type: ignore[arg-type]


_AUTO_MODEL_SENTINELS = {"", "auto"}
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
    "text-to-speech",
    "transcription",
    "tts",
    "video",
)
_MODEL_INDEX_IDENTIFIER_NON_CHAT_HINTS = (
    "audio",
    "asr",
    "embedding",
    "embeddings",
    "moderation",
    "rerank",
    "speech",
    "text-to-speech",
    "transcription",
    "tts",
)
_MODEL_INDEX_VISION_HINTS = (
    "image",
    "vision",
    "vl",
    "multimodal",
)
_MODEL_INDEX_TEXT_INPUT_HINTS = (
    "embedding",
    "embeddings",
    "moderation",
    "rerank",
    "tts",
)
_DEFAULT_GROQ_MODEL_INDEX_BASE = "https://api.groq.com/openai/v1"

_STATIC_PROVIDER_MODELS: dict[str, tuple[dict[str, Any], ...]] = {
    "openai": (
        {
            "id": "gpt-4o",
            "displayName": "GPT-4o",
            "contextWindow": 128000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
            "supports_chat": True,
            "supports_vision": True,
            "supports_text_input": True,
            "model_kind": "vision_chat",
        },
        {
            "id": "gpt-4.1-mini",
            "displayName": "GPT-4.1 Mini",
            "contextWindow": 128000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
            "supports_chat": True,
            "supports_vision": True,
            "supports_text_input": True,
            "model_kind": "vision_chat",
        },
    ),
    "anthropic": (
        {
            "id": "claude-3-5-sonnet-latest",
            "displayName": "Claude 3.5 Sonnet",
            "contextWindow": 200000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
            "supports_chat": True,
            "supports_vision": True,
            "supports_text_input": True,
            "model_kind": "vision_chat",
        },
        {
            "id": "claude-3-5-haiku-latest",
            "displayName": "Claude 3.5 Haiku",
            "contextWindow": 200000,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
            "supports_chat": True,
            "supports_vision": True,
            "supports_text_input": True,
            "model_kind": "vision_chat",
        },
    ),
    "gemini": (
        {
            "id": "gemini-1.5-pro",
            "displayName": "Gemini 1.5 Pro",
            "contextWindow": 1048576,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
            "supports_chat": True,
            "supports_vision": True,
            "supports_text_input": True,
            "model_kind": "vision_chat",
        },
        {
            "id": "gemini-1.5-flash",
            "displayName": "Gemini 1.5 Flash",
            "contextWindow": 1048576,
            "capabilities": {"vision": True, "tools": True, "streaming": True},
            "supports_chat": True,
            "supports_vision": True,
            "supports_text_input": True,
            "model_kind": "vision_chat",
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
            "supports_chat": True,
            "supports_vision": False,
            "supports_text_input": True,
            "model_kind": "chat",
        },
        {
            "id": "meta-llama/llama-4-scout-17b-16e-instruct",
            "displayName": "Llama 4 Scout 17B",
            "contextWindow": 128000,
            "capabilities": {
                "vision": True,
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
            "supports_chat": True,
            "supports_vision": False,
            "supports_text_input": True,
            "model_kind": "chat",
        },
    ),
}

_MINIMAX_DOCUMENTED_MODELS: tuple[dict[str, Any], ...] = (
    {
        "id": "MiniMax-M2.7",
        "displayName": "MiniMax M2.7",
        "contextWindow": 204800,
        "capabilities": {"chat": True, "vision": False, "text_input": True},
        "supports_chat": True,
        "supports_vision": False,
        "supports_text_input": True,
        "model_kind": "chat",
    },
    {
        "id": "MiniMax-M2.7-highspeed",
        "displayName": "MiniMax M2.7 Highspeed",
        "contextWindow": 204800,
        "capabilities": {"chat": True, "vision": False, "text_input": True},
        "supports_chat": True,
        "supports_vision": False,
        "supports_text_input": True,
        "model_kind": "chat",
    },
    {
        "id": "MiniMax-M2.5",
        "displayName": "MiniMax M2.5",
        "contextWindow": 204800,
        "capabilities": {"chat": True, "vision": False, "text_input": True},
        "supports_chat": True,
        "supports_vision": False,
        "supports_text_input": True,
        "model_kind": "chat",
    },
    {
        "id": "MiniMax-M2.5-highspeed",
        "displayName": "MiniMax M2.5 Highspeed",
        "contextWindow": 204800,
        "capabilities": {"chat": True, "vision": False, "text_input": True},
        "supports_chat": True,
        "supports_vision": False,
        "supports_text_input": True,
        "model_kind": "chat",
    },
    {
        "id": "MiniMax-M2.1",
        "displayName": "MiniMax M2.1",
        "contextWindow": 204800,
        "capabilities": {"chat": True, "vision": False, "text_input": True},
        "supports_chat": True,
        "supports_vision": False,
        "supports_text_input": True,
        "model_kind": "chat",
    },
    {
        "id": "MiniMax-M2.1-highspeed",
        "displayName": "MiniMax M2.1 Highspeed",
        "contextWindow": 204800,
        "capabilities": {"chat": True, "vision": False, "text_input": True},
        "supports_chat": True,
        "supports_vision": False,
        "supports_text_input": True,
        "model_kind": "chat",
    },
    {
        "id": "MiniMax-M2",
        "displayName": "MiniMax M2",
        "contextWindow": 204800,
        "capabilities": {"chat": True, "vision": False, "text_input": True},
        "supports_chat": True,
        "supports_vision": False,
        "supports_text_input": True,
        "model_kind": "chat",
    },
)


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


def _provider_governance_rule(
    provider_id: str | None,
) -> ProviderGovernanceRule | None:
    return _PROVIDER_GOVERNANCE_BY_ID.get(normalize_provider(provider_id))


# Backwards compatibility: retain old function name for governance lookup
def _provider_governance(provider: str) -> ProviderGovernanceRule | None:
    """Alias to the new governance rule lookup function."""
    return _provider_governance_rule(provider)


def provider_governance(provider_id: str | None) -> dict[str, Any]:
    rule = _provider_governance_rule(provider_id)
    if rule is None:
        normalized = normalize_provider(provider_id)
        raise ValueError(f"Unsupported provider: {normalized or '<empty>'}")
    return rule.as_dict()


def provider_governance_contract() -> dict[str, dict[str, Any]]:
    return {
        rule.provider: rule.as_dict() for rule in _PROVIDER_GOVERNANCE_RULES
    }


def provider_routing_requires_discovered_inventory(
    provider_id: str | None,
) -> bool:
    rule = _provider_governance_rule(provider_id)
    return bool(rule and rule.routing_validate_discovered_inventory)


def provider_allows_default_during_degraded_discovery(
    provider_id: str | None,
) -> bool:
    rule = _provider_governance_rule(provider_id)
    return bool(
        rule and rule.configured_defaults_allowed_during_degraded_discovery
    )


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
    if provider == "groq":
        raw = getattr(settings, "GROQ_MODEL_DISCOVERY_TIMEOUT_SECONDS", 3.0)
    elif provider == "alibaba":
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

    if provider == "groq":
        override = str(
            getattr(settings, "GROQ_MODEL_DISCOVERY_URL", "") or ""
        ).strip()
        base_url = (
            str(getattr(settings, "GROQ_BASE_URL", "") or "").strip()
            or _DEFAULT_GROQ_MODEL_INDEX_BASE
        )
    elif provider == "alibaba":
        override = str(
            getattr(settings, "ALIBABA_MODEL_DISCOVERY_URL", "") or ""
        ).strip()
        base_url = str(getattr(settings, "ALIBABA_API_BASE", "") or "").strip()
    elif provider == "minimax":
        override = str(
            getattr(settings, "MINIMAX_MODEL_DISCOVERY_URL", "") or ""
        ).strip()
        api_flavor = (
            str(getattr(settings, "MINIMAX_API_FLAVOR", "anthropic") or "")
            .strip()
            .lower()
            or "anthropic"
        )
        if override:
            return override.rstrip("/")
        if api_flavor == "anthropic":
            return ""
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
    if provider == "groq":
        api_key = str(getattr(settings, "GROQ_API_KEY", "") or "").strip()
        headers["Authorization"] = f"Bearer {api_key}"
        return headers
    if provider == "alibaba":
        headers[
            "Authorization"
        ] = f"Bearer {str(getattr(settings, 'ALIBABA_API_KEY', '') or '').strip()}"
        return headers
    if provider == "minimax":
        api_key = str(getattr(settings, "MINIMAX_API_KEY", "") or "").strip()
        api_flavor = (
            str(getattr(settings, "MINIMAX_API_FLAVOR", "anthropic") or "")
            .strip()
            .lower()
            or "anthropic"
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
    utility_model_count: int | None = None,
    total_model_count: int | None = None,
    failure_kind: str | None = None,
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
    if utility_model_count is not None:
        payload["utility_model_count"] = int(utility_model_count)
    if total_model_count is not None:
        payload["total_model_count"] = int(total_model_count)
    if failure_kind:
        payload["failure_kind"] = failure_kind
    return payload


def _model_index_unavailable_failure_kind(
    provider_id: str,
    disabled_reason: str | None,
) -> str:
    provider = normalize_provider(provider_id)
    reason = str(disabled_reason or "").strip().lower()
    if not reason:
        return "provider_unavailable"
    if "credential" in reason or "api_key" in reason:
        return "auth_config_error"
    if "egress" in reason or "allowlist" in reason:
        return "egress_blocked"
    if "disabled" in reason:
        return "provider_disabled"
    if provider in {"alibaba", "minimax"}:
        return "auth_config_error"
    return "provider_unavailable"


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


def _model_identifier_hint_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("id", "model", "name", "displayName", "display_label"):
        value = item.get(key)
        if isinstance(value, str):
            clean = value.strip()
            if clean:
                parts.append(clean)
    return " ".join(parts).lower()


def _is_chat_model_index_item(item: dict[str, Any]) -> bool:
    raw_chat = item.get("supports_chat")
    if isinstance(raw_chat, bool):
        return raw_chat
    raw_chat = item.get("supportsChat")
    if isinstance(raw_chat, bool):
        return raw_chat
    hint_text = _model_index_hint_text(item)
    if not hint_text:
        identifier_hint_text = _model_identifier_hint_text(item)
        if not identifier_hint_text:
            return True
        return not any(
            hint in identifier_hint_text
            for hint in _MODEL_INDEX_IDENTIFIER_NON_CHAT_HINTS
        )
    if any(hint in hint_text for hint in _MODEL_INDEX_NON_CHAT_HINTS):
        return False
    identifier_hint_text = _model_identifier_hint_text(item)
    return not any(
        hint in identifier_hint_text
        for hint in _MODEL_INDEX_IDENTIFIER_NON_CHAT_HINTS
    )


def _is_vision_model_index_item(item: dict[str, Any]) -> bool:
    raw_vision = item.get("supports_vision")
    if isinstance(raw_vision, bool):
        return raw_vision
    raw_vision = item.get("supportsVision")
    if isinstance(raw_vision, bool):
        return raw_vision
    raw_caps = item.get("capabilities")
    if isinstance(raw_caps, dict):
        for key in ("vision", "supports_vision", "supportsVision"):
            value = raw_caps.get(key)
            if isinstance(value, bool):
                return value
    hint_text = _model_index_hint_text(item)
    return any(hint in hint_text for hint in _MODEL_INDEX_VISION_HINTS)


def _supports_text_input_model(
    item: dict[str, Any],
    *,
    supports_chat: bool,
) -> bool:
    raw_text_input = item.get("supports_text_input")
    if isinstance(raw_text_input, bool):
        return raw_text_input
    raw_text_input = item.get("supportsTextInput")
    if isinstance(raw_text_input, bool):
        return raw_text_input
    raw_caps = item.get("capabilities")
    if isinstance(raw_caps, dict):
        for key in ("text_input", "supports_text_input", "supportsTextInput"):
            value = raw_caps.get(key)
            if isinstance(value, bool):
                return value
    if supports_chat:
        return True
    hint_text = _model_index_hint_text(item)
    return any(hint in hint_text for hint in _MODEL_INDEX_TEXT_INPUT_HINTS)


def _normalize_model_kind(
    item: dict[str, Any],
    *,
    supports_chat: bool,
    supports_vision: bool,
) -> str:
    raw_kind = (
        str(item.get("model_kind") or item.get("modelKind") or "")
        .strip()
        .lower()
    )
    if raw_kind in {"chat", "vision_chat", "utility"}:
        return raw_kind
    if not supports_chat:
        return "utility"
    if supports_vision:
        return "vision_chat"
    return "chat"


def _normalize_model_descriptor(item: dict[str, Any]) -> dict[str, Any]:
    descriptor = dict(item)
    supports_chat = _is_chat_model_index_item(descriptor)
    supports_vision = _is_vision_model_index_item(descriptor)
    supports_text_input = _supports_text_input_model(
        descriptor,
        supports_chat=supports_chat,
    )
    model_kind = _normalize_model_kind(
        descriptor,
        supports_chat=supports_chat,
        supports_vision=supports_vision,
    )

    descriptor["supports_chat"] = supports_chat
    descriptor["supports_vision"] = supports_vision
    descriptor["supports_text_input"] = supports_text_input
    descriptor["model_kind"] = model_kind

    capabilities = dict(descriptor.get("capabilities") or {})
    capabilities["chat"] = supports_chat
    capabilities["vision"] = supports_vision
    capabilities["text_input"] = supports_text_input
    descriptor["capabilities"] = capabilities
    return descriptor


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
) -> tuple[list[dict[str, Any]], bool, int, int]:
    collections = _extract_model_index_collections(payload)
    if not collections:
        return [], False, 0, 0

    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    chat_model_count = 0
    utility_model_count = 0

    for collection in collections:
        for item in collection:
            model_id = _model_id_from_index_item(item)
            if not model_id or model_id in seen:
                continue

            if isinstance(item, dict):
                descriptor = dict(item)
                descriptor["id"] = model_id
                descriptor["displayName"] = str(
                    item.get("displayName") or item.get("name") or model_id
                ).strip()
                context_window = _extract_context_window(item)
                if context_window is not None:
                    descriptor["contextWindow"] = context_window
                capabilities = _extract_capabilities(item)
                if capabilities:
                    descriptor["capabilities"] = capabilities
            else:
                descriptor = {"id": model_id, "displayName": model_id}
            descriptor = _normalize_model_descriptor(descriptor)

            if bool(descriptor.get("supports_chat")):
                chat_model_count += 1
            else:
                utility_model_count += 1

            seen.add(model_id)
            models.append(descriptor)

    return models, True, chat_model_count, utility_model_count


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
            failure_kind=_model_index_unavailable_failure_kind(
                provider, disabled_reason
            ),
        )

    if not endpoint:
        return [], _model_index_metadata(
            "unavailable",
            reason="Provider model index URL is not configured",
            failure_kind="auth_config_error",
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
            failure_kind="provider_timeout",
        )
    except req_exc.RequestException as exc:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason=f"Provider model index request failed: {type(exc).__name__}",
            failure_kind="transport_error",
        )

    if not (200 <= response.status_code < 300):
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason=(
                "Provider model index request failed "
                f"(HTTP {response.status_code})"
            ),
            failure_kind="provider_http_error",
        )

    try:
        payload = response.json()
    except ValueError:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason="Provider model index returned invalid JSON",
            failure_kind="provider_payload_error",
        )

    (
        models,
        recognized_payload,
        chat_model_count,
        utility_model_count,
    ) = _parse_dynamic_model_descriptors(payload)
    if not recognized_payload:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason="Provider model index payload was invalid",
            failure_kind="provider_payload_error",
        )
    if chat_model_count <= 0:
        return [], _model_index_metadata(
            "degraded",
            endpoint=endpoint,
            reason="Provider model index returned no chat-capable models",
            model_count=0,
            utility_model_count=utility_model_count,
            total_model_count=len(models),
            failure_kind="empty_model_result",
        )
    return models, _model_index_metadata(
        "available",
        endpoint=endpoint,
        model_count=chat_model_count,
        utility_model_count=utility_model_count,
        total_model_count=len(models),
    )


def provider_authorized(provider_id: str, settings: Settings) -> bool:
    provider = normalize_provider(provider_id)
    governance = _provider_governance_rule(provider)

    if governance and governance.local_only:
        return True
    if governance and governance.governance_classification == "disabled":
        return False
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
    governance = _provider_governance_rule(provider)
    if governance is None:
        return False, "Unsupported provider"
    authorized_value = (
        provider_authorized(provider, settings)
        if authorized is None
        else bool(authorized)
    )

    if provider in CLOUD_PROVIDERS and not authorized_value:
        return False, "Missing provider credentials"

    if governance.classification == "disabled":
        return False, _AvailabilityReason(
            "Provider disabled", legacy_alias="Unsupported provider"
        )

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
        _normalize_model_descriptor(dict(item))
        for item in _STATIC_PROVIDER_MODELS.get(provider, ())
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
            _normalize_model_descriptor(
                {
                    "id": default_model,
                    "displayName": default_model,
                    "supports_chat": True,
                    "supports_vision": False,
                    "supports_text_input": True,
                    "model_kind": "chat",
                }
            ),
        )
    return static_models


def _minimax_documented_models(settings: Settings) -> list[dict[str, Any]]:
    models = [
        _normalize_model_descriptor(dict(item))
        for item in _MINIMAX_DOCUMENTED_MODELS
    ]
    default_model = default_model_for_provider("minimax", settings)
    existing_ids = {
        str(item.get("id") or "").strip()
        for item in models
        if str(item.get("id") or "").strip()
    }
    if default_model and default_model not in existing_ids:
        models.insert(
            0,
            _normalize_model_descriptor(
                {
                    "id": default_model,
                    "displayName": default_model,
                    "supports_chat": True,
                    "supports_vision": False,
                    "supports_text_input": True,
                    "model_kind": "chat",
                }
            ),
        )
    return models


def resolve_provider_capability(
    provider_id: str,
    settings: Settings,
) -> dict[str, Any]:
    provider = normalize_provider(provider_id)
    governance = _provider_governance_rule(provider)
    authorized = provider_authorized(provider, settings)
    available, disabled_reason = provider_availability(
        provider,
        settings,
        authorized=authorized,
    )
    default_model = default_model_for_provider(provider, settings)

    if governance and governance.local_only:
        models: list[dict[str, Any]] = []
        model_index = {
            "source": "local",
            "state": "available",
            "model_count": 0,
            "utility_model_count": 0,
            "total_model_count": 0,
        }
    elif governance and governance.live_discovery_expected:
        models, model_index = _discover_dynamic_provider_models(
            provider,
            settings,
            available=available,
            disabled_reason=disabled_reason,
        )
        if (
            provider == "minimax"
            and available
            and model_index["state"] != "available"
        ):
            fallback_models = _minimax_documented_models(settings)
            if fallback_models:
                models = fallback_models
                chat_model_count = sum(
                    1 for model in models if bool(model.get("supports_chat"))
                )
                utility_model_count = sum(
                    1
                    for model in models
                    if not bool(model.get("supports_chat"))
                )
                model_index = {
                    **model_index,
                    "source": "fallback",
                    "state": "degraded",
                    "reason": (
                        f"{str(model_index.get('reason') or 'MiniMax live discovery unavailable').strip()} "
                        "using documented model list"
                    ),
                    "failure_kind": str(
                        model_index.get("failure_kind")
                        or "discovery_unavailable"
                    ).strip()
                    or "discovery_unavailable",
                    "model_count": chat_model_count,
                    "utility_model_count": utility_model_count,
                    "total_model_count": len(models),
                }
        elif model_index["state"] != "available" and (
            not default_model
            or not provider_allows_default_during_degraded_discovery(provider)
        ):
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
            "model_count": sum(
                1 for model in models if bool(model.get("supports_chat"))
            ),
            "utility_model_count": sum(
                1 for model in models if not bool(model.get("supports_chat"))
            ),
            "total_model_count": len(models),
        }

    chat_model_count = sum(
        1 for model in models if bool(model.get("supports_chat"))
    )
    if chat_model_count <= 0 and model_index.get("state") == "available":
        model_index = {
            **model_index,
            "state": "degraded",
            "model_count": 0,
            "utility_model_count": sum(
                1 for model in models if not bool(model.get("supports_chat"))
            ),
            "total_model_count": len(models),
            "failure_kind": "empty_model_result",
            "reason": "Provider model index returned no chat-capable models",
        }
        available = False
        disabled_reason = "Provider model index returned no chat-capable models"

    enabled = bool(available) and (
        bool(governance and governance.local_only) or bool(authorized)
    )
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

    governance = _provider_governance(provider)
    if governance is None:
        return []

    default_model = normalize_model_id(capability["default_model"])
    model_index_state = str(
        capability["model_index"].get("state") or ""
    ).strip()
    if (
        governance.configured_defaults_allowed_on_discovery_failure
        and default_model
        and model_index_state != "available"
    ):
        return [
            _normalize_model_descriptor(
                {
                    "id": default_model,
                    "displayName": default_model,
                    "supports_chat": True,
                    "supports_vision": False,
                    "supports_text_input": True,
                    "model_kind": "chat",
                }
            )
        ]
    return []


def model_supports_capability(
    provider_id: str,
    model_id: str | None,
    capability_key: str,
    settings: Settings,
) -> bool:
    provider = normalize_provider(provider_id)
    target = normalize_model_id(model_id)
    if not target:
        return False
    for item in get_provider_model_descriptors(provider, settings):
        if normalize_model_id(item.get("id")) != target:
            continue
        capabilities = item.get("capabilities")
        if not isinstance(capabilities, dict):
            return False
        value = capabilities.get(capability_key)
        return bool(value) if isinstance(value, bool) else False
    return False


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
            if not bool(model.get("supports_chat")):
                continue
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
        normalize_model_id(item.get("id"))
        for item in capability["models"]
        if bool(item.get("supports_chat"))
    }
    if model not in provider_model_ids:
        model_index = capability["model_index"]
        if (
            provider_routing_requires_discovered_inventory(provider)
            and normalize_model_id(capability["default_model"]) == model
            and str(model_index.get("state") or "").strip() != "available"
            and provider_allows_default_during_degraded_discovery(provider)
        ):
            return True, None
        return (
            False,
            f"Requested model '{model}' is not available for provider '{provider}'",
        )
    return True, None
