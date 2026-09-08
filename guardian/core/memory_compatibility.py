"""Read-only canonical-envelope compatibility projections for legacy memory sources.

UMS-03E introduced the first compatibility reader: a deterministic
projection of authoritative legacy ``memory_entries`` rows into the
canonical memory envelope defined in §4.1 of the Unified Memory Store
Contract. UMS-03F extends the same projection type with the second
authorized source family — verified + active ``personal_facts`` rows —
without introducing a sibling projection subsystem.

The contract is explicit:

    legacy source row         = durable authority for that legacy record
    compatibility envelope    = normalized read projection only

This module implements the read side only. It performs no canonical-table
writes, no legacy-row mutations, no Project inference, no Persona
inference, and no canonical durable ``memory_id`` assignment. The
projection is a semantic read object, not an ORM mirror of
``memory_records``.

The exact mapping is frozen in §4.13 of the contract.

For ``memory_entries`` (any ``silo``):

    Envelope species        : episodic_semantic_memory
    Owner derivation        : user_id
    Project scope           : absent (account scope)
    Persona attribution     : zero links
    Provenance              : source_system='codexify',
                              source_record_id='memory_entries:<id>'
    Activation / review     : ambient-eligible by default
    Lossless source fields  : id, user_id, silo, content, tags, pinned,
                              created_at, updated_at

For ``personal_facts`` (``status='verified'`` AND ``is_active=true``):

    Envelope species        : verified_personal_fact
    Owner derivation        : user_id
    Project scope           : absent (account scope)
    Persona attribution     : zero links
    Provenance              : source_system='codexify',
                              source_record_id='personal_facts:<id>'
                              primary source_type / evidence_meta /
                              source_message_id from latest evidence row
    Activation / review     : approved, active (no ambient upgrade)
    Lossless source fields  : id, user_id, key, value, status, confidence,
                              is_active, last_confirmed_at,
                              guardrail_metadata, created_at, updated_at;
                              full evidence rows; revisions

Candidate / unreviewed facts (status in {candidate, disputed, archived}
or is_active=false) are not in scope for UMS-03F. The reader returns
``None`` for those rows exactly as it does for not-found / not-owned.

Fail-closed conditions (per §4.14) are honored by returning ``None``
for not-found / not-owned / non-authoritative, and by raising
``MemoryCompatibilityReadError`` for source rows whose evidence cannot
be losslessly projected (e.g. unknown ``source_type`` or
self-referential ``evidence_meta``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from guardian.db.models import (
    MemoryEntry,
    PersonalFact,
    PersonalFactEvidence,
    PersonalFactRevision,
)
from guardian.protocol_tokens import MemorySemanticSpecies, PersonalFactStatus

try:
    from sqlalchemy import or_  # SQLAlchemy >= 1.4
except ImportError:  # pragma: no cover - SQLAlchemy 1.3 compatibility
    from sqlalchemy.sql import or_  # type: ignore[no-redef]

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

#: Canonical closed source-type vocabulary for ``personal_fact_evidence``.
#: Mirrored from the §4.6 inventory and §4.13 fail-closed enumeration.
PERSONAL_FACT_EVIDENCE_SOURCE_TYPES: frozenset[str] = frozenset(
    {
        "chatgpt_import",
        "runtime_extraction",
        "user_stated",
        "user_corrected",
        "claude_import",
    }
)

#: Canonical envelope species for verified + active ``personal_facts`` rows.
#: Frozen by UMS-03A §4.13; serialized spelling is the protocol authority.
PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES: str = (
    MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value
)

#: Canonical envelope species for candidate / unreviewed ``personal_facts``
#: rows. Frozen by UMS-03A §4.13 line 901 and §4.10 line 725 exactly.
PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES: str = (
    MemorySemanticSpecies.CANDIDATE_UNREVIEWED_FACT.value
)

#: Legacy source-family identifier used in compatibility projections.
PERSONAL_FACT_LEGACY_SOURCE_FAMILY: str = "personal_facts"

#: Closed ``source_system`` for the compatibility provenance.
PERSONAL_FACT_LEGACY_SOURCE_SYSTEM: str = "codexify"

#: Canonical eligibility predicate for the verified + active fact adapter.
#: Mirrors §4.13 line 900 and §4.10 line 724 exactly.
VERIFIED_PERSONAL_FACT_PREDICATE: str = (
    f"status = '{PersonalFactStatus.VERIFIED.value}' " f"AND is_active = TRUE"
)

#: Canonical eligibility predicate for the candidate / unreviewed fact
#: adapter. Mirrors §4.13 line 901 and §4.10 line 725 exactly:
#: status in {candidate, disputed, archived} OR is_active = false.
CANDIDATE_PERSONAL_FACT_PREDICATE: str = (
    f"status IN ("
    f"'{PersonalFactStatus.CANDIDATE.value}', "
    f"'{PersonalFactStatus.DISPUTED.value}', "
    f"'{PersonalFactStatus.ARCHIVED.value}') "
    f"OR is_active = FALSE"
)

#: Closed set of status tokens that map to the candidate / unreviewed
#: species per the §4.13 row.
CANDIDATE_PERSONAL_FACT_STATUSES: frozenset[str] = frozenset(
    {
        PersonalFactStatus.CANDIDATE.value,
        PersonalFactStatus.DISPUTED.value,
        PersonalFactStatus.ARCHIVED.value,
    }
)


# ---------------------------------------------------------------------------
# Projection types.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryCompatibilityPersonaLink:
    """A typed stable-Persona attribution link on a compatibility projection.

    The frozen UMS-03A mapping for both ``memory_entries`` and verified
    ``personal_facts`` says "absent today → zero links", so the
    projection always reports an empty list. This type exists so
    future source-family adapters can populate the canonical shape
    without changing the projection contract.
    """

    persona_subject_id: str
    link_kind: str


@dataclass(frozen=True)
class MemoryCompatibilityEvidence:
    """A preserved evidence row attached to a verified-fact projection.

    Evidence is read-only lineage; it does not confer ownership or
    activation authority. Multiple evidence rows are preserved
    distinct from one another; they are not deduplicated by provider
    or ``source_type``.
    """

    evidence_id: int
    source_type: str
    source_message_id: int | None
    modality: str
    excerpt: str | None
    evidence_meta: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class MemoryCompatibilityRevision:
    """A preserved revision row attached to a verified-fact projection.

    Revisions are historical lineage only. They never replace the
    current authoritative fact row, never promote an old revision to
    a second active fact, and never carry activation authority.
    """

    revision_id: int
    actor: str
    action: str
    field_changed: str | None
    old_value: str | None
    new_value: str | None
    reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class MemoryCompatibilityProvenance:
    """Compatibility-side provenance preserved from the legacy source row.

    For ``memory_entries`` the projection carries the
    ``memory_entries:<id>`` lineage. For verified ``personal_facts``
    the projection additionally carries the primary (latest)
    evidence's ``source_type``, ``source_message_id``,
    ``evidence_meta``, ``modality``, and ``excerpt``. None of those
    additional fields confer ownership or activation authority.
    """

    source_system: str
    source_record_id: str
    source_thread_id: str | None = None
    source_message_id: str | None = None
    source_type: str | None = None
    evidence_meta: dict[str, Any] | None = None
    modality: str | None = None
    excerpt: str | None = None


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

    For ``memory_entries`` rows the legacy-shape fields (``content``,
    ``retention_class``, ``tags``, ``pinned``) are populated and the
    fact-shape fields are ``None`` / empty.

    For verified + active ``personal_facts`` rows the fact-shape
    fields (``fact_key``, ``fact_value``, ``confidence``,
    ``last_confirmed_at``, ``guardrail_metadata``, ``evidence``,
    ``revisions``) are populated and the legacy-shape fields are
    ``None`` / ``False`` / empty.
    """

    # Compatibility lineage (required for compatibility reads).
    legacy_source_family: str
    legacy_source_record_id: str

    # Canonical envelope — ownership.
    account_user_id: str

    # Canonical envelope — semantic species and content.
    semantic_species: str
    content: str | None
    retention_class: str | None
    tags: str | None

    # Canonical envelope — priority / decay control.
    pinned: bool

    # Canonical envelope — lifecycle.
    created_at: datetime
    updated_at: datetime

    # Canonical envelope — scope (always account scope for
    # memory_entries and verified personal_facts).
    project_id: str | None = None

    # Canonical envelope — Persona attribution (always zero for
    # memory_entries and verified personal_facts).
    persona_links: list[MemoryCompatibilityPersonaLink] = field(default_factory=list)

    # Compatibility provenance (preserved; not authority).
    provenance: MemoryCompatibilityProvenance | None = None

    # Verified-fact shape (populated only for verified + active
    # ``personal_facts`` rows; ``None`` / empty for ``memory_entries``).
    fact_key: str | None = None
    fact_value: str | None = None
    confidence: float | None = None
    last_confirmed_at: datetime | None = None
    guardrail_metadata: dict[str, Any] | None = None
    evidence: list[MemoryCompatibilityEvidence] = field(default_factory=list)
    revisions: list[MemoryCompatibilityRevision] = field(default_factory=list)

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


