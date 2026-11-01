"""Canonical vocabulary for the observe-only inference usage ledger."""

from enum import Enum


class InferenceUsageSource(str, Enum):
    PROVIDER_REPORTED = "provider_reported"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class InferenceCostSource(str, Enum):
    RATE_SNAPSHOT_ESTIMATE = "rate_snapshot_estimate"
    UNAVAILABLE = "unavailable"
