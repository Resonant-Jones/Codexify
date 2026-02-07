"""Browser control-plane primitives."""

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
    "ManagedBrowserSession",
    "PlaywrightBridge",
    "PlaywrightNotAvailableError",
]
