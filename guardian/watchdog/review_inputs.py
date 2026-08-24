"""Capture immutable, model-neutral GitHub PR review-input snapshots."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from guardian.db.models import (
    GitHubWatchdogReviewAttempt,
    GitHubWatchdogReviewInputSnapshot,
)
from guardian.watchdog.contracts import (
    WatchdogGitHubAppError,
    WatchdogGitHubAppErrorCode,
    WatchdogOperation,
    WatchdogPolicyResolutionState,
    WatchdogReviewAttemptState,
    WatchdogReviewInputCaptureError,
    WatchdogReviewInputCaptureErrorCode,
    WatchdogReviewInputSnapshotState,
)
from guardian.watchdog.github_app import (
    GitHubPullRequestFilesResult,
    GitHubPullRequestMetadata,
    GitHubWatchdogAppReadClient,
    validate_pull_request_head,
)

REVIEW_INPUT_SNAPSHOT_VERSION = 1
GitHubClientFactory = Callable[[object, str], GitHubWatchdogAppReadClient]


@dataclass(frozen=True)
class ReviewInputCaptureResult:
    """The terminal durable capture truth for one review attempt."""

    snapshot_id: str
    review_attempt_id: str
    capture_state: str
    snapshot_sha256: str | None
    block_error_code: str | None


@dataclass(frozen=True)
class _AttemptCaptureContext:
    review_attempt_id: str
    installation_id: str
    repository_id: str
    repository_full_name: str
    pull_request_number: int
    expected_head_sha: str


class GitHubWatchdogReviewInputCaptureService:
    """Capture one immutable terminal snapshot without model or queue coupling."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        settings: object,
        github_client_factory: GitHubClientFactory | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._github_client_factory = (
            github_client_factory or self._default_github_client_factory
        )

    def capture_review_input(self, review_attempt_id: str) -> ReviewInputCaptureResult:
        """Persist one complete source-consistent snapshot or a terminal block."""
        existing, context = self._load_existing_or_context(review_attempt_id)
        if existing is not None:
            return self._result(existing)
        assert context is not None

        client = self._github_client_factory(self._settings, context.installation_id)
        try:
            pre_read = client.get_pull_request(
                context.repository_full_name,
                context.pull_request_number,
            )
            if not self._same_repository_and_pr(context, pre_read):
                return self._persist_terminal(
                    context,
                    capture_state=WatchdogReviewInputSnapshotState.BLOCKED_STALE,
                    error_code=(
                        WatchdogReviewInputCaptureErrorCode.SOURCE_CHANGED_DURING_CAPTURE
                    ),
                    observed_head_sha=pre_read.head_sha,
                    base_sha=pre_read.base_sha,
                    observed_base_sha=pre_read.base_sha,
                )

            head_validation = validate_pull_request_head(
                pre_read,
                context.expected_head_sha,
            )
            if not head_validation.matches:
                return self._persist_terminal(
                    context,
                    capture_state=WatchdogReviewInputSnapshotState.BLOCKED_STALE,
                    error_code=WatchdogReviewInputCaptureErrorCode.LIVE_HEAD_MISMATCH,
                    observed_head_sha=pre_read.head_sha,
                    base_sha=pre_read.base_sha,
                    observed_base_sha=pre_read.base_sha,
                )

            changed_files = client.get_pull_request_files(
                context.repository_full_name,
                context.pull_request_number,
            )
            if changed_files.limit_error_code is not None:
                return self._persist_terminal(
                    context,
                    capture_state=WatchdogReviewInputSnapshotState.BLOCKED_LIMITS,
                    error_code=changed_files.limit_error_code,
                    observed_head_sha=pre_read.head_sha,
                    base_sha=pre_read.base_sha,
                    observed_base_sha=pre_read.base_sha,
                    changed_file_count=changed_files.changed_file_count,
                    files_without_patch_count=(
                        changed_files.files_without_patch_count
                    ),
                    captured_patch_bytes=changed_files.patch_bytes,
                )

            post_read = client.get_pull_request(
                context.repository_full_name,
                context.pull_request_number,
            )
        except WatchdogGitHubAppError as exc:
            raise _capture_error_from_github_error(exc) from exc

        if not self._source_is_consistent(context, pre_read, post_read):
            return self._persist_terminal(
                context,
                capture_state=WatchdogReviewInputSnapshotState.BLOCKED_STALE,
                error_code=(
                    WatchdogReviewInputCaptureErrorCode.SOURCE_CHANGED_DURING_CAPTURE
                ),
                observed_head_sha=post_read.head_sha,
                base_sha=pre_read.base_sha,
                observed_base_sha=post_read.base_sha,
            )

        return self._persist_captured(context, pre_read, post_read, changed_files)

    def _default_github_client_factory(
        self,
        settings: object,
        installation_id: str,
    ) -> GitHubWatchdogAppReadClient:
        return GitHubWatchdogAppReadClient(
            settings=settings,
            installation_id=installation_id,
        )

    def _load_existing_or_context(
        self,
        review_attempt_id: str,
    ) -> tuple[GitHubWatchdogReviewInputSnapshot | None, _AttemptCaptureContext | None]:
        try:
            with self._session_factory() as session:
                existing = session.scalar(
                    _snapshot_for_attempt_statement(review_attempt_id)
                )
                if existing is not None:
                    return existing, None
                attempt = session.get(GitHubWatchdogReviewAttempt, review_attempt_id)
                if attempt is None:
                    raise WatchdogReviewInputCaptureError(
                        WatchdogReviewInputCaptureErrorCode.ATTEMPT_NOT_FOUND
                    )
                return None, _context_from_eligible_attempt(attempt)
        except WatchdogReviewInputCaptureError:
            raise
        except Exception as exc:
            raise WatchdogReviewInputCaptureError(
                WatchdogReviewInputCaptureErrorCode.SNAPSHOT_PERSISTENCE_FAILED,
                retryable=True,
            ) from exc

    @staticmethod
    def _same_repository_and_pr(
        context: _AttemptCaptureContext,
        pull_request: GitHubPullRequestMetadata,
    ) -> bool:
        return (
            pull_request.repository_id == context.repository_id
            and pull_request.repository_full_name == context.repository_full_name
            and pull_request.pull_request_number == context.pull_request_number
        )

    def _source_is_consistent(
        self,
        context: _AttemptCaptureContext,
        pre_read: GitHubPullRequestMetadata,
        post_read: GitHubPullRequestMetadata,
    ) -> bool:
        return (
            self._same_repository_and_pr(context, post_read)
            and pre_read.head_sha == context.expected_head_sha
            and post_read.head_sha == context.expected_head_sha
            and post_read.head_sha == pre_read.head_sha
            and post_read.base_sha == pre_read.base_sha
        )

    def _persist_captured(
        self,
        context: _AttemptCaptureContext,
        pre_read: GitHubPullRequestMetadata,
        post_read: GitHubPullRequestMetadata,
        changed_files: GitHubPullRequestFilesResult,
    ) -> ReviewInputCaptureResult:
        canonical_files = _canonical_changed_files(changed_files)
        aggregates = _aggregate_changes(changed_files)
        canonical_input = _canonical_review_input(
            context=context,
            pull_request=pre_read,
            changed_files=canonical_files,
            aggregates=aggregates,
            files_without_patch_count=changed_files.files_without_patch_count,
        )
        digest = hashlib.sha256(canonical_input).hexdigest()
        return self._persist_row(
            context,
            {
                "capture_state": WatchdogReviewInputSnapshotState.CAPTURED.value,
                "observed_head_sha": post_read.head_sha,
                "base_sha": pre_read.base_sha,
                "observed_base_sha": post_read.base_sha,
                "pull_request_title": pre_read.title,
                "pull_request_body": pre_read.body,
                "author_id": pre_read.author_id,
                "author_login": pre_read.author_login,
                "draft": pre_read.draft,
                "changed_file_count": changed_files.changed_file_count,
                "files_without_patch_count": changed_files.files_without_patch_count,
                "aggregate_additions": aggregates["additions"],
                "aggregate_deletions": aggregates["deletions"],
                "aggregate_changes": aggregates["changes"],
                "changed_files_json": canonical_files,
                "captured_patch_bytes": changed_files.patch_bytes,
                "snapshot_sha256": digest,
                "block_error_code": None,
            },
        )

    def _persist_terminal(
        self,
        context: _AttemptCaptureContext,
        *,
        capture_state: WatchdogReviewInputSnapshotState,
        error_code: WatchdogReviewInputCaptureErrorCode,
        observed_head_sha: str | None,
        base_sha: str | None,
        observed_base_sha: str | None,
        changed_file_count: int | None = None,
        files_without_patch_count: int | None = None,
        captured_patch_bytes: int | None = None,
    ) -> ReviewInputCaptureResult:
        return self._persist_row(
            context,
            {
                "capture_state": capture_state.value,
                "observed_head_sha": observed_head_sha,
                "base_sha": base_sha,
                "observed_base_sha": observed_base_sha,
                "pull_request_title": None,
                "pull_request_body": None,
                "author_id": None,
                "author_login": None,
                "draft": None,
                "changed_file_count": changed_file_count,
                "files_without_patch_count": files_without_patch_count,
                "aggregate_additions": None,
                "aggregate_deletions": None,
                "aggregate_changes": None,
                "changed_files_json": None,
                "captured_patch_bytes": captured_patch_bytes,
                "snapshot_sha256": None,
                "block_error_code": error_code.value,
            },
        )

    def _persist_row(
        self,
        context: _AttemptCaptureContext,
        attributes: dict[str, Any],
    ) -> ReviewInputCaptureResult:
        try:
            with self._session_factory() as session:
                existing = session.scalar(
                    _snapshot_for_attempt_statement(context.review_attempt_id)
                )
                if existing is not None:
                    return self._result(existing)

                attempt = session.get(
                    GitHubWatchdogReviewAttempt,
                    context.review_attempt_id,
                )
                if attempt is None:
                    raise WatchdogReviewInputCaptureError(
                        WatchdogReviewInputCaptureErrorCode.ATTEMPT_NOT_FOUND
                    )
                if _context_from_eligible_attempt(attempt) != context:
                    raise WatchdogReviewInputCaptureError(
                        WatchdogReviewInputCaptureErrorCode.ATTEMPT_SUPERSEDED
                    )

                row = GitHubWatchdogReviewInputSnapshot(
                    snapshot_id=f"wri_{uuid4().hex}",
                    review_attempt_id=context.review_attempt_id,
                    installation_id=context.installation_id,
                    repository_id=context.repository_id,
                    repository_full_name=context.repository_full_name,
                    pull_request_number=context.pull_request_number,
                    expected_head_sha=context.expected_head_sha,
                    **attributes,
                )
                session.add(row)
                try:
                    session.flush()
                except IntegrityError as exc:
                    session.rollback()
                    existing = session.scalar(
                        _snapshot_for_attempt_statement(context.review_attempt_id)
                    )
                    if existing is not None:
                        return self._result(existing)
                    raise WatchdogReviewInputCaptureError(
                        WatchdogReviewInputCaptureErrorCode.SNAPSHOT_PERSISTENCE_FAILED,
                        retryable=True,
                    ) from exc
                session.commit()
                session.refresh(row)
                return self._result(row)
        except WatchdogReviewInputCaptureError:
            raise
        except Exception as exc:
            raise WatchdogReviewInputCaptureError(
                WatchdogReviewInputCaptureErrorCode.SNAPSHOT_PERSISTENCE_FAILED,
                retryable=True,
            ) from exc

    @staticmethod
    def _result(
        row: GitHubWatchdogReviewInputSnapshot,
    ) -> ReviewInputCaptureResult:
        return ReviewInputCaptureResult(
            snapshot_id=row.snapshot_id,
            review_attempt_id=row.review_attempt_id,
            capture_state=row.capture_state,
            snapshot_sha256=row.snapshot_sha256,
            block_error_code=row.block_error_code,
        )


