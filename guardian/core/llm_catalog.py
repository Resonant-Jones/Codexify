"""Policy-aware provider/model catalog for the unified selector UI."""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

import requests

from guardian.core.ai_router import (
    _resolve_local_base,
    describe_local_runtime,
    discover_local_model_inventory,
    resolve_local_execution_model,
)
from guardian.core.config import Settings, get_settings
from guardian.core.provider_registry import CLOUD_PROVIDERS as _CLOUD_PROVIDERS
from guardian.core.provider_registry import PROVIDER_LABELS as _PROVIDER_LABELS
from guardian.core.provider_registry import PROVIDER_ORDER as _PROVIDER_ORDER
from guardian.core.provider_registry import (
    get_provider_model_descriptors,
    normalize_model_id,
    normalize_provider,
    resolve_provider_capability,
)
from guardian.core.provider_registry import (
    resolve_provider_for_model as resolve_provider_for_model_registry,
)
from guardian.core.provider_truth import build_provider_truth

_MODEL_FAMILY_ALIASES = {
    "deepseek": "DeepSeek",
    "gemma": "Gemma",
    "gpt": "GPT",
    "josie": "JOSIE",
    "lfm": "LFM",
    "llama": "Llama",
    "llava": "LLaVA",
    "ministral": "Ministral",
    "mistral": "Mistral",
    "phi": "Phi",
    "qwen": "Qwen",
    "qwq": "QwQ",
}
_MEANINGFUL_VARIANT_LABELS = {
    "coder": "Coder",
    "flash": "Flash",
    "instruct": "Instruct",
    "thinking": "Thinking",
    "vl": "VL",
}
_LOCAL_VISION_HINTS = (
    "image",
    "vision",
    "llava",
    "vl",
    "multimodal",
    "gemma",
)
_QUANTIZATION_MARKER_RE = re.compile(
    r"^(?:q\d+(?:_[a-z0-9]+)*|bf16|f16|fp16|fp32|fp8|int4|int8)$",
    re.IGNORECASE,
)
_SIZE_TOKEN_RE = re.compile(r"(?i)\b(\d+(?:\.\d+)?)b\b")
logger = logging.getLogger(__name__)


def _catalog_timeout_seconds() -> float:
    raw = os.getenv("LLM_CATALOG_REQUEST_TIMEOUT_SECONDS", "1.5").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 1.5
    return max(0.2, value)


