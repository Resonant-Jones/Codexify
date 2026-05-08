"""Typed contracts for extension persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence

from guardian.command_bus.contracts import (
    CapabilityManualDispatchResult as CommandBusManualDispatchResult,
)
from guardian.command_bus.contracts import (
    CommandBusInvokeResult,
    InvokeArguments,
    InvokeRequest,
)
from guardian.extensions.tokens import (
    CapabilityActivationConflictClassToken,
    CapabilityActivationContextToken,
    CapabilityActivationDenyReasonToken,
    CapabilityActivationOutcomeToken,
    CapabilityAssistantReentryFailureReason,
    CapabilityAssistantReentryOutcome,
    CapabilityDispatchSourceToken,
    CapabilityEntryProvenanceClass,
    CapabilityManualDispatchDenyReasonToken,
    CapabilityManualDispatchIdempotencyClassToken,
    CapabilityManualDispatchOutcomeToken,
    CapabilityManualDispatchSourceToken,
    CapabilityRegistryStatus,
    CapabilityReinjectionResultShape,
    CapabilityReinjectionSource,
    CapabilityResultReinjectionOutcome,
    ExtensionInstallBindingScope,
    ExtensionInstallBindingStatus,
    InstallGateDecisionToken,
    normalize_capability_activation_conflict_class_token,
    normalize_capability_activation_context_token,
    normalize_capability_activation_deny_reason_token,
    normalize_capability_activation_outcome_token,
    normalize_capability_assistant_reentry_failure_reason,
    normalize_capability_assistant_reentry_outcome,
    normalize_capability_dispatch_source_token,
    normalize_capability_entry_provenance_class,
    normalize_capability_manual_dispatch_deny_reason_token,
    normalize_capability_manual_dispatch_idempotency_class_token,
    normalize_capability_manual_dispatch_outcome_token,
    normalize_capability_manual_dispatch_source_token,
    normalize_capability_registry_status,
    normalize_capability_reinjection_failure_reason,
    normalize_capability_reinjection_result_shape,
    normalize_capability_reinjection_source,
    normalize_capability_result_reinjection_outcome,
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
    return tuple(
        item_text for item in value if (item_text := str(item).strip())
    )


def _canonical_json_payload(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _coerce_optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid datetime value: {value!r}") from exc


def _coerce_optional_int(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _coerce_invoke_arguments(
    value: InvokeArguments | Mapping[str, Any] | None,
) -> InvokeArguments:
    if isinstance(value, InvokeArguments):
        return value
    if isinstance(value, Mapping):
        return InvokeArguments.model_validate(dict(value))
    return InvokeArguments()


def _coerce_invoke_request(
    value: InvokeRequest | Mapping[str, Any] | None,
) -> InvokeRequest | None:
    if value is None:
        return None
    if isinstance(value, InvokeRequest):
        return value
    if isinstance(value, Mapping):
        return InvokeRequest.model_validate(dict(value))
    raise ValueError("command_bus_request must be an invoke request payload")


def _coerce_command_bus_result(
    value: CommandBusInvokeResult | Mapping[str, Any] | None,
) -> CommandBusInvokeResult | None:
    if value is None:
        return None
    if isinstance(value, CommandBusInvokeResult):
        return value
    if isinstance(value, Mapping):
        return CommandBusInvokeResult.model_validate(dict(value))
    raise ValueError(
        "command_bus_result must be a command bus invoke result payload"
    )


def _permission_sort_key(
    permission: ExtensionRequestedPermission,
) -> tuple[str, str, str, str]:
    metadata_json = json.dumps(
        permission.metadata, sort_keys=True, default=str, separators=(",", ":")
    )
    return (
        permission.permission,
        permission.resource or "",
        permission.reason or "",
        metadata_json,
    )


def _normalize_permission_snapshot(
    permissions: Sequence[ExtensionRequestedPermission | Mapping[str, Any]]
    | None,
) -> tuple[ExtensionRequestedPermission, ...]:
    if permissions is None:
        return ()
    normalized: list[ExtensionRequestedPermission] = []
    for item in permissions:
        if isinstance(item, ExtensionRequestedPermission):
            normalized.append(item)
            continue
        if isinstance(item, Mapping):
            normalized.append(ExtensionRequestedPermission.from_payload(item))
            continue
        raise ValueError(
            "permissions must be extension permission records or mappings"
        )
    normalized.sort(key=_permission_sort_key)
    return tuple(normalized)


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
    """Activation request for a read-time effective capability lookup."""

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
            _coerce_optional_int(self.project_id, field_name="project_id"),
        )
        object.__setattr__(
            self, "profile_id", _clean_optional_text(self.profile_id)
        )
        object.__setattr__(
            self,
            "requested_permissions",
            _normalize_permission_snapshot(self.requested_permissions),
        )
        object.__setattr__(
            self, "request_metadata", _clean_mapping(self.request_metadata)
        )
        object.__setattr__(
            self,
            "source_thread_id",
            _coerce_optional_int(
                self.source_thread_id, field_name="source_thread_id"
            ),
        )
        object.__setattr__(
            self,
            "source_message_id",
            _coerce_optional_int(
                self.source_message_id, field_name="source_message_id"
            ),
        )
        object.__setattr__(
            self,
            "requested_at",
            _coerce_optional_datetime(self.requested_at),
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.requested_command_id:
            raise ValueError("requested_command_id is required")

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
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityActivationRequest:
        data = dict(payload or {})
        requested_permissions = data.get("requested_permissions_json")
        if requested_permissions is None:
            requested_permissions = data.get("requested_permissions") or []
        request_metadata = data.get("request_metadata_json")
        if request_metadata is None:
            request_metadata = data.get("request_metadata") or {}
        return cls(
            account_id=data.get("account_id") or "",
            requested_command_id=data.get("requested_command_id") or "",
            activation_context_token=data.get("activation_context_token") or "",
            project_id=data.get("project_id"),
            profile_id=data.get("profile_id"),
            requested_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in requested_permissions
            ),
            request_metadata=_clean_mapping(request_metadata)
            if isinstance(request_metadata, Mapping)
            else {},
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
            requested_at=data.get("requested_at"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityActivationMatch:
    """Selected effective-capability record plus the matched exposure."""

    account_id: str
    registry_entry_id: str
    proposal_id: str
    binding_id: str
    resolved_from_scope_token: str
    manifest_snapshot: ExtensionProposalManifest | Mapping[str, Any]
    approved_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    exposed_command: CapabilityExposedCommand | Mapping[str, Any] = field(
        default_factory=dict
    )
    matched_alias: str | None = None
    source_thread_id: int | None = None
    source_message_id: int | None = None
    target_surface_token: str = ""
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
            "manifest_snapshot",
            _coerce_manifest_snapshot(self.manifest_snapshot),
        )
        object.__setattr__(
            self,
            "approved_permissions",
            _normalize_permission_snapshot(self.approved_permissions),
        )
        object.__setattr__(
            self,
            "exposed_command",
            self.exposed_command
            if isinstance(self.exposed_command, CapabilityExposedCommand)
            else CapabilityExposedCommand.from_payload(self.exposed_command),
        )
        object.__setattr__(
            self, "matched_alias", _clean_optional_text(self.matched_alias)
        )
        object.__setattr__(
            self,
            "source_thread_id",
            _coerce_optional_int(
                self.source_thread_id, field_name="source_thread_id"
            ),
        )
        object.__setattr__(
            self,
            "source_message_id",
            _coerce_optional_int(
                self.source_message_id, field_name="source_message_id"
            ),
        )
        object.__setattr__(
            self,
            "target_surface_token",
            normalize_extension_target_surface(self.target_surface_token),
        )
        object.__setattr__(
            self, "match_metadata", _clean_mapping(self.match_metadata)
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.registry_entry_id:
            raise ValueError("registry_entry_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.binding_id:
            raise ValueError("binding_id is required")

    @property
    def command_id(self) -> str:
        return self.exposed_command.command_id

    @property
    def tool_aliases(self) -> tuple[str, ...]:
        return self.exposed_command.tool_aliases

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "registry_entry_id": self.registry_entry_id,
            "proposal_id": self.proposal_id,
            "binding_id": self.binding_id,
            "resolved_from_scope_token": self.resolved_from_scope_token,
            "manifest_snapshot_json": (
                self.manifest_snapshot.to_payload()
                if self.manifest_snapshot is not None
                else None
            ),
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
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityActivationMatch:
        data = dict(payload or {})
        manifest_payload = data.get("manifest_snapshot_json")
        if manifest_payload is None:
            manifest_payload = data.get("manifest_snapshot")
        exposed_command_payload = data.get("exposed_command_json")
        if exposed_command_payload is None:
            exposed_command_payload = data.get("exposed_command")
        approved_permissions = data.get("approved_permissions_json")
        if approved_permissions is None:
            approved_permissions = data.get("approved_permissions") or []
        match_metadata = data.get("match_metadata_json")
        if match_metadata is None:
            match_metadata = data.get("match_metadata") or {}
        return cls(
            account_id=data.get("account_id") or "",
            registry_entry_id=data.get("registry_entry_id") or "",
            proposal_id=data.get("proposal_id") or "",
            binding_id=data.get("binding_id") or "",
            resolved_from_scope_token=data.get("resolved_from_scope_token")
            or "",
            manifest_snapshot=manifest_payload
            if manifest_payload is not None
            else {},
            approved_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in approved_permissions
            ),
            exposed_command=(
                exposed_command_payload
                if exposed_command_payload is not None
                else {}
            ),
            matched_alias=data.get("matched_alias"),
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
            target_surface_token=data.get("target_surface_token") or "",
            match_metadata=_clean_mapping(match_metadata)
            if isinstance(match_metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class CapabilityActivationConflictDetail:
    """Conflict diagnostics for overlapping activation matches."""

    conflict_class_token: str
    requested_command_id: str
    candidate_matches: tuple[CapabilityActivationMatch, ...]
    summary: str
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
            tuple(
                item
                if isinstance(item, CapabilityActivationMatch)
                else CapabilityActivationMatch.from_payload(item)
                for item in self.candidate_matches
            ),
        )
        object.__setattr__(
            self, "summary", _clean_optional_text(self.summary) or ""
        )
        object.__setattr__(
            self, "conflict_metadata", _clean_mapping(self.conflict_metadata)
        )
        if not self.requested_command_id:
            raise ValueError("requested_command_id is required")
        if not self.summary:
            raise ValueError("summary is required")

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
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityActivationConflictDetail:
        data = dict(payload or {})
        candidate_matches = data.get("candidate_matches_json")
        if candidate_matches is None:
            candidate_matches = data.get("candidate_matches") or []
        conflict_metadata = data.get("conflict_metadata_json")
        if conflict_metadata is None:
            conflict_metadata = data.get("conflict_metadata") or {}
        return cls(
            conflict_class_token=data.get("conflict_class_token") or "",
            requested_command_id=data.get("requested_command_id") or "",
            candidate_matches=tuple(
                CapabilityActivationMatch.from_payload(item)
                for item in candidate_matches
            ),
            summary=data.get("summary") or "",
            conflict_metadata=_clean_mapping(conflict_metadata)
            if isinstance(conflict_metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class CapabilityDispatchEnvelope:
    """Read-time dispatch envelope prepared from an allowed activation."""

    owner_account_id: str
    requested_command_id: str
    command_id: str
    activation_context_token: str
    proposal_id: str
    registry_entry_id: str
    binding_id: str
    resolved_from_scope_token: str
    manifest_snapshot: ExtensionProposalManifest | Mapping[str, Any]
    approved_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    matched_alias: str | None = None
    actor_id: str = ""
    actor_session_id: str | None = None
    delegated_by: str | None = None
    arguments: InvokeArguments | Mapping[str, Any] = field(
        default_factory=InvokeArguments
    )
    requested_at: datetime | None = None
    envelope_metadata: dict[str, Any] = field(default_factory=dict)
    invoke_version: str = "1.0"
    actor_kind: str = "human"
    dispatch_source_token: str = (
        CapabilityDispatchSourceToken.CAPABILITY_ACTIVATION.value
    )
    idempotency_key: str | None = None

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
            "manifest_snapshot",
            _coerce_manifest_snapshot(self.manifest_snapshot),
        )
        object.__setattr__(
            self,
            "approved_permissions",
            _normalize_permission_snapshot(self.approved_permissions),
        )
        object.__setattr__(
            self,
            "requested_permissions",
            _normalize_permission_snapshot(self.requested_permissions),
        )
        object.__setattr__(
            self, "matched_alias", _clean_optional_text(self.matched_alias)
        )
        object.__setattr__(
            self, "actor_id", _clean_optional_text(self.actor_id) or ""
        )
        object.__setattr__(
            self,
            "actor_session_id",
            _clean_optional_text(self.actor_session_id),
        )
        object.__setattr__(
            self, "delegated_by", _clean_optional_text(self.delegated_by)
        )
        object.__setattr__(
            self, "arguments", _coerce_invoke_arguments(self.arguments)
        )
        object.__setattr__(
            self,
            "requested_at",
            _coerce_optional_datetime(self.requested_at),
        )
        object.__setattr__(
            self, "envelope_metadata", _clean_mapping(self.envelope_metadata)
        )
        object.__setattr__(
            self,
            "invoke_version",
            _clean_optional_text(self.invoke_version) or "1.0",
        )
        object.__setattr__(
            self,
            "actor_kind",
            _clean_optional_text(self.actor_kind) or "human",
        )
        object.__setattr__(
            self,
            "dispatch_source_token",
            normalize_capability_dispatch_source_token(
                self.dispatch_source_token
            ),
        )
        object.__setattr__(
            self, "idempotency_key", _clean_optional_text(self.idempotency_key)
        )
        if not self.owner_account_id:
            raise ValueError("owner_account_id is required")
        if not self.requested_command_id:
            raise ValueError("requested_command_id is required")
        if not self.command_id:
            raise ValueError("command_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.registry_entry_id:
            raise ValueError("registry_entry_id is required")
        if not self.binding_id:
            raise ValueError("binding_id is required")
        if not self.actor_id:
            raise ValueError("actor_id is required")

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
            "manifest_snapshot_json": (
                self.manifest_snapshot.to_payload()
                if self.manifest_snapshot is not None
                else None
            ),
            "approved_permissions_json": [
                permission.to_payload()
                for permission in self.approved_permissions
            ],
            "requested_permissions_json": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "matched_alias": self.matched_alias,
            "actor_id": self.actor_id,
            "actor_session_id": self.actor_session_id,
            "delegated_by": self.delegated_by,
            "arguments_json": self.arguments.model_dump(mode="json"),
            "requested_at": self.requested_at,
            "envelope_metadata_json": dict(self.envelope_metadata),
            "invoke_version": self.invoke_version,
            "actor_kind": self.actor_kind,
            "dispatch_source_token": self.dispatch_source_token,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityDispatchEnvelope:
        data = dict(payload or {})
        manifest_payload = data.get("manifest_snapshot_json")
        if manifest_payload is None:
            manifest_payload = data.get("manifest_snapshot")
        requested_permissions = data.get("requested_permissions_json")
        if requested_permissions is None:
            requested_permissions = data.get("requested_permissions") or []
        approved_permissions = data.get("approved_permissions_json")
        if approved_permissions is None:
            approved_permissions = data.get("approved_permissions") or []
        envelope_metadata = data.get("envelope_metadata_json")
        if envelope_metadata is None:
            envelope_metadata = data.get("envelope_metadata") or {}
        arguments = data.get("arguments_json")
        if arguments is None:
            arguments = data.get("arguments")
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
            manifest_snapshot=manifest_payload
            if manifest_payload is not None
            else {},
            approved_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in approved_permissions
            ),
            requested_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in requested_permissions
            ),
            matched_alias=data.get("matched_alias"),
            actor_id=data.get("actor_id") or "",
            actor_session_id=data.get("actor_session_id"),
            delegated_by=data.get("delegated_by"),
            arguments=arguments if arguments is not None else {},
            requested_at=data.get("requested_at"),
            envelope_metadata=_clean_mapping(envelope_metadata)
            if isinstance(envelope_metadata, Mapping)
            else {},
            invoke_version=data.get("invoke_version") or "1.0",
            actor_kind=data.get("actor_kind") or "human",
            dispatch_source_token=data.get("dispatch_source_token")
            or CapabilityDispatchSourceToken.CAPABILITY_ACTIVATION.value,
            idempotency_key=data.get("idempotency_key"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityActivationDecision:
    """Outcome of the read-time activation check."""

    request: CapabilityActivationRequest | Mapping[str, Any]
    outcome_token: str
    candidate_matches: tuple[CapabilityActivationMatch, ...] = ()
    denial_reason_token: str | None = None
    conflict_class_token: str | None = None
    conflict_details: tuple[CapabilityActivationConflictDetail, ...] = ()
    dispatch_envelope: CapabilityDispatchEnvelope | Mapping[
        str, Any
    ] | None = None
    evaluated_at: datetime | None = None
    decision_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request",
            self.request
            if isinstance(self.request, CapabilityActivationRequest)
            else CapabilityActivationRequest.from_payload(self.request),
        )
        object.__setattr__(
            self,
            "outcome_token",
            normalize_capability_activation_outcome_token(self.outcome_token),
        )
        object.__setattr__(
            self,
            "candidate_matches",
            tuple(
                item
                if isinstance(item, CapabilityActivationMatch)
                else CapabilityActivationMatch.from_payload(item)
                for item in self.candidate_matches
            ),
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
            "conflict_details",
            tuple(
                item
                if isinstance(item, CapabilityActivationConflictDetail)
                else CapabilityActivationConflictDetail.from_payload(item)
                for item in self.conflict_details
            ),
        )
        object.__setattr__(
            self,
            "dispatch_envelope",
            (
                self.dispatch_envelope
                if isinstance(
                    self.dispatch_envelope, CapabilityDispatchEnvelope
                )
                else CapabilityDispatchEnvelope.from_payload(
                    self.dispatch_envelope
                )
                if isinstance(self.dispatch_envelope, Mapping)
                else None
            ),
        )
        object.__setattr__(
            self,
            "evaluated_at",
            _coerce_optional_datetime(self.evaluated_at),
        )
        object.__setattr__(
            self, "decision_metadata", _clean_mapping(self.decision_metadata)
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
        if self.is_allowed and len(self.candidate_matches) == 1:
            return self.candidate_matches[0]
        return None

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_json": self.request.to_payload(),
            "outcome_token": self.outcome_token,
            "candidate_matches_json": [
                match.to_payload() for match in self.candidate_matches
            ],
            "denial_reason_token": self.denial_reason_token,
            "conflict_class_token": self.conflict_class_token,
            "conflict_details_json": [
                detail.to_payload() for detail in self.conflict_details
            ],
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
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityActivationDecision:
        data = dict(payload or {})
        request_payload = data.get("request_json")
        if request_payload is None:
            request_payload = data.get("request")
        candidate_matches = data.get("candidate_matches_json")
        if candidate_matches is None:
            candidate_matches = data.get("candidate_matches") or []
        conflict_details = data.get("conflict_details_json")
        if conflict_details is None:
            conflict_details = data.get("conflict_details") or []
        dispatch_envelope = data.get("dispatch_envelope_json")
        if dispatch_envelope is None:
            dispatch_envelope = data.get("dispatch_envelope")
        decision_metadata = data.get("decision_metadata_json")
        if decision_metadata is None:
            decision_metadata = data.get("decision_metadata") or {}
        return cls(
            request=request_payload if request_payload is not None else {},
            outcome_token=data.get("outcome_token") or "",
            candidate_matches=tuple(
                CapabilityActivationMatch.from_payload(item)
                for item in candidate_matches
            ),
            denial_reason_token=data.get("denial_reason_token"),
            conflict_class_token=data.get("conflict_class_token"),
            conflict_details=tuple(
                CapabilityActivationConflictDetail.from_payload(item)
                for item in conflict_details
            ),
            dispatch_envelope=(
                dispatch_envelope if dispatch_envelope is not None else None
            ),
            evaluated_at=data.get("evaluated_at"),
            decision_metadata=_clean_mapping(decision_metadata)
            if isinstance(decision_metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class CapabilityManualDispatchRequest:
    """Request envelope for bounded manual capability dispatch."""

    account_id: str
    requested_command_id: str
    command_arguments: InvokeArguments | Mapping[str, Any]
    project_id: int | None = None
    profile_id: str | None = None
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    request_metadata: dict[str, Any] = field(default_factory=dict)
    dispatch_envelope: CapabilityDispatchEnvelope | Mapping[
        str, Any
    ] | None = None
    invocation_source_token: str = (
        CapabilityManualDispatchSourceToken.MANUAL_CAPABILITY_DISPATCH.value
    )
    idempotency_class_token: str = (
        CapabilityManualDispatchIdempotencyClassToken.SINGLE_COMMAND_BUS_INVOCATION.value
    )
    idempotency_key: str | None = None
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
            "command_arguments",
            _coerce_invoke_arguments(self.command_arguments),
        )
        object.__setattr__(
            self,
            "project_id",
            _coerce_optional_int(self.project_id, field_name="project_id"),
        )
        object.__setattr__(
            self, "profile_id", _clean_optional_text(self.profile_id)
        )
        object.__setattr__(
            self,
            "requested_permissions",
            _normalize_permission_snapshot(self.requested_permissions),
        )
        object.__setattr__(
            self, "request_metadata", _clean_mapping(self.request_metadata)
        )
        object.__setattr__(
            self,
            "dispatch_envelope",
            (
                self.dispatch_envelope
                if isinstance(
                    self.dispatch_envelope, CapabilityDispatchEnvelope
                )
                else CapabilityDispatchEnvelope.from_payload(
                    self.dispatch_envelope
                )
                if isinstance(self.dispatch_envelope, Mapping)
                else None
            ),
        )
        object.__setattr__(
            self,
            "invocation_source_token",
            normalize_capability_manual_dispatch_source_token(
                self.invocation_source_token
            ),
        )
        object.__setattr__(
            self,
            "idempotency_class_token",
            normalize_capability_manual_dispatch_idempotency_class_token(
                self.idempotency_class_token
            ),
        )
        object.__setattr__(
            self, "idempotency_key", _clean_optional_text(self.idempotency_key)
        )
        object.__setattr__(
            self,
            "source_thread_id",
            _coerce_optional_int(
                self.source_thread_id, field_name="source_thread_id"
            ),
        )
        object.__setattr__(
            self,
            "source_message_id",
            _coerce_optional_int(
                self.source_message_id, field_name="source_message_id"
            ),
        )
        object.__setattr__(
            self,
            "requested_at",
            _coerce_optional_datetime(self.requested_at),
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.requested_command_id:
            raise ValueError("requested_command_id is required")

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "requested_command_id": self.requested_command_id,
            "command_arguments_json": self.command_arguments.model_dump(
                mode="json"
            ),
            "project_id": self.project_id,
            "profile_id": self.profile_id,
            "requested_permissions_json": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "request_metadata_json": dict(self.request_metadata),
            "dispatch_envelope_json": (
                self.dispatch_envelope.to_payload()
                if self.dispatch_envelope is not None
                else None
            ),
            "invocation_source_token": self.invocation_source_token,
            "idempotency_class_token": self.idempotency_class_token,
            "idempotency_key": self.idempotency_key,
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "requested_at": self.requested_at,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityManualDispatchRequest:
        data = dict(payload or {})
        command_arguments = data.get("command_arguments_json")
        if command_arguments is None:
            command_arguments = data.get("command_arguments")
        requested_permissions = data.get("requested_permissions_json")
        if requested_permissions is None:
            requested_permissions = data.get("requested_permissions") or []
        request_metadata = data.get("request_metadata_json")
        if request_metadata is None:
            request_metadata = data.get("request_metadata") or {}
        dispatch_envelope = data.get("dispatch_envelope_json")
        if dispatch_envelope is None:
            dispatch_envelope = data.get("dispatch_envelope")
        return cls(
            account_id=data.get("account_id") or "",
            requested_command_id=data.get("requested_command_id") or "",
            command_arguments=command_arguments
            if command_arguments is not None
            else {},
            project_id=data.get("project_id"),
            profile_id=data.get("profile_id"),
            requested_permissions=tuple(
                ExtensionRequestedPermission.from_payload(item)
                for item in requested_permissions
            ),
            request_metadata=_clean_mapping(request_metadata)
            if isinstance(request_metadata, Mapping)
            else {},
            dispatch_envelope=(
                dispatch_envelope if dispatch_envelope is not None else None
            ),
            invocation_source_token=data.get("invocation_source_token")
            or CapabilityManualDispatchSourceToken.MANUAL_CAPABILITY_DISPATCH.value,
            idempotency_class_token=data.get("idempotency_class_token")
            or CapabilityManualDispatchIdempotencyClassToken.SINGLE_COMMAND_BUS_INVOCATION.value,
            idempotency_key=data.get("idempotency_key"),
            source_thread_id=data.get("source_thread_id"),
            source_message_id=data.get("source_message_id"),
            requested_at=data.get("requested_at"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityManualDispatchResult:
    """Result of a bounded manual capability dispatch."""

    request: CapabilityManualDispatchRequest | Mapping[str, Any]
    outcome_token: str
    activation_decision: CapabilityActivationDecision | Mapping[
        str, Any
    ] | None = None
    dispatch_envelope: CapabilityDispatchEnvelope | Mapping[
        str, Any
    ] | None = None
    command_bus_request: InvokeRequest | Mapping[str, Any] | None = None
    command_bus_result: CommandBusInvokeResult | Mapping[str, Any] | None = None
    command_run_id: str | None = None
    denial_reason_token: str | None = None
    result_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request",
            self.request
            if isinstance(self.request, CapabilityManualDispatchRequest)
            else CapabilityManualDispatchRequest.from_payload(self.request),
        )
        object.__setattr__(
            self,
            "outcome_token",
            normalize_capability_manual_dispatch_outcome_token(
                self.outcome_token
            ),
        )
        object.__setattr__(
            self,
            "activation_decision",
            (
                self.activation_decision
                if isinstance(
                    self.activation_decision, CapabilityActivationDecision
                )
                else CapabilityActivationDecision.from_payload(
                    self.activation_decision
                )
                if isinstance(self.activation_decision, Mapping)
                else None
            ),
        )
        object.__setattr__(
            self,
            "dispatch_envelope",
            (
                self.dispatch_envelope
                if isinstance(
                    self.dispatch_envelope, CapabilityDispatchEnvelope
                )
                else CapabilityDispatchEnvelope.from_payload(
                    self.dispatch_envelope
                )
                if isinstance(self.dispatch_envelope, Mapping)
                else None
            ),
        )
        object.__setattr__(
            self,
            "command_bus_request",
            _coerce_invoke_request(self.command_bus_request),
        )
        object.__setattr__(
            self,
            "command_bus_result",
            _coerce_command_bus_result(self.command_bus_result),
        )
        if self.command_run_id is None and self.command_bus_result is not None:
            object.__setattr__(
                self,
                "command_run_id",
                _clean_optional_text(self.command_bus_result.run_id),
            )
        object.__setattr__(
            self, "command_run_id", _clean_optional_text(self.command_run_id)
        )
        object.__setattr__(
            self,
            "denial_reason_token",
            (
                normalize_capability_manual_dispatch_deny_reason_token(
                    self.denial_reason_token
                )
                if self.denial_reason_token is not None
                else None
            ),
        )
        object.__setattr__(
            self, "result_metadata", _clean_mapping(self.result_metadata)
        )

    @property
    def account_id(self) -> str:
        return self.request.account_id

    @property
    def requested_command_id(self) -> str:
        return self.request.requested_command_id

    @property
    def project_id(self) -> int | None:
        return self.request.project_id

    @property
    def profile_id(self) -> str | None:
        return self.request.profile_id

    @property
    def requested_permissions(self) -> tuple[ExtensionRequestedPermission, ...]:
        return self.request.requested_permissions

    @property
    def request_metadata(self) -> dict[str, Any]:
        return dict(self.request.request_metadata)

    @property
    def invocation_source_token(self) -> str:
        return self.request.invocation_source_token

    @property
    def idempotency_class_token(self) -> str:
        return self.request.idempotency_class_token

    @property
    def idempotency_key(self) -> str | None:
        return self.request.idempotency_key

    @property
    def source_thread_id(self) -> int | None:
        return self.request.source_thread_id

    @property
    def source_message_id(self) -> int | None:
        return self.request.source_message_id

    @property
    def requested_at(self) -> datetime | None:
        return self.request.requested_at

    @property
    def proposal_id(self) -> str:
        if self.activation_decision is not None:
            selected_match = self.activation_decision.selected_match
            if selected_match is not None:
                return selected_match.proposal_id
        if self.dispatch_envelope is not None:
            return self.dispatch_envelope.proposal_id
        return ""

    @property
    def registry_entry_id(self) -> str:
        if self.activation_decision is not None:
            selected_match = self.activation_decision.selected_match
            if selected_match is not None:
                return selected_match.registry_entry_id
        if self.dispatch_envelope is not None:
            return self.dispatch_envelope.registry_entry_id
        return ""

    @property
    def effective_binding_id(self) -> str:
        if self.activation_decision is not None:
            selected_match = self.activation_decision.selected_match
            if selected_match is not None:
                return selected_match.binding_id
        if self.dispatch_envelope is not None:
            return self.dispatch_envelope.binding_id
        return ""

    @property
    def resolved_from_scope_token(self) -> str:
        if self.activation_decision is not None:
            selected_match = self.activation_decision.selected_match
            if selected_match is not None:
                return selected_match.resolved_from_scope_token
        if self.dispatch_envelope is not None:
            return self.dispatch_envelope.resolved_from_scope_token
        return ""

    @property
    def command_bus_run_id(self) -> str | None:
        return self.command_run_id

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_json": self.request.to_payload(),
            "outcome_token": self.outcome_token,
            "activation_decision_json": (
                self.activation_decision.to_payload()
                if self.activation_decision is not None
                else None
            ),
            "dispatch_envelope_json": (
                self.dispatch_envelope.to_payload()
                if self.dispatch_envelope is not None
                else None
            ),
            "command_bus_request_json": (
                self.command_bus_request.model_dump(mode="json")
                if self.command_bus_request is not None
                else None
            ),
            "command_bus_result_json": (
                self.command_bus_result.model_dump(mode="json")
                if self.command_bus_result is not None
                else None
            ),
            "command_run_id": self.command_run_id,
            "denial_reason_token": self.denial_reason_token,
            "result_metadata_json": dict(self.result_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityManualDispatchResult:
        data = dict(payload or {})
        request_payload = data.get("request_json")
        if request_payload is None:
            request_payload = data.get("request")
        activation_decision = data.get("activation_decision_json")
        if activation_decision is None:
            activation_decision = data.get("activation_decision")
        dispatch_envelope = data.get("dispatch_envelope_json")
        if dispatch_envelope is None:
            dispatch_envelope = data.get("dispatch_envelope")
        command_bus_request = data.get("command_bus_request_json")
        if command_bus_request is None:
            command_bus_request = data.get("command_bus_request")
        command_bus_result = data.get("command_bus_result_json")
        if command_bus_result is None:
            command_bus_result = data.get("command_bus_result")
        result_metadata = data.get("result_metadata_json")
        if result_metadata is None:
            result_metadata = data.get("result_metadata") or {}
        return cls(
            request=request_payload if request_payload is not None else {},
            outcome_token=data.get("outcome_token") or "",
            activation_decision=activation_decision
            if activation_decision is not None
            else None,
            dispatch_envelope=dispatch_envelope
            if dispatch_envelope is not None
            else None,
            command_bus_request=command_bus_request
            if command_bus_request is not None
            else None,
            command_bus_result=command_bus_result
            if command_bus_result is not None
            else None,
            command_run_id=data.get("command_run_id"),
            denial_reason_token=data.get("denial_reason_token"),
            result_metadata=_clean_mapping(result_metadata)
            if isinstance(result_metadata, Mapping)
            else {},
        )


def _coerce_manual_dispatch_result(
    value: CommandBusManualDispatchResult | Mapping[str, Any]
) -> CommandBusManualDispatchResult:
    if isinstance(value, CommandBusManualDispatchResult):
        return value
    if isinstance(value, Mapping):
        return CommandBusManualDispatchResult.model_validate(dict(value))
    raise ValueError(
        "manual_dispatch_result must be a capability manual dispatch result"
    )


def _coerce_manifest_snapshot(
    value: ExtensionProposalManifest | Mapping[str, Any] | None,
) -> ExtensionProposalManifest | None:
    if value is None:
        return None
    if isinstance(value, ExtensionProposalManifest):
        return value
    if isinstance(value, Mapping):
        return ExtensionProposalManifest.from_payload(value)
    raise ValueError("manifest snapshot must be a manifest payload")


@dataclass(frozen=True, slots=True)
class CapabilityResultReinjectionRequest:
    """Request contract for reinjecting one manual capability dispatch result."""

    account_id: str
    manual_dispatch_result: CommandBusManualDispatchResult | Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        object.__setattr__(
            self,
            "manual_dispatch_result",
            _coerce_manual_dispatch_result(self.manual_dispatch_result),
        )

    @property
    def proposal_id(self) -> str:
        return self.manual_dispatch_result.proposal_id

    @property
    def registry_entry_id(self) -> str:
        return self.manual_dispatch_result.registry_entry_id

    @property
    def effective_binding_id(self) -> str:
        return self.manual_dispatch_result.effective_binding_id

    @property
    def resolved_from_scope_token(self) -> str:
        return self.manual_dispatch_result.resolved_from_scope_token

    @property
    def manual_dispatch_id(self) -> str:
        return self.manual_dispatch_result.manual_dispatch_id

    @property
    def command_bus_run_id(self) -> str | None:
        return self.manual_dispatch_result.command_bus_run_id

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "manual_dispatch_result_json": self.manual_dispatch_result.to_payload(),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityResultReinjectionRequest:
        data = dict(payload or {})
        manual_dispatch_payload = data.get("manual_dispatch_result_json")
        if not isinstance(manual_dispatch_payload, Mapping):
            manual_dispatch_payload = data.get("manual_dispatch_result") or {}
        return cls(
            account_id=data.get("account_id") or "",
            manual_dispatch_result=manual_dispatch_payload,
        )


@dataclass(frozen=True, slots=True)
class CapabilityReinjectedOutput:
    """Extension-facing output for one normalized manual capability dispatch."""

    account_id: str
    proposal_id: str
    registry_entry_id: str
    effective_binding_id: str
    resolved_from_scope_token: str
    manual_dispatch_id: str
    command_bus_run_id: str | None
    manifest_snapshot: ExtensionProposalManifest | Mapping[
        str, Any
    ] | None = None
    approved_permissions: tuple[
        ExtensionRequestedPermission | Mapping[str, Any], ...
    ] = ()
    reinjection_source_token: str = (
        CapabilityReinjectionSource.MANUAL_DISPATCH.value
    )
    reinjection_outcome_token: str = (
        CapabilityResultReinjectionOutcome.UNUSABLE.value
    )
    result_shape_token: str = (
        CapabilityReinjectionResultShape.FAILED_CLOSED.value
    )
    normalized_command_result_payload: dict[str, Any] | None = None
    normalized_command_failure_payload: dict[str, Any] | None = None
    reinjection_failure_reason_token: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
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
            self,
            "effective_binding_id",
            _clean_optional_text(self.effective_binding_id) or "",
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
            "manual_dispatch_id",
            _clean_optional_text(self.manual_dispatch_id) or "",
        )
        object.__setattr__(
            self,
            "command_bus_run_id",
            _clean_optional_text(self.command_bus_run_id),
        )
        object.__setattr__(
            self,
            "manifest_snapshot",
            _coerce_manifest_snapshot(self.manifest_snapshot),
        )
        object.__setattr__(
            self,
            "approved_permissions",
            _normalize_permission_snapshot(self.approved_permissions),
        )
        object.__setattr__(
            self,
            "reinjection_source_token",
            normalize_capability_reinjection_source(
                self.reinjection_source_token
            ),
        )
        object.__setattr__(
            self,
            "reinjection_outcome_token",
            normalize_capability_result_reinjection_outcome(
                self.reinjection_outcome_token
            ),
        )
        object.__setattr__(
            self,
            "result_shape_token",
            normalize_capability_reinjection_result_shape(
                self.result_shape_token
            ),
        )
        object.__setattr__(
            self,
            "reinjection_failure_reason_token",
            (
                normalize_capability_reinjection_failure_reason(
                    self.reinjection_failure_reason_token
                )
                if self.reinjection_failure_reason_token is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "normalized_command_result_payload",
            (
                _canonical_json_payload(self.normalized_command_result_payload)
                if self.normalized_command_result_payload is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "normalized_command_failure_payload",
            (
                _canonical_json_payload(self.normalized_command_failure_payload)
                if self.normalized_command_failure_payload is not None
                else None
            ),
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.registry_entry_id:
            raise ValueError("registry_entry_id is required")
        if not self.effective_binding_id:
            raise ValueError("effective_binding_id is required")
        if not self.manual_dispatch_id:
            raise ValueError("manual_dispatch_id is required")

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "proposal_id": self.proposal_id,
            "registry_entry_id": self.registry_entry_id,
            "effective_binding_id": self.effective_binding_id,
            "resolved_from_scope_token": self.resolved_from_scope_token,
            "manual_dispatch_id": self.manual_dispatch_id,
            "command_bus_run_id": self.command_bus_run_id,
            "manifest_snapshot_json": (
                self.manifest_snapshot.to_payload()
                if self.manifest_snapshot is not None
                else None
            ),
            "approved_permissions_json": [
                permission.to_payload()
                for permission in self.approved_permissions
            ],
            "reinjection_source_token": self.reinjection_source_token,
            "reinjection_outcome_token": self.reinjection_outcome_token,
            "result_shape_token": self.result_shape_token,
            "normalized_command_result_payload": (
                _canonical_json_payload(self.normalized_command_result_payload)
                if self.normalized_command_result_payload is not None
                else None
            ),
            "normalized_command_failure_payload": (
                _canonical_json_payload(self.normalized_command_failure_payload)
                if self.normalized_command_failure_payload is not None
                else None
            ),
            "reinjection_failure_reason_token": self.reinjection_failure_reason_token,
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityReinjectedOutput:
        data = dict(payload or {})
        manifest_payload = data.get("manifest_snapshot_json")
        approved_permissions = tuple(
            ExtensionRequestedPermission.from_payload(item)
            for item in data.get("approved_permissions_json") or []
        )
        return cls(
            account_id=data.get("account_id") or "",
            proposal_id=data.get("proposal_id") or "",
            registry_entry_id=data.get("registry_entry_id") or "",
            effective_binding_id=data.get("effective_binding_id") or "",
            resolved_from_scope_token=data.get("resolved_from_scope_token")
            or "",
            manual_dispatch_id=data.get("manual_dispatch_id") or "",
            command_bus_run_id=data.get("command_bus_run_id"),
            manifest_snapshot=manifest_payload
            if isinstance(manifest_payload, Mapping)
            else None,
            approved_permissions=approved_permissions,
            reinjection_source_token=(
                data.get("reinjection_source_token")
                or CapabilityReinjectionSource.MANUAL_DISPATCH.value
            ),
            reinjection_outcome_token=(
                data.get("reinjection_outcome_token")
                or CapabilityResultReinjectionOutcome.UNUSABLE.value
            ),
            result_shape_token=(
                data.get("result_shape_token")
                or CapabilityReinjectionResultShape.FAILED_CLOSED.value
            ),
            normalized_command_result_payload=data.get(
                "normalized_command_result_payload"
            ),
            normalized_command_failure_payload=data.get(
                "normalized_command_failure_payload"
            ),
            reinjection_failure_reason_token=(
                data.get("reinjection_failure_reason_token")
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityResultReinjectionResult:
    """Normalized reinjection result for one completed manual command-bus invocation."""

    request: CapabilityResultReinjectionRequest
    reinjection_outcome_token: str
    result_shape_token: str
    reinjection_source_token: str = (
        CapabilityReinjectionSource.MANUAL_DISPATCH.value
    )
    reinjection_failure_reason_token: str | None = None
    reinjected_output: CapabilityReinjectedOutput | Mapping[
        str, Any
    ] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request",
            self.request
            if isinstance(self.request, CapabilityResultReinjectionRequest)
            else CapabilityResultReinjectionRequest.from_payload(self.request),
        )
        object.__setattr__(
            self,
            "reinjection_source_token",
            normalize_capability_reinjection_source(
                self.reinjection_source_token
            ),
        )
        object.__setattr__(
            self,
            "reinjection_outcome_token",
            normalize_capability_result_reinjection_outcome(
                self.reinjection_outcome_token
            ),
        )
        object.__setattr__(
            self,
            "result_shape_token",
            normalize_capability_reinjection_result_shape(
                self.result_shape_token
            ),
        )
        object.__setattr__(
            self,
            "reinjection_failure_reason_token",
            (
                normalize_capability_reinjection_failure_reason(
                    self.reinjection_failure_reason_token
                )
                if self.reinjection_failure_reason_token is not None
                else None
            ),
        )
        if self.reinjected_output is None:
            raise ValueError("reinjected_output is required")
        object.__setattr__(
            self,
            "reinjected_output",
            self.reinjected_output
            if isinstance(self.reinjected_output, CapabilityReinjectedOutput)
            else CapabilityReinjectedOutput.from_payload(
                self.reinjected_output
            ),
        )

    @property
    def account_id(self) -> str:
        return self.request.account_id

    @property
    def proposal_id(self) -> str:
        return self.request.proposal_id

    @property
    def registry_entry_id(self) -> str:
        return self.request.registry_entry_id

    @property
    def effective_binding_id(self) -> str:
        return self.request.effective_binding_id

    @property
    def resolved_from_scope_token(self) -> str:
        return self.request.resolved_from_scope_token

    @property
    def manual_dispatch_id(self) -> str:
        return self.request.manual_dispatch_id

    @property
    def command_bus_run_id(self) -> str | None:
        return self.request.command_bus_run_id

    @property
    def manifest_snapshot(self) -> ExtensionProposalManifest | None:
        return self.reinjected_output.manifest_snapshot

    @property
    def approved_permissions(self) -> tuple[ExtensionRequestedPermission, ...]:
        return self.reinjected_output.approved_permissions

    @property
    def normalized_command_result_payload(self) -> dict[str, Any] | None:
        return self.reinjected_output.normalized_command_result_payload

    @property
    def normalized_command_failure_payload(self) -> dict[str, Any] | None:
        return self.reinjected_output.normalized_command_failure_payload

    def to_payload(self) -> dict[str, Any]:
        return {
            "request": self.request.to_payload(),
            "reinjection_outcome_token": self.reinjection_outcome_token,
            "result_shape_token": self.result_shape_token,
            "reinjection_source_token": self.reinjection_source_token,
            "reinjection_failure_reason_token": self.reinjection_failure_reason_token,
            "reinjected_output": self.reinjected_output.to_payload(),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityResultReinjectionResult:
        data = dict(payload or {})
        request_payload = data.get("request")
        output_payload = data.get("reinjected_output")
        return cls(
            request=CapabilityResultReinjectionRequest.from_payload(
                request_payload if isinstance(request_payload, Mapping) else {}
            ),
            reinjection_outcome_token=(
                data.get("reinjection_outcome_token")
                or CapabilityResultReinjectionOutcome.UNUSABLE.value
            ),
            result_shape_token=(
                data.get("result_shape_token")
                or CapabilityReinjectionResultShape.FAILED_CLOSED.value
            ),
            reinjection_source_token=(
                data.get("reinjection_source_token")
                or CapabilityReinjectionSource.MANUAL_DISPATCH.value
            ),
            reinjection_failure_reason_token=(
                data.get("reinjection_failure_reason_token")
            ),
            reinjected_output=(
                output_payload if isinstance(output_payload, Mapping) else {}
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilityAssistantReentryRequest:
    """Request contract for one-turn assistant reentry."""

    account_id: str
    reinjection_result: CapabilityResultReinjectionResult | Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        object.__setattr__(
            self,
            "reinjection_result",
            self.reinjection_result
            if isinstance(
                self.reinjection_result, CapabilityResultReinjectionResult
            )
            else CapabilityResultReinjectionResult.from_payload(
                self.reinjection_result
            ),
        )

    @property
    def proposal_id(self) -> str:
        return self.reinjection_result.proposal_id

    @property
    def registry_entry_id(self) -> str:
        return self.reinjection_result.registry_entry_id

    @property
    def effective_binding_id(self) -> str:
        return self.reinjection_result.effective_binding_id

    @property
    def resolved_from_scope_token(self) -> str:
        return self.reinjection_result.resolved_from_scope_token

    @property
    def manual_dispatch_id(self) -> str:
        return self.reinjection_result.manual_dispatch_id

    @property
    def command_bus_run_id(self) -> str | None:
        return self.reinjection_result.command_bus_run_id

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "reinjection_result_json": self.reinjection_result.to_payload(),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityAssistantReentryRequest:
        data = dict(payload or {})
        reinjection_payload = data.get("reinjection_result_json")
        if not isinstance(reinjection_payload, Mapping):
            reinjection_payload = data.get("reinjection_result") or {}
        return cls(
            account_id=data.get("account_id") or "",
            reinjection_result=reinjection_payload,
        )


@dataclass(frozen=True, slots=True)
class CapabilityAssistantContinuationPayload:
    """Bounded assistant-facing continuation payload from one reinjection result."""

    account_id: str
    proposal_id: str
    registry_entry_id: str
    effective_binding_id: str
    resolved_from_scope_token: str
    manual_dispatch_id: str
    command_bus_run_id: str | None
    requested_command_id: str | None = None
    manifest_snapshot_json: dict[str, Any] | None = None
    approved_permissions_json: list[dict[str, Any]] = field(
        default_factory=list
    )
    reentry_outcome_token: str = (
        CapabilityAssistantReentryOutcome.FAILED_CLOSED.value
    )
    reentry_failure_reason_token: str | None = None
    normalized_command_result_payload: dict[str, Any] | None = None
    normalized_command_failure_payload: dict[str, Any] | None = None
    continuation_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "account_id", _clean_optional_text(self.account_id) or ""
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
            self,
            "effective_binding_id",
            _clean_optional_text(self.effective_binding_id) or "",
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
            "manual_dispatch_id",
            _clean_optional_text(self.manual_dispatch_id) or "",
        )
        object.__setattr__(
            self,
            "command_bus_run_id",
            _clean_optional_text(self.command_bus_run_id),
        )
        object.__setattr__(
            self,
            "requested_command_id",
            _clean_optional_text(self.requested_command_id),
        )
        object.__setattr__(
            self,
            "manifest_snapshot_json",
            _clean_mapping(self.manifest_snapshot_json),
        )
        object.__setattr__(
            self,
            "approved_permissions_json",
            list(self.approved_permissions_json or []),
        )
        object.__setattr__(
            self,
            "reentry_outcome_token",
            normalize_capability_assistant_reentry_outcome(
                self.reentry_outcome_token
            ),
        )
        object.__setattr__(
            self,
            "reentry_failure_reason_token",
            (
                normalize_capability_assistant_reentry_failure_reason(
                    self.reentry_failure_reason_token
                )
                if self.reentry_failure_reason_token is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "normalized_command_result_payload",
            (
                _canonical_json_payload(self.normalized_command_result_payload)
                if self.normalized_command_result_payload is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "normalized_command_failure_payload",
            (
                _canonical_json_payload(self.normalized_command_failure_payload)
                if self.normalized_command_failure_payload is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "continuation_metadata",
            _clean_mapping(self.continuation_metadata),
        )
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.proposal_id:
            raise ValueError("proposal_id is required")
        if not self.registry_entry_id:
            raise ValueError("registry_entry_id is required")
        if not self.effective_binding_id:
            raise ValueError("effective_binding_id is required")
        if not self.manual_dispatch_id:
            raise ValueError("manual_dispatch_id is required")

    @property
    def is_success(self) -> bool:
        return (
            self.reentry_outcome_token
            == CapabilityAssistantReentryOutcome.SUCCESS.value
        )

    @property
    def is_failure(self) -> bool:
        return (
            self.reentry_outcome_token
            == CapabilityAssistantReentryOutcome.FAILURE.value
        )

    @property
    def is_failed_closed(self) -> bool:
        return (
            self.reentry_outcome_token
            == CapabilityAssistantReentryOutcome.FAILED_CLOSED.value
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "proposal_id": self.proposal_id,
            "registry_entry_id": self.registry_entry_id,
            "effective_binding_id": self.effective_binding_id,
            "resolved_from_scope_token": self.resolved_from_scope_token,
            "manual_dispatch_id": self.manual_dispatch_id,
            "command_bus_run_id": self.command_bus_run_id,
            "requested_command_id": self.requested_command_id,
            "manifest_snapshot_json": self.manifest_snapshot_json,
            "approved_permissions_json": list(self.approved_permissions_json),
            "reentry_outcome_token": self.reentry_outcome_token,
            "reentry_failure_reason_token": self.reentry_failure_reason_token,
            "normalized_command_result_payload": (
                _canonical_json_payload(self.normalized_command_result_payload)
                if self.normalized_command_result_payload is not None
                else None
            ),
            "normalized_command_failure_payload": (
                _canonical_json_payload(self.normalized_command_failure_payload)
                if self.normalized_command_failure_payload is not None
                else None
            ),
            "continuation_metadata_json": dict(self.continuation_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityAssistantContinuationPayload:
        data = dict(payload or {})
        continuation_metadata = data.get("continuation_metadata_json")
        if continuation_metadata is None:
            continuation_metadata = data.get("continuation_metadata") or {}
        return cls(
            account_id=data.get("account_id") or "",
            proposal_id=data.get("proposal_id") or "",
            registry_entry_id=data.get("registry_entry_id") or "",
            effective_binding_id=data.get("effective_binding_id") or "",
            resolved_from_scope_token=data.get("resolved_from_scope_token")
            or "",
            manual_dispatch_id=data.get("manual_dispatch_id") or "",
            command_bus_run_id=data.get("command_bus_run_id"),
            requested_command_id=data.get("requested_command_id"),
            manifest_snapshot_json=data.get("manifest_snapshot_json"),
            approved_permissions_json=(
                data.get("approved_permissions_json") or []
            ),
            reentry_outcome_token=(
                data.get("reentry_outcome_token")
                or CapabilityAssistantReentryOutcome.FAILED_CLOSED.value
            ),
            reentry_failure_reason_token=data.get(
                "reentry_failure_reason_token"
            ),
            normalized_command_result_payload=data.get(
                "normalized_command_result_payload"
            ),
            normalized_command_failure_payload=data.get(
                "normalized_command_failure_payload"
            ),
            continuation_metadata=_clean_mapping(continuation_metadata)
            if isinstance(continuation_metadata, Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class CapabilityAssistantReentryResult:
    """One-turn assistant reentry result from one completed reinjection."""

    request: CapabilityAssistantReentryRequest | Mapping[str, Any]
    reentry_outcome_token: str
    reentry_failure_reason_token: str | None = None
    continuation_payload: CapabilityAssistantContinuationPayload | Mapping[
        str, Any
    ] | None = None
    result_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request",
            self.request
            if isinstance(self.request, CapabilityAssistantReentryRequest)
            else CapabilityAssistantReentryRequest.from_payload(self.request),
        )
        object.__setattr__(
            self,
            "reentry_outcome_token",
            normalize_capability_assistant_reentry_outcome(
                self.reentry_outcome_token
            ),
        )
        object.__setattr__(
            self,
            "reentry_failure_reason_token",
            (
                normalize_capability_assistant_reentry_failure_reason(
                    self.reentry_failure_reason_token
                )
                if self.reentry_failure_reason_token is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "continuation_payload",
            (
                self.continuation_payload
                if isinstance(
                    self.continuation_payload,
                    CapabilityAssistantContinuationPayload,
                )
                else CapabilityAssistantContinuationPayload.from_payload(
                    self.continuation_payload
                )
                if isinstance(self.continuation_payload, Mapping)
                else None
            ),
        )
        object.__setattr__(
            self,
            "result_metadata",
            _clean_mapping(self.result_metadata),
        )

    @property
    def account_id(self) -> str:
        return self.request.account_id

    @property
    def proposal_id(self) -> str:
        return self.request.proposal_id

    @property
    def registry_entry_id(self) -> str:
        return self.request.registry_entry_id

    @property
    def effective_binding_id(self) -> str:
        return self.request.effective_binding_id

    @property
    def is_success(self) -> bool:
        return (
            self.reentry_outcome_token
            == CapabilityAssistantReentryOutcome.SUCCESS.value
        )

    @property
    def is_failure(self) -> bool:
        return (
            self.reentry_outcome_token
            == CapabilityAssistantReentryOutcome.FAILURE.value
        )

    @property
    def is_failed_closed(self) -> bool:
        return (
            self.reentry_outcome_token
            == CapabilityAssistantReentryOutcome.FAILED_CLOSED.value
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_json": self.request.to_payload(),
            "reentry_outcome_token": self.reentry_outcome_token,
            "reentry_failure_reason_token": self.reentry_failure_reason_token,
            "continuation_payload_json": (
                self.continuation_payload.to_payload()
                if self.continuation_payload is not None
                else None
            ),
            "result_metadata_json": dict(self.result_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> CapabilityAssistantReentryResult:
        data = dict(payload or {})
        request_payload = data.get("request_json")
        if request_payload is None:
            request_payload = data.get("request")
        continuation_payload = data.get("continuation_payload_json")
        if continuation_payload is None:
            continuation_payload = data.get("continuation_payload")
        result_metadata = data.get("result_metadata_json")
        if result_metadata is None:
            result_metadata = data.get("result_metadata") or {}
        return cls(
            request=request_payload if request_payload is not None else {},
            reentry_outcome_token=(
                data.get("reentry_outcome_token")
                or CapabilityAssistantReentryOutcome.FAILED_CLOSED.value
            ),
            reentry_failure_reason_token=data.get(
                "reentry_failure_reason_token"
            ),
            continuation_payload=(
                continuation_payload
                if continuation_payload is not None
                else None
            ),
            result_metadata=_clean_mapping(result_metadata)
            if isinstance(result_metadata, Mapping)
            else {},
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
    "CapabilityManualDispatchRequest",
    "CapabilityManualDispatchResult",
    "CapabilityResultReinjectionRequest",
    "CapabilityReinjectedOutput",
    "CapabilityResultReinjectionResult",
    "CapabilityAssistantReentryRequest",
    "CapabilityAssistantContinuationPayload",
    "CapabilityAssistantReentryResult",
]
