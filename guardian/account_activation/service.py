"""Guardian-owned lifecycle for one-time account activation capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from guardian.account_activation.tokens import (
    ACCOUNT_ACTIVATION_ENTITY,
    AccountActivationAuditAction,
    digest_activation_token,
    generate_activation_token,
)
from guardian.core.passwords import hash_password
from guardian.core.preview_access import ADMIN_ROLE, GUEST_ROLE
from guardian.db.models import AccountActivationCapability, AuditLog, User

CANONICAL_ACCOUNT_ROLES = frozenset({ADMIN_ROLE, GUEST_ROLE})


class ActivationConflictError(ValueError):
    """Issuance conflicts with canonical account or capability state."""


class ActivationAuthorizationError(ValueError):
    """The named operator does not own activation authority."""


class ActivationNotFoundError(ValueError):
    """The operator-selected durable activation does not exist."""


class ActivationStateError(ValueError):
    """The requested operator lifecycle transition is invalid."""


class ActivationUnavailableError(ValueError):
    """Public-generic redemption failure for any unusable bearer."""


@dataclass(frozen=True, slots=True)
class IssuedActivation:
    capability: AccountActivationCapability
    raw_token: str


def _utc_now(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc)


def _comparable_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_recipient_email(value: object) -> str:
    """Apply the tester runtime's canonical email normalization semantics."""

    email = str(value or "").strip().casefold()
    if not email:
        raise ValueError("email is required")
    local, separator, domain = email.partition("@")
    if separator != "@" or not local or not domain or "@" in domain:
        raise ValueError("email must have a nonempty local part and domain")
    if len(email) > 255:
        raise ValueError("email is too long")
    return email


def normalize_actor_user_id(value: object) -> str:
    actor_user_id = str(value or "").strip()
    if not actor_user_id:
        raise ActivationAuthorizationError("operator user id is required")
    if len(actor_user_id) > 255:
        raise ActivationAuthorizationError("operator user id is invalid")
    return actor_user_id


def normalize_role(value: object) -> str:
    role = str(value or "").strip().lower()
    if role not in CANONICAL_ACCOUNT_ROLES:
        raise ValueError("role must be admin or guest")
    return role


def _require_admin_operator(session: Session, actor_user_id: object) -> User:
    actor_id = normalize_actor_user_id(actor_user_id)
    actor = session.get(User, actor_id)
    if actor is None or actor.role != ADMIN_ROLE:
        raise ActivationAuthorizationError(
            "operator must be an existing canonical admin user"
        )
    return actor


def _account_for_email(session: Session, email: str) -> User | None:
    return session.scalar(
        select(User).where(
            or_(User.id == email, User.username == email, User.email == email)
        )
    )


def _serialize_recipient_issuance(session: Session, email: str) -> None:
    """Serialize same-recipient issuance on Postgres without durable lock rows."""

    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"),
            {"email": email},
        )


def _record_activation_audit(
    session: Session,
    *,
    action: AccountActivationAuditAction,
    activation_id: str,
    actor_user_id: str,
    occurred_at: datetime,
) -> None:
    session.add(
        AuditLog(
            event=action.value,
            entity=ACCOUNT_ACTIVATION_ENTITY,
            entity_id=activation_id,
            user_id=actor_user_id,
            timestamp=occurred_at,
        )
    )


