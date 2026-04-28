"""Typed contracts for extension persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence

from guardian.command_bus.contracts import INVOKE_VERSION
from guardian.extensions.tokens import (
    CapabilityActivationConflictClassToken,
    CapabilityActivationContextToken,
    CapabilityActivationDenyReasonToken,
    CapabilityActivationOutcomeToken,
    CapabilityDispatchSourceToken,
    CapabilityEntryProvenanceClass,
    CapabilityRegistryStatus,
    ExtensionInstallBindingScope,
    ExtensionInstallBindingStatus,
    InstallGateDecisionToken,
    normalize_capability_activation_conflict_class_token,
    normalize_capability_activation_context_token,
    normalize_capability_activation_deny_reason_token,
    normalize_capability_activation_outcome_token,
    normalize_capability_dispatch_source_token,
    normalize_capability_entry_provenance_class,
    normalize_capability_registry_status,
    normalize_extension_install_binding_scope,
    normalize_extension_install_binding_status,
    normalize_extension_proposal_scope,
    normalize_extension_proposal_status,
    normalize_extension_target_surface,
    normalize_install_gate_decision_token,
)

MANIFEST_VERSION = "extension-proposal-manifest.v1"


def _clean_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return {str(key): item for key, item in dict(value).items()}


def _clean_text_sequence(value: Sequence[Any] | None) -> tuple[str, ...]:
    if not value:
        return ()
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


@dataclass(frozen=True, slots=True)
class ExtensionRequestedPermission:
    """Declared permission request for a proposal manifest."""

    permission: str
    resource: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        permission = _clean_optional_text(self.permission)
        if not permission:
            raise ValueError("permission is required")
        object.__setattr__(self, "permission", permission)
        object.__setattr__(
            self, "resource", _clean_optional_text(self.resource)
        )
        object.__setattr__(self, "reason", _clean_optional_text(self.reason))
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "permission": self.permission,
            "resource": self.resource,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }
        return payload

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> ExtensionRequestedPermission:
        data = dict(payload or {})
        return cls(
            permission=data.get("permission") or data.get("key") or "",
            resource=data.get("resource"),
            reason=data.get("reason"),
            metadata=_clean_mapping(data.get("metadata"))
            if isinstance(data.get("metadata"), Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class ExtensionDeclaredDependency:
    """Declared dependency for a proposal manifest."""

    name: str
    version_spec: str | None = None
    source: str | None = None
    required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        name = _clean_optional_text(self.name)
        if not name:
            raise ValueError("dependency name is required")
        object.__setattr__(self, "name", name)
        object.__setattr__(
            self, "version_spec", _clean_optional_text(self.version_spec)
        )
        object.__setattr__(self, "source", _clean_optional_text(self.source))
        object.__setattr__(self, "required", bool(self.required))
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version_spec": self.version_spec,
            "source": self.source,
            "required": self.required,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> ExtensionDeclaredDependency:
        data = dict(payload or {})
        metadata = data.get("metadata")
        return cls(
            name=data.get("name") or data.get("package") or "",
            version_spec=data.get("version_spec"),
            source=data.get("source"),
            required=bool(data.get("required", True)),
            metadata=_clean_mapping(metadata)
            if isinstance(metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class ExtensionRollbackMetadata:
    """Rollback metadata for a proposal manifest."""

    strategy: str
    rollback_ref: str | None = None
    can_rollback: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        strategy = _clean_optional_text(self.strategy)
        if not strategy:
            raise ValueError("rollback strategy is required")
        object.__setattr__(self, "strategy", strategy)
        object.__setattr__(
            self, "rollback_ref", _clean_optional_text(self.rollback_ref)
        )
        object.__setattr__(self, "can_rollback", bool(self.can_rollback))
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "rollback_ref": self.rollback_ref,
            "can_rollback": self.can_rollback,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> ExtensionRollbackMetadata | None:
        if not payload:
            return None
        data = dict(payload)
        metadata = data.get("metadata")
        return cls(
            strategy=data.get("strategy") or "",
            rollback_ref=data.get("rollback_ref"),
            can_rollback=bool(data.get("can_rollback", True)),
            metadata=_clean_mapping(metadata)
            if isinstance(metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class ExtensionTestEvidenceMetadata:
    """Test-evidence metadata for a proposal manifest."""

    status: str
    summary: str | None = None
    artifacts: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        status = _clean_optional_text(self.status)
        if not status:
            raise ValueError("test evidence status is required")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "summary", _clean_optional_text(self.summary))
        object.__setattr__(
            self,
            "artifacts",
            tuple(
                str(item).strip()
                for item in self.artifacts
                if str(item).strip()
            ),
        )
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "summary": self.summary,
            "artifacts": list(self.artifacts),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> ExtensionTestEvidenceMetadata | None:
        if not payload:
            return None
        data = dict(payload)
        metadata = data.get("metadata")
        artifacts = data.get("artifacts")
        return cls(
            status=data.get("status") or "",
            summary=data.get("summary"),
            artifacts=tuple(str(item) for item in artifacts or []),
            metadata=_clean_mapping(metadata)
            if isinstance(metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class CapabilityExposedCommand:
    """Manifest-declared command exposure plus bounded tool aliases."""

    command_id: str
    tool_aliases: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        command_id = _clean_optional_text(self.command_id)
        if not command_id:
            raise ValueError("command_id is required")
        object.__setattr__(self, "command_id", command_id)
        object.__setattr__(
            self, "tool_aliases", _clean_text_sequence(self.tool_aliases)
        )
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "command_id": self.command_id,
            "tool_aliases": list(self.tool_aliases),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityExposedCommand:
        data = dict(payload or {})
        metadata = data.get("metadata")
        return cls(
            command_id=data.get("command_id") or data.get("tool_id") or "",
            tool_aliases=tuple(
                str(item) for item in data.get("tool_aliases") or []
            ),
            metadata=_clean_mapping(metadata)
            if isinstance(metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class ExtensionProposalManifest:
    """Manifest draft persisted for a proposed extension."""

    target_surface: str
    scope: str
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    declared_dependencies: tuple[ExtensionDeclaredDependency, ...] = ()
    exposed_commands: tuple[CapabilityExposedCommand, ...] = ()
    rollback_metadata: ExtensionRollbackMetadata | None = None
    test_evidence_metadata: ExtensionTestEvidenceMetadata | None = None
    source_thread_id: int | None = None
    source_message_id: int | None = None
    project_id: int | None = None
    profile_id: str | None = None
    summary: str | None = None
    description: str | None = None
    manifest_version: str = MANIFEST_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_surface",
            normalize_extension_target_surface(self.target_surface),
        )
        object.__setattr__(
            self,
            "scope",
            normalize_extension_proposal_scope(self.scope),
        )
        object.__setattr__(
            self,
            "requested_permissions",
            tuple(self.requested_permissions or ()),
        )
        object.__setattr__(
            self,
            "declared_dependencies",
            tuple(self.declared_dependencies or ()),
        )
        object.__setattr__(
            self,
            "exposed_commands",
            tuple(self.exposed_commands or ()),
        )
        object.__setattr__(
            self, "profile_id", _clean_optional_text(self.profile_id)
        )
        object.__setattr__(self, "summary", _clean_optional_text(self.summary))
        object.__setattr__(
            self, "description", _clean_optional_text(self.description)
        )
        object.__setattr__(
            self,
            "manifest_version",
            _clean_optional_text(self.manifest_version) or MANIFEST_VERSION,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "target_surface": self.target_surface,
            "scope": self.scope,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "summary": self.summary,
            "description": self.description,
            "requested_permissions": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "declared_dependencies": [
                dependency.to_payload()
                for dependency in self.declared_dependencies
            ],
            "exposed_commands": [
                command.to_payload() for command in self.exposed_commands
            ],
            "rollback_metadata": (
                self.rollback_metadata.to_payload()
                if self.rollback_metadata is not None
                else None
            ),
            "test_evidence_metadata": (
                self.test_evidence_metadata.to_payload()
                if self.test_evidence_metadata is not None
                else None
            ),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> ExtensionProposalManifest:
        data = dict(payload or {})
        requested_permissions = tuple(
            ExtensionRequestedPermission.from_payload(item)
            for item in data.get("requested_permissions") or []
        )
        declared_dependencies = tuple(
            ExtensionDeclaredDependency.from_payload(item)
            for item in data.get("declared_dependencies") or []
        )
        exposed_commands = tuple(
            CapabilityExposedCommand.from_payload(item)
            for item in data.get("exposed_commands") or []
        )
        rollback_metadata = ExtensionRollbackMetadata.from_payload(
            data.get("rollback_metadata")
        )
        test_evidence_metadata = ExtensionTestEvidenceMetadata.from_payload(
            data.get("test_evidence_metadata")
        )
        return cls(
            target_surface=data.get("target_surface") or "",
            scope=data.get("scope") or "",
            requested_permissions=requested_permissions,
            declared_dependencies=declared_dependencies,
            exposed_commands=exposed_commands,
            rollback_metadata=rollback_metadata,
            test_evidence_metadata=test_evidence_metadata,
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
            project_id=data.get("project_id"),
            profile_id=data.get("profile_id"),
            summary=data.get("summary"),
            description=data.get("description"),
            manifest_version=data.get("manifest_version") or MANIFEST_VERSION,
        )


@dataclass(frozen=True, slots=True)
class ExtensionProposalRecord:
    """Durable proposal row with manifest draft and canonical status."""

    proposal_id: str
    account_id: str
    status: str
    manifest: ExtensionProposalManifest
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "proposal_id",
            _clean_optional_text(self.proposal_id) or "",
        )
        object.__setattr__(
            self,
            "account_id",
            _clean_optional_text(self.account_id) or "",
        )
        object.__setattr__(
            self,
            "status",
            normalize_extension_proposal_status(self.status),
        )
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.account_id:
            raise ValueError("account_id is required")

    @property
    def target_surface(self) -> str:
        return self.manifest.target_surface

    @property
    def scope(self) -> str:
        return self.manifest.scope

    @property
    def project_id(self) -> int | None:
        return self.manifest.project_id

    @property
    def profile_id(self) -> str | None:
        return self.manifest.profile_id

    @property
    def source_thread_id(self) -> int | None:
        return self.manifest.source_thread_id

    @property
    def source_message_id(self) -> int | None:
        return self.manifest.source_message_id

    @property
    def requested_permissions(self) -> tuple[ExtensionRequestedPermission, ...]:
        return self.manifest.requested_permissions

    @property
    def declared_dependencies(self) -> tuple[ExtensionDeclaredDependency, ...]:
        return self.manifest.declared_dependencies

    @property
    def rollback_metadata(self) -> ExtensionRollbackMetadata | None:
        return self.manifest.rollback_metadata

    @property
    def test_evidence_metadata(self) -> ExtensionTestEvidenceMetadata | None:
        return self.manifest.test_evidence_metadata

    def to_payload(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "account_id": self.account_id,
            "status": self.status,
            "target_surface_token": self.target_surface,
            "scope_token": self.scope,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "requested_permissions_json": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "declared_dependencies_json": [
                dependency.to_payload()
                for dependency in self.declared_dependencies
            ],
            "rollback_metadata_json": (
                self.rollback_metadata.to_payload()
                if self.rollback_metadata is not None
                else None
            ),
            "test_evidence_json": (
                self.test_evidence_metadata.to_payload()
                if self.test_evidence_metadata is not None
                else None
            ),
            "manifest_json": self.manifest.to_payload(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> ExtensionProposalRecord:
        data = dict(payload)
        manifest_payload = data.get("manifest_json")
        if not isinstance(manifest_payload, Mapping):
            manifest_payload = {
                "target_surface": data.get("target_surface_token"),
                "scope": data.get("scope_token"),
                "source_thread_id": data.get("source_thread_id"),
                "source_message_id": data.get("source_message_id"),
                "project_id": data.get("project_id"),
                "profile_id": data.get("profile_id"),
                "requested_permissions": data.get("requested_permissions_json")
                or [],
                "declared_dependencies": data.get("declared_dependencies_json")
                or [],
                "rollback_metadata": data.get("rollback_metadata_json"),
                "test_evidence_metadata": data.get("test_evidence_json"),
            }
        manifest = ExtensionProposalManifest.from_payload(manifest_payload)
        return cls(
            proposal_id=data.get("proposal_id") or data.get("id") or "",
            account_id=data.get("account_id") or "",
            status=data.get("status_token") or data.get("status") or "",
            manifest=manifest,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass(frozen=True, slots=True)
class InstallGateDecisionRecord:
    """Durable manual install-gate decision record."""

    decision_id: str
    account_id: str
    proposal_id: str
    decision_token: str
    reason: str | None = None
    notes: dict[str, Any] = field(default_factory=dict)
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    approved_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision_id", _clean_optional_text(self.decision_id) or ""
        )
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        object.__setattr__(
            self, "proposal_id", _clean_optional_text(self.proposal_id) or ""
        )
        object.__setattr__(
            self,
            "decision_token",
            normalize_install_gate_decision_token(self.decision_token),
        )
        object.__setattr__(self, "reason", _clean_optional_text(self.reason))
        object.__setattr__(self, "notes", _clean_mapping(self.notes))
        object.__setattr__(
            self,
            "requested_permissions",
            tuple(self.requested_permissions or ()),
        )
        object.__setattr__(
            self,
            "approved_permissions",
            tuple(self.approved_permissions or ()),
        )
        if not self.decision_id:
            raise ValueError("decision_id is required")
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")

    @property
    def is_approved(self) -> bool:
        return self.decision_token == InstallGateDecisionToken.APPROVED.value

    @property
    def is_rejected(self) -> bool:
        return self.decision_token == InstallGateDecisionToken.REJECTED.value

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "account_id": self.account_id,
            "proposal_id": self.proposal_id,
            "decision_token": self.decision_token,
            "reason": self.reason,
            "notes_json": dict(self.notes),
            "requested_permissions_json": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "approved_permissions_json": [
                permission.to_payload()
                for permission in self.approved_permissions
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> InstallGateDecisionRecord:
        data = dict(payload)
        requested_permissions = tuple(
            ExtensionRequestedPermission.from_payload(item)
            for item in data.get("requested_permissions_json") or []
        )
        approved_permissions = tuple(
            ExtensionRequestedPermission.from_payload(item)
            for item in data.get("approved_permissions_json") or []
        )
        notes = data.get("notes_json")
        return cls(
            decision_id=data.get("decision_id") or data.get("id") or "",
            account_id=data.get("account_id") or "",
            proposal_id=data.get("proposal_id") or "",
            decision_token=data.get("decision_token")
            or data.get("decision")
            or "",
            reason=data.get("reason"),
            notes=_clean_mapping(notes) if isinstance(notes, Mapping) else {},
            requested_permissions=requested_permissions,
            approved_permissions=approved_permissions,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityRegistryEntry:
    """Durable registry record for an approved extension."""

    registry_id: str
    account_id: str
    proposal_id: str
    decision_id: str
    status_token: str
    manifest_snapshot: ExtensionProposalManifest
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    approved_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    provenance_class_token: str = (
        CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value
    )
    registration_metadata: dict[str, Any] = field(default_factory=dict)
    provenance_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "registry_id", _clean_optional_text(self.registry_id) or ""
        )
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        object.__setattr__(
            self, "proposal_id", _clean_optional_text(self.proposal_id) or ""
        )
        object.__setattr__(
            self, "decision_id", _clean_optional_text(self.decision_id) or ""
        )
        object.__setattr__(
            self,
            "status_token",
            normalize_capability_registry_status(self.status_token),
        )
        object.__setattr__(
            self,
            "provenance_class_token",
            normalize_capability_entry_provenance_class(
                self.provenance_class_token
            ),
        )
        object.__setattr__(
            self,
            "requested_permissions",
            tuple(self.requested_permissions or ()),
        )
        object.__setattr__(
            self,
            "approved_permissions",
            tuple(self.approved_permissions or ()),
        )
        object.__setattr__(
            self,
            "registration_metadata",
            _clean_mapping(self.registration_metadata),
        )
        object.__setattr__(
            self, "provenance_json", _clean_mapping(self.provenance_json)
        )
        if not self.registry_id:
            raise ValueError("registry_id is required")
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.decision_id:
            raise ValueError("decision_id is required")

    @property
    def target_surface(self) -> str:
        return self.manifest_snapshot.target_surface

    @property
    def scope(self) -> str:
        return self.manifest_snapshot.scope

    @property
    def project_id(self) -> int | None:
        return self.manifest_snapshot.project_id

    @property
    def profile_id(self) -> str | None:
        return self.manifest_snapshot.profile_id

    @property
    def source_thread_id(self) -> int | None:
        return self.manifest_snapshot.source_thread_id

    @property
    def source_message_id(self) -> int | None:
        return self.manifest_snapshot.source_message_id

    @property
    def is_registered(self) -> bool:
        return self.status_token == CapabilityRegistryStatus.REGISTERED.value

    @property
    def is_suspended(self) -> bool:
        return self.status_token == CapabilityRegistryStatus.SUSPENDED.value

    def to_payload(self) -> dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "account_id": self.account_id,
            "proposal_id": self.proposal_id,
            "decision_id": self.decision_id,
            "status_token": self.status_token,
            "target_surface_token": self.target_surface,
            "scope_token": self.scope,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "requested_permissions_json": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "approved_permissions_json": [
                permission.to_payload()
                for permission in self.approved_permissions
            ],
            "manifest_snapshot_json": self.manifest_snapshot.to_payload(),
            "registration_metadata_json": dict(self.registration_metadata),
            "provenance_class_token": self.provenance_class_token,
            "provenance_json": dict(self.provenance_json),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> CapabilityRegistryEntry:
        data = dict(payload)
        manifest_payload = data.get("manifest_snapshot_json")
        if not isinstance(manifest_payload, Mapping):
            manifest_payload = data.get("manifest_json")
        if not isinstance(manifest_payload, Mapping):
            manifest_payload = {
                "target_surface": data.get("target_surface_token"),
                "scope": data.get("scope_token"),
                "source_thread_id": data.get("source_thread_id"),
                "source_message_id": data.get("source_message_id"),
                "project_id": data.get("project_id"),
                "profile_id": data.get("profile_id"),
                "requested_permissions": data.get("requested_permissions_json")
                or [],
                "declared_dependencies": [],
            }
        requested_permissions = tuple(
            ExtensionRequestedPermission.from_payload(item)
            for item in data.get("requested_permissions_json") or []
        )
        approved_permissions = tuple(
            ExtensionRequestedPermission.from_payload(item)
            for item in data.get("approved_permissions_json") or []
        )
        registration_metadata = data.get("registration_metadata_json")
        provenance_json = data.get("provenance_json")
        return cls(
            registry_id=data.get("registry_id") or data.get("id") or "",
            account_id=data.get("account_id") or "",
            proposal_id=data.get("proposal_id") or "",
            decision_id=data.get("decision_id") or "",
            status_token=data.get("status_token") or data.get("status") or "",
            manifest_snapshot=ExtensionProposalManifest.from_payload(
                manifest_payload
            ),
            requested_permissions=requested_permissions,
            approved_permissions=approved_permissions,
            provenance_class_token=(
                data.get("provenance_class_token")
                or data.get("provenance_class")
                or CapabilityEntryProvenanceClass.PROPOSAL_APPROVAL.value
            ),
            registration_metadata=_clean_mapping(registration_metadata)
            if isinstance(registration_metadata, Mapping)
            else {},
            provenance_json=_clean_mapping(provenance_json)
            if isinstance(provenance_json, Mapping)
            else {},
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass(frozen=True, slots=True)
class ExtensionInstallBinding:
    """Request contract for binding an approved registry entry to a scope."""

    account_id: str
    registry_entry_id: str
    scope_token: str
    project_id: int | None = None
    profile_id: str | None = None
    account_scope_target_id: str | None = None
    bind_reason: str | None = None
    bind_notes: dict[str, Any] = field(default_factory=dict)
    bind_metadata: dict[str, Any] = field(default_factory=dict)
    source_thread_id: int | None = None
    source_message_id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        object.__setattr__(
            self,
            "registry_entry_id",
            _clean_optional_text(self.registry_entry_id) or "",
        )
        object.__setattr__(
            self,
            "scope_token",
            normalize_extension_install_binding_scope(self.scope_token),
        )
        object.__setattr__(
            self, "bind_reason", _clean_optional_text(self.bind_reason)
        )
        object.__setattr__(self, "bind_notes", _clean_mapping(self.bind_notes))
        object.__setattr__(
            self, "bind_metadata", _clean_mapping(self.bind_metadata)
        )
        object.__setattr__(
            self,
            "profile_id",
            _clean_optional_text(self.profile_id),
        )
        object.__setattr__(
            self,
            "account_scope_target_id",
            _clean_optional_text(self.account_scope_target_id),
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.registry_entry_id:
            raise ValueError("registry_entry_id is required")
        if self.scope_token == ExtensionInstallBindingScope.PROJECT.value:
            if self.project_id is None:
                raise ValueError("project_id is required for project bindings")
            if (
                self.profile_id is not None
                or self.account_scope_target_id is not None
            ):
                raise ValueError(
                    "project bindings must not carry profile or account targets"
                )
        elif self.scope_token == ExtensionInstallBindingScope.PROFILE.value:
            if not self.profile_id:
                raise ValueError("profile_id is required for profile bindings")
            if (
                self.project_id is not None
                or self.account_scope_target_id is not None
            ):
                raise ValueError(
                    "profile bindings must not carry project or account targets"
                )
        elif self.scope_token == ExtensionInstallBindingScope.ACCOUNT.value:
            if not self.account_scope_target_id:
                raise ValueError(
                    "account_scope_target_id is required for account bindings"
                )
            if self.project_id is not None or self.profile_id is not None:
                raise ValueError(
                    "account bindings must not carry project or profile targets"
                )

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "registry_entry_id": self.registry_entry_id,
            "scope_token": self.scope_token,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "account_scope_target_id": self.account_scope_target_id,
            "bind_reason": self.bind_reason,
            "bind_notes_json": dict(self.bind_notes),
            "bind_metadata_json": dict(self.bind_metadata),
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> ExtensionInstallBinding:
        data = dict(payload or {})
        bind_notes = data.get("bind_notes_json")
        bind_metadata = data.get("bind_metadata_json")
        return cls(
            account_id=data.get("account_id") or "",
            registry_entry_id=data.get("registry_entry_id") or "",
            scope_token=data.get("scope_token") or "",
            project_id=data.get("project_id"),
            profile_id=data.get("profile_id"),
            account_scope_target_id=data.get("account_scope_target_id"),
            bind_reason=data.get("bind_reason"),
            bind_notes=_clean_mapping(bind_notes)
            if isinstance(bind_notes, Mapping)
            else {},
            bind_metadata=_clean_mapping(bind_metadata)
            if isinstance(bind_metadata, Mapping)
            else {},
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
        )


@dataclass(frozen=True, slots=True)
class ExtensionBindingRecord:
    """Durable install-binding row with explicit scope and lineage."""

    binding_id: str
    account_id: str
    registry_entry_id: str
    proposal_id: str
    scope_token: str
    project_id: int | None = None
    profile_id: str | None = None
    account_scope_target_id: str | None = None
    binding_status_token: str = "active"
    bind_reason: str | None = None
    bind_notes: dict[str, Any] = field(default_factory=dict)
    bind_metadata: dict[str, Any] = field(default_factory=dict)
    unbind_metadata: dict[str, Any] = field(default_factory=dict)
    source_thread_id: int | None = None
    source_message_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    unbound_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "binding_id", _clean_optional_text(self.binding_id) or ""
        )
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        object.__setattr__(
            self,
            "registry_entry_id",
            _clean_optional_text(self.registry_entry_id) or "",
        )
        object.__setattr__(
            self, "proposal_id", _clean_optional_text(self.proposal_id) or ""
        )
        object.__setattr__(
            self,
            "scope_token",
            normalize_extension_install_binding_scope(self.scope_token),
        )
        object.__setattr__(
            self,
            "binding_status_token",
            normalize_extension_install_binding_status(
                self.binding_status_token
            ),
        )
        object.__setattr__(
            self, "bind_reason", _clean_optional_text(self.bind_reason)
        )
        object.__setattr__(self, "bind_notes", _clean_mapping(self.bind_notes))
        object.__setattr__(
            self, "bind_metadata", _clean_mapping(self.bind_metadata)
        )
        object.__setattr__(
            self, "unbind_metadata", _clean_mapping(self.unbind_metadata)
        )
        object.__setattr__(
            self,
            "profile_id",
            _clean_optional_text(self.profile_id),
        )
        object.__setattr__(
            self,
            "account_scope_target_id",
            _clean_optional_text(self.account_scope_target_id),
        )
        if not self.binding_id:
            raise ValueError("binding_id is required")
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.registry_entry_id:
            raise ValueError("registry_entry_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if self.scope_token == "project_scoped":
            if self.project_id is None:
                raise ValueError("project_id is required for project bindings")
            if (
                self.profile_id is not None
                or self.account_scope_target_id is not None
            ):
                raise ValueError(
                    "project bindings must not carry profile or account targets"
                )
        elif self.scope_token == "profile_scoped":
            if not self.profile_id:
                raise ValueError("profile_id is required for profile bindings")
            if (
                self.project_id is not None
                or self.account_scope_target_id is not None
            ):
                raise ValueError(
                    "profile bindings must not carry project or account targets"
                )
        elif self.scope_token == "account_scoped":
            if not self.account_scope_target_id:
                raise ValueError(
                    "account_scope_target_id is required for account bindings"
                )
            if self.project_id is not None or self.profile_id is not None:
                raise ValueError(
                    "account bindings must not carry project or profile targets"
                )

    @property
    def is_active(self) -> bool:
        return (
            self.binding_status_token
            == ExtensionInstallBindingStatus.ACTIVE.value
        )

    @property
    def is_unbound(self) -> bool:
        return (
            self.binding_status_token
            == ExtensionInstallBindingStatus.UNBOUND.value
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "account_id": self.account_id,
            "registry_entry_id": self.registry_entry_id,
            "proposal_id": self.proposal_id,
            "scope_token": self.scope_token,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "account_scope_target_id": self.account_scope_target_id,
            "binding_status_token": self.binding_status_token,
            "bind_reason": self.bind_reason,
            "bind_notes_json": dict(self.bind_notes),
            "bind_metadata_json": dict(self.bind_metadata),
            "unbind_metadata_json": dict(self.unbind_metadata),
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "unbound_at": self.unbound_at,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ExtensionBindingRecord:
        data = dict(payload)
        bind_notes = data.get("bind_notes_json")
        bind_metadata = data.get("bind_metadata_json")
        unbind_metadata = data.get("unbind_metadata_json")
        return cls(
            binding_id=data.get("binding_id") or data.get("id") or "",
            account_id=data.get("account_id") or "",
            registry_entry_id=data.get("registry_entry_id") or "",
            proposal_id=data.get("proposal_id") or "",
            scope_token=data.get("scope_token") or "",
            project_id=data.get("project_id"),
            profile_id=data.get("profile_id"),
            account_scope_target_id=data.get("account_scope_target_id"),
            binding_status_token=(
                data.get("binding_status_token")
                or data.get("status_token")
                or data.get("status")
                or ""
            ),
            bind_reason=data.get("bind_reason"),
            bind_notes=_clean_mapping(bind_notes)
            if isinstance(bind_notes, Mapping)
            else {},
            bind_metadata=_clean_mapping(bind_metadata)
            if isinstance(bind_metadata, Mapping)
            else {},
            unbind_metadata=_clean_mapping(unbind_metadata)
            if isinstance(unbind_metadata, Mapping)
            else {},
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            unbound_at=data.get("unbound_at"),
        )


@dataclass(frozen=True, slots=True)
class EffectiveCapabilityRecord:
    """Read-time effective capability snapshot for one registry entry."""

    registry_entry: CapabilityRegistryEntry
    binding: ExtensionBindingRecord
    query_project_id: int | None = None
    query_profile_id: str | None = None

    def __post_init__(self) -> None:
        query_project_id = (
            None
            if self.query_project_id is None
            else int(self.query_project_id)
        )
        object.__setattr__(
            self,
            "query_project_id",
            query_project_id,
        )
        object.__setattr__(
            self,
            "query_profile_id",
            _clean_optional_text(self.query_profile_id),
        )
        if self.registry_entry.account_id != self.binding.account_id:
            raise ValueError(
                "registry entry and binding account ids must match"
            )
        if self.registry_entry.registry_id != self.binding.registry_entry_id:
            raise ValueError("registry entry and binding ids must match")
        if self.registry_entry.proposal_id != self.binding.proposal_id:
            raise ValueError(
                "registry entry and binding proposal ids must match"
            )
        if not self.registry_entry.is_registered:
            raise ValueError(
                "effective capabilities require registered entries"
            )
        if not self.binding.is_active:
            raise ValueError("effective capabilities require active bindings")

    @property
    def account_id(self) -> str:
        return self.registry_entry.account_id

    @property
    def registry_entry_id(self) -> str:
        return self.registry_entry.registry_id

    @property
    def proposal_id(self) -> str:
        return self.registry_entry.proposal_id

    @property
    def decision_id(self) -> str:
        return self.registry_entry.decision_id

    @property
    def binding_id(self) -> str:
        return self.binding.binding_id

    @property
    def target_surface_token(self) -> str:
        return self.registry_entry.target_surface

    @property
    def registry_status_token(self) -> str:
        return self.registry_entry.status_token

    @property
    def binding_status_token(self) -> str:
        return self.binding.binding_status_token

    @property
    def binding_scope_token(self) -> str:
        return self.binding.scope_token

    @property
    def manifest_snapshot(self) -> ExtensionProposalManifest:
        return self.registry_entry.manifest_snapshot

    @property
    def requested_permissions(self) -> tuple[ExtensionRequestedPermission, ...]:
        return self.registry_entry.requested_permissions

    @property
    def approved_permissions(self) -> tuple[ExtensionRequestedPermission, ...]:
        return self.registry_entry.approved_permissions

    @property
    def provenance_class_token(self) -> str:
        return self.registry_entry.provenance_class_token

    @property
    def provenance_json(self) -> dict[str, Any]:
        return dict(self.registry_entry.provenance_json)

    @property
    def registration_metadata(self) -> dict[str, Any]:
        return dict(self.registry_entry.registration_metadata)

    @property
    def bind_notes(self) -> dict[str, Any]:
        return dict(self.binding.bind_notes)

    @property
    def bind_metadata(self) -> dict[str, Any]:
        return dict(self.binding.bind_metadata)

    @property
    def unbind_metadata(self) -> dict[str, Any]:
        return dict(self.binding.unbind_metadata)

    @property
    def source_thread_id(self) -> int | None:
        return self.binding.source_thread_id

    @property
    def source_message_id(self) -> int | None:
        return self.binding.source_message_id

    @property
    def project_id(self) -> int | None:
        return self.binding.project_id

    @property
    def profile_id(self) -> str | None:
        return self.binding.profile_id

    @property
    def account_scope_target_id(self) -> str | None:
        return self.binding.account_scope_target_id

    @property
    def resolved_from_scope_token(self) -> str:
        return self.binding.scope_token

    def to_payload(self) -> dict[str, Any]:
        return {
            "registry_entry": self.registry_entry.to_payload(),
            "binding": self.binding.to_payload(),
            "query_project_id": self.query_project_id,
            "query_profile_id": self.query_profile_id,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> EffectiveCapabilityRecord:
        data = dict(payload)
        registry_payload = data.get("registry_entry")
        binding_payload = data.get("binding")
        if not isinstance(registry_payload, Mapping):
            registry_payload = {}
        if not isinstance(binding_payload, Mapping):
            binding_payload = {}
        return cls(
            registry_entry=CapabilityRegistryEntry.from_payload(
                registry_payload
            ),
            binding=ExtensionBindingRecord.from_payload(binding_payload),
            query_project_id=data.get("query_project_id"),
            query_profile_id=data.get("query_profile_id"),
        )


@dataclass(frozen=True, slots=True)
class EffectiveCapabilitySnapshot:
    """Read-time collection of effective capabilities for a context."""

    account_id: str
    records: tuple[EffectiveCapabilityRecord, ...] = ()
    project_id: int | None = None
    profile_id: str | None = None
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        project_id = None if self.project_id is None else int(self.project_id)
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        object.__setattr__(self, "project_id", project_id)
        object.__setattr__(
            self,
            "profile_id",
            _clean_optional_text(self.profile_id),
        )
        object.__setattr__(self, "records", tuple(self.records or ()))
        if not self.account_id:
            raise ValueError("account_id is required")

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "resolved_at": self.resolved_at,
            "records": [record.to_payload() for record in self.records],
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> EffectiveCapabilitySnapshot:
        data = dict(payload)
        return cls(
            account_id=data.get("account_id") or "",
            project_id=data.get("project_id"),
            profile_id=data.get("profile_id"),
            records=tuple(
                EffectiveCapabilityRecord.from_payload(item)
                for item in data.get("records") or []
            ),
            resolved_at=data.get("resolved_at"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityActivationRequest:
    """Read-time request for capability activation."""

    account_id: str
    requested_command_id: str
    activation_context_token: str
    project_id: int | None = None
    profile_id: str | None = None
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    request_metadata: dict[str, Any] = field(default_factory=dict)
    source_thread_id: int | None = None
    source_message_id: int | None = None
    requested_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        object.__setattr__(
            self,
            "requested_command_id",
            _clean_optional_text(self.requested_command_id) or "",
        )
        object.__setattr__(
            self,
            "activation_context_token",
            normalize_capability_activation_context_token(
                self.activation_context_token
            ),
        )
        object.__setattr__(
            self,
            "project_id",
            None if self.project_id is None else int(self.project_id),
        )
        object.__setattr__(
            self, "profile_id", _clean_optional_text(self.profile_id)
        )
        object.__setattr__(
            self,
            "requested_permissions",
            tuple(self.requested_permissions or ()),
        )
        object.__setattr__(
            self, "request_metadata", _clean_mapping(self.request_metadata)
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.requested_command_id:
            raise ValueError("requested_command_id is required")
        if (
            self.activation_context_token
            == CapabilityActivationContextToken.OWNER_ONLY.value
        ):
            if self.project_id is not None or self.profile_id is not None:
                raise ValueError(
                    "owner-only activation must not carry project or profile context"
                )
        elif (
            self.activation_context_token
            == CapabilityActivationContextToken.OWNER_PROJECT.value
        ):
            if self.project_id is None or self.profile_id is not None:
                raise ValueError(
                    "owner+project activation requires project context and excludes profile context"
                )
        elif (
            self.activation_context_token
            == CapabilityActivationContextToken.OWNER_PROFILE.value
        ):
            if self.profile_id is None or self.project_id is not None:
                raise ValueError(
                    "owner+profile activation requires profile context and excludes project context"
                )
        elif (
            self.activation_context_token
            == CapabilityActivationContextToken.OWNER_PROJECT_PROFILE.value
        ):
            if self.project_id is None or self.profile_id is None:
                raise ValueError(
                    "owner+project+profile activation requires both project and profile context"
                )

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "requested_command_id": self.requested_command_id,
            "activation_context_token": self.activation_context_token,
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "requested_permissions_json": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "request_metadata_json": dict(self.request_metadata),
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "requested_at": self.requested_at,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> CapabilityActivationRequest:
        data = dict(payload)
        return cls(
            account_id=data.get("account_id") or "",
            requested_command_id=data.get("requested_command_id")
            or data.get("command_id")
            or "",
            activation_context_token=data.get("activation_context_token") or "",
            project_id=data.get("project_id"),
            profile_id=data.get("profile_id"),
            requested_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in data.get("requested_permissions_json") or []
            ),
            request_metadata=_clean_mapping(
                data.get("request_metadata_json")
                if isinstance(data.get("request_metadata_json"), Mapping)
                else {}
            ),
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
            requested_at=data.get("requested_at"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityActivationMatch:
    """A unique effective capability that matched a requested command."""

    account_id: str
    registry_entry_id: str
    proposal_id: str
    binding_id: str
    resolved_from_scope_token: str
    manifest_snapshot: ExtensionProposalManifest
    approved_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    exposed_command: CapabilityExposedCommand | None = None
    matched_alias: str | None = None
    source_thread_id: int | None = None
    source_message_id: int | None = None
    target_surface_token: str | None = None
    match_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        object.__setattr__(
            self,
            "registry_entry_id",
            _clean_optional_text(self.registry_entry_id) or "",
        )
        object.__setattr__(
            self, "proposal_id", _clean_optional_text(self.proposal_id) or ""
        )
        object.__setattr__(
            self, "binding_id", _clean_optional_text(self.binding_id) or ""
        )
        object.__setattr__(
            self,
            "resolved_from_scope_token",
            normalize_extension_install_binding_scope(
                self.resolved_from_scope_token
            ),
        )
        object.__setattr__(
            self,
            "approved_permissions",
            tuple(self.approved_permissions or ()),
        )
        object.__setattr__(
            self,
            "matched_alias",
            _clean_optional_text(self.matched_alias),
        )
        object.__setattr__(
            self,
            "target_surface_token",
            _clean_optional_text(self.target_surface_token)
            or self.manifest_snapshot.target_surface,
        )
        object.__setattr__(
            self, "match_metadata", _clean_mapping(self.match_metadata)
        )
        if self.exposed_command is None:
            raise ValueError("exposed_command is required")
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.registry_entry_id:
            raise ValueError("registry_entry_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.binding_id:
            raise ValueError("binding_id is required")

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "registry_entry_id": self.registry_entry_id,
            "proposal_id": self.proposal_id,
            "binding_id": self.binding_id,
            "resolved_from_scope_token": self.resolved_from_scope_token,
            "manifest_snapshot_json": self.manifest_snapshot.to_payload(),
            "approved_permissions_json": [
                permission.to_payload()
                for permission in self.approved_permissions
            ],
            "exposed_command_json": self.exposed_command.to_payload(),
            "matched_alias": self.matched_alias,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "target_surface_token": self.target_surface_token,
            "match_metadata_json": dict(self.match_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> CapabilityActivationMatch:
        data = dict(payload)
        manifest_payload = data.get("manifest_snapshot_json")
        if not isinstance(manifest_payload, Mapping):
            manifest_payload = {}
        exposed_payload = data.get("exposed_command_json")
        if not isinstance(exposed_payload, Mapping):
            exposed_payload = {}
        match_metadata = data.get("match_metadata_json")
        return cls(
            account_id=data.get("account_id") or "",
            registry_entry_id=data.get("registry_entry_id") or "",
            proposal_id=data.get("proposal_id") or "",
            binding_id=data.get("binding_id") or "",
            resolved_from_scope_token=data.get("resolved_from_scope_token")
            or "",
            manifest_snapshot=ExtensionProposalManifest.from_payload(
                manifest_payload
            ),
            approved_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in data.get("approved_permissions_json") or []
            ),
            exposed_command=CapabilityExposedCommand.from_payload(
                exposed_payload
            )
            if exposed_payload
            else None,
            matched_alias=data.get("matched_alias"),
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
            target_surface_token=data.get("target_surface_token"),
            match_metadata=_clean_mapping(match_metadata)
            if isinstance(match_metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class CapabilityActivationConflictDetail:
    """Structured conflict metadata for a denied activation."""

    conflict_class_token: str
    requested_command_id: str
    candidate_matches: tuple[CapabilityActivationMatch, ...] = ()
    summary: str | None = None
    conflict_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "conflict_class_token",
            normalize_capability_activation_conflict_class_token(
                self.conflict_class_token
            ),
        )
        object.__setattr__(
            self,
            "requested_command_id",
            _clean_optional_text(self.requested_command_id) or "",
        )
        object.__setattr__(
            self,
            "candidate_matches",
            tuple(self.candidate_matches or ()),
        )
        object.__setattr__(self, "summary", _clean_optional_text(self.summary))
        object.__setattr__(
            self,
            "conflict_metadata",
            _clean_mapping(self.conflict_metadata),
        )
        if not self.requested_command_id:
            raise ValueError("requested_command_id is required")

    def to_payload(self) -> dict[str, Any]:
        return {
            "conflict_class_token": self.conflict_class_token,
            "requested_command_id": self.requested_command_id,
            "candidate_matches_json": [
                match.to_payload() for match in self.candidate_matches
            ],
            "summary": self.summary,
            "conflict_metadata_json": dict(self.conflict_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> CapabilityActivationConflictDetail:
        data = dict(payload)
        conflict_metadata = data.get("conflict_metadata_json")
        return cls(
            conflict_class_token=data.get("conflict_class_token") or "",
            requested_command_id=data.get("requested_command_id") or "",
            candidate_matches=tuple(
                CapabilityActivationMatch.from_payload(item)
                for item in data.get("candidate_matches_json") or []
            ),
            summary=data.get("summary"),
            conflict_metadata=_clean_mapping(conflict_metadata)
            if isinstance(conflict_metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class CapabilityDispatchEnvelope:
    """Command-bus-shaped envelope prepared for later invocation."""

    owner_account_id: str
    requested_command_id: str
    command_id: str
    activation_context_token: str
    proposal_id: str
    registry_entry_id: str
    binding_id: str
    resolved_from_scope_token: str
    manifest_snapshot: ExtensionProposalManifest
    approved_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    dispatch_source_token: str = (
        CapabilityDispatchSourceToken.CAPABILITY_ACTIVATION.value
    )
    matched_alias: str | None = None
    actor_kind: str = "human"
    actor_id: str | None = None
    actor_session_id: str | None = None
    delegated_by: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None
    invoke_version: str = INVOKE_VERSION
    envelope_metadata: dict[str, Any] = field(default_factory=dict)
    requested_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "owner_account_id",
            _clean_optional_text(self.owner_account_id) or "",
        )
        object.__setattr__(
            self,
            "requested_command_id",
            _clean_optional_text(self.requested_command_id) or "",
        )
        object.__setattr__(
            self, "command_id", _clean_optional_text(self.command_id) or ""
        )
        object.__setattr__(
            self,
            "activation_context_token",
            normalize_capability_activation_context_token(
                self.activation_context_token
            ),
        )
        object.__setattr__(
            self, "proposal_id", _clean_optional_text(self.proposal_id) or ""
        )
        object.__setattr__(
            self,
            "registry_entry_id",
            _clean_optional_text(self.registry_entry_id) or "",
        )
        object.__setattr__(
            self, "binding_id", _clean_optional_text(self.binding_id) or ""
        )
        object.__setattr__(
            self,
            "resolved_from_scope_token",
            normalize_extension_install_binding_scope(
                self.resolved_from_scope_token
            ),
        )
        object.__setattr__(
            self,
            "approved_permissions",
            tuple(self.approved_permissions or ()),
        )
        object.__setattr__(
            self,
            "requested_permissions",
            tuple(self.requested_permissions or ()),
        )
        object.__setattr__(
            self,
            "dispatch_source_token",
            normalize_capability_dispatch_source_token(
                self.dispatch_source_token
            ),
        )
        object.__setattr__(
            self, "matched_alias", _clean_optional_text(self.matched_alias)
        )
        object.__setattr__(
            self, "actor_kind", _clean_optional_text(self.actor_kind) or "human"
        )
        object.__setattr__(
            self,
            "actor_id",
            _clean_optional_text(self.actor_id) or self.owner_account_id,
        )
        object.__setattr__(
            self,
            "actor_session_id",
            _clean_optional_text(self.actor_session_id),
        )
        object.__setattr__(
            self, "delegated_by", _clean_optional_text(self.delegated_by)
        )
        object.__setattr__(self, "arguments", _clean_mapping(self.arguments))
        object.__setattr__(
            self,
            "idempotency_key",
            _clean_optional_text(self.idempotency_key),
        )
        object.__setattr__(
            self,
            "invoke_version",
            _clean_optional_text(self.invoke_version) or INVOKE_VERSION,
        )
        object.__setattr__(
            self,
            "envelope_metadata",
            _clean_mapping(self.envelope_metadata),
        )
        if not self.owner_account_id:
            raise ValueError("owner_account_id is required")
        if not self.requested_command_id:
            raise ValueError("requested_command_id is required")
        if not self.command_id:
            raise ValueError("command_id is required")

    def to_payload(self) -> dict[str, Any]:
        return {
            "owner_account_id": self.owner_account_id,
            "requested_command_id": self.requested_command_id,
            "command_id": self.command_id,
            "activation_context_token": self.activation_context_token,
            "proposal_id": self.proposal_id,
            "registry_entry_id": self.registry_entry_id,
            "binding_id": self.binding_id,
            "resolved_from_scope_token": self.resolved_from_scope_token,
            "manifest_snapshot_json": self.manifest_snapshot.to_payload(),
            "approved_permissions_json": [
                permission.to_payload()
                for permission in self.approved_permissions
            ],
            "requested_permissions_json": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "dispatch_source_token": self.dispatch_source_token,
            "matched_alias": self.matched_alias,
            "actor_kind": self.actor_kind,
            "actor_id": self.actor_id,
            "actor_session_id": self.actor_session_id,
            "delegated_by": self.delegated_by,
            "arguments_json": dict(self.arguments),
            "idempotency_key": self.idempotency_key,
            "invoke_version": self.invoke_version,
            "envelope_metadata_json": dict(self.envelope_metadata),
            "requested_at": self.requested_at,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> CapabilityDispatchEnvelope:
        data = dict(payload)
        manifest_payload = data.get("manifest_snapshot_json")
        if not isinstance(manifest_payload, Mapping):
            manifest_payload = {}
        envelope_metadata = data.get("envelope_metadata_json")
        arguments = data.get("arguments_json")
        return cls(
            owner_account_id=data.get("owner_account_id") or "",
            requested_command_id=data.get("requested_command_id") or "",
            command_id=data.get("command_id") or "",
            activation_context_token=data.get("activation_context_token") or "",
            proposal_id=data.get("proposal_id") or "",
            registry_entry_id=data.get("registry_entry_id") or "",
            binding_id=data.get("binding_id") or "",
            resolved_from_scope_token=data.get("resolved_from_scope_token")
            or "",
            manifest_snapshot=ExtensionProposalManifest.from_payload(
                manifest_payload
            ),
            approved_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in data.get("approved_permissions_json") or []
            ),
            requested_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in data.get("requested_permissions_json") or []
            ),
            dispatch_source_token=data.get("dispatch_source_token") or "",
            matched_alias=data.get("matched_alias"),
            actor_kind=data.get("actor_kind") or "human",
            actor_id=data.get("actor_id"),
            actor_session_id=data.get("actor_session_id"),
            delegated_by=data.get("delegated_by"),
            arguments=_clean_mapping(arguments)
            if isinstance(arguments, Mapping)
            else {},
            idempotency_key=data.get("idempotency_key"),
            invoke_version=data.get("invoke_version") or INVOKE_VERSION,
            envelope_metadata=_clean_mapping(envelope_metadata)
            if isinstance(envelope_metadata, Mapping)
            else {},
            requested_at=data.get("requested_at"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityActivationDecision:
    """Outcome for a read-time activation decision."""

    request: CapabilityActivationRequest
    outcome_token: str
    candidate_matches: tuple[CapabilityActivationMatch, ...] = ()
    conflict_details: tuple[CapabilityActivationConflictDetail, ...] = ()
    denial_reason_token: str | None = None
    conflict_class_token: str | None = None
    dispatch_envelope: CapabilityDispatchEnvelope | None = None
    evaluated_at: datetime | None = None
    decision_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "outcome_token",
            normalize_capability_activation_outcome_token(self.outcome_token),
        )
        object.__setattr__(
            self,
            "candidate_matches",
            tuple(self.candidate_matches or ()),
        )
        object.__setattr__(
            self,
            "conflict_details",
            tuple(self.conflict_details or ()),
        )
        object.__setattr__(
            self,
            "denial_reason_token",
            (
                normalize_capability_activation_deny_reason_token(
                    self.denial_reason_token
                )
                if self.denial_reason_token is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "conflict_class_token",
            (
                normalize_capability_activation_conflict_class_token(
                    self.conflict_class_token
                )
                if self.conflict_class_token is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "decision_metadata",
            _clean_mapping(self.decision_metadata),
        )
        if self.outcome_token == CapabilityActivationOutcomeToken.ALLOWED.value:
            if self.dispatch_envelope is None:
                raise ValueError(
                    "allowed activation requires a dispatch envelope"
                )
            if self.denial_reason_token is not None:
                raise ValueError(
                    "allowed activation must not carry a denial reason"
                )
            if self.conflict_class_token is not None:
                raise ValueError(
                    "allowed activation must not carry conflict metadata"
                )
            if self.conflict_details:
                raise ValueError(
                    "allowed activation must not carry conflict details"
                )
            if len(self.candidate_matches) != 1:
                raise ValueError(
                    "allowed activation requires one matched capability"
                )
        elif (
            self.outcome_token == CapabilityActivationOutcomeToken.DENIED.value
        ):
            if self.dispatch_envelope is not None:
                raise ValueError(
                    "denied activation must not carry a dispatch envelope"
                )
            if self.denial_reason_token is None:
                raise ValueError("denied activation requires a denial reason")
            if self.conflict_class_token is not None:
                raise ValueError(
                    "denied activation must not carry conflict class metadata"
                )
            if self.conflict_details:
                raise ValueError(
                    "denied activation must not carry conflict details"
                )
        elif (
            self.outcome_token
            == CapabilityActivationOutcomeToken.CONFLICT.value
        ):
            if self.dispatch_envelope is not None:
                raise ValueError(
                    "conflict activation must not carry a dispatch envelope"
                )
            if self.conflict_class_token is None:
                raise ValueError(
                    "conflict activation requires a conflict class"
                )
            if not self.conflict_details:
                raise ValueError(
                    "conflict activation requires conflict details"
                )
            if self.denial_reason_token is not None:
                raise ValueError(
                    "conflict activation must not carry a denial reason"
                )

    @property
    def is_allowed(self) -> bool:
        return (
            self.outcome_token == CapabilityActivationOutcomeToken.ALLOWED.value
        )

    @property
    def is_denied(self) -> bool:
        return (
            self.outcome_token == CapabilityActivationOutcomeToken.DENIED.value
        )

    @property
    def is_conflict(self) -> bool:
        return (
            self.outcome_token
            == CapabilityActivationOutcomeToken.CONFLICT.value
        )

    @property
    def selected_match(self) -> CapabilityActivationMatch | None:
        return self.candidate_matches[0] if self.candidate_matches else None

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_json": self.request.to_payload(),
            "outcome_token": self.outcome_token,
            "candidate_matches_json": [
                match.to_payload() for match in self.candidate_matches
            ],
            "conflict_details_json": [
                detail.to_payload() for detail in self.conflict_details
            ],
            "denial_reason_token": self.denial_reason_token,
            "conflict_class_token": self.conflict_class_token,
            "dispatch_envelope_json": (
                self.dispatch_envelope.to_payload()
                if self.dispatch_envelope is not None
                else None
            ),
            "evaluated_at": self.evaluated_at,
            "decision_metadata_json": dict(self.decision_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any]
    ) -> CapabilityActivationDecision:
        data = dict(payload)
        request_payload = data.get("request_json")
        if not isinstance(request_payload, Mapping):
            request_payload = {}
        envelope_payload = data.get("dispatch_envelope_json")
        if not isinstance(envelope_payload, Mapping):
            envelope_payload = None
        return cls(
            request=CapabilityActivationRequest.from_payload(request_payload),
            outcome_token=data.get("outcome_token") or "",
            candidate_matches=tuple(
                CapabilityActivationMatch.from_payload(item)
                for item in data.get("candidate_matches_json") or []
            ),
            conflict_details=tuple(
                CapabilityActivationConflictDetail.from_payload(item)
                for item in data.get("conflict_details_json") or []
            ),
            denial_reason_token=data.get("denial_reason_token"),
            conflict_class_token=data.get("conflict_class_token"),
            dispatch_envelope=(
                CapabilityDispatchEnvelope.from_payload(envelope_payload)
                if envelope_payload is not None
                else None
            ),
            evaluated_at=data.get("evaluated_at"),
            decision_metadata=_clean_mapping(
                data.get("decision_metadata_json")
                if isinstance(data.get("decision_metadata_json"), Mapping)
                else {}
            ),
        )


__all__ = [
    "MANIFEST_VERSION",
    "ExtensionRequestedPermission",
    "ExtensionDeclaredDependency",
    "ExtensionRollbackMetadata",
    "ExtensionTestEvidenceMetadata",
    "CapabilityExposedCommand",
    "ExtensionProposalManifest",
    "ExtensionProposalRecord",
    "InstallGateDecisionRecord",
    "CapabilityRegistryEntry",
    "ExtensionInstallBinding",
    "ExtensionBindingRecord",
    "EffectiveCapabilityRecord",
    "EffectiveCapabilitySnapshot",
    "CapabilityActivationRequest",
    "CapabilityActivationMatch",
    "CapabilityActivationConflictDetail",
    "CapabilityDispatchEnvelope",
    "CapabilityActivationDecision",
]
