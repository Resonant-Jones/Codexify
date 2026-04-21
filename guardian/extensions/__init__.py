"""Canonical extension proposal contracts and persistence helpers."""

from .contracts import (
    CapabilityRegistryEntry,
    ExtensionDeclaredDependency,
    ExtensionProposalManifest,
    ExtensionProposalRecord,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
    InstallGateDecisionRecord,
)
from .tokens import (
    CAPABILITY_ENTRY_PROVENANCE_CLASSES,
    CAPABILITY_REGISTRY_STATUSES,
    EXTENSION_PROPOSAL_SCOPES,
    EXTENSION_PROPOSAL_STATUSES,
    EXTENSION_TARGET_SURFACES,
    INSTALL_GATE_DECISION_TOKENS,
    CapabilityEntryProvenanceClass,
    CapabilityRegistryStatus,
    ExtensionProposalScope,
    ExtensionProposalStatus,
    ExtensionTargetSurface,
    InstallGateDecisionToken,
)

__all__ = [
    "ExtensionDeclaredDependency",
    "CapabilityRegistryEntry",
    "ExtensionProposalManifest",
    "ExtensionProposalRecord",
    "ExtensionRequestedPermission",
    "ExtensionRollbackMetadata",
    "ExtensionTestEvidenceMetadata",
    "InstallGateDecisionRecord",
    "EXTENSION_PROPOSAL_SCOPES",
    "EXTENSION_PROPOSAL_STATUSES",
    "EXTENSION_TARGET_SURFACES",
    "INSTALL_GATE_DECISION_TOKENS",
    "CAPABILITY_REGISTRY_STATUSES",
    "CAPABILITY_ENTRY_PROVENANCE_CLASSES",
    "ExtensionProposalScope",
    "ExtensionProposalStatus",
    "ExtensionTargetSurface",
    "CapabilityEntryProvenanceClass",
    "CapabilityRegistryStatus",
    "InstallGateDecisionToken",
]
