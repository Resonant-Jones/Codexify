"""
Lightweight user settings store.

For now this is an in-memory shim to gate identity writes by memory_mode and diary settings.
In production, replace with durable persistence.
"""

from __future__ import annotations

from typing import Dict

_settings: dict[str, dict] = {}


def get_user_settings(user_id: str) -> dict:
    """Return settings for a user; defaults to deep memory mode."""
    return _settings.get(
        user_id,
        {
            "memory_mode": "deep",
            "diary_requires_unlock": False,
            "allow_sensitive_modeling": False,
        },
    )


def set_user_settings(user_id: str, settings: dict) -> None:
    """Set settings (test helper / future persistence hook)."""
    _settings[user_id] = dict(settings)


__all__ = ["get_user_settings", "set_user_settings"]
