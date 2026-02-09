"""In-memory registry for channel adapters."""

from __future__ import annotations

from typing import Dict

from guardian.channels.base import Adapter

_ADAPTERS: Dict[str, Adapter] = {}


def register_adapter(adapter: Adapter) -> None:
    adapter_id = adapter.adapter_id.strip()
    if not adapter_id:
        raise ValueError("adapter_id must be non-empty")
    if adapter_id in _ADAPTERS:
        raise ValueError(f"adapter already registered: {adapter_id}")
    _ADAPTERS[adapter_id] = adapter


def get_adapter(adapter_id: str) -> Adapter:
    try:
        return _ADAPTERS[adapter_id]
    except KeyError as exc:
        raise KeyError(f"unknown adapter: {adapter_id}") from exc


def list_adapters() -> list[str]:
    return sorted(_ADAPTERS.keys())


def clear_adapters() -> None:
    """Test helper to reset global adapter registry."""

    _ADAPTERS.clear()

