"""Memory Vault direct user-authored creation service (UMS-05C6).

Implements the explicit authenticated human canonical-memory authoring
authority admitted by the frozen Vault contract:

    direct authenticated human
      ↓
    stable RequestUserScope.account_id
      ↓
    MemoryVaultCreationService
      ↓
    server-generated canonical memory_id
      ↓
    episodic_semantic_memory
      + exact authored text
      + account scope only (project_id = NULL)
      + reviewed_at = activated_at (database-authored, single transaction)
      + pinned = held = false
      + extensions = NULL
      + zero Persona links
      +
    canonical Vault provenance / ``create_memory`` receipt
      ↓
    one PostgreSQL transaction
      ↓
    MemoryVaultReadService canonical readback

This module deliberately does not:

- mutate an existing canonical memory;
- create Personal Facts;
- choose semantic species;
- accept caller-supplied memory IDs;
- bundle Project scope, Persona attribution, pin, hold, review, or
  activation choice;
- call a model to summarize, classify, or rewrite the authored text;
- write ambient eligibility or trigger retrieval.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from guardian.db.models import MemoryProvenance, MemoryRecord
from guardian.protocol_tokens import MemorySemanticSpecies
from guardian.services.memory_vault_read import (
    MemoryVaultReadService,
    VaultIdentity,
    VaultItem,
)

#: Stable receipt schema marker stored in provenance extensions.
RECEIPT_SCHEMA = "memory-vault-mutation.v1"

#: Frozen C6 action label stored in the creation receipt.
ACTION_CREATE_MEMORY = "create_memory"

#: Canonical Vault provenance vocabulary for direct C6 creation.
SOURCE_SYSTEM_CODEXIFY = "codexify"
SOURCE_SUBJECT_KIND_VAULT = "vault"
MUTATION_SOURCE = "vault"

#: The only semantic species C6 may create.
_EPISODIC_SEMANTIC_SPECIES = MemorySemanticSpecies.EPISODIC_SEMANTIC_MEMORY.value


@dataclass(frozen=True)
class VaultCreationResult:
    """Internal result returned by ``MemoryVaultCreationService.create_memory``.

    ``receipt_id`` is the server-generated initial Vault provenance
    (``memory_provenance.provenance_id``). ``item`` is the canonical
    ``VaultItem`` readback produced by ``MemoryVaultReadService``.
    """

    receipt_id: str
    item: VaultItem


class MemoryVaultCreationError(Exception):
    """Fail-closed error for Vault direct-creation integrity defects."""


class MemoryVaultCreationAccountNotAvailable(MemoryVaultCreationError):
    """The authenticated account id is missing, blank, or otherwise invalid."""


class MemoryVaultCreationIntegrityError(MemoryVaultCreationError):
    """Creation transaction or canonical readback integrity failure."""


class MemoryVaultCreationService:
    """Direct user-authored canonical episodic memory creation authority.

    Account is constructor-bound. No per-call owner/identity override is
    permitted. The service writes exactly one canonical ``MemoryRecord``
    and exactly one initial ``memory_provenance`` receipt per call,
    atomically, in a single PostgreSQL transaction.
    """

    def __init__(
        self,
        session: Session,
        *,
        authenticated_account_id: str,
    ) -> None:
        account = (
            authenticated_account_id.strip()
            if isinstance(authenticated_account_id, str)
            else ""
        )
        if not account:
            raise MemoryVaultCreationAccountNotAvailable(
                "authenticated account id is required"
            )
        self._session = session
        self._account = account

    def create_memory(
        self,
        *,
        content: str,
        request_ref: str | None = None,
    ) -> VaultCreationResult:
        """Create one canonical account-scoped episodic Vault memory.

        Persists a single ``MemoryRecord`` (account owner; project NULL;
        semantic species fixed to ``episodic_semantic_memory``;
        ``reviewed_at`` and ``activated_at`` set from a single database
        ``now()`` expression; ``fact_*`` NULL; ``pinned``/``held`` false;
        ``extensions`` NULL) and one initial ``MemoryProvenance``
        creation receipt in the same transaction. Returns the canonical
        ``VaultItem`` readback.

        Whitespace-only content is rejected (the canonical envelope is
        explicit human authored text). The exact submitted text is
        persisted verbatim — no summarization, classification, or
        silent normalization.
        """
        validated_content = self._validate_content(content)
        normalized_request_ref = self._normalize_request_ref(request_ref)

        memory_id = str(uuid.uuid4())
        now_expr = text("now()")
        new_row = MemoryRecord(
            memory_id=memory_id,
            user_id=self._account,
            project_id=None,
            semantic_species=_EPISODIC_SEMANTIC_SPECIES,
            text_content=validated_content,
            fact_key=None,
            fact_value=None,
            fact_confidence=None,
            reviewed_at=now_expr,
            activated_at=now_expr,
            pinned=False,
            held=False,
            extensions=None,
        )
        self._session.add(new_row)
        try:
            self._session.flush()
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultCreationIntegrityError(
                "memory row persistence failed"
            ) from exc

        # Force the row to load its server-defaulted ``created_at`` and
        # ``updated_at`` into the in-memory instance so the receipt and
        # readback can use the database-authored timestamps.
        self._session.refresh(new_row)

        if new_row.reviewed_at is None or new_row.activated_at is None:
            self._session.rollback()
            raise MemoryVaultCreationIntegrityError(
                "creation did not produce reviewed_at/activated_at"
            )
        if new_row.activated_at < new_row.reviewed_at:
            self._session.rollback()
            raise MemoryVaultCreationIntegrityError(
                "creation activated_at precedes reviewed_at"
            )

        receipt = MemoryProvenance(
            provenance_id=str(uuid.uuid4()),
            memory_id=memory_id,
            user_id=self._account,
            source_system=SOURCE_SYSTEM_CODEXIFY,
            source_record_id=memory_id,
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
                "action": ACTION_CREATE_MEMORY,
                "actor_account_id": self._account,
                "previous_values": {"exists": False},
                "new_values": {
                    "exists": True,
                    "semantic_species": _EPISODIC_SEMANTIC_SPECIES,
                    "project_id": None,
                    "review_posture": "approved",
                    "lifecycle_posture": "active",
                    "pinned": False,
                    "held": False,
                },
                "resulting_created_at": new_row.created_at.isoformat(),
                "resulting_updated_at": new_row.updated_at.isoformat(),
                "reason": None,
                "request_ref": normalized_request_ref,
            },
        )
        self._session.add(receipt)
        try:
            self._session.flush()
        except Exception as exc:  # noqa: BLE001
            self._session.rollback()
            raise MemoryVaultCreationIntegrityError(
                "creation receipt persistence failed"
            ) from exc

        self._session.commit()

        item = self._readback_item(memory_id)
        return VaultCreationResult(
            receipt_id=receipt.provenance_id,
            item=item,
        )

    @staticmethod
    def _validate_content(content: object) -> str:
        if not isinstance(content, str):
            raise MemoryVaultCreationError("content must be a string")
        if not content.strip():
            raise MemoryVaultCreationError("content is required")
        return content

    @staticmethod
    def _normalize_request_ref(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise MemoryVaultCreationError("request_ref must be a string")
        stripped = value.strip()
        return stripped or None

    def _readback_item(self, memory_id: str) -> VaultItem:
        read_service = MemoryVaultReadService(
            self._session, authenticated_account_id=self._account
        )
        identity = VaultIdentity(kind="canonical", canonical_memory_id=memory_id)
        item = read_service.get_item(identity=identity)
        if item is None:
            raise MemoryVaultCreationIntegrityError(
                "canonical readback returned no Vault item"
            )
        return item


__all__ = [
    "ACTION_CREATE_MEMORY",
    "MemoryVaultCreationAccountNotAvailable",
    "MemoryVaultCreationError",
    "MemoryVaultCreationIntegrityError",
    "MemoryVaultCreationService",
    "MUTATION_SOURCE",
    "RECEIPT_SCHEMA",
    "SOURCE_SUBJECT_KIND_VAULT",
    "SOURCE_SYSTEM_CODEXIFY",
    "VaultCreationResult",
]
