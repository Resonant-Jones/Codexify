"""Internal capability-grant resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from guardian.core.capability_tokens import (
    CANONICAL_CAPABILITY_IDENTIFIERS,
    CAPABILITY_GRANT_KINDS,
    CAPABILITY_GRANT_SCOPES,
    CAPABILITY_GRANT_STATUSES,
    CapabilityGrantKind,
    CapabilityGrantScope,
    CapabilityGrantStatus,
)


class CapabilityGrantError(ValueError):
    """Raised when a grant payload violates the contract."""


@dataclass(frozen=True)
class ResolvedCapabilityGrant:
    """Normalized view of a durable capability grant."""

    grant_id: str
    account_id: str
    tier_key: str
    tier_family: str
    tier_priority: int
    grant_scope: str
    grant_kind: str
    grant_status: str
    starts_at: datetime | None
    ends_at: datetime | None
    issued_at: datetime | None
    revoked_at: datetime | None
    provenance_source: str | None
    provenance_ref: str | None
    provenance_reason: str | None
    capability_identifiers: tuple[str, ...]


def _normalize_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityGrantError(f"{label} must be a non-empty string")
    return value.strip()


def _coerce_token(value: Any, allowed: frozenset[str], label: str) -> str:
    token = _normalize_text(value, label)
    if token not in allowed:
        raise CapabilityGrantError(
            f"{label} must be one of {sorted(allowed)!r}"
        )
    return token


def _coerce_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise CapabilityGrantError("time bounds must be datetimes")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


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


def _grant_kind_rank(kind: str) -> int:
    if kind == CapabilityGrantKind.PERMANENT.value:
        return 0
    if kind == CapabilityGrantKind.PROMO.value:
        return 1
    if kind == CapabilityGrantKind.TRIAL.value:
        return 2
    if kind == CapabilityGrantKind.TIME_BOXED.value:
        return 3
    return 4


def canonical_capability_identifiers(source: Any) -> tuple[str, ...]:
    """Return canonical capability identifiers from a tier or grant payload."""

    raw = _get_value(
        source,
        (
            "capabilities_json",
            "capabilities",
            "capability_tokens",
            "capability_identifiers",
        ),
    )
    if (
        raw is None
        and not isinstance(source, Mapping)
        and hasattr(source, "tier")
    ):
        raw = _get_value(
            getattr(source, "tier"),
            (
                "capabilities_json",
                "capabilities",
                "capability_tokens",
                "capability_identifiers",
            ),
        )

    if raw is None:
        return tuple()

    if isinstance(raw, str):
        tokens = [raw]
    else:
        try:
            tokens = list(raw)
        except TypeError as exc:  # pragma: no cover - defensive contract guard
            raise CapabilityGrantError(
                "capability identifiers must be an iterable of tokens"
            ) from exc

    normalized: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized_token = _coerce_token(
            token,
            CANONICAL_CAPABILITY_IDENTIFIERS,
            "capability identifier",
        )
        if normalized_token not in seen:
            seen.add(normalized_token)
            normalized.append(normalized_token)
    return tuple(normalized)


def is_grant_active(grant: Any, now: datetime | None = None) -> bool:
    """Return True when a grant is active by status and optional bounds."""

    resolved_now = _coerce_datetime(now) or datetime.now(timezone.utc)
    status = _coerce_token(
        _get_value(grant, ("grant_status", "status")),
        CAPABILITY_GRANT_STATUSES,
        "grant status",
    )
    if status != CapabilityGrantStatus.ACTIVE.value:
        return False

    scope = _coerce_token(
        _get_value(grant, ("grant_scope", "scope")),
        CAPABILITY_GRANT_SCOPES,
        "grant scope",
    )
    if scope != CapabilityGrantScope.ACCOUNT.value:
        return False

    starts_at = _coerce_datetime(
        _get_value(grant, ("starts_at", "effective_from"))
    )
    ends_at = _coerce_datetime(
        _get_value(grant, ("ends_at", "expires_at", "effective_until"))
    )
    revoked_at = _coerce_datetime(_get_value(grant, ("revoked_at",)))

    if starts_at is not None and resolved_now < starts_at:
        return False
    if ends_at is not None and resolved_now >= ends_at:
        return False
    if revoked_at is not None and resolved_now >= revoked_at:
        return False
    return True


def _resolved_grant_view(grant: Any) -> ResolvedCapabilityGrant:
    tier = _get_value(grant, ("tier",))
    if tier is None and isinstance(grant, Mapping):
        tier = grant.get("tier")

    tier_family = _coerce_token(
        _get_value(tier, ("capability_family", "family")),
        CANONICAL_CAPABILITY_IDENTIFIERS,
        "capability family",
    )
    return ResolvedCapabilityGrant(
        grant_id=_normalize_text(
            _get_value(grant, ("grant_id", "id")), "grant id"
        ),
        account_id=_normalize_text(
            _get_value(grant, ("account_id",)), "account id"
        ),
        tier_key=_normalize_text(
            _get_value(tier, ("tier_key", "package_key", "code")),
            "tier key",
        ),
        tier_family=tier_family,
        tier_priority=int(_get_value(tier, ("priority",)) or 0),
        grant_scope=_coerce_token(
            _get_value(grant, ("grant_scope", "scope")),
            CAPABILITY_GRANT_SCOPES,
            "grant scope",
        ),
        grant_kind=_coerce_token(
            _get_value(grant, ("grant_kind", "kind")),
            CAPABILITY_GRANT_KINDS,
            "grant kind",
        ),
        grant_status=_coerce_token(
            _get_value(grant, ("grant_status", "status")),
            CAPABILITY_GRANT_STATUSES,
            "grant status",
        ),
        starts_at=_coerce_datetime(
            _get_value(grant, ("starts_at", "effective_from"))
        ),
        ends_at=_coerce_datetime(
            _get_value(grant, ("ends_at", "expires_at", "effective_until"))
        ),
        issued_at=_coerce_datetime(
            _get_value(grant, ("issued_at", "granted_at", "created_at"))
        ),
        revoked_at=_coerce_datetime(_get_value(grant, ("revoked_at",))),
        provenance_source=_get_value(
            grant, ("provenance_source", "source_type")
        ),
        provenance_ref=_get_value(grant, ("provenance_ref", "source_ref")),
        provenance_reason=_get_value(
            grant, ("provenance_reason", "reason", "source_reason")
        ),
        capability_identifiers=canonical_capability_identifiers(tier or grant),
    )


def _grant_sort_key(grant: ResolvedCapabilityGrant) -> tuple[Any, ...]:
    ends_at = grant.ends_at or datetime.max.replace(tzinfo=timezone.utc)
    starts_at = grant.starts_at or datetime.min.replace(tzinfo=timezone.utc)
    return (
        -grant.tier_priority,
        _grant_kind_rank(grant.grant_kind),
        ends_at,
        starts_at,
        grant.grant_id,
    )


def resolve_active_grants(
    account_id: str,
    grants: Iterable[Any],
    now: datetime | None = None,
) -> tuple[ResolvedCapabilityGrant, ...]:
    """Return active grants for an account in deterministic order."""

    normalized_account_id = _normalize_text(account_id, "account id")
    resolved_now = _coerce_datetime(now)
    active_grants = []
    for grant in grants:
        grant_account_id = _normalize_text(
            _get_value(grant, ("account_id",)), "account id"
        )
        if grant_account_id != normalized_account_id:
            continue
        if not is_grant_active(grant, now=resolved_now):
            continue
        active_grants.append(_resolved_grant_view(grant))
    return tuple(sorted(active_grants, key=_grant_sort_key))


def active_capability_identifiers_for_account(
    account_id: str,
    grants: Iterable[Any],
    now: datetime | None = None,
) -> tuple[str, ...]:
    """Return canonical capability identifiers visible to an account."""

    identifiers: list[str] = []
    seen: set[str] = set()
    for grant in resolve_active_grants(account_id, grants, now=now):
        for identifier in grant.capability_identifiers:
            if identifier not in seen:
                seen.add(identifier)
                identifiers.append(identifier)
    return tuple(identifiers)


__all__ = [
    "CapabilityGrantError",
    "ResolvedCapabilityGrant",
    "canonical_capability_identifiers",
    "is_grant_active",
    "resolve_active_grants",
    "active_capability_identifiers_for_account",
    "CANONICAL_CAPABILITY_IDENTIFIERS",
]
