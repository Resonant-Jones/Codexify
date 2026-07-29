"""Canonical tokens for the account-observability persistence foundation."""

from __future__ import annotations

from enum import Enum
from typing import Final


class AccountObservabilityInviteStatus(str, Enum):
    """Persisted invite-link lifecycle values."""

    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


class AccountObservabilityInviteResolutionResult(str, Enum):
    """Public result values for a successful invite resolution."""

    ATTRIBUTED = "attributed"
    ALREADY_ATTRIBUTED = "already_attributed"


class AccountObservabilityInvitePublicError(str, Enum):
    """Generic public failure values that do not disclose invite state."""

    UNAVAILABLE = "invite_unavailable"


class AccountObservabilityInviteAuditAction(str, Enum):
    """Bounded audit actions for invite and registration lineage."""

    CREATED = "invite_created"
    DISABLED = "invite_disabled"
    REVOKED = "invite_revoked"
    RESOLVED = "invite_resolved"
    REGISTRATION_ATTRIBUTED = "registration_attributed"


class AccountObservabilityAttributionMethod(str, Enum):
    """Persisted account-acquisition attribution method."""

    FIRST_PARTY_FIRST_TOUCH = "first_party_first_touch"


class AccountObservabilityAttributionConfidence(str, Enum):
    """Persisted confidence for verified first-party attribution."""

    VERIFIED = "verified"


INVITE_STATUSES: Final[frozenset[str]] = frozenset(
    status.value for status in AccountObservabilityInviteStatus
)
ATTRIBUTION_METHODS: Final[frozenset[str]] = frozenset(
    method.value for method in AccountObservabilityAttributionMethod
)
ATTRIBUTION_CONFIDENCES: Final[frozenset[str]] = frozenset(
    confidence.value for confidence in AccountObservabilityAttributionConfidence
)

INVITE_RESOLUTION_RESULTS: Final[frozenset[str]] = frozenset(
    result.value for result in AccountObservabilityInviteResolutionResult
)
INVITE_PUBLIC_ERRORS: Final[frozenset[str]] = frozenset(
    error.value for error in AccountObservabilityInvitePublicError
)
INVITE_AUDIT_ACTIONS: Final[frozenset[str]] = frozenset(
    action.value for action in AccountObservabilityInviteAuditAction
)

ATTRIBUTION_COOKIE_NAME: Final[str] = "codexify_guest_attribution"
ATTRIBUTION_COOKIE_MAX_AGE_SECONDS: Final[int] = 90 * 24 * 60 * 60

PRESENCE_HEARTBEAT_INTERVAL_SECONDS: Final[int] = 60
PRESENCE_ACTIVE_WINDOW_SECONDS: Final[int] = 300
PRESENCE_IDLE_EXPIRY_SECONDS: Final[int] = 1800
PRESENCE_ROW_RETENTION_DAYS: Final[int] = 30
GUEST_LINEAGE_RETENTION_DAYS: Final[int] = 90

ACCOUNT_OBSERVABILITY_TIMING_DEFAULTS_SECONDS: Final[dict[str, int]] = {
    "heartbeat_interval": PRESENCE_HEARTBEAT_INTERVAL_SECONDS,
    "active_window": PRESENCE_ACTIVE_WINDOW_SECONDS,
    "idle_expiry": PRESENCE_IDLE_EXPIRY_SECONDS,
    "presence_row_retention_days": PRESENCE_ROW_RETENTION_DAYS,
    "guest_lineage_retention_days": GUEST_LINEAGE_RETENTION_DAYS,
}
ACCOUNT_OBSERVABILITY_TIMING_DEFAULTS: Final[
    tuple[tuple[str, int], ...]
] = tuple(ACCOUNT_OBSERVABILITY_TIMING_DEFAULTS_SECONDS.items())


__all__ = [
    "AccountObservabilityInviteStatus",
    "AccountObservabilityInviteResolutionResult",
    "AccountObservabilityInvitePublicError",
    "AccountObservabilityInviteAuditAction",
    "AccountObservabilityAttributionMethod",
    "AccountObservabilityAttributionConfidence",
    "INVITE_STATUSES",
    "ATTRIBUTION_METHODS",
    "ATTRIBUTION_CONFIDENCES",
    "INVITE_RESOLUTION_RESULTS",
    "INVITE_PUBLIC_ERRORS",
    "INVITE_AUDIT_ACTIONS",
    "ATTRIBUTION_COOKIE_NAME",
    "ATTRIBUTION_COOKIE_MAX_AGE_SECONDS",
    "PRESENCE_HEARTBEAT_INTERVAL_SECONDS",
    "PRESENCE_ACTIVE_WINDOW_SECONDS",
    "PRESENCE_IDLE_EXPIRY_SECONDS",
    "PRESENCE_ROW_RETENTION_DAYS",
    "GUEST_LINEAGE_RETENTION_DAYS",
    "ACCOUNT_OBSERVABILITY_TIMING_DEFAULTS",
    "ACCOUNT_OBSERVABILITY_TIMING_DEFAULTS_SECONDS",
]
