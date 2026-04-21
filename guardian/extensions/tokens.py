"""Canonical tokens for extension persistence."""

from __future__ import annotations

from enum import Enum


class ExtensionTargetSurface(str, Enum):
    """Bounded target surfaces for self-extending proposals."""

    COMMAND_BUS = "command_bus"
    WORKFLOW_BUILDER = "workflow_builder"
    RETRIEVAL_ROUTER = "retrieval_router"
    PERSONA_STUDIO = "persona_studio"


class ExtensionProposalScope(str, Enum):
    """Canonical scope bindings for extension proposals."""

    PROJECT = "project_scoped"
    PROFILE = "profile_scoped"
    ACCOUNT = "account_scoped"


class ExtensionProposalStatus(str, Enum):
    """Canonical proposal lifecycle statuses."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class InstallGateDecisionToken(str, Enum):
    """Canonical install-gate decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"


class CapabilityRegistryStatus(str, Enum):
    """Canonical registry lifecycle statuses."""

    REGISTERED = "registered"
    SUSPENDED = "suspended"
    RETIRED = "retired"
    ARCHIVED = "archived"


class CapabilityEntryProvenanceClass(str, Enum):
    """Canonical provenance classes for registry entries."""

    PROPOSAL_APPROVAL = "proposal_approval"


class ExtensionInstallBindingScope(str, Enum):
    """Canonical scope bindings for install bindings."""

    PROJECT = "project_scoped"
    PROFILE = "profile_scoped"
    ACCOUNT = "account_scoped"


class ExtensionInstallBindingStatus(str, Enum):
    """Canonical lifecycle states for install bindings."""

    ACTIVE = "active"
    UNBOUND = "unbound"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


EXTENSION_TARGET_SURFACES: frozenset[str] = frozenset(
    surface.value for surface in ExtensionTargetSurface
)
EXTENSION_PROPOSAL_SCOPES: frozenset[str] = frozenset(
    scope.value for scope in ExtensionProposalScope
)
EXTENSION_PROPOSAL_STATUSES: frozenset[str] = frozenset(
    status.value for status in ExtensionProposalStatus
)
INSTALL_GATE_DECISION_TOKENS: frozenset[str] = frozenset(
    decision.value for decision in InstallGateDecisionToken
)
CAPABILITY_REGISTRY_STATUSES: frozenset[str] = frozenset(
    status.value for status in CapabilityRegistryStatus
)
CAPABILITY_ENTRY_PROVENANCE_CLASSES: frozenset[str] = frozenset(
    provenance.value for provenance in CapabilityEntryProvenanceClass
)
EXTENSION_INSTALL_BINDING_SCOPES: frozenset[str] = frozenset(
    scope.value for scope in ExtensionInstallBindingScope
)
EXTENSION_INSTALL_BINDING_STATUSES: frozenset[str] = frozenset(
    status.value for status in ExtensionInstallBindingStatus
)


class ExtensionTokenError(ValueError):
    """Raised when a caller supplies an invalid extension token."""


def _normalize_token(
    value: str | None, *, allowed: frozenset[str], kind: str
) -> str:
    token = str(value or "").strip()
    if token not in allowed:
        raise ExtensionTokenError(f"Invalid {kind}: {value!r}")
    return token


def normalize_extension_target_surface(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_TARGET_SURFACES, kind="target_surface"
    )


def normalize_extension_proposal_scope(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_PROPOSAL_SCOPES, kind="proposal_scope"
    )


def normalize_extension_proposal_status(value: str | None) -> str:
    return _normalize_token(
        value, allowed=EXTENSION_PROPOSAL_STATUSES, kind="proposal_status"
    )


def normalize_install_gate_decision_token(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=INSTALL_GATE_DECISION_TOKENS,
        kind="install_gate_decision",
    )


def normalize_capability_registry_status(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_REGISTRY_STATUSES,
        kind="capability_registry_status",
    )


def normalize_capability_entry_provenance_class(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=CAPABILITY_ENTRY_PROVENANCE_CLASSES,
        kind="capability_entry_provenance_class",
    )


def normalize_extension_install_binding_scope(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=EXTENSION_INSTALL_BINDING_SCOPES,
        kind="install_binding_scope",
    )


def normalize_extension_install_binding_status(value: str | None) -> str:
    return _normalize_token(
        value,
        allowed=EXTENSION_INSTALL_BINDING_STATUSES,
        kind="install_binding_status",
    )


__all__ = [
    "ExtensionTargetSurface",
    "ExtensionProposalScope",
    "ExtensionProposalStatus",
    "InstallGateDecisionToken",
    "CapabilityRegistryStatus",
    "CapabilityEntryProvenanceClass",
    "ExtensionInstallBindingScope",
    "ExtensionInstallBindingStatus",
    "ExtensionTokenError",
    "EXTENSION_TARGET_SURFACES",
    "EXTENSION_PROPOSAL_SCOPES",
    "EXTENSION_PROPOSAL_STATUSES",
    "INSTALL_GATE_DECISION_TOKENS",
    "CAPABILITY_REGISTRY_STATUSES",
    "CAPABILITY_ENTRY_PROVENANCE_CLASSES",
    "EXTENSION_INSTALL_BINDING_SCOPES",
    "EXTENSION_INSTALL_BINDING_STATUSES",
    "normalize_extension_target_surface",
    "normalize_extension_proposal_scope",
    "normalize_extension_proposal_status",
    "normalize_install_gate_decision_token",
    "normalize_capability_registry_status",
    "normalize_capability_entry_provenance_class",
    "normalize_extension_install_binding_scope",
    "normalize_extension_install_binding_status",
]
