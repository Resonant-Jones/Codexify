"""Dedicated worker for already-captured GitHub Watchdog review dispatches."""

from __future__ import annotations

import logging
import os
import re
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.config import get_settings as get_core_settings
from guardian.core.dependencies import get_database_dsn
from guardian.db.models import (
    GitHubWatchdogReviewAttempt,
    GitHubWatchdogReviewDispatch,
    GitHubWatchdogReviewInputSnapshot,
    GitHubWatchdogReviewResult,
)
from guardian.queue.redis_queue import dequeue_watchdog_review
from guardian.tasks.types import GITHUB_WATCHDOG_REVIEW_TASK_TYPE
from guardian.watchdog.contracts import (
    WatchdogReviewAttemptState,
    WatchdogReviewDispatchErrorCode,
    WatchdogReviewDispatchState,
    WatchdogReviewExecutionErrorCode,
    WatchdogReviewInputSnapshotState,
    WatchdogReviewResultState,
)
from guardian.watchdog.review_execution import (
    GitHubWatchdogReviewExecutionService,
    WatchdogReviewExecutionError,
    WatchdogReviewExecutionResult,
)

logger = logging.getLogger(__name__)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_REQUIRED_ENVELOPE_KEYS = frozenset(
    {
        "task_id",
        "type",
        "dispatch_id",
        "review_attempt_id",
        "created_at",
    }
)
_TERMINAL_DISPATCH_STATES = frozenset(
    {
        WatchdogReviewDispatchState.COMPLETED.value,
        WatchdogReviewDispatchState.FAILED.value,
        WatchdogReviewDispatchState.BLOCKED.value,
        WatchdogReviewDispatchState.DISCARDED_SUPERSEDED.value,
        WatchdogReviewDispatchState.ENQUEUE_FAILED.value,
    }
)


@dataclass(frozen=True)
class _WatchdogQueueEnvelope:
    task_id: str
    dispatch_id: str
    review_attempt_id: str


@dataclass(frozen=True)
class _ExecutionClaim:
    dispatch_id: str
    review_attempt_id: str


