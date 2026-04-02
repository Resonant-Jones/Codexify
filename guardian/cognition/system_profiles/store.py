"""Backend-backed persona profile persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import PersonaProfile

_SessionFactory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    """Return a cached Session factory backed by the configured DSN."""
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot access persona profiles."
        )
    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _SessionFactory


def _set_session_factory(factory: sessionmaker | None) -> None:
    """Test hook to override the session factory."""
    global _SessionFactory
    _SessionFactory = factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_provider(value: Any) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        raise ValueError("model_provider is required")
    return cleaned.lower()


def _normalize_temperature(value: Any) -> float:
    try:
        temperature = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("temperature must be a number") from exc
    if temperature < 0.0 or temperature > 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")
    return temperature


def persona_profile_to_dict(profile: PersonaProfile) -> dict[str, Any]:
    """Serialize a persona profile row for API responses."""
    return {
        "id": profile.id,
        "name": profile.name,
        "system_prompt": profile.system_prompt,
        "model_provider": profile.model_provider,
        "model_id": profile.model_id,
        "temperature": float(profile.temperature),
        "created_at": (
            profile.created_at.isoformat()
            if isinstance(profile.created_at, datetime)
            else None
        ),
        "updated_at": (
            profile.updated_at.isoformat()
            if isinstance(profile.updated_at, datetime)
            else None
        ),
    }


def list_persona_profiles() -> list[PersonaProfile]:
    """List persona profiles newest-first by creation time."""
    Session = _get_session_factory()
    with Session() as session:
        stmt = select(PersonaProfile).order_by(
            PersonaProfile.created_at.asc(),
            PersonaProfile.id.asc(),
        )
        return list(session.scalars(stmt))


def get_persona_profile_by_id(profile_id: str) -> PersonaProfile | None:
    """Fetch one persona profile by id."""
    cleaned = _clean_text(profile_id)
    if not cleaned:
        return None
    Session = _get_session_factory()
    with Session() as session:
        return session.get(PersonaProfile, cleaned)


def create_persona_profile(
    *,
    profile_id: str | None = None,
    name: str,
    system_prompt: str,
    model_provider: str,
    model_id: str,
    temperature: float,
) -> PersonaProfile:
    """Create a persona profile row."""
    cleaned_id = _clean_text(profile_id) or f"persona-{uuid4().hex}"
    cleaned_name = _clean_text(name)
    cleaned_prompt = _clean_text(system_prompt)
    cleaned_model_id = _clean_text(model_id)
    if not cleaned_name:
        raise ValueError("name is required")
    if not cleaned_prompt:
        raise ValueError("system_prompt is required")
    if not cleaned_model_id:
        raise ValueError("model_id is required")

    Session = _get_session_factory()
    with Session() as session:
        profile = PersonaProfile(
            id=cleaned_id,
            name=cleaned_name,
            system_prompt=cleaned_prompt,
            model_provider=_normalize_provider(model_provider),
            model_id=cleaned_model_id,
            temperature=_normalize_temperature(temperature),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        session.add(profile)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError(f"persona_profile_exists:{cleaned_id}") from exc
        session.refresh(profile)
        return profile


def update_persona_profile(
    profile_id: str,
    *,
    name: str | None = None,
    system_prompt: str | None = None,
    model_provider: str | None = None,
    model_id: str | None = None,
    temperature: float | None = None,
) -> PersonaProfile:
    """Update the first-wave persona fields for a profile."""
    cleaned_id = _clean_text(profile_id)
    if not cleaned_id:
        raise ValueError("profile_id is required")

    Session = _get_session_factory()
    with Session() as session:
        profile = session.get(PersonaProfile, cleaned_id)
        if profile is None:
            raise ValueError(f"persona_profile_not_found:{cleaned_id}")

        if name is not None:
            cleaned_name = _clean_text(name)
            if not cleaned_name:
                raise ValueError("name is required")
            profile.name = cleaned_name
        if system_prompt is not None:
            cleaned_prompt = _clean_text(system_prompt)
            if not cleaned_prompt:
                raise ValueError("system_prompt is required")
            profile.system_prompt = cleaned_prompt
        if model_provider is not None:
            profile.model_provider = _normalize_provider(model_provider)
        if model_id is not None:
            cleaned_model_id = _clean_text(model_id)
            if not cleaned_model_id:
                raise ValueError("model_id is required")
            profile.model_id = cleaned_model_id
        if temperature is not None:
            profile.temperature = _normalize_temperature(temperature)
        profile.updated_at = _utcnow()

        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile


__all__ = [
    "create_persona_profile",
    "get_persona_profile_by_id",
    "list_persona_profiles",
    "persona_profile_to_dict",
    "update_persona_profile",
    "_set_session_factory",
]
