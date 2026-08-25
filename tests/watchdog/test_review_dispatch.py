"""Focused proof for Postgres-first GitHub Watchdog review dispatch."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    GitHubWatchdogDeliveryReceipt,
    GitHubWatchdogReviewAttempt,
    GitHubWatchdogReviewDispatch,
    GitHubWatchdogReviewInputSnapshot,
    GitHubWatchdogReviewResult,
)
from guardian.watchdog.contracts import (
    WatchdogOperation,
    WatchdogPolicyResolutionState,
    WatchdogReviewAttemptState,
    WatchdogReviewInputSnapshotState,
)
from guardian.watchdog.review_dispatch import (
    GitHubWatchdogReviewDispatchService,
    WatchdogReviewDispatchError,
)

HEAD_SHA = "a" * 40
BASE_SHA = "b" * 40


class DispatchHarness:
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
        GitHubWatchdogReviewResult.__table__.create(engine)
        GitHubWatchdogReviewDispatch.__table__.create(engine)
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
        policy_state: str = WatchdogPolicyResolutionState.RESOLVED.value,
        snapshot_state: str = WatchdogReviewInputSnapshotState.CAPTURED.value,
        superseded_by_attempt_id: str | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        with self.Session() as session:
            receipt_id = "receipt-" + review_attempt_id[-8:]
            session.add(
                GitHubWatchdogDeliveryReceipt(
                    receipt_id=receipt_id,
                    github_delivery_id="delivery-" + review_attempt_id[-4:],
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
                    github_delivery_id="delivery-" + review_attempt_id[-4:],
                    installation_id="42",
                    repository_id="99",
                    repository_full_name="octo/example",
                    pull_request_number=17,
                    head_sha=HEAD_SHA,
                    operation=WatchdogOperation.AUTOMATED_REVIEW.value,
                    attempt_number=1,
                    attempt_state=attempt_state,
                    policy_resolution_state=policy_state,
                    provider_id="local",
                    model_id="review-model",
                    inference_mode="think",
                    model_selection_source="system_default",
                    policy_fingerprint="f" * 64,
                    escalation_mode="disabled",
                    escalation_provider_id=None,
                    escalation_model_id=None,
                    policy_reason_code=None,
                    superseded_by_attempt_id=superseded_by_attempt_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                GitHubWatchdogReviewInputSnapshot(
                    snapshot_id="wri_" + review_attempt_id[-32:],
                    review_attempt_id=review_attempt_id,
                    installation_id="42",
                    repository_id="99",
                    repository_full_name="octo/example",
                    pull_request_number=17,
                    capture_state=snapshot_state,
                    expected_head_sha=HEAD_SHA,
                    observed_head_sha=HEAD_SHA,
                    base_sha=BASE_SHA,
                    observed_base_sha=BASE_SHA,
                    pull_request_title="Untrusted title",
                    pull_request_body="Untrusted body",
                    author_id="7",
                    author_login="octocat",
                    draft=False,
                    changed_file_count=1,
                    files_without_patch_count=0,
                    aggregate_additions=2,
                    aggregate_deletions=1,
                    aggregate_changes=3,
                    changed_files_json=[{"filename": "src/app.py", "patch": "+x"}],
                    captured_patch_bytes=2,
                    snapshot_sha256=("e" * 64 if snapshot_state == "captured" else None),
                    block_error_code=(
                        None if snapshot_state == "captured" else "capture_file_limit_exceeded"
                    ),
                    captured_at=now,
                )
            )
            session.commit()
        return review_attempt_id

    def dispatch(self, review_attempt_id: str) -> GitHubWatchdogReviewDispatch | None:
        with self.Session() as session:
            return session.scalar(
                select(GitHubWatchdogReviewDispatch).where(
                    GitHubWatchdogReviewDispatch.review_attempt_id == review_attempt_id
                )
            )

    def attempt(self, review_attempt_id: str) -> GitHubWatchdogReviewAttempt:
        with self.Session() as session:
            attempt = session.get(GitHubWatchdogReviewAttempt, review_attempt_id)
            assert attempt is not None
            return attempt

    def add_result(self, review_attempt_id: str) -> None:
        now = datetime.now(timezone.utc)
        with self.Session() as session:
            session.add(
                GitHubWatchdogReviewResult(
                    result_id="wrr_" + review_attempt_id[-32:],
                    review_attempt_id=review_attempt_id,
                    review_input_snapshot_id="wri_" + review_attempt_id[-32:],
                    snapshot_sha256="e" * 64,
                    result_state="completed",
                    schema_version="github-watchdog-review-result-v1",
                    prompt_version="github-watchdog-review-v1",
                    prompt_sha256="p" * 64,
                    invoked_provider_id="local",
                    invoked_model_id="review-model",
                    inference_mode="think",
                    requested_max_output_tokens=4096,
                    raw_output_text=None,
                    raw_output_sha256=None,
                    raw_output_bytes=None,
                    structured_review_json={"assessment": "no_findings"},
                    provider_input_tokens=None,
                    provider_output_tokens=None,
                    provider_total_tokens=None,
                    provider_request_id=None,
                    terminal_error_code=None,
                    started_at=now,
                    completed_at=now,
                )
            )
            session.commit()


@pytest.fixture()
def harness() -> DispatchHarness:
    return DispatchHarness()


def test_dispatch_commits_intent_before_minimal_redis_enqueue(
    harness: DispatchHarness,
) -> None:
    attempt_id = harness.create_attempt()
    seen: list[dict[str, str]] = []

    def enqueue(**payload: str) -> None:
        durable = harness.dispatch(attempt_id)
        assert durable is not None
        assert durable.dispatch_state == "pending_enqueue"
        assert durable.enqueue_count == 0
        seen.append(payload)

    result = GitHubWatchdogReviewDispatchService(
        session_factory=harness.Session,
        enqueue_fn=enqueue,
    ).dispatch_review_attempt(attempt_id)

    assert result.dispatch_state == "queued"
    assert result.enqueue_count == 1
    assert seen == [
        {
            "task_id": result.queue_task_id,
            "dispatch_id": result.dispatch_id,
            "review_attempt_id": attempt_id,
            "created_at": seen[0]["created_at"],
        }
    ]
    assert len(seen[0]) == 4
    assert "patch" not in seen[0]
    assert "provider_id" not in seen[0]
    assert harness.attempt(attempt_id).attempt_state == "prepared"


def test_enqueue_failure_is_durable_and_never_executes_a_model(
    harness: DispatchHarness,
) -> None:
    attempt_id = harness.create_attempt()
    calls = 0

    def enqueue(**_payload: str) -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("redis unavailable")

    result = GitHubWatchdogReviewDispatchService(
        session_factory=harness.Session,
        enqueue_fn=enqueue,
    ).dispatch_review_attempt(attempt_id)

    assert calls == 1
    assert result.dispatch_state == "enqueue_failed"
    assert result.enqueue_count == 1
    assert result.terminal_error_code == "queue_enqueue_failed"
    assert harness.attempt(attempt_id).attempt_state == "prepared"


def test_repeated_normal_dispatch_is_one_row_and_one_enqueue(
    harness: DispatchHarness,
) -> None:
    attempt_id = harness.create_attempt()
    queued: list[dict[str, str]] = []
    service = GitHubWatchdogReviewDispatchService(
        session_factory=harness.Session,
        enqueue_fn=lambda **payload: queued.append(payload),
    )

    first = service.dispatch_review_attempt(attempt_id)
    second = service.dispatch_review_attempt(attempt_id)

    assert first == second
    assert len(queued) == 1
    assert harness.dispatch(attempt_id).dispatch_id == first.dispatch_id  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("attempt_state", "policy_state", "snapshot_state", "superseded_by", "code"),
    [
        ("blocked_policy", "blocked", "captured", None, "attempt_not_eligible"),
        ("prepared", "resolved", "blocked_stale", None, "snapshot_not_captured"),
        ("superseded", "resolved", "captured", "wra_replacement", "attempt_superseded"),
    ],
)
def test_ineligible_attempts_do_not_create_dispatch_or_enqueue(
    harness: DispatchHarness,
    attempt_state: str,
    policy_state: str,
    snapshot_state: str,
    superseded_by: str | None,
    code: str,
) -> None:
    attempt_id = harness.create_attempt(
        attempt_state=attempt_state,
        policy_state=policy_state,
        snapshot_state=snapshot_state,
        superseded_by_attempt_id=superseded_by,
    )
    queued: list[dict[str, str]] = []
    service = GitHubWatchdogReviewDispatchService(
        session_factory=harness.Session,
        enqueue_fn=lambda **payload: queued.append(payload),
    )

    with pytest.raises(WatchdogReviewDispatchError) as exc:
        service.dispatch_review_attempt(attempt_id)

    assert exc.value.code.value == code
    assert harness.dispatch(attempt_id) is None
    assert queued == []


def test_existing_result_cannot_be_dispatched(
    harness: DispatchHarness,
) -> None:
    attempt_id = harness.create_attempt()
    harness.add_result(attempt_id)

    with pytest.raises(WatchdogReviewDispatchError) as exc:
        GitHubWatchdogReviewDispatchService(
            session_factory=harness.Session,
            enqueue_fn=lambda **_payload: None,
        ).dispatch_review_attempt(attempt_id)

    assert exc.value.code.value == "review_result_exists"
    assert harness.dispatch(attempt_id) is None
