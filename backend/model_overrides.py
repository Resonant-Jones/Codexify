"""Model metadata override helpers backed by the chatlog database."""

from __future__ import annotations

import copy
from typing import Any

_MODEL_OVERRIDES_CACHE: dict[str, dict[str, dict[str, Any]]] | None = None


def _normalize_provider_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    clean = value.strip().lower()
    return clean or None


def _normalize_model_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    clean = value.strip()
    return clean or None


def invalidate_model_overrides_cache() -> None:
    """Drop the in-process cache so the next read reflects the database."""
    global _MODEL_OVERRIDES_CACHE
    _MODEL_OVERRIDES_CACHE = None


def load_model_overrides(
    *, force_refresh: bool = False
) -> dict[str, dict[str, dict[str, Any]]]:
    """Return provider/model overrides grouped by provider and model id."""
    global _MODEL_OVERRIDES_CACHE
    if _MODEL_OVERRIDES_CACHE is not None and not force_refresh:
        return copy.deepcopy(_MODEL_OVERRIDES_CACHE)

    from guardian.core import dependencies

    db = getattr(dependencies, "chatlog_db", None)
    if db is None or not hasattr(db, "list_inference_model_overrides"):
        return {}

    try:
        rows = db.list_inference_model_overrides() or []
    except Exception:
        return {}

    grouped: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        provider_id = _normalize_provider_id(row.get("provider_id"))
        model_id = _normalize_model_id(row.get("model_id"))
        if not provider_id or not model_id:
            continue
        grouped.setdefault(provider_id, {})[model_id] = {
            "provider_id": provider_id,
            "model_id": model_id,
            "display_label": row.get("display_label"),
            "picker_label": row.get("picker_label"),
            "supports_chat": row.get("supports_chat"),
            "supports_vision": row.get("supports_vision"),
            "supports_text_input": row.get("supports_text_input"),
            "model_kind": row.get("model_kind"),
            "notes": row.get("notes"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    _MODEL_OVERRIDES_CACHE = grouped
    return copy.deepcopy(grouped)


def get_model_override(
    provider_id: str | None, model_id: str | None
) -> dict[str, Any] | None:
    provider_key = _normalize_provider_id(provider_id)
    model_key = _normalize_model_id(model_id)
    if not provider_key or not model_key:
        return None
    overrides = load_model_overrides()
    provider_overrides = overrides.get(provider_key, {})
    return copy.deepcopy(provider_overrides.get(model_key))


def get_model_override_map() -> dict[str, dict[str, dict[str, Any]]]:
    """Return a defensive copy of the full grouped override map."""
    return load_model_overrides()
