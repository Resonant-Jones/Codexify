"""Memory Vault mutation service (UMS-05C1 / UMS-05C3 / UMS-05C4 / UMS-05C5).

Implements account-owned canonical ``memory_records`` pin/unpin,
hold/release-hold, Project-scope mutation, and stable Persona-attribution
mutation through an explicit ``updated_at`` compare-and-swap token and one
append-only ``memory_provenance`` receipt per actual state change.

It writes only canonical ``pinned``, ``held``, ``project_id``, and
``memory_persona_links`` state. It does not:

- expose an HTTP route;
- mutate content, review, activation, or ``extensions``;
- mutate compatibility projections or Personal Facts;
- mutate Persona subject lifecycle, bindings, profiles, or prompts;
- introduce a revision column or a mutation-receipt table;
- grant retrieval or ambient eligibility;
- implement decay, heat, or ranking.

Receipts are AUDIT / LINEAGE only. Pin authority remains
``memory_records.pinned`` and hold authority remains
``memory_records.held``; the provenance ``extensions`` payload is
non-authoritative evidence. Persona attribution authority remains
``memory_persona_links`` referencing the stable
``persona_subjects.persona_subject_id``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from guardian.core.project_ownership import (
    PROJECT_OWNERSHIP_AUTHORITY_CONFLICT,
    classify_project_ownership,
)
from guardian.db.models import (
    MemoryLifecycleRevision,
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryRecord,
    MemoryReviewRevision,
    MemoryRevision,
    PersonaSubject,
    Project,
)
from guardian.protocol_tokens import (
    MemoryPersonaLinkKind,
    MemorySemanticSpecies,
    PersonaSubjectLifecycle,
)
from guardian.services.memory_vault_read import (
    MemoryVaultReadService,
    VaultIdentity,
    VaultItem,
)

#: Frozen receipt audit labels. These are audit/lineage labels only; they do
#: not grant retrieval or authorization semantics.
ACTION_PIN = "pin"
ACTION_UNPIN = "unpin"
ACTION_HOLD = "hold"
ACTION_RELEASE_HOLD = "release_hold"
ACTION_SET_PROJECT_SCOPE = "set_project_scope"
ACTION_CLEAR_PROJECT_SCOPE = "clear_project_scope"
ACTION_ADD_PERSONA_ATTRIBUTION = "add_persona_attribution"
ACTION_REMOVE_PERSONA_ATTRIBUTION = "remove_persona_attribution"
ACTION_CONTENT_CORRECTION = "content_correction"

#: UMS-05C10A-W / ADR-088. The three admitted direct ordinary-memory review
#: actions. There is deliberately no ``set_pending`` / reset / unreview
#: action: ``pending`` is an ingress state, not a user review outcome.
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_DISPUTE = "dispute"

#: UMS-05C10B-W / ADR-089. Exactly two generic direct lifecycle actions.
#: There is deliberately no ``activate`` / ``set_lifecycle_state``: the
#: runtime action boundary is intentionally narrower than the persistence
#: vocabulary, and ``pending``-style or raw-state targeting is not admitted.
ACTION_RETIRE = "retire"
ACTION_RESTORE = "restore"

#: Canonical ordinary lifecycle vocabulary. A persisted value outside this
#: set is treated as integrity corruption, never repaired.
_LIFECYCLE_STATES: frozenset[str] = frozenset({"active", "dormant", "retired"})

#: Postures a retirement may legally be restored to, per ADR-089.
_RESTORABLE_POSTURES: frozenset[str] = frozenset({"active", "dormant"})

#: Frozen action -> target-state mapping from ADR-088. A caller can never
#: request a raw ``review_state``; it can only request one of these actions.
REVIEW_ACTION_TARGETS: dict[str, str] = {
    ACTION_APPROVE: "approved",
    ACTION_REJECT: "rejected",
    ACTION_DISPUTE: "disputed",
}

#: Canonical ordinary review vocabulary. A persisted ``review_state`` outside
#: this set is treated as integrity corruption, never repaired.
_REVIEW_STATES: frozenset[str] = frozenset(
    {"pending", "approved", "rejected", "disputed"}
)

#: Stable receipt schema marker stored in provenance extensions.
RECEIPT_SCHEMA = "memory-vault-mutation.v1"

#: Canonical provenance vocabulary for the Vault mutation receipt.
SOURCE_SYSTEM_CODEXIFY = "codexify"
SOURCE_SUBJECT_KIND_VAULT = "vault"
MUTATION_SOURCE = "vault"

#: Closed vocabulary of canonical boolean governance fields this service may
#: mutate. Kept explicitly closed; there is no dynamic caller-selected field
#: mutation.
_GOVERNANCE_FIELDS = frozenset({"pinned", "held"})

#: The single canonical semantic species the generic content-correction
#: writer may mutate. Personal Fact species remain specialized and are
#: owned by ``personal_fact_revisions`` plus the Personal Facts service.
_CORRECTABLE_SPECIES = MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value

#: Closed vocabulary of canonical Persona-link token values. Mirrors
#: ``MemoryPersonaLinkKind`` for internal normalization; the canonical enum
#: is the protocol authority for accepted values.
_PERSONA_LINK_KIND_VALUES = frozenset({kind.value for kind in MemoryPersonaLinkKind})


class MemoryVaultMutationError(Exception):
    """Fail-closed error for Vault mutation integrity defects."""


class MemoryVaultMutationNotAvailable(MemoryVaultMutationError):
    """The requested canonical memory is not available to this account.

    Missing and cross-account share this same posture; the service never
    reveals record existence to a non-owner.
    """


class MemoryVaultMutationConflict(MemoryVaultMutationError):
    """The supplied ``expected_updated_at`` token is stale."""


class MemoryVaultProjectNotAvailable(MemoryVaultMutationError):
    """The requested Project is missing or belongs to another account."""


class MemoryVaultProjectAuthorityConflict(MemoryVaultMutationError):
    """A canonical Project carries conflicting ADR-081 compatibility data."""

    code = PROJECT_OWNERSHIP_AUTHORITY_CONFLICT


class MemoryVaultPersonaSubjectNotAvailable(MemoryVaultMutationError):
    """The requested Persona subject is missing or belongs to another account.

    Missing and foreign-account share this same posture; the service never
    reveals subject existence to a non-owner.
    """


class MemoryVaultPersonaSubjectLifecycleConflict(MemoryVaultMutationError):
    """A NEW Persona attribution was requested against a non-active subject.

    Existing exact link persistence against a retired subject remains a
    fresh-token no-op; this conflict is reserved for new-attribution
    attempts against retired subjects.
    """


class MemoryVaultContentCorrectionInvalid(MemoryVaultMutationError):
    """Authored content is missing, non-string, or whitespace-only.

    This is ordinary request validation rather than an integrity failure,
    so the HTTP layer maps it to 422 instead of the sanitized 409 family.
    """


class MemoryVaultContentCorrectionUnsupported(MemoryVaultMutationError):
    """The target canonical memory is not writable by the generic writer.

    Raised when the target is a specialized Personal Fact species. The
    generic Vault writer does not own Personal Facts content; that
    authority remains ``personal_fact_revisions`` plus the Personal Facts
    service. The HTTP layer maps this to the same sanitized 409 family as
    other integrity failures so no species detail leaks.
    """


class MemoryVaultContentCorrectionIntegrityError(MemoryVaultMutationError):
    """Existing revision history is not consistent with canonical content.

    Raised when the existing ``memory_revisions`` tail for the target
    memory is gapped or diverges from current canonical
    ``memory_records.text_content``. The writer refuses to append onto
    malformed history and never repairs it.
    """


@dataclass(frozen=True)
class VaultMutationResult:
    """Outcome of one Vault governance mutation attempt."""

    changed: bool
    receipt_id: str | None
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItem


@dataclass(frozen=True)
class VaultContentCorrectionResult:
    """Outcome of one direct ordinary-memory content correction.

    Extends the shared Vault mutation result with the canonical revision
    identity created by a changed correction. For an exact no-op both
    ``receipt_id`` and ``revision_id`` are ``None`` and
    ``revision_number`` is ``None``: no revision and no receipt are
    created when content did not change.
    """

    changed: bool
    receipt_id: str | None
    revision_id: str | None
    revision_number: int | None
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItem


class MemoryVaultReviewTransitionInvalid(MemoryVaultMutationError):
    """The requested review action is not one of ADR-088's admitted actions."""


