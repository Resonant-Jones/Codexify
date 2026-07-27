"""Contract tests for the account-observability token foundation."""

from guardian.account_observability.tokens import (
    ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCES,
    ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHODS,
    ACCOUNT_OBSERVABILITY_INVITE_STATUSES,
    ACTIVE_WINDOW_SECONDS,
    ATTRIBUTION_CONFIDENCES,
    ATTRIBUTION_METHODS,
    HEARTBEAT_INTERVAL_SECONDS,
    IDLE_SESSION_EXPIRY_SECONDS,
    AttributionConfidence,
    AttributionMethod,
    InviteLifecycleStatus,
)


def test_invite_status_registry_is_exact_and_not_expired() -> None:
    assert ACCOUNT_OBSERVABILITY_INVITE_STATUSES == {
        "active",
        "disabled",
        "revoked",
    }
    assert set(InviteLifecycleStatus) == {
        InviteLifecycleStatus.ACTIVE,
        InviteLifecycleStatus.DISABLED,
        InviteLifecycleStatus.REVOKED,
    }
    assert "expired" not in ACCOUNT_OBSERVABILITY_INVITE_STATUSES


def test_attribution_registries_are_exact() -> None:
    assert ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHODS == {
        "first_party_first_touch"
    }
    assert ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCES == {"verified"}
    assert set(AttributionMethod) == {AttributionMethod.FIRST_PARTY_FIRST_TOUCH}
    assert set(AttributionConfidence) == {AttributionConfidence.VERIFIED}
    assert ATTRIBUTION_METHODS == ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHODS
    assert (
        ATTRIBUTION_CONFIDENCES == ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCES
    )


def test_presence_timing_defaults_are_canonical() -> None:
    assert HEARTBEAT_INTERVAL_SECONDS == 60
    assert ACTIVE_WINDOW_SECONDS == 300
    assert IDLE_SESSION_EXPIRY_SECONDS == 1800


def test_each_token_domain_has_unique_values() -> None:
    assert len(ACCOUNT_OBSERVABILITY_INVITE_STATUSES) == len(
        InviteLifecycleStatus
    )
    assert len(ACCOUNT_OBSERVABILITY_ATTRIBUTION_METHODS) == len(
        AttributionMethod
    )
    assert len(ACCOUNT_OBSERVABILITY_ATTRIBUTION_CONFIDENCES) == len(
        AttributionConfidence
    )