# ---------------------------------------------------------------------------
# Verified personal-fact reader (UMS-03F).
# ---------------------------------------------------------------------------


def _personal_fact_source_record_id(personal_fact_id: int) -> str:
    """Build the frozen ``source_record_id`` for a ``personal_facts`` row."""

    return f"{PERSONAL_FACT_LEGACY_SOURCE_FAMILY}:{personal_fact_id}"


def _evidence_meta_is_self_referential(
    fact_id: int, evidence_meta: dict[str, Any]
) -> bool:
    """Recursive fail-closed check for self-referential ``evidence_meta``.

    §4.13 fail-closed: a row whose ``evidence_meta`` is self-referential
    must not project as a verified personal fact. The JSONB column
    already guarantees the payload is valid JSON; this check is a
    defense-in-depth walk that flags any recursive value equal to the
    parent ``fact_id`` (as ``int``).

    The check walks every nested value (dict, list, scalar) and fails
    only when a value equals ``fact_id`` exactly. Substring matches
    in longer string values (e.g. ``"msg-1"``) are not flagged.
    """

    target = int(fact_id)

    def _walk(value: Any) -> bool:
        if isinstance(value, bool):
            return False
        if isinstance(value, int) and not isinstance(value, bool):
            return value == target
        if isinstance(value, dict):
            return any(_walk(v) for v in value.values())
        if isinstance(value, list):
            return any(_walk(v) for v in value)
        if isinstance(value, tuple):
            return any(_walk(v) for v in value)
        return False

    try:
        return _walk(evidence_meta)
    except RecursionError:
        return True


