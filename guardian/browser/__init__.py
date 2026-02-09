"""Browser control-plane primitives."""

from .approval import (
    ApprovalError,
    ApprovalNotFoundError,
    ApprovalRequiredError,
    ApprovalTransitionError,
    configure_db,
    create_approval_request,
    decide_approval,
    ensure_tables,
    is_approved,
    list_approvals,
    require_approval_for_operation,
)
from .cdp_bridge import (
    BrowserPageBridge,
    PlaywrightBridge,
    PlaywrightNotAvailableError,
)
from .session_manager import (
    BrowserAllowlistViolationError,
    BrowserSessionError,
    BrowserSessionExpiredError,
    BrowserSessionLimitExceededError,
    BrowserSessionManager,
    BrowserSessionNotFoundError,
    ManagedBrowserSession,
)

__all__ = [
    "BrowserAllowlistViolationError",
    "BrowserPageBridge",
    "BrowserSessionError",
    "BrowserSessionExpiredError",
    "BrowserSessionLimitExceededError",
    "BrowserSessionManager",
    "BrowserSessionNotFoundError",
    "ApprovalError",
    "ApprovalNotFoundError",
    "ApprovalRequiredError",
    "ApprovalTransitionError",
    "ManagedBrowserSession",
    "PlaywrightBridge",
    "PlaywrightNotAvailableError",
    "configure_db",
    "create_approval_request",
    "decide_approval",
    "ensure_tables",
    "is_approved",
    "list_approvals",
    "require_approval_for_operation",
]
