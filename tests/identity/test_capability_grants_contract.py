from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from guardian.core.capability_grants import (
    active_capability_identifiers_for_account,
    canonical_capability_identifiers,
    is_grant_active,
    resolve_active_grants,
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
) -> SimpleNamespace:
    return SimpleNamespace(
        tier_key=key,
        capability_family=family.value,
        priority=priority,
        capabilities_json=list(capabilities),
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
    issued_at: datetime | None = None,
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
        issued_at=issued_at or datetime.now(timezone.utc),
        revoked_at=None,
        provenance_source="manual",
        provenance_ref="seed",
        provenance_reason="contract test seed",
    )


def test_active_grant_resolution_honors_status_and_time_bounds() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    active_tier = _tier(
        key="release-trial",
        family=CapabilityFamily.RELEASE_FAMILY,
        priority=20,
        capabilities=[CapabilityFamily.RELEASE_FAMILY.value],
    )
    future_tier = _tier(
        key="future-promo",
        family=CapabilityFamily.PROJECT,
        priority=10,
        capabilities=[CapabilityFamily.PROJECT.value],
    )
    revoked_tier = _tier(
        key="revoked-plugin",
        family=CapabilityFamily.PLUGIN,
        priority=30,
        capabilities=[CapabilityFamily.PLUGIN.value],
    )

    active_grant = _grant(
        grant_id="grant-active",
        account_id="account-1",
        tier=active_tier,
        kind=CapabilityGrantKind.TRIAL,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
        issued_at=now - timedelta(days=2),
    )
    future_grant = _grant(
        grant_id="grant-future",
        account_id="account-1",
        tier=future_tier,
        kind=CapabilityGrantKind.PROMO,
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=7),
        issued_at=now - timedelta(days=1),
    )
    revoked_grant = _grant(
        grant_id="grant-revoked",
        account_id="account-1",
        tier=revoked_tier,
        kind=CapabilityGrantKind.PERMANENT,
        status=CapabilityGrantStatus.REVOKED,
        starts_at=now - timedelta(days=2),
        ends_at=None,
        issued_at=now - timedelta(days=2),
    )

    assert is_grant_active(active_grant, now=now) is True
    assert is_grant_active(future_grant, now=now) is False
    assert is_grant_active(revoked_grant, now=now) is False

    resolved = resolve_active_grants(
        "account-1",
        [future_grant, revoked_grant, active_grant],
        now=now,
    )

    assert [grant.grant_id for grant in resolved] == ["grant-active"]
    assert resolved[0].capability_identifiers == (
        CapabilityFamily.RELEASE_FAMILY.value,
    )
    assert canonical_capability_identifiers(active_grant) == (
        CapabilityFamily.RELEASE_FAMILY.value,
    )


def test_expired_grants_are_not_treated_as_active() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    tier = _tier(
        key="expired-persona",
        family=CapabilityFamily.PERSONA_PROFILE,
        priority=15,
        capabilities=[CapabilityFamily.PERSONA_PROFILE.value],
    )
    expired_grant = _grant(
        grant_id="grant-expired",
        account_id="account-2",
        tier=tier,
        kind=CapabilityGrantKind.TIME_BOXED,
        starts_at=now - timedelta(days=10),
        ends_at=now - timedelta(seconds=1),
        issued_at=now - timedelta(days=11),
    )

    assert is_grant_active(expired_grant, now=now) is False
    assert resolve_active_grants("account-2", [expired_grant], now=now) == ()


def test_permanent_grants_remain_active_without_expiry() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    tier = _tier(
        key="permanent-plugin",
        family=CapabilityFamily.PLUGIN,
        priority=99,
        capabilities=[CapabilityFamily.PLUGIN.value],
    )
    permanent_grant = _grant(
        grant_id="grant-permanent",
        account_id="account-3",
        tier=tier,
        kind=CapabilityGrantKind.PERMANENT,
        starts_at=None,
        ends_at=None,
        issued_at=now - timedelta(days=100),
    )

    assert is_grant_active(permanent_grant, now=now) is True
    resolved = resolve_active_grants("account-3", [permanent_grant], now=now)
    assert [grant.grant_id for grant in resolved] == ["grant-permanent"]
    assert active_capability_identifiers_for_account(
        "account-3", [permanent_grant], now=now
    ) == (CapabilityFamily.PLUGIN.value,)


def test_multiple_grants_for_one_account_resolve_deterministically() -> None:
    now = datetime(2026, 4, 13, tzinfo=timezone.utc)
    gold_tier = _tier(
        key="gold-release",
        family=CapabilityFamily.RELEASE_FAMILY,
        priority=100,
        capabilities=[
            CapabilityFamily.RELEASE_FAMILY.value,
            CapabilityFamily.PLUGIN.value,
        ],
    )
    starter_tier = _tier(
        key="starter-persona",
        family=CapabilityFamily.PERSONA_PROFILE,
        priority=10,
        capabilities=[CapabilityFamily.PERSONA_PROFILE.value],
    )
    other_account_tier = _tier(
        key="other-account",
        family=CapabilityFamily.CHAT,
        priority=999,
        capabilities=[CapabilityFamily.CHAT.value],
    )

    gold_grant = _grant(
        grant_id="grant-gold",
        account_id="account-4",
        tier=gold_tier,
        kind=CapabilityGrantKind.PERMANENT,
        starts_at=now - timedelta(days=1),
        ends_at=None,
        issued_at=now - timedelta(days=1),
    )
    starter_grant = _grant(
        grant_id="grant-starter",
        account_id="account-4",
        tier=starter_tier,
        kind=CapabilityGrantKind.PROMO,
        starts_at=now - timedelta(days=2),
        ends_at=now + timedelta(days=30),
        issued_at=now - timedelta(days=2),
    )
    other_account_grant = _grant(
        grant_id="grant-other",
        account_id="account-999",
        tier=other_account_tier,
        kind=CapabilityGrantKind.PERMANENT,
        starts_at=now - timedelta(days=1),
        ends_at=None,
        issued_at=now - timedelta(days=1),
    )

    resolved = resolve_active_grants(
        "account-4",
        [starter_grant, other_account_grant, gold_grant],
        now=now,
    )

    assert [grant.grant_id for grant in resolved] == [
        "grant-gold",
        "grant-starter",
    ]
    assert resolved[0].capability_identifiers == (
        CapabilityFamily.RELEASE_FAMILY.value,
        CapabilityFamily.PLUGIN.value,
    )
    assert active_capability_identifiers_for_account(
        "account-4",
        [starter_grant, other_account_grant, gold_grant],
        now=now,
    ) == (
        CapabilityFamily.RELEASE_FAMILY.value,
        CapabilityFamily.PLUGIN.value,
        CapabilityFamily.PERSONA_PROFILE.value,
    )
