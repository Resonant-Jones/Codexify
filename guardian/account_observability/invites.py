"""Invite creation, resolution, lineage, and registration attribution services."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from guardian.core.request_correlation import is_safe_identifier
from guardian.db.models import (
    AccountObservabilityAccountMetadata,
    AccountObservabilityGuestIdentity,
    AccountObservabilityInviteLink,
    AuditLog,
    EventGraphEvent,
    User,
)

from .tokens import (
    AccountObservabilityAttributionConfidence,
    AccountObservabilityAttributionMethod,
    AccountObservabilityInviteAuditAction,
    AccountObservabilityInviteResolutionResult,
    AccountObservabilityInviteStatus,
)


class InviteValidationError(ValueError):
    """A caller supplied invite value violates the bounded domain."""


class InviteConflictError(ValueError):
    """An invite cannot be created or transitioned in the requested state."""


class InviteNotFoundError(LookupError):
    """An operator requested a missing invite."""


@dataclass(frozen=True)
class InviteResolutionResult:
    result: str | None
    guest_id: str | None
    invite_id: str | None

    @property
    def available(self) -> bool:
        return self.result is not None


@dataclass(frozen=True)
class RegistrationAttributionResult:
    attributed: bool
    guest_id: str | None
    invite_id: str | None
    created: bool
    skipped_reason: str | None = None


def _utc_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def generate_invite_token() -> str:
    """Generate a URL-safe bearer token with at least 256 bits of entropy."""

    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    """Hash a high-entropy bearer token deterministically for lookup."""

    if not isinstance(token, str) or not token:
        raise InviteValidationError("invite token is required")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invite_fragment(token: str) -> str:
    """Build a fragment-only landing suffix without creating a server URL."""

    return f"#invite={quote(token, safe='')}"


def _validate_expiry(expires_at: datetime | None, now: datetime) -> None:
    if expires_at is not None and _utc_now(expires_at) <= now:
        raise InviteValidationError("expires_at must be in the future")


def create_invite(
    session: Session,
    *,
    created_by_user_id: str,
    name: str,
    campaign_label: str | None = None,
    placement_label: str | None = None,
    expires_at: datetime | None = None,
    now: datetime | None = None,
) -> tuple[AccountObservabilityInviteLink, str]:
    """Persist one invite hash and return its raw token exactly once."""

    current = _utc_now(now)
    normalized_name = str(name or "").strip()
    actor = str(created_by_user_id or "").strip()
    if not normalized_name:
        raise InviteValidationError("name is required")
    if not actor:
        raise InviteValidationError("created_by_user_id is required")
    _validate_expiry(expires_at, current)

    raw_token = generate_invite_token()
    row = AccountObservabilityInviteLink(
        invite_id=str(uuid4()),
        token_hash=hash_invite_token(raw_token),
        name=normalized_name,
        campaign_label=(campaign_label or None),
        placement_label=(placement_label or None),
        created_by_user_id=actor,
        status=AccountObservabilityInviteStatus.ACTIVE.value,
        expires_at=expires_at,
        created_at=current,
        updated_at=current,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        raise InviteConflictError("invite token conflict") from exc
    return row, raw_token


def _is_expired(row: AccountObservabilityInviteLink, now: datetime) -> bool:
    return row.expires_at is not None and _utc_now(row.expires_at) <= now


def invite_metadata(
    row: AccountObservabilityInviteLink, *, now: datetime | None = None
) -> dict[str, Any]:
    current = _utc_now(now)
    return {
        "invite_id": row.invite_id,
        "name": row.name,
        "campaign_label": row.campaign_label,
        "placement_label": row.placement_label,
        "created_by_user_id": row.created_by_user_id,
        "status": row.status,
        "expires_at": row.expires_at,
        "effective_expired": _is_expired(row, current),
        "disabled_at": row.disabled_at,
        "revoked_at": row.revoked_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_invites(session: Session) -> list[AccountObservabilityInviteLink]:
    return list(
        session.scalars(
            select(AccountObservabilityInviteLink).order_by(
                AccountObservabilityInviteLink.created_at.desc(),
                AccountObservabilityInviteLink.invite_id.desc(),
            )
        ).all()
    )


def _get_invite_for_update(
    session: Session, invite_id: str
) -> AccountObservabilityInviteLink:
    row = session.scalar(
        select(AccountObservabilityInviteLink)
        .where(AccountObservabilityInviteLink.invite_id == invite_id)
        .with_for_update()
    )
    if row is None:
        raise InviteNotFoundError("invite not found")
    return row


def disable_invite(
    session: Session, invite_id: str, *, now: datetime | None = None
) -> AccountObservabilityInviteLink:
    current = _utc_now(now)
    row = _get_invite_for_update(session, invite_id)
    if row.status != AccountObservabilityInviteStatus.ACTIVE.value:
        raise InviteConflictError("invite is not active")
    row.status = AccountObservabilityInviteStatus.DISABLED.value
    row.disabled_at = current
    row.updated_at = current
    session.flush()
    return row


def revoke_invite(
    session: Session, invite_id: str, *, now: datetime | None = None
) -> AccountObservabilityInviteLink:
    current = _utc_now(now)
    row = _get_invite_for_update(session, invite_id)
    if row.status not in {
        AccountObservabilityInviteStatus.ACTIVE.value,
        AccountObservabilityInviteStatus.DISABLED.value,
    }:
        raise InviteConflictError("invite is already revoked")
    row.status = AccountObservabilityInviteStatus.REVOKED.value
    row.revoked_at = current
    row.updated_at = current
    session.flush()
    return row


def _guest_id_from_cookie(cookie_value: str | None) -> str | None:
    candidate = str(cookie_value or "").strip()
    if not candidate:
        return None
    try:
        return str(UUID(candidate))
    except (ValueError, AttributeError, TypeError):
        return None


def _valid_invite_for_resolution(
    session: Session, token: str | None, now: datetime
) -> AccountObservabilityInviteLink | None:
    if not isinstance(token, str) or not token or len(token) > 512:
        return None
    row = session.scalar(
        select(AccountObservabilityInviteLink).where(
            AccountObservabilityInviteLink.token_hash == hash_invite_token(token)
        )
    )
    if row is None or row.status != AccountObservabilityInviteStatus.ACTIVE.value:
        return None
    if _is_expired(row, now):
        return None
    return row


def resolve_invite(
    session: Session,
    *,
    token: str | None,
    guest_cookie: str | None,
    now: datetime | None = None,
) -> InviteResolutionResult:
    """Resolve an invite and assign immutable first-touch guest lineage."""

    current = _utc_now(now)
    invite = _valid_invite_for_resolution(session, token, current)
    if invite is None:
        return InviteResolutionResult(result=None, guest_id=None, invite_id=None)

    guest_id = _guest_id_from_cookie(guest_cookie)
    guest = None
    if guest_id is not None:
        guest = session.scalar(
            select(AccountObservabilityGuestIdentity)
            .where(
                AccountObservabilityGuestIdentity.guest_id == guest_id,
                AccountObservabilityGuestIdentity.deleted_at.is_(None),
            )
            .with_for_update()
        )

    if guest is None:
        guest_id = str(uuid4())
        guest = AccountObservabilityGuestIdentity(
            guest_id=guest_id,
            first_invite_id=invite.invite_id,
            created_at=current,
            updated_at=current,
        )
        session.add(guest)
        session.flush()
        return InviteResolutionResult(
            result=AccountObservabilityInviteResolutionResult.ATTRIBUTED.value,
            guest_id=guest_id,
            invite_id=invite.invite_id,
        )

    if guest.first_invite_id is None:
        guest.first_invite_id = invite.invite_id
        guest.updated_at = current
        session.flush()
        return InviteResolutionResult(
            result=AccountObservabilityInviteResolutionResult.ATTRIBUTED.value,
            guest_id=guest.guest_id,
            invite_id=invite.invite_id,
        )

    return InviteResolutionResult(
        result=AccountObservabilityInviteResolutionResult.ALREADY_ATTRIBUTED.value,
        guest_id=guest.guest_id,
        invite_id=guest.first_invite_id,
    )


_NON_HUMAN_IDS = {"local", "system", "service", "seed", "seeded"}
_NON_HUMAN_PREFIXES = ("system:", "service:", "seed:", "seeded:")


def is_eligible_human_registration(user: User) -> bool:
    candidates = {
        str(getattr(user, "id", "") or "").strip().casefold(),
        str(getattr(user, "username", "") or "").strip().casefold(),
    }
    return not any(
        candidate in _NON_HUMAN_IDS
        or candidate.startswith(_NON_HUMAN_PREFIXES)
        for candidate in candidates
    )


def complete_registration_attribution(
    session: Session,
    *,
    user_id: str,
    guest_cookie: str | None,
    registered_at: datetime,
) -> RegistrationAttributionResult:
    """Create one idempotent metadata row after canonical account commit."""

    user = session.get(User, user_id)
    if user is None:
        raise LookupError("registered user not found")
    if not is_eligible_human_registration(user):
        return RegistrationAttributionResult(
            attributed=False,
            guest_id=None,
            invite_id=None,
            created=False,
            skipped_reason="ineligible_identity",
        )

    existing = session.get(AccountObservabilityAccountMetadata, user_id)
    if existing is not None:
        return RegistrationAttributionResult(
            attributed=existing.acquisition_invite_id is not None,
            guest_id=existing.prior_guest_id,
            invite_id=existing.acquisition_invite_id,
            created=False,
            skipped_reason="already_recorded",
        )

    current = _utc_now(registered_at)
    guest_id = _guest_id_from_cookie(guest_cookie)
    guest = None
    if guest_id is not None:
        guest = session.scalar(
            select(AccountObservabilityGuestIdentity)
            .where(
                AccountObservabilityGuestIdentity.guest_id == guest_id,
                AccountObservabilityGuestIdentity.deleted_at.is_(None),
            )
            .with_for_update()
        )

    invite_id = (
        guest.first_invite_id
        if guest is not None and guest.converted_at is None
        else None
    )
    metadata = AccountObservabilityAccountMetadata(
        user_id=user_id,
        registered_at=current,
        acquisition_invite_id=invite_id,
        prior_guest_id=guest.guest_id if invite_id else None,
        attribution_method=(
            AccountObservabilityAttributionMethod.FIRST_PARTY_FIRST_TOUCH.value
            if invite_id
            else None
        ),
        attribution_confidence=(
            AccountObservabilityAttributionConfidence.VERIFIED.value
            if invite_id
            else None
        ),
        created_at=current,
        updated_at=current,
    )
    session.add(metadata)
    if guest is not None and invite_id is not None and guest.converted_at is None:
        guest.converted_at = current
        guest.updated_at = current
    session.flush()
    return RegistrationAttributionResult(
        attributed=invite_id is not None,
        guest_id=guest.guest_id if invite_id and guest is not None else None,
        invite_id=invite_id,
        created=True,
    )


def record_invite_audit(
    session: Session,
    *,
    action: str,
    invite_id: str,
    actor_id: str,
    request_id: str,
    result: str | None = None,
    occurred_at: datetime | None = None,
) -> None:
    """Write bounded audit rows without bearer or cookie values."""

    if not is_safe_identifier(request_id):
        raise ValueError("request_id must be a bounded identifier")
    if action not in {item.value for item in AccountObservabilityInviteAuditAction}:
        raise ValueError("unsupported invite audit action")
    current = _utc_now(occurred_at)
    session.add(
        AuditLog(
            event=action,
            entity="account_observability_invite",
            entity_id=invite_id,
            user_id=actor_id,
            timestamp=current,
        )
    )
    idempotency_key = f"account_observability:{action}:{invite_id}:{request_id}"
    existing = session.scalar(
        select(EventGraphEvent).where(
            EventGraphEvent.idempotency_key == idempotency_key
        )
    )
    if existing is None:
        session.add(
            EventGraphEvent(
                event_type=action,
                occurred_at=current,
                actor_user_id=actor_id,
                entity_type="account_observability_invite",
                entity_id=invite_id,
                idempotency_key=idempotency_key,
                payload_json={
                    "request_id": request_id,
                    **({"result": result} if result else {}),
                },
            )
        )


__all__ = [
    "InviteConflictError",
    "InviteNotFoundError",
    "InviteResolutionResult",
    "InviteValidationError",
    "RegistrationAttributionResult",
    "complete_registration_attribution",
    "create_invite",
    "disable_invite",
    "generate_invite_token",
    "hash_invite_token",
    "invite_fragment",
    "invite_metadata",
    "is_eligible_human_registration",
    "list_invites",
    "record_invite_audit",
    "resolve_invite",
    "revoke_invite",
]
