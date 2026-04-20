"""Typed contracts for extension proposal persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from guardian.extensions.tokens import (
    normalize_extension_proposal_scope,
    normalize_extension_proposal_status,
    normalize_extension_target_surface,
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
class ExtensionProposalManifest:
    """Manifest draft persisted for a proposed extension."""

    target_surface: str
    scope: str
    requested_permissions: tuple[ExtensionRequestedPermission, ...] = ()
    declared_dependencies: tuple[ExtensionDeclaredDependency, ...] = ()
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


__all__ = [
    "MANIFEST_VERSION",
    "ExtensionRequestedPermission",
    "ExtensionDeclaredDependency",
    "ExtensionRollbackMetadata",
    "ExtensionTestEvidenceMetadata",
    "ExtensionProposalManifest",
    "ExtensionProposalRecord",
]
