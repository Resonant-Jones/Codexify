"""Typed boundary contracts for Pi-like invocation envelopes and receipts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from guardian.pi.tokens import (
    PiHarnessResultClass,
    PiInvocationValidationOutcome,
    PiReceiptStatus,
    normalize_pi_validation_outcome,
)


def _clean_text(value: object | None) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("value is required")
    return text


def _clean_optional_text(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _clean_text_tuple(values: Sequence[object] | None) -> tuple[str, ...]:
    if not values:
        return ()
    return tuple(str(value).strip() for value in values if str(value).strip())


def _clean_mapping(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return {str(key): item for key, item in dict(value).items()}


@dataclass(frozen=True, slots=True)
class PiInvocationArtifact:
    artifact_id: str
    artifact_type: str
    uri: str | None = None
    digest: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _clean_text(self.artifact_id))
        object.__setattr__(
            self, "artifact_type", _clean_text(self.artifact_type)
        )
        object.__setattr__(self, "uri", _clean_optional_text(self.uri))
        object.__setattr__(self, "digest", _clean_optional_text(self.digest))
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> PiInvocationArtifact:
        data = dict(payload)
        return cls(
            artifact_id=data.get("artifact_id") or data.get("id") or "",
            artifact_type=data.get("artifact_type") or data.get("type") or "",
            uri=data.get("uri"),
            digest=data.get("digest"),
            metadata=data.get("metadata")
            if isinstance(data.get("metadata"), Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class PiInvocationEnvelope:
    owner_account_id: str
    source_thread_id: str
    source_message_id: str
    invocation_id: str
    harness_id: str
    harness_version: str | None = None
    authored_request_id: str | None = None
    execution_attempt_id: str | None = None
    provider_lane: str = "local"
    provider_lane_metadata: dict[str, Any] = field(default_factory=dict)
    requested_permissions: tuple[str, ...] = ()
    granted_permissions: tuple[str, ...] = ()
    command_bus_linkage: dict[str, Any] | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "owner_account_id",
            _clean_optional_text(self.owner_account_id) or "",
        )
        object.__setattr__(
            self,
            "source_thread_id",
            _clean_optional_text(self.source_thread_id) or "",
        )
        object.__setattr__(
            self,
            "source_message_id",
            _clean_optional_text(self.source_message_id) or "",
        )
        object.__setattr__(
            self,
            "invocation_id",
            _clean_optional_text(self.invocation_id) or "",
        )
        object.__setattr__(
            self, "harness_id", _clean_optional_text(self.harness_id) or ""
        )
        object.__setattr__(
            self, "harness_version", _clean_optional_text(self.harness_version)
        )
        object.__setattr__(
            self,
            "authored_request_id",
            _clean_optional_text(self.authored_request_id),
        )
        object.__setattr__(
            self,
            "execution_attempt_id",
            _clean_optional_text(self.execution_attempt_id),
        )
        object.__setattr__(
            self,
            "provider_lane",
            _clean_optional_text(self.provider_lane) or "",
        )
        object.__setattr__(
            self,
            "provider_lane_metadata",
            _clean_mapping(self.provider_lane_metadata),
        )
        object.__setattr__(
            self,
            "requested_permissions",
            _clean_text_tuple(self.requested_permissions),
        )
        object.__setattr__(
            self,
            "granted_permissions",
            _clean_text_tuple(self.granted_permissions),
        )
        linkage = self.command_bus_linkage
        if linkage is not None and not isinstance(linkage, Mapping):
            raise ValueError(
                "command_bus_linkage must be a mapping when provided"
            )
        object.__setattr__(
            self,
            "command_bus_linkage",
            _clean_mapping(linkage) if linkage else None,
        )
        object.__setattr__(self, "provenance", _clean_mapping(self.provenance))

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> PiInvocationEnvelope:
        data = dict(payload)
        return cls(
            owner_account_id=data.get("owner_account_id")
            or data.get("owner")
            or "",
            source_thread_id=data.get("source_thread_id") or "",
            source_message_id=data.get("source_message_id") or "",
            authored_request_id=data.get("authored_request_id"),
            execution_attempt_id=data.get("execution_attempt_id"),
            invocation_id=data.get("invocation_id") or "",
            harness_id=data.get("harness_id") or "",
            harness_version=data.get("harness_version"),
            provider_lane=data.get("provider_lane") or "",
            provider_lane_metadata=data.get("provider_lane_metadata")
            if isinstance(data.get("provider_lane_metadata"), Mapping)
            else {},
            requested_permissions=tuple(
                data.get("requested_permissions") or ()
            ),
            granted_permissions=tuple(data.get("granted_permissions") or ()),
            command_bus_linkage=data.get("command_bus_linkage")
            if isinstance(data.get("command_bus_linkage"), Mapping)
            else None,
            provenance=data.get("provenance")
            if isinstance(data.get("provenance"), Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class PiInvocationReceipt:
    owner_account_id: str
    invocation_id: str
    receipt_id: str
    receipt_status: str = PiReceiptStatus.ACCEPTED.value
    harness_id: str = ""
    execution_attempt_id: str | None = None
    granted_permissions: tuple[str, ...] = ()
    command_bus_linkage: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "owner_account_id",
            _clean_optional_text(self.owner_account_id) or "",
        )
        object.__setattr__(
            self,
            "invocation_id",
            _clean_optional_text(self.invocation_id) or "",
        )
        object.__setattr__(
            self, "receipt_id", _clean_optional_text(self.receipt_id) or ""
        )
        object.__setattr__(
            self,
            "receipt_status",
            _clean_optional_text(self.receipt_status) or "",
        )
        object.__setattr__(
            self, "harness_id", _clean_optional_text(self.harness_id) or ""
        )
        object.__setattr__(
            self,
            "execution_attempt_id",
            _clean_optional_text(self.execution_attempt_id),
        )
        object.__setattr__(
            self,
            "granted_permissions",
            _clean_text_tuple(self.granted_permissions),
        )
        linkage = self.command_bus_linkage
        if linkage is not None and not isinstance(linkage, Mapping):
            raise ValueError(
                "command_bus_linkage must be a mapping when provided"
            )
        object.__setattr__(
            self,
            "command_bus_linkage",
            _clean_mapping(linkage) if linkage else None,
        )
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> PiInvocationReceipt:
        data = dict(payload)
        return cls(
            owner_account_id=data.get("owner_account_id")
            or data.get("owner")
            or "",
            invocation_id=data.get("invocation_id") or "",
            receipt_id=data.get("receipt_id") or "",
            receipt_status=data.get("receipt_status")
            or PiReceiptStatus.ACCEPTED.value,
            harness_id=data.get("harness_id") or "",
            execution_attempt_id=data.get("execution_attempt_id"),
            granted_permissions=tuple(data.get("granted_permissions") or ()),
            command_bus_linkage=data.get("command_bus_linkage")
            if isinstance(data.get("command_bus_linkage"), Mapping)
            else None,
            metadata=data.get("metadata")
            if isinstance(data.get("metadata"), Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class PiHarnessResult:
    owner_account_id: str
    invocation_id: str
    receipt_id: str
    harness_result_id: str
    harness_result_class: str = PiHarnessResultClass.SUCCESS.value
    failure_classification: str | None = None
    artifacts: tuple[PiInvocationArtifact, ...] = ()
    command_bus_linkage: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "owner_account_id",
            _clean_optional_text(self.owner_account_id) or "",
        )
        object.__setattr__(
            self,
            "invocation_id",
            _clean_optional_text(self.invocation_id) or "",
        )
        object.__setattr__(
            self, "receipt_id", _clean_optional_text(self.receipt_id) or ""
        )
        object.__setattr__(
            self,
            "harness_result_id",
            _clean_optional_text(self.harness_result_id) or "",
        )
        object.__setattr__(
            self,
            "harness_result_class",
            _clean_optional_text(self.harness_result_class) or "",
        )
        object.__setattr__(
            self,
            "failure_classification",
            _clean_optional_text(self.failure_classification),
        )
        artifacts: list[PiInvocationArtifact] = []
        for item in self.artifacts:
            if isinstance(item, PiInvocationArtifact):
                artifacts.append(item)
            elif isinstance(item, Mapping):
                artifacts.append(PiInvocationArtifact.from_payload(item))
            else:
                raise ValueError(
                    "artifacts must contain PiInvocationArtifact values"
                )
        object.__setattr__(self, "artifacts", tuple(artifacts))
        linkage = self.command_bus_linkage
        if linkage is not None and not isinstance(linkage, Mapping):
            raise ValueError(
                "command_bus_linkage must be a mapping when provided"
            )
        object.__setattr__(
            self,
            "command_bus_linkage",
            _clean_mapping(linkage) if linkage else None,
        )
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    def to_payload(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "artifacts": [artifact.to_payload() for artifact in self.artifacts],
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> PiHarnessResult:
        data = dict(payload)
        raw_artifacts = data.get("artifacts") or ()
        return cls(
            owner_account_id=data.get("owner_account_id")
            or data.get("owner")
            or "",
            invocation_id=data.get("invocation_id") or "",
            receipt_id=data.get("receipt_id") or "",
            harness_result_id=data.get("harness_result_id") or "",
            harness_result_class=data.get("harness_result_class")
            or PiHarnessResultClass.SUCCESS.value,
            failure_classification=data.get("failure_classification"),
            artifacts=tuple(raw_artifacts)
            if isinstance(raw_artifacts, Sequence)
            else (),
            command_bus_linkage=data.get("command_bus_linkage")
            if isinstance(data.get("command_bus_linkage"), Mapping)
            else None,
            metadata=data.get("metadata")
            if isinstance(data.get("metadata"), Mapping)
            else {},
        )


@dataclass(frozen=True, slots=True)
class PiInvocationValidationResult:
    outcome: str = PiInvocationValidationOutcome.VALID.value
    failure_reason: str | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "outcome", normalize_pi_validation_outcome(self.outcome)
        )
        object.__setattr__(
            self, "failure_reason", _clean_optional_text(self.failure_reason)
        )
        object.__setattr__(self, "message", _clean_optional_text(self.message))
        object.__setattr__(self, "metadata", _clean_mapping(self.metadata))

    @property
    def ok(self) -> bool:
        return self.outcome == PiInvocationValidationOutcome.VALID.value

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


__all__ = [
    "PiInvocationArtifact",
    "PiInvocationEnvelope",
    "PiInvocationReceipt",
    "PiHarnessResult",
    "PiInvocationValidationResult",
]
