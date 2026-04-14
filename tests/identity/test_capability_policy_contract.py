from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from guardian.core.capability_policy import (
    account_has_capability,
    active_capability_identifiers_for_account,
    effective_limit_for_account,
    evaluate_capability_policy,
)
from guardian.core.capability_tokens import (
    CapabilityFamily,
    CapabilityGrantKind,
    CapabilityGrantScope,
    CapabilityGrantStatus,
)


def _tier(
    *,
    key: str,
    family: CapabilityFamily,
    priority: int,
    capabilities: list[str],
    limits: dict[str, int] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        tier_key=key,
        capability_family=family.value,
        priority=priority,
        capabilities_json=list(capabilities),
        limits_json=dict(limits or {}),
    )


def _grant(
    *,
    grant_id: str,
    account_id: str,
    tier: SimpleNamespace,
    kind: CapabilityGrantKind,
    status: CapabilityGrantStatus = CapabilityGrantStatus.ACTIVE,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=grant_id,
        account_id=account_id,
        tier=tier,
        grant_scope=CapabilityGrantScope.ACCOUNT.value,
        grant_kind=kind.value,
        grant_status=status.value,
        starts_at=starts_at,
        ends_at=ends_at,
        issued_at=datetime.now(timezone.utc),
        revoked_at=None,
        provenance_source="manual",
        provenance_ref="seed",
        provenance_reason="policy contract test",
    )


def test_boolean_capability_evaluation_for_active_grants() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    grant = _grant(
        grant_id="grant-chat",
        account_id="account-1",
        tier=_tier(
            key="chat-core",
            family=CapabilityFamily.CHAT,
            priority=10,
            capabilities=[CapabilityFamily.CHAT.value],
        ),
        kind=CapabilityGrantKind.PERMANENT,
        starts_at=now - timedelta(days=1),
        ends_at=None,
    )

    policy = evaluate_capability_policy(
        "account-1",
        [grant],
        now=now,
    )

    decision = policy.decision_for("chat")
    assert decision is not None
    assert account_has_capability("account-1", "chat", [grant], now=now)
    assert policy.has_capability("chat") is True
    assert decision.enabled is True
    assert decision.source_grant_id == "grant-chat"
    assert active_capability_identifiers_for_account(
        "account-1", [grant], now=now
    ) == ("chat",)


def test_expired_grants_do_not_contribute_to_effective_policy() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    expired_grant = _grant(
        grant_id="grant-expired",
        account_id="account-2",
        tier=_tier(
            key="expired-plugin",
            family=CapabilityFamily.PLUGIN,
            priority=20,
            capabilities=[CapabilityFamily.PLUGIN.value],
        ),
        kind=CapabilityGrantKind.TIME_BOXED,
        starts_at=now - timedelta(days=10),
        ends_at=now - timedelta(seconds=1),
    )

    policy = evaluate_capability_policy(
        "account-2",
        [expired_grant],
        now=now,
    )

    assert (
        account_has_capability("account-2", "plugin", [expired_grant], now=now)
        is False
    )
    assert policy.active_capability_ids == ()
    assert policy.decision_for("plugin") is None


def test_deterministic_precedence_for_overlapping_grants() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    high_priority_grant = _grant(
        grant_id="grant-high",
        account_id="account-3",
        tier=_tier(
            key="plugin-pro",
            family=CapabilityFamily.PLUGIN,
            priority=100,
            capabilities=[CapabilityFamily.PLUGIN.value],
            limits={CapabilityFamily.PLUGIN.value: 8},
        ),
        kind=CapabilityGrantKind.PERMANENT,
        starts_at=now - timedelta(days=1),
        ends_at=None,
    )
    low_priority_grant = _grant(
        grant_id="grant-low",
        account_id="account-3",
        tier=_tier(
            key="plugin-basic",
            family=CapabilityFamily.PLUGIN,
            priority=10,
            capabilities=[CapabilityFamily.PLUGIN.value],
            limits={CapabilityFamily.PLUGIN.value: 2},
        ),
        kind=CapabilityGrantKind.TRIAL,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=30),
    )

    policy = evaluate_capability_policy(
        "account-3",
        [low_priority_grant, high_priority_grant],
        now=now,
    )

    decision = policy.decision_for("plugin")
    assert decision is not None
    assert [grant.grant_id for grant in policy.active_grants] == [
        "grant-high",
        "grant-low",
    ]
    assert decision.source_grant_id == "grant-high"
    assert policy.limit_for("plugin") == 8
    assert (
        effective_limit_for_account(
            "account-3",
            "plugin",
            [low_priority_grant, high_priority_grant],
            now=now,
        )
        == 8
    )


def test_quota_limit_resolution_for_persona_family() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    grant = _grant(
        grant_id="grant-persona",
        account_id="account-4",
        tier=_tier(
            key="persona-lite",
            family=CapabilityFamily.PERSONA_PROFILE,
            priority=25,
            capabilities=[CapabilityFamily.PERSONA_PROFILE.value],
            limits={CapabilityFamily.PERSONA_PROFILE.value: 5},
        ),
        kind=CapabilityGrantKind.PROMO,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=7),
    )

    policy = evaluate_capability_policy(
        "account-4",
        [grant],
        now=now,
    )

    assert policy.limit_for("persona_profile") == 5
    assert (
        effective_limit_for_account(
            "account-4", "persona_profile", [grant], now=now
        )
        == 5
    )
    assert policy.effective_limits[0].capability_id == "persona_profile"
    assert policy.effective_limits[0].limit == 5


def test_unknown_capability_identifiers_fail_closed() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    grant = _grant(
        grant_id="grant-chat",
        account_id="account-5",
        tier=_tier(
            key="chat-core",
            family=CapabilityFamily.CHAT,
            priority=10,
            capabilities=[CapabilityFamily.CHAT.value],
        ),
        kind=CapabilityGrantKind.PERMANENT,
        starts_at=now - timedelta(days=1),
        ends_at=None,
    )

    policy = evaluate_capability_policy(
        "account-5",
        [grant],
        capability_ids=["not-a-real-capability"],
        now=now,
    )

    assert policy.unknown_capability_ids == ("not-a-real-capability",)
    assert policy.decision_for("not-a-real-capability") is None
    assert (
        account_has_capability(
            "account-5",
            "not-a-real-capability",
            [grant],
            now=now,
        )
        is False
    )
    assert (
        effective_limit_for_account(
            "account-5",
            "not-a-real-capability",
            [grant],
            now=now,
        )
        is None
    )
