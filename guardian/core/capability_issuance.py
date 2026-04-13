"""Internal capability-grant issuance helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from guardian.core.capability_grants import (
    CapabilityGrantError,
    canonical_capability_identifiers,
)
from guardian.core.capability_tokens import (
    CAPABILITY_FAMILIES,
    CAPABILITY_GRANT_KINDS,
    CAPABILITY_GRANT_SCOPES,
    CAPABILITY_GRANT_STATUSES,
    CapabilityGrantKind,
    CapabilityGrantScope,
    CapabilityGrantStatus,
)
from guardian.db.models import CapabilityGrant, CapabilityTier


class CapabilityIssuanceError(ValueError):
    """Raised when issuance payloads violate the contract."""


@dataclass(frozen=True)
class CapabilityIssuanceRequest:
    """Normalized request for issuing a durable capability grant."""

    account_id: str
    tier: CapabilityTier | Any
    grant_kind: str
    grant_scope: str = CapabilityGrantScope.ACCOUNT.value
    grant_status: str = CapabilityGrantStatus.ACTIVE.value
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    issued_at: datetime | None = None
    provenance_source: str | None = None
    provenance_ref: str | None = None
    provenance_reason: str | None = None
    provenance_json: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class CapabilityIssuanceResult:
    """Issued grant plus normalized metadata for tooling and tests."""

    grant: CapabilityGrant
    account_id: str
    tier_id: int
    tier_key: str
    tier_family: str
    capability_identifiers: tuple[str, ...]
    grant_scope: str
    grant_kind: str
    grant_status: str
    issued_at: datetime
    starts_at: datetime
    ends_at: datetime | None
    provenance_source: str | None
    provenance_ref: str | None
    provenance_reason: str | None
    provenance_json: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Render the result as JSON-safe primitives."""

        return {
            "grant_id": self.grant.id,
            "account_id": self.account_id,
            "tier_id": self.tier_id,
            "tier_key": self.tier_key,
            "tier_family": self.tier_family,
            "capability_identifiers": list(self.capability_identifiers),
            "grant_scope": self.grant_scope,
            "grant_kind": self.grant_kind,
            "grant_status": self.grant_status,
            "issued_at": self.issued_at.isoformat(),
            "starts_at": self.starts_at.isoformat(),
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "provenance_source": self.provenance_source,
            "provenance_ref": self.provenance_ref,
            "provenance_reason": self.provenance_reason,
            "provenance_json": dict(self.provenance_json),
        }


def _normalize_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityIssuanceError(f"{label} must be a non-empty string")
    return value.strip()


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