class GitHubWatchdogReviewWorker:
    """Consume one Watchdog-only Redis envelope and delegate model execution."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        execution_service: GitHubWatchdogReviewExecutionService,
        dequeue_fn: Callable[..., dict[str, Any] | None] | None = None,
        worker_id: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._execution_service = execution_service
        self._dequeue_fn = dequeue_fn or dequeue_watchdog_review
        self.worker_id = worker_id or _default_worker_id()

    def process_once(
        self,
        *,
        block: bool = False,
        timeout: int | None = None,
    ) -> str | None:
        """Consume at most one envelope so focused tests never start a loop."""
        payload = self._dequeue_fn(block=block, timeout=timeout)
        if payload is None:
            return None
        return self.process_envelope(payload)

    def process_envelope(self, payload: object) -> str | None:
        """Validate Redis metadata, claim Postgres truth, then call the executor."""
        envelope = _parse_envelope(payload)
        if envelope is None:
            logger.warning("[watchdog-review-worker] invalid_queue_envelope")
            return None
        logger.info(
            "[watchdog-review-worker] dequeued dispatch_id=%s review_attempt_id=%s",
            envelope.dispatch_id,
            envelope.review_attempt_id,
        )
        claim = self._claim_dispatch(envelope)
        if claim is None:
            return envelope.dispatch_id

        try:
            execution = self._execution_service.execute_review_attempt(
                claim.review_attempt_id
            )
        except WatchdogReviewExecutionError as exc:
            self._handle_execution_error(claim, exc)
            return claim.dispatch_id
        except Exception:
            logger.exception(
                "[watchdog-review-worker] executor_error dispatch_id=%s "
                "review_attempt_id=%s",
                claim.dispatch_id,
                claim.review_attempt_id,
            )
            return claim.dispatch_id

        self._map_execution_result(claim, execution)
        return claim.dispatch_id

    def _claim_dispatch(
        self,
        envelope: _WatchdogQueueEnvelope,
    ) -> _ExecutionClaim | None:
        try:
            with self._session_factory() as session:
                dispatch = session.scalar(
                    select(GitHubWatchdogReviewDispatch)
                    .where(
                        GitHubWatchdogReviewDispatch.dispatch_id
                        == envelope.dispatch_id
                    )
                    .with_for_update()
                )
                if dispatch is None:
                    logger.warning(
                        "[watchdog-review-worker] unknown_dispatch dispatch_id=%s",
                        envelope.dispatch_id,
                    )
                    return None
                if (
                    dispatch.review_attempt_id != envelope.review_attempt_id
                    or dispatch.queue_task_id != envelope.task_id
                ):
                    logger.warning(
                        "[watchdog-review-worker] queue_identity_mismatch "
                        "dispatch_id=%s review_attempt_id=%s",
                        envelope.dispatch_id,
                        envelope.review_attempt_id,
                    )
                    return None
                if dispatch.dispatch_state in _TERMINAL_DISPATCH_STATES:
                    return None
                if dispatch.dispatch_state == WatchdogReviewDispatchState.RUNNING.value:
                    return None
                if dispatch.dispatch_state != WatchdogReviewDispatchState.QUEUED.value:
                    return None

                attempt = session.scalar(
                    select(GitHubWatchdogReviewAttempt)
                    .where(
                        GitHubWatchdogReviewAttempt.review_attempt_id
                        == dispatch.review_attempt_id
                    )
                    .with_for_update()
                )
                snapshot = session.scalar(
                    select(GitHubWatchdogReviewInputSnapshot)
                    .where(
                        GitHubWatchdogReviewInputSnapshot.review_attempt_id
                        == dispatch.review_attempt_id
                    )
                    .with_for_update()
                )
                result = session.scalar(
                    select(GitHubWatchdogReviewResult)
                    .where(
                        GitHubWatchdogReviewResult.review_attempt_id
                        == dispatch.review_attempt_id
                    )
                    .with_for_update()
                )
                if _attempt_is_superseded(attempt):
                    _terminalize_dispatch(
                        dispatch,
                        WatchdogReviewDispatchState.DISCARDED_SUPERSEDED,
                        WatchdogReviewDispatchErrorCode.ATTEMPT_SUPERSEDED.value,
                    )
                    session.commit()
                    return None
                if result is not None and (
                    result.result_state != WatchdogReviewResultState.RUNNING.value
                ):
                    _map_result_to_dispatch(dispatch, result)
                    session.commit()
                    return None
                if result is not None:
                    now = _utcnow()
                    dispatch.dispatch_state = WatchdogReviewDispatchState.RUNNING.value
                    dispatch.worker_id = self.worker_id
                    dispatch.started_at = dispatch.started_at or now
                    dispatch.review_result_id = result.result_id
                    dispatch.updated_at = now
                    session.commit()
                    return _ExecutionClaim(
                        dispatch_id=dispatch.dispatch_id,
                        review_attempt_id=dispatch.review_attempt_id,
                    )
                error_code = _pre_execution_error(dispatch, attempt, snapshot)
                if error_code is not None:
                    _terminalize_dispatch(
                        dispatch,
                        WatchdogReviewDispatchState.FAILED,
                        error_code,
                    )
                    session.commit()
                    return None

                now = _utcnow()
                dispatch.dispatch_state = WatchdogReviewDispatchState.RUNNING.value
                dispatch.worker_id = self.worker_id
                dispatch.started_at = dispatch.started_at or now
                dispatch.updated_at = now
                session.commit()
                logger.info(
                    "[watchdog-review-worker] started dispatch_id=%s "
                    "review_attempt_id=%s worker_id=%s",
                    dispatch.dispatch_id,
                    dispatch.review_attempt_id,
                    self.worker_id,
                )
                return _ExecutionClaim(
                    dispatch_id=dispatch.dispatch_id,
                    review_attempt_id=dispatch.review_attempt_id,
                )
        except Exception:
            logger.exception(
                "[watchdog-review-worker] dispatch_claim_error dispatch_id=%s "
                "review_attempt_id=%s",
                envelope.dispatch_id,
                envelope.review_attempt_id,
            )
            return None

    def _handle_execution_error(
        self,
        claim: _ExecutionClaim,
        error: WatchdogReviewExecutionError,
    ) -> None:
        if error.code == WatchdogReviewExecutionErrorCode.RESULT_PERSISTENCE_FAILED:
            logger.warning(
                "[watchdog-review-worker] execution_state_uncertain dispatch_id=%s "
                "review_attempt_id=%s error_code=%s",
                claim.dispatch_id,
                claim.review_attempt_id,
                error.code.value,
            )
            return
        try:
            with self._session_factory() as session:
                dispatch = session.scalar(
                    select(GitHubWatchdogReviewDispatch)
                    .where(GitHubWatchdogReviewDispatch.dispatch_id == claim.dispatch_id)
                    .with_for_update()
                )
                result = session.scalar(
                    select(GitHubWatchdogReviewResult)
                    .where(
                        GitHubWatchdogReviewResult.review_attempt_id
                        == claim.review_attempt_id
                    )
                    .with_for_update()
                )
                if dispatch is None or dispatch.dispatch_state != (
                    WatchdogReviewDispatchState.RUNNING.value
                ):
                    return
                if result is not None:
                    if result.result_state != WatchdogReviewResultState.RUNNING.value:
                        _map_result_to_dispatch(dispatch, result)
                        session.commit()
                    return
                state = (
                    WatchdogReviewDispatchState.DISCARDED_SUPERSEDED
                    if error.code == WatchdogReviewExecutionErrorCode.ATTEMPT_SUPERSEDED
                    else WatchdogReviewDispatchState.FAILED
                )
                _terminalize_dispatch(
                    dispatch,
                    state,
                    error.code.value,
                )
                session.commit()
        except Exception:
            logger.exception(
                "[watchdog-review-worker] execution_error_persistence_failed "
                "dispatch_id=%s review_attempt_id=%s",
                claim.dispatch_id,
                claim.review_attempt_id,
            )

    def _map_execution_result(
        self,
        claim: _ExecutionClaim,
        execution: WatchdogReviewExecutionResult,
    ) -> None:
        try:
            with self._session_factory() as session:
                dispatch = session.scalar(
                    select(GitHubWatchdogReviewDispatch)
                    .where(GitHubWatchdogReviewDispatch.dispatch_id == claim.dispatch_id)
                    .with_for_update()
                )
                result = session.scalar(
                    select(GitHubWatchdogReviewResult)
                    .where(
                        GitHubWatchdogReviewResult.result_id == execution.result_id
                    )
                    .with_for_update()
                )
                if dispatch is None or result is None:
                    return
                if dispatch.dispatch_state in _TERMINAL_DISPATCH_STATES:
                    return
                _map_result_to_dispatch(dispatch, result)
                session.commit()
                logger.info(
                    "[watchdog-review-worker] result_state dispatch_id=%s "
                    "review_attempt_id=%s result_state=%s terminal_error_code=%s",
                    dispatch.dispatch_id,
                    dispatch.review_attempt_id,
                    result.result_state,
                    result.terminal_error_code,
                )
        except Exception:
            logger.exception(
                "[watchdog-review-worker] result_mapping_failed dispatch_id=%s "
                "review_attempt_id=%s",
                claim.dispatch_id,
                claim.review_attempt_id,
            )


def _parse_envelope(payload: object) -> _WatchdogQueueEnvelope | None:
    if not isinstance(payload, dict) or set(payload) != _REQUIRED_ENVELOPE_KEYS:
        return None
    if payload.get("type") != GITHUB_WATCHDOG_REVIEW_TASK_TYPE:
        return None
    task_id = payload.get("task_id")
    dispatch_id = payload.get("dispatch_id")
    review_attempt_id = payload.get("review_attempt_id")
    created_at = payload.get("created_at")
    if not all(
        isinstance(value, str) and _IDENTIFIER.fullmatch(value)
        for value in (task_id, dispatch_id, review_attempt_id)
    ):
        return None
    if not isinstance(created_at, str) or not created_at.strip() or len(created_at) > 64:
        return None
    return _WatchdogQueueEnvelope(
        task_id=task_id,
        dispatch_id=dispatch_id,
        review_attempt_id=review_attempt_id,
    )


def _attempt_is_superseded(attempt: GitHubWatchdogReviewAttempt | None) -> bool:
    return attempt is not None and (
        attempt.attempt_state == WatchdogReviewAttemptState.SUPERSEDED.value
        or attempt.superseded_by_attempt_id is not None
    )


def _pre_execution_error(
    dispatch: GitHubWatchdogReviewDispatch,
    attempt: GitHubWatchdogReviewAttempt | None,
    snapshot: GitHubWatchdogReviewInputSnapshot | None,
) -> str | None:
    if attempt is None:
        return WatchdogReviewDispatchErrorCode.ATTEMPT_NOT_FOUND.value
    if attempt.attempt_state != WatchdogReviewAttemptState.PREPARED.value:
        return WatchdogReviewDispatchErrorCode.ATTEMPT_NOT_ELIGIBLE.value
    if snapshot is None:
        return WatchdogReviewDispatchErrorCode.SNAPSHOT_MISSING.value
    if snapshot.capture_state != WatchdogReviewInputSnapshotState.CAPTURED.value:
        return WatchdogReviewDispatchErrorCode.SNAPSHOT_NOT_CAPTURED.value
    if (
        snapshot.review_attempt_id != attempt.review_attempt_id
        or snapshot.snapshot_id != dispatch.review_input_snapshot_id
        or snapshot.snapshot_sha256 != dispatch.snapshot_sha256
        or snapshot.expected_head_sha != attempt.head_sha
        or snapshot.observed_head_sha != attempt.head_sha
        or dispatch.head_sha != attempt.head_sha
    ):
        return WatchdogReviewDispatchErrorCode.SNAPSHOT_IDENTITY_MISMATCH.value
    if not snapshot.snapshot_sha256:
        return WatchdogReviewDispatchErrorCode.SNAPSHOT_DIGEST_MISSING.value
    return None


def _map_result_to_dispatch(
    dispatch: GitHubWatchdogReviewDispatch,
    result: GitHubWatchdogReviewResult,
) -> None:
    dispatch.review_result_id = result.result_id
    dispatch.updated_at = _utcnow()
    if result.result_state == WatchdogReviewResultState.RUNNING.value:
        return
    mapping = {
        WatchdogReviewResultState.COMPLETED.value: WatchdogReviewDispatchState.COMPLETED,
        WatchdogReviewResultState.BLOCKED_RUNTIME_POLICY.value: WatchdogReviewDispatchState.BLOCKED,
        WatchdogReviewResultState.FAILED_PROVIDER.value: WatchdogReviewDispatchState.FAILED,
        WatchdogReviewResultState.FAILED_OUTPUT_CONTRACT.value: WatchdogReviewDispatchState.FAILED,
        WatchdogReviewResultState.DISCARDED_SUPERSEDED.value: (
            WatchdogReviewDispatchState.DISCARDED_SUPERSEDED
        ),
    }
    state = mapping.get(result.result_state)
    if state is None:
        return
    _terminalize_dispatch(dispatch, state, result.terminal_error_code)


def _terminalize_dispatch(
    dispatch: GitHubWatchdogReviewDispatch,
    state: WatchdogReviewDispatchState,
    error_code: str | None,
) -> None:
    now = _utcnow()
    dispatch.dispatch_state = state.value
    dispatch.terminal_error_code = error_code
    dispatch.completed_at = now
    dispatch.updated_at = now


def _default_worker_id() -> str:
    return f"watchdog-review:{socket.gethostname()}:{os.getpid()}"[:255]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _runtime_session_factory() -> sessionmaker:
    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError("GitHub Watchdog review worker requires a Postgres DSN")
    engine = create_engine(dsn, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def run_worker_loop() -> None:
    """Run the opt-in worker loop; no recovery or replay policy is implied."""
    session_factory = _runtime_session_factory()
    worker = GitHubWatchdogReviewWorker(
        session_factory=session_factory,
        execution_service=GitHubWatchdogReviewExecutionService(
            session_factory=session_factory,
            settings=get_core_settings(),
        ),
    )
    logger.info("[watchdog-review-worker] started worker_id=%s", worker.worker_id)
    while True:
        try:
            worker.process_once(block=True, timeout=5)
        except Exception:
            logger.exception("[watchdog-review-worker] dequeue_error")
            time.sleep(1)


if __name__ == "__main__":
    run_worker_loop()
