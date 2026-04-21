"""Canonical extension proposal contracts and persistence helpers."""

from .contracts import (
    ExtensionDeclaredDependency,
    ExtensionProposalManifest,
    ExtensionProposalRecord,
    ExtensionRequestedPermission,
    ExtensionRollbackMetadata,
    ExtensionTestEvidenceMetadata,
)
from .tokens import (
    EXTENSION_PROPOSAL_SCOPES,
    EXTENSION_PROPOSAL_STATUSES,
    EXTENSION_TARGET_SURFACES,
    ExtensionProposalScope,
    ExtensionProposalStatus,
    ExtensionTargetSurface,
)

__all__ = [
    "ExtensionDeclaredDependency",
    "ExtensionProposalManifest",
    "ExtensionProposalRecord",
    "ExtensionRequestedPermission",
    "ExtensionRollbackMetadata",
    "ExtensionTestEvidenceMetadata",
    "EXTENSION_PROPOSAL_SCOPES",
    "EXTENSION_PROPOSAL_STATUSES",
    "EXTENSION_TARGET_SURFACES",
    "ExtensionProposalScope",
    "ExtensionProposalStatus",
    "ExtensionTargetSurface",
]
