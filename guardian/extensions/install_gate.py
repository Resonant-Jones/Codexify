"""Manual install-gate approval and rejection helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from guardian.extensions.contracts import (
    CapabilityRegistryEntry,
    ExtensionRequestedPermission,
    InstallGateDecisionRecord,
)
from guardian.extensions.registry import CapabilityRegistry
from guardian.extensions.store import ExtensionProposalStore
from guardian.extensions.tokens import (
    CapabilityRegistryStatus,
    InstallGateDecisionToken,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_decision_id() -> str:
    return f"decision_{uuid4().hex[:16]}"


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


class InstallGate:
    """Backend-only manual decision helpers for proposal approval."""

    def __init__(
        self,
        store: ExtensionProposalStore | None = None,
        registry: CapabilityRegistry | None = None,
    ) -> None:
        self.store = store or ExtensionProposalStore()
        self.registry = registry or CapabilityRegistry(self.store)

    def approve_proposal(
        self,
        *,
        account_id: str,
        proposal_id: str,
        reason: str | None = None,
        notes: Mapping[str, Any] | None = None,
        approved_permissions: Sequence[
            ExtensionRequestedPermission | Mapping[str, Any]
        ]
        | None = None,
        registry_status: str = CapabilityRegistryStatus.REGISTERED.value,
        registration_metadata: Mapping[str, Any] | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> tuple[InstallGateDecisionRecord, CapabilityRegistryEntry]:
        proposal = self.store.get_proposal_by_id(
            account_id=account_id, proposal_id=proposal_id
        )
        if proposal is None:
            raise LookupError(
                f"proposal not found for account_id={account_id!r}"
            )

        approved_snapshot = _coerce_permissions(
            approved_permissions if approved_permissions is not None else None
        )
        if approved_permissions is not None:
            from guardian.extensions.registry import _ensure_approved_subset

            _ensure_approved_subset(
                proposal.requested_permissions, approved_snapshot
            )
        else:
            approved_snapshot = proposal.requested_permissions

        decision_created_at = _utc_now()
        decision = InstallGateDecisionRecord(
            decision_id=_new_decision_id(),
            account_id=proposal.account_id,
            proposal_id=proposal.proposal_id,
            decision_token=InstallGateDecisionToken.APPROVED.value,
            reason=reason,
            notes=dict(notes or {}),
            requested_permissions=proposal.requested_permissions,
            approved_permissions=approved_snapshot,
            created_at=decision_created_at,
            updated_at=decision_created_at,
        )
        stored_decision = self.store.create_install_gate_decision(decision)
        registry_entry = self.registry.promote_approved_proposal(
            proposal=proposal,
            decision=stored_decision,
            approved_permissions=approved_snapshot,
            status=registry_status,
            registration_metadata=registration_metadata,
            provenance=provenance,
        )
        self.store.update_proposal_status(
            account_id=proposal.account_id,
            proposal_id=proposal.proposal_id,
            status="accepted",
        )
        return stored_decision, registry_entry

    def reject_proposal(
        self,
        *,
        account_id: str,
        proposal_id: str,
        reason: str | None = None,
        notes: Mapping[str, Any] | None = None,
    ) -> InstallGateDecisionRecord:
        proposal = self.store.get_proposal_by_id(
            account_id=account_id, proposal_id=proposal_id
        )
        if proposal is None:
            raise LookupError(
                f"proposal not found for account_id={account_id!r}"
            )

        decision_created_at = _utc_now()
        decision = InstallGateDecisionRecord(
            decision_id=_new_decision_id(),
            account_id=proposal.account_id,
            proposal_id=proposal.proposal_id,
            decision_token=InstallGateDecisionToken.REJECTED.value,
            reason=reason,
            notes=dict(notes or {}),
            requested_permissions=proposal.requested_permissions,
            approved_permissions=(),
            created_at=decision_created_at,
            updated_at=decision_created_at,
        )
        stored_decision = self.store.create_install_gate_decision(decision)
        self.store.update_proposal_status(
            account_id=proposal.account_id,
            proposal_id=proposal.proposal_id,
            status="rejected",
        )
        return stored_decision


__all__ = ["InstallGate"]
