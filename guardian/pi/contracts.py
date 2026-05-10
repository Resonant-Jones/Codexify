"""Typed contracts for the Pi invocation boundary.

This module is intentionally dependency-light and only models contracts plus
payload round-tripping. It does not execute adapters or providers.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from guardian.pi.tokens import (
    PiHarnessResultClass,
    PiInvocationEnvelopeStatus,
    PiInvocationReceiptStatus,
    PiInvocationValidationOutcome,
    PiProviderLaneClass,
    PiValidationFailureReason,
    normalize_pi_validation_outcome,
)


def _clean_text(value: object | None) -> str:
    return str(value or "").strip()


def _clean_optional_text(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _clean_text_tuple(values: Sequence[object] | None) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(str(value).strip() for value in values if str(value).strip())


def _clean_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        return {}
    return {str(key): copy.deepcopy(item) for key, item in value.items()}


def _payload_from_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return dict(value)


def _coerce_permission(
    value: object,
) -> PiPermissionGrant:
    if isinstance(value, PiPermissionGrant):
        return value
    if isinstance(value, Mapping):
        return PiPermissionGrant.from_payload(value)
    return PiPermissionGrant(permission=value)


def _coerce_permission_list(
    value: Sequence[Any] | None,
) -> tuple[PiPermissionGrant, ...]:
    if not value:
        return ()
    return tuple(_coerce_permission(item) for item in value)


def _coerce_boundary(
    value: PiGuardianBoundary | Mapping[str, Any] | None,
    *,
    fallback_account_id: str | None = None,
) -> PiGuardianBoundary:
    if isinstance(value, PiGuardianBoundary):
        return value
    if isinstance(value, Mapping):
        return PiGuardianBoundary.from_payload(value)
    return PiGuardianBoundary(owner_account_id=fallback_account_id or "")


def _coerce_lane(
    value: PiProviderLane | Mapping[str, Any] | str | None,
) -> PiProviderLane:
    if isinstance(value, PiProviderLane):
        return value
    if isinstance(value, Mapping):
        return PiProviderLane.from_payload(value)
    return PiProviderLane(provider_lane_class=str(value or ""))


def _coerce_linkage(
    value: PiCommandBusLinkage | Mapping[str, Any] | None,
) -> PiCommandBusLinkage | None:
    if value is None:
        return None
    if isinstance(value, PiCommandBusLinkage):
        return value
    if isinstance(value, Mapping):
        return PiCommandBusLinkage.from_payload(value)
    return PiCommandBusLinkage(command_run_id=str(value))


def _coerce_artifact(
    value: PiInvocationArtifact | Mapping[str, Any] | None,
) -> PiInvocationArtifact | None:
    if value is None:
        return None
    if isinstance(value, PiInvocationArtifact):
        return value
    if isinstance(value, Mapping):
        return PiInvocationArtifact.from_payload(value)
    return PiInvocationArtifact(artifact_id=str(value), artifact_ref=str(value))


@dataclass(frozen=True, slots=True)
class PiGuardianBoundary:
    owner_account_id: str
    request_policy_owner: str = "guardian"
    transcript_lineage_owner: str = "guardian"
    provenance_owner: str = "guardian"
    command_authority_owner: str = "guardian"
    result_return_owner: str = "guardian"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "owner_account_id", _clean_text(self.owner_account_id)
        )
        object.__setattr__(
            self, "request_policy_owner", _clean_text(self.request_policy_owner)
        )
        object.__setattr__(
            self,
            "transcript_lineage_owner",
            _clean_text(self.transcript_lineage_owner),
        )
        object.__setattr__(
            self, "provenance_owner", _clean_text(self.provenance_owner)
        )
        object.__setattr__(
            self,
            "command_authority_owner",
            _clean_text(self.command_authority_owner),
        )
        object.__setattr__(
            self, "result_return_owner", _clean_text(self.result_return_owner)
        )
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "owner_account_id": self.owner_account_id,
            "request_policy_owner": self.request_policy_owner,
            "transcript_lineage_owner": self.transcript_lineage_owner,
            "provenance_owner": self.provenance_owner,
            "command_authority_owner": self.command_authority_owner,
            "result_return_owner": self.result_return_owner,
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> PiGuardianBoundary:
        data = _payload_from_mapping(payload)
        return cls(
            owner_account_id=data.get("owner_account_id")
            or data.get("account_id")
            or "",
            request_policy_owner=data.get("request_policy_owner", "guardian"),
            transcript_lineage_owner=data.get(
                "transcript_lineage_owner", "guardian"
            ),
            provenance_owner=data.get("provenance_owner", "guardian"),
            command_authority_owner=data.get(
                "command_authority_owner", "guardian"
            ),
            result_return_owner=data.get("result_return_owner", "guardian"),
            metadata=_clean_mapping(data.get("metadata")),
        )


@dataclass(frozen=True, slots=True)
class PiPermissionGrant:
    permission: str
    resource: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "permission", _clean_text(self.permission))
        object.__setattr__(
            self, "resource", _clean_optional_text(self.resource)
        )
        object.__setattr__(self, "reason", _clean_optional_text(self.reason))
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "permission": self.permission,
            "resource": self.resource,
            "reason": self.reason,
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> PiPermissionGrant:
        data = _payload_from_mapping(payload)
        return cls(
            permission=data.get("permission") or data.get("key") or "",
            resource=data.get("resource"),
            reason=data.get("reason"),
            metadata=_clean_mapping(data.get("metadata")),
        )


@dataclass(frozen=True, slots=True)
class PiProviderLane:
    provider_lane_class: str
    provider_name: str | None = None
    model_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "provider_lane_class", _clean_text(self.provider_lane_class)
        )
        object.__setattr__(
            self, "provider_name", _clean_optional_text(self.provider_name)
        )
        object.__setattr__(
            self, "model_id", _clean_optional_text(self.model_id)
        )
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider_lane_class": self.provider_lane_class,
            "provider_name": self.provider_name,
            "model_id": self.model_id,
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> PiProviderLane:
        data = _payload_from_mapping(payload)
        return cls(
            provider_lane_class=data.get("provider_lane_class")
            or data.get("lane_class")
            or "",
            provider_name=data.get("provider_name"),
            model_id=data.get("model_id"),
            metadata=_clean_mapping(data.get("metadata")),
        )


@dataclass(frozen=True, slots=True)
class PiCommandBusLinkage:
    command_run_id: str
    command_request_id: str | None = None
    dispatch_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "command_run_id", _clean_text(self.command_run_id)
        )
        object.__setattr__(
            self,
            "command_request_id",
            _clean_optional_text(self.command_request_id),
        )
        object.__setattr__(
            self, "dispatch_id", _clean_optional_text(self.dispatch_id)
        )
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "command_run_id": self.command_run_id,
            "command_request_id": self.command_request_id,
            "dispatch_id": self.dispatch_id,
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> PiCommandBusLinkage:
        data = _payload_from_mapping(payload)
        return cls(
            command_run_id=data.get("command_run_id")
            or data.get("run_id")
            or "",
            command_request_id=data.get("command_request_id"),
            dispatch_id=data.get("dispatch_id"),
            metadata=_clean_mapping(data.get("metadata")),
        )


@dataclass(frozen=True, slots=True)
class PiInvocationArtifact:
    artifact_id: str
    artifact_ref: str
    artifact_class: str | None = None
    artifact_type: str | None = None
    uri: str | None = None
    digest: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _clean_text(self.artifact_id))
        artifact_ref = _clean_optional_text(self.artifact_ref)
        artifact_class = _clean_optional_text(self.artifact_class)
        artifact_type = _clean_optional_text(self.artifact_type)
        if artifact_ref is None:
            artifact_ref = (
                artifact_class
                or artifact_type
                or _clean_optional_text(self.uri)
            )
        if artifact_class is None:
            artifact_class = artifact_type
        if artifact_type is None:
            artifact_type = artifact_class
        object.__setattr__(self, "artifact_ref", _clean_text(artifact_ref))
        object.__setattr__(self, "artifact_class", artifact_class)
        object.__setattr__(self, "artifact_type", artifact_type)
        object.__setattr__(self, "uri", _clean_optional_text(self.uri))
        object.__setattr__(self, "digest", _clean_optional_text(self.digest))
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_ref": self.artifact_ref,
            "artifact_class": self.artifact_class,
            "artifact_type": self.artifact_type,
            "uri": self.uri,
            "digest": self.digest,
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> PiInvocationArtifact:
        data = _payload_from_mapping(payload)
        return cls(
            artifact_id=data.get("artifact_id") or data.get("id") or "",
            artifact_ref=data.get("artifact_ref")
            or data.get("reference")
            or "",
            artifact_class=data.get("artifact_class") or data.get("class"),
            artifact_type=data.get("artifact_type") or data.get("type"),
            uri=data.get("uri"),
            digest=data.get("digest"),
            metadata=_clean_mapping(data.get("metadata")),
        )


@dataclass(frozen=True, slots=True)
class PiInvocationEnvelope:
    guardian_boundary: PiGuardianBoundary | Mapping[str, Any]
    source_thread_id: str
    source_message_id: str
    invocation_id: str
    harness_id: str
    harness_version: str
    provider_lane: PiProviderLane | Mapping[str, Any] | str
    requested_permissions: tuple[PiPermissionGrant, ...] = field(
        default_factory=tuple
    )
    granted_permissions: tuple[PiPermissionGrant, ...] = field(
        default_factory=tuple
    )
    authored_request_id: str | None = None
    attempt_id: str | None = None
    execution_attempt_id: str | None = None
    owner_account_id: str = ""
    command_bus_linkage: PiCommandBusLinkage | Mapping[str, Any] | None = None
    status: str = PiInvocationEnvelopeStatus.PREPARED.value
    validation_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        boundary = _coerce_boundary(
            self.guardian_boundary, fallback_account_id=self.owner_account_id
        )
        object.__setattr__(self, "guardian_boundary", boundary)
        object.__setattr__(
            self, "owner_account_id", _clean_text(boundary.owner_account_id)
        )
        object.__setattr__(
            self, "source_thread_id", _clean_text(self.source_thread_id)
        )
        object.__setattr__(
            self, "source_message_id", _clean_text(self.source_message_id)
        )
        object.__setattr__(
            self, "invocation_id", _clean_text(self.invocation_id)
        )
        object.__setattr__(self, "harness_id", _clean_text(self.harness_id))
        object.__setattr__(
            self, "harness_version", _clean_text(self.harness_version)
        )
        object.__setattr__(
            self, "provider_lane", _coerce_lane(self.provider_lane)
        )
        object.__setattr__(
            self,
            "requested_permissions",
            _coerce_permission_list(self.requested_permissions),
        )
        object.__setattr__(
            self,
            "granted_permissions",
            _coerce_permission_list(self.granted_permissions),
        )
        object.__setattr__(
            self,
            "authored_request_id",
            _clean_optional_text(self.authored_request_id),
        )
        attempt_id = _clean_optional_text(self.attempt_id)
        execution_attempt_id = _clean_optional_text(self.execution_attempt_id)
        if attempt_id is None:
            attempt_id = execution_attempt_id
        if execution_attempt_id is None:
            execution_attempt_id = attempt_id
        object.__setattr__(self, "attempt_id", attempt_id)
        object.__setattr__(self, "execution_attempt_id", execution_attempt_id)
        object.__setattr__(
            self,
            "command_bus_linkage",
            _coerce_linkage(self.command_bus_linkage),
        )
        object.__setattr__(self, "status", _clean_text(self.status))
        object.__setattr__(
            self,
            "validation_metadata",
            _clean_mapping(self.validation_metadata),
        )

    @property
    def provider_lane_metadata(self) -> dict[str, Any]:
        return self.provider_lane.metadata

    def to_payload(self) -> dict[str, Any]:
        return {
            "owner_account_id": self.owner_account_id,
            "guardian_boundary": self.guardian_boundary.to_payload(),
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "authored_request_id": self.authored_request_id,
            "attempt_id": self.attempt_id,
            "execution_attempt_id": self.execution_attempt_id,
            "invocation_id": self.invocation_id,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "provider_lane": self.provider_lane.to_payload(),
            "requested_permissions": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "granted_permissions": [
                permission.to_payload()
                for permission in self.granted_permissions
            ],
            "command_bus_linkage": (
                self.command_bus_linkage.to_payload()
                if self.command_bus_linkage is not None
                else None
            ),
            "status": self.status,
            "validation_metadata": copy.deepcopy(self.validation_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> PiInvocationEnvelope:
        data = _payload_from_mapping(payload)
        boundary = data.get("guardian_boundary")
        if boundary is None:
            boundary = {
                "owner_account_id": data.get("owner_account_id")
                or data.get("account_id")
                or ""
            }
        return cls(
            guardian_boundary=boundary,
            source_thread_id=data.get("source_thread_id") or "",
            source_message_id=data.get("source_message_id") or "",
            authored_request_id=data.get("authored_request_id"),
            attempt_id=data.get("attempt_id"),
            execution_attempt_id=data.get("execution_attempt_id"),
            owner_account_id=data.get("owner_account_id")
            or data.get("account_id")
            or "",
            invocation_id=data.get("invocation_id") or "",
            harness_id=data.get("harness_id") or "",
            harness_version=data.get("harness_version") or "",
            provider_lane=data.get("provider_lane") or "",
            requested_permissions=_coerce_permission_list(
                data.get("requested_permissions")
            ),
            granted_permissions=_coerce_permission_list(
                data.get("granted_permissions")
            ),
            command_bus_linkage=data.get("command_bus_linkage"),
            status=data.get("status")
            or PiInvocationEnvelopeStatus.PREPARED.value,
            validation_metadata=_clean_mapping(data.get("validation_metadata")),
        )


@dataclass(frozen=True, slots=True)
class PiInvocationReceipt:
    receipt_id: str
    guardian_boundary: PiGuardianBoundary | Mapping[str, Any]
    source_thread_id: str
    source_message_id: str
    invocation_id: str
    harness_id: str
    harness_version: str
    provider_lane: PiProviderLane | Mapping[str, Any] | str
    requested_permissions: tuple[PiPermissionGrant, ...] = field(
        default_factory=tuple
    )
    granted_permissions: tuple[PiPermissionGrant, ...] = field(
        default_factory=tuple
    )
    authored_request_id: str | None = None
    attempt_id: str | None = None
    execution_attempt_id: str | None = None
    owner_account_id: str = ""
    command_bus_linkage: PiCommandBusLinkage | Mapping[str, Any] | None = None
    result_artifact_ref: str | None = None
    receipt_status: str = PiInvocationReceiptStatus.ISSUED.value
    validation_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        boundary = _coerce_boundary(
            self.guardian_boundary, fallback_account_id=self.owner_account_id
        )
        object.__setattr__(self, "guardian_boundary", boundary)
        object.__setattr__(
            self, "owner_account_id", _clean_text(boundary.owner_account_id)
        )
        object.__setattr__(self, "receipt_id", _clean_text(self.receipt_id))
        object.__setattr__(
            self, "source_thread_id", _clean_text(self.source_thread_id)
        )
        object.__setattr__(
            self, "source_message_id", _clean_text(self.source_message_id)
        )
        object.__setattr__(
            self, "invocation_id", _clean_text(self.invocation_id)
        )
        object.__setattr__(self, "harness_id", _clean_text(self.harness_id))
        object.__setattr__(
            self, "harness_version", _clean_text(self.harness_version)
        )
        object.__setattr__(
            self, "provider_lane", _coerce_lane(self.provider_lane)
        )
        object.__setattr__(
            self,
            "requested_permissions",
            _coerce_permission_list(self.requested_permissions),
        )
        object.__setattr__(
            self,
            "granted_permissions",
            _coerce_permission_list(self.granted_permissions),
        )
        object.__setattr__(
            self,
            "authored_request_id",
            _clean_optional_text(self.authored_request_id),
        )
        attempt_id = _clean_optional_text(self.attempt_id)
        execution_attempt_id = _clean_optional_text(self.execution_attempt_id)
        if attempt_id is None:
            attempt_id = execution_attempt_id
        if execution_attempt_id is None:
            execution_attempt_id = attempt_id
        object.__setattr__(self, "attempt_id", attempt_id)
        object.__setattr__(self, "execution_attempt_id", execution_attempt_id)
        object.__setattr__(
            self,
            "command_bus_linkage",
            _coerce_linkage(self.command_bus_linkage),
        )
        object.__setattr__(
            self,
            "result_artifact_ref",
            _clean_optional_text(self.result_artifact_ref),
        )
        object.__setattr__(
            self, "receipt_status", _clean_text(self.receipt_status)
        )
        object.__setattr__(
            self,
            "validation_metadata",
            _clean_mapping(self.validation_metadata),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "owner_account_id": self.owner_account_id,
            "guardian_boundary": self.guardian_boundary.to_payload(),
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "authored_request_id": self.authored_request_id,
            "attempt_id": self.attempt_id,
            "execution_attempt_id": self.execution_attempt_id,
            "invocation_id": self.invocation_id,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "provider_lane": self.provider_lane.to_payload(),
            "requested_permissions": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "granted_permissions": [
                permission.to_payload()
                for permission in self.granted_permissions
            ],
            "command_bus_linkage": (
                self.command_bus_linkage.to_payload()
                if self.command_bus_linkage is not None
                else None
            ),
            "result_artifact_ref": self.result_artifact_ref,
            "receipt_status": self.receipt_status,
            "validation_metadata": copy.deepcopy(self.validation_metadata),
        }

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> PiInvocationReceipt:
        data = _payload_from_mapping(payload)
        boundary = data.get("guardian_boundary")
        if boundary is None:
            boundary = {
                "owner_account_id": data.get("owner_account_id")
                or data.get("owner")
                or ""
            }
        return cls(
            receipt_id=data.get("receipt_id") or data.get("id") or "",
            owner_account_id=data.get("owner_account_id")
            or data.get("owner")
            or "",
            guardian_boundary=boundary,
            source_thread_id=data.get("source_thread_id") or "",
            source_message_id=data.get("source_message_id") or "",
            authored_request_id=data.get("authored_request_id"),
            attempt_id=data.get("attempt_id"),
            execution_attempt_id=data.get("execution_attempt_id"),
            invocation_id=data.get("invocation_id") or "",
            harness_id=data.get("harness_id") or "",
            harness_version=data.get("harness_version") or "",
            provider_lane=data.get("provider_lane") or "",
            requested_permissions=_coerce_permission_list(
                data.get("requested_permissions")
            ),
            granted_permissions=_coerce_permission_list(
                data.get("granted_permissions")
            ),
            command_bus_linkage=data.get("command_bus_linkage"),
            result_artifact_ref=data.get("result_artifact_ref")
            or data.get("artifact_ref"),
            receipt_status=data.get("receipt_status")
            or PiInvocationReceiptStatus.ISSUED.value,
            validation_metadata=_clean_mapping(data.get("validation_metadata")),
        )


@dataclass(frozen=True, slots=True)
class PiHarnessResult:
    harness_result_id: str
    receipt_id: str
    guardian_boundary: PiGuardianBoundary | Mapping[str, Any]
    source_thread_id: str
    source_message_id: str
    invocation_id: str
    harness_id: str
    harness_version: str
    provider_lane: PiProviderLane | Mapping[str, Any] | str
    requested_permissions: tuple[PiPermissionGrant, ...] = field(
        default_factory=tuple
    )
    granted_permissions: tuple[PiPermissionGrant, ...] = field(
        default_factory=tuple
    )
    artifact: PiInvocationArtifact | Mapping[str, Any] | None = None
    authored_request_id: str | None = None
    attempt_id: str | None = None
    execution_attempt_id: str | None = None
    owner_account_id: str = ""
    command_bus_linkage: PiCommandBusLinkage | Mapping[str, Any] | None = None
    result_class: str = PiHarnessResultClass.SUCCESS.value
    failure_classification: str | None = None
    validation_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        boundary = _coerce_boundary(
            self.guardian_boundary, fallback_account_id=self.owner_account_id
        )
        object.__setattr__(self, "guardian_boundary", boundary)
        object.__setattr__(
            self, "owner_account_id", _clean_text(boundary.owner_account_id)
        )
        object.__setattr__(
            self, "harness_result_id", _clean_text(self.harness_result_id)
        )
        object.__setattr__(self, "receipt_id", _clean_text(self.receipt_id))
        object.__setattr__(
            self, "source_thread_id", _clean_text(self.source_thread_id)
        )
        object.__setattr__(
            self, "source_message_id", _clean_text(self.source_message_id)
        )
        object.__setattr__(
            self, "invocation_id", _clean_text(self.invocation_id)
        )
        object.__setattr__(self, "harness_id", _clean_text(self.harness_id))
        object.__setattr__(
            self, "harness_version", _clean_text(self.harness_version)
        )
        object.__setattr__(
            self, "provider_lane", _coerce_lane(self.provider_lane)
        )
        object.__setattr__(
            self,
            "requested_permissions",
            _coerce_permission_list(self.requested_permissions),
        )
        object.__setattr__(
            self,
            "granted_permissions",
            _coerce_permission_list(self.granted_permissions),
        )
        object.__setattr__(self, "artifact", _coerce_artifact(self.artifact))
        object.__setattr__(
            self,
            "authored_request_id",
            _clean_optional_text(self.authored_request_id),
        )
        attempt_id = _clean_optional_text(self.attempt_id)
        execution_attempt_id = _clean_optional_text(self.execution_attempt_id)
        if attempt_id is None:
            attempt_id = execution_attempt_id
        if execution_attempt_id is None:
            execution_attempt_id = attempt_id
        object.__setattr__(self, "attempt_id", attempt_id)
        object.__setattr__(self, "execution_attempt_id", execution_attempt_id)
        object.__setattr__(
            self,
            "command_bus_linkage",
            _coerce_linkage(self.command_bus_linkage),
        )
        object.__setattr__(self, "result_class", _clean_text(self.result_class))
        object.__setattr__(
            self,
            "failure_classification",
            _clean_optional_text(self.failure_classification),
        )
        object.__setattr__(
            self,
            "validation_metadata",
            _clean_mapping(self.validation_metadata),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "harness_result_id": self.harness_result_id,
            "receipt_id": self.receipt_id,
            "owner_account_id": self.owner_account_id,
            "guardian_boundary": self.guardian_boundary.to_payload(),
            "source_thread_id": self.source_thread_id,
            "source_message_id": self.source_message_id,
            "authored_request_id": self.authored_request_id,
            "attempt_id": self.attempt_id,
            "execution_attempt_id": self.execution_attempt_id,
            "invocation_id": self.invocation_id,
            "harness_id": self.harness_id,
            "harness_version": self.harness_version,
            "provider_lane": self.provider_lane.to_payload(),
            "requested_permissions": [
                permission.to_payload()
                for permission in self.requested_permissions
            ],
            "granted_permissions": [
                permission.to_payload()
                for permission in self.granted_permissions
            ],
            "artifact": self.artifact.to_payload() if self.artifact else None,
            "command_bus_linkage": (
                self.command_bus_linkage.to_payload()
                if self.command_bus_linkage is not None
                else None
            ),
            "result_class": self.result_class,
            "failure_classification": self.failure_classification,
            "validation_metadata": copy.deepcopy(self.validation_metadata),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | None) -> PiHarnessResult:
        data = _payload_from_mapping(payload)
        boundary = data.get("guardian_boundary")
        if boundary is None:
            boundary = {
                "owner_account_id": data.get("owner_account_id")
                or data.get("owner")
                or ""
            }
        return cls(
            harness_result_id=data.get("harness_result_id")
            or data.get("id")
            or "",
            receipt_id=data.get("receipt_id") or "",
            owner_account_id=data.get("owner_account_id")
            or data.get("owner")
            or "",
            guardian_boundary=boundary,
            source_thread_id=data.get("source_thread_id") or "",
            source_message_id=data.get("source_message_id") or "",
            authored_request_id=data.get("authored_request_id"),
            attempt_id=data.get("attempt_id"),
            execution_attempt_id=data.get("execution_attempt_id"),
            invocation_id=data.get("invocation_id") or "",
            harness_id=data.get("harness_id") or "",
            harness_version=data.get("harness_version") or "",
            provider_lane=data.get("provider_lane") or "",
            requested_permissions=_coerce_permission_list(
                data.get("requested_permissions")
            ),
            granted_permissions=_coerce_permission_list(
                data.get("granted_permissions")
            ),
            artifact=data.get("artifact"),
            command_bus_linkage=data.get("command_bus_linkage"),
            result_class=data.get("result_class")
            or PiHarnessResultClass.SUCCESS.value,
            failure_classification=data.get("failure_classification"),
            validation_metadata=_clean_mapping(data.get("validation_metadata")),
        )


class PiInvocationValidationResult:
    """Structured validation outcome for a Pi contract check."""

    def __init__(
        self,
        *,
        outcome: str | None = None,
        failure_reason: str | None = None,
        message: str | None = None,
        validation_outcome: str | None = None,
        failure_reasons: Sequence[str] | None = None,
        validation_metadata: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        resolved_outcome = (
            validation_outcome
            or outcome
            or PiInvocationValidationOutcome.FAILED_CLOSED.value
        )
        self.validation_outcome = normalize_pi_validation_outcome(
            resolved_outcome
        )
        reasons: list[str] = []
        if failure_reasons:
            reasons.extend(
                str(reason).strip()
                for reason in failure_reasons
                if str(reason).strip()
            )
        if failure_reason:
            reason = str(failure_reason).strip()
            if reason:
                reasons.append(reason)
        self.failure_reasons = tuple(dict.fromkeys(reasons))
        self.validation_metadata = _clean_mapping(
            validation_metadata or metadata
        )
        self.message = _clean_optional_text(message)

    @property
    def outcome(self) -> str:
        return self.validation_outcome

    @property
    def failure_reason(self) -> str | None:
        return (
            self.failure_reasons[0] if len(self.failure_reasons) == 1 else None
        )

    @property
    def metadata(self) -> dict[str, Any]:
        return self.validation_metadata

    @property
    def ok(self) -> bool:
        return (
            self.validation_outcome == PiInvocationValidationOutcome.VALID.value
        )

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "outcome": self.validation_outcome,
            "validation_outcome": self.validation_outcome,
            "failure_reason": self.failure_reason,
            "failure_reasons": list(self.failure_reasons),
            "message": self.message,
            "validation_metadata": copy.deepcopy(self.validation_metadata),
            "metadata": copy.deepcopy(self.validation_metadata),
        }
        return payload

    @classmethod
    def from_payload(
        cls, payload: Mapping[str, Any] | None
    ) -> PiInvocationValidationResult:
        data = _payload_from_mapping(payload)
        return cls(
            outcome=data.get("outcome"),
            failure_reason=data.get("failure_reason"),
            message=data.get("message"),
            validation_outcome=data.get("validation_outcome"),
            failure_reasons=data.get("failure_reasons"),
            validation_metadata=data.get("validation_metadata")
            or data.get("metadata"),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PiInvocationValidationResult):
            return NotImplemented
        return self.to_payload() == other.to_payload()

    def __repr__(self) -> str:
        return (
            "PiInvocationValidationResult("
            f"validation_outcome={self.validation_outcome!r}, "
            f"failure_reasons={self.failure_reasons!r}, "
            f"message={self.message!r})"
        )


__all__ = [
    "PiGuardianBoundary",
    "PiPermissionGrant",
    "PiProviderLane",
    "PiCommandBusLinkage",
    "PiInvocationArtifact",
    "PiInvocationEnvelope",
    "PiInvocationReceipt",
    "PiHarnessResult",
    "PiInvocationValidationResult",
    "PiHarnessResultClass",
    "PiInvocationEnvelopeStatus",
    "PiInvocationReceiptStatus",
    "PiInvocationValidationOutcome",
    "PiProviderLaneClass",
    "PiValidationFailureReason",
]