def _project_evidence(
    fact_id: int, evidence: list[PersonalFactEvidence]
) -> list[MemoryCompatibilityEvidence]:
    """Translate evidence rows, ordered by ``created_at`` DESC, into the projection shape.

    The first entry in the returned list is the "primary" (latest)
    evidence referenced by the §4.13 mapping's "primary source_type
    from latest personal_fact_evidence" clause. All rows remain
    distinct — no deduplication by provider or ``source_type``.

    Per §4.14, an evidence row whose ``source_type`` is outside the
    closed vocabulary, or whose ``evidence_meta`` is self-referential
    on the parent fact, fails closed.
    """

    ordered = sorted(evidence, key=lambda row: row.created_at, reverse=True)
    projected: list[MemoryCompatibilityEvidence] = []
    for row in ordered:
        if row.source_type not in PERSONAL_FACT_EVIDENCE_SOURCE_TYPES:
            raise MemoryCompatibilityReadError(
                f"personal_facts row {fact_id} has evidence id={row.id} with "
                f"unknown source_type={row.source_type!r}; frozen §4.13 "
                f"mapping requires one of "
                f"{sorted(PERSONAL_FACT_EVIDENCE_SOURCE_TYPES)}"
            )
        if _evidence_meta_is_self_referential(fact_id, row.evidence_meta):
            raise MemoryCompatibilityReadError(
                f"personal_facts row {fact_id} has evidence id={row.id} "
                "with self-referential evidence_meta; cannot be "
                "losslessly projected"
            )
        projected.append(
            MemoryCompatibilityEvidence(
                evidence_id=row.id,
                source_type=row.source_type,
                source_message_id=row.source_message_id,
                modality=row.modality,
                excerpt=row.excerpt,
                evidence_meta=dict(row.evidence_meta),
                created_at=row.created_at,
            )
        )
    return projected


def _project_revisions(
    fact_id: int, revisions: list[PersonalFactRevision]
) -> list[MemoryCompatibilityRevision]:
    """Translate revision rows, ordered by ``created_at`` ASC, into the projection shape.

    Revisions are historical lineage only. They never replace the
    current authoritative fact row and never carry activation
    authority. The returned list is read-only; this function does not
    mutate the source rows.
    """

    ordered = sorted(revisions, key=lambda row: row.created_at)
    return [
        MemoryCompatibilityRevision(
            revision_id=row.id,
            actor=row.actor,
            action=row.action,
            field_changed=row.field_changed,
            old_value=row.old_value,
            new_value=row.new_value,
            reason=row.reason,
            created_at=row.created_at,
        )
        for row in ordered
    ]


