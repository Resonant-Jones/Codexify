"""
Durable user-global IDDB settings service.

This is the backend authority for identity-modeling policy controls.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import UserSettings

DEFAULT_COMPATIBILITY_USER_ID = "default"
DEFAULT_SETTINGS: dict[str, Any] = {
    "memory_mode": "deep",
    "diary_requires_unlock": False,
    "allow_sensitive_modeling": False,
}
VALID_MEMORY_MODES = {"none", "light", "deep"}

_SessionFactory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    """Return a cached Session factory backed by the configured DSN."""
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory

    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access IDDB settings."
        )

    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _SessionFactory


def _set_session_factory(factory: sessionmaker) -> None:
    """Test hook to override the session factory."""
    global _SessionFactory
    _SessionFactory = factory


def _normalize_user_id(user_id: str) -> str:
    resolved = str(user_id or "").strip()
    if not resolved:
        raise HTTPException(
            status_code=403, detail="current user could not be resolved"
        )
    return resolved


def _assert_mutation_user_id(user_id: str) -> str:
    resolved = _normalize_user_id(user_id)
    if resolved == DEFAULT_COMPATIBILITY_USER_ID:
        raise HTTPException(
            status_code=403,
            detail="default is read-only compatibility fallback",
        )
    return resolved


def _coerce_bool(value: Any, fallback: bool) -> bool:
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_memory_mode(value: Any, fallback: str) -> str:
    mode = str(value if value is not None else fallback).strip().lower()
    if mode not in VALID_MEMORY_MODES:
        raise ValueError("invalid memory_mode")
    return mode


def _serialize_settings(row: UserSettings | None) -> dict[str, Any]:
    if row is None:
        return dict(DEFAULT_SETTINGS)
    return {
        "memory_mode": row.memory_mode or DEFAULT_SETTINGS["memory_mode"],
        "diary_requires_unlock": bool(row.diary_requires_unlock),
        "allow_sensitive_modeling": bool(row.allow_sensitive_modeling),
    }


def normalize_settings_payload(
    payload: Mapping[str, Any],
    *,
    base: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = dict(base or DEFAULT_SETTINGS)
    next_settings = {
        "memory_mode": _normalize_memory_mode(
            payload.get("memory_mode", current["memory_mode"]),
            str(current["memory_mode"]),
        ),
        "diary_requires_unlock": _coerce_bool(
            payload.get("diary_requires_unlock"),
            bool(current["diary_requires_unlock"]),
        ),
        "allow_sensitive_modeling": _coerce_bool(
            payload.get("allow_sensitive_modeling"),
            bool(current["allow_sensitive_modeling"]),
        ),
    }
    return next_settings


def get_user_settings(
    user_id: str,
    *,
    allow_legacy_default_fallback: bool = True,
) -> dict[str, Any]:
    """
    Return durable policy settings for a user.

    The compatibility fallback to `default` is read-only and isolated here.
    """
    resolved_user = _normalize_user_id(user_id)
    Session = _get_session_factory()
    with Session() as session:
        row = session.get(UserSettings, resolved_user)
        if row is not None:
            return _serialize_settings(row)

        if (
            allow_legacy_default_fallback
            and resolved_user != DEFAULT_COMPATIBILITY_USER_ID
        ):
            legacy_row = session.get(
                UserSettings, DEFAULT_COMPATIBILITY_USER_ID
            )
            if legacy_row is not None:
                return _serialize_settings(legacy_row)

    return dict(DEFAULT_SETTINGS)


def upsert_user_settings(
    user_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Persist user-global policy settings.

    Mutable writes must never target `default`.
    """
    resolved_user = _assert_mutation_user_id(user_id)
    base_settings = get_user_settings(
        resolved_user, allow_legacy_default_fallback=False
    )
    next_settings = normalize_settings_payload(
        payload,
        base=base_settings,
    )

    Session = _get_session_factory()
    now = datetime.now(timezone.utc)
    with Session() as session:
        row = session.get(UserSettings, resolved_user)
        if row is None:
            row = UserSettings(user_id=resolved_user)
            session.add(row)
        row.memory_mode = next_settings["memory_mode"]
        row.diary_requires_unlock = bool(next_settings["diary_requires_unlock"])
        row.allow_sensitive_modeling = bool(
            next_settings["allow_sensitive_modeling"]
        )
        # Keep timestamps fresh for auditability; DB defaults also apply on create.
        row.updated_at = now
        if getattr(row, "created_at", None) is None:
            row.created_at = now
        session.commit()
        session.refresh(row)
        return _serialize_settings(row)


__all__ = [
    "DEFAULT_COMPATIBILITY_USER_ID",
    "DEFAULT_SETTINGS",
    "get_user_settings",
    "normalize_settings_payload",
    "upsert_user_settings",
    "_set_session_factory",
]
