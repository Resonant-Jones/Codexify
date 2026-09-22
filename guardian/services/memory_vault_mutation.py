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
    MemoryPersonaLink,
    MemoryProvenance,
    MemoryRecord,
    PersonaSubject,
    Project,
)
from guardian.protocol_tokens import MemoryPersonaLinkKind, PersonaSubjectLifecycle
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


@dataclass(frozen=True)
class VaultMutationResult:
    """Outcome of one Vault governance mutation attempt."""

    changed: bool
    receipt_id: str | None
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
    "MemoryVaultMutationConflict",
    "MemoryVaultMutationError",
    "MemoryVaultMutationNotAvailable",
    "MemoryVaultProjectNotAvailable",
    "MemoryVaultProjectAuthorityConflict",
    "MemoryVaultPersonaSubjectNotAvailable",
    "MemoryVaultPersonaSubjectLifecycleConflict",
    "MemoryVaultMutationService",
    "RECEIPT_SCHEMA",
    "VaultMutationResult",
]