class MemoryVaultReviewTransitionUnsupported(MemoryVaultMutationError):
    """The canonical memory is not writable by the generic review writer."""


class MemoryVaultReviewTransitionIntegrityError(MemoryVaultMutationError):
    """Existing review history or persisted review state is not trustworthy."""


class MemoryVaultLifecycleInvalid(MemoryVaultMutationError):
    """The requested lifecycle action is not one of ADR-089's two actions."""


class MemoryVaultLifecycleUnsupported(MemoryVaultMutationError):
    """The canonical memory is not writable by the generic lifecycle writer."""


class MemoryVaultLifecycleIntegrityError(MemoryVaultMutationError):
    """Lifecycle history or persisted state cannot justify the mutation.

    Raised when a restore would otherwise have to guess the pre-retirement
    posture, and when existing history is not safe to append onto.
    """


@dataclass(slots=True)
class VaultLifecycleTransitionResult:
    """Outcome of one direct ordinary-memory lifecycle transition.

    For an ADR-089 same-state no-op, ``changed`` is ``False`` and
    ``receipt_id`` / ``lifecycle_revision_id`` / ``lifecycle_revision_number``
    are ``None``: no lifecycle revision, no receipt, and no CAS advance occur
    when the requested action would not change the current lifecycle state.
    """

    changed: bool
    action: str
    receipt_id: str | None
    lifecycle_revision_id: str | None
    lifecycle_revision_number: int | None
    previous_lifecycle_state: str
    resulting_lifecycle_state: str
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItem


@dataclass(slots=True)
class VaultReviewTransitionResult:
    """Outcome of one direct ordinary-memory review transition (UMS-05C10A-W).

    For an ADR-088 same-state no-op, ``changed`` is ``False`` and
    ``receipt_id`` / ``review_revision_id`` / ``review_revision_number`` are
    ``None``: no review revision, no receipt, and no CAS advance occur when
    the requested action would not change the current review state.
    """

    changed: bool
    action: str
    receipt_id: str | None
    review_revision_id: str | None
    review_revision_number: int | None
    previous_review_state: str
    resulting_review_state: str
    previous_updated_at: datetime
    resulting_updated_at: datetime
    item: VaultItem


