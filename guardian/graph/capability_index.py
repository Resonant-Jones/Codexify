"""Capability index and event tracking for Guardian."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from guardian.core import event_bus

CAPABILITY_EVENT_TOPICS: dict[str, dict[str, str]] = {
    "plugin.installed": {
        "category": "plugins",
        "timestamp_key": "installed_at",
    },
    "plugin.removed": {"category": "plugins", "timestamp_key": "removed_at"},
    "connector.installed": {
        "category": "connectors",
        "timestamp_key": "installed_at",
    },
    "connector.removed": {
        "category": "connectors",
        "timestamp_key": "removed_at",
    },
    "mcp.installed": {"category": "mcps", "timestamp_key": "installed_at"},
    "mcp.removed": {"category": "mcps", "timestamp_key": "removed_at"},
}

DEFAULT_CORE_CAPABILITIES: list[dict[str, Any]] = [
    {
        "id": "chat",
        "triggers": ["chat", "message", "assistant"],
        "help": "General conversation, reasoning, and assistance.",
    },
    {
        "id": "rag_uploads",
        "triggers": ["upload", "document", "rag"],
        "help": "Use uploaded or retrieved context when provided.",
    },
]

_capability_event_cache: list[dict[str, Any]] = []


def _to_iso8601(value: Any | None = None) -> str:
    """Coerce datetime-like values to ISO 8601 (UTC, Z-suffixed)."""
    if isinstance(value, datetime):
        dt = value.astimezone(timezone.utc)
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except Exception:
            return value
    else:
        dt = datetime.now(timezone.utc)

    iso = dt.isoformat()
    return iso.replace("+00:00", "Z")


def reset_capability_event_cache() -> None:
    """Test helper to clear in-memory capability events."""
    _capability_event_cache.clear()


def record_capability_event(
    event_type: str,
    *,
    name: str,
    display_name: str | None = None,
    version: str | None = None,
    capabilities: list[str] | None = None,
    help_triggers: list[str] | None = None,
    help_text_ref: str | None = None,
    timestamp: Any | None = None,
    tenant_id: str = "default",
) -> dict[str, Any]:
    """Emit and cache capability lifecycle events (install/remove)."""
    if event_type not in CAPABILITY_EVENT_TOPICS:
        raise ValueError(f"Unsupported capability event type: {event_type}")

    ts_field = CAPABILITY_EVENT_TOPICS[event_type]["timestamp_key"]
    ts_value = _to_iso8601(timestamp)

    payload: dict[str, Any] = {
        "name": name,
        "display_name": display_name or name,
        "version": version,
        "capabilities": capabilities or [],
        "help_triggers": help_triggers or [],
        "help_text_ref": help_text_ref,
        ts_field: ts_value,
    }

    try:
        event_bus.emit_event(event_type, payload, tenant_id=tenant_id)
    except Exception:
        # Emit failures should never block capability tracking; rely on cache.
        pass

    _capability_event_cache.append(
        {
            "topic": event_type,
            "payload": payload,
            "tenant_id": tenant_id,
            "created_at": ts_value,
        }
    )
    return payload


def _fetch_events_from_store(tenant_id: str) -> list[dict[str, Any]]:
    """Return capability events from the durable event store when available."""
    if not event_bus.is_persistent_enabled():
        return []

    events: list[dict[str, Any]] = []
    last_id = 0
    batch_size = 500
    while True:
        batch = event_bus.fetch_events_after(last_id, limit=batch_size)
        if not batch:
            break
        for ev in batch:
            if ev.get("tenant_id") and ev.get("tenant_id") != tenant_id:
                continue
            if ev.get("topic") not in CAPABILITY_EVENT_TOPICS:
                continue
            events.append(ev)
        last_id = batch[-1].get("id") or last_id
        if len(batch) < batch_size:
            break
    return events


def _combine_events(
    store_events: Iterable[dict[str, Any]],
    cached_events: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge store-backed and cached events without duplicates."""
    combined: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for ev in list(store_events) + list(cached_events):
        payload = ev.get("payload") or {}
        key = (
            ev.get("topic"),
            payload.get("name"),
            payload.get("installed_at"),
            payload.get("removed_at"),
            ev.get("created_at"),
        )
        if key in seen:
            continue
        seen.add(key)
        combined.append(ev)
    return combined


def _event_time_key(ev: dict[str, Any]) -> datetime:
    payload = ev.get("payload") or {}
    for key in ("installed_at", "removed_at"):
        ts = payload.get(key)
        if ts:
            try:
                return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except Exception:
                break
    created = ev.get("created_at")
    if created:
        try:
            return datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        except Exception:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def _state_from_events(
    events: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, set[str]]]:
    """Return active capability state and removed markers derived from events."""
    state: dict[str, dict[str, dict[str, Any]]] = {
        "plugins": {},
        "connectors": {},
        "mcps": {},
    }
    removed: dict[str, set[str]] = {
        "plugins": set(),
        "connectors": set(),
        "mcps": set(),
    }

    for ev in sorted(events, key=_event_time_key):
        topic = ev.get("topic")
        meta = CAPABILITY_EVENT_TOPICS.get(topic or "")
        if not meta:
            continue
        payload = dict(ev.get("payload") or {})
        name = payload.get("name")
        if not name:
            continue

        category = meta["category"]
        ts_field = meta["timestamp_key"]
        timestamp = _to_iso8601(payload.get(ts_field) or ev.get("created_at"))

        if topic.endswith(".installed"):
            removed[category].discard(name)
            state[category][name] = {
                "id": name,
                "display_name": payload.get("display_name") or name,
                "version": payload.get("version"),
                "capabilities": payload.get("capabilities") or [],
                "help_triggers": payload.get("help_triggers") or [],
                "help_text_ref": payload.get("help_text_ref"),
                ts_field: timestamp,
            }
        else:
            state[category].pop(name, None)
            removed[category].add(name)
    return state, removed


