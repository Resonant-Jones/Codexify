"""Backend store for extension proposal persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import asc

from guardian.db.models import (
    AgentExtensionInstallGateDecision,
    AgentExtensionProposal,
    AgentExtensionRegistryEntry,
)
from guardian.extensions.contracts import (
    CapabilityRegistryEntry,
    ExtensionProposalManifest,
    ExtensionProposalRecord,
    InstallGateDecisionRecord,
)
from guardian.extensions.tokens import (
    normalize_capability_registry_status,
    normalize_extension_proposal_scope,
    normalize_extension_proposal_status,
    normalize_install_gate_decision_token,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_account_id(value: str | None) -> str:
    account_id = str(value or "").strip()
    if not account_id:
        raise ValueError("account_id is required")
    return account_id


def _coerce_optional_int(value: int | None, *, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _coerce_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class ExtensionProposalStore:
    """Durable store for extension proposal drafts and statuses."""

    def __init__(self, db: Any | None = None) -> None:
        self.db = db

    def configure_db(self, db: Any | None) -> None:
        self.db = db

    def _has_db(self) -> bool:
        return bool(self.db is not None and hasattr(self.db, "get_session"))

    def _session(self):
        if not self._has_db():
            raise RuntimeError("extension proposal store requires a database")
        return self.db.get_session()

    @staticmethod
    def _row_to_record(row: AgentExtensionProposal) -> ExtensionProposalRecord:
        return ExtensionProposalRecord.from_payload(
            {
                "proposal_id": row.proposal_id,
                "account_id": row.account_id,
                "status_token": row.status_token,
                "target_surface_token": row.target_surface_token,
                "scope_token": row.scope_token,
                "project_id": row.project_id,
                "profile_id": row.profile_id,
                "source_thread_id": row.source_thread_id,
                "source_message_id": row.source_message_id,
                "requested_permissions_json": row.requested_permissions_json,
                "declared_dependencies_json": row.declared_dependencies_json,
                "rollback_metadata_json": row.rollback_metadata_json,
                "test_evidence_json": row.test_evidence_json,
                "manifest_json": row.manifest_json,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    @staticmethod
    def _decision_row_to_record(
        row: AgentExtensionInstallGateDecision,
    ) -> InstallGateDecisionRecord:
        return InstallGateDecisionRecord.from_payload(
            {
                "decision_id": row.decision_id,
                "account_id": row.account_id,
                "proposal_id": row.proposal_id,
                "decision_token": row.decision_token,
                "reason": row.reason,
                "notes_json": row.notes_json,
                "requested_permissions_json": row.requested_permissions_json,
                "approved_permissions_json": row.approved_permissions_json,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    @staticmethod
    def _registry_row_to_record(
        row: AgentExtensionRegistryEntry,
    ) -> CapabilityRegistryEntry:
        return CapabilityRegistryEntry.from_payload(
            {
                "registry_id": row.registry_id,
                "account_id": row.account_id,
                "proposal_id": row.proposal_id,
                "decision_id": row.decision_id,
                "status_token": row.status_token,
                "target_surface_token": row.target_surface_token,
                "scope_token": row.scope_token,
                "project_id": row.project_id,
                "profile_id": row.profile_id,
                "source_thread_id": row.source_thread_id,
                "source_message_id": row.source_message_id,
                "requested_permissions_json": row.requested_permissions_json,
                "approved_permissions_json": row.approved_permissions_json,
                "manifest_snapshot_json": row.manifest_snapshot_json,
                "registration_metadata_json": row.registration_metadata_json,
                "provenance_class_token": row.provenance_class_token,
                "provenance_json": row.provenance_json,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    def create_proposal(
        self,
        *,
        account_id: str,
        manifest: ExtensionProposalManifest,
        status: str = "draft",
        proposal_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> ExtensionProposalRecord:
        account_id = _clean_account_id(account_id)
        status_token = normalize_extension_proposal_status(status)
        proposal_id = (
            _coerce_optional_text(proposal_id) or f"proposal_{uuid4().hex[:16]}"
        )
        created_at = created_at or _utc_now()
        updated_at = updated_at or created_at

        row = AgentExtensionProposal(
            proposal_id=proposal_id,
            account_id=account_id,
            project_id=_coerce_optional_int(
                manifest.project_id, field_name="project_id"
            ),
            profile_id=_coerce_optional_text(manifest.profile_id),
            source_thread_id=_coerce_optional_int(
                manifest.source_thread_id, field_name="source_thread_id"
            ),
            source_message_id=_coerce_optional_int(
                manifest.source_message_id, field_name="source_message_id"
            ),
            target_surface_token=manifest.target_surface,
            scope_token=normalize_extension_proposal_scope(manifest.scope),
            status_token=status_token,
            requested_permissions_json=[
                permission.to_payload()
                for permission in manifest.requested_permissions
            ],
            declared_dependencies_json=[
                dependency.to_payload()
                for dependency in manifest.declared_dependencies
            ],
            rollback_metadata_json=(
                manifest.rollback_metadata.to_payload()
                if manifest.rollback_metadata is not None
                else None
            ),
            test_evidence_json=(
                manifest.test_evidence_metadata.to_payload()
                if manifest.test_evidence_metadata is not None
                else None
            ),
            manifest_json=manifest.to_payload(),
            created_at=created_at,
            updated_at=updated_at,
        )

        with self._session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._row_to_record(row)

    def get_proposal_by_id(
        self, *, account_id: str, proposal_id: str
    ) -> ExtensionProposalRecord | None:
        account_id = _clean_account_id(account_id)
        proposal_id = _coerce_optional_text(proposal_id)
        if not proposal_id:
            return None

        with self._session() as session:
            row = (
                session.query(AgentExtensionProposal)
                .filter_by(account_id=account_id, proposal_id=proposal_id)
                .first()
            )
            if row is None:
                return None
            return self._row_to_record(row)

    def list_proposals(
        self,
        *,
        account_id: str,
        project_id: int | None = None,
        profile_id: str | None = None,
        scope: str | None = None,
        status: str | None = None,
    ) -> list[ExtensionProposalRecord]:
        account_id = _clean_account_id(account_id)
        filters: list[Any] = [AgentExtensionProposal.account_id == account_id]
        if project_id is not None:
            filters.append(AgentExtensionProposal.project_id == int(project_id))
        if profile_id is not None:
            filters.append(
                AgentExtensionProposal.profile_id
                == _coerce_optional_text(profile_id)
            )
        if scope is not None:
            filters.append(
                AgentExtensionProposal.scope_token
                == normalize_extension_proposal_scope(scope)
            )
        if status is not None:
            filters.append(
                AgentExtensionProposal.status_token
                == normalize_extension_proposal_status(status)
            )

        with self._session() as session:
            rows = (
                session.query(AgentExtensionProposal)
                .filter(*filters)
                .order_by(
                    asc(AgentExtensionProposal.created_at),
                    asc(AgentExtensionProposal.proposal_id),
                )
                .all()
            )
            return [self._row_to_record(row) for row in rows]

    def update_proposal_status(
        self,
        *,
        account_id: str,
        proposal_id: str,
        status: str,
    ) -> ExtensionProposalRecord:
        account_id = _clean_account_id(account_id)
        proposal_id = _coerce_optional_text(proposal_id)
        if not proposal_id:
            raise LookupError("proposal_id is required")
        status_token = normalize_extension_proposal_status(status)

        with self._session() as session:
            row = (
                session.query(AgentExtensionProposal)
                .filter_by(account_id=account_id, proposal_id=proposal_id)
                .first()
            )
            if row is None:
                raise LookupError(
                    f"proposal not found for account_id={account_id!r}"
                )
            row.status_token = status_token
            row.updated_at = _utc_now()
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._row_to_record(row)

    def create_install_gate_decision(
        self, record: InstallGateDecisionRecord
    ) -> InstallGateDecisionRecord:
        row = AgentExtensionInstallGateDecision(**record.to_payload())
        with self._session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._decision_row_to_record(row)

    def get_install_gate_decision_by_id(
        self, *, account_id: str, decision_id: str
    ) -> InstallGateDecisionRecord | None:
        account_id = _clean_account_id(account_id)
        decision_id = _coerce_optional_text(decision_id)
        if not decision_id:
            return None

        with self._session() as session:
            row = (
                session.query(AgentExtensionInstallGateDecision)
                .filter_by(account_id=account_id, decision_id=decision_id)
                .first()
            )
            if row is None:
                return None
            return self._decision_row_to_record(row)

    def list_install_gate_decisions(
        self,
        *,
        account_id: str,
        proposal_id: str | None = None,
        decision_token: str | None = None,
    ) -> list[InstallGateDecisionRecord]:
        account_id = _clean_account_id(account_id)
        filters: list[Any] = [
            AgentExtensionInstallGateDecision.account_id == account_id
        ]
        if proposal_id is not None:
            filters.append(
                AgentExtensionInstallGateDecision.proposal_id
                == _coerce_optional_text(proposal_id)
            )
        if decision_token is not None:
            filters.append(
                AgentExtensionInstallGateDecision.decision_token
                == normalize_install_gate_decision_token(decision_token)
            )

        with self._session() as session:
            rows = (
                session.query(AgentExtensionInstallGateDecision)
                .filter(*filters)
                .order_by(
                    asc(AgentExtensionInstallGateDecision.created_at),
                    asc(AgentExtensionInstallGateDecision.decision_id),
                )
                .all()
            )
            return [self._decision_row_to_record(row) for row in rows]

    def create_registry_entry(
        self, record: CapabilityRegistryEntry
    ) -> CapabilityRegistryEntry:
        row = AgentExtensionRegistryEntry(**record.to_payload())
        with self._session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._registry_row_to_record(row)

    def get_registry_entry_by_id(
        self, *, account_id: str, registry_id: str
    ) -> CapabilityRegistryEntry | None:
        account_id = _clean_account_id(account_id)
        registry_id = _coerce_optional_text(registry_id)
        if not registry_id:
            return None

        with self._session() as session:
            row = (
                session.query(AgentExtensionRegistryEntry)
                .filter_by(account_id=account_id, registry_id=registry_id)
                .first()
            )
            if row is None:
                return None
            return self._registry_row_to_record(row)

    def list_registry_entries(
        self,
        *,
        account_id: str,
        project_id: int | None = None,
        profile_id: str | None = None,
        proposal_id: str | None = None,
        status: str | None = None,
    ) -> list[CapabilityRegistryEntry]:
        account_id = _clean_account_id(account_id)
        filters: list[Any] = [
            AgentExtensionRegistryEntry.account_id == account_id
        ]
        if project_id is not None:
            filters.append(
                AgentExtensionRegistryEntry.project_id == int(project_id)
            )
        if profile_id is not None:
            filters.append(
                AgentExtensionRegistryEntry.profile_id
                == _coerce_optional_text(profile_id)
            )
        if proposal_id is not None:
            filters.append(
                AgentExtensionRegistryEntry.proposal_id
                == _coerce_optional_text(proposal_id)
            )
        if status is not None:
            filters.append(
                AgentExtensionRegistryEntry.status_token
                == normalize_capability_registry_status(status)
            )

        with self._session() as session:
            rows = (
                session.query(AgentExtensionRegistryEntry)
                .filter(*filters)
                .order_by(
                    asc(AgentExtensionRegistryEntry.created_at),
                    asc(AgentExtensionRegistryEntry.registry_id),
                )
                .all()
            )
            return [self._registry_row_to_record(row) for row in rows]

    def update_registry_status(
        self,
        *,
        account_id: str,
        registry_id: str,
        status: str,
    ) -> CapabilityRegistryEntry:
        account_id = _clean_account_id(account_id)
        registry_id = _coerce_optional_text(registry_id)
        if not registry_id:
            raise LookupError("registry_id is required")
        status_token = normalize_capability_registry_status(status)

        with self._session() as session:
            row = (
                session.query(AgentExtensionRegistryEntry)
                .filter_by(account_id=account_id, registry_id=registry_id)
                .first()
            )
            if row is None:
                raise LookupError(
                    f"registry entry not found for account_id={account_id!r}"
                )
            row.status_token = status_token
            row.updated_at = _utc_now()
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._registry_row_to_record(row)


__all__ = ["ExtensionProposalStore"]