def issue_activation(
    session: Session,
    *,
    recipient_email: object,
    intended_role: object,
    created_by_user_id: object,
    expires_at: datetime,
    now: datetime | None = None,
) -> IssuedActivation:
    """Stage one recipient-bound activation and return its raw bearer once."""

    current = _utc_now(now)
    expiry = _utc_now(expires_at)
    if expiry <= current:
        raise ValueError("expiry must be in the future")

    email = normalize_recipient_email(recipient_email)
    role = normalize_role(intended_role)
    actor = _require_admin_operator(session, created_by_user_id)
    _serialize_recipient_issuance(session, email)

    if _account_for_email(session, email) is not None:
        raise ActivationConflictError(
            "recipient already has a canonical account"
        )

    outstanding = session.scalar(
        select(AccountActivationCapability)
        .where(
            AccountActivationCapability.recipient_email == email,
            AccountActivationCapability.consumed_at.is_(None),
            AccountActivationCapability.revoked_at.is_(None),
            AccountActivationCapability.expires_at > current,
        )
        .with_for_update()
    )
    if outstanding is not None:
        raise ActivationConflictError(
            "recipient already has a usable activation; revoke it first"
        )

    raw_token = generate_activation_token()
    capability = AccountActivationCapability(
        activation_id=str(uuid4()),
        token_digest=digest_activation_token(raw_token),
        recipient_email=email,
        intended_role=role,
        created_by_user_id=actor.id,
        created_at=current,
        expires_at=expiry,
    )
    session.add(capability)
    _record_activation_audit(
        session,
        action=AccountActivationAuditAction.ISSUED,
        activation_id=capability.activation_id,
        actor_user_id=actor.id,
        occurred_at=current,
    )
    session.flush()
    return IssuedActivation(capability=capability, raw_token=raw_token)


def revoke_activation(
    session: Session,
    *,
    activation_id: object,
    actor_user_id: object,
    now: datetime | None = None,
) -> AccountActivationCapability:
    """Stage a history-preserving operator revocation."""

    current = _utc_now(now)
    actor = _require_admin_operator(session, actor_user_id)
    durable_id = str(activation_id or "").strip()
    if not durable_id or len(durable_id) > 64:
        raise ActivationNotFoundError("activation was not found")

    capability = session.scalar(
        select(AccountActivationCapability)
        .where(AccountActivationCapability.activation_id == durable_id)
        .with_for_update()
    )
    if capability is None:
        raise ActivationNotFoundError("activation was not found")
    if capability.consumed_at is not None:
        raise ActivationStateError("consumed activation cannot be revoked")
    if capability.revoked_at is not None:
        raise ActivationStateError("activation is already revoked")

    capability.revoked_at = current
    _record_activation_audit(
        session,
        action=AccountActivationAuditAction.REVOKED,
        activation_id=capability.activation_id,
        actor_user_id=actor.id,
        occurred_at=current,
    )
    session.flush()
    return capability


def redeem_activation(
    session: Session,
    *,
    raw_token: object,
    password: object,
    now: datetime | None = None,
) -> User:
    """Atomically stage canonical User creation and capability consumption."""

    current = _utc_now(now)
    password_value = str(password or "").strip()
    if not password_value:
        raise ValueError("password is required")
    try:
        token_digest = digest_activation_token(raw_token)
    except ValueError as exc:
        raise ActivationUnavailableError("activation_unavailable") from exc

    capability = session.scalar(
        select(AccountActivationCapability)
        .where(AccountActivationCapability.token_digest == token_digest)
        .with_for_update()
    )
    if (
        capability is None
        or capability.consumed_at is not None
        or capability.revoked_at is not None
        or _comparable_utc(capability.expires_at) <= current
    ):
        raise ActivationUnavailableError("activation_unavailable")

    if _account_for_email(session, capability.recipient_email) is not None:
        raise ActivationUnavailableError("activation_unavailable")

    user = User(
        id=capability.recipient_email,
        username=capability.recipient_email,
        email=capability.recipient_email,
        password_hash=hash_password(password_value),
        role=capability.intended_role,
        created_at=current,
    )
    session.add(user)
    capability.consumed_at = current
    capability.resulting_user_id = user.id
    _record_activation_audit(
        session,
        action=AccountActivationAuditAction.REDEEMED,
        activation_id=capability.activation_id,
        actor_user_id=user.id,
        occurred_at=current,
    )
    session.flush()
    return user


__all__ = [
    "ActivationAuthorizationError",
    "ActivationConflictError",
    "ActivationNotFoundError",
    "ActivationStateError",
    "ActivationUnavailableError",
    "CANONICAL_ACCOUNT_ROLES",
    "IssuedActivation",
    "issue_activation",
    "normalize_actor_user_id",
    "normalize_recipient_email",
    "normalize_role",
    "redeem_activation",
    "revoke_activation",
]
