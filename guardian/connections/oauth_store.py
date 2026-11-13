"""Durable OAuth custody for the two read-only Knowledge pilots.

No network requests occur in transactions. Conditional writes fence stale callbacks,
rotating refreshes and disconnects. A crashed refresh fails closed until reconnect;
we never retry a possibly consumed rotating refresh token automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import secrets
import time
from typing import Any

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from guardian.connectors.oauth_crypto import decrypt_token, encrypt_token
from guardian.db.models import KnowledgeOAuthCredential as Credential
from guardian.db.models import KnowledgeOAuthFlow as Flow
from guardian.db.models import (
    User,
    NotionConnectionCredential,
    GitHubKnowledgeCredential,
)


class OAuthStateError(ValueError):
    """Bounded error safe to expose; never includes codes, state or tokens."""


@dataclass(frozen=True)
class FlowStart:
    state: str = field(repr=False)
    code_verifier: str = field(repr=False)
    generation: str


@dataclass(frozen=True)
class ConsumedFlow:
    user_id: str
    provider: str
    generation: str
    code_verifier: str = field(repr=False)
    redirect_uri: str
    repositories: list[str]


@dataclass(frozen=True)
class CredentialSnapshot:
    user_id: str
    provider: str
    generation: str
    access_token: str = field(repr=False)
    refresh_token: str | None = field(repr=False)
    expires_at: float | None
    metadata: dict[str, Any]
    repositories: list[str]


@dataclass(frozen=True)
class RefreshClaim:
    credential: CredentialSnapshot
    claim_id: str = field(repr=False)


def _scope(user_id: str, provider: str) -> None:
    if provider not in {"notion", "github"} or not user_id or len(user_id) > 255:
        raise OAuthStateError("oauth_scope_invalid")


def _query(session: Any, user_id: str, provider: str) -> Any:
    return session.query(Credential).filter_by(user_id=user_id, provider=provider)


def _blank(generation: str, status: str) -> dict[str, Any]:
    return dict(
        generation=generation,
        status=status,
        encrypted_access_token=None,
        encrypted_refresh_token=None,
        expires_at=None,
        refresh_claim=None,
        provider_metadata={},
        repositories=[],
    )


def _delete_legacy(session: Any, user_id: str, provider: str) -> int:
    model = (
        NotionConnectionCredential
        if provider == "notion"
        else GitHubKnowledgeCredential
    )
    return (
        session.query(model)
        .filter_by(user_id=user_id)
        .delete(synchronize_session=False)
    )


def begin_flow(
    db: Any,
    user_id: str,
    provider: str,
    redirect_uri: str,
    repositories: list[str] | None = None,
    *,
    browser_binding: str,
) -> FlowStart:
    _scope(user_id, provider)
    state, verifier, generation = (
        secrets.token_urlsafe(32),
        secrets.token_urlsafe(48),
        secrets.token_hex(24),
    )
    if not browser_binding or len(browser_binding) > 256:
        raise OAuthStateError("oauth_browser_binding_invalid")
    encrypted = encrypt_token(verifier)
    # Concurrent first inserts can conflict. Retry only the rolled-back transaction.
    for attempt in range(2):
        try:
            with db.get_session() as session:
                _delete_legacy(session, user_id, provider)
                values = _blank(generation, "pending")
                row = _query(session, user_id, provider).with_for_update().one_or_none()
                if row is None:
                    session.add(
                        Credential(user_id=user_id, provider=provider, **values)
                    )
                else:
                    for key, value in values.items():
                        setattr(row, key, value)
                session.add(
                    Flow(
                        state_hash=hashlib.sha256(state.encode()).hexdigest(),
                        user_id=user_id,
                        provider=provider,
                        generation=generation,
                        encrypted_verifier=encrypted,
                        redirect_uri=redirect_uri,
                        browser_binding_hash=hashlib.sha256(
                            browser_binding.encode()
                        ).hexdigest(),
                        expires_at=time.time() + 600,
                        consumed=False,
                        repositories=list(repositories or []),
                    )
                )
                session.commit()
            return FlowStart(state, verifier, generation)
        except IntegrityError:
            if attempt:
                raise OAuthStateError("oauth_storage_conflict") from None
    raise OAuthStateError("oauth_storage_conflict")


def consume_flow(
    db: Any, provider: str, state: str, *, browser_binding: str
) -> ConsumedFlow:
    _scope("callback", provider)
    if not isinstance(state, str) or not 32 <= len(state) <= 256:
        raise OAuthStateError("oauth_state_invalid")
    if not browser_binding or len(browser_binding) > 256:
        raise OAuthStateError("oauth_browser_binding_invalid")
    digest = hashlib.sha256(state.encode()).hexdigest()
    with db.get_session() as session:
        result = session.execute(
            update(Flow)
            .where(
                Flow.state_hash == digest,
                Flow.provider == provider,
                Flow.browser_binding_hash
                == hashlib.sha256(browser_binding.encode()).hexdigest(),
                Flow.consumed.is_(False),
                Flow.expires_at > time.time(),
            )
            .values(consumed=True)
        )
        if result.rowcount != 1:
            raise OAuthStateError("oauth_state_invalid")
        row = session.query(Flow).filter_by(state_hash=digest).one()
        user_id = row.user_id
        current = _query(session, user_id, provider).one_or_none()
        if (
            current is None
            or current.generation != row.generation
            or current.status != "pending"
        ):
            session.commit()  # Invalidated states remain consumed.
            raise OAuthStateError("oauth_state_invalid")
        flow = ConsumedFlow(
            user_id,
            provider,
            row.generation,
            decrypt_token(row.encrypted_verifier) or "",
            row.redirect_uri,
            list(row.repositories),
        )
        session.commit()
        return flow


def _tokens(
    access_token: str,
    refresh_token: str | None,
    expires_in: float | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    if not access_token or len(access_token) > 16384:
        raise OAuthStateError("oauth_token_invalid")
    if refresh_token is not None and (not refresh_token or len(refresh_token) > 16384):
        raise OAuthStateError("oauth_token_invalid")
    if expires_in is not None and not 0 < expires_in <= 365 * 86400:
        raise OAuthStateError("oauth_expiry_invalid")
    return dict(
        encrypted_access_token=encrypt_token(access_token),
        encrypted_refresh_token=encrypt_token(refresh_token),
        expires_at=time.time() + expires_in if expires_in else None,
        provider_metadata=dict(metadata or {}),
        status="connected",
        refresh_claim=None,
    )


def complete_flow(
    db: Any,
    flow: ConsumedFlow,
    access_token: str,
    refresh_token: str | None = None,
    expires_in: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    values = _tokens(access_token, refresh_token, expires_in, metadata)
    with db.get_session() as session:
        if (
            session.query(User.id).filter_by(id=flow.user_id).with_for_update().scalar()
            is None
        ):
            return False
        count = (
            _query(session, flow.user_id, flow.provider)
            .filter_by(generation=flow.generation, status="pending")
            .update(
                dict(**values, repositories=list(flow.repositories)),
                synchronize_session=False,
            )
        )
        session.commit()
        return count == 1


def credential(db: Any, user_id: str, provider: str) -> CredentialSnapshot | None:
    _scope(user_id, provider)
    with db.get_session() as session:
        if session.query(User.id).filter_by(id=user_id).scalar() is None:
            return None
        row = (
            _query(session, user_id, provider)
            .filter_by(status="connected")
            .one_or_none()
        )
        if row is None or row.refresh_claim is not None:
            return None
        return CredentialSnapshot(
            user_id,
            provider,
            row.generation,
            decrypt_token(row.encrypted_access_token) or "",
            decrypt_token(row.encrypted_refresh_token),
            row.expires_at,
            dict(row.provider_metadata),
            list(row.repositories),
        )


def status(db: Any, user_id: str, provider: str) -> dict[str, Any]:
    _scope(user_id, provider)
    with db.get_session() as session:
        row = _query(session, user_id, provider).one_or_none()
        connected = bool(
            row and row.status == "connected" and row.refresh_claim is None
        )
        needs_scope = connected and provider == "github" and not row.repositories
        return {
            "state": "needs_scope"
            if needs_scope
            else (
                "reconnect_required"
                if row and row.refresh_claim is not None
                else (row.status if row else "unconfigured")
            ),
            "configured": connected and not needs_scope,
            "generation": row.generation if row else None,
            "provider_metadata": dict(row.provider_metadata) if row else {},
            "repositories": list(row.repositories) if row else [],
        }


def disconnect(db: Any, user_id: str, provider: str) -> bool:
    _scope(user_id, provider)
    for attempt in range(2):
        try:
            with db.get_session() as session:
                deleted = _delete_legacy(session, user_id, provider)
                row = _query(session, user_id, provider).with_for_update().one_or_none()
                existed = row is not None or deleted > 0
                values = _blank(secrets.token_hex(24), "disconnected")
                if row is None:
                    session.add(
                        Credential(user_id=user_id, provider=provider, **values)
                    )
                else:
                    for key, value in values.items():
                        setattr(row, key, value)
                session.commit()
                return existed
        except IntegrityError:
            if attempt:
                raise OAuthStateError("oauth_storage_conflict") from None
    raise OAuthStateError("oauth_storage_conflict")


def claim_refresh(db: Any, user_id: str, provider: str) -> RefreshClaim | None:
    snapshot = credential(db, user_id, provider)
    if snapshot is None or not snapshot.refresh_token:
        return None
    claim = secrets.token_hex(24)
    with db.get_session() as session:
        count = (
            _query(session, user_id, provider)
            .filter_by(
                generation=snapshot.generation, status="connected", refresh_claim=None
            )
            .update({"refresh_claim": claim}, synchronize_session=False)
        )
        session.commit()
        return RefreshClaim(snapshot, claim) if count == 1 else None


def complete_refresh(
    db: Any,
    claim: RefreshClaim,
    access_token: str,
    refresh_token: str | None = None,
    expires_in: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    snapshot = claim.credential
    values = _tokens(
        access_token,
        refresh_token,
        expires_in,
        metadata if metadata is not None else snapshot.metadata,
    )
    values["generation"] = secrets.token_hex(24)
    with db.get_session() as session:
        if (
            session.query(User.id)
            .filter_by(id=snapshot.user_id)
            .with_for_update()
            .scalar()
            is None
        ):
            return False
        count = (
            _query(session, snapshot.user_id, snapshot.provider)
            .filter_by(
                generation=snapshot.generation,
                status="connected",
                refresh_claim=claim.claim_id,
            )
            .update(values, synchronize_session=False)
        )
        session.commit()
        return count == 1


def fail_refresh(db: Any, claim: RefreshClaim) -> None:
    snapshot = claim.credential
    with db.get_session() as session:
        _query(session, snapshot.user_id, snapshot.provider).filter_by(
            generation=snapshot.generation, refresh_claim=claim.claim_id
        ).update(
            _blank(secrets.token_hex(24), "reconnect_required"),
            synchronize_session=False,
        )
        session.commit()


def save_repositories(
    db: Any,
    user_id: str,
    provider: str,
    generation: str,
    installation_id: str,
    repositories: list[str],
) -> bool:
    _scope(user_id, provider)
    if provider != "github" or not repositories or len(repositories) > 20:
        raise OAuthStateError("oauth_scope_invalid")
    with db.get_session() as session:
        row = (
            _query(session, user_id, provider)
            .filter_by(generation=generation, status="connected", refresh_claim=None)
            .with_for_update()
            .one_or_none()
        )
        if row is None:
            return False
        row.generation = secrets.token_hex(24)
        row.repositories = list(repositories)
        row.provider_metadata = dict(
            row.provider_metadata, installation_id=str(installation_id)
        )
        session.commit()
        return True


def invalidate_credential(
    db: Any, user_id: str, provider: str, expected_access_token: str
) -> bool:
    """Fence a provider rejection against the exact token that was attempted.

    Never apply a delayed failure to a rotated or reconnected credential. No
    external revocation is performed; this only disables local credential use.
    """
    _scope(user_id, provider)
    if not isinstance(expected_access_token, str) or not expected_access_token:
        return False
    with db.get_session() as session:
        row = (
            _query(session, user_id, provider)
            .filter_by(status="connected")
            .one_or_none()
        )
        if row is None:
            return False
        token = decrypt_token(row.encrypted_access_token)
        if not token or not secrets.compare_digest(
            token.encode(), expected_access_token.encode()
        ):
            return False
        count = (
            _query(session, user_id, provider)
            .filter_by(
                generation=row.generation,
                status="connected",
                encrypted_access_token=row.encrypted_access_token,
            )
            .update(
                _blank(secrets.token_hex(24), "reconnect_required"),
                synchronize_session=False,
            )
        )
        session.commit()
        return count == 1
