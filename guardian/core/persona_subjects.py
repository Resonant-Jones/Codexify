"""Server-owned resolution of stable Persona-subject identity."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from guardian.db.models import (
    Persona,
    PersonaProfile,
    PersonaProfileBinding,
    PersonaSubject,
    PersonaSubjectBinding,
)
from guardian.protocol_tokens import PersonaSubjectLifecycle

PERSONA_REF_KIND = "persona"
PERSONA_PROFILE_REF_KIND = "persona_profile"
PERSONA_SUBJECT_REF_KINDS = frozenset({PERSONA_REF_KIND, PERSONA_PROFILE_REF_KIND})


class PersonaSubjectResolutionError(ValueError):
    """Raised when stable Persona-subject resolution must fail closed."""


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonaSubjectResolutionError(f"{label} must be a non-empty string")
    return value.strip()


def _canonical_persona_ref_id(ref_id: str) -> tuple[int, str]:
    try:
        persona_id = int(ref_id)
    except ValueError as exc:
        raise PersonaSubjectResolutionError(
            "persona ref_id must be an integer string"
        ) from exc
    if persona_id < 1 or str(persona_id) != ref_id:
        raise PersonaSubjectResolutionError(
            "persona ref_id must be a canonical positive integer string"
        )
    return persona_id, ref_id


def _source_for_ref(
    session: Session,
    ref_kind: str,
    ref_id: str,
) -> tuple[str, str, str | None, datetime]:
    if ref_kind == PERSONA_REF_KIND:
        persona_id, canonical_ref_id = _canonical_persona_ref_id(ref_id)
        persona = session.get(Persona, persona_id)
        if persona is None:
            raise PersonaSubjectResolutionError("Persona source does not exist")
        if persona.created_at is None:
            raise PersonaSubjectResolutionError(
                "Persona source lacks a durable creation timestamp"
            )
        return (
            canonical_ref_id,
            _required_text(persona.user_id, "Persona source account"),
            None,
            persona.created_at,
        )

    if ref_kind == PERSONA_PROFILE_REF_KIND:
        profile = session.get(PersonaProfile, ref_id)
        if profile is None:
            raise PersonaSubjectResolutionError("PersonaProfile source does not exist")
        profile_binding = session.get(PersonaProfileBinding, profile.id)
        if profile_binding is None:
            raise PersonaSubjectResolutionError(
                "PersonaProfile source has no canonical account binding"
            )
        if profile_binding.created_at is None:
            raise PersonaSubjectResolutionError(
                "PersonaProfile source binding lacks a durable creation timestamp"
            )
        return (
            profile.id,
            _required_text(
                profile_binding.owner_account_id,
                "PersonaProfile source account",
            ),
            profile.name,
            profile_binding.created_at,
        )

    raise PersonaSubjectResolutionError(
        f"ref_kind must be one of {sorted(PERSONA_SUBJECT_REF_KINDS)!r}"
    )


def _validate_current_binding_history(
    bindings: list[PersonaSubjectBinding],
) -> PersonaSubjectBinding | None:
    current = [binding for binding in bindings if binding.valid_until is None]
    if len(current) > 1:
        raise PersonaSubjectResolutionError(
            "source has multiple current Persona-subject bindings"
        )
    if not current:
        if bindings:
            raise PersonaSubjectResolutionError(
                "source has closed binding history without current continuity evidence"
            )
        return None

    ordered_bindings = sorted(
        bindings,
        key=lambda binding: (binding.valid_from, binding.binding_id),
    )
    current_binding = current[0]
    if ordered_bindings[-1] is not current_binding:
        raise PersonaSubjectResolutionError(
            "source binding history has a current binding before a closed interval"
        )
    for binding, successor in zip(ordered_bindings, ordered_bindings[1:]):
        if binding.valid_until is None or binding.valid_until != successor.valid_from:
            raise PersonaSubjectResolutionError(
                "source binding history is not a contiguous half-open sequence"
            )
    return current_binding


def _validated_subject_for_binding(
    session: Session,
    binding: PersonaSubjectBinding,
    source_account_id: str,
) -> PersonaSubject:
    subject = session.get(PersonaSubject, binding.persona_subject_id)
    if subject is None:
        raise PersonaSubjectResolutionError(
            "binding refers to a missing Persona subject"
        )
    if (
        binding.subject_user_id != subject.user_id
        or binding.source_account_id != source_account_id
        or binding.source_account_id != binding.subject_user_id
    ):
        raise PersonaSubjectResolutionError(
            "binding account integrity is contradictory"
        )
    if subject.lifecycle != PersonaSubjectLifecycle.ACTIVE.value:
        raise PersonaSubjectResolutionError(
            "current binding refers to a non-active Persona subject"
        )
    return subject


def ensure_persona_subject(
    session: Session,
    authenticated_account_id: str,
    ref_kind: str,
    ref_id: str,
) -> PersonaSubject:
    """Resolve or create one account-owned subject for a canonical source.

    The authenticated account is request authority only. Source ownership is
    independently derived from the canonical persisted Persona or
    PersonaProfile binding surface before any stable subject is returned or
    created. The caller never supplies subject or source account identifiers.
    """

    account_id = _required_text(authenticated_account_id, "authenticated account")
    normalized_ref_kind = _required_text(ref_kind, "ref_kind")
    normalized_ref_id = _required_text(ref_id, "ref_id")
    (
        canonical_ref_id,
        source_account_id,
        display_name_snapshot,
        valid_from,
    ) = _source_for_ref(session, normalized_ref_kind, normalized_ref_id)

    if source_account_id != account_id:
        raise PersonaSubjectResolutionError("authenticated account does not own source")

    bindings = list(
        session.scalars(
            select(PersonaSubjectBinding)
            .where(
                PersonaSubjectBinding.ref_kind == normalized_ref_kind,
                PersonaSubjectBinding.ref_id == canonical_ref_id,
            )
            .order_by(
                PersonaSubjectBinding.valid_from, PersonaSubjectBinding.binding_id
            )
            .with_for_update()
        )
    )
    current_binding = _validate_current_binding_history(bindings)
    if current_binding is not None:
        return _validated_subject_for_binding(
            session,
            current_binding,
            source_account_id,
        )

    subject = PersonaSubject(
        persona_subject_id=str(uuid.uuid4()),
        user_id=source_account_id,
        display_name_snapshot=display_name_snapshot,
        lifecycle=PersonaSubjectLifecycle.ACTIVE.value,
    )
    binding = PersonaSubjectBinding(
        binding_id=str(uuid.uuid4()),
        persona_subject_id=subject.persona_subject_id,
        subject_user_id=source_account_id,
        source_account_id=source_account_id,
        ref_kind=normalized_ref_kind,
        ref_id=canonical_ref_id,
        valid_from=valid_from,
        valid_until=None,
    )
    session.add_all((subject, binding))
    session.flush()
    return subject


__all__ = [
    "PERSONA_PROFILE_REF_KIND",
    "PERSONA_REF_KIND",
    "PERSONA_SUBJECT_REF_KINDS",
    "PersonaSubjectResolutionError",
    "ensure_persona_subject",
]
