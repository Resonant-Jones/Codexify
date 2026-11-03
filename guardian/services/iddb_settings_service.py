"""
Durable user-global IDDB settings service.

This is the backend authority for identity-modeling policy controls.

It is also the backend authority for the account's explicit consent to
automatic Personal Fact collection.  That consent is deliberately kept on its
own seam: it is never inferred from ``memory_mode`` (an identity-modeling
depth control), never inherited from the legacy ``default`` compatibility row,
and never writable through the identity settings payload.
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
from guardian.protocol_tokens import (
    AUTOMATIC_MEMORY_SUGGESTIONS_CONSENT_STATES,
    AutomaticMemorySuggestionsConsent,
)

DEFAULT_COMPATIBILITY_USER_ID = "default"
DEFAULT_SETTINGS: dict[str, Any] = {
    "memory_mode": "deep",
    "diary_requires_unlock": False,
    "allow_sensitive_modeling": False,
}
VALID_MEMORY_MODES = {"none", "light", "deep"}

# Server-controlled consent policy version.  A consent record only grants
# collection while it carries this version; a record written under an older
# policy is treated as not granted.
CONSENT_POLICY_VERSION = "1"

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


# ── Automatic collection consent ──────────────────────────────────────
#
# Consent to automatic Personal Fact collection is account-owned, durable,
# versioned and attributable.  It is deliberately separate from the identity
# settings payload above: `memory_mode` must never be reused as collection
# consent, and the identity settings write path can never overwrite it.


def _normalize_consent_state(value: Any) -> str:
    state = str(value if value is not None else "").strip().lower()
    if state not in AUTOMATIC_MEMORY_SUGGESTIONS_CONSENT_STATES:
        raise ValueError("invalid automatic_memory_suggestions state")
    return state


def _iso_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    try:
        return value.isoformat()
    except Exception:  # pragma: no cover - defensive
        return None


def _denied_consent_record(reason: str) -> dict[str, Any]:
    """Return the fail-closed consent record for a denied state."""
    return {
        "state": AutomaticMemorySuggestionsConsent.UNSET.value,
        "policy_version": CONSENT_POLICY_VERSION,
        "recorded_by_user_id": None,
        "recorded_at": None,
        "updated_at": None,
        "effective": False,
        "reason": reason,
    }


def _serialize_consent(
    row: UserSettings | None, *, resolved_user: str
) -> dict[str, Any]:
    """
    Serialize a durable consent row into an effective consent record.

    Fail-closed: a missing row, an unrecognized state, a stale policy
    version, or a record that was not attributed to this account never
    grants collection.
    """
    if row is None:
        return _denied_consent_record("unset")

    raw_state = str(row.automatic_memory_suggestions or "").strip().lower()
    if raw_state not in AUTOMATIC_MEMORY_SUGGESTIONS_CONSENT_STATES:
        return _denied_consent_record("invalid_state")

    policy_version = str(row.consent_policy_version or "").strip()
    recorded_by = str(row.consent_recorded_by_user_id or "").strip() or None

    effective = False
    reason = raw_state
    if raw_state == AutomaticMemorySuggestionsConsent.ENABLED.value:
        if policy_version != CONSENT_POLICY_VERSION:
            reason = "stale_policy_version"
        elif not recorded_by:
            reason = "not_recorded"
        elif recorded_by != resolved_user:
            # Consent must have been recorded by this account.  A record
            # attributed to any other principal cannot grant collection.
            reason = "actor_mismatch"
        else:
            effective = True

    return {
        "state": raw_state,
        "policy_version": policy_version or CONSENT_POLICY_VERSION,
        "recorded_by_user_id": recorded_by,
        "recorded_at": _iso_timestamp(row.consent_recorded_at),
        "updated_at": _iso_timestamp(row.consent_updated_at),
        "effective": effective,
        "reason": reason,
    }


def read_automatic_memory_suggestions_consent(user_id: str) -> dict[str, Any]:
    """
    Return the account's durable consent record for automatic collection.

    The legacy `default` compatibility row is never consulted: consent is
    account-owned, so a shared fallback row can neither be inherited from nor
    confer consent to an ambiguous identity.
    """
    resolved_user = _normalize_user_id(user_id)
    if resolved_user == DEFAULT_COMPATIBILITY_USER_ID:
        return _denied_consent_record("ambiguous_account")

    Session = _get_session_factory()
    with Session() as session:
        row = session.get(UserSettings, resolved_user)
        return _serialize_consent(row, resolved_user=resolved_user)


def set_automatic_memory_suggestions_consent(
    user_id: str,
    state: str,
    *,
    actor_user_id: str,
) -> dict[str, Any]:
    """
    Record the account's explicit consent choice.

    Account identity, actor identity, consent policy version and timestamps
    are all server-derived.  A caller may supply only the consent state.
    """
    resolved_user = _assert_mutation_user_id(user_id)
    resolved_actor = _normalize_user_id(actor_user_id)
    if resolved_actor != resolved_user:
        raise HTTPException(
            status_code=403,
            detail="consent actor must match the authenticated account",
        )
    try:
        next_state = _normalize_consent_state(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    Session = _get_session_factory()
    now = datetime.now(timezone.utc)
    with Session() as session:
        row = session.get(UserSettings, resolved_user)
        if row is None:
            row = UserSettings(user_id=resolved_user)
            session.add(row)
        row.automatic_memory_suggestions = next_state
        row.consent_policy_version = CONSENT_POLICY_VERSION
        row.consent_recorded_by_user_id = resolved_actor
        if getattr(row, "consent_recorded_at", None) is None:
            row.consent_recorded_at = now
        row.consent_updated_at = now
        row.updated_at = now
        if getattr(row, "created_at", None) is None:
            row.created_at = now
        session.commit()
        session.refresh(row)
        return _serialize_consent(row, resolved_user=resolved_user)


def is_automatic_memory_collection_enabled(user_id: str) -> bool:
    """
    Fail-closed effective-consent check for automatic collection.

    Returns True only when the account explicitly recorded `enabled` consent
    under the current policy version.  Missing, invalid, stale, ambiguous or
    unreadable consent denies collection.
    """
    try:
        record = read_automatic_memory_suggestions_consent(user_id)
    except Exception:
        return False
    return bool(record.get("effective"))


__all__ = [
    "DEFAULT_COMPATIBILITY_USER_ID",
    "DEFAULT_SETTINGS",
    "CONSENT_POLICY_VERSION",
    "get_user_settings",
    "is_automatic_memory_collection_enabled",
    "normalize_settings_payload",
    "read_automatic_memory_suggestions_consent",
    "set_automatic_memory_suggestions_consent",
    "upsert_user_settings",
    "_set_session_factory",
]
