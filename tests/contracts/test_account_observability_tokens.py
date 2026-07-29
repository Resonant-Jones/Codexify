"""Contract tests for the account-observability token foundation."""

from guardian.account_observability.tokens import (
    ACCOUNT_OBSERVABILITY_TIMING_DEFAULTS_SECONDS,
    ATTRIBUTION_CONFIDENCES,
    ATTRIBUTION_METHODS,
    GUEST_LINEAGE_RETENTION_DAYS,
    INVITE_STATUSES,
    PRESENCE_ACTIVE_WINDOW_SECONDS,
    PRESENCE_HEARTBEAT_INTERVAL_SECONDS,
    PRESENCE_IDLE_EXPIRY_SECONDS,
    AccountObservabilityAttributionConfidence,
    AccountObservabilityAttributionMethod,
    AccountObservabilityInviteStatus,
)


def test_invite_status_registry_is_exact_and_not_expired() -> None:
    assert INVITE_STATUSES == {"active", "disabled", "revoked"}
    assert set(AccountObservabilityInviteStatus) == {
        AccountObservabilityInviteStatus.ACTIVE,
        AccountObservabilityInviteStatus.DISABLED,
        AccountObservabilityInviteStatus.REVOKED,
    }
    assert "expired" not in INVITE_STATUSES


def test_attribution_registries_are_exact() -> None:
    assert ATTRIBUTION_METHODS == {"first_party_first_touch"}
    assert ATTRIBUTION_CONFIDENCES == {"verified"}
    assert set(AccountObservabilityAttributionMethod) == {
        AccountObservabilityAttributionMethod.FIRST_PARTY_FIRST_TOUCH
    }
    assert set(AccountObservabilityAttributionConfidence) == {
        AccountObservabilityAttributionConfidence.VERIFIED
    }


def test_presence_timing_defaults_are_canonical() -> None:
    assert PRESENCE_HEARTBEAT_INTERVAL_SECONDS == 60
    assert PRESENCE_ACTIVE_WINDOW_SECONDS == 300
    assert PRESENCE_IDLE_EXPIRY_SECONDS == 1800
    assert GUEST_LINEAGE_RETENTION_DAYS == 90
    assert ACCOUNT_OBSERVABILITY_TIMING_DEFAULTS_SECONDS["active_window"] == 300


def test_each_token_domain_has_unique_values() -> None:
    assert len(INVITE_STATUSES) == len(AccountObservabilityInviteStatus)
    assert len(ATTRIBUTION_METHODS) == len(
        AccountObservabilityAttributionMethod
    )
    assert len(ATTRIBUTION_CONFIDENCES) == len(
        AccountObservabilityAttributionConfidence
    )
