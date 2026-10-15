"""Guardian authority for invocation-scoped coding credentials.

Only API keys are exportable in this initial slice. Owner scope, funding route,
revocation, and eligibility are checked both before queue dispatch and at the
execution-time lease boundary. Durable records contain encrypted custody or
opaque references, never plaintext provider secrets.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from guardian.connectors.oauth_crypto import decrypt_token, encrypt_token
from guardian.db.models import CodingExecutionCredential, CodingExecutionCredentialLease

ACCOUNT_FUNDING_ROUTE = "user_byok"
SERVICE_FUNDING_ROUTES = frozenset({"codexify_included", "codexify_metered"})
OPERATOR_FUNDING_ROUTE = "local_self_hosted"
SUPPORTED_OWNER_SCOPES = frozenset({"account", "service", "operator"})
LEASE_LIFETIME = timedelta(minutes=2)


class CredentialAuthorityError(RuntimeError):
    """Safe, stable denial code; messages never include credential material."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_credential(row: CodingExecutionCredential) -> dict[str, Any]:
    source = {
        "account": "account_api_key",
        "service": "service_api_key",
        "operator": "operator_api_key",
    }.get(row.owner_scope, "unknown")
    return {
        "credential_ref": row.credential_ref,
        "owner_scope": row.owner_scope,
        "owner_id": row.owner_id,
        "provider_id": row.provider_id,
        "credential_type": row.credential_type,
        "funding_route": row.funding_route,
        "source_class": source,
        "status": row.status,
        "usage_policy_ref": row.usage_policy_ref,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
    }


def store_api_key(
    db: Any,
    *,
    owner_scope: str,
    owner_id: str,
    provider_id: str,
    api_key: str,
    funding_route: str,
    allowed_account_ids: list[str] | None = None,
    allowed_model_ids: list[str] | None = None,
    usage_policy_ref: str | None = None,
) -> dict[str, Any]:
    """Store an encrypted API key under one explicit canonical owner."""
    scope = _text(owner_scope).lower()
    owner = _text(owner_id)
    provider = _text(provider_id).lower()
    route = _text(funding_route).lower()
    secret = str(api_key or "").strip()
    if scope not in SUPPORTED_OWNER_SCOPES or not owner or not provider or not secret:
        raise CredentialAuthorityError("credential_input_invalid")
    if scope == "account" and route != ACCOUNT_FUNDING_ROUTE:
        raise CredentialAuthorityError("account_funding_route_invalid")
    if scope == "service":
        if route not in SERVICE_FUNDING_ROUTES:
            raise CredentialAuthorityError("service_funding_route_invalid")
        if not allowed_account_ids or not allowed_model_ids or not _text(usage_policy_ref):
            raise CredentialAuthorityError("service_policy_incomplete")
    if scope == "operator" and route != OPERATOR_FUNDING_ROUTE:
        raise CredentialAuthorityError("operator_funding_route_invalid")

    encrypted = encrypt_token(secret)
    if not encrypted:
        raise CredentialAuthorityError("credential_encryption_unavailable")
    row = CodingExecutionCredential(
        credential_ref=f"ccr_{uuid4().hex}",
        owner_scope=scope,
        owner_id=owner,
        provider_id=provider,
        credential_type="api_key",
        funding_route=route,
        encrypted_secret=encrypted,
        status="active",
        allowed_account_ids=sorted({_text(value) for value in allowed_account_ids or [] if _text(value)}),
        allowed_model_ids=sorted({_text(value) for value in allowed_model_ids or [] if _text(value)}),
        usage_policy_ref=_text(usage_policy_ref) or None,
    )
    try:
        with db.get_session() as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            return _safe_credential(row)
    except Exception as exc:
        raise CredentialAuthorityError("credential_storage_unavailable") from exc


def list_account_credentials(db: Any, *, account_id: str) -> list[dict[str, Any]]:
    account = _text(account_id)
    if not account:
        raise CredentialAuthorityError("account_identity_missing")
    with db.get_session() as session:
        rows = (
            session.query(CodingExecutionCredential)
            .filter_by(owner_scope="account", owner_id=account)
            .order_by(CodingExecutionCredential.created_at.desc())
            .all()
        )
        return [_safe_credential(row) for row in rows]


def revoke_account_credential(
    db: Any, *, account_id: str, credential_ref: str
) -> bool:
    account = _text(account_id)
    ref = _text(credential_ref)
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(
                credential_ref=ref,
                owner_scope="account",
                owner_id=account,
            )
            .with_for_update()
            .one_or_none()
        )
        if row is None:
            return False
        if row.status != "revoked":
            row.status = "revoked"
            row.encrypted_secret = None
            row.revoked_at = _now()
            session.commit()
        return True


def authorize_binding_credential(
    db: Any,
    *,
    binding: dict[str, Any],
    account_id: str,
) -> dict[str, Any]:
    """Revalidate owner, provider/model, funding route, expiry, and policy."""
    ref = _text(binding.get("credential_ref"))
    account = _text(account_id)
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(credential_ref=ref)
            .one_or_none()
        )
        _validate_row(row, binding=binding, account_id=account)
        assert row is not None
        return _safe_credential(row)


def authorize_credential_selection(
    db: Any,
    *,
    credential_ref: str,
    account_id: str,
    provider_id: str,
    model_id: str,
) -> dict[str, Any]:
    """Resolve a caller-selected opaque reference under Guardian policy."""
    ref = _text(credential_ref)
    account = _text(account_id)
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(credential_ref=ref)
            .one_or_none()
        )
        if row is None:
            raise CredentialAuthorityError("credential_reference_missing")
        binding = {
            "credential_ref": row.credential_ref,
            "credential_owner_scope": row.owner_scope,
            "credential_owner_id": row.owner_id,
            "provider_id": _text(provider_id),
            "model_id": _text(model_id),
            "funding_route": row.funding_route,
            "usage_policy_ref": row.usage_policy_ref,
            "user_id": account,
        }
        _validate_row(row, binding=binding, account_id=account)
        return _safe_credential(row)


