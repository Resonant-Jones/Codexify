"""Server-owned storage for GitHub Knowledge integration credentials."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from guardian.connectors.oauth_crypto import decrypt_token, encrypt_token
from guardian.db import models as db_models
from guardian.connections import knowledge_oauth, oauth_store

VALIDATION_UNVALIDATED = "unvalidated"
VALIDATION_VALID = "valid"
VALIDATION_AUTHORIZATION_ERROR = "authorization_error"
VALIDATION_TRANSPORT_ERROR = "transport_error"
VALIDATION_PROVIDER_ERROR = "provider_error"


def _record(db: Any, user_id: str) -> db_models.GitHubKnowledgeCredential | None:
    with db.get_session() as session:
        return (
            session.query(db_models.GitHubKnowledgeCredential)
            .filter_by(user_id=user_id)
            .one_or_none()
        )


def configured_connection(db: Any, user_id: str) -> tuple[str, list[str]] | None:
    """Resolve a credential only inside the provider execution boundary."""
    if knowledge_oauth.enabled() and oauth_store.status(db, user_id, "github").get(
        "generation"
    ):
        try:
            snapshot = knowledge_oauth.credential(db, user_id, "github")
        except knowledge_oauth.KnowledgeOAuthError:
            return None
        return (
            (snapshot.access_token, snapshot.repositories)
            if snapshot is not None and snapshot.repositories
            else None
        )
    record = _record(db, user_id)
    if record is None:
        return None
    token = decrypt_token(record.encrypted_token)
    return (token, list(record.repositories)) if token else None


def configure_token(db: Any, user_id: str, token: str, repositories: list[str]) -> None:
    """Replace the current user's token and invalidate prior validation."""
    encrypted = encrypt_token(token)
    with db.get_session() as session:
        record = (
            session.query(db_models.GitHubKnowledgeCredential)
            .filter_by(user_id=user_id)
            .with_for_update()
            .one_or_none()
        )
        if record is None:
            session.add(
                db_models.GitHubKnowledgeCredential(
                    user_id=user_id,
                    encrypted_token=encrypted,
                    repositories=list(repositories),
                    validation_status=VALIDATION_UNVALIDATED,
                )
            )
        else:
            record.encrypted_token = encrypted
            record.repositories = list(repositories)
            record.validation_status = VALIDATION_UNVALIDATED
            record.last_validated_at = None
        session.commit()


def mark_validation(
    db: Any,
    user_id: str,
    status: str,
    *,
    expected_connection: tuple[str, list[str]] | None = None,
) -> None:
    """Persist only a bounded validation classification, never error text."""
    if knowledge_oauth.enabled() and oauth_store.status(db, user_id, "github").get(
        "generation"
    ):
        expected = expected_connection[0] if expected_connection else None
        if status == VALIDATION_AUTHORIZATION_ERROR and expected:
            oauth_store.invalidate_credential(db, user_id, "github", expected)
        return
    with db.get_session() as session:
        record = (
            session.query(db_models.GitHubKnowledgeCredential)
            .filter_by(user_id=user_id)
            .with_for_update()
            .one_or_none()
        )
        if record is None:
            return
        if expected_connection is not None:
            token, repositories = expected_connection
            if (
                decrypt_token(record.encrypted_token) != token
                or list(record.repositories) != repositories
            ):
                return
        record.validation_status = status
        record.last_validated_at = datetime.now(timezone.utc)
        session.commit()


def disconnect(db: Any, user_id: str) -> bool:
    """Remove the user's credential record; no provider mutation is made."""
    oauth_removed = (
        oauth_store.disconnect(db, user_id, "github")
        if knowledge_oauth.enabled()
        else False
    )
    with db.get_session() as session:
        record = (
            session.query(db_models.GitHubKnowledgeCredential)
            .filter_by(user_id=user_id)
            .one_or_none()
        )
        if record is None:
            return oauth_removed
        session.delete(record)
        session.commit()
        return True


def status_projection(db: Any, user_id: str) -> dict[str, Any]:
    """Return safe status metadata for routes and Connections projection."""
    if knowledge_oauth.enabled():
        status = oauth_store.status(db, user_id, "github")
        if status.get("generation"):
            return {
                **status,
                "state": "valid" if status["configured"] else status["state"],
                "last_validated_at": None,
            }
    record = _record(db, user_id)
    if record is None:
        return {
            "configured": False,
            "state": "unconfigured",
            "last_validated_at": None,
        }
    return {
        "configured": True,
        "repositories": list(record.repositories),
        "state": str(record.validation_status),
        "last_validated_at": (
            record.last_validated_at.isoformat()
            if record.last_validated_at is not None
            else None
        ),
    }