def _context_from_eligible_attempt(
    attempt: GitHubWatchdogReviewAttempt,
) -> _AttemptCaptureContext:
    if (
        attempt.attempt_state == WatchdogReviewAttemptState.SUPERSEDED.value
        or attempt.superseded_by_attempt_id is not None
    ):
        raise WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.ATTEMPT_SUPERSEDED
        )
    if (
        attempt.operation != WatchdogOperation.AUTOMATED_REVIEW.value
        or attempt.attempt_state != WatchdogReviewAttemptState.PREPARED.value
        or attempt.policy_resolution_state
        != WatchdogPolicyResolutionState.RESOLVED.value
    ):
        raise WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.ATTEMPT_NOT_ELIGIBLE
        )
    if not attempt.installation_id:
        raise WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.INSTALLATION_ID_MISSING
        )
    if not attempt.repository_id or not attempt.repository_full_name:
        raise WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.REPOSITORY_IDENTITY_MISSING
        )
    if attempt.pull_request_number is None or attempt.pull_request_number <= 0:
        raise WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.PULL_REQUEST_IDENTITY_MISSING
        )
    if not _is_valid_git_sha(attempt.head_sha):
        raise WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.EXPECTED_HEAD_MISSING
        )
    return _AttemptCaptureContext(
        review_attempt_id=attempt.review_attempt_id,
        installation_id=attempt.installation_id,
        repository_id=attempt.repository_id,
        repository_full_name=attempt.repository_full_name,
        pull_request_number=attempt.pull_request_number,
        expected_head_sha=attempt.head_sha,
    )


