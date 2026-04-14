"""Runtime capability policy evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from guardian.core.capability_grants import (
    ResolvedCapabilityGrant,
    resolve_active_grants,
)
from guardian.core.capability_tokens import CANONICAL_CAPABILITY_IDENTIFIERS


class CapabilityPolicyError(ValueError):
    """Raised when a runtime capability policy payload is invalid."""


@dataclass(frozen=True)
class CapabilityPolicyLimit:
    """Effective numeric limit for a canonical capability identifier."""

    capability_id: str
    limit: int
    source_grant_id: str
    source_tier_key: str
    source_field: str = "limits_json"


@dataclass(frozen=True)
class CapabilityPolicyDecision:
    """Effective boolean and numeric policy result for one capability."""

    capability_id: str
    known: bool
    enabled: bool
    source_grant_id: str | None = None
    source_tier_key: str | None = None
    source_family: str | None = None
    source_kind: str | None = None
    limit: int | None = None
    limit_source_grant_id: str | None = None
    limit_source_tier_key: str | None = None
    limit_source_field: str | None = None


@dataclass(frozen=True)
class CapabilityPolicy:
    """Immutable runtime policy snapshot for an account."""

    account_id: str
    evaluated_at: datetime
    active_grants: tuple[ResolvedCapabilityGrant, ...]
    capability_results: tuple[CapabilityPolicyDecision, ...]
    effective_limits: tuple[CapabilityPolicyLimit, ...]
    active_capability_ids: tuple[str, ...]
    unknown_capability_ids: tuple[str, ...]

    def decision_for(
        self, capability_id: str
    ) -> CapabilityPolicyDecision | None:
        normalized = _normalize_known_capability_id(capability_id)
        if normalized is None:
            return None
        for decision in self.capability_results:
            if decision.capability_id == normalized:
                return decision
        return None

    def has_capability(self, capability_id: str) -> bool:
        decision = self.decision_for(capability_id)
        return bool(decision and decision.known and decision.enabled)

    def limit_for(self, capability_id: str) -> int | None:
        decision = self.decision_for(capability_id)
        if decision is None or not decision.known or not decision.enabled:
            return None
        return decision.limit


def _normalize_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityPolicyError(f"{label} must be a non-empty string")
    return value.strip()


def _coerce_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if not isinstance(now, datetime):
        raise CapabilityPolicyError("now must be a datetime when provided")
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _normalize_known_capability_id(capability_id: Any) -> str | None:
    try:
        normalized = _normalize_text(capability_id, "capability id")
    except CapabilityPolicyError:
        return None
    if normalized not in CANONICAL_CAPABILITY_IDENTIFIERS:
        return None
    return normalized


def _get_value(source: Any, names: tuple[str, ...]) -> Any:
    if isinstance(source, Mapping):
        for name in names:
            if name in source:
                return source[name]
        return None
    for name in names:
        if hasattr(source, name):
            return getattr(source, name)
    return None


def _get_tier(source: Any) -> Any:
    tier = _get_value(source, ("tier",))
    if (
        tier is None
        and not isinstance(source, Mapping)
        and hasattr(source, "tier")
    ):
        tier = getattr(source, "tier")
    return tier


def _extract_limit_value(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise CapabilityPolicyError(f"{label} must be an integer")
    if isinstance(value, int):
        if value < 0:
            raise CapabilityPolicyError(f"{label} must be >= 0")
        return value
    if isinstance(value, float):
        if not value.is_integer() or value < 0:
            raise CapabilityPolicyError(f"{label} must be an integer")
        return int(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw.isdigit():
            raise CapabilityPolicyError(f"{label} must be an integer")
        return int(raw)
    if isinstance(value, Mapping):
        for key in ("limit", "max", "value", "count", "quota"):
            if key in value:
                return _extract_limit_value(value[key], f"{label}.{key}")
    raise CapabilityPolicyError(f"{label} must be an integer")


def _extract_tier_limits(tier: Any) -> dict[str, int]:
    raw = _get_value(tier, ("limits_json", "limits"))
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise CapabilityPolicyError("tier limits must be a mapping")

    limits: dict[str, int] = {}
    for key, value in raw.items():
        normalized_key = _normalize_known_capability_id(key)
        if normalized_key is None:
            raise CapabilityPolicyError(
                "tier limits may only use canonical capability identifiers"
            )
        limits[normalized_key] = _extract_limit_value(
            value, f"tier limits[{normalized_key}]"
        )
    return limits


def _extract_grant_id(grant: Any) -> str:
    grant_id = _get_value(grant, ("grant_id", "id"))
    return _normalize_text(grant_id, "grant id")


def _build_grant_index(grants: Iterable[Any]) -> dict[str, Any]:
    indexed: dict[str, Any] = {}
    for grant in grants:
        indexed[_extract_grant_id(grant)] = grant
    return indexed


def _normalize_requested_capability_ids(
    capability_ids: Iterable[str] | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if capability_ids is None:
        return tuple(), tuple()

    requested: list[str] = []
    unknown: list[str] = []
    seen_requested: set[str] = set()
    seen_unknown: set[str] = set()
    for capability_id in capability_ids:
        normalized = _normalize_text(capability_id, "capability id")
        if normalized in CANONICAL_CAPABILITY_IDENTIFIERS:
            if normalized not in seen_requested:
                seen_requested.add(normalized)
                requested.append(normalized)
            continue
        if normalized not in seen_unknown:
            seen_unknown.add(normalized)
            unknown.append(normalized)
    return tuple(requested), tuple(unknown)


def _active_grant_for_capability(
    capability_id: str, active_grants: tuple[ResolvedCapabilityGrant, ...]
) -> ResolvedCapabilityGrant | None:
    for grant in active_grants:
        if capability_id in grant.capability_identifiers:
            return grant
    return None


def _effective_limit_from_grant(
    capability_id: str,
    grant: ResolvedCapabilityGrant,
    grant_source: Any,
) -> CapabilityPolicyLimit | None:
    tier = _get_tier(grant_source)
    if tier is None:
        return None
    limits = _extract_tier_limits(tier)
    limit = limits.get(capability_id)
    if limit is None:
        return None
    tier_key = _normalize_text(
        _get_value(tier, ("tier_key", "package_key", "code")),
        "tier key",
    )
    return CapabilityPolicyLimit(
        capability_id=capability_id,
        limit=limit,
        source_grant_id=grant.grant_id,
        source_tier_key=tier_key,
    )


def _decision_for_capability(
    capability_id: str,
    active_grants: tuple[ResolvedCapabilityGrant, ...],
    grant_index: Mapping[str, Any],
) -> CapabilityPolicyDecision:
    grant = _active_grant_for_capability(capability_id, active_grants)
    if grant is None:
        return CapabilityPolicyDecision(
            capability_id=capability_id,
            known=True,
            enabled=False,
        )

    source = grant_index.get(grant.grant_id)
    limit_result = (
        _effective_limit_from_grant(capability_id, grant, source)
        if source is not None
        else None
    )
    return CapabilityPolicyDecision(
        capability_id=capability_id,
        known=True,
        enabled=True,
        source_grant_id=grant.grant_id,
        source_tier_key=grant.tier_key,
        source_family=grant.tier_family,
        source_kind=grant.grant_kind,
        limit=limit_result.limit if limit_result is not None else None,
        limit_source_grant_id=(
            limit_result.source_grant_id if limit_result is not None else None
        ),
        limit_source_tier_key=(
            limit_result.source_tier_key if limit_result is not None else None
        ),
        limit_source_field=(
            limit_result.source_field if limit_result is not None else None
        ),
    )


def evaluate_capability_policy(
    account_id: str,
    grants: Iterable[Any],
    *,
    capability_ids: Iterable[str] | None = None,
    now: datetime | None = None,
) -> CapabilityPolicy:
    """Resolve the effective runtime policy for an account."""

    normalized_account_id = _normalize_text(account_id, "account id")
    evaluated_at = _coerce_now(now)
    grant_list = list(grants)
    grant_index = _build_grant_index(grant_list)
    active_grants = resolve_active_grants(
        normalized_account_id, grant_list, now=evaluated_at
    )
    active_capability_ids = tuple(
        dict.fromkeys(
            capability_id
            for grant in active_grants
            for capability_id in grant.capability_identifiers
        )
    )

    if capability_ids is None:
        requested_ids = active_capability_ids
        unknown_capability_ids = tuple()
    else:
        (
            requested_ids,
            unknown_capability_ids,
        ) = _normalize_requested_capability_ids(capability_ids)

    capability_results = tuple(
        _decision_for_capability(capability_id, active_grants, grant_index)
        for capability_id in requested_ids
    )

    effective_limits: list[CapabilityPolicyLimit] = []
    seen_limits: set[str] = set()
    for decision in capability_results:
        if (
            decision.enabled
            and decision.limit is not None
            and decision.capability_id not in seen_limits
        ):
            seen_limits.add(decision.capability_id)
            effective_limits.append(
                CapabilityPolicyLimit(
                    capability_id=decision.capability_id,
                    limit=decision.limit,
                    source_grant_id=decision.limit_source_grant_id or "",
                    source_tier_key=decision.limit_source_tier_key or "",
                    source_field=decision.limit_source_field or "limits_json",
                )
            )

    return CapabilityPolicy(
        account_id=normalized_account_id,
        evaluated_at=evaluated_at,
        active_grants=active_grants,
        capability_results=capability_results,
        effective_limits=tuple(effective_limits),
        active_capability_ids=active_capability_ids,
        unknown_capability_ids=unknown_capability_ids,
    )


def account_has_capability(
    account_id: str,
    capability_id: str,
    grants: Iterable[Any],
    *,
    now: datetime | None = None,
) -> bool:
    """Return True when the account currently has the requested capability."""

    policy = evaluate_capability_policy(
        account_id,
        grants,
        capability_ids=[capability_id],
        now=now,
    )
    return policy.has_capability(capability_id)


def active_capability_identifiers_for_account(
    account_id: str,
    grants: Iterable[Any],
    *,
    now: datetime | None = None,
) -> tuple[str, ...]:
    """Return the canonical active capability identifiers for an account."""

    return evaluate_capability_policy(
        account_id, grants, now=now
    ).active_capability_ids


def effective_limits_for_account(
    account_id: str,
    grants: Iterable[Any],
    *,
    now: datetime | None = None,
) -> tuple[CapabilityPolicyLimit, ...]:
    """Return the effective numeric limits currently visible to an account."""

    return evaluate_capability_policy(
        account_id, grants, now=now
    ).effective_limits


def effective_limit_for_account(
    account_id: str,
    capability_id: str,
    grants: Iterable[Any],
    *,
    now: datetime | None = None,
) -> int | None:
    """Return the effective limit for a single canonical capability."""

    return evaluate_capability_policy(
        account_id,
        grants,
        capability_ids=[capability_id],
        now=now,
    ).limit_for(capability_id)


__all__ = [
    "CapabilityPolicyError",
    "CapabilityPolicyLimit",
    "CapabilityPolicyDecision",
    "CapabilityPolicy",
    "evaluate_capability_policy",
    "account_has_capability",
    "active_capability_identifiers_for_account",
    "effective_limits_for_account",
    "effective_limit_for_account",
]
