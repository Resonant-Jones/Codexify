"""Persist and transport one already-captured GitHub Watchdog review."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from guardian.db.models import (
    GitHubWatchdogReviewAttempt,
    GitHubWatchdogReviewDispatch,
    GitHubWatchdogReviewInputSnapshot,
    GitHubWatchdogReviewResult,
)
from guardian.queue.redis_queue import enqueue_watchdog_review
from guardian.watchdog.contracts import (
    WatchdogOperation,
    WatchdogPolicyResolutionState,
    WatchdogReviewAttemptState,
    WatchdogReviewDispatchErrorCode,
    WatchdogReviewDispatchState,
    WatchdogReviewInputSnapshotState,
)

QueueEnqueue = Callable[..., None]
logger = logging.getLogger(__name__)


class WatchdogReviewDispatchError(RuntimeError):
    """A bounded error from durable Watchdog dispatch preparation."""

    def __init__(self, code: WatchdogReviewDispatchErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True)
class WatchdogReviewDispatchResult:
    """Durable dispatch truth returned to an explicit caller."""

    dispatch_id: str
    review_attempt_id: str
    dispatch_state: str
    queue_task_id: str
    enqueue_count: int
    review_result_id: str | None
    terminal_error_code: str | None


@dataclass(frozen=True)
class _NewDispatchIntent:
    dispatch_id: str
    review_attempt_id: str
    queue_task_id: str
    created_at: str


class GitHubWatchdogReviewDispatchService:
    """Write Postgres dispatch intent before attempting Redis transport."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        enqueue_fn: QueueEnqueue | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._enqueue_fn = enqueue_fn or enqueue_watchdog_review

    def dispatch_review_attempt(
        self, review_attempt_id: str
    ) -> WatchdogReviewDispatchResult:
        """Create one durable intent, then attempt exactly one Redis enqueue."""
        existing, intent = self._create_or_recover_intent(review_attempt_id)
        if existing is not None:
            return existing
        assert intent is not None

        try:
            self._enqueue_fn(
                task_id=intent.queue_task_id,
                dispatch_id=intent.dispatch_id,
                review_attempt_id=intent.review_attempt_id,
                created_at=intent.created_at,
            )
        except Exception:
            logger.warning(
                "[watchdog-review-dispatch] enqueue_failed dispatch_id=%s "
                "review_attempt_id=%s error_code=%s",
                intent.dispatch_id,
                intent.review_attempt_id,
                WatchdogReviewDispatchErrorCode.QUEUE_ENQUEUE_FAILED.value,
            )
            return self._persist_enqueue_outcome(
                intent.dispatch_id,
                accepted=False,
            )
        logger.info(
            "[watchdog-review-dispatch] queue_accepted dispatch_id=%s "
            "review_attempt_id=%s",
            intent.dispatch_id,
            intent.review_attempt_id,
        )
        return self._persist_enqueue_outcome(intent.dispatch_id, accepted=True)

    def _create_or_recover_intent(
        self,
        review_attempt_id: str,
    ) -> tuple[WatchdogReviewDispatchResult | None, _NewDispatchIntent | None]:
        try:
            with self._session_factory() as session:
                existing = session.scalar(
                    _dispatch_for_attempt_statement(review_attempt_id).with_for_update()
                )
                if existing is not None:
                    return self._result(existing), None

                attempt = session.scalar(
                    select(GitHubWatchdogReviewAttempt)
                    .where(
                        GitHubWatchdogReviewAttempt.review_attempt_id
                        == review_attempt_id
                    )
                    .with_for_update()
                )
                snapshot = session.scalar(
                    _snapshot_for_attempt_statement(review_attempt_id).with_for_update()
                )
                result = session.scalar(
                    _result_for_attempt_statement(review_attempt_id).with_for_update()
                )
                _assert_dispatch_eligible(attempt, snapshot, result)
                assert attempt is not None
                assert snapshot is not None

                now = _utcnow()
                dispatch_id = f"wrd_{uuid4().hex}"
                queue_task_id = f"wdq_{uuid4().hex}"
                row = GitHubWatchdogReviewDispatch(
                    dispatch_id=dispatch_id,
                    review_attempt_id=attempt.review_attempt_id,
                    review_input_snapshot_id=snapshot.snapshot_id,
                    snapshot_sha256=snapshot.snapshot_sha256,
                    head_sha=attempt.head_sha,
                    dispatch_state=WatchdogReviewDispatchState.PENDING_ENQUEUE.value,
                    queue_task_id=queue_task_id,
                    enqueue_count=0,
                    last_enqueue_at=None,
                    worker_id=None,
                    started_at=None,
                    completed_at=None,
                    review_result_id=None,
                    terminal_error_code=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                try:
                    session.flush()
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    existing = session.scalar(
                        _dispatch_for_attempt_statement(review_attempt_id)
                    )
                    if existing is not None:
                        return self._result(existing), None
                    raise
                return None, _NewDispatchIntent(
                    dispatch_id=dispatch_id,
                    review_attempt_id=attempt.review_attempt_id,
                    queue_task_id=queue_task_id,
                    created_at=now.isoformat(),
                )
        except WatchdogReviewDispatchError:
            raise
        except Exception as exc:
            raise WatchdogReviewDispatchError(
                WatchdogReviewDispatchErrorCode.DISPATCH_PERSISTENCE_FAILED
            ) from exc

    def _persist_enqueue_outcome(
        self,
        dispatch_id: str,
        *,
        accepted: bool,
    ) -> WatchdogReviewDispatchResult:
        try:
            with self._session_factory() as session:
                row = session.scalar(
                    select(GitHubWatchdogReviewDispatch)
                    .where(GitHubWatchdogReviewDispatch.dispatch_id == dispatch_id)
                    .with_for_update()
                )
                if row is None:
                    raise WatchdogReviewDispatchError(
                        WatchdogReviewDispatchErrorCode.DISPATCH_PERSISTENCE_FAILED
                    )
                now = _utcnow()
                row.enqueue_count += 1
                row.last_enqueue_at = now
                row.updated_at = now
                if row.dispatch_state == WatchdogReviewDispatchState.PENDING_ENQUEUE.value:
                    if accepted:
                        row.dispatch_state = WatchdogReviewDispatchState.QUEUED.value
                        row.terminal_error_code = None
                    else:
                        row.dispatch_state = (
                            WatchdogReviewDispatchState.ENQUEUE_FAILED.value
                        )
                        row.terminal_error_code = (
                            WatchdogReviewDispatchErrorCode.QUEUE_ENQUEUE_FAILED.value
                        )
                        row.completed_at = now
                session.commit()
                return self._result(row)
        except WatchdogReviewDispatchError:
            raise
        except Exception as exc:
            raise WatchdogReviewDispatchError(
                WatchdogReviewDispatchErrorCode.DISPATCH_PERSISTENCE_FAILED
            ) from exc

    @staticmethod
    def _result(
        row: GitHubWatchdogReviewDispatch,
    ) -> WatchdogReviewDispatchResult:
        return WatchdogReviewDispatchResult(
            dispatch_id=row.dispatch_id,
            review_attempt_id=row.review_attempt_id,
            dispatch_state=row.dispatch_state,
            queue_task_id=row.queue_task_id,
            enqueue_count=row.enqueue_count,
            review_result_id=row.review_result_id,
            terminal_error_code=row.terminal_error_code,
        )


def _assert_dispatch_eligible(
    attempt: GitHubWatchdogReviewAttempt | None,
    snapshot: GitHubWatchdogReviewInputSnapshot | None,
    result: GitHubWatchdogReviewResult | None,
) -> None:
    if attempt is None:
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.ATTEMPT_NOT_FOUND
        )
    if (
        attempt.attempt_state == WatchdogReviewAttemptState.SUPERSEDED.value
        or attempt.superseded_by_attempt_id is not None
    ):
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.ATTEMPT_SUPERSEDED
        )
    if (
        attempt.operation != WatchdogOperation.AUTOMATED_REVIEW.value
        or attempt.policy_resolution_state
        != WatchdogPolicyResolutionState.RESOLVED.value
        or attempt.attempt_state != WatchdogReviewAttemptState.PREPARED.value
    ):
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.ATTEMPT_NOT_ELIGIBLE
        )
    if snapshot is None:
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.SNAPSHOT_MISSING
        )
    if snapshot.capture_state != WatchdogReviewInputSnapshotState.CAPTURED.value:
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.SNAPSHOT_NOT_CAPTURED
        )
    if (
        snapshot.review_attempt_id != attempt.review_attempt_id
        or snapshot.expected_head_sha != attempt.head_sha
        or snapshot.observed_head_sha != attempt.head_sha
    ):
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.SNAPSHOT_IDENTITY_MISMATCH
        )
    if not snapshot.snapshot_sha256:
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.SNAPSHOT_DIGEST_MISSING
        )
    if result is not None:
        raise WatchdogReviewDispatchError(
            WatchdogReviewDispatchErrorCode.REVIEW_RESULT_EXISTS
        )


def _dispatch_for_attempt_statement(review_attempt_id: str) -> Any:
    return select(GitHubWatchdogReviewDispatch).where(
        GitHubWatchdogReviewDispatch.review_attempt_id == review_attempt_id
    )


def _snapshot_for_attempt_statement(review_attempt_id: str) -> Any:
    return select(GitHubWatchdogReviewInputSnapshot).where(
        GitHubWatchdogReviewInputSnapshot.review_attempt_id == review_attempt_id
    )


def _result_for_attempt_statement(review_attempt_id: str) -> Any:
    return select(GitHubWatchdogReviewResult).where(
        GitHubWatchdogReviewResult.review_attempt_id == review_attempt_id
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "GitHubWatchdogReviewDispatchService",
    "WatchdogReviewDispatchError",
    "WatchdogReviewDispatchResult",
]
