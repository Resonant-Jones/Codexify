"""Pure Guardian-owned Browser Host contract seams.

The contract and grant classes remain pure and process-local.  The separate
development-only HTTP adapter lives in ``guardian.browser_host.http_adapter``
and is mounted only by the explicitly gated Guardian route module.
"""

from .attachment_grants import (
    AttachmentGrantAuthorizationContext,
    AttachmentGrantDecision,
    AttachmentGrantIssueResult,
    AttachmentGrantPolicy,
    AttachmentGrantStore,
)
from .contract_loader import BrowserHostContractMetadata, ContractLoadError, load_contract_metadata
from .negotiation import (
    BrowserHostNegotiationDecision,
    BrowserHostNegotiationPolicy,
    build_default_negotiation_policy,
    negotiate_browser_host_hello,
    validate_browser_host_hello,
    validate_browser_host_hello_request,
)

__all__ = [
    "AttachmentGrantAuthorizationContext",
    "AttachmentGrantDecision",
    "AttachmentGrantIssueResult",
    "AttachmentGrantPolicy",
    "AttachmentGrantStore",
    "BrowserHostContractMetadata",
    "ContractLoadError",
    "load_contract_metadata",
    "BrowserHostNegotiationDecision",
    "BrowserHostNegotiationPolicy",
    "build_default_negotiation_policy",
    "negotiate_browser_host_hello",
    "validate_browser_host_hello",
    "validate_browser_host_hello_request",
]
