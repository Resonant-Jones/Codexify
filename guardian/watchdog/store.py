"""Postgres-backed durable receipt persistence for GitHub Watchdog intake."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import GitHubWatchdogDeliveryReceipt
from guardian.watchdog.contracts import NormalizedGitHubDelivery


class WatchdogReceiptStoreUnavailable(RuntimeError):
    """Raised when Postgres receipt storage has not been configured."""


class WatchdogReceiptPersistenceError(RuntimeError):
    """Raised when a receipt cannot be durably written or updated."""


class ConflictingGitHubDeliveryError(RuntimeError):
    """Raised when an idempotency key is presented with a different body."""


class ReceiptPersistenceResult:
    """Receipt-level result of a durable insert or authenticated redelivery."""

    def __init__(self, *, receipt_id: str, duplicate: bool) -> None:
        self.receipt_id = receipt_id
        self.duplicate = duplicate


_runtime_session_factory: sessionmaker | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_runtime_session_factory() -> sessionmaker:
    """Resolve a dedicated Postgres ORM session factory only when needed."""
    global _runtime_session_factory
    if _runtime_session_factory is not None:
        return _runtime_session_factory

    dsn = get_database_dsn()
    if not dsn:
        raise WatchdogReceiptStoreUnavailable(
            "GitHub Watchdog receipt storage requires a Postgres DSN"
        )
    try:
        engine = create_engine(dsn, future=True)
    except Exception as exc:
        raise WatchdogReceiptStoreUnavailable(
            "GitHub Watchdog receipt storage is unavailable"
        ) from exc
    _runtime_session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _runtime_session_factory


class GitHubWatchdogDeliveryReceiptStore:
    """Race-safe receipt persistence for authenticated GitHub deliveries."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._session_factory = session_factory or _get_runtime_session_factory()

    def persist(self, delivery: NormalizedGitHubDelivery) -> ReceiptPersistenceResult:
        """Insert once or record an authenticated redelivery of the same body."""
        try:
            with self._session_factory() as session:
                existing = self._find_by_idempotency_key(
                    session, delivery.idempotency_key, lock=True
                )
                if existing is not None:
                    return self._reuse_or_reject_conflict(session, existing, delivery)

                now = _utcnow()
                row = GitHubWatchdogDeliveryReceipt(
                    receipt_id=f"gwd_{uuid4().hex}",
                    github_delivery_id=delivery.github_delivery_id,
                    idempotency_key=delivery.idempotency_key,
                    event_name=delivery.event_name,
                    action=delivery.action,
                    installation_id=delivery.installation_id,
                    repository_id=delivery.repository_id,
                    repository_full_name=delivery.repository_full_name,
                    trigger_actor_id=delivery.trigger_actor_id,
                    trigger_actor_login=delivery.trigger_actor_login,
                    pull_request_number=delivery.pull_request_number,
                    head_sha=delivery.head_sha,
                    payload_sha256=delivery.payload_sha256,
                    first_received_at=now,
                    last_received_at=now,
                    redelivery_count=0,
                )
                session.add(row)
                try:
                    session.commit()
                except IntegrityError as exc:
                    session.rollback()
                    existing = self._find_by_idempotency_key(
                        session, delivery.idempotency_key, lock=True
                    )
                    if existing is None:
                        raise WatchdogReceiptPersistenceError(
                            "receipt insert lost without an existing receipt"
                        ) from exc
                    return self._reuse_or_reject_conflict(session, existing, delivery)

                session.refresh(row)
                return ReceiptPersistenceResult(
                    receipt_id=row.receipt_id, duplicate=False
                )
        except (
            ConflictingGitHubDeliveryError,
            WatchdogReceiptPersistenceError,
        ):
            raise
        except Exception as exc:
            raise WatchdogReceiptPersistenceError("receipt persistence failed") from exc

    @staticmethod
    def _find_by_idempotency_key(
        session: Session,
        idempotency_key: str,
        *,
        lock: bool,
    ) -> GitHubWatchdogDeliveryReceipt | None:
        statement = select(GitHubWatchdogDeliveryReceipt).where(
            GitHubWatchdogDeliveryReceipt.idempotency_key == idempotency_key
        )
        if lock:
            statement = statement.with_for_update()
        return session.scalars(statement).first()

    @staticmethod
    def _reuse_or_reject_conflict(
        session: Session,
        existing: GitHubWatchdogDeliveryReceipt,
        delivery: NormalizedGitHubDelivery,
    ) -> ReceiptPersistenceResult:
        if not hmac.compare_digest(existing.payload_sha256, delivery.payload_sha256):
            raise ConflictingGitHubDeliveryError("delivery digest conflict")

        existing.redelivery_count += 1
        existing.last_received_at = _utcnow()
        try:
            session.commit()
        except Exception as exc:
            session.rollback()
            raise WatchdogReceiptPersistenceError(
                "redelivery evidence update failed"
            ) from exc
        session.refresh(existing)
        return ReceiptPersistenceResult(receipt_id=existing.receipt_id, duplicate=True)
