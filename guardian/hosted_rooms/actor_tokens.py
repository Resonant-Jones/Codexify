"""Canonical Hosted Room actor identity tokens.

Defines the bounded actor-source domain, resident actor references,
and validation rules for actor bindings.  Does not contain invocation,
completion, or message behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

# ── Actor source domain ─────────────────────────────────────────────────

RESIDENT_SOURCE = "resident"
LOCAL_PERSONA_SOURCE = "local_persona"

_VALID_SOURCES: frozenset[str] = frozenset(
    {RESIDENT_SOURCE, LOCAL_PERSONA_SOURCE}
)

# ── Resident actor domain ───────────────────────────────────────────────

GUARDIAN_REF = "guardian"
GUARDIAN_DISPLAY = "Guardian"

_VALID_RESIDENT_REFS: frozenset[str] = frozenset({GUARDIAN_REF})


@dataclass(frozen=True)
class ActorBinding:
    """Immutable actor identity binding."""

    source: str
    ref: str


def validate_actor_binding(source: str, ref: str) -> ActorBinding:
    """Validate an actor source/reference pair.

    Raises HTTPException(422) for unsupported sources or references.
    Returns an ActorBinding on success.
    """
    source = str(source or "").strip()
    ref = str(ref or "").strip()

    if not source:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_actor_source",
                "message": "Actor source is required",
            },
        )
    if not ref:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_actor_ref",
                "message": "Actor reference is required",
            },
        )

    if source not in _VALID_SOURCES:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "unsupported_actor_source",
                "message": f"Unsupported actor source: {source}",
                "valid_sources": sorted(_VALID_SOURCES),
            },
        )

    if source == RESIDENT_SOURCE:
        if ref not in _VALID_RESIDENT_REFS:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "unsupported_resident_actor",
                    "message": f"Unsupported resident actor: {ref}",
                    "valid_resident_actors": sorted(_VALID_RESIDENT_REFS),
                },
            )

    return ActorBinding(source=source, ref=ref)


def resolve_actor_display_name(source: str, ref: str) -> str:
    """Resolve a canonical display label for an actor binding.

    Does NOT perform database lookups or ownership checks.
    For local_persona, the caller must resolve the Persona name.
    """
    if source == RESIDENT_SOURCE and ref == GUARDIAN_REF:
        return GUARDIAN_DISPLAY
    # For local_persona, caller resolves PersonaProfile.name
    return ref


def validate_enabled_actors(raw: Any) -> list[ActorBinding]:
    """Validate and deduplicate a list of actor binding objects.

    Accepts list of {source, ref} dicts. Rejects unknown sources,
    unknown resident refs, and duplicates.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_enabled_actors",
                "message": "enabled_actors must be a list of actor binding objects",
            },
        )

    seen: set[tuple[str, str]] = set()
    result: list[ActorBinding] = []

    for item in raw:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "invalid_actor_binding",
                    "message": "Each enabled_actors entry must be an object with source and ref",
                },
            )
        binding = validate_actor_binding(
            source=str(item.get("source", "")),
            ref=str(item.get("ref", "")),
        )
        key = (binding.source, binding.ref)
        if key not in seen:
            seen.add(key)
            result.append(binding)

    return result
