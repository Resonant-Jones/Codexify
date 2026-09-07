"""Read-only canonical-envelope compatibility projections for legacy memory sources.

UMS-03E introduces the first compatibility reader: a deterministic
projection of authoritative legacy ``memory_entries`` rows into the
canonical memory envelope defined in §4.1 of the Unified Memory Store
Contract.

The contract is explicit:

    legacy source row         = durable authority for that legacy record
    compatibility envelope    = normalized read projection only

This module implements the read side only. It performs no canonical-table
writes, no legacy-row mutations, no Project inference, no Persona
inference, and no canonical durable ``memory_id`` assignment. The
projection is a semantic read object, not an ORM mirror of
``memory_records``.

The exact mapping is frozen in §4.13 of the contract under the
``memory_entries`` row:

    Envelope species        : episodic_semantic_memory
    Owner derivation        : user_id
    Project scope           : absent (account scope)
    Persona attribution     : zero links
    Provenance              : source_system='codexify',
                              source_record_id='memory_entries:<id>'
    Activation / review     : ambient-eligible by default
    Lossless source fields  : id, user_id, silo, content, tags, pinned,
                              created_at, updated_at

Fail-closed conditions (per §4.14) are honored by returning ``None``
for not-found / not-owned and by raising
``MemoryCompatibilityReadError`` for malformed source rows that cannot
be losslessly projected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from guardian.db.models import MemoryEntry
from guardian.protocol_tokens import MemorySemanticSpecies

# ---------------------------------------------------------------------------
# Frozen UMS-03A compatibility mapping constants for ``memory_entries``.
# ---------------------------------------------------------------------------

#: Canonical envelope species for legacy ``memory_entries`` rows.
#: Frozen by UMS-03A §4.13; serialized spelling is the protocol authority.
MEMORY_ENTRY_ENVELOPE_SPECIES: str = (
    MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value
)

#: Legacy source-family identifier used in compatibility projections.
MEMORY_ENTRY_LEGACY_SOURCE_FAMILY: str = "memory_entries"

#: Closed ``source_system`` for the compatibility provenance.
MEMORY_ENTRY_LEGACY_SOURCE_SYSTEM: str = "codexify"

#: Closed retention class vocabulary, mirrored from the table-level CHECK.
MEMORY_ENTRY_VALID_SILOS: frozenset[str] = frozenset(
    {"ephemeral", "midterm", "longterm"}
)


# ---------------------------------------------------------------------------
# Projection types.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryCompatibilityPersonaLink:
    """A typed stable-Persona attribution link on a compatibility projection.

    The frozen UMS-03A mapping for ``memory_entries`` says "absent today →
    zero links", so the projection always reports an empty list. This
    type exists so future source-family adapters can populate the
    canonical shape without changing the projection contract.
    """

    persona_subject_id: str
    link_kind: str


@dataclass(frozen=True)
class MemoryCompatibilityProvenance:
    """Compatibility-side provenance preserved from the legacy source row.

    This is a read projection of the §4.11 spine restricted to the
    fields the frozen mapping authorizes. It is not a row in the
    canonical ``memory_provenance`` table and confers no ownership.
    """

    source_system: str
    source_record_id: str
    source_thread_id: str | None = None
    source_message_id: str | None = None


@dataclass(frozen=True)
class MemoryCompatibilityProjection:
    """A normalized read projection of a legacy memory source row.

    The projection is the canonical-envelope view of the source row.
    It is a semantic read object, not an ORM mirror of
    ``memory_records``. It does not assign a durable canonical
    ``memory_id``; the legacy source identity is preserved on the
    ``legacy_source_family`` / ``legacy_source_record_id`` pair so
    downstream consumers can attribute the projection back to the
    authoritative legacy row.

    All fields below are populated exactly as the frozen §4.13
    mapping authorizes for the ``memory_entries`` source family.
    """

    # Compatibility lineage (required for compatibility reads).
    legacy_source_family: str
    legacy_source_record_id: str

    # Canonical envelope — ownership.
    account_user_id: str

    # Canonical envelope — semantic species and content.
    semantic_species: str
    content: str | None
    retention_class: str
    tags: str | None

    # Canonical envelope — priority / decay control.
    pinned: bool

    # Canonical envelope — lifecycle.
    created_at: datetime
    updated_at: datetime

    # Canonical envelope — scope (always account scope for memory_entries).
    project_id: str | None = None

    # Canonical envelope — Persona attribution (always zero for memory_entries).
    persona_links: list[MemoryCompatibilityPersonaLink] = field(default_factory=list)

    # Compatibility provenance (preserved; not authority).
    provenance: MemoryCompatibilityProvenance | None = None

    # Governance posture surfaced from the frozen mapping; the
    # compatibility reader describes the record, not routing policy.
    ambient_eligible: bool = True


# ---------------------------------------------------------------------------
# Errors.
# ---------------------------------------------------------------------------


class MemoryCompatibilityReadError(Exception):
    """Raised when a legacy source row cannot be losslessly projected.

    This is the fail-closed signal for compatibility reads. It is
    distinct from "not found" (returns ``None``) and from
    "not owned" (also returns ``None``); it is reserved for source
    rows whose persisted state cannot be reconciled with the frozen
    §4.13 mapping.
    """


# ---------------------------------------------------------------------------
# Reader.
# ---------------------------------------------------------------------------


def _legacy_source_record_id(memory_entry_id: int) -> str:
    """Build the frozen ``source_record_id`` for a ``memory_entries`` row."""

    return f"{MEMORY_ENTRY_LEGACY_SOURCE_FAMILY}:{memory_entry_id}"


def _build_provenance(memory_entry_id: int) -> MemoryCompatibilityProvenance:
    """Build the frozen compatibility provenance for a ``memory_entries`` row.

    The §4.13 mapping states there is no ``source_thread_id`` or
    ``source_message_id`` on the legacy row, so those fields are
    ``None`` and intentionally not inferred.
    """

    return MemoryCompatibilityProvenance(
        source_system=MEMORY_ENTRY_LEGACY_SOURCE_SYSTEM,
        source_record_id=_legacy_source_record_id(memory_entry_id),
    )


def _project(row: MemoryEntry) -> MemoryCompatibilityProjection:
    """Translate a loaded ``MemoryEntry`` into the canonical envelope.

    Defense-in-depth: even though the DB CHECK constraint prevents a
    malformed ``silo`` from being persisted, the reader re-validates
    so a future schema relaxation cannot silently widen the species
    mapping. Per §4.14, a row whose ``silo`` is outside the closed
    vocabulary fails closed.
    """

    if row.silo not in MEMORY_ENTRY_VALID_SILOS:
        raise MemoryCompatibilityReadError(
            f"memory_entries row {row.id} has malformed silo={row.silo!r}; "
            "frozen §4.13 mapping requires "
            f"{sorted(MEMORY_ENTRY_VALID_SILOS)}"
        )

    if row.content is not None and not isinstance(row.content, str):
        raise MemoryCompatibilityReadError(
            f"memory_entries row {row.id} has non-str content; "
            "cannot be losslessly projected"
        )

    return MemoryCompatibilityProjection(
        legacy_source_family=MEMORY_ENTRY_LEGACY_SOURCE_FAMILY,
        legacy_source_record_id=_legacy_source_record_id(row.id),
        account_user_id=row.user_id,
        semantic_species=MEMORY_ENTRY_ENVELOPE_SPECIES,
        content=row.content,
        retention_class=row.silo,
        tags=row.tags,
        pinned=bool(row.pinned),
        created_at=row.created_at,
        updated_at=row.updated_at,
        project_id=None,
        persona_links=[],
        provenance=_build_provenance(row.id),
        ambient_eligible=True,
    )


def read_memory_entry_projection(
    session: Session,
    *,
    authenticated_account_id: str,
    memory_entry_id: int,
) -> MemoryCompatibilityProjection | None:
    """Project an authoritative legacy ``memory_entries`` row into the canonical envelope.

    The caller supplies only the authenticated account identity and the
    legacy source identifier. Every other field is derived from the
    source row and the frozen §4.13 mapping; the caller may not
    supply memory ownership, semantic species, Project authority,
    Persona attribution, review state, activation state, or
    provenance authority.

    Account authorization is enforced by filtering the query on both
    the legacy row identity and the authenticated account. The
    not-found and not-owned cases are concealed identically per the
    existing repository posture, returning ``None``. A source row
    that cannot be losslessly projected raises
    :class:`MemoryCompatibilityReadError`.
    """

    if not authenticated_account_id:
        raise MemoryCompatibilityReadError(
            "authenticated_account_id is required for compatibility reads"
        )

    row = (
        session.query(MemoryEntry)
        .filter(MemoryEntry.id == memory_entry_id)
        .filter(MemoryEntry.user_id == authenticated_account_id)
        .one_or_none()
    )
    if row is None:
        return None
    return _project(row)
