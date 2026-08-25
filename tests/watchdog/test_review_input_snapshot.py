"""Proof for immutable, source-consistent Watchdog review-input capture."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    GitHubWatchdogDeliveryReceipt,
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
)
from guardian.watchdog.github_app import (
    GitHubPullRequestFile,
    GitHubPullRequestFilesResult,
    GitHubPullRequestMetadata,
)
from guardian.watchdog.review_inputs import (
    GitHubWatchdogReviewInputCaptureService,
)

HEAD_SHA = "a" * 40
BASE_SHA = "b" * 40


def _pull_request(
    *,
    head_sha: str = HEAD_SHA,
    base_sha: str = BASE_SHA,
) -> GitHubPullRequestMetadata:
    return GitHubPullRequestMetadata(
        repository_id="99",
        repository_full_name="octo/example",
        pull_request_number=17,
        title="Review boundary",
        body="A bounded PR body.",
        state="open",
        base_sha=base_sha,
        head_sha=head_sha,
        author_id="7",
        author_login="octocat",
        draft=False,
        head_repository_id="100",
        head_repository_full_name="forker/example",
        head_repository_owner_id="8",
        head_repository_owner_login="forker",
        head_is_fork=True,
    )


def _files(
    *,
    limit_error_code: WatchdogReviewInputCaptureErrorCode | None = None,
) -> GitHubPullRequestFilesResult:
    files = (
        GitHubPullRequestFile(
            filename="src/z.py",
            previous_filename=None,
            status="modified",
            additions=3,
            deletions=1,
            changes=4,
            patch="@@ -1 +1 @@\n-old\n+new\n",
        ),
        GitHubPullRequestFile(
            filename="assets/logo.png",
            previous_filename=None,
            status="added",
            additions=0,
            deletions=0,
            changes=0,
            patch=None,
        ),
    )
    return GitHubPullRequestFilesResult(
        files=files,
        changed_file_count=301 if limit_error_code is not None else len(files),
        patch_bytes=1_000_001 if limit_error_code is not None else len(
            files[0].patch.encode("utf-8")
        ),
        files_without_patch_count=1,
        limit_error_code=limit_error_code,
    )


class FakeGitHubClient:
    """Typed GitHub App boundary fake; no raw response objects enter capture."""

    def __init__(
        self,
        *,
        pull_requests: list[GitHubPullRequestMetadata],
        files: GitHubPullRequestFilesResult,
    ) -> None:
        self.pull_requests = list(pull_requests)
        self.files = files
        self.pull_request_calls = 0
        self.file_calls = 0

    def get_pull_request(
        self,
        repository_full_name: str,
        pull_request_number: int,
    ) -> GitHubPullRequestMetadata:
        assert repository_full_name == "octo/example"
        assert pull_request_number == 17
        self.pull_request_calls += 1
        return self.pull_requests.pop(0)

    def get_pull_request_files(
        self,
        repository_full_name: str,
        pull_request_number: int,
    ) -> GitHubPullRequestFilesResult:
        assert repository_full_name == "octo/example"
        assert pull_request_number == 17
        self.file_calls += 1
        return self.files


class SnapshotHarness:
    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        GitHubWatchdogDeliveryReceipt.__table__.create(engine)
        GitHubWatchdogReviewAttempt.__table__.create(engine)
        GitHubWatchdogReviewInputSnapshot.__table__.create(engine)
        self.Session = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def create_attempt(
        self,
        *,
        review_attempt_id: str = "wra_" + "1" * 32,
        attempt_state: str = WatchdogReviewAttemptState.PREPARED.value,
        policy_resolution_state: str = WatchdogPolicyResolutionState.RESOLVED.value,
    ) -> str:
        now = datetime.now(timezone.utc)
        with self.Session() as session:
            receipt_id = "receipt-" + review_attempt_id[-8:]
            session.add(
                GitHubWatchdogDeliveryReceipt(
                    receipt_id=receipt_id,
                    github_delivery_id="delivery-1",
                    idempotency_key=review_attempt_id[-64:],
                    event_name="pull_request",
                    action="opened",
                    installation_id="42",
                    repository_id="99",
                    repository_full_name="octo/example",
                    trigger_actor_id="7",
                    trigger_actor_login="octocat",
                    pull_request_number=17,
                    head_sha=HEAD_SHA,
                    payload_sha256="d" * 64,
                    first_received_at=now,
                    last_received_at=now,
                    redelivery_count=0,
                )
            )
            session.add(
                GitHubWatchdogReviewAttempt(
                    review_attempt_id=review_attempt_id,
                    trigger_receipt_id=receipt_id,
                    github_delivery_id="delivery-1",
                    installation_id="42",
                    repository_id="99",
                    repository_full_name="octo/example",
                    pull_request_number=17,
                    head_sha=HEAD_SHA,
                    operation=WatchdogOperation.AUTOMATED_REVIEW.value,
                    attempt_number=1,
                    attempt_state=attempt_state,
                    policy_resolution_state=policy_resolution_state,
                    provider_id="local",
                    model_id="review-model",
                    inference_mode=None,
                    model_selection_source="system_default",
                    policy_fingerprint="f" * 64,
                    escalation_mode="disabled",
                    escalation_provider_id=None,
                    escalation_model_id=None,
                    policy_reason_code=None,
                    superseded_by_attempt_id=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()
        return review_attempt_id

    def snapshots(self) -> list[GitHubWatchdogReviewInputSnapshot]:
        with self.Session() as session:
            return list(
                session.scalars(
                    select(GitHubWatchdogReviewInputSnapshot).order_by(
                        GitHubWatchdogReviewInputSnapshot.snapshot_id
                    )
                )
            )


@pytest.fixture()
def harness() -> SnapshotHarness:
    return SnapshotHarness()


def _service(
    harness: SnapshotHarness,
    client: FakeGitHubClient,
) -> GitHubWatchdogReviewInputCaptureService:
    return GitHubWatchdogReviewInputCaptureService(
        session_factory=harness.Session,
        settings=SimpleNamespace(),
        github_client_factory=lambda _settings, _installation_id: client,
    )


def test_capture_persists_a_complete_immutable_digest_snapshot(
    harness: SnapshotHarness,
) -> None:
    attempt_id = harness.create_attempt()
    client = FakeGitHubClient(
        pull_requests=[_pull_request(), _pull_request()],
        files=_files(),
    )
    service = _service(harness, client)

    first = service.capture_review_input(attempt_id)
    second = service.capture_review_input(attempt_id)

    assert first == second
    assert first.capture_state == "captured"
    assert first.block_error_code is None
    assert client.pull_request_calls == 2
    assert client.file_calls == 1
    snapshots = harness.snapshots()
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.review_attempt_id == attempt_id
    assert snapshot.expected_head_sha == snapshot.observed_head_sha == HEAD_SHA
    assert snapshot.base_sha == snapshot.observed_base_sha == BASE_SHA
    assert snapshot.pull_request_body == "A bounded PR body."
    assert snapshot.changed_file_count == 2
    assert snapshot.files_without_patch_count == 1
    assert snapshot.aggregate_additions == 3
    assert snapshot.aggregate_deletions == 1
    assert snapshot.aggregate_changes == 4
    assert snapshot.changed_files_json[0]["filename"] == "assets/logo.png"
    assert snapshot.changed_files_json[1]["patch"] == "@@ -1 +1 @@\n-old\n+new\n"
    assert snapshot.captured_patch_bytes == len("@@ -1 +1 @@\n-old\n+new\n".encode())

    expected_payload = {
        "aggregates": {"additions": 3, "changes": 4, "deletions": 1},
        "changedFiles": snapshot.changed_files_json,
        "filesWithoutPatchCount": 1,
        "pullRequest": {
            "authorId": "7",
            "authorLogin": "octocat",
            "baseSha": BASE_SHA,
            "body": "A bounded PR body.",
            "draft": False,
            "headSha": HEAD_SHA,
            "number": 17,
            "repositoryFullName": "octo/example",
            "repositoryId": "99",
            "title": "Review boundary",
        },
        "snapshotVersion": 1,
    }
    expected_digest = hashlib.sha256(
        json.dumps(
            expected_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    assert snapshot.snapshot_sha256 == expected_digest


def test_live_head_mismatch_blocks_before_changed_file_retrieval(
    harness: SnapshotHarness,
) -> None:
    attempt_id = harness.create_attempt()
    client = FakeGitHubClient(
        pull_requests=[_pull_request(head_sha="c" * 40)],
        files=_files(),
    )

    result = _service(harness, client).capture_review_input(attempt_id)

    assert result.capture_state == "blocked_stale"
    assert result.block_error_code == "live_head_mismatch"
    assert client.pull_request_calls == 1
    assert client.file_calls == 0
    snapshot = harness.snapshots()[0]
    assert snapshot.expected_head_sha == HEAD_SHA
    assert snapshot.observed_head_sha == "c" * 40
    assert snapshot.snapshot_sha256 is None
    assert snapshot.changed_files_json is None


def test_post_read_source_change_discards_changed_file_content(
    harness: SnapshotHarness,
) -> None:
    attempt_id = harness.create_attempt()
    client = FakeGitHubClient(
        pull_requests=[_pull_request(), _pull_request(base_sha="c" * 40)],
        files=_files(),
    )

    result = _service(harness, client).capture_review_input(attempt_id)

    assert result.capture_state == "blocked_stale"
    assert result.block_error_code == "source_changed_during_capture"
    snapshot = harness.snapshots()[0]
    assert snapshot.base_sha == BASE_SHA
    assert snapshot.observed_base_sha == "c" * 40
    assert snapshot.changed_files_json is None
    assert snapshot.snapshot_sha256 is None


def test_limit_exceedance_persists_no_partial_review_input(
    harness: SnapshotHarness,
) -> None:
    attempt_id = harness.create_attempt()
    client = FakeGitHubClient(
        pull_requests=[_pull_request()],
        files=_files(
            limit_error_code=(
                WatchdogReviewInputCaptureErrorCode.CAPTURE_FILE_LIMIT_EXCEEDED
            )
        ),
    )

    result = _service(harness, client).capture_review_input(attempt_id)

    assert result.capture_state == "blocked_limits"
    assert result.block_error_code == "capture_file_limit_exceeded"
    assert client.pull_request_calls == 1
    assert client.file_calls == 1
    snapshot = harness.snapshots()[0]
    assert snapshot.changed_file_count == 301
    assert snapshot.captured_patch_bytes == 1_000_001
    assert snapshot.changed_files_json is None
    assert snapshot.snapshot_sha256 is None


def test_supersession_before_final_persistence_fails_closed(
    harness: SnapshotHarness,
) -> None:
    attempt_id = harness.create_attempt()

    class SupersedingClient(FakeGitHubClient):
        def get_pull_request_files(
            self,
            repository_full_name: str,
            pull_request_number: int,
        ) -> GitHubPullRequestFilesResult:
            result = super().get_pull_request_files(
                repository_full_name,
                pull_request_number,
            )
            with harness.Session() as session:
                attempt = session.get(GitHubWatchdogReviewAttempt, attempt_id)
                assert attempt is not None
                attempt.attempt_state = WatchdogReviewAttemptState.SUPERSEDED.value
                session.commit()
            return result

    client = SupersedingClient(
        pull_requests=[_pull_request(), _pull_request()],
        files=_files(),
    )

    with pytest.raises(WatchdogReviewInputCaptureError) as error:
        _service(harness, client).capture_review_input(attempt_id)

    assert error.value.code is WatchdogReviewInputCaptureErrorCode.ATTEMPT_SUPERSEDED
    assert harness.snapshots() == []


def test_ineligible_attempt_never_calls_github(harness: SnapshotHarness) -> None:
    attempt_id = harness.create_attempt(
        attempt_state=WatchdogReviewAttemptState.BLOCKED_POLICY.value,
        policy_resolution_state=WatchdogPolicyResolutionState.BLOCKED.value,
    )
    client = FakeGitHubClient(pull_requests=[_pull_request()], files=_files())

    with pytest.raises(WatchdogReviewInputCaptureError) as error:
        _service(harness, client).capture_review_input(attempt_id)

    assert error.value.code is WatchdogReviewInputCaptureErrorCode.ATTEMPT_NOT_ELIGIBLE
    assert client.pull_request_calls == 0
    assert client.file_calls == 0


def test_transient_github_failure_is_retryable_and_creates_no_snapshot(
    harness: SnapshotHarness,
) -> None:
    attempt_id = harness.create_attempt()

    class FailingGitHubClient:
        def get_pull_request(
            self,
            repository_full_name: str,
            pull_request_number: int,
        ) -> GitHubPullRequestMetadata:
            raise WatchdogGitHubAppError(
                WatchdogGitHubAppErrorCode.TRANSPORT_FAILURE
            )

    service = GitHubWatchdogReviewInputCaptureService(
        session_factory=harness.Session,
        settings=SimpleNamespace(),
        github_client_factory=lambda _settings, _installation_id: FailingGitHubClient(),
    )

    with pytest.raises(WatchdogReviewInputCaptureError) as error:
        service.capture_review_input(attempt_id)

    assert error.value.code is WatchdogReviewInputCaptureErrorCode.GITHUB_READ_FAILURE
    assert error.value.retryable is True
    assert harness.snapshots() == []
