"""Durable preparation of bounded GitHub Watchdog review attempts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.dependencies import get_database_dsn
from guardian.db.models import (
    GitHubWatchdogDeliveryReceipt,
    GitHubWatchdogReviewAttempt,
)
from guardian.watchdog.contracts import (
    GITHUB_PULL_REQUEST_SYNCHRONIZE_ACTION,
    WatchdogOperation,
    WatchdogPolicyResolutionState,
    WatchdogReviewAttemptState,
    is_automated_review_trigger,
)
from guardian.watchdog.policy import (
    WatchdogPolicySnapshot,
    block_policy_for_missing_head_sha,
    resolve_automated_review_policy,
)


class WatchdogReviewAttemptStoreUnavailable(RuntimeError):
    """Raised when durable Watchdog attempt storage is not configured."""


class WatchdogReviewAttemptPersistenceError(RuntimeError):
    """Raised when attempt preparation cannot persist its durable truth."""


class WatchdogReviewAttemptReceiptNotFound(RuntimeError):
    """Raised when an attempt is requested for a missing delivery receipt."""


class WatchdogReviewAttemptNotActionable(RuntimeError):
    """Raised when a receipt is outside the automatic-review trigger scope."""


class ReviewAttemptPreparationResult:
    """Bounded attempt truth returned to authenticated webhook intake."""

    def __init__(
        self,
        *,
        review_attempt_id: str,
        attempt_state: str,
        policy_resolution_state: str,
    ) -> None:
        self.review_attempt_id = review_attempt_id
        self.attempt_state = attempt_state
        self.policy_resolution_state = policy_resolution_state


_runtime_session_factory: sessionmaker | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_runtime_session_factory() -> sessionmaker:
    """Build the Postgres session factory only when preparation is requested."""
    global _runtime_session_factory
    if _runtime_session_factory is not None:
        return _runtime_session_factory

    dsn = get_database_dsn()
    if not dsn:
        raise WatchdogReviewAttemptStoreUnavailable(
            "GitHub Watchdog attempt storage requires a Postgres DSN"
        )
    try:
        engine = create_engine(dsn, future=True)
    except Exception as exc:
        raise WatchdogReviewAttemptStoreUnavailable(
            "GitHub Watchdog attempt storage is unavailable"
        ) from exc
    _runtime_session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return _runtime_session_factory


class GitHubWatchdogReviewAttemptPreparer:
    """Create one receipt-bound attempt and preserve immutable policy truth."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        self._session_factory = session_factory or _get_runtime_session_factory()

    def prepare_from_receipt(
        self,
        *,
        trigger_receipt_id: str,
        settings: Any,
    ) -> ReviewAttemptPreparationResult:
        """Prepare one automatic-review attempt or reuse it for redelivery."""
        try:
            with self._session_factory() as session:
                existing = self._find_by_trigger_receipt(session, trigger_receipt_id)
                if existing is not None:
                    return self._result(existing)

                receipt = session.get(GitHubWatchdogDeliveryReceipt, trigger_receipt_id)
                if receipt is None:
                    raise WatchdogReviewAttemptReceiptNotFound(
                        "delivery receipt does not exist"
                    )
                if not is_automated_review_trigger(receipt.event_name, receipt.action):
                    raise WatchdogReviewAttemptNotActionable(
                        "delivery receipt is not an automatic-review trigger"
                    )

                policy_snapshot = resolve_automated_review_policy(settings)
                resolved_snapshot = policy_snapshot
                if not receipt.head_sha:
                    resolved_snapshot = block_policy_for_missing_head_sha(
                        policy_snapshot
                    )

                now = _utcnow()
                row = GitHubWatchdogReviewAttempt(
                    review_attempt_id=f"wra_{uuid4().hex}",
                    trigger_receipt_id=receipt.receipt_id,
                    github_delivery_id=receipt.github_delivery_id,
                    installation_id=receipt.installation_id,
                    repository_id=receipt.repository_id,
                    repository_full_name=receipt.repository_full_name,
                    pull_request_number=receipt.pull_request_number,
                    head_sha=receipt.head_sha,
                    operation=WatchdogOperation.AUTOMATED_REVIEW.value,
                    attempt_number=1,
                    attempt_state=self._attempt_state_for(resolved_snapshot),
                    policy_resolution_state=(resolved_snapshot.policy_resolution_state),
                    provider_id=resolved_snapshot.provider_id,
                    model_id=resolved_snapshot.model_id,
                    inference_mode=resolved_snapshot.inference_mode,
                    model_selection_source=(resolved_snapshot.model_selection_source),
                    policy_fingerprint=resolved_snapshot.policy_fingerprint,
                    escalation_mode=resolved_snapshot.escalation_mode,
                    escalation_provider_id=(resolved_snapshot.escalation_provider_id),
                    escalation_model_id=resolved_snapshot.escalation_model_id,
                    policy_reason_code=resolved_snapshot.policy_reason_code,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                try:
                    session.flush()
                except IntegrityError as exc:
                    session.rollback()
                    existing = self._find_by_trigger_receipt(
                        session, trigger_receipt_id
                    )
                    if existing is None:
                        raise WatchdogReviewAttemptPersistenceError(
                            "attempt insert lost without an existing attempt"
                        ) from exc
                    return self._result(existing)

                self._supersede_older_prepared_attempts(
                    session, receipt=receipt, replacement=row, now=now
                )
                try:
                    session.commit()
                except Exception as exc:
                    session.rollback()
                    raise WatchdogReviewAttemptPersistenceError(
                        "attempt preparation commit failed"
                    ) from exc
                session.refresh(row)
                return self._result(row)
        except (
            WatchdogReviewAttemptNotActionable,
            WatchdogReviewAttemptReceiptNotFound,
            WatchdogReviewAttemptPersistenceError,
        ):
            raise
        except Exception as exc:
            raise WatchdogReviewAttemptPersistenceError(
                "attempt preparation failed"
            ) from exc

    @staticmethod
    def _find_by_trigger_receipt(
        session: Session,
        trigger_receipt_id: str,
    ) -> GitHubWatchdogReviewAttempt | None:
        statement = select(GitHubWatchdogReviewAttempt).where(
            GitHubWatchdogReviewAttempt.trigger_receipt_id == trigger_receipt_id
        )
        return session.scalars(statement).first()

    @staticmethod
    def _attempt_state_for(snapshot: WatchdogPolicySnapshot) -> str:
        if (
            snapshot.policy_resolution_state
            == WatchdogPolicyResolutionState.RESOLVED.value
        ):
            return WatchdogReviewAttemptState.PREPARED.value
        return WatchdogReviewAttemptState.BLOCKED_POLICY.value

    @staticmethod
    def _result(
        row: GitHubWatchdogReviewAttempt,
    ) -> ReviewAttemptPreparationResult:
        return ReviewAttemptPreparationResult(
            review_attempt_id=row.review_attempt_id,
            attempt_state=row.attempt_state,
            policy_resolution_state=row.policy_resolution_state,
        )

    @staticmethod
    def _supersede_older_prepared_attempts(
        session: Session,
        *,
        receipt: GitHubWatchdogDeliveryReceipt,
        replacement: GitHubWatchdogReviewAttempt,
        now: datetime,
    ) -> None:
        if (
            receipt.action != GITHUB_PULL_REQUEST_SYNCHRONIZE_ACTION
            or not receipt.head_sha
            or receipt.repository_id is None
            or receipt.pull_request_number is None
        ):
            return
        statement = (
            select(GitHubWatchdogReviewAttempt)
            .where(
                GitHubWatchdogReviewAttempt.repository_id == receipt.repository_id,
                GitHubWatchdogReviewAttempt.pull_request_number
                == receipt.pull_request_number,
                GitHubWatchdogReviewAttempt.operation
                == WatchdogOperation.AUTOMATED_REVIEW.value,
                GitHubWatchdogReviewAttempt.attempt_state
                == WatchdogReviewAttemptState.PREPARED.value,
                GitHubWatchdogReviewAttempt.head_sha != receipt.head_sha,
            )
            .with_for_update()
        )
        for prior in session.scalars(statement):
            prior.attempt_state = WatchdogReviewAttemptState.SUPERSEDED.value
            prior.superseded_by_attempt_id = replacement.review_attempt_id
            prior.updated_at = now
