"""Account-scoped Persona Profile manifest persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from guardian.cognition.system_profiles.manifest import (
    PersonaProfileManifest,
    PersonaProfileManifestWrite,
    assign_manifest_revision,
    authored_manifest_dict,
    build_legacy_manifest,
    persisted_manifest_dict,
)
from guardian.core.dependencies import get_database_dsn
from guardian.db.models import (
    PersonaProfile,
    PersonaProfileBinding,
    PersonaProfileRevision,
    User,
)

_SessionFactory: sessionmaker | None = None


@dataclass(frozen=True)
class StoredPersonaProfile:
    """Detached current snapshot returned by the persistence boundary."""

    id: str
    name: str
    system_prompt: str
    model_provider: str
    model_id: str
    temperature: float
    current_revision: int
    manifest: PersonaProfileManifest
    created_at: datetime | None
    updated_at: datetime | None


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


def _require_account_id(value: Any) -> str:
    account_id = _clean_text(value)
    if not account_id:
        raise ValueError("account_id is required")
    return account_id


def _normalize_temperature(value: Any) -> float:
    try:
        temperature = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("temperature must be a number") from exc
    if temperature < 0.0 or temperature > 2.0:
        raise ValueError("temperature must be between 0.0 and 2.0")
    return temperature


def _validate_manifest_write(
    manifest: PersonaProfileManifestWrite | dict[str, Any],
) -> PersonaProfileManifestWrite:
    if isinstance(manifest, PersonaProfileManifestWrite):
        return PersonaProfileManifestWrite.model_validate(
            manifest.model_dump(mode="python", by_alias=True, exclude_none=True)
        )
    return PersonaProfileManifestWrite.model_validate(manifest)


def _legacy_manifest(
    *,
    profile_id: str,
    name: Any,
    system_prompt: Any,
    model_provider: Any,
    model_id: Any,
    temperature: Any,
) -> PersonaProfileManifestWrite:
    cleaned_name = _clean_text(name)
    cleaned_prompt = _clean_text(system_prompt)
    cleaned_provider = _clean_text(model_provider)
    cleaned_model_id = _clean_text(model_id)
    if not cleaned_name:
        raise ValueError("name is required")
    if not cleaned_prompt:
        raise ValueError("system_prompt is required")
    if not cleaned_provider:
        raise ValueError("model_provider is required")
    if not cleaned_model_id:
        raise ValueError("model_id is required")
    return build_legacy_manifest(
        profile_identity=profile_id,
        name=cleaned_name,
        system_prompt=cleaned_prompt,
        model_provider=cleaned_provider.lower(),
        model_id=cleaned_model_id,
        temperature=_normalize_temperature(temperature),
    )


def _revision_row(
    session: Session,
    profile: PersonaProfile,
) -> PersonaProfileRevision:
    revision = session.get(
        PersonaProfileRevision,
        {
            "profile_id": profile.id,
            "revision": profile.current_revision,
        },
    )
    if revision is None:
        raise RuntimeError(f"persona_profile_current_revision_missing:{profile.id}")
    return revision


def _snapshot(
    profile: PersonaProfile,
    revision: PersonaProfileRevision,
) -> StoredPersonaProfile:
    manifest = PersonaProfileManifest.model_validate(revision.manifest_json)
    if (
        manifest.profile_identity != profile.id
        or manifest.revision != profile.current_revision
        or manifest.api_version != revision.api_version
    ):
        raise RuntimeError(f"persona_profile_revision_mismatch:{profile.id}")
    return StoredPersonaProfile(
        id=profile.id,
        name=profile.name,
        system_prompt=profile.system_prompt,
        model_provider=profile.model_provider,
        model_id=profile.model_id,
        temperature=float(profile.temperature),
        current_revision=profile.current_revision,
        manifest=manifest,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _apply_projection(
    profile: PersonaProfile,
    manifest: PersonaProfileManifestWrite,
) -> None:
    profile.name = manifest.identity.name
    profile.system_prompt = manifest.prompt.system_prompt
    profile.model_provider = manifest.model.provider
    profile.model_id = manifest.model.model
    profile.temperature = manifest.model.temperature


def _current_profile_statement(account_id: str, profile_id: str | None = None):
    statement = (
        select(PersonaProfile, PersonaProfileRevision)
        .join(
            PersonaProfileBinding,
            PersonaProfileBinding.profile_id == PersonaProfile.id,
        )
        .join(
            PersonaProfileRevision,
            and_(
                PersonaProfileRevision.profile_id == PersonaProfile.id,
                PersonaProfileRevision.revision == PersonaProfile.current_revision,
            ),
        )
        .where(PersonaProfileBinding.owner_account_id == account_id)
    )
    if profile_id is not None:
        statement = statement.where(PersonaProfile.id == profile_id)
    return statement


def persona_profile_to_dict(profile: StoredPersonaProfile) -> dict[str, Any]:
    """Serialize a current profile snapshot without exposing its binding."""
    return {
        "id": profile.id,
        "name": profile.name,
        "system_prompt": profile.system_prompt,
        "model_provider": profile.model_provider,
        "model_id": profile.model_id,
        "temperature": profile.temperature,
        "api_version": profile.manifest.api_version,
        "current_revision": profile.current_revision,
        "manifest": persisted_manifest_dict(profile.manifest),
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


def list_persona_profiles(*, account_id: str) -> list[StoredPersonaProfile]:
    """List only profiles bound to the supplied canonical account."""
    cleaned_account_id = _require_account_id(account_id)
    SessionFactory = _get_session_factory()
    with SessionFactory() as session:
        statement = _current_profile_statement(cleaned_account_id).order_by(
            PersonaProfile.created_at.asc(),
            PersonaProfile.id.asc(),
        )
        return [
            _snapshot(profile, revision)
            for profile, revision in session.execute(statement).all()
        ]


def get_persona_profile_by_id(
    profile_id: str,
    *,
    account_id: str,
) -> StoredPersonaProfile | None:
    """Fetch a profile only through its owning-account binding."""
    cleaned_account_id = _require_account_id(account_id)
    cleaned_profile_id = _clean_text(profile_id)
    if not cleaned_profile_id:
        return None
    SessionFactory = _get_session_factory()
    with SessionFactory() as session:
        row = session.execute(
            _current_profile_statement(
                cleaned_account_id,
                cleaned_profile_id,
            )
        ).one_or_none()
        if row is None:
            return None
        return _snapshot(row[0], row[1])


def get_current_persona_profile_manifest(
    profile_id: str,
    *,
    account_id: str,
) -> PersonaProfileManifest | None:
    """Read the account-scoped current immutable manifest."""
    profile = get_persona_profile_by_id(profile_id, account_id=account_id)
    return profile.manifest if profile is not None else None


def create_persona_profile(
    *,
    account_id: str,
    manifest: PersonaProfileManifestWrite | dict[str, Any] | None = None,
    profile_id: str | None = None,
    name: str | None = None,
    system_prompt: str | None = None,
    model_provider: str | None = None,
    model_id: str | None = None,
    temperature: float | None = None,
) -> StoredPersonaProfile:
    """Atomically create registry, binding, and immutable revision 1."""
    cleaned_account_id = _require_account_id(account_id)
    if manifest is not None:
        if any(
            value is not None
            for value in (
                profile_id,
                name,
                system_prompt,
                model_provider,
                model_id,
                temperature,
            )
        ):
            raise ValueError("manifest and legacy fields may not be mixed")
        write_manifest = _validate_manifest_write(manifest)
        cleaned_profile_id = write_manifest.profile_identity
    else:
        cleaned_profile_id = _clean_text(profile_id) or f"persona-{uuid4().hex}"
        write_manifest = _legacy_manifest(
            profile_id=cleaned_profile_id,
            name=name,
            system_prompt=system_prompt,
            model_provider=model_provider,
            model_id=model_id,
            temperature=temperature,
        )

    persisted_manifest = assign_manifest_revision(write_manifest, 1)
    now = _utcnow()
    SessionFactory = _get_session_factory()
    with SessionFactory() as session:
        if session.get(User, cleaned_account_id) is None:
            raise ValueError("persona_profile_owner_not_found")
        if session.get(PersonaProfile, cleaned_profile_id) is not None:
            raise ValueError("persona_profile_conflict")

        profile = PersonaProfile(
            id=cleaned_profile_id,
            name=write_manifest.identity.name,
            system_prompt=write_manifest.prompt.system_prompt,
            model_provider=write_manifest.model.provider,
            model_id=write_manifest.model.model,
            temperature=write_manifest.model.temperature,
            current_revision=1,
            created_at=now,
            updated_at=now,
        )
        binding = PersonaProfileBinding(
            profile_id=cleaned_profile_id,
            owner_account_id=cleaned_account_id,
            created_at=now,
            updated_at=now,
        )
        revision = PersonaProfileRevision(
            profile_id=cleaned_profile_id,
            revision=1,
            api_version=persisted_manifest.api_version,
            manifest_json=persisted_manifest_dict(persisted_manifest),
            created_at=now,
        )
        session.add_all([profile, binding, revision])
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("persona_profile_conflict") from exc
        session.refresh(profile)
        return _snapshot(profile, revision)


def _apply_legacy_patch(
    current: PersonaProfileManifest,
    *,
    name: str | None,
    system_prompt: str | None,
    model_provider: str | None,
    model_id: str | None,
    temperature: float | None,
) -> PersonaProfileManifestWrite:
    payload = authored_manifest_dict(current)
    if name is not None:
        cleaned = _clean_text(name)
        if not cleaned:
            raise ValueError("name is required")
        payload["identity"]["name"] = cleaned
    if system_prompt is not None:
        cleaned = _clean_text(system_prompt)
        if not cleaned:
            raise ValueError("system_prompt is required")
        payload["prompt"]["systemPrompt"] = cleaned
    if model_provider is not None:
        cleaned = _clean_text(model_provider)
        if not cleaned:
            raise ValueError("model_provider is required")
        payload["model"]["provider"] = cleaned.lower()
    if model_id is not None:
        cleaned = _clean_text(model_id)
        if not cleaned:
            raise ValueError("model_id is required")
        payload["model"]["model"] = cleaned
    if temperature is not None:
        payload["model"]["temperature"] = _normalize_temperature(temperature)
    return PersonaProfileManifestWrite.model_validate(payload)


def update_persona_profile(
    profile_id: str,
    *,
    account_id: str,
    manifest: PersonaProfileManifestWrite | dict[str, Any] | None = None,
    name: str | None = None,
    system_prompt: str | None = None,
    model_provider: str | None = None,
    model_id: str | None = None,
    temperature: float | None = None,
) -> StoredPersonaProfile:
    """Append one revision for a substantive account-scoped authored change."""
    cleaned_account_id = _require_account_id(account_id)
    cleaned_profile_id = _clean_text(profile_id)
    if not cleaned_profile_id:
        raise ValueError("profile_id is required")

    legacy_values = (
        name,
        system_prompt,
        model_provider,
        model_id,
        temperature,
    )
    if manifest is not None and any(value is not None for value in legacy_values):
        raise ValueError("manifest and legacy fields may not be mixed")
    if manifest is None and not any(value is not None for value in legacy_values):
        raise ValueError("at least one persona field is required")

    SessionFactory = _get_session_factory()
    with SessionFactory() as session:
        profile = session.scalar(
            select(PersonaProfile)
            .join(
                PersonaProfileBinding,
                PersonaProfileBinding.profile_id == PersonaProfile.id,
            )
            .where(
                PersonaProfile.id == cleaned_profile_id,
                PersonaProfileBinding.owner_account_id == cleaned_account_id,
            )
            .with_for_update()
        )
        if profile is None:
            raise ValueError(f"persona_profile_not_found:{cleaned_profile_id}")

        current_revision_row = _revision_row(session, profile)
        current_manifest = PersonaProfileManifest.model_validate(
            current_revision_row.manifest_json
        )
        if manifest is not None:
            write_manifest = _validate_manifest_write(manifest)
            if write_manifest.profile_identity != cleaned_profile_id:
                raise ValueError("persona_profile_identity_mismatch")
        else:
            write_manifest = _apply_legacy_patch(
                current_manifest,
                name=name,
                system_prompt=system_prompt,
                model_provider=model_provider,
                model_id=model_id,
                temperature=temperature,
            )

        if authored_manifest_dict(write_manifest) == authored_manifest_dict(
            current_manifest
        ):
            return _snapshot(profile, current_revision_row)

        next_revision = profile.current_revision + 1
        persisted_manifest = assign_manifest_revision(
            write_manifest,
            next_revision,
        )
        now = _utcnow()
        revision = PersonaProfileRevision(
            profile_id=profile.id,
            revision=next_revision,
            api_version=persisted_manifest.api_version,
            manifest_json=persisted_manifest_dict(persisted_manifest),
            created_at=now,
        )
        _apply_projection(profile, write_manifest)
        profile.current_revision = next_revision
        profile.updated_at = now
        session.add_all([profile, revision])
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("persona_profile_revision_conflict") from exc
        session.refresh(profile)
        return _snapshot(profile, revision)


__all__ = [
    "StoredPersonaProfile",
    "_set_session_factory",
    "create_persona_profile",
    "get_current_persona_profile_manifest",
    "get_persona_profile_by_id",
    "list_persona_profiles",
    "persona_profile_to_dict",
    "update_persona_profile",
]