def _build_personal_fact_provenance(
    fact_id: int, primary_evidence: MemoryCompatibilityEvidence | None
) -> MemoryCompatibilityProvenance:
    """Build the compatibility provenance for a verified personal fact.

    The frozen §4.13 mapping requires the primary evidence's
    ``source_type`` / ``source_message_id`` / ``evidence_meta`` to be
    preserved on the projection. When a fact has no evidence rows
    the projection carries the fact's own lineage only and the
    evidence-derived fields are ``None``.
    """

    return MemoryCompatibilityProvenance(
        source_system=PERSONAL_FACT_LEGACY_SOURCE_SYSTEM,
        source_record_id=_personal_fact_source_record_id(fact_id),
        source_thread_id=None,
        source_message_id=(
            str(primary_evidence.source_message_id)
            if primary_evidence and primary_evidence.source_message_id is not None
            else None
        ),
        source_type=primary_evidence.source_type if primary_evidence else None,
        evidence_meta=primary_evidence.evidence_meta if primary_evidence else None,
        modality=primary_evidence.modality if primary_evidence else None,
        excerpt=primary_evidence.excerpt if primary_evidence else None,
    )


def _project_personal_fact(
    fact: PersonalFact,
    evidence_rows: list[PersonalFactEvidence],
    revision_rows: list[PersonalFactRevision],
    *,
    semantic_species: str = PERSONAL_FACT_VERIFIED_ENVELOPE_SPECIES,
    ambient_eligible: bool = True,
) -> MemoryCompatibilityProjection:
    """Translate a legacy ``personal_facts`` row into the canonical envelope.

    The default behavior is the UMS-03F verified + active projection.
    Per §4.13, verified + active personal facts project with:

        semantic_species     = verified_personal_fact
        fact_key, fact_value = legacy key / value
        confidence           = legacy confidence
        last_confirmed_at    = legacy last_confirmed_at
        guardrail_metadata   = legacy guardrail_metadata
        evidence             = full evidence rows (one-to-many, distinct)
        revisions            = full revision rows (historical only)

    Activation posture is the frozen §4.10 line 724
    "approved, active" truth; the projection reports the record
    state, not routing policy. ``ambient_eligible`` is left as the
    reader's "approved" default; the reader does not perform
    ambient-influence routing decisions.

    UMS-03G reuses this helper to project candidate / unreviewed
    facts with a different ``semantic_species`` token and
    ``ambient_eligible=False``. The verified reader is unaffected
    by the optional keyword arguments.
    """

    evidence_projection = _project_evidence(fact.id, evidence_rows)
    revisions_projection = _project_revisions(fact.id, revision_rows)
    primary_evidence = evidence_projection[0] if evidence_projection else None
    provenance = _build_personal_fact_provenance(fact.id, primary_evidence)

    return MemoryCompatibilityProjection(
        legacy_source_family=PERSONAL_FACT_LEGACY_SOURCE_FAMILY,
        legacy_source_record_id=_personal_fact_source_record_id(fact.id),
        account_user_id=fact.user_id,
        semantic_species=semantic_species,
        content=None,
        retention_class=None,
        tags=None,
        pinned=False,
        created_at=fact.created_at,
        updated_at=fact.updated_at,
        project_id=None,
        persona_links=[],
        provenance=provenance,
        fact_key=fact.key,
        fact_value=fact.value,
        confidence=float(fact.confidence) if fact.confidence is not None else None,
        last_confirmed_at=fact.last_confirmed_at,
        guardrail_metadata=(
            dict(fact.guardrail_metadata)
            if fact.guardrail_metadata is not None
            else None
        ),
        evidence=evidence_projection,
        revisions=revisions_projection,
        ambient_eligible=ambient_eligible,
    )