def _coerce_datetime(value: Any, label: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise CapabilityIssuanceError(f"{label} must be a datetime")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _coerce_token(value: Any, allowed: frozenset[str], label: str) -> str:
    token = _normalize_text(value, label)
    if token not in allowed:
        raise CapabilityIssuanceError(
            f"{label} must be one of {sorted(allowed)!r}"
        )
    return token


def _normalize_provenance_json(
    provenance_json: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if provenance_json is None:
        return {}
    if not isinstance(provenance_json, Mapping):
        raise CapabilityIssuanceError(
            "provenance_json must be a mapping when provided"
        )
    normalized: dict[str, Any] = {}
    for key, value in provenance_json.items():
        if not isinstance(key, str) or not key.strip():
            raise CapabilityIssuanceError(
                "provenance_json keys must be non-empty strings"
            )
        normalized[key.strip()] = value
    return normalized


def _resolve_tier(tier: Any) -> tuple[int, str, str, tuple[str, ...]]:
    if tier is None:
        raise CapabilityIssuanceError(
            "tier must reference an existing capability tier"
        )

    tier_id = _get_value(tier, ("id", "tier_id"))
    tier_key = _normalize_text(
        _get_value(tier, ("tier_key", "package_key", "code")),
        "tier key",
    )
    tier_family = _coerce_token(
        _get_value(tier, ("capability_family", "family")),
        CAPABILITY_FAMILIES,
        "capability family",
    )

    try:
        tier_capability_identifiers = canonical_capability_identifiers(tier)
    except CapabilityGrantError as exc:
        raise CapabilityIssuanceError(str(exc)) from exc

    if tier_id is None:
        raise CapabilityIssuanceError(
            "tier must reference an existing capability tier"
        )

    try:
        normalized_tier_id = int(tier_id)
    except (TypeError, ValueError) as exc:
        raise CapabilityIssuanceError(
            "tier must reference an existing capability tier"
        ) from exc

    return (
        normalized_tier_id,
        tier_key,
        tier_family,
        tier_capability_identifiers,
    )


def _normalize_time_bounds(
    grant_kind: str,
    starts_at: datetime | None,
    ends_at: datetime | None,
    *,
    issued_at: datetime,
) -> tuple[datetime, datetime | None]:
    normalized_starts_at = starts_at or issued_at

    if grant_kind == CapabilityGrantKind.PERMANENT.value:
        if ends_at is not None:
            raise CapabilityIssuanceError(
                "permanent grants cannot have an ends_at"
            )
        return normalized_starts_at, None

    if ends_at is None:
        raise CapabilityIssuanceError("time-boxed grants require an ends_at")
    if ends_at <= normalized_starts_at:
        raise CapabilityIssuanceError(
            "ends_at must be after starts_at for time-boxed grants"
        )
    return normalized_starts_at, ends_at


def issue_capability_grant(
    request: CapabilityIssuanceRequest,
    *,
    now: datetime | None = None,
) -> CapabilityIssuanceResult:
    """Validate and normalize a capability grant issuance request."""

    resolved_now = _coerce_datetime(now, "now") or datetime.now(timezone.utc)
    account_id = _normalize_text(request.account_id, "account id")
    tier_id, tier_key, tier_family, capability_identifiers = _resolve_tier(
        request.tier
    )
    grant_scope = _coerce_token(
        request.grant_scope, CAPABILITY_GRANT_SCOPES, "grant scope"
    )
    grant_kind = _coerce_token(
        request.grant_kind, CAPABILITY_GRANT_KINDS, "grant kind"
    )
    grant_status = _coerce_token(
        request.grant_status, CAPABILITY_GRANT_STATUSES, "grant status"
    )

    issued_at = _coerce_datetime(request.issued_at, "issued_at") or resolved_now
    starts_at, ends_at = _normalize_time_bounds(
        grant_kind,
        _coerce_datetime(request.starts_at, "starts_at"),
        _coerce_datetime(request.ends_at, "ends_at"),
        issued_at=issued_at,
    )
    provenance_json = _normalize_provenance_json(request.provenance_json)
    provenance_source = (
        _normalize_text(request.provenance_source, "provenance source")
        if request.provenance_source
        else None
    )
    provenance_ref = (
        _normalize_text(request.provenance_ref, "provenance ref")
        if request.provenance_ref
        else None
    )
    provenance_reason = (
        _normalize_text(request.provenance_reason, "provenance reason")
        if request.provenance_reason
        else None
    )

    grant = CapabilityGrant(
        account_id=account_id,
        tier_id=tier_id,
        grant_scope=grant_scope,
        grant_kind=grant_kind,
        grant_status=grant_status,
        starts_at=starts_at,
        ends_at=ends_at,
        issued_at=issued_at,
        provenance_source=provenance_source,
        provenance_ref=provenance_ref,
        provenance_reason=provenance_reason,
        provenance_json=provenance_json,
    )
    if isinstance(request.tier, CapabilityTier):
        grant.tier = request.tier

    return CapabilityIssuanceResult(
        grant=grant,
        account_id=account_id,
        tier_id=tier_id,
        tier_key=tier_key,
        tier_family=tier_family,
        capability_identifiers=capability_identifiers,
        grant_scope=grant_scope,
        grant_kind=grant_kind,
        grant_status=grant_status,
        issued_at=issued_at,
        starts_at=starts_at,
        ends_at=ends_at,
        provenance_source=provenance_source,
        provenance_ref=provenance_ref,
        provenance_reason=provenance_reason,
        provenance_json=provenance_json,
    )


__all__ = [
    "CapabilityIssuanceError",
    "CapabilityIssuanceRequest",
    "CapabilityIssuanceResult",
    "issue_capability_grant",
]
