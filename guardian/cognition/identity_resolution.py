"""Deterministic persona/imprint resolution with explicit precedence rules.

Current runtime posture: actor-plus-role. Guardian remains the stable actor;
persona and imprint are additive layers that shape behavior and presentation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from guardian.cognition.identity_contract import (
    IMPRINT_RESOLUTION_SOURCE_ACTIVE_SCOPE,
    IMPRINT_RESOLUTION_SOURCE_SYSTEM_DEFAULT,
    IMPRINT_RESOLUTION_SOURCE_USER_DEFAULT,
    PERSONA_RESOLUTION_SOURCE_ACTIVE_SCOPE,
    PERSONA_RESOLUTION_SOURCE_PROJECT_DEFAULT,
    PERSONA_RESOLUTION_SOURCE_REQUEST_OVERRIDE,
    PERSONA_RESOLUTION_SOURCE_SYSTEM_DEFAULT,
)
from guardian.cognition.imprints import store as imprint_store
from guardian.cognition.personas import store as persona_store
from guardian.db.models import Imprint, Persona

SYSTEM_DEFAULT_PERSONA = ""
SYSTEM_DEFAULT_IMPRINT: dict[str, Any] = {
    "guardian_name": None,
    "preferred_name": None,
    "style": None,
    "grammar_prefs": {},
    "metrics": {},
    "heat_score": None,
}


@dataclass(frozen=True)
class ResolvedPersona:
    source: str
    persona_id: int | None
    user_id: str
    project_id: int | None
    body: str
    record_source: str | None = None


@dataclass(frozen=True)
class ResolvedImprint:
    source: str
    imprint_id: int | None
    user_id: str
    project_id: int | None
    guardian_name: str | None
    preferred_name: str | None
    style: str | None
    grammar_prefs: dict[str, Any]
    metrics: dict[str, Any]
    heat_score: float | None


def _try_parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _from_persona_row(source: str, row: Persona) -> ResolvedPersona:
    return ResolvedPersona(
        source=source,
        persona_id=row.id,
        user_id=row.user_id,
        project_id=row.project_id,
        body=row.body,
        record_source=row.source,
    )


def _from_imprint_row(source: str, row: Imprint) -> ResolvedImprint:
    return ResolvedImprint(
        source=source,
        imprint_id=row.id,
        user_id=row.user_id,
        project_id=row.project_id,
        guardian_name=row.guardian_name,
        preferred_name=row.preferred_name,
        style=row.style,
        grammar_prefs=dict(row.grammar_prefs or {}),
        metrics=dict(row.metrics or {}),
        heat_score=row.heat_score,
    )


def resolve_persona(
    user_id: str,
    project_id: int | None,
    requested_persona_id_or_name: int | str | None = None,
    *,
    system_default_persona: str = SYSTEM_DEFAULT_PERSONA,
) -> ResolvedPersona:
    """Resolve persona using deterministic precedence.

    Request-scoped overrides are resolved first. They may point at a persisted
    persona record or supply an inline runtime override string, but they do not
    replace the stable Guardian actor.
    """
    requested = requested_persona_id_or_name
    if requested is not None and str(requested).strip():
        requested_id = _try_parse_int(requested)
        if requested_id is not None:
            candidate = persona_store.get_persona_by_id(requested_id)
            if not candidate:
                raise ValueError(f"requested persona {requested_id} not found")
            if candidate.user_id != user_id:
                raise ValueError("requested persona user mismatch")
            if candidate.project_id not in {project_id, None}:
                raise ValueError("requested persona scope mismatch")
            return _from_persona_row(
                PERSONA_RESOLUTION_SOURCE_REQUEST_OVERRIDE, candidate
            )
        return ResolvedPersona(
            source=PERSONA_RESOLUTION_SOURCE_REQUEST_OVERRIDE,
            persona_id=None,
            user_id=user_id,
            project_id=project_id,
            body=str(requested).strip(),
            record_source="runtime_override",
        )

    active_scope = persona_store.get_active_persona(user_id, project_id)
    if active_scope:
        return _from_persona_row(
            PERSONA_RESOLUTION_SOURCE_ACTIVE_SCOPE, active_scope
        )

    if project_id is not None:
        project_default = persona_store.get_active_persona(user_id, None)
        if project_default:
            return _from_persona_row(
                PERSONA_RESOLUTION_SOURCE_PROJECT_DEFAULT, project_default
            )

    return ResolvedPersona(
        source=PERSONA_RESOLUTION_SOURCE_SYSTEM_DEFAULT,
        persona_id=None,
        user_id=user_id,
        project_id=project_id,
        body=system_default_persona,
        record_source="system_default",
    )


def resolve_imprint(
    user_id: str,
    project_id: int | None,
    *,
    system_default_imprint: dict[str, Any] | None = None,
) -> ResolvedImprint:
    """Resolve imprint using deterministic precedence.

    Imprint remains additive presentation/style state. It can influence how
    Guardian presents itself, but it does not rebind the stable actor.
    """
    active_scope = imprint_store.get_active_imprint(user_id, project_id)
    if active_scope:
        return _from_imprint_row(
            IMPRINT_RESOLUTION_SOURCE_ACTIVE_SCOPE, active_scope
        )

    if project_id is not None:
        user_default = imprint_store.get_active_imprint(user_id, None)
        if user_default:
            return _from_imprint_row(
                IMPRINT_RESOLUTION_SOURCE_USER_DEFAULT, user_default
            )

    fallback = dict(system_default_imprint or SYSTEM_DEFAULT_IMPRINT)
    return ResolvedImprint(
        source=IMPRINT_RESOLUTION_SOURCE_SYSTEM_DEFAULT,
        imprint_id=None,
        user_id=user_id,
        project_id=project_id,
        guardian_name=fallback.get("guardian_name"),
        preferred_name=fallback.get("preferred_name"),
        style=fallback.get("style"),
        grammar_prefs=dict(fallback.get("grammar_prefs") or {}),
        metrics=dict(fallback.get("metrics") or {}),
        heat_score=fallback.get("heat_score"),
    )


__all__ = [
    "ResolvedImprint",
    "ResolvedPersona",
    "SYSTEM_DEFAULT_IMPRINT",
    "SYSTEM_DEFAULT_PERSONA",
    "resolve_imprint",
    "resolve_persona",
]
