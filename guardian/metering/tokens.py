"""Canonical vocabulary for the observe-only inference usage ledger."""

from enum import Enum


class InferenceUsageSource(str, Enum):
    PROVIDER_REPORTED = "provider_reported"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class InferenceCostSource(str, Enum):
    RATE_SNAPSHOT_ESTIMATE = "rate_snapshot_estimate"
    UNAVAILABLE = "unavailable"


class InferenceBudgetState(str, Enum):
    """Internal reservation lifecycle, not a public runtime event domain."""

    RESERVED = "reserved"
    DISPATCHED = "dispatched"
    SETTLED = "settled"
    RELEASED = "released"


class VoiceBillingUnit(str, Enum):
    """Private typed voice accounting dimensions, not public runtime events."""

    CONNECTION_MS = "connection_ms"
    SYNTHESIS_CHARACTERS = "synthesis_characters"


class VoicePayerKind(str, Enum):
    """Private routing descriptors; never credential ownership grants."""

    SPONSOR = "sponsor"
    ACCOUNT_OWNED = "account_owned"


class VoiceBudgetService(str, Enum):
    """Service derived from the validated exact endpoint."""

    AGENT = "voice_agent"
    SPEAK = "speak"