def _base_model_entry(
    model_id: str,
    display_name: str | None = None,
    context_window: int | None = None,
    capabilities: dict[str, bool] | None = None,
    *,
    supports_chat: bool | None = None,
    supports_vision: bool | None = None,
    supports_text_input: bool | None = None,
    model_kind: str | None = None,
) -> dict[str, Any]:
    clean_id = str(model_id or "").strip()
    clean_name = str(display_name or clean_id).strip() or clean_id
    entry: dict[str, Any] = {
        "id": clean_id,
        "canonical_id": clean_id,
        "displayName": clean_name,
        "display_label": clean_name,
        "alias": None,
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
    if isinstance(supports_chat, bool):
        entry["supports_chat"] = supports_chat
    if isinstance(supports_vision, bool):
        entry["supports_vision"] = supports_vision
    if isinstance(supports_text_input, bool):
        entry["supports_text_input"] = supports_text_input
    normalized_kind = str(model_kind or "").strip().lower()
    if normalized_kind in {"chat", "vision_chat", "utility"}:
        entry["model_kind"] = normalized_kind
    return entry


def _local_model_capabilities(
    model_id: str, display_name: str
) -> dict[str, Any]:
    haystack = f"{model_id} {display_name}".lower()
    supports_vision = any(hint in haystack for hint in _LOCAL_VISION_HINTS)
    return {
        "supports_chat": True,
        "supports_vision": supports_vision,
        "supports_text_input": True,
        "model_kind": "vision_chat" if supports_vision else "chat",
    }


def _split_local_model_id(model_id: str) -> tuple[str | None, str, str | None]:
    clean_id = str(model_id or "").strip()
    namespace: str | None = None
    remainder = clean_id
    if "/" in clean_id:
        maybe_namespace, maybe_model = clean_id.split("/", 1)
        maybe_namespace = maybe_namespace.strip()
        maybe_model = maybe_model.strip()
        if maybe_namespace and maybe_model:
            namespace = maybe_namespace
            remainder = maybe_model

    base_name, separator, tag = remainder.partition(":")
    clean_base = base_name.strip() or remainder
    clean_tag = tag.strip() if separator else ""
    return namespace, clean_base, clean_tag or None


def _format_model_label_token(token: str) -> str:
    clean = str(token or "").strip()
    if not clean:
        return ""

    lower = clean.lower()
    size_match = _SIZE_TOKEN_RE.fullmatch(lower)
    if size_match:
        return f"{size_match.group(1)}B"
    if lower in _MEANINGFUL_VARIANT_LABELS:
        return _MEANINGFUL_VARIANT_LABELS[lower]
    if lower in _MODEL_FAMILY_ALIASES:
        return _MODEL_FAMILY_ALIASES[lower]
    if clean.isupper() and any(char.isalpha() for char in clean):
        return clean
    if re.fullmatch(r"\d+(?:\.\d+)?", clean):
        return clean
    if clean.isalpha():
        return clean[:1].upper() + clean[1:].lower()
    return clean


def _normalize_base_model_label(base_name: str) -> str:
    clean = str(base_name or "").strip()
    if not clean:
        return ""

    spaced = re.sub(r"[-_]+", " ", clean)
    spaced = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", spaced)
    spaced = re.sub(r"(?<=\d)(?=[A-Za-z])", " ", spaced)
    tokens = [_format_model_label_token(part) for part in spaced.split()]
    return " ".join(token for token in tokens if token).strip()


def _extract_size_label(tag: str | None) -> str | None:
    if not tag:
        return None
    match = _SIZE_TOKEN_RE.search(tag)
    if not match:
        return None
    return f"{match.group(1)}B"


def _is_quantization_marker(token: str) -> bool:
    clean = str(token or "").strip()
    if not clean:
        return False
    return bool(_QUANTIZATION_MARKER_RE.fullmatch(clean.lower()))


def _extract_meaningful_variants(tag: str | None) -> list[str]:
    if not tag:
        return []

    variants: list[str] = []
    seen: set[str] = set()
    for raw_part in re.split(r"[-]+", tag):
        clean = str(raw_part or "").strip(" _")
        if not clean:
            continue
        lower = clean.lower()
        if _SIZE_TOKEN_RE.fullmatch(lower) or _is_quantization_marker(lower):
            continue
        if lower not in _MEANINGFUL_VARIANT_LABELS:
            continue
        label = _MEANINGFUL_VARIANT_LABELS[lower]
        if label in seen:
            continue
        seen.add(label)
        variants.append(label)
    return variants


def _local_model_identity(
    model_id: str,
    *,
    source_label: str | None = None,
) -> dict[str, Any]:
    canonical_id = str(model_id or "").strip()
    namespace, base_name, tag = _split_local_model_id(canonical_id)
    base_label = _normalize_base_model_label(base_name) or canonical_id
    size_label = _extract_size_label(tag)
    meaningful_variants = _extract_meaningful_variants(tag)
    display_parts = [base_label]
    if size_label:
        display_parts.append(size_label)
    display_parts.extend(meaningful_variants)
    derived_label = (
        " ".join(part for part in display_parts if part).strip() or canonical_id
    )

    return {
        "canonical_id": canonical_id,
        "display_label": derived_label,
        "alias": None,
        "namespace": namespace,
        "source": namespace or source_label,
        "raw_tag": tag,
    }


def _identity_disambiguator(identity: dict[str, Any]) -> str:
    namespace = str(identity.get("namespace") or "").strip()
    if namespace:
        return namespace

    raw_tag = str(identity.get("raw_tag") or "").strip()
    if raw_tag:
        residual_parts: list[str] = []
        for raw_part in re.split(r"[-]+", raw_tag):
            clean = str(raw_part or "").strip(" _")
            if not clean:
                continue
            lower = clean.lower()
            if _SIZE_TOKEN_RE.fullmatch(lower):
                continue
            if lower in _MEANINGFUL_VARIANT_LABELS:
                continue
            residual_parts.append(clean)
        if residual_parts:
            return "-".join(residual_parts)

    source = str(identity.get("source") or "").strip()
    if source:
        return source
    return str(identity.get("canonical_id") or "").strip()


def _apply_local_display_disambiguation(
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    label_counts = Counter(
        str(entry.get("display_label") or "").strip() for entry in entries
    )
    for entry in entries:
        base_label = str(entry.get("display_label") or "").strip()
        if not base_label or label_counts.get(base_label, 0) < 2:
            continue
        disambiguator = _identity_disambiguator(entry)
        if disambiguator:
            entry["display_label"] = f"{base_label} · {disambiguator}"
    return entries


def _fetch_local_models(
    settings: Settings,
) -> tuple[list[dict[str, Any]], dict[str, Any], Any]:
    timeout = _catalog_timeout_seconds()
    names, endpoint_resolution = discover_local_model_inventory(
        settings, timeout_seconds=timeout, request_get=requests.get
    )

    deduped: list[str] = []
    seen: set[str] = set()
    for model_name in names:
        key = model_name.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    local_model_resolution = resolve_local_execution_model(
        settings=settings,
        validate_availability=True,
        discovered_model_names=deduped,
        endpoint_resolution=endpoint_resolution,
    )
    effective_model = normalize_model_id(local_model_resolution.model)
    if effective_model:
        normalized_names = {
            normalize_model_id(name): name for name in deduped if name
        }
        if effective_model in normalized_names:
            deduped = [
                normalized_names[effective_model],
                *[
                    name
                    for name in deduped
                    if normalize_model_id(name) != effective_model
                ],
            ]
        elif str(endpoint_resolution.get("state") or "").strip() != "available":
            deduped = [effective_model, *deduped]
    source_base = str(
        (endpoint_resolution.get("selected_endpoint") or {}).get("base_url")
        or ""
    ).strip()
    if not source_base:
        try:
            source_base = _resolve_local_base(settings)
        except Exception:
            source_base = None
    source_label = _source_label(source_base) if source_base else None
    identities = _apply_local_display_disambiguation(
        [
            _local_model_identity(name, source_label=source_label)
            for name in deduped
        ]
    )
    entries: list[dict[str, Any]] = []
    for name, identity in zip(deduped, identities, strict=False):
        display_label = str(
            identity.get("alias") or identity.get("display_label") or name
        ).strip()
        local_capabilities = _local_model_capabilities(name, display_label)
        entry = _base_model_entry(
            name,
            display_name=display_label,
            supports_chat=bool(local_capabilities["supports_chat"]),
            supports_vision=bool(local_capabilities["supports_vision"]),
            supports_text_input=bool(local_capabilities["supports_text_input"]),
            model_kind=str(local_capabilities["model_kind"]),
        )
        entry["capabilities"] = {
            "chat": bool(local_capabilities["supports_chat"]),
            "vision": bool(local_capabilities["supports_vision"]),
            "text_input": bool(local_capabilities["supports_text_input"]),
        }
        entry["canonical_id"] = str(
            identity.get("canonical_id") or name
        ).strip()
        entry["display_label"] = str(
            identity.get("display_label") or display_label
        ).strip()
        entry["alias"] = identity.get("alias")
        namespace = str(identity.get("namespace") or "").strip()
        if namespace:
            entry["namespace"] = namespace
        source = str(identity.get("source") or "").strip()
        if source:
            entry["source"] = source
        entry["runtime"] = describe_local_runtime(name, settings=settings)
        entries.append(entry)
    if endpoint_resolution.get("state") != "available" and names:
        logger.warning(
            "Local model discovery degraded; using configured/local fallback names. resolution=%s",
            endpoint_resolution,
        )
    return entries, endpoint_resolution, local_model_resolution


def _cloud_models(
    provider_id: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    capability = resolve_provider_capability(provider_id, settings)
    for item in capability["models"]:
        model_id = str(item.get("id") or "").strip()
        if not model_id:
            continue
        capabilities = (
            item.get("capabilities")
            if isinstance(item.get("capabilities"), dict)
            else {}
        )
        supports_chat = (
            item.get("supports_chat")
            if isinstance(item.get("supports_chat"), bool)
            else bool(capabilities.get("chat"))
        )
        supports_vision = (
            item.get("supports_vision")
            if isinstance(item.get("supports_vision"), bool)
            else bool(capabilities.get("vision"))
        )
        supports_text_input = (
            item.get("supports_text_input")
            if isinstance(item.get("supports_text_input"), bool)
            else bool(capabilities.get("text_input"))
        )
        model_kind = str(item.get("model_kind") or "").strip().lower()
        if not model_kind:
            model_kind = (
                "vision_chat"
                if supports_chat and supports_vision
                else "chat"
                if supports_chat
                else "utility"
            )
        if not supports_chat or model_kind == "utility":
            continue
        entry = _base_model_entry(
            model_id=model_id,
            display_name=str(item.get("displayName") or model_id).strip(),
            context_window=(
                int(item["contextWindow"])
                if isinstance(item.get("contextWindow"), int)
                else None
            ),
            capabilities=capabilities if capabilities else None,
            supports_chat=bool(supports_chat),
            supports_vision=bool(supports_vision),
            supports_text_input=bool(supports_text_input),
            model_kind=model_kind,
        )
        capability_status = str(item.get("_capability") or "").strip().lower()
        if capability_status in {"confirmed", "inferred", "unsupported"}:
            entry["_capability"] = capability_status
        entries.append(entry)
    return entries


def _provider_models(
    provider_id: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    if provider_id == "local":
        models, _resolution, _local_model_resolution = _fetch_local_models(
            settings
        )
        return models
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


def _provider_entry(
    provider_id: str,
    settings: Settings,
    include_all: bool,
) -> dict[str, Any] | None:
    capability = resolve_provider_capability(provider_id, settings)
    authorized = bool(capability["authorized"])
    if not include_all and provider_id != "local" and not authorized:
        return None

    available = bool(capability["available"])
    disabled_reason = capability["disabled_reason"]
    enabled = bool(capability["enabled"])
    endpoint_resolution: dict[str, Any] | None = None
    local_model_resolution = None
    if provider_id == "local":
        (
            models,
            endpoint_resolution,
            local_model_resolution,
        ) = _fetch_local_models(settings)
        if (
            models
            and endpoint_resolution is not None
            and str(endpoint_resolution.get("state") or "").strip()
            == "available"
        ):
            available = True
            enabled = True
            disabled_reason = None
        if (
            local_model_resolution is not None
            and local_model_resolution.failure_kind
        ):
            enabled = False
            disabled_reason = local_model_resolution.message
    else:
        models = _provider_models(provider_id, settings)

    provider_capability = (
        {
            **capability,
            "enabled": enabled,
            "available": available,
            "disabled_reason": disabled_reason,
        }
        if provider_id == "local"
        else capability
    )
    entry: dict[str, Any] = {
        "id": provider_id,
        "displayName": _PROVIDER_LABELS.get(provider_id, provider_id.title()),
        "enabled": enabled,
        # backward compatibility fields used by existing callers
        "label": _PROVIDER_LABELS.get(provider_id, provider_id.title()),
        "authorized": authorized,
        "available": available,
        "models": models,
        "model_index": dict(capability["model_index"]),
        "truth": build_provider_truth(
            provider_id,
            settings,
            capability=provider_capability,
            discoverable=(
                str(endpoint_resolution.get("state") or "").strip()
                == "available"
                if endpoint_resolution is not None
                else str(
                    (capability.get("model_index") or {}).get("state") or ""
                ).strip()
                == "available"
            ),
            selectable=bool(enabled),
        ),
    }
    source = _provider_source(provider_id, settings)
    if source is not None:
        entry["source"] = source
    if endpoint_resolution is not None:
        entry["endpoint_resolution"] = endpoint_resolution
    if local_model_resolution is not None:
        entry["default_model"] = local_model_resolution.model
        entry["model_resolution"] = local_model_resolution.as_dict()
    if disabled_reason:
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
    resolved = settings or get_settings()
    local_models, _resolution, _local_model_resolution = _fetch_local_models(
        resolved
    )
    local_model_ids = [model.get("id") for model in local_models]
    return resolve_provider_for_model_registry(
        model_id,
        settings=resolved,
        local_model_ids=local_model_ids,
        enabled_only=True,
    )


def first_enabled_provider(*, settings: Settings | None = None) -> str | None:
    catalog = build_llm_catalog(settings=settings, include_all=True)
    for provider in catalog.get("providers", []):
        if provider.get("enabled"):
            resolved = normalize_provider(provider.get("id"))
            if resolved:
                return resolved
    return None


def first_model_for_provider(
    provider_id: str | None,
    *,
    settings: Settings | None = None,
) -> str | None:
    target = normalize_provider(provider_id)
    if not target:
        return None

    catalog = build_llm_catalog(settings=settings, include_all=True)
    for provider in catalog.get("providers", []):
        if normalize_provider(provider.get("id")) != target:
            continue
        if not provider.get("enabled"):
            return None
        models = provider.get("models")
        if not isinstance(models, list) or not models:
            return None
        first = normalize_model_id(models[0].get("id"))
        return first or None
    return None
