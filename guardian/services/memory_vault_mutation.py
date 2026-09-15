"""Memory Vault mutation service (UMS-05C1): CAS-backed pin/unpin.

This module implements the first internal Guardian Vault mutation seam:
account-owned canonical ``memory_records`` pin/unpin through an explicit
``updated_at`` compare-and-swap token and one append-only
``memory_provenance`` receipt per actual state change.

It is a write service only for the ``pinned`` boolean. It does not:

- expose an HTTP route;
- mutate content, review, activation, Project scope, Persona links,
  ``held``, or ``extensions``;
- mutate compatibility projections or Personal Facts;
- introduce a revision column or a mutation-receipt table;
- grant retrieval or ambient eligibility.

Receipts are AUDIT / LINEAGE only. Pin authority remains
``memory_records.pinned``; the provenance ``extensions`` payload is
non-authoritative evidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from guardian.db.models import MemoryProvenance, MemoryRecord
from guardian.services.memory_vault_read import (
    MemoryVaultReadService,
    VaultIdentity,
    VaultItem,
)

#: Frozen receipt audit labels for this slice. These are audit/lineage
#: labels only; they do not grant retrieval or authorization semantics.
ACTION_PIN = "pin"
ACTION_UNPIN = "unpin"

#: Stable receipt schema marker stored in provenance extensions.
RECEIPT_SCHEMA = "memory-vault-mutation.v1"

#: Canonical provenance vocabulary for the Vault mutation receipt.
SOURCE_SYSTEM_CODEXIFY = "codexify"
SOURCE_SUBJECT_KIND_VAULT = "vault"
MUTATION_SOURCE = "vault"


class MemoryVaultMutationError(Exception):
    """Fail-closed error for Vault mutation integrity defects."""


class MemoryVaultMutationNotAvailable(MemoryVaultMutationError):
    """The requested canonical memory is not available to this account.

    Missing and cross-account share this same posture; the service never
    reveals record existence to a non-owner.
    """


class MemoryVaultMutationConflict(MemoryVaultMutationError):
    """The supplied ``expected_updated_at`` token is stale."""


@dataclass(frozen=True)
class VaultMutationResult:
    """Outcome of one pin/unpin mutation attempt."""

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
        """Set canonical pin state with an explicit stale-write CAS token.

        A changed mutation is one PostgreSQL transaction: authorize the
        account-owned canonical row, compare ``expected_updated_at``, flip
        ``pinned``, advance the database-authored ``updated_at``, append one
        Vault provenance receipt, then commit and read back through the B1
        read service. A no-op (same pin state, fresh token) returns
        ``changed=False`` with no write. A stale token fails closed with no
        write and no receipt.
        """
        self._validate_memory_id(memory_id)
        self._validate_cas_token(expected_updated_at)
        desired = bool(pinned)

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

        if row.updated_at != expected_updated_at:
            self._session.rollback()
            raise MemoryVaultMutationConflict(
                "memory item changed; expected_updated_at is stale"
            )

        previous_pinned = bool(row.pinned)
        previous_updated_at = row.updated_at

        if previous_pinned == desired:
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
                    pinned=desired,
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
            action=ACTION_PIN if desired else ACTION_UNPIN,
            previous_pinned=previous_pinned,
            new_pinned=desired,
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
        if bool(item.pinned) != desired:
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
        previous_pinned: bool,
        new_pinned: bool,
        expected_updated_at: datetime,
        resulting_updated_at: datetime,
        reason: str | None,
        request_ref: str | None,
    ) -> MemoryProvenance:
        """Build one append-only Vault provenance receipt row.

        The receipt carries audit evidence only; it never becomes pin
        authority. Full memory content / fact payload is intentionally not
        stored.
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
                "previous_values": {"pinned": previous_pinned},
                "new_values": {"pinned": new_pinned},
                "expected_updated_at": expected_updated_at.isoformat(),
                "resulting_updated_at": resulting_updated_at.isoformat(),
                "reason": reason,
                "request_ref": normalized_request_ref,
            },
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


__all__ = [
    "ACTION_PIN",
    "ACTION_UNPIN",
    "MemoryVaultMutationConflict",
    "MemoryVaultMutationError",
    "MemoryVaultMutationNotAvailable",
    "MemoryVaultMutationService",
    "RECEIPT_SCHEMA",
    "VaultMutationResult",
]
