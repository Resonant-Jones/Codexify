"""Canonical tokens and timing defaults for account observability.

The values in this module are the bounded vocabulary for the persistence
foundation. They do not authorize telemetry collection or runtime behavior.
"""

from __future__ import annotations

from enum import Enum


class InviteLifecycleStatus(str, Enum):
    """Persisted invite-link lifecycle values.

    Expiration is derived from ``expires_at`` and is intentionally not a
    persisted status.
    """

    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


class AttributionMethod(str, Enum):
    """Canonical method used for verified acquisition attribution."""

    FIRST_PARTY_FIRST_TOUCH = "first_party_first_touch"


class AttributionConfidence(str, Enum):
    """Canonical confidence for the first-party attribution binding."""

    VERIFIED = "verified"


ACCOUNT_OBSERVABILITY_INVITE_STATUSES: frozenset[str] = frozenset(
    status.value for status in InviteLifecycleStatus
)
ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHODS: frozenset[str] = frozenset(
    method.value for method in AttributionMethod
)
ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCES: frozenset[str] = frozenset(
    confidence.value for confidence in AttributionConfidence
)

# Short module-local names keep later validators readable while the prefixed
# collections remain the canonical exports for cross-module use.
INVITE_STATUSES = ACCOUNT_OBSERVABILITY_INVITE_STATUSES
ATTRIBUTION_METHODS = ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHODS
ATTRIBUTION_CONFIDENCES = ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCES

PRESENCE_HEARTBEAT_INTERVAL_SECONDS = 60
PRESENCE_ACTIVE_WINDOW_SECONDS = 300
PRESENCE_IDLE_EXPIRY_SECONDS = 1800
PRESENCE_ROW_RETENTION_DAYS = 30
GUEST_LINEAGE_RETENTION_DAYS = 90
GUEST_ID_COOKIE_NAME = "codexify_guest_id"

# These names mirror the contract's prose and remain aliases of the bounded
# timing defaults above, not separate configuration values.
HEARTBEAT_INTERVAL_SECONDS = PRESENCE_HEARTBEAT_INTERVAL_SECONDS
ACTIVE_WINDOW_SECONDS = PRESENCE_ACTIVE_WINDOW_SECONDS
IDLE_SESSION_EXPIRY_SECONDS = PRESENCE_IDLE_EXPIRY_SECONDS


__all__ = [
    "InviteLifecycleStatus",
    "AttributionMethod",
    "AttributionConfidence",
    "ACCOUNT_OBSERVABILITY_INVITE_STATUSES",
    "ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHODS",
    "ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCES",
    "INVITE_STATUSES",
    "ATTRIBUTION_METHODS",
    "ATTRIBUTION_CONFIDENCES",
    "PRESENCE_HEARTBEAT_INTERVAL_SECONDS",
    "PRESENCE_ACTIVE_WINDOW_SECONDS",
    "PRESENCE_IDLE_EXPIRY_SECONDS",
    "HEARTBEAT_INTERVAL_SECONDS",
    "ACTIVE_WINDOW_SECONDS",
    "IDLE_SESSION_EXPIRY_SECONDS",
    "PRESENCE_ROW_RETENTION_DAYS",
    "GUEST_LINEAGE_RETENTION_DAYS",
    "GUEST_ID_COOKIE_NAME",
]