def _augment_plugins(
    state: dict[str, dict[str, dict[str, Any]]],
    removed: dict[str, set[str]],
    plugin_loader: Any = None,
) -> None:
    """Merge active plugins from canonical service manifests into state."""

    def _get_value(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _manifest_capability_fields(
        manifest: Any,
    ) -> tuple[list[str], list[str]]:
        capabilities: set[str] = set()
        help_triggers: set[str] = set()
        for capability in _get_value(manifest, "capabilities", []) or []:
            if isinstance(capability, str):
                capability_id = capability
                actions: list[Any] = []
            elif isinstance(capability, dict):
                capability_id = capability.get("id")
                actions = capability.get("actions", []) or []
            else:
                capability_id = getattr(capability, "id", None)
                actions = getattr(capability, "actions", []) or []
            if not capability_id:
                continue
            help_triggers.add(str(capability_id))
            for action in actions:
                if action:
                    capabilities.add(f"{capability_id}.{action}")
            if not actions:
                capabilities.add(str(capability_id))
        return sorted(capabilities), sorted(help_triggers)

    manifests: list[Any] = []
    source = plugin_loader
    if source is None:
        try:
            from guardian.core.plugins import list_plugin_manifests

            manifests = list_plugin_manifests()
        except Exception:
            manifests = []
    elif hasattr(source, "list_plugin_manifests"):
        manifests = list(source.list_plugin_manifests())
    elif isinstance(source, (list, tuple, set)):
        manifests = list(source)
    else:
        manifests = []

    for manifest in manifests:
        plugin_id = _get_value(manifest, "id")
        if not plugin_id or plugin_id in removed["plugins"]:
            continue

        manifest_capabilities, help_triggers = _manifest_capability_fields(
            manifest
        )
        entry = state["plugins"].get(plugin_id, {"id": plugin_id})
        entry["display_name"] = (
            _get_value(manifest, "name", plugin_id) or plugin_id
        )
        entry["version"] = _get_value(manifest, "version")
        entry["capabilities"] = manifest_capabilities
        entry["help_triggers"] = help_triggers
        entry.setdefault("help_text_ref", None)
        entry.setdefault("installed_at", _to_iso8601())
        state["plugins"][plugin_id] = entry


def _coerce_connector_configs(source: Any) -> list[dict[str, Any]]:
    if source is None:
        return []
    if hasattr(source, "list_connector_configs_with_last_run"):
        return source.list_connector_configs_with_last_run()  # type: ignore[no-any-return]
    if hasattr(source, "list_connector_configs"):
        return source.list_connector_configs()  # type: ignore[no-any-return]
    return []


def _augment_connectors(
    state: dict[str, dict[str, dict[str, Any]]],
    removed: dict[str, set[str]],
    connector_source: Any = None,
) -> None:
    configs = _coerce_connector_configs(connector_source)
    for cfg in configs:
        name = cfg.get("name")
        if not name or name in removed["connectors"]:
            continue
        entry = state["connectors"].get(name, {"id": name})
        entry.setdefault(
            "display_name", cfg.get("display_name") or cfg.get("name")
        )
        entry.setdefault(
            "version",
            cfg.get("version")
            or cfg.get("type")
            or (cfg.get("settings") or {}).get("version"),
        )
        entry.setdefault(
            "capabilities",
            cfg.get("capabilities")
            or (cfg.get("settings") or {}).get("capabilities")
            or [],
        )
        entry.setdefault(
            "help_triggers",
            cfg.get("help_triggers") or [cfg.get("type")]
            if cfg.get("type")
            else [],
        )
        entry.setdefault("installed_at", _to_iso8601(cfg.get("created_at")))
        state["connectors"][name] = entry


def list_capability_events(tenant_id: str = "default") -> list[dict[str, Any]]:
    """Return capability events from the persistent store or in-memory cache."""
    store_events = _fetch_events_from_store(tenant_id)
    cached_events = [
        ev for ev in _capability_event_cache if ev.get("tenant_id") == tenant_id
    ]
    return sorted(
        _combine_events(store_events, cached_events),
        key=_event_time_key,
    )


def query_capability_events(
    name: str, tenant_id: str = "default"
) -> list[dict[str, Any]]:
    """Return capability lifecycle events for a given capability name."""
    events = []
    for ev in list_capability_events(tenant_id):
        payload = ev.get("payload") or {}
        if payload.get("name") == name:
            events.append(ev)
    return sorted(events, key=_event_time_key)


def get_capability_index(
    *,
    plugin_loader: Any = None,
    connector_source: Any = None,
    core_capabilities: list[dict[str, Any]] | None = None,
    tenant_id: str = "default",
) -> dict[str, list[dict[str, Any]]]:
    """
    Materialize a compact capability index for the prompt layer.

    Combines persisted capability events with live plugin/connector state.
    """
    events = list_capability_events(tenant_id)
    state, removed = _state_from_events(events)

    _augment_plugins(state, removed, plugin_loader)
    _augment_connectors(state, removed, connector_source)

    return {
        "core": core_capabilities or DEFAULT_CORE_CAPABILITIES,
        "plugins": list(state["plugins"].values()),
        "connectors": list(state["connectors"].values()),
        "mcps": list(state["mcps"].values()),
    }


__all__ = [
    "CAPABILITY_EVENT_TOPICS",
    "DEFAULT_CORE_CAPABILITIES",
    "get_capability_index",
    "list_capability_events",
    "query_capability_events",
    "record_capability_event",
    "reset_capability_event_cache",
]
