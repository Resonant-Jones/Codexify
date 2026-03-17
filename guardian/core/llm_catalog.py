"""Policy-aware provider/model catalog for the unified selector UI."""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

import requests

from guardian.core.ai_router import _resolve_local_base, describe_local_runtime
from guardian.core.config import Settings, get_settings
from guardian.core.provider_registry import CLOUD_PROVIDERS as _CLOUD_PROVIDERS
from guardian.core.provider_registry import PROVIDER_LABELS as _PROVIDER_LABELS
from guardian.core.provider_registry import PROVIDER_ORDER as _PROVIDER_ORDER
from guardian.core.provider_registry import (
    default_model_for_provider,
    get_provider_model_descriptors,
    normalize_model_id,
    normalize_provider,
    provider_status,
)
from guardian.core.provider_registry import (
    resolve_provider_for_model as resolve_provider_for_model_registry,
)

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
_QUANTIZATION_MARKER_RE = re.compile(
    r"^(?:q\d+(?:_[a-z0-9]+)*|bf16|f16|fp16|fp32|fp8|int4|int8)$",
    re.IGNORECASE,
)
_SIZE_TOKEN_RE = re.compile(r"(?i)\b(\d+(?:\.\d+)?)b\b")


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
    return entry


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
    try:
        source_label = _source_label(_resolve_local_base(settings))
    except Exception:
        source_label = None
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
        entry = _base_model_entry(name, display_name=display_label)
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
    return entries


def _cloud_models(provider_id: str, settings: Settings) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in get_provider_model_descriptors(provider_id, settings):
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
    status = provider_status(provider_id, settings)
    return bool(status["available"]), status["disabled_reason"]


def _provider_entry(
    provider_id: str,
    settings: Settings,
    include_all: bool,
) -> dict[str, Any] | None:
    status = provider_status(provider_id, settings)
    authorized = bool(status["authorized"])
    if not include_all and provider_id != "local" and not authorized:
        return None

    available = bool(status["available"])
    disabled_reason = status["disabled_reason"]
    enabled = bool(status["enabled"])
    models = _provider_models(provider_id, settings)
    if provider_id != "local" and not models:
        available = False
        enabled = False
        disabled_reason = disabled_reason or "No models configured for provider"
        if not include_all:
            return None

    entry: dict[str, Any] = {
        "id": provider_id,
        "displayName": _PROVIDER_LABELS.get(provider_id, provider_id.title()),
        "enabled": enabled,
        # backward compatibility fields used by existing callers
        "label": _PROVIDER_LABELS.get(provider_id, provider_id.title()),
        "authorized": authorized,
        "available": available,
        "models": models,
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
    resolved = settings or get_settings()
    local_model_ids = [
        model.get("id") for model in _fetch_local_models(resolved)
    ]
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
