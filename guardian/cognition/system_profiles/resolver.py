"""Thread-scoped system profile resolver and persistence helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_profile_blocks(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    blocks: dict[str, str] = {}
    for key, block in value.items():
        block_key = _clean_text(key)
        block_text = _clean_text(block)
        if block_key and block_text:
            blocks[block_key] = block_text
    return blocks


def _coerce_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return dict(value)
    return None


def _normalize_mode(
    mode: str | None, provider_override: str | None
) -> Literal["local", "cloud"]:
    cleaned_mode = _clean_text(mode)
    if cleaned_mode == "local":
        return "local"
    if cleaned_mode == "cloud":
        return "cloud"
    provider = _clean_text(provider_override)
    if provider and provider.lower() == "local":
        return "local"
    return "cloud"


def _default_profile_name(profile_id: str) -> str:
    cleaned = profile_id.replace("_", " ").replace("-", " ").strip()
    if not cleaned:
        return "Profile"
    return " ".join(part.capitalize() for part in cleaned.split())


def _extract_metadata(thread_row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(thread_row, dict):
        return {}
    raw = thread_row.get("metadata")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return dict(parsed)
    return {}


class SystemProfilePayload(BaseModel):
    """Structured profile payload that can be persisted or merged."""

    profile_id: str = Field(min_length=1, max_length=128)
    name: str | None = None
    mode: Literal["local", "cloud"] | None = None
    provider_override: str | None = None
    model_override: str | None = None
    temperature_override: float | None = Field(default=None, ge=0.0, le=2.0)
    system_prompt: str | None = None
    system_prompt_blocks: dict[str, str] = Field(default_factory=dict)
    retrieval_config: dict[str, Any] | None = None
    tool_permissions: dict[str, Any] | None = None
    model_config_payload: dict[str, Any] | None = Field(
        default=None,
        alias="model_config",
        serialization_alias="model_config",
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("profile_id", mode="before")
    @classmethod
    def _validate_profile_id(cls, value: Any) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("profile_id is required")
        return cleaned

    @field_validator("provider_override", mode="before")
    @classmethod
    def _validate_provider(cls, value: Any) -> str | None:
        cleaned = _clean_text(value)
        return cleaned.lower() if cleaned else None

    @field_validator("model_override", mode="before")
    @classmethod
    def _validate_model(cls, value: Any) -> str | None:
        return _clean_text(value)

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: Any) -> str | None:
        return _clean_text(value)

    @field_validator("mode", mode="before")
    @classmethod
    def _validate_mode(cls, value: Any) -> str | None:
        cleaned = _clean_text(value)
        if not cleaned:
            return None
        normalized = cleaned.lower()
        if normalized in {"local", "cloud"}:
            return normalized
        raise ValueError("mode must be one of: local, cloud")

    @field_validator("system_prompt", mode="before")
    @classmethod
    def _validate_system_prompt(cls, value: Any) -> str | None:
        return _clean_text(value)

    @field_validator("system_prompt_blocks", mode="before")
    @classmethod
    def _validate_blocks(cls, value: Any) -> dict[str, str]:
        return _coerce_profile_blocks(value)

    @field_validator(
        "retrieval_config",
        "tool_permissions",
        "model_config_payload",
        mode="before",
    )
    @classmethod
    def _validate_optional_maps(cls, value: Any) -> dict[str, Any] | None:
        return _coerce_mapping(value)

    @model_validator(mode="after")
    def _normalize_runtime_fields(self) -> SystemProfilePayload:
        self.mode = _normalize_mode(self.mode, self.provider_override)
        if not self.name:
            self.name = _default_profile_name(self.profile_id)
        return self


class ResolvedSystemProfile(SystemProfilePayload):
    """Fully resolved profile payload used by the completion runtime."""

    active_profile_id: str | None = None
    source: str = "default"

    model_config = ConfigDict(extra="forbid")


def _default_profile_catalog() -> dict[str, SystemProfilePayload]:
    local_model = (
        os.getenv("LOCAL_LLM_MODEL")
        or os.getenv("DEFAULT_LOCAL_MODEL")
        or os.getenv("LLM_MODEL")
        or "mlx-community/Llama-3B"
    )
    cloud_provider = (
        os.getenv("LLM_PROVIDER") or os.getenv("CHAT_PROVIDER") or "openai"
    ).strip()
    if cloud_provider.lower() == "local":
        cloud_provider = "openai"
    builtins = [
        {
            "profile_id": "default",
            "name": "Default",
            "mode": "cloud",
            "system_prompt_blocks": {},
        },
        {
            "profile_id": "cloud_mode",
            "name": "Cloud Profile",
            "mode": "cloud",
            "provider_override": cloud_provider,
            "system_prompt_blocks": {
                "behavior": "Prioritize high-capability cloud inference for complex tasks.",
            },
        },
        {
            "profile_id": "local_mode",
            "name": "Local Mode",
            "mode": "local",
            "provider_override": "local",
            "model_override": local_model,
            "temperature_override": 0.4,
            "system_prompt_blocks": {
                "behavior": "Prefer concise execution-oriented reasoning.",
                "constraints": "Prioritize local/offline-friendly behavior where feasible.",
            },
        },
    ]
    catalog: dict[str, SystemProfilePayload] = {}
    for entry in builtins:
        try:
            parsed = SystemProfilePayload.model_validate(entry)
        except ValidationError:
            continue
        catalog[parsed.profile_id] = parsed
    return catalog


def _load_env_catalog() -> dict[str, SystemProfilePayload]:
    raw = (os.getenv("GUARDIAN_SYSTEM_PROFILES_JSON") or "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    if isinstance(payload, dict):
        entries = list(payload.values())
    elif isinstance(payload, list):
        entries = payload
    else:
        return {}

    catalog: dict[str, SystemProfilePayload] = {}
    for entry in entries:
        try:
            parsed = SystemProfilePayload.model_validate(entry)
        except ValidationError:
            continue
        catalog[parsed.profile_id] = parsed
    return catalog


def _profile_catalog() -> dict[str, SystemProfilePayload]:
    catalog = _default_profile_catalog()
    catalog.update(_load_env_catalog())
    if "default" not in catalog:
        catalog["default"] = SystemProfilePayload(
            profile_id="default",
            system_prompt_blocks={},
        )
    return catalog


def _merge_profiles(
    base: SystemProfilePayload | None,
    override: SystemProfilePayload | None,
    *,
    active_profile_id: str | None,
) -> ResolvedSystemProfile:
    merged: dict[str, Any] = {
        "profile_id": active_profile_id or "default",
        "system_prompt_blocks": {},
    }
    source = "default"

    if base is not None:
        merged.update(base.model_dump(mode="json", exclude_none=True))
        source = "catalog"
    if override is not None:
        override_payload = override.model_dump(mode="json", exclude_none=True)
        override_blocks = override_payload.pop("system_prompt_blocks", {})
        merged.update(override_payload)
        merged_blocks = dict(merged.get("system_prompt_blocks") or {})
        merged_blocks.update(override_blocks)
        merged["system_prompt_blocks"] = merged_blocks
        source = "flow_override" if base is None else "catalog+flow_override"

    merged.setdefault("system_prompt_blocks", {})
    merged["active_profile_id"] = active_profile_id or merged.get("profile_id")
    merged["source"] = source
    return ResolvedSystemProfile.model_validate(merged)


def _resolve_chatlog_db(chatlog_db: Any | None) -> Any | None:
    if chatlog_db is not None:
        return chatlog_db
    try:
        from guardian.core import dependencies  # local import to avoid cycles

        return getattr(dependencies, "chatlog_db", None)
    except Exception:
        return None


def _validate_profile_payload(payload: dict[str, Any]) -> SystemProfilePayload:
    return SystemProfilePayload.model_validate(payload or {})


def _save_profile_override(
    *,
    db: Any,
    thread_id: int,
    profile: SystemProfilePayload,
) -> None:
    thread = db.get_chat_thread(thread_id)
    if not thread:
        raise ValueError("thread_not_found")

    metadata = _extract_metadata(thread)
    overrides_raw = metadata.get("profile_overrides")
    if not isinstance(overrides_raw, dict):
        overrides_raw = {}

    overrides_raw[profile.profile_id] = profile.model_dump(
        mode="json", exclude_none=True
    )
    metadata["profile_overrides"] = overrides_raw

    if hasattr(db, "set_thread_profile_overrides"):
        db.set_thread_profile_overrides(thread_id, overrides_raw)
    elif hasattr(db, "update_thread_metadata"):
        db.update_thread_metadata(thread_id, metadata)
    else:
        raise RuntimeError("chat_db_missing_profile_override_persistence")


def _set_active_profile(db: Any, thread_id: int, profile_id: str) -> None:
    if hasattr(db, "set_thread_active_profile_id"):
        updated = db.set_thread_active_profile_id(thread_id, profile_id)
        if not updated:
            raise RuntimeError("active_profile_update_failed")
        return
    if hasattr(db, "update_thread"):
        db.update_thread(
            thread_id,
            active_profile_id=profile_id,
            active_profile_id_set=True,
        )
        return
    raise RuntimeError("chat_db_missing_active_profile_api")


def _override_profiles_for_thread(
    thread: dict[str, Any] | None,
) -> dict[str, SystemProfilePayload]:
    metadata = _extract_metadata(thread)
    overrides_raw = metadata.get("profile_overrides")
    if not isinstance(overrides_raw, dict):
        return {}

    parsed: dict[str, SystemProfilePayload] = {}
    for raw_profile_id, candidate in overrides_raw.items():
        if not isinstance(candidate, dict):
            continue
        with_implicit_id = dict(candidate)
        with_implicit_id.setdefault("profile_id", _clean_text(raw_profile_id))
        try:
            override = SystemProfilePayload.model_validate(with_implicit_id)
        except ValidationError:
            continue
        parsed[override.profile_id] = override
    return parsed


def _fallback_profile_id_if_unavailable(
    profile: SystemProfilePayload,
) -> str | None:
    if profile.mode != "cloud":
        return None

    provider = _clean_text(profile.provider_override)
    if not provider:
        return None
    if provider.lower() == "local":
        return None

    try:
        from guardian.core.config import (
            LLMConfigError,
            get_settings,
            validate_llm_config,
        )
    except Exception:
        return None

    try:
        validate_llm_config(get_settings(), provider_override=provider.lower())
        return None
    except LLMConfigError:
        return "local_mode"
    except Exception:
        return "local_mode"


def list_available_system_profiles(
    *,
    thread_id: int | None = None,
    chatlog_db: Any | None = None,
) -> list[dict[str, Any]]:
    """
    Return available profiles (catalog + thread overrides) as UI-safe summaries.
    """
    db = _resolve_chatlog_db(chatlog_db)
    thread = (
        db.get_chat_thread(thread_id)
        if db is not None and thread_id is not None
        else None
    )

    catalog = _profile_catalog()
    overrides = _override_profiles_for_thread(thread)
    catalog.update(overrides)

    output: list[dict[str, Any]] = []
    for profile_id in sorted(catalog.keys()):
        profile = catalog[profile_id]
        output.append(
            {
                "id": profile.profile_id,
                "profile_id": profile.profile_id,
                "name": profile.name
                or _default_profile_name(profile.profile_id),
                "mode": profile.mode
                or _normalize_mode(None, profile.provider_override),
                "provider_override": profile.provider_override,
                "model_override": profile.model_override,
            }
        )
    return output


def resolve_thread_system_profile(
    thread_id: int,
    *,
    chatlog_db: Any | None = None,
) -> ResolvedSystemProfile:
    """Resolve the active profile for a thread and merge flow overrides."""
    db = _resolve_chatlog_db(chatlog_db)
    thread = db.get_chat_thread(thread_id) if db is not None else None
    active_profile_id = _clean_text(
        thread.get("active_profile_id") if isinstance(thread, dict) else None
    )

    catalog = _profile_catalog()
    base = catalog.get(active_profile_id or "")

    overrides = _override_profiles_for_thread(thread)
    override: SystemProfilePayload | None = None
    if active_profile_id:
        override = overrides.get(active_profile_id)

    if not active_profile_id:
        default_profile = catalog["default"]
        return ResolvedSystemProfile.model_validate(
            {
                **default_profile.model_dump(mode="json"),
                "active_profile_id": None,
                "source": "default",
            }
        )
    return _merge_profiles(
        base,
        override,
        active_profile_id=active_profile_id,
    )


def persist_flow_profile_override(
    thread_id: int,
    profile_override_payload: dict[str, Any],
    *,
    chatlog_db: Any | None = None,
) -> ResolvedSystemProfile:
    """
    Persist a flow-produced profile override and activate it on the thread.
    """
    db = _resolve_chatlog_db(chatlog_db)
    if db is None:
        raise RuntimeError("chat_db_unavailable")

    parsed = _validate_profile_payload(profile_override_payload)
    fallback_profile_id = _fallback_profile_id_if_unavailable(parsed)
    _save_profile_override(db=db, thread_id=thread_id, profile=parsed)
    _set_active_profile(db, thread_id, fallback_profile_id or parsed.profile_id)
    return resolve_thread_system_profile(thread_id, chatlog_db=db)


def switch_thread_profile(
    thread_id: int,
    profile_id: str,
    *,
    chatlog_db: Any | None = None,
) -> ResolvedSystemProfile:
    """Switch active profile for a thread."""
    db = _resolve_chatlog_db(chatlog_db)
    if db is None:
        raise RuntimeError("chat_db_unavailable")
    cleaned = _clean_text(profile_id)
    if not cleaned:
        raise ValueError("profile_id is required")

    thread = (
        db.get_chat_thread(thread_id)
        if hasattr(db, "get_chat_thread")
        else None
    )
    catalog = _profile_catalog()
    overrides = _override_profiles_for_thread(thread)
    candidate = overrides.get(cleaned) or catalog.get(cleaned)
    if candidate is None:
        raise ValueError(f"unknown_profile_id:{cleaned}")
    fallback_profile_id = _fallback_profile_id_if_unavailable(candidate)

    _set_active_profile(db, thread_id, fallback_profile_id or cleaned)
    return resolve_thread_system_profile(thread_id, chatlog_db=db)