class MemoryVaultMutationService:
    """Internal account-owned canonical Memory Vault mutation service.

    The authenticated account identity is constructor-supplied and
    immutable; there is no per-call actor/account override.
    """

    def __init__(
        self,
        session: Session,
        *,
        authenticated_account_id: str,
    ) -> None:
        if session is None:
            raise MemoryVaultMutationError("session is required")
        if not authenticated_account_id or not isinstance(
            authenticated_account_id, str
        ):
            raise MemoryVaultMutationError(
                "authenticated_account_id is required and must be a non-empty string"
            )
        self._session = session
        self._account = authenticated_account_id

    # -- Public API --------------------------------------------------------

    def set_pinned(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        pinned: bool,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        """Set canonical pin state with an explicit stale-write CAS token."""
        return self._set_boolean_governance_state(
            memory_id=memory_id,
            expected_updated_at=expected_updated_at,
            desired=bool(pinned),
            field_name="pinned",
            true_action=ACTION_PIN,
            false_action=ACTION_UNPIN,
            reason=reason,
            request_ref=request_ref,
        )

    def set_held(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        held: bool,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        """Set canonical hold state with an explicit stale-write CAS token.

        Holding suspends decay only; this mutation performs no decay, heat,
        ranking, retrieval, or ambient-eligibility work.
        """
        return self._set_boolean_governance_state(
            memory_id=memory_id,
            expected_updated_at=expected_updated_at,
            desired=bool(held),
            field_name="held",
            true_action=ACTION_HOLD,
            false_action=ACTION_RELEASE_HOLD,
            reason=reason,
            request_ref=request_ref,
        )

    def set_project_scope(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        project_id: int | None,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        """Set or clear canonical Project scope through the record CAS.

        ``projects.user_id`` is the only ownership authority. Legacy owner
        envelopes are inspected only to fail closed on ADR-081 conflicts.
        The operation never creates, edits, repairs, archives, or otherwise
        mutates a Project.
        """
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)
        self._validate_project_id(project_id)

        row = self._load_authorized_memory(memory_id)
        self._require_fresh_token(row, expected_updated_at)

        previous_project_id = row.project_id
        previous_updated_at = row.updated_at
        current_project = self._load_current_project(previous_project_id)
        if current_project is not None:
            self._require_conflict_free_project(current_project)

        if project_id is not None and project_id != previous_project_id:
            target_project = self._load_available_project(project_id)
            self._require_conflict_free_project(target_project)

        if previous_project_id == project_id:
            item = self._readback(memory_id)
            self._session.rollback()
            return VaultMutationResult(
                changed=False,
                receipt_id=None,
                previous_updated_at=previous_updated_at,
                resulting_updated_at=previous_updated_at,
                item=item,
            )

        try:
            new_token = self._session.execute(
                update(MemoryRecord)
                .where(
                    MemoryRecord.memory_id == memory_id,
                    MemoryRecord.user_id == self._account,
                    MemoryRecord.updated_at == expected_updated_at,
                )
                .values(
                    project_id=project_id,
                    updated_at=func.clock_timestamp(),
                )
                .returning(MemoryRecord.updated_at)
            ).scalar_one()
        except NoResultFound as exc:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            ) from exc
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError("memory mutation failed") from exc

        receipt = self._build_receipt(
            memory_id=memory_id,
            action=(
                ACTION_SET_PROJECT_SCOPE
                if project_id is not None
                else ACTION_CLEAR_PROJECT_SCOPE
            ),
            field_name="project_id",
            previous_value=previous_project_id,
            new_value=project_id,
            expected_updated_at=expected_updated_at,
            resulting_updated_at=new_token,
            reason=reason,
            request_ref=request_ref,
        )
        self._session.add(receipt)

        try:
            self._session.flush()
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError(
                "memory mutation transaction failed"
            ) from exc

        self._session.commit()

        item = self._readback(memory_id)
        if item.project_id != project_id:
            raise MemoryVaultMutationError("canonical readback mismatch after mutation")
        if item.updated_at != new_token:
            raise MemoryVaultMutationError(
                "canonical readback timestamp mismatch after mutation"
            )

        return VaultMutationResult(
            changed=True,
            receipt_id=receipt.provenance_id,
            previous_updated_at=previous_updated_at,
            resulting_updated_at=new_token,
            item=item,
        )

    def set_persona_attribution(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        persona_subject_id: str,
        link_kind: MemoryPersonaLinkKind | str,
        present: bool,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultMutationResult:
        """Set or remove one exact stable-Persona attribution link.

        ``persona_subjects.persona_subject_id`` is the attribution target;
        ``MemoryPersonaLinkKind`` is the link-kind token authority. The
        mutation is desired-state, not command-style: ``present=True`` asserts
        the exact link must exist, ``present=False`` asserts it must not.

        - PersonaProfile identity, display names, and prompts are not
          attribution authority.
        - Same-account subject is enforced by direct subject lookup;
          missing and foreign-account subjects share one unavailable posture.
        - For ``present=True`` with no existing exact link, the subject
          lifecycle must equal ``active``; ``retired`` fails closed.
        - For ``present=True`` with an existing exact link, the operation is
          a fresh-token no-op (retirement does not silently prune links).
        - For ``present=False``, an existing exact link may be removed
          whether the subject is ``active`` or ``retired``.
        - Subject lifecycle and bindings are never mutated; the
          ``memory_records.updated_at`` CAS is advanced atomically with the
          child-link insert/delete plus the canonical provenance receipt.
        """
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)
        self._validate_persona_subject_id(persona_subject_id)
        canonical_link_kind = self._normalize_link_kind(link_kind)

        row = self._load_authorized_memory(memory_id)
        self._require_fresh_token(row, expected_updated_at)

        previous_updated_at = row.updated_at

        subject = self._load_available_persona_subject(persona_subject_id)
        existing_link = self._find_existing_persona_link(
            memory_id=memory_id,
            persona_subject_id=persona_subject_id,
            link_kind=canonical_link_kind,
        )
        current_present = existing_link is not None

        if current_present == present:
            item = self._readback(memory_id)
            self._session.rollback()
            return VaultMutationResult(
                changed=False,
                receipt_id=None,
                previous_updated_at=previous_updated_at,
                resulting_updated_at=previous_updated_at,
                item=item,
            )

        if present and subject.lifecycle != PersonaSubjectLifecycle.ACTIVE.value:
            self._session.rollback()
            raise MemoryVaultPersonaSubjectLifecycleConflict(
                "Persona subject is not active for new attribution."
            )

        try:
            new_token = self._session.execute(
                update(MemoryRecord)
                .where(
                    MemoryRecord.memory_id == memory_id,
                    MemoryRecord.user_id == self._account,
                    MemoryRecord.updated_at == expected_updated_at,
                )
                .values(updated_at=func.clock_timestamp())
                .returning(MemoryRecord.updated_at)
            ).scalar_one()
        except NoResultFound as exc:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            ) from exc
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError("memory mutation failed") from exc

        if present:
            link_id = str(uuid.uuid4())
            self._session.add(
                MemoryPersonaLink(
                    link_id=link_id,
                    memory_id=memory_id,
                    user_id=self._account,
                    persona_subject_id=persona_subject_id,
                    persona_user_id=self._account,
                    link_kind=canonical_link_kind,
                )
            )
            previous_value: dict | None = None
            new_value: dict | None = {
                "link_id": link_id,
                "persona_subject_id": persona_subject_id,
                "link_kind": canonical_link_kind,
            }
            action = ACTION_ADD_PERSONA_ATTRIBUTION
            assert existing_link is None
        else:
            assert existing_link is not None
            self._session.delete(existing_link)
            previous_value = {
                "link_id": existing_link.link_id,
                "persona_subject_id": existing_link.persona_subject_id,
                "link_kind": existing_link.link_kind,
            }
            new_value = None
            action = ACTION_REMOVE_PERSONA_ATTRIBUTION

        receipt = self._build_receipt(
            memory_id=memory_id,
            action=action,
            field_name="persona_attribution",
            previous_value=previous_value,
            new_value=new_value,
            expected_updated_at=expected_updated_at,
            resulting_updated_at=new_token,
            reason=reason,
            request_ref=request_ref,
        )
        self._session.add(receipt)

        try:
            self._session.flush()
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError(
                "memory mutation transaction failed"
            ) from exc

        self._session.commit()

        item = self._readback(memory_id)
        resulting_present = any(
            link.persona_subject_id == persona_subject_id
            and link.link_kind == canonical_link_kind
            for link in item.persona_links
        )
        if present != resulting_present:
            raise MemoryVaultMutationError(
                "canonical readback Persona-link mismatch after mutation"
            )
        if item.updated_at != new_token:
            raise MemoryVaultMutationError(
                "canonical readback timestamp mismatch after mutation"
            )

        return VaultMutationResult(
            changed=True,
            receipt_id=receipt.provenance_id,
            previous_updated_at=previous_updated_at,
            resulting_updated_at=new_token,
            item=item,
        )

    # -- Shared mutation spine --------------------------------------------

    def _set_boolean_governance_state(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        desired: bool,
        field_name: str,
        true_action: str,
        false_action: str,
        reason: str | None,
        request_ref: str | None,
    ) -> VaultMutationResult:
        """Run one CAS-guarded canonical boolean governance mutation.

        A changed mutation is one PostgreSQL transaction: authorize the
        account-owned canonical row, compare ``expected_updated_at``, flip
        the bounded governance field, advance the database-authored
        ``updated_at``, append one Vault provenance receipt, then commit and
        read back through the B1 read service. A no-op (same state, fresh
        token) returns ``changed=False`` with no write. A stale token fails
        closed with no write and no receipt.
        """
        if field_name not in _GOVERNANCE_FIELDS:
            raise MemoryVaultMutationError(
                f"unsupported governance field: {field_name!r}"
            )
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)

        row = self._load_authorized_memory(memory_id)
        self._require_fresh_token(row, expected_updated_at)

        previous_value = bool(getattr(row, field_name))
        previous_updated_at = row.updated_at

        if previous_value == desired:
            item = self._readback(memory_id)
            self._session.rollback()
            return VaultMutationResult(
                changed=False,
                receipt_id=None,
                previous_updated_at=previous_updated_at,
                resulting_updated_at=previous_updated_at,
                item=item,
            )

        try:
            new_token = self._session.execute(
                update(MemoryRecord)
                .where(
                    MemoryRecord.memory_id == memory_id,
                    MemoryRecord.user_id == self._account,
                    MemoryRecord.updated_at == expected_updated_at,
                )
                .values(
                    **{field_name: desired},
                    updated_at=func.clock_timestamp(),
                )
                .returning(MemoryRecord.updated_at)
            ).scalar_one()
        except NoResultFound as exc:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            ) from exc
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError("memory mutation failed") from exc

        receipt = self._build_receipt(
            memory_id=memory_id,
            action=true_action if desired else false_action,
            field_name=field_name,
            previous_value=previous_value,
            new_value=desired,
            expected_updated_at=expected_updated_at,
            resulting_updated_at=new_token,
            reason=reason,
            request_ref=request_ref,
        )
        self._session.add(receipt)

        try:
            self._session.flush()
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError(
                "memory mutation transaction failed"
            ) from exc

        self._session.commit()

        item = self._readback(memory_id)
        if bool(getattr(item, field_name)) != desired:
            raise MemoryVaultMutationError("canonical readback mismatch after mutation")
        if item.updated_at != new_token:
            raise MemoryVaultMutationError(
                "canonical readback timestamp mismatch after mutation"
            )

        return VaultMutationResult(
            changed=True,
            receipt_id=receipt.provenance_id,
            previous_updated_at=previous_updated_at,
            resulting_updated_at=new_token,
            item=item,
        )

    def correct_content(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        content: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultContentCorrectionResult:
        """Correct the canonical text of one ordinary memory (UMS-05C9-W).

        A changed correction atomically produces all of:

        1. the new canonical ``memory_records.text_content``;
        2. exactly one append-only ``memory_revisions`` row preserving the
           exact prior and resulting text;
        3. exactly one ``memory-vault-mutation.v1`` receipt that references
           the created revision without duplicating authored content;
        4. one new database-authored ``memory_records.updated_at`` token.

        An exact no-op (requested text identical to current canonical text,
        with a fresh CAS token) creates neither a revision nor a receipt and
        does not advance the CAS. A stale token conflicts even when the
        requested text happens to equal current text.

        Only canonical ordinary ``episodic_semantic_memory`` is writable
        here. Personal Facts remain specialized and are never corrected
        through this generic writer.
        """
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)
        validated_content = self._validate_authored_content(content)

        row = self._load_authorized_memory(memory_id)
        self._require_fresh_token(row, expected_updated_at)

        if row.semantic_species != _CORRECTABLE_SPECIES:
            self._session.rollback()
            raise MemoryVaultContentCorrectionUnsupported(
                "canonical memory is not writable by the generic content writer"
            )

        previous_updated_at = row.updated_at
        previous_text = row.text_content

        if previous_text == validated_content:
            # Exact no-op. Stale tokens already conflicted above, so this
            # branch is only reachable with a genuinely fresh token.
            item = self._readback(memory_id)
            self._session.rollback()
            return VaultContentCorrectionResult(
                changed=False,
                receipt_id=None,
                revision_id=None,
                revision_number=None,
                previous_updated_at=previous_updated_at,
                resulting_updated_at=previous_updated_at,
                item=item,
            )

        next_revision_number = self._next_revision_number(
            memory_id=memory_id,
            current_text=previous_text,
        )

        try:
            new_token = self._session.execute(
                update(MemoryRecord)
                .where(
                    MemoryRecord.memory_id == memory_id,
                    MemoryRecord.user_id == self._account,
                    MemoryRecord.updated_at == expected_updated_at,
                )
                .values(
                    text_content=validated_content,
                    updated_at=func.clock_timestamp(),
                )
                .returning(MemoryRecord.updated_at)
            ).scalar_one()
        except NoResultFound as exc:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            ) from exc
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError("memory mutation failed") from exc

        revision = MemoryRevision(
            revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=self._account,
            revision_number=next_revision_number,
            old_text_content=previous_text,
            new_text_content=validated_content,
        )
        self._session.add(revision)

        try:
            self._session.flush()
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultContentCorrectionIntegrityError(
                "memory content correction transaction failed"
            ) from exc

        # The receipt is audit evidence only. It references the created
        # revision and never duplicates authored old/new text.
        receipt = self._build_receipt(
            memory_id=memory_id,
            action=ACTION_CONTENT_CORRECTION,
            field_name="revision_number",
            previous_value=next_revision_number - 1,
            new_value=next_revision_number,
            expected_updated_at=expected_updated_at,
            resulting_updated_at=new_token,
            reason=reason,
            request_ref=request_ref,
        )
        receipt.extensions = {
            **dict(receipt.extensions or {}),
            "revision_id": revision.revision_id,
            "new_values": {
                "revision_id": revision.revision_id,
                "revision_number": revision.revision_number,
                "content_changed": True,
            },
        }
        self._session.add(receipt)

        try:
            self._session.flush()
        except Exception as exc:
            self._session.rollback()
            raise MemoryVaultMutationError(
                "memory mutation transaction failed"
            ) from exc

        self._session.commit()

        item = self._readback(memory_id)
        if item.content != validated_content:
            raise MemoryVaultMutationError("canonical readback mismatch after mutation")
        if item.updated_at != new_token:
            raise MemoryVaultMutationError(
                "canonical readback timestamp mismatch after mutation"
            )

        return VaultContentCorrectionResult(
            changed=True,
            receipt_id=receipt.provenance_id,
            revision_id=revision.revision_id,
            revision_number=revision.revision_number,
            previous_updated_at=previous_updated_at,
            resulting_updated_at=new_token,
            item=item,
        )

    def transition_lifecycle(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        action: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultLifecycleTransitionResult:
        """Apply one ADR-089 direct lifecycle transition to ordinary memory.

        A changed transition atomically produces all of:

        1. the new canonical ``memory_records.lifecycle_state``;
        2. exactly one append-only ``memory_lifecycle_revisions`` row;
        3. exactly one ``memory-vault-mutation.v1`` intent receipt; and
        4. one new database-authored ``memory_records.updated_at`` CAS token.

        Restore is **not** "set active". It recovers the immediately
        pre-retirement governed posture from canonical lifecycle history, so a
        record retired from ``active`` and one retired from ``dormant`` stay
        distinct. A retired record whose pre-retirement posture cannot be
        proven from history fails closed rather than guessing.

        A same-state action under a fresh CAS token is a semantic no-op: it
        creates neither a lifecycle revision nor a receipt and does not
        advance the CAS. A stale token conflicts even when the action would
        otherwise be a no-op — CAS is validated before the no-op decision.
        """
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)
        normalized_action = self._validate_lifecycle_action(action)

        row = self._load_authorized_memory(memory_id)
        # CAS authority is established before any no-op determination.
        self._require_fresh_token(row, expected_updated_at)

        if row.semantic_species != _CORRECTABLE_SPECIES:
            self._session.rollback()
            raise MemoryVaultLifecycleUnsupported(
                "canonical memory is not writable by the generic lifecycle writer"
            )

        current_state = str(row.lifecycle_state or "")
        if current_state not in _LIFECYCLE_STATES:
            self._session.rollback()
            raise MemoryVaultLifecycleIntegrityError(
                "persisted lifecycle state is outside the canonical vocabulary"
            )

        previous_updated_at = row.updated_at
        target_state = self._resolve_lifecycle_target(
            memory_id=memory_id,
            current_state=current_state,
            action=normalized_action,
        )

        if target_state == current_state:
            # ADR-089 same-state no-op. Reachable only with a fresh token,
            # because the stale check above already conflicted.
            item = self._readback(memory_id)
            self._session.rollback()
            return VaultLifecycleTransitionResult(
                changed=False,
                action=normalized_action,
                receipt_id=None,
                lifecycle_revision_id=None,
                lifecycle_revision_number=None,
                previous_lifecycle_state=current_state,
                resulting_lifecycle_state=current_state,
                previous_updated_at=previous_updated_at,
                resulting_updated_at=previous_updated_at,
                item=item,
            )

        next_revision_number = self._next_lifecycle_revision_number(
            memory_id=memory_id,
            current_state=current_state,
        )

        try:
            new_token = self._session.execute(
                update(MemoryRecord)
                .where(
                    MemoryRecord.memory_id == memory_id,
                    MemoryRecord.user_id == self._account,
                    MemoryRecord.updated_at == expected_updated_at,
                )
                .values(
                    lifecycle_state=target_state,
                    updated_at=func.clock_timestamp(),
                )
                .returning(MemoryRecord.updated_at)
            ).scalar_one()
        except NoResultFound as exc:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultMutationError("memory mutation failed") from exc

        lifecycle_revision = MemoryLifecycleRevision(
            lifecycle_revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=self._account,
            revision_number=next_revision_number,
            old_lifecycle_state=current_state,
            new_lifecycle_state=target_state,
        )
        self._session.add(lifecycle_revision)

        try:
            self._session.flush()
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultLifecycleIntegrityError(
                "memory lifecycle transition transaction failed"
            ) from exc

        # The receipt is intent/audit evidence only. It references the created
        # lifecycle revision and never duplicates canonical history.
        receipt = self._build_receipt(
            memory_id=memory_id,
            action=normalized_action,
            field_name="lifecycle_state",
            previous_value=current_state,
            new_value=target_state,
            expected_updated_at=expected_updated_at,
            resulting_updated_at=new_token,
            reason=reason,
            request_ref=request_ref,
        )
        receipt.extensions = {
            **dict(receipt.extensions or {}),
            "lifecycle_revision_id": lifecycle_revision.lifecycle_revision_id,
            "new_values": {
                "lifecycle_state": target_state,
                "lifecycle_revision_id": (lifecycle_revision.lifecycle_revision_id),
                "lifecycle_revision_number": lifecycle_revision.revision_number,
            },
        }
        self._session.add(receipt)

        try:
            self._session.flush()
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultMutationError(
                "memory mutation transaction failed"
            ) from exc

        self._session.commit()

        item = self._readback(memory_id)
        # ``lifecycle_posture`` is the canonical read projection of
        # ``memory_records.lifecycle_state``.
        if item.lifecycle_posture != target_state:
            raise MemoryVaultMutationError(
                "canonical readback mismatch after lifecycle transition"
            )
        if item.updated_at != new_token:
            raise MemoryVaultMutationError(
                "canonical readback timestamp mismatch after lifecycle transition"
            )

        return VaultLifecycleTransitionResult(
            changed=True,
            action=normalized_action,
            receipt_id=receipt.provenance_id,
            lifecycle_revision_id=lifecycle_revision.lifecycle_revision_id,
            lifecycle_revision_number=lifecycle_revision.revision_number,
            previous_lifecycle_state=current_state,
            resulting_lifecycle_state=target_state,
            previous_updated_at=previous_updated_at,
            resulting_updated_at=new_token,
            item=item,
        )

    @staticmethod
    def _validate_lifecycle_action(action: object) -> str:
        """Accept only ADR-089's two admitted direct lifecycle actions."""
        if not isinstance(action, str):
            raise MemoryVaultLifecycleInvalid("lifecycle action must be a string")
        normalized = action.strip()
        if normalized not in (ACTION_RETIRE, ACTION_RESTORE):
            raise MemoryVaultLifecycleInvalid(
                "lifecycle action must be retire or restore"
            )
        return normalized

    def _resolve_lifecycle_target(
        self,
        *,
        memory_id: str,
        current_state: str,
        action: str,
    ) -> str:
        """Return the target lifecycle state for this action.

        Same-state outcomes return ``current_state`` and become no-ops. A
        changed restore derives its target **only** from the canonical
        lifecycle-history tail; it never defaults to ``active`` or ``dormant``.
        """
        if action == ACTION_RETIRE:
            if current_state == "retired":
                return current_state
            return "retired"

        # restore
        if current_state != "retired":
            # Already satisfied: active / dormant need no restoration.
            return current_state

        tail = self._lifecycle_history_tail(memory_id=memory_id)
        if tail is None:
            # A legacy/current retired record with no reconstructable history.
            # ADR-089 requires failing closed rather than guessing.
            self._session.rollback()
            raise MemoryVaultLifecycleIntegrityError(
                "restore requires canonical pre-retirement lifecycle history"
            )
        old_state = str(tail.old_lifecycle_state or "")
        if (
            tail.new_lifecycle_state != "retired"
            or old_state not in _RESTORABLE_POSTURES
        ):
            self._session.rollback()
            raise MemoryVaultLifecycleIntegrityError(
                "lifecycle history tail does not prove a restorable retirement"
            )
        return old_state

    def _lifecycle_history_tail(self, *, memory_id: str):
        """Return the newest canonical lifecycle revision, or None.

        The parent mutation transaction holds the row lock for the whole call,
        so the tail cannot change underneath this read.
        """
        return self._session.execute(
            select(MemoryLifecycleRevision)
            .where(
                MemoryLifecycleRevision.memory_id == memory_id,
                MemoryLifecycleRevision.user_id == self._account,
            )
            .order_by(MemoryLifecycleRevision.revision_number.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _next_lifecycle_revision_number(
        self,
        *,
        memory_id: str,
        current_state: str,
    ) -> int:
        """Return the next contiguous lifecycle revision number.

        Fails closed when existing history is gapped, when its chain is
        broken, or when its tail does not reconcile with the parent's current
        lifecycle state. Malformed history is never renumbered, repaired, or
        reconstructed from provenance extensions.
        """
        rows = (
            self._session.execute(
                select(MemoryLifecycleRevision)
                .where(
                    MemoryLifecycleRevision.memory_id == memory_id,
                    MemoryLifecycleRevision.user_id == self._account,
                )
                .order_by(MemoryLifecycleRevision.revision_number.asc())
            )
            .scalars()
            .all()
        )
        if not rows:
            # Zero prior history is valid for a first retirement: there is no
            # posture to reconstruct because nothing is being restored.
            return 1
        numbers = [r.revision_number for r in rows]
        if numbers != list(range(1, len(numbers) + 1)):
            self._session.rollback()
            raise MemoryVaultLifecycleIntegrityError(
                "existing memory lifecycle history is not contiguous"
            )
        for previous, following in zip(rows, rows[1:]):
            if previous.new_lifecycle_state != following.old_lifecycle_state:
                self._session.rollback()
                raise MemoryVaultLifecycleIntegrityError(
                    "existing memory lifecycle history chain is broken"
                )
        latest = rows[-1]
        if latest.new_lifecycle_state != current_state:
            self._session.rollback()
            raise MemoryVaultLifecycleIntegrityError(
                "existing memory lifecycle history tail diverges from canonical "
                "lifecycle state"
            )
        return latest.revision_number + 1

    def transition_review(
        self,
        *,
        memory_id: str,
        expected_updated_at: datetime,
        action: str,
        reason: str | None = None,
        request_ref: str | None = None,
    ) -> VaultReviewTransitionResult:
        """Apply one ADR-088 direct review transition to ordinary memory.

        A changed transition atomically produces all of:

        1. the new canonical ``memory_records.review_state``;
        2. ``reviewed_at`` set only on first authoritative approval;
        3. exactly one append-only ``memory_review_revisions`` row;
        4. exactly one ``memory-vault-mutation.v1`` intent receipt; and
        5. one new database-authored ``memory_records.updated_at`` CAS token.

        Any failure rolls all of them back.

        A same-state action under a fresh CAS token is a semantic no-op: it
        creates neither a review revision nor a receipt and does not advance
        the CAS. A stale token conflicts even when the action would otherwise
        be a no-op — CAS is validated before the no-op decision.

        ``action`` must be one of ``approve``, ``reject``, or ``dispute``.
        There is no path that targets ``pending``: ADR-088 defines
        ``pending`` as an ingress state, not a user review outcome.
        """
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)
        normalized_action = self._validate_review_action(action)

        row = self._load_authorized_memory(memory_id)
        # CAS authority is established before any no-op determination.
        self._require_fresh_token(row, expected_updated_at)

        if row.semantic_species != _CORRECTABLE_SPECIES:
            self._session.rollback()
            raise MemoryVaultReviewTransitionUnsupported(
                "canonical memory is not writable by the generic review writer"
            )

        current_state = str(row.review_state or "")
        if current_state not in _REVIEW_STATES:
            self._session.rollback()
            raise MemoryVaultReviewTransitionIntegrityError(
                "persisted review state is outside the canonical vocabulary"
            )

        target_state = REVIEW_ACTION_TARGETS[normalized_action]
        previous_updated_at = row.updated_at

        if current_state == target_state:
            # ADR-088 same-state no-op. Reachable only with a fresh token,
            # because the stale check above already conflicted.
            item = self._readback(memory_id)
            self._session.rollback()
            return VaultReviewTransitionResult(
                changed=False,
                action=normalized_action,
                receipt_id=None,
                review_revision_id=None,
                review_revision_number=None,
                previous_review_state=current_state,
                resulting_review_state=current_state,
                previous_updated_at=previous_updated_at,
                resulting_updated_at=previous_updated_at,
                item=item,
            )

        next_revision_number = self._next_review_revision_number(
            memory_id=memory_id,
            current_state=current_state,
        )

        # ADR-088: reviewed_at is the timestamp of FIRST authoritative
        # approval. First approval sets it; re-approval preserves it;
        # rejection and dispute never clear or rewrite it.
        reviewed_at_value: object = MemoryRecord.reviewed_at
        if target_state == "approved" and row.reviewed_at is None:
            reviewed_at_value = func.clock_timestamp()

        try:
            new_token = self._session.execute(
                update(MemoryRecord)
                .where(
                    MemoryRecord.memory_id == memory_id,
                    MemoryRecord.user_id == self._account,
                    MemoryRecord.updated_at == expected_updated_at,
                )
                .values(
                    review_state=target_state,
                    reviewed_at=reviewed_at_value,
                    updated_at=func.clock_timestamp(),
                )
                .returning(MemoryRecord.updated_at)
            ).scalar_one()
        except NoResultFound as exc:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultMutationError("memory mutation failed") from exc

        review_revision = MemoryReviewRevision(
            review_revision_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=self._account,
            revision_number=next_revision_number,
            old_review_state=current_state,
            new_review_state=target_state,
            actor_account_id=self._account,
        )
        self._session.add(review_revision)

        try:
            self._session.flush()
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultReviewTransitionIntegrityError(
                "memory review transition transaction failed"
            ) from exc

        # The receipt is intent/audit evidence only. It references the created
        # review revision and never duplicates canonical review history.
        receipt = self._build_receipt(
            memory_id=memory_id,
            action=normalized_action,
            field_name="review_state",
            previous_value=current_state,
            new_value=target_state,
            expected_updated_at=expected_updated_at,
            resulting_updated_at=new_token,
            reason=reason,
            request_ref=request_ref,
        )
        receipt.extensions = {
            **dict(receipt.extensions or {}),
            "review_revision_id": review_revision.review_revision_id,
            "new_values": {
                "review_state": target_state,
                "review_revision_id": review_revision.review_revision_id,
                "review_revision_number": review_revision.revision_number,
            },
        }
        self._session.add(receipt)

        try:
            self._session.flush()
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultMutationError(
                "memory mutation transaction failed"
            ) from exc

        self._session.commit()

        item = self._readback(memory_id)
        # ``review_posture`` is the canonical read projection of
        # ``memory_records.review_state``.
        if item.review_posture != target_state:
            raise MemoryVaultMutationError(
                "canonical readback mismatch after review transition"
            )
        if item.updated_at != new_token:
            raise MemoryVaultMutationError(
                "canonical readback timestamp mismatch after review transition"
            )

        return VaultReviewTransitionResult(
            changed=True,
            action=normalized_action,
            receipt_id=receipt.provenance_id,
            review_revision_id=review_revision.review_revision_id,
            review_revision_number=review_revision.revision_number,
            previous_review_state=current_state,
            resulting_review_state=target_state,
            previous_updated_at=previous_updated_at,
            resulting_updated_at=new_token,
            item=item,
        )

    @staticmethod
    def _validate_review_action(action: object) -> str:
        """Accept only ADR-088's three admitted direct review actions."""
        if not isinstance(action, str):
            raise MemoryVaultReviewTransitionInvalid("review action must be a string")
        normalized = action.strip()
        if normalized not in REVIEW_ACTION_TARGETS:
            raise MemoryVaultReviewTransitionInvalid(
                "review action must be approve, reject, or dispute"
            )
        return normalized

    def _next_review_revision_number(
        self,
        *,
        memory_id: str,
        current_state: str,
    ) -> int:
        """Return the next contiguous review revision number.

        Fails closed when existing review history is gapped or when its tail
        no longer reconciles with the parent's current ``review_state``.
        Malformed history is never renumbered, repaired, or reconstructed
        from provenance extensions.
        """
        rows = (
            self._session.execute(
                select(MemoryReviewRevision)
                .where(
                    MemoryReviewRevision.memory_id == memory_id,
                    MemoryReviewRevision.user_id == self._account,
                )
                .order_by(MemoryReviewRevision.revision_number.asc())
            )
            .scalars()
            .all()
        )
        if not rows:
            return 1
        numbers = [r.revision_number for r in rows]
        if numbers != list(range(1, len(numbers) + 1)):
            self._session.rollback()
            raise MemoryVaultReviewTransitionIntegrityError(
                "existing memory review history is not contiguous"
            )
        latest = rows[-1]
        if latest.new_review_state != current_state:
            self._session.rollback()
            raise MemoryVaultReviewTransitionIntegrityError(
                "existing memory review history tail diverges from canonical "
                "review state"
            )
        return latest.revision_number + 1

    def _next_revision_number(
        self,
        *,
        memory_id: str,
        current_text: str | None,
    ) -> int:
        """Return the next contiguous revision number after validating the tail.

        Fails closed when existing history is gapped or when its tail no
        longer reconciles with current canonical content. Malformed
        history is never repaired here.
        """
        rows = (
            self._session.execute(
                select(MemoryRevision)
                .where(
                    MemoryRevision.memory_id == memory_id,
                    MemoryRevision.user_id == self._account,
                )
                .order_by(MemoryRevision.revision_number.asc())
            )
            .scalars()
            .all()
        )
        if not rows:
            return 1
        numbers = [r.revision_number for r in rows]
        if numbers != list(range(1, len(numbers) + 1)):
            self._session.rollback()
            raise MemoryVaultContentCorrectionIntegrityError(
                "existing memory revision history is not contiguous"
            )
        latest = rows[-1]
        if latest.new_text_content != current_text:
            self._session.rollback()
            raise MemoryVaultContentCorrectionIntegrityError(
                "existing memory revision tail diverges from canonical content"
            )
        return latest.revision_number + 1

    @staticmethod
    def _validate_authored_content(value: object) -> str:
        """Validate authored text and return it unchanged.

        Blankness is judged on the stripped form, but the original
        unstripped string is what gets persisted so exact whitespace,
        line breaks, Unicode, punctuation, and casing survive.
        """
        if not isinstance(value, str):
            raise MemoryVaultContentCorrectionInvalid("content must be a string")
        if not value.strip():
            raise MemoryVaultContentCorrectionInvalid("content is required")
        return value

    # -- Helpers ----------------------------------------------------------

    def _readback(self, memory_id: str) -> VaultItem:
        """Read back the canonical Vault item through the B1 read service.

        No Vault projection logic is duplicated here.
        """
        item = MemoryVaultReadService(
            self._session,
            authenticated_account_id=self._account,
        ).get_item(
            identity=VaultIdentity(
                kind="canonical",
                canonical_memory_id=memory_id,
            )
        )
        if item is None:
            raise MemoryVaultMutationError(
                "canonical readback unavailable after mutation"
            )
        return item

    def _build_receipt(
        self,
        *,
        memory_id: str,
        action: str,
        field_name: str,
        previous_value: bool | int | dict | None,
        new_value: bool | int | dict | None,
        expected_updated_at: datetime,
        resulting_updated_at: datetime,
        reason: str | None,
        request_ref: str | None,
    ) -> MemoryProvenance:
        """Build one append-only Vault provenance receipt row.

        The receipt carries audit evidence only; it never becomes authority.
        Full memory content / fact payload is intentionally not stored.

        ``previous_value`` / ``new_value`` accept primitives (for
        ``pinned``/``held``/``project_id``) or a structured dict
        (``memory_persona_links`` link fields plus stable subject ID and
        canonical link kind for Persona-attribution mutations).
        """
        normalized_request_ref = str(request_ref).strip() if request_ref else None
        return MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=self._account,
            source_system=SOURCE_SYSTEM_CODEXIFY,
            source_record_id=normalized_request_ref,
            source_thread_id=None,
            source_message_id=None,
            source_import_job_id=None,
            source_export_fingerprint=None,
            source_subject_kind=SOURCE_SUBJECT_KIND_VAULT,
            source_subject_id=None,
            is_imported=False,
            extensions={
                "receipt_schema": RECEIPT_SCHEMA,
                "mutation_source": MUTATION_SOURCE,
                "action": action,
                "actor_account_id": self._account,
                "previous_values": {field_name: previous_value},
                "new_values": {field_name: new_value},
                "expected_updated_at": expected_updated_at.isoformat(),
                "resulting_updated_at": resulting_updated_at.isoformat(),
                "reason": reason,
                "request_ref": normalized_request_ref,
            },
        )

    def _load_authorized_memory(self, memory_id: str) -> MemoryRecord:
        row = self._session.execute(
            select(MemoryRecord)
            .where(
                MemoryRecord.memory_id == memory_id,
                MemoryRecord.user_id == self._account,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if row is None:
            self._session.rollback()
            raise MemoryVaultMutationNotAvailable("memory item is not available")
        return row

    def _require_fresh_token(
        self,
        row: MemoryRecord,
        expected_updated_at: datetime,
    ) -> None:
        if row.updated_at != expected_updated_at:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            )

    def _load_current_project(self, project_id: int | None) -> Project | None:
        if project_id is None:
            return None
        project = self._session.execute(
            select(Project)
            .where(
                Project.id == project_id,
                Project.user_id == self._account,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if project is None:
            self._session.rollback()
            raise MemoryVaultMutationError("current Project authority is unavailable")
        return project

    def _load_available_project(self, project_id: int) -> Project:
        project = self._session.execute(
            select(Project)
            .where(
                Project.id == project_id,
                Project.user_id == self._account,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if project is None:
            self._session.rollback()
            raise MemoryVaultProjectNotAvailable("Project is not available")
        return project

    def _require_conflict_free_project(self, project: Project) -> None:
        if classify_project_ownership(project).has_authority_conflict:
            self._session.rollback()
            raise MemoryVaultProjectAuthorityConflict(
                "Project ownership metadata conflicts with canonical authority."
            )

    @staticmethod
    def _validate_memory_id(value: object) -> None:
        if not value or not isinstance(value, str) or not value.strip():
            raise MemoryVaultMutationError("memory_id is required")

    @staticmethod
    def _validate_cas_token(value: object) -> None:
        if value is None:
            raise MemoryVaultMutationError("expected_updated_at is required")
        if not isinstance(value, datetime):
            raise MemoryVaultMutationError(
                "expected_updated_at must be a timezone-aware datetime"
            )
        if value.tzinfo is None or value.utcoffset() is None:
            raise MemoryVaultMutationError("expected_updated_at must be timezone-aware")

    @staticmethod
    def _validate_project_id(value: object) -> None:
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
        ):
            raise MemoryVaultMutationError(
                "project_id must be a positive integer or null"
            )

    @staticmethod
    def _validate_persona_subject_id(value: object) -> None:
        if not value or not isinstance(value, str) or not value.strip():
            raise MemoryVaultMutationError("persona_subject_id is required")

    @staticmethod
    def _normalize_link_kind(value: object) -> str:
        """Normalize one canonical link-kind value to ``MemoryPersonaLinkKind``.

        Accepts either the enum instance or its string ``value``; rejects
        everything else. The canonical enum is the protocol authority and
        is the only path that can supply a valid token.
        """
        if isinstance(value, MemoryPersonaLinkKind):
            return value.value
        if not isinstance(value, str) or not value.strip():
            raise MemoryVaultMutationError("link_kind is required")
        candidate = value.strip()
        if candidate not in _PERSONA_LINK_KIND_VALUES:
            raise MemoryVaultMutationError(
                "link_kind must be a canonical MemoryPersonaLinkKind value"
            )
        return candidate

    def _load_available_persona_subject(
        self, persona_subject_id: str
    ) -> PersonaSubject:
        """Resolve one same-account canonical Persona subject.

        Missing and foreign-account subjects share one unavailable posture;
        the service does not differentiate them.
        """
        subject = self._session.execute(
            select(PersonaSubject).where(
                PersonaSubject.persona_subject_id == persona_subject_id,
                PersonaSubject.user_id == self._account,
            )
        ).scalar_one_or_none()
        if subject is None:
            self._session.rollback()
            raise MemoryVaultPersonaSubjectNotAvailable(
                "Persona subject is not available"
            )
        return subject

    def _find_existing_persona_link(
        self,
        *,
        memory_id: str,
        persona_subject_id: str,
        link_kind: str,
    ) -> MemoryPersonaLink | None:
        return self._session.execute(
            select(MemoryPersonaLink).where(
                MemoryPersonaLink.memory_id == memory_id,
                MemoryPersonaLink.user_id == self._account,
                MemoryPersonaLink.persona_subject_id == persona_subject_id,
                MemoryPersonaLink.persona_user_id == self._account,
                MemoryPersonaLink.link_kind == link_kind,
            )
        ).scalar_one_or_none()


__all__ = [
    "ACTION_PIN",
    "ACTION_UNPIN",
    "ACTION_HOLD",
    "ACTION_RELEASE_HOLD",
    "ACTION_SET_PROJECT_SCOPE",
    "ACTION_CLEAR_PROJECT_SCOPE",
    "ACTION_ADD_PERSONA_ATTRIBUTION",
    "ACTION_REMOVE_PERSONA_ATTRIBUTION",
    "ACTION_CONTENT_CORRECTION",
    "ACTION_APPROVE",
    "ACTION_REJECT",
    "ACTION_DISPUTE",
    "ACTION_RETIRE",
    "ACTION_RESTORE",
    "REVIEW_ACTION_TARGETS",
    "MemoryVaultMutationConflict",
    "MemoryVaultMutationError",
    "MemoryVaultMutationNotAvailable",
    "MemoryVaultProjectNotAvailable",
    "MemoryVaultProjectAuthorityConflict",
    "MemoryVaultPersonaSubjectNotAvailable",
    "MemoryVaultPersonaSubjectLifecycleConflict",
    "MemoryVaultContentCorrectionInvalid",
    "MemoryVaultContentCorrectionUnsupported",
    "MemoryVaultContentCorrectionIntegrityError",
    "MemoryVaultLifecycleInvalid",
    "MemoryVaultLifecycleUnsupported",
    "MemoryVaultLifecycleIntegrityError",
    "MemoryVaultReviewTransitionInvalid",
    "MemoryVaultReviewTransitionUnsupported",
    "MemoryVaultReviewTransitionIntegrityError",
    "MemoryVaultMutationService",
    "RECEIPT_SCHEMA",
    "VaultMutationResult",
    "VaultContentCorrectionResult",
    "VaultReviewTransitionResult",
    "VaultLifecycleTransitionResult",
]