def issue_api_key_lease(
    db: Any,
    *,
    binding: dict[str, Any],
    account_id: str,
    attempt_id: str,
    attempt_index: int,
) -> tuple[str, dict[str, Any]]:
    """Revalidate and return an API key once for one bound attempt."""
    binding_id = _text(binding.get("binding_id"))
    attempt = _text(attempt_id)
    account = _text(account_id)
    if not binding_id or not attempt or attempt_index < 1:
        raise CredentialAuthorityError("credential_lease_identity_invalid")
    if attempt != _text(binding.get("attempt_id")):
        raise CredentialAuthorityError("credential_attempt_binding_mismatch")
    now = _now()
    with db.get_session() as session:
        row = (
            session.query(CodingExecutionCredential)
            .filter_by(credential_ref=_text(binding.get("credential_ref")))
            .with_for_update()
            .one_or_none()
        )
        _validate_row(row, binding=binding, account_id=account)
        assert row is not None
        max_attempts = int(binding.get("max_attempts") or 0)
        if attempt_index > max_attempts:
            raise CredentialAuthorityError("credential_attempt_not_authorized")

        try:
            lease = CodingExecutionCredentialLease(
                lease_id=f"cl_{uuid4().hex}",
                binding_id=binding_id,
                attempt_id=attempt,
                attempt_index=attempt_index,
                credential_ref=row.credential_ref,
                owner_scope=row.owner_scope,
                owner_id=row.owner_id,
                account_id=account,
                issued_at=now,
                expires_at=now + LEASE_LIFETIME,
            )
            session.add(lease)
            session.flush()
            secret = decrypt_token(row.encrypted_secret)
            if not secret:
                raise CredentialAuthorityError("credential_secret_unavailable")
            safe_lease = {
                "lease_id": lease.lease_id,
                "binding_id": lease.binding_id,
                "credential_ref": row.credential_ref,
                "owner_scope": row.owner_scope,
                "owner_id": row.owner_id,
                "credential_owner_scope": row.owner_scope,
                "credential_owner_id": row.owner_id,
                "account_id": account,
                "provider_id": row.provider_id,
                "model_id": _text(binding.get("model_id")),
                "funding_route": row.funding_route,
                "source_class": _safe_credential(row)["source_class"],
                "harness_id": _text(binding.get("harness_id")),
                "harness_selection_mode": _text(
                    binding.get("harness_selection_mode")
                ),
                "usage_policy_ref": row.usage_policy_ref,
                "attempt_id": attempt,
                "attempt_index": attempt_index,
                "expires_at": lease.expires_at.isoformat(),
            }
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise CredentialAuthorityError("credential_attempt_already_leased") from exc
        except CredentialAuthorityError:
            session.rollback()
            raise
        except Exception as exc:
            session.rollback()
            raise CredentialAuthorityError("credential_lease_unavailable") from exc
        return secret, safe_lease


def _validate_row(
    row: CodingExecutionCredential | None,
    *,
    binding: dict[str, Any],
    account_id: str,
) -> None:
    if row is None:
        raise CredentialAuthorityError("credential_reference_missing")
    if row.status != "active" or not row.encrypted_secret:
        raise CredentialAuthorityError("credential_revoked_or_missing")
    if row.credential_type != "api_key":
        raise CredentialAuthorityError("credential_type_unsupported")
    if row.expires_at is not None:
        expiry = row.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= _now():
            raise CredentialAuthorityError("credential_expired")
    if row.provider_id != _text(binding.get("provider_id")):
        raise CredentialAuthorityError("credential_provider_mismatch")
    if row.owner_scope != _text(binding.get("credential_owner_scope")):
        raise CredentialAuthorityError("credential_owner_scope_mismatch")
    if row.owner_id != _text(binding.get("credential_owner_id")):
        raise CredentialAuthorityError("credential_owner_mismatch")
    if row.funding_route != _text(binding.get("funding_route")):
        raise CredentialAuthorityError("credential_funding_route_mismatch")
    if _text(binding.get("user_id")) != account_id:
        raise CredentialAuthorityError("credential_account_binding_mismatch")
    if row.owner_scope == "account":
        if row.owner_id != account_id or row.funding_route != ACCOUNT_FUNDING_ROUTE:
            raise CredentialAuthorityError("account_credential_owner_mismatch")
        if binding.get("usage_policy_ref") not in (None, ""):
            raise CredentialAuthorityError("account_usage_policy_unexpected")
    elif row.owner_scope == "service":
        if row.funding_route not in SERVICE_FUNDING_ROUTES:
            raise CredentialAuthorityError("service_funding_route_invalid")
        if account_id not in (row.allowed_account_ids or []):
            raise CredentialAuthorityError("service_account_policy_denied")
        if _text(binding.get("model_id")) not in (row.allowed_model_ids or []):
            raise CredentialAuthorityError("service_model_policy_denied")
        if not _text(row.usage_policy_ref):
            raise CredentialAuthorityError("service_usage_policy_missing")
        if _text(binding.get("usage_policy_ref")) != _text(row.usage_policy_ref):
            raise CredentialAuthorityError("service_usage_policy_mismatch")
    elif row.owner_scope == "operator":
        raise CredentialAuthorityError("operator_credential_not_authorized_for_account")
    else:
        raise CredentialAuthorityError("credential_owner_scope_unsupported")