def read_verified_personal_fact_projection(
    session: Session,
    *,
    authenticated_account_id: str,
    personal_fact_id: int,
) -> MemoryCompatibilityProjection | None:
    """Project an authoritative verified + active legacy ``personal_facts`` row.

    Eligibility is the canonical predicate frozen in §4.13 line 900
    and §4.10 line 724:

        status    = PersonalFactStatus.VERIFIED.value   (i.e. 'verified')
        is_active = TRUE

    The caller supplies only the authenticated account identity and
    the legacy source identifier. Every other field is derived from
    the source row, the frozen §4.13 mapping, and the related
    evidence / revision rows; the caller may not supply ownership,
    status, activity, semantic species, Project authority, Persona
    attribution, review authority, activation authority, or
    provenance authority.

    Account authorization is enforced by filtering the query on the
    legacy row identity, the authenticated account, and the
    verified + active predicate. Candidate / disputed / archived /
    inactive rows return ``None`` identically to not-found and
    not-owned, per existing repository concealment semantics. A row
    that passes the predicate but cannot be losslessly projected
    (e.g. malformed evidence) raises
    :class:`MemoryCompatibilityReadError`.
    """

    if not authenticated_account_id:
        raise MemoryCompatibilityReadError(
            "authenticated_account_id is required for compatibility reads"
        )

    row = (
        session.query(PersonalFact)
        .filter(PersonalFact.id == personal_fact_id)
        .filter(PersonalFact.user_id == authenticated_account_id)
        .filter(PersonalFact.status == PersonalFactStatus.VERIFIED.value)
        .filter(PersonalFact.is_active.is_(True))
        .one_or_none()
    )
    if row is None:
        return None
    evidence_rows = list(row.evidence)
    revision_rows = list(row.revisions)
    return _project_personal_fact(row, evidence_rows, revision_rows)


# ---------------------------------------------------------------------------
# Candidate / unreviewed personal-fact reader (UMS-03G).
# ---------------------------------------------------------------------------


def read_candidate_personal_fact_projection(
    session: Session,
    *,
    authenticated_account_id: str,
    personal_fact_id: int,
) -> MemoryCompatibilityProjection | None:
    """Project a candidate / unreviewed legacy ``personal_facts`` row.

    Eligibility is the canonical predicate frozen in §4.13 line 901
    and §4.10 line 725:

        status    IN ('candidate', 'disputed', 'archived')
        OR
        is_active = FALSE

    This is the natural complement of the UMS-03F verified + active
    predicate. Together the two readers cover every ``personal_facts``
    row exactly.

    Per §4.13, candidate / unreviewed facts project with:

        semantic_species     = candidate_unreviewed_fact
        review posture       = pending / unapproved (carried by species)
        lifecycle authority  = Personal Facts (source `is_active` is
                               preserved; the projection does not
                               reinterpret activation as approval)
        ambient_eligible     = False (candidate content is never
                               ambiently influential through the
                               compatibility reader)

    The caller supplies only the authenticated account identity and
    the legacy source identifier. Every other field is derived from
    the source row, the frozen §4.13 mapping, and the related
    evidence / revision rows; the caller may not supply ownership,
    status, activity, semantic species, Project authority, Persona
    attribution, review authority, activation authority, or
    provenance authority.

    Account authorization is enforced by filtering the query on the
    legacy row identity and the authenticated account. The natural
    complement with the verified reader means a verified + active
    fact returns ``None`` from this reader, a candidate / disputed /
    archived / inactive fact returns ``None`` from the verified
    reader, and either case returns ``None`` for not-found and
    not-owned, per existing repository concealment semantics. A row
    that passes the candidate predicate but cannot be losslessly
    projected (e.g. malformed evidence) raises
    :class:`MemoryCompatibilityReadError`.
    """

    if not authenticated_account_id:
        raise MemoryCompatibilityReadError(
            "authenticated_account_id is required for compatibility reads"
        )

    row = (
        session.query(PersonalFact)
        .filter(PersonalFact.id == personal_fact_id)
        .filter(PersonalFact.user_id == authenticated_account_id)
        .filter(
            or_(
                PersonalFact.status.in_(tuple(CANDIDATE_PERSONAL_FACT_STATUSES)),
                PersonalFact.is_active.is_(False),
            )
        )
        .one_or_none()
    )
    if row is None:
        return None
    evidence_rows = list(row.evidence)
    revision_rows = list(row.revisions)
    return _project_personal_fact(
        row,
        evidence_rows,
        revision_rows,
        semantic_species=PERSONAL_FACT_CANDIDATE_ENVELOPE_SPECIES,
        ambient_eligible=False,
    )
