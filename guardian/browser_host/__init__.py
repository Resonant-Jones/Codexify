"""Pure Guardian-owned Browser Host contract seams.

This package intentionally exposes no route, transport, persistence, or
authentication adapter.  It only loads the shared contract and manages
process-local, one-use attachment grants for deterministic qualification.
"""

from .attachment_grants import (
    AttachmentGrantAuthorizationContext,
    AttachmentGrantDecision,
    AttachmentGrantIssueResult,
    AttachmentGrantPolicy,
    AttachmentGrantStore,
)
from .contract_loader import BrowserHostContractMetadata, ContractLoadError, load_contract_metadata

__all__ = [
    "AttachmentGrantAuthorizationContext",
    "AttachmentGrantDecision",
    "AttachmentGrantIssueResult",
    "AttachmentGrantPolicy",
    "AttachmentGrantStore",
    "BrowserHostContractMetadata",
    "ContractLoadError",
    "load_contract_metadata",
]
