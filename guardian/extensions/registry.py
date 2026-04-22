"""Capability registry promotion helpers for approved extensions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from guardian.extensions.contracts import (
    CapabilityRegistryEntry,
    ExtensionProposalRecord,
    ExtensionRequestedPermission,
    InstallGateDecisionRecord,
)
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityEntryProvenanceClass,
    CapabilityRegistryStatus,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_registry_id() -> str:
    return f"registry_{uuid4().hex[:16]}"


def _coerce_permissions(
    value: Sequence[ExtensionRequestedPermission | Mapping[str, Any]] | None,
) -> tuple[ExtensionRequestedPermission, ...]:
    if value is None:
        return ()
    normalized: list[ExtensionRequestedPermission] = []
    for item in value:
        if isinstance(item, ExtensionRequestedPermission):
            normalized.append(item)
            continue
        if isinstance(item, Mapping):
            normalized.append(ExtensionRequestedPermission.from_payload(item))
            continue
        raise ValueError(
            "permissions must be extension permission records or mappings"
        )
    return tuple(normalized)


def _permission_key(
    permission: ExtensionRequestedPermission,
) -> tuple[str, str]:
    return permission.permission, permission.resource or ""


def _ensure_approved_subset(
    requested: tuple[ExtensionRequestedPermission, ...],
    approved: tuple[ExtensionRequestedPermission, ...],
) -> None:
    requested_keys = {_permission_key(item) for item in requested}
    for item in approved:
        if _permission_key(item) not in requested_keys:
            raise ValueError(
                "approved permissions must be a subset of requested permissions"
            )


class CapabilityRegistry:
    """Backend-only capability registry persistence facade."""

    def __init__(self, store: ExtensionProposalStore | None = None) -> None:
        self.store = store or ExtensionProposalStore()

    def get_registry_entry_by_id(
        self, *, account_id: str, registry_id: str
    ) -> CapabilityRegistryEntry | None:
        return self.store.get_registry_entry_by_id(
            account_id=account_id, registry_id=registry_id
        )

    def list_registry_entries(
        self,
        *,
        account_id: str,
        project_id: int | None = None,
        profile_id: str | None = None,
        proposal_id: str | None = None,
        status: str | None = None,
    ) -> list[CapabilityRegistryEntry]:
        return self.store.list_registry_entries(
            account_id=account_id,
            project_id=project_id,
            profile_id=profile_id,
            proposal_id=proposal_id,
            status=status,
        )

    def update_registry_status(
        self,
        *,
        account_id: str,
        registry_id: str,
        status: str,
    ) -> CapabilityRegistryEntry:
        return self.store.update_registry_status(
            account_id=account_id,
            registry_id=registry_id,
            status=status,
        )

    def promote_approved_proposal(
        self,
        *,
        proposal: ExtensionProposalRecord,
        decision: InstallGateDecisionRecord,
        approved_permissions: Sequence[
            ExtensionRequestedPermission | Mapping[str, Any]
        ]
        | None = None,
        registry_id: str | None = None,
        status: str = CapabilityRegistryStatus.REGISTERED.value,
        registration_metadata: Mapping[str, Any] | None = None,
        provenance: Mapping[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> CapabilityRegistryEntry:
        if proposal.account_id != decision.account_id:
            raise ValueError("proposal and decision account ids must match")
        if proposal.proposal_id != decision.proposal_id:
            raise ValueError("proposal and decision ids must match")
        if not decision.is_approved:
            raise ValueError(
                "approved proposal promotion requires an approved decision"
            )

        approved_snapshot = _coerce_permissions(
            approved_permissions
            if approved_permissions is not None
            else decision.approved_permissions or proposal.requested_permissions
        )
        if approved_permissions is not None:
            _ensure_approved_subset(
                proposal.requested_permissions, approved_snapshot
            )

        created_at = created_at or _utc_now()
        updated_at = updated_at or created_at
        registry_id = registry_id or _new_registry_id()

        registration_metadata_payload = {
            "decision_id": decision.decision_id,
            "decision_token": decision.decision_token,
            "decision_reason": decision.reason,
            "decision_notes": dict(decision.notes),
            "proposal_id": proposal.proposal_id,
            "account_id": proposal.account_id,
        }
        if registration_metadata:
            registration_metadata_payload.update(dict(registration_metadata))

        provenance_payload = {
            "provenance_class": "proposal_approval",
            "proposal_id": proposal.proposal_id,
            "decision_id": decision.decision_id,
            "source_thread_id": proposal.source_thread_id,
            "source_message_id": proposal.source_message_id,
            "target_surface": proposal.target_surface,
        }
        if provenance:
            provenance_payload.update(dict(provenance))

        record = CapabilityRegistryEntry(
            registry_id=registry_id,
            account_id=proposal.account_id,
            proposal_id=proposal.proposal_id,
            decision_id=decision.decision_id,
            status_token=status,
            manifest_snapshot=proposal.manifest,
            requested_permissions=proposal.requested_permissions,
            approved_permissions=approved_snapshot,
            provenance_class_token=CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value,
            registration_metadata=registration_metadata_payload,
            provenance_json=provenance_payload,
            created_at=created_at,
            updated_at=updated_at,
        )
        return self.store.create_registry_entry(record)


__all__ = ["CapabilityRegistry"]
