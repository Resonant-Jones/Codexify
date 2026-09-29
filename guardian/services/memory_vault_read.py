"""
Memory Vault backend read projection service (UMS-05B1).

This module implements one internal Guardian service that projects the
canonical account-owned Unified Memory Store for the authenticated
account:

    canonical memory_records
      + canonical memory_persona_links
      + canonical memory_provenance
      + stable persona_subjects
      + admitted UMS compatibility projections
        (legacy ``memory_entries``,
         verified + active ``personal_facts``,
         candidate / disputed / archived / inactive ``personal_facts``)
      + Personal Facts derived posture

It is a READ-ONLY projection. It performs:

    no canonical write
    no legacy mutation
    no compatibility -> canonical promotion
    no read repair
    no read canonicalization
    no Project inference
    no Persona inference
    no ambient-eligibility write
    no recall widening
    no Vault mutation
    no UMS-06+ behavior

The contract this service implements is the frozen UMS-05A Memory
Vault operator contract. The contract governs what the Vault is and
what it is not; this service is the executable form of the read
projection half of that contract. The HTTP/API surface and any
mutations are explicitly deferred to later UMS-05B / UMS-05C slices.

The service is named to be unambiguous against the unrelated
``guardian/modules/memory_key_vault.py`` ``MemoryKeyVault`` in-memory
summary encryption helper, which is not the UMS-05 Memory Vault and
shares no authority, persistence semantics, or governance with this
service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

<<<<<<< ours
from sqlalchemy import String, cast, or_
=======
from sqlalchemy import String, and_, cast, or_
>>>>>>> theirs
from sqlalchemy.orm import Session

from guardian.core.memory_compatibility import (
    MemoryCompatibilityProjection,
    MemoryCompatibilitySourceKind,
    MemoryCompatibilitySourceRef,
    read_memory_compatibility_projection,
)
from guardian.db.models import (
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryRecord,
    MemoryEntry,
    PersonalFact,
    PersonaSubject,
)

# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

#: Service version identifier. The frozen UMS-05A contract is the
#: authoritative source of truth; this is a discoverable marker.
SERVICE_VERSION = "memory-vault-read-v1"

#: Default list bound (per UMS-05A contract: default <= 50).
DEFAULT_LIST_LIMIT: int = 50

#: Maximum list bound (per UMS-05A contract: maximum <= 100).
MAX_LIST_LIMIT: int = 100

#: Closed lifecycle / review posture vocabulary. Frozen by UMS-04C
#: and §4.10 of the Unified Memory Store Contract. The Vault
#: projection renders these strings to the operator; it does not
#: invent new posture values.
REVIEW_POSTURE_PENDING: str = "pending"
REVIEW_POSTURE_APPROVED: str = "approved"
REVIEW_POSTURE_DISPUTED: str = "disputed"
LIFECYCLE_POSTURE_ACTIVE: str = "active"
LIFECYCLE_POSTURE_INACTIVE: str = "inactive"
PINNED_TRUE: str = "pinned"
PINNED_FALSE: str = "not_pinned"
HELD_TRUE: str = "held"
HELD_FALSE: str = "not_held"


# ---------------------------------------------------------------------------
# Errors.
# ---------------------------------------------------------------------------


class MemoryVaultReadError(Exception):
    """Fail-closed error for Vault read projection integrity defects.

    Raised when a row passes account authorization but cannot be
    losslessly projected into the Vault logical item model. Distinct
    from "not available to this account" (which returns ``None``).
    Used to surface integrity defects without leaking partial
    content.
    """


# ---------------------------------------------------------------------------
# DTOs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VaultPersonaLink:
    """A typed stable-Persona attribution link on a Vault item.

    The Persona subject identity is the stable ``persona_subject_id``;
    the user-visible display name is informational only and is never
    used as a filter authority.
    """

    link_id: str
    persona_subject_id: str
    persona_user_id: str
    link_kind: str
    display_name_snapshot: str | None = None


@dataclass(frozen=True)
class VaultProvenance:
    """A typed provenance row preserved on a Vault item.

    External source identifiers are preserved verbatim and remain
    opaque to the Vault. ``source_system`` is the closed vocabulary
    used for filtering.
    """

    provenance_id: str
    source_system: str
    source_record_id: str | None = None
    source_thread_id: int | None = None
    source_message_id: int | None = None
    source_import_job_id: str | None = None
    source_export_fingerprint: str | None = None
    source_subject_kind: str | None = None
    source_subject_id: str | None = None
    is_imported: bool = False


@dataclass(frozen=True)
class VaultIdentity:
    """Authoritative identity of one Vault item.

    The ``kind`` discriminator selects the underlying authority.
    A ``canonical`` Vault item resolves to a canonical
    ``memory_records.memory_id``. A ``compatibility`` Vault item
    resolves to an existing UMS compatibility source reference
    (``MemoryCompatibilitySourceRef``) whose identity is preserved
    verbatim on the projection.

    The Vault mints no synthetic canonical ``memory_id`` for
    compatibility-only records.
    """

    kind: str  # ``"canonical"`` | ``"compatibility"``
    canonical_memory_id: str | None = None
    compatibility_source: MemoryCompatibilitySourceRef | None = None


@dataclass(frozen=True)
class VaultItem:
    """The operator-facing logical projection of one memory.

    Each item carries enough typed information to identify its
    authoritative source (canonical or compatibility) and to
    render the UMS-05A contract fields.

    Field authority sources:

    - ``identity``: canonical ``memory_id`` or UMS compatibility
      source reference (preserved verbatim).
    - ``semantic_species``: canonical ``memory_records.semantic_species``
      for canonical items; frozen UMS-03 §4.13 mapping for compatibility
      items.
    - ``content``: canonical ``text_content`` / ``fact_value`` or
      frozen compatibility mapping.
    - ``account_owner``: canonical ``user_id`` (asserted equal to the
      authenticated identity for canonical items; enforced by the
      compatibility reader for compatibility items).
    - ``project_id``: canonical ``memory_records.project_id`` (None
      for compatibility items, per frozen mapping).
    - ``review_posture`` / ``lifecycle_posture``: derived from
      canonical ``reviewed_at`` / ``activated_at`` timestamps for
      canonical items; frozen compatibility posture for compatibility
      items. Personal Facts posture is sourced from Personal Facts
      authority (status + is_active) through the UMS-03F / UMS-03G
      readers, never independently reinterpreted.
    - ``pinned`` / ``held``: canonical fields on canonical items;
      compatibility ``pinned`` (legacy semantic preserved verbatim).
    - ``persona_links``: canonical ``memory_persona_links`` joined
      against ``persona_subjects`` for canonical items; empty for
      compatibility items.
    - ``provenance``: canonical ``memory_provenance`` rows for
      canonical items (multiplicity preserved); one frozen
      compatibility provenance row for compatibility items.
    - ``created_at`` / ``updated_at``: canonical timestamps for
      canonical items; legacy timestamps for compatibility items.
    - ``extensions``: canonical ``extensions`` JSONB for canonical
      items (labelled non-authority); None for compatibility items.
    """

    identity: VaultIdentity

    semantic_species: str
    content: str | None = None

    account_owner: str = ""
    project_id: int | None = None

    review_posture: str = REVIEW_POSTURE_PENDING
    lifecycle_posture: str = LIFECYCLE_POSTURE_INACTIVE

    pinned: bool = False
    held: bool = False

    created_at: datetime | None = None
    updated_at: datetime | None = None

    persona_links: list[VaultPersonaLink] = field(default_factory=list)
    provenance: list[VaultProvenance] = field(default_factory=list)
    extensions: dict[str, Any] | None = None

    #: Compatibility provenance (preserved when this item is a
    #: compatibility projection). None for canonical items.
    compatibility_legacy_source_family: str | None = None
    compatibility_legacy_source_record_id: str | None = None
    compatibility_semantic_species: str | None = None


# ---------------------------------------------------------------------------
# Filter / list DTOs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VaultListFilter:
    """Filter parameters for ``MemoryVaultReadService.list_items``.

    All filter dimensions are optional. Multiple supplied dimensions
    combine with logical AND.

    A compatibility projection that cannot authoritatively answer a
    supplied dimension is excluded from the result rather than
    fabricated to match.
    """

    semantic_species: str | None = None
    project_id: int | None = None
    account_scoped_only: bool = False
    persona_subject_id: str | None = None
    review_posture: str | None = None
    lifecycle_posture: str | None = None
    source_system: str | None = None
    pinned: bool | None = None
    held: bool | None = None


# ---------------------------------------------------------------------------
# Service.
# ---------------------------------------------------------------------------


class MemoryVaultReadService:
    """Read-only Memory Vault projection service.

    Constructed with an authenticated account identity and a
    SQLAlchemy session. The session is read-only by service contract:
    this service NEVER calls ``.add()``, ``.delete()``, ``.commit()``,
    or any mutation surface on the session.

    The service combines:

    - canonical ``memory_records`` (via SQLAlchemy);
    - canonical ``memory_persona_links`` (via SQLAlchemy) joined
      against ``persona_subjects`` for stable attribution;
    - canonical ``memory_provenance`` (via SQLAlchemy) for
      multiplicity-preserving provenance readback;
    - admitted UMS compatibility projections through
      ``read_memory_compatibility_projection`` (UMS-03I dispatcher).

    All four authority surfaces are reused; no parallel authority is
    introduced.
    """

    def __init__(
        self,
        session: Session,
        *,
        authenticated_account_id: str,
    ) -> None:
        if session is None:
            raise MemoryVaultReadError("session is required for MemoryVaultReadService")
        if not authenticated_account_id or not isinstance(
            authenticated_account_id, str
        ):
            raise MemoryVaultReadError(
                "authenticated_account_id is required and must be a non-empty string"
            )
        self._session = session
        self._account = authenticated_account_id

    # -- Public API --------------------------------------------------------

    def list_items(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        filter: VaultListFilter | None = None,
    ) -> list[VaultItem]:
        """Return an account-owned bounded list of Vault items.

        Canonical and compatibility items participate in one combined
        deterministic presentation order (newest ``created_at`` first;
        stable identity tie-breaker). The final logical list is then
        sliced by ``offset`` and ``limit``. This is PRESENTATION
        ORDERING ONLY; the Vault does not sort by priority, relevance,
        heat, or recall rank.
        """
        effective_limit = self._normalize_limit(
            DEFAULT_LIST_LIMIT if limit is None else limit
        )
        effective_offset = self._normalize_offset(offset)
        effective_filter = filter or VaultListFilter()

        items: list[VaultItem] = []

<<<<<<< ours
        # Fetch only enough already-filtered rows from each authority to
        # determine the requested page in the combined presentation order.
        # A row ranked below this window in its own source cannot occur in the
        # first ``candidate_limit`` rows of the merged source set.
=======
>>>>>>> theirs
        candidate_limit = effective_offset + effective_limit

        canonical_items = self._list_canonical_items(
            effective_filter, candidate_limit=candidate_limit
        )
        items.extend(canonical_items)

        compatibility_items = self._list_compatibility_items(
            effective_filter, candidate_limit=candidate_limit
        )
        items.extend(compatibility_items)

        items = self._apply_filters(items, effective_filter)

        # Presentation order: created_at DESC, then stable identity.
        items.sort(
            key=lambda item: (
                -(item.created_at.timestamp() if item.created_at else 0),
                _stable_identity_key(item),
            )
        )

        return items[effective_offset : effective_offset + effective_limit]

    def get_item(
        self,
        *,
        identity: VaultIdentity,
    ) -> VaultItem | None:
        """Return one Vault item by authoritative identity.

        Returns ``None`` if the item is not available to this
        account. NOT-FOUND and CROSS-ACCOUNT share the same
        externally-usable posture to avoid leaking record existence.
        """
        if identity is None:
            raise MemoryVaultReadError("identity is required")

        if identity.kind == "canonical":
            if not identity.canonical_memory_id:
                raise MemoryVaultReadError(
                    "canonical identity requires canonical_memory_id"
                )
            return self._get_canonical_item(identity.canonical_memory_id)

        if identity.kind == "compatibility":
            if identity.compatibility_source is None:
                raise MemoryVaultReadError(
                    "compatibility identity requires compatibility_source"
                )
            return self._get_compatibility_item(identity.compatibility_source)

        raise MemoryVaultReadError(f"unknown identity kind: {identity.kind!r}")

    # -- Canonical projection --------------------------------------------

    def _list_canonical_items(
        self, flt: VaultListFilter, *, candidate_limit: int
    ) -> list[VaultItem]:
<<<<<<< ours
        """Query a bounded, filtered canonical candidate window."""
=======
        """Query a bounded canonical candidate set for the account."""
>>>>>>> theirs
        try:
            query = self._session.query(MemoryRecord).filter(
                MemoryRecord.user_id == self._account
            )
            if flt.semantic_species is not None:
                query = query.filter(
                    MemoryRecord.semantic_species == flt.semantic_species
                )
            if flt.project_id is not None:
                query = query.filter(MemoryRecord.project_id == flt.project_id)
            if flt.account_scoped_only:
                query = query.filter(MemoryRecord.project_id.is_(None))
            if flt.pinned is not None:
                query = query.filter(MemoryRecord.pinned == flt.pinned)
            if flt.held is not None:
                query = query.filter(MemoryRecord.held == flt.held)
            if flt.persona_subject_id is not None:
                query = query.filter(
<<<<<<< ours
                    self._session.query(MemoryPersonaLink.link_id)
                    .filter(MemoryPersonaLink.memory_id == MemoryRecord.memory_id)
                    .filter(MemoryPersonaLink.user_id == self._account)
                    .filter(
                        MemoryPersonaLink.persona_subject_id == flt.persona_subject_id
                    )
                    .exists()
                )
            if flt.review_posture is not None:
                query = query.filter(
                    MemoryRecord.reviewed_at.is_not(None)
                    if flt.review_posture == REVIEW_POSTURE_APPROVED
                    else MemoryRecord.reviewed_at.is_(None)
                )
            if flt.lifecycle_posture is not None:
                query = query.filter(
                    MemoryRecord.activated_at.is_not(None)
                    if flt.lifecycle_posture == LIFECYCLE_POSTURE_ACTIVE
                    else MemoryRecord.activated_at.is_(None)
                )
            if flt.source_system is not None:
                query = query.filter(
                    self._session.query(MemoryProvenance.provenance_id)
                    .filter(MemoryProvenance.memory_id == MemoryRecord.memory_id)
                    .filter(MemoryProvenance.user_id == self._account)
                    .filter(MemoryProvenance.source_system == flt.source_system)
                    .exists()
                )
            rows = (
                query.order_by(
                    MemoryRecord.created_at.desc(), MemoryRecord.memory_id.asc()
                )
=======
                    MemoryRecord.memory_id.in_(
                        self._session.query(MemoryPersonaLink.memory_id)
                        .filter(MemoryPersonaLink.user_id == self._account)
                        .filter(
                            MemoryPersonaLink.persona_subject_id
                            == flt.persona_subject_id
                        )
                    )
                )
            if flt.review_posture == REVIEW_POSTURE_APPROVED:
                query = query.filter(MemoryRecord.reviewed_at.is_not(None))
            elif flt.review_posture == REVIEW_POSTURE_PENDING:
                query = query.filter(MemoryRecord.reviewed_at.is_(None))
            if flt.lifecycle_posture == LIFECYCLE_POSTURE_ACTIVE:
                query = query.filter(MemoryRecord.activated_at.is_not(None))
            elif flt.lifecycle_posture == LIFECYCLE_POSTURE_INACTIVE:
                query = query.filter(MemoryRecord.activated_at.is_(None))
            if flt.source_system is not None:
                query = query.filter(
                    MemoryRecord.memory_id.in_(
                        self._session.query(MemoryProvenance.memory_id)
                        .filter(MemoryProvenance.user_id == self._account)
                        .filter(MemoryProvenance.source_system == flt.source_system)
                    )
                )
            rows = (
                query.order_by(MemoryRecord.created_at.desc(), MemoryRecord.memory_id)
>>>>>>> theirs
                .limit(candidate_limit)
                .all()
            )
        except Exception as exc:  # pragma: no cover - SQL layer failure
            raise MemoryVaultReadError(
                "failed to query canonical memory records"
            ) from exc

        return [self._project_canonical_row(row) for row in rows]

    def _get_canonical_item(self, memory_id: str) -> VaultItem | None:
        try:
            row = (
                self._session.query(MemoryRecord)
                .filter(MemoryRecord.memory_id == memory_id)
                .filter(MemoryRecord.user_id == self._account)
                .one_or_none()
            )
        except Exception as exc:  # pragma: no cover - SQL layer failure
            raise MemoryVaultReadError(
                "failed to query canonical memory record"
            ) from exc

        if row is None:
            return None
        return self._project_canonical_row(row)

    def _project_canonical_row(self, row: MemoryRecord) -> VaultItem:
        """Translate one canonical ``MemoryRecord`` into a ``VaultItem``.

        Joins Persona links and provenance rows for the same account.
        Validates that any linked Persona subject belongs to the same
        account; an account mismatch is an integrity defect and
        fails closed.
        """
        memory_id = row.memory_id

        try:
            persona_link_rows = (
                self._session.query(MemoryPersonaLink, PersonaSubject)
                .join(
                    PersonaSubject,
                    (
                        PersonaSubject.persona_subject_id
                        == MemoryPersonaLink.persona_subject_id
                    )
                    & (PersonaSubject.user_id == MemoryPersonaLink.persona_user_id),
                )
                .filter(MemoryPersonaLink.memory_id == memory_id)
                .filter(MemoryPersonaLink.user_id == self._account)
                .all()
            )
            provenance_rows = (
                self._session.query(MemoryProvenance)
                .filter(MemoryProvenance.memory_id == memory_id)
                .filter(MemoryProvenance.user_id == self._account)
                .all()
            )
        except Exception as exc:  # pragma: no cover - SQL layer failure
            raise MemoryVaultReadError(
                f"failed to load persona links / provenance for {memory_id}"
            ) from exc

        persona_links: list[VaultPersonaLink] = []
        for link, subject in persona_link_rows:
            # Account consistency check: a linked Persona subject
            # must belong to the same account as the memory.
            if (
                link.user_id != self._account
                or link.persona_user_id != self._account
                or subject.user_id != self._account
            ):
                raise MemoryVaultReadError(
                    f"memory_persona_links integrity defect: "
                    f"link {link.link_id} for memory {memory_id} "
                    f"references an out-of-account Persona subject"
                )
            persona_links.append(
                VaultPersonaLink(
                    link_id=link.link_id,
                    persona_subject_id=link.persona_subject_id,
                    persona_user_id=link.persona_user_id,
                    link_kind=link.link_kind,
                    display_name_snapshot=subject.display_name_snapshot,
                )
            )

        provenance: list[VaultProvenance] = []
        for prov in provenance_rows:
            provenance.append(
                VaultProvenance(
                    provenance_id=prov.provenance_id,
                    source_system=prov.source_system,
                    source_record_id=prov.source_record_id,
                    source_thread_id=prov.source_thread_id,
                    source_message_id=prov.source_message_id,
                    source_import_job_id=prov.source_import_job_id,
                    source_export_fingerprint=prov.source_export_fingerprint,
                    source_subject_kind=prov.source_subject_kind,
                    source_subject_id=prov.source_subject_id,
                    is_imported=bool(prov.is_imported),
                )
            )

        # Content + payload: episodic uses text_content; facts use
        # fact_key + fact_value. Both may exist for either species;
        # the projection surfaces what is present.
        if row.text_content is not None:
            content = row.text_content
        elif row.fact_value is not None:
            content = row.fact_value
        else:
            content = None

        review_posture = (
            REVIEW_POSTURE_APPROVED
            if row.reviewed_at is not None
            else REVIEW_POSTURE_PENDING
        )
        lifecycle_posture = (
            LIFECYCLE_POSTURE_ACTIVE
            if row.activated_at is not None
            else LIFECYCLE_POSTURE_INACTIVE
        )

        return VaultItem(
            identity=VaultIdentity(
                kind="canonical",
                canonical_memory_id=memory_id,
            ),
            semantic_species=row.semantic_species,
            content=content,
            account_owner=row.user_id,
            project_id=row.project_id,
            review_posture=review_posture,
            lifecycle_posture=lifecycle_posture,
            pinned=bool(row.pinned),
            held=bool(row.held),
            created_at=row.created_at,
            updated_at=row.updated_at,
            persona_links=persona_links,
            provenance=provenance,
            extensions=row.extensions if isinstance(row.extensions, dict) else None,
            compatibility_legacy_source_family=None,
            compatibility_legacy_source_record_id=None,
            compatibility_semantic_species=None,
        )

    # -- Compatibility projection -----------------------------------------

    def _list_compatibility_items(
        self, flt: VaultListFilter, *, candidate_limit: int
    ) -> list[VaultItem]:
        """Query the admitted compatibility sources for the account.

        Uses the proven UMS-03E/F/G adapters through the UMS-03I
        dispatcher. The dispatcher requires explicit source kind, so
        we enumerate the supported kinds.

        Envelope ``memory_entries`` (UMS-03E) is identified by
        ``memory_entries`` rows in the legacy table whose
        ``user_id`` is the authenticated account. The ``memory_entries``
        table is queried directly because there is no list-level
        compatibility dispatcher for it (the dispatcher is single-row
        detail).

        Verified + active ``personal_facts`` (UMS-03F) and candidate
        ``personal_facts`` (UMS-03G) are queried directly via their
        ORM models, then projected through the proven per-row readers.
        """
        items: list[VaultItem] = []

<<<<<<< ours
        # memory_entries (any silo) -> episodic_semantic_memory.
        try:
            query = self._session.query(MemoryEntry).filter(
                MemoryEntry.user_id == self._account
            )
            if not self._memory_entries_can_match(flt):
                memory_entry_rows = []
            else:
=======
        from guardian.db.models import MemoryEntry

        compatibility_dimensions_match = (
            flt.project_id is None
            and flt.persona_subject_id is None
            and flt.source_system in (None, "codexify")
            and flt.held in (None, False)
        )

        # memory_entries (any silo) -> episodic_semantic_memory.
        memory_entry_rows: list[MemoryEntry] = []
        memory_entries_match = (
            compatibility_dimensions_match
            and flt.semantic_species in (None, MemoryEntrySemanticSpecies())
            and flt.review_posture in (None, REVIEW_POSTURE_APPROVED)
            and flt.lifecycle_posture in (None, LIFECYCLE_POSTURE_ACTIVE)
        )
        if memory_entries_match:
            try:
                query = self._session.query(MemoryEntry).filter(
                    MemoryEntry.user_id == self._account
                )
>>>>>>> theirs
                if flt.pinned is not None:
                    query = query.filter(MemoryEntry.pinned == flt.pinned)
                memory_entry_rows = (
                    query.order_by(
<<<<<<< ours
                        MemoryEntry.created_at.desc(),
                        cast(MemoryEntry.id, String).asc(),
=======
                        MemoryEntry.created_at.desc(), cast(MemoryEntry.id, String)
>>>>>>> theirs
                    )
                    .limit(candidate_limit)
                    .all()
                )
<<<<<<< ours
        except Exception as exc:  # pragma: no cover - SQL layer failure
            raise MemoryVaultReadError("failed to query memory_entries") from exc
=======
            except Exception as exc:  # pragma: no cover - SQL layer failure
                raise MemoryVaultReadError("failed to query memory_entries") from exc
>>>>>>> theirs

        for me in memory_entry_rows:
            projection = read_memory_compatibility_projection(
                self._session,
                authenticated_account_id=self._account,
                source=MemoryCompatibilitySourceRef(
                    source_kind=MemoryCompatibilitySourceKind.MEMORY_ENTRY,
                    source_id=int(me.id),
                ),
            )
            if projection is None:
                continue
            items.append(self._project_compatibility_projection(projection))

        # personal_facts: both verified + active AND candidate.
<<<<<<< ours
        try:
            query = self._session.query(PersonalFact).filter(
                PersonalFact.user_id == self._account
            )
            if not self._personal_facts_can_match(flt):
                personal_fact_rows = []
            else:
                verified_active = (
                    PersonalFact.status == "verified"
                ) & PersonalFact.is_active.is_(True)
                if (
                    flt.semantic_species == PersonalFactVerifiedSemanticSpecies()
                    or flt.review_posture == REVIEW_POSTURE_APPROVED
                    or flt.lifecycle_posture == LIFECYCLE_POSTURE_ACTIVE
                ):
                    query = query.filter(verified_active)
                elif (
                    flt.semantic_species == PersonalFactCandidateSemanticSpecies()
                    or flt.review_posture == REVIEW_POSTURE_PENDING
                    or flt.lifecycle_posture == LIFECYCLE_POSTURE_INACTIVE
                ):
                    query = query.filter(
                        or_(
                            PersonalFact.status.in_(
                                ("candidate", "disputed", "archived")
                            ),
=======
        personal_fact_rows: list[PersonalFact] = []
        personal_facts_match = (
            compatibility_dimensions_match
            and flt.semantic_species
            in (
                None,
                PersonalFactVerifiedSemanticSpecies(),
                PersonalFactCandidateSemanticSpecies(),
            )
            and flt.pinned in (None, False)
        )
        if personal_facts_match:
            try:
                verified = and_(
                    PersonalFact.status == "verified",
                    PersonalFact.is_active.is_(True),
                )
                query = self._session.query(PersonalFact).filter(
                    PersonalFact.user_id == self._account
                )
                if flt.semantic_species == PersonalFactVerifiedSemanticSpecies():
                    query = query.filter(verified)
                elif flt.semantic_species == PersonalFactCandidateSemanticSpecies():
                    query = query.filter(
                        or_(
                            PersonalFact.status != "verified",
                            PersonalFact.is_active.is_(False),
                        )
                    )
                if flt.review_posture == REVIEW_POSTURE_APPROVED:
                    query = query.filter(verified)
                elif flt.review_posture == REVIEW_POSTURE_PENDING:
                    query = query.filter(
                        or_(
                            PersonalFact.status != "verified",
                            PersonalFact.is_active.is_(False),
                        )
                    )
                if flt.lifecycle_posture == LIFECYCLE_POSTURE_ACTIVE:
                    query = query.filter(verified)
                elif flt.lifecycle_posture == LIFECYCLE_POSTURE_INACTIVE:
                    query = query.filter(
                        or_(
                            PersonalFact.status != "verified",
>>>>>>> theirs
                            PersonalFact.is_active.is_(False),
                        )
                    )
                personal_fact_rows = (
                    query.order_by(
<<<<<<< ours
                        PersonalFact.created_at.desc(),
                        cast(PersonalFact.id, String).asc(),
=======
                        PersonalFact.created_at.desc(), cast(PersonalFact.id, String)
>>>>>>> theirs
                    )
                    .limit(candidate_limit)
                    .all()
                )
<<<<<<< ours
        except Exception as exc:  # pragma: no cover - SQL layer failure
            raise MemoryVaultReadError("failed to query personal_facts") from exc
=======
            except Exception as exc:  # pragma: no cover - SQL layer failure
                raise MemoryVaultReadError("failed to query personal_facts") from exc
>>>>>>> theirs

        for pf in personal_fact_rows:
            projection = read_memory_compatibility_projection(
                self._session,
                authenticated_account_id=self._account,
                source=MemoryCompatibilitySourceRef(
                    source_kind=MemoryCompatibilitySourceKind.PERSONAL_FACT,
                    source_id=int(pf.id),
                ),
            )
            if projection is None:
                continue
            items.append(self._project_compatibility_projection(projection))

        return items

    @staticmethod
    def _memory_entries_can_match(flt: VaultListFilter) -> bool:
        """Return whether a legacy memory entry can satisfy ``flt``."""
        return not (
            (
                flt.semantic_species is not None
                and flt.semantic_species != "episodic_semantic_memory"
            )
            or flt.project_id is not None
            or flt.persona_subject_id is not None
            or flt.review_posture not in (None, REVIEW_POSTURE_APPROVED)
            or flt.lifecycle_posture not in (None, LIFECYCLE_POSTURE_ACTIVE)
            or flt.source_system not in (None, "codexify")
            or flt.held is True
        )

    @staticmethod
    def _personal_facts_can_match(flt: VaultListFilter) -> bool:
        """Return whether a compatibility Personal Fact can satisfy ``flt``."""
        return not (
            (
                flt.semantic_species is not None
                and flt.semantic_species
                not in {
                    PersonalFactVerifiedSemanticSpecies(),
                    PersonalFactCandidateSemanticSpecies(),
                }
            )
            or flt.project_id is not None
            or flt.persona_subject_id is not None
            or flt.source_system not in (None, "codexify")
            or flt.pinned is True
            or flt.held is True
        )

    def _get_compatibility_item(
        self, source: MemoryCompatibilitySourceRef
    ) -> VaultItem | None:
        projection = read_memory_compatibility_projection(
            self._session,
            authenticated_account_id=self._account,
            source=source,
        )
        if projection is None:
            return None
        return self._project_compatibility_projection(projection)

    def _project_compatibility_projection(
        self, projection: MemoryCompatibilityProjection
    ) -> VaultItem:
        """Translate a ``MemoryCompatibilityProjection`` into a ``VaultItem``.

        The compatibility projection is the canonical-envelope view
        of a legacy source row. The Vault normalizes the result
        into its logical read DTO without persisting that
        normalization.
        """
        # Posture derivation reuses the UMS-03F / UMS-03G readers'
        # frozen mapping. The compatibility reader's
        # ``semantic_species`` field already carries the correct
        # canonical envelope species (verified_personal_fact or
        # candidate_unreviewed_fact) for personal facts, and
        # episodic_semantic_memory for memory entries.
        semantic_species = projection.semantic_species

        if projection.legacy_source_family == (
            MemoryCompatibilitySourceKind.MEMORY_ENTRY.value
        ):
            # Legacy memory entry -> episodic_semantic_memory.
            # Review posture is approved (ambient-eligible by
            # default at insertion); lifecycle is active. No
            # personal-facts authority applies.
            review_posture = REVIEW_POSTURE_APPROVED
            lifecycle_posture = LIFECYCLE_POSTURE_ACTIVE
        elif semantic_species == PersonalFactVerifiedSemanticSpecies():
            review_posture = REVIEW_POSTURE_APPROVED
            lifecycle_posture = LIFECYCLE_POSTURE_ACTIVE
        elif semantic_species == PersonalFactCandidateSemanticSpecies():
            review_posture = REVIEW_POSTURE_PENDING
            # Personal Facts authority retains activation state on
            # the source row; the Vault does not reinterpret it as
            # approval. ``is_active`` is preserved on the projection
            # via the underlying reader; we render lifecycle as the
            # admitted posture.
            lifecycle_posture = LIFECYCLE_POSTURE_INACTIVE
        else:
            review_posture = REVIEW_POSTURE_PENDING
            lifecycle_posture = LIFECYCLE_POSTURE_INACTIVE

        # Compatibility items never carry canonical Project scope,
        # canonical Persona links, or canonical provenance
        # multiplicity. Their sole provenance row is the frozen
        # compatibility provenance.
        compatibility_provenance: list[VaultProvenance] = []
        if projection.provenance is not None:
            cp = projection.provenance
            compatibility_provenance.append(
                VaultProvenance(
                    provenance_id=(f"{cp.source_system}:{cp.source_record_id}"),
                    source_system=cp.source_system,
                    source_record_id=cp.source_record_id,
                    source_thread_id=None,
                    source_message_id=None,
                    source_import_job_id=None,
                    source_export_fingerprint=None,
                    source_subject_kind=None,
                    source_subject_id=None,
                    is_imported=False,
                )
            )

        return VaultItem(
            identity=VaultIdentity(
                kind="compatibility",
                compatibility_source=MemoryCompatibilitySourceRef(
                    source_kind=(
                        MemoryCompatibilitySourceKind.MEMORY_ENTRY
                        if projection.legacy_source_family
                        == MemoryCompatibilitySourceKind.MEMORY_ENTRY.value
                        else MemoryCompatibilitySourceKind.PERSONAL_FACT
                    ),
                    source_id=_source_id_from_record_id(
                        projection.legacy_source_record_id
                    ),
                ),
            ),
            semantic_species=semantic_species,
            content=projection.content,
            account_owner=projection.account_user_id,
            project_id=projection.project_id,
            review_posture=review_posture,
            lifecycle_posture=lifecycle_posture,
            pinned=bool(projection.pinned),
            held=False,
            created_at=projection.created_at,
            updated_at=projection.updated_at,
            persona_links=[],
            provenance=compatibility_provenance,
            extensions=None,
            compatibility_legacy_source_family=(projection.legacy_source_family),
            compatibility_legacy_source_record_id=(projection.legacy_source_record_id),
            compatibility_semantic_species=projection.semantic_species,
        )

    # -- Filters ----------------------------------------------------------

    def _apply_filters(
        self,
        items: list[VaultItem],
        flt: VaultListFilter,
    ) -> list[VaultItem]:
        """Apply the supplied filter dimensions to the candidate list."""
        result: list[VaultItem] = []
        for item in items:
            if flt.semantic_species is not None:
                if item.semantic_species != flt.semantic_species:
                    continue
            if flt.project_id is not None:
                if item.project_id != flt.project_id:
                    continue
            if flt.account_scoped_only:
                if item.project_id is not None:
                    continue
            if flt.persona_subject_id is not None:
                if not any(
                    link.persona_subject_id == flt.persona_subject_id
                    for link in item.persona_links
                ):
                    continue
            if flt.review_posture is not None:
                if item.review_posture != flt.review_posture:
                    continue
            if flt.lifecycle_posture is not None:
                if item.lifecycle_posture != flt.lifecycle_posture:
                    continue
            if flt.source_system is not None:
                if not any(
                    p.source_system == flt.source_system for p in item.provenance
                ):
                    continue
            if flt.pinned is not None:
                if item.pinned != flt.pinned:
                    continue
            if flt.held is not None:
                if item.held != flt.held:
                    continue
            result.append(item)
        return result

    # -- Helpers ----------------------------------------------------------

    @staticmethod
    def _normalize_limit(limit: int) -> int:
        if not isinstance(limit, int):
            raise MemoryVaultReadError("limit must be an integer")
        if limit <= 0:
            raise MemoryVaultReadError("limit must be positive")
        if limit > MAX_LIST_LIMIT:
            return MAX_LIST_LIMIT
        return limit

    @staticmethod
    def _normalize_offset(offset: int) -> int:
        if not isinstance(offset, int):
            raise MemoryVaultReadError("offset must be an integer")
        if offset < 0:
            raise MemoryVaultReadError("offset must be non-negative")
        return offset


def _stable_identity_key(item: VaultItem) -> str:
    """Return a deterministic identity string for tie-break sorting."""
    if item.identity.kind == "canonical" and item.identity.canonical_memory_id:
        return f"canonical:{item.identity.canonical_memory_id}"
    if item.identity.compatibility_source is not None:
        src = item.identity.compatibility_source
        return f"compatibility:{src.source_kind.value}:{src.source_id}"
    return f"compatibility:{item.compatibility_legacy_source_family}:{item.compatibility_legacy_source_record_id}"


def _source_id_from_record_id(record_id: str | None) -> int:
    """Extract the numeric source id from a ``<family>:<id>`` record id.

    Compatibility record ids are frozen to ``"<family>:<id>"`` form by
    the UMS-03 readers. This helper is robust to unexpected shapes by
    raising ``MemoryVaultReadError`` so an unrecognized projection
    cannot masquerade as a known identity.
    """
    if not record_id:
        raise MemoryVaultReadError("compatibility source_record_id is missing")
    parts = record_id.split(":", 1)
    if len(parts) != 2:
        raise MemoryVaultReadError(
            f"unrecognized compatibility source_record_id shape: {record_id!r}"
        )
    try:
        return int(parts[1])
    except ValueError as exc:
        raise MemoryVaultReadError(
            f"non-numeric compatibility source_record_id: {record_id!r}"
        ) from exc


def PersonalFactVerifiedSemanticSpecies() -> str:
    """Return the canonical ``verified_personal_fact`` species token.

    Imported lazily so the service module loads even if Personal
    Facts authority surface changes its import path.
    """
    from guardian.protocol_tokens import MemorySemanticSpecies

    return MemorySemanticSpecies.VERIFIED_PERSONAL_FACT.value


def MemoryEntrySemanticSpecies() -> str:
    """Return the canonical ``episodic_semantic_memory`` species token."""
    from guardian.protocol_tokens import MemorySemanticSpecies

    return MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value


def PersonalFactCandidateSemanticSpecies() -> str:
    """Return the canonical ``candidate_unreviewed_fact`` species token."""
    from guardian.protocol_tokens import MemorySemanticSpecies

    return MemorySemanticSpecies.CANDIDATE_UNREVIEWED_FACT.value


__all__ = [
    "DEFAULT_LIST_LIMIT",
    "MAX_LIST_LIMIT",
    "MemoryVaultReadError",
    "MemoryVaultReadService",
    "VaultIdentity",
    "VaultItem",
    "VaultListFilter",
    "VaultPersonaLink",
    "VaultProvenance",
]