def _canonical_changed_files(
    result: GitHubPullRequestFilesResult,
) -> list[dict[str, Any]]:
    return [
        {
            "additions": item.additions,
            "changes": item.changes,
            "deletions": item.deletions,
            "filename": item.filename,
            "patch": item.patch,
            "previousFilename": item.previous_filename,
            "status": item.status,
        }
        for item in sorted(
            result.files,
            key=lambda item: (item.filename, item.previous_filename or ""),
        )
    ]


def _aggregate_changes(result: GitHubPullRequestFilesResult) -> dict[str, int]:
    return {
        "additions": sum(item.additions for item in result.files),
        "deletions": sum(item.deletions for item in result.files),
        "changes": sum(item.changes for item in result.files),
    }


def _canonical_review_input(
    *,
    context: _AttemptCaptureContext,
    pull_request: GitHubPullRequestMetadata,
    changed_files: list[dict[str, Any]],
    aggregates: dict[str, int],
    files_without_patch_count: int,
) -> bytes:
    payload = {
        "aggregates": aggregates,
        "changedFiles": changed_files,
        "filesWithoutPatchCount": files_without_patch_count,
        "pullRequest": {
            "authorId": pull_request.author_id,
            "authorLogin": pull_request.author_login,
            "baseSha": pull_request.base_sha,
            "body": pull_request.body,
            "draft": pull_request.draft,
            "headSha": pull_request.head_sha,
            "number": pull_request.pull_request_number,
            "repositoryFullName": pull_request.repository_full_name,
            "repositoryId": pull_request.repository_id,
            "title": pull_request.title,
        },
        "snapshotVersion": REVIEW_INPUT_SNAPSHOT_VERSION,
    }
    if (
        pull_request.repository_id != context.repository_id
        or pull_request.head_sha != context.expected_head_sha
    ):
        raise WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.SOURCE_CHANGED_DURING_CAPTURE
        )
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _snapshot_for_attempt_statement(review_attempt_id: str) -> Any:
    from sqlalchemy import select

    return select(GitHubWatchdogReviewInputSnapshot).where(
        GitHubWatchdogReviewInputSnapshot.review_attempt_id == review_attempt_id
    )


def _is_valid_git_sha(value: str | None) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _capture_error_from_github_error(
    error: WatchdogGitHubAppError,
) -> WatchdogReviewInputCaptureError:
    if error.code is WatchdogGitHubAppErrorCode.MALFORMED_GITHUB_RESPONSE:
        return WatchdogReviewInputCaptureError(
            WatchdogReviewInputCaptureErrorCode.MALFORMED_GITHUB_RESPONSE
        )
    return WatchdogReviewInputCaptureError(
        WatchdogReviewInputCaptureErrorCode.GITHUB_READ_FAILURE,
        retryable=error.code
        in {
            WatchdogGitHubAppErrorCode.TRANSPORT_FAILURE,
            WatchdogGitHubAppErrorCode.GITHUB_API_RATE_LIMITED,
            WatchdogGitHubAppErrorCode.GITHUB_API_REQUEST_REJECTED,
        },
    )


__all__ = [
    "GitHubWatchdogReviewInputCaptureService",
    "REVIEW_INPUT_SNAPSHOT_VERSION",
    "ReviewInputCaptureResult",
]
