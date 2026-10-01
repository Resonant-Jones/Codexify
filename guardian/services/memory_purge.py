"""Audited ordinary-memory permanent erasure and resurrection suppression (UMS-11).

This is the sole canonical permanent-erasure authority for ordinary
account-owned memory. It closes the one foundational gap admitted by the
2026-09-30 Campaign revalidation, which recorded::

    UMS_FOUNDATIONAL_GAP_REMAINS
    EXACT FOUNDATIONAL GAP: audited permanent erasure + import-resurrection
                            suppression

Contract §12 makes purge mandatory before supported user-facing release and
ADR-084 holds that release until permanent erasure and re-import suppression
are *proven*. Both were absent: no relation, no service, no route, no proof.
Contract §12 also twice deferred its own implementation to UMS-11, so the
capability had no owner. This module is that owner.

Retirement is not purge. ``retired`` (ADR-089, UMS-05C10B-W) is canonically
retained and reversibly restorable. Purge is neither: it destroys content and
leaves only a minimum non-content tombstone. The two are never conflated here.

Design commitments
------------------

**One exact target.** This service purges exactly one canonical
``memory_records`` row inside the authenticated account boundary. There is no
bulk, Project-wide, or account-wide purge; those are separate capabilities and
are not authorized.

**Tombstone first, and it is minimal.** The surviving row carries no memory
text, no revision text, no evidence excerpt, no plaintext source entity id, no
Project or Persona name, no embedding, and no free-form extensions. Identity
is a versioned domain-separated digest; the suppression posture is
structurally immutable.

**Fail closed on ambiguous import origin.** A record that is demonstrably
import-origin but cannot yield one safe deterministic source-atom identity is
*not* erased, because erasing it while knowingly leaving automatic
resurrection possible would be a false erasure claim.

**Suppression cannot be cleared.** There is no bypass flag. No model,
Operator, importer, retry, or internal service clears suppression. Explicit
account-user reintroduction is a separate audited future flow and is not
built here.

**Import admission is provider-neutral.** The suppression authority is
expressed over canonical source identity, not over any provider adapter. UMS-08
stays parked; no Anthropic adapter is built and no importer is opened.

Current derived-state inventory (verified, not assumed)
-------------------------------------------------------

Purge deletes derived state only where a current runtime surface actually
exists and is keyed to the erased memory. Repository inspection at UMS-11
established:

* **Vector/embedding** -- NONE. ``guardian/vector_store.py`` and
  ``guardian/embeddings/`` never reference ``memory_records`` or
  ``memory_id``. There is no canonical UMS vector projection to remove.
* **Summaries** -- NONE. No UMS summary relation exists.
* **Heat/ranking projection** -- NOT UMS. The only ``heat_score`` column
  belongs to ``imprints`` (cognition), which is not a canonical memory
  relation and is not keyed to ``memory_records``.
* **Cache** -- NONE. No UMS memory cache or projection table exists.
* **Queued derived work / retry payloads** -- NONE. No ``memory_id`` appears
  anywhere under ``guardian/queue/`` or ``guardian/cognition/``.
* **Working export artifacts** -- NONE under application control. Archives
  previously downloaded by a user are outside Codexify's control and are
  explicitly *not* claimed as erased.
* **Graph-derived memory state** -- NONE.

No generic queue scanner, vector-deletion framework, or graph-erasure
subsystem is created for projections that do not exist. Creating one would be
architecture expansion, which Campaign governance has frozen. If a UMS
derived surface is introduced later, this inventory -- not this slice -- is
where it must be added, together with its own deletion obligation.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from guardian.db.models import (
    MemoryLifecycleRevision,
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryPurgeTombstone,
    MemoryRecord,
    MemoryReviewRevision,
    MemoryRevision,
)

__all__ = [
    "MemoryPurgeAmbiguousSourceIdentity",
    "MemoryPurgeConflict",
    "MemoryPurgeError",
    "MemoryPurgeIntegrityError",
    "MemoryPurgeInvalid",
    "MemoryPurgeNotAvailable",
    "MemoryPurgePreview",
    "MemoryPurgeResult",
    "MemoryPurgeService",
    "MemorySourceSuppressionStatus",
    "PURGED_RECORD_FINGERPRINT_VERSION",
    "SOURCE_ATOM_FINGERPRINT_VERSION",
    "SUPPRESSION_OUTCOME_ALLOWED",
    "SUPPRESSION_OUTCOME_SUPPRESSED",
    "purged_record_fingerprint",
    "source_atom_fingerprint",
]


# ---------------------------------------------------------------------------
# Vocabulary.
# ---------------------------------------------------------------------------

#: Suppression outcome when a source atom was previously purged by this
#: account. Deliberately distinct from deduplication: a suppressed atom is
#: never created, not merely skipped as a duplicate.
SUPPRESSION_OUTCOME_SUPPRESSED = "suppressed_previously_purged"

#: Suppression outcome when no tombstone matches. Callers may admit the atom.
SUPPRESSION_OUTCOME_ALLOWED = "allowed"


# ---------------------------------------------------------------------------
# Fingerprint versions and domains.
#
# Centralized here so the algorithm and its version are auditable in one
# place and are test-covered rather than re-derived per call site. The
# ``v1:`` prefix is part of the stored value: a future algorithm change is a
# new version, never a silent reinterpretation of existing digests.
# ---------------------------------------------------------------------------

PURGED_RECORD_FINGERPRINT_VERSION = "v1"
SOURCE_ATOM_FINGERPRINT_VERSION = "v1"

_PURGED_RECORD_DOMAIN = "memory-purge.purged-record.v1"
_SOURCE_ATOM_DOMAIN = "memory-purge.source-atom.v1"
_CONFIRMATION_TOKEN_DOMAIN = "memory-purge.confirmation.v1"

#: ASCII unit separator. Used only as a domain marker ahead of the hashed
#: payload, never as a field delimiter: a bare delimiter lets a
#: caller-controlled identity shift a field boundary and collide with a
#: different tuple. Fields are length-prefixed instead, which makes the
#: encoding injective.
_DOMAIN_MARKER = "\x1f"


def _digest(domain: str, payload: str) -> str:
    return hashlib.sha256(f"{domain}{_DOMAIN_MARKER}{payload}".encode()).hexdigest()


def _encode_fields(*fields: str) -> str:
    """Length-prefix each field so field boundaries cannot be forged.

    ``["a\\x1fb", "c"]`` and ``["a", "b\\x1fc"]`` join to different strings,
    whereas a naive separator join would let them collide. Suppression
    identity must be injective: a collision would make two different source
    atoms share one suppression entry, or let one atom forge another's.
    """
    return "".join(f"{len(field)}:{field}" for field in fields)


def purged_record_fingerprint(memory_id: str) -> str:
    """Return the versioned opaque digest of an erased canonical record.

    Deterministic, so an idempotent retry can detect an existing tombstone
    from the requested identity alone -- after the canonical row is gone.
    Non-content and non-reversible in normal operation: the input is a
    server-generated UUID-shaped identity, never authored text.
    """
    if not isinstance(memory_id, str) or not memory_id.strip():
        raise MemoryPurgeInvalid("memory_id is required")
    digest = _digest(_PURGED_RECORD_DOMAIN, memory_id.strip())
    return f"{PURGED_RECORD_FINGERPRINT_VERSION}:{digest}"


def source_atom_fingerprint(
    *,
    source_system: str,
    source_entity_kind: str | None,
    source_atom_identity: str,
) -> str:
    """Return the versioned opaque digest of a minimum source-atom identity.

    The input is the minimum stable source identity needed to detect replay.
    It is hashed, never retained: the plaintext source entity id is not
    recoverable from a tombstone.
    """
    if not isinstance(source_system, str) or not source_system.strip():
        raise MemoryPurgeInvalid("source_system is required")
    if not isinstance(source_atom_identity, str) or not source_atom_identity.strip():
        raise MemoryPurgeInvalid("source_atom_identity is required")
    kind = (source_entity_kind or "").strip()
    payload = _encode_fields(
        source_system.strip(),
        kind,
        source_atom_identity.strip(),
    )
    digest = _digest(_SOURCE_ATOM_DOMAIN, payload)
    return f"{SOURCE_ATOM_FINGERPRINT_VERSION}:{digest}"


def _confirmation_token(envelope: _PurgeEnvelope) -> str:
    """Return an opaque confirmation token bound to the current target.

    This is a *target confirmation* mechanism, not authentication. The
    authenticated account principal remains the authority boundary; a caller
    who cannot authenticate cannot reach this check at all. The token only
    proves that the caller saw this exact destructive envelope and still
    intends it.

    The token changes whenever the destructive target changes: it binds the
    canonical identity, the current CAS token, the record fingerprint, and
    every linked-state count that will be destroyed. It embeds no content.
    """
    parts = [
        envelope.memory_id,
        envelope.record_fingerprint,
        envelope.updated_at.isoformat(),
        str(envelope.content_revision_count),
        str(envelope.review_revision_count),
        str(envelope.lifecycle_revision_count),
        str(envelope.provenance_count),
        str(envelope.persona_link_count),
        str(envelope.derived_state_count),
    ]
    digest = _digest(_CONFIRMATION_TOKEN_DOMAIN, _encode_fields(*parts))
    return f"{PURGED_RECORD_FINGERPRINT_VERSION}:{digest}"


# ---------------------------------------------------------------------------
# Errors.
#
# Bounded, typed, and free of SQL, fingerprints, source plaintext ids, and
# another account's existence. HTTP mapping lives in the route adapter.
# ---------------------------------------------------------------------------


class MemoryPurgeError(Exception):
    """Base class for permanent-erasure failures."""


class MemoryPurgeNotAvailable(MemoryPurgeError):
    """Target is missing or belongs to another account. Externally 404."""


class MemoryPurgeConflict(MemoryPurgeError):
    """Stale CAS, stale confirmation, or ambiguous destructive target."""


class MemoryPurgeAmbiguousSourceIdentity(MemoryPurgeConflict):
    """Import-origin record cannot yield one safe source-atom identity."""


class MemoryPurgeIntegrityError(MemoryPurgeError):
    """Persisted canonical state is outside the vocabulary purge can trust."""


class MemoryPurgeInvalid(MemoryPurgeError):
    """Malformed request input. Externally 422."""


# ---------------------------------------------------------------------------
# Result shapes.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PurgeEnvelope:
    """Internal exact destructive-target description."""

    memory_id: str
    updated_at: datetime
    record_fingerprint: str
    content_revision_count: int
    review_revision_count: int
    lifecycle_revision_count: int
    provenance_count: int
    persona_link_count: int
    derived_state_count: int
    source_system: str | None
    source_entity_kind: str | None
    source_atom_fingerprint: str | None
    suppression_ambiguity: str | None


@dataclass(frozen=True)
class MemoryPurgePreview:
    """Exactly what one authenticated account is about to destroy.

    Carries no content, no hidden unrelated records, no raw queue payloads,
    and no vector bodies. It reports counts and identity so the authenticated
    user can make an informed decision.
    """

    memory_id: str
    record_fingerprint: str
    updated_at: datetime
    content_revision_count: int
    review_revision_count: int
    lifecycle_revision_count: int
    provenance_count: int
    persona_link_count: int
    derived_state_count: int
    suppression_fingerprint_available: bool
    suppression_ambiguity: str | None
    confirmation_token: str

    @property
    def total_affected_rows(self) -> int:
        """Canonical rows destroyed, excluding the surviving tombstone."""
        return (
            1
            + self.content_revision_count
            + self.review_revision_count
            + self.lifecycle_revision_count
            + self.provenance_count
            + self.persona_link_count
        )


@dataclass(frozen=True)
class MemoryPurgeResult:
    """Outcome of one purge, or of one idempotent retry."""

    memory_id: str
    changed: bool
    already_purged: bool
    purge_receipt_id: str
    purged_at: datetime
    record_fingerprint: str
    source_atom_fingerprint: str | None
    suppression: bool
    deleted_content_revisions: int = 0
    deleted_review_revisions: int = 0
    deleted_lifecycle_revisions: int = 0
    deleted_provenance: int = 0
    deleted_persona_links: int = 0


@dataclass(frozen=True)
class MemorySourceSuppressionStatus:
    """Account-scoped replay-suppression verdict for one source atom."""

    suppressed: bool
    outcome: str
    source_system: str
    source_entity_kind: str | None
    source_atom_fingerprint: str
    purged_at: datetime | None = None
    reasons: tuple[str, ...] = field(default=())


#: Canonical child relations destroyed by a successful first-time purge. The
#: parent ``memory_records`` row is removed separately and is the only row not
#: enumerated here.
_CANONICAL_CHILD_MODELS: tuple[type, ...] = (
    MemoryRevision,
    MemoryReviewRevision,
    MemoryLifecycleRevision,
    MemoryProvenance,
    MemoryPersonaLink,
)


class MemoryPurgeService:
    """Account-owned canonical permanent-erasure service for ordinary memory.

    The authenticated account identity is constructor-supplied and immutable;
    there is no per-call actor or account override. Infrastructure Operator
    authority, model authority, Persona authority, and Project ownership are
    all insufficient: only the owning authenticated account may purge.
    """

    def __init__(
        self,
        session: Session,
        *,
        authenticated_account_id: str,
    ) -> None:
        if session is None:
            raise MemoryPurgeError("session is required")
        if not authenticated_account_id or not isinstance(
            authenticated_account_id, str
        ):
            raise MemoryPurgeError(
                "authenticated_account_id is required and must be a non-empty string"
            )
        self._session = session
        self._account = authenticated_account_id

    # -- Public API --------------------------------------------------------

    def preview_purge(self, *, memory_id: str) -> MemoryPurgePreview:
        """Describe the exact destructive target without destroying anything.

        Read-only. Account-scoped: a missing or cross-account canonical
        target raises :class:`MemoryPurgeNotAvailable`, so preview never
        discloses another account's existence.
        """
        self._validate_memory_id(memory_id)
        row = self._load_authorized_memory(memory_id, for_update=False)
        if row is None:
            # A missing and a cross-account target share one indistinguishable
            # posture. Preview must never surface a different error for them,
            # and must never fall through to envelope construction.
            self._session.rollback()
            raise MemoryPurgeNotAvailable("memory item is not available")
        envelope = self._compute_envelope(row)
        return MemoryPurgePreview(
            memory_id=envelope.memory_id,
            record_fingerprint=envelope.record_fingerprint,
            updated_at=envelope.updated_at,
            content_revision_count=envelope.content_revision_count,
            review_revision_count=envelope.review_revision_count,
            lifecycle_revision_count=envelope.lifecycle_revision_count,
            provenance_count=envelope.provenance_count,
            persona_link_count=envelope.persona_link_count,
            derived_state_count=envelope.derived_state_count,
            suppression_fingerprint_available=(
                envelope.source_atom_fingerprint is not None
            ),
            suppression_ambiguity=envelope.suppression_ambiguity,
            confirmation_token=_confirmation_token(envelope),
        )

    def purge(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        confirmation_token: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> MemoryPurgeResult:
        """Permanently erase one canonical ordinary memory.

        Ordering is authority-first. Nothing destructive begins before the
        target is locked, account ownership is proven, the supplied CAS token
        is fresh, and the confirmation token is recomputed and matched against
        the *current* envelope. A stale CAS token or a confirmation token
        minted against an older snapshot fails before any deletion.

        Within the database transaction a first-time purge atomically:

        1. inserts exactly one minimum non-content purge tombstone;
        2. removes every canonical child relation;
        3. removes the canonical ``memory_records`` parent; and
        4. commits.

        ``content absent + no tombstone`` and ``tombstone present + content
        still present`` are both impossible across a commit boundary.

        Retrying a completed purge with the same account and the same
        canonical identity is idempotent: it returns the original receipt
        identity and purge time and creates nothing. A cross-account retry
        cannot observe the tombstone and receives
        :class:`MemoryPurgeNotAvailable`.

        ``reason`` and ``request_ref`` are accepted for audit correlation but
        are deliberately **not** written to the tombstone: the tombstone is
        non-content and must not accumulate descriptive text.
        """
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)
        if not isinstance(confirmation_token, str) or not confirmation_token.strip():
            raise MemoryPurgeInvalid("confirmation_token is required")

        record_fp = purged_record_fingerprint(memory_id)

        # 1. Lock and load the canonical target, proving account ownership.
        row = self._load_authorized_memory(memory_id, for_update=True)

        if row is None:
            # The canonical row is gone. This is either a retry of a purge
            # this account already performed, or a target that never existed
            # / belongs to another account. Only an account-scoped tombstone
            # distinguishes them, so a cross-account caller learns nothing.
            existing = self._find_tombstone_by_record_fingerprint(record_fp)
            if existing is None:
                self._session.rollback()
                raise MemoryPurgeNotAvailable("memory item is not available")
            self._session.rollback()
            return MemoryPurgeResult(
                memory_id=memory_id,
                changed=False,
                already_purged=True,
                purge_receipt_id=existing.purge_receipt_id,
                purged_at=existing.purged_at,
                record_fingerprint=existing.purged_record_fingerprint,
                source_atom_fingerprint=existing.source_atom_fingerprint,
                suppression=True,
            )

        # 2. CAS authority, validated before any confirmation or deletion.
        if row.updated_at != expected_updated_at:
            self._session.rollback()
            raise MemoryPurgeConflict(
                "memory item changed; expected_updated_at is stale"
            )

        # 3. Recompute the envelope against the locked current state.
        envelope = self._compute_envelope(row)

        # 4. Validate the confirmation token against the current envelope.
        expected_token = _confirmation_token(envelope)
        if not _constant_time_equals(expected_token, confirmation_token.strip()):
            self._session.rollback()
            raise MemoryPurgeConflict("purge confirmation is stale or invalid")

        # 5. Fail closed *before* deletion when import origin is ambiguous.
        #    Erasing here would knowingly leave automatic resurrection
        #    possible while claiming the record was permanently erased.
        if envelope.suppression_ambiguity is not None:
            self._session.rollback()
            raise MemoryPurgeAmbiguousSourceIdentity(
                "import-origin record has no single safe source-atom identity"
            )

        purge_receipt_id = str(uuid.uuid4())
        tombstone = MemoryPurgeTombstone(
            purge_receipt_id=purge_receipt_id,
            user_id=self._account,
            purged_record_fingerprint=envelope.record_fingerprint,
            source_system=envelope.source_system,
            source_entity_kind=envelope.source_entity_kind,
            source_atom_fingerprint=envelope.source_atom_fingerprint,
            suppress_reimport=True,
        )
        self._session.add(tombstone)
        # Surface constraint violations (for example a concurrent duplicate
        # suppression entry) before destructive statements run.
        self._session.flush()

        # 6. Canonical deletion fan-out. Child relations are removed
        #    explicitly rather than relying on CASCADE so the destroyed
        #    surface is enumerable and provable.
        deleted_counts: dict[type, int] = {}
        for model in _CANONICAL_CHILD_MODELS:
            result = self._session.execute(
                delete(model).where(model.memory_id == memory_id)
            )
            deleted_counts[model] = int(result.rowcount or 0)

        # 7. Remove the canonical parent itself.
        parent = self._session.execute(
            delete(MemoryRecord).where(
                MemoryRecord.memory_id == memory_id,
                MemoryRecord.user_id == self._account,
            )
        )
        deleted_parent = int(parent.rowcount or 0)
        if deleted_parent != 1:
            # Should be unreachable while the row is locked, but a purge that
            # did not destroy its target is never committed.
            self._session.rollback()
            raise MemoryPurgeIntegrityError("canonical memory was not destroyed")

        self._session.commit()
        self._session.refresh(tombstone)

        return MemoryPurgeResult(
            memory_id=memory_id,
            changed=True,
            already_purged=False,
            purge_receipt_id=purge_receipt_id,
            purged_at=tombstone.purged_at,
            record_fingerprint=envelope.record_fingerprint,
            source_atom_fingerprint=envelope.source_atom_fingerprint,
            suppression=True,
            deleted_content_revisions=deleted_counts[MemoryRevision],
            deleted_review_revisions=deleted_counts[MemoryReviewRevision],
            deleted_lifecycle_revisions=deleted_counts[MemoryLifecycleRevision],
            deleted_provenance=deleted_counts[MemoryProvenance],
            deleted_persona_links=deleted_counts[MemoryPersonaLink],
        )

    def source_atom_suppression_status(
        self,
        *,
        source_system: str,
        source_entity_kind: str | None,
        source_atom_identity: str,
    ) -> MemorySourceSuppressionStatus:
        """Report whether this account previously purged a source atom.

        Provider-neutral and account-scoped. The caller supplies canonical
        *raw* source identity; stored fingerprints are never accepted as the
        caller-facing authority input and never leave this service.

        Import admission must consult this before creating any canonical
        memory atom. A ``suppressed_previously_purged`` result means: create
        no record, no revision, no provenance, and no derived state, and do
        not report it as deduplication.
        """
        if not isinstance(source_system, str) or not source_system.strip():
            raise MemoryPurgeInvalid("source_system is required")
        if (
            not isinstance(source_atom_identity, str)
            or not source_atom_identity.strip()
        ):
            raise MemoryPurgeInvalid("source_atom_identity is required")

        fingerprint = source_atom_fingerprint(
            source_system=source_system,
            source_entity_kind=source_entity_kind,
            source_atom_identity=source_atom_identity,
        )
        row = self._session.execute(
            select(MemoryPurgeTombstone).where(
                MemoryPurgeTombstone.user_id == self._account,
                MemoryPurgeTombstone.source_atom_fingerprint == fingerprint,
                MemoryPurgeTombstone.suppress_reimport.is_(True),
            )
        ).scalar_one_or_none()

        if row is None:
            return MemorySourceSuppressionStatus(
                suppressed=False,
                outcome=SUPPRESSION_OUTCOME_ALLOWED,
                source_system=source_system.strip(),
                source_entity_kind=(source_entity_kind or None),
                source_atom_fingerprint=fingerprint,
            )

        return MemorySourceSuppressionStatus(
            suppressed=True,
            outcome=SUPPRESSION_OUTCOME_SUPPRESSED,
            source_system=source_system.strip(),
            source_entity_kind=row.source_entity_kind,
            source_atom_fingerprint=fingerprint,
            purged_at=row.purged_at,
        )

    # -- Internals ---------------------------------------------------------

    def _load_authorized_memory(
        self, memory_id: str, *, for_update: bool
    ) -> MemoryRecord | None:
        statement = select(MemoryRecord).where(
            MemoryRecord.memory_id == memory_id,
            MemoryRecord.user_id == self._account,
        )
        if for_update:
            # Serialize purge against content correction, review transition,
            # lifecycle transition, Persona attribution, and pin/hold, all of
            # which take the same row lock. A competing mutation either
            # finishes first and invalidates this CAS/confirmation, or waits
            # and then observes the row gone.
            statement = statement.with_for_update()
        return self._session.execute(statement).scalar_one_or_none()

    def _find_tombstone_by_record_fingerprint(
        self, record_fingerprint: str
    ) -> MemoryPurgeTombstone | None:
        return self._session.execute(
            select(MemoryPurgeTombstone).where(
                MemoryPurgeTombstone.user_id == self._account,
                MemoryPurgeTombstone.purged_record_fingerprint == record_fingerprint,
            )
        ).scalar_one_or_none()

    def _count(self, model: type, memory_id: str) -> int:
        return int(
            self._session.execute(
                select(func.count())
                .select_from(model)
                .where(model.memory_id == memory_id)
            ).scalar_one()
        )

    def _compute_envelope(self, row: MemoryRecord) -> _PurgeEnvelope:
        memory_id = row.memory_id
        (
            source_system,
            source_entity_kind,
            source_fp,
            ambiguity,
        ) = self._derive_suppression_identity(memory_id)
        return _PurgeEnvelope(
            memory_id=memory_id,
            updated_at=row.updated_at,
            record_fingerprint=purged_record_fingerprint(memory_id),
            content_revision_count=self._count(MemoryRevision, memory_id),
            review_revision_count=self._count(MemoryReviewRevision, memory_id),
            lifecycle_revision_count=self._count(MemoryLifecycleRevision, memory_id),
            provenance_count=self._count(MemoryProvenance, memory_id),
            persona_link_count=self._count(MemoryPersonaLink, memory_id),
            # Verified absent; see the module docstring inventory. Reported
            # explicitly so the preview never implies derived cleanup that
            # is not happening.
            derived_state_count=0,
            source_system=source_system,
            source_entity_kind=source_entity_kind,
            source_atom_fingerprint=source_fp,
            suppression_ambiguity=ambiguity,
        )

    def _derive_suppression_identity(
        self, memory_id: str
    ) -> tuple[str | None, str | None, str | None, str | None]:
        """Derive minimum suppression identity from provenance before deletion.

        Returns ``(source_system, source_entity_kind, fingerprint, ambiguity)``.

        A direct or manually authored memory has no import-origin provenance
        and legitimately carries a NULL source-atom fingerprint. An
        import-origin record must yield exactly one safe deterministic
        identity; anything else is reported as ambiguity so purge fails
        closed rather than erasing a record whose atom could be resurrected.
        """
        imported_rows = (
            self._session.execute(
                select(MemoryProvenance)
                .where(
                    MemoryProvenance.memory_id == memory_id,
                    MemoryProvenance.is_imported.is_(True),
                )
                .order_by(MemoryProvenance.created_at, MemoryProvenance.provenance_id)
            )
            .scalars()
            .all()
        )

        if not imported_rows:
            return (None, None, None, None)

        identities: set[tuple[str, str | None, str]] = set()
        for provenance in imported_rows:
            source_system = (provenance.source_system or "").strip()
            identity = (provenance.source_record_id or "").strip()
            if not source_system or not identity:
                # Import-origin provenance without a stable source entity
                # id. Erasing would guarantee a resurrection we could not
                # suppress afterwards.
                return (
                    None,
                    None,
                    None,
                    "import-origin provenance lacks a stable source identity",
                )
            identities.add(
                (
                    source_system,
                    (provenance.source_subject_kind or None),
                    identity,
                )
            )

        if len(identities) > 1:
            # One canonical record fed by several distinct import atoms
            # cannot be represented by the single source-atom fingerprint a
            # minimal tombstone carries. Refuse rather than suppress one atom
            # and silently leave the others resurrectable.
            return (
                None,
                None,
                None,
                "import-origin record has multiple distinct source atoms",
            )

        source_system, source_entity_kind, identity = identities.pop()
        return (
            source_system,
            source_entity_kind,
            source_atom_fingerprint(
                source_system=source_system,
                source_entity_kind=source_entity_kind,
                source_atom_identity=identity,
            ),
            None,
        )

    def _validate_memory_id(self, memory_id: str) -> None:
        if not isinstance(memory_id, str) or not memory_id.strip():
            raise MemoryPurgeInvalid("memory_id is required")

    def _validate_cas_token(self, expected_updated_at: datetime) -> None:
        if not isinstance(expected_updated_at, datetime):
            raise MemoryPurgeInvalid("expected_updated_at is required")


def _constant_time_equals(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)
