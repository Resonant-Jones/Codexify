"""Focused proof for the dedicated GitHub Watchdog review worker."""

from __future__ import annotations

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
    GitHubWatchdogReviewDispatch,
    GitHubWatchdogReviewInputSnapshot,
    GitHubWatchdogReviewResult,
)
from guardian.tasks.types import GITHUB_WATCHDOG_REVIEW_TASK_TYPE
from guardian.watchdog.contracts import (
    WATCHDOG_REVIEW_RESULT_SCHEMA_VERSION,
    WatchdogOperation,
    WatchdogPolicyResolutionState,
    WatchdogReviewAttemptState,
    WatchdogReviewExecutionErrorCode,
)
from guardian.watchdog.review_dispatch import GitHubWatchdogReviewDispatchService
from guardian.watchdog.review_execution import (
    GitHubWatchdogReviewExecutionService,
    WatchdogReviewExecutionError,
)
from guardian.workers.watchdog_review_worker import GitHubWatchdogReviewWorker

HEAD_SHA = "a" * 40
BASE_SHA = "b" * 40


class ModelResponse(str):
    def __new__(cls, content: str):
        value = super().__new__(cls, content)
        value.raw_payload = {"id": "provider-request-1"}
        return value


class WorkerHarness:
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
        review_attempt_id: str = "wra_" + "2" * 32,
        provider_id: str = "local",
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
                    attempt_state=WatchdogReviewAttemptState.PREPARED.value,
                    policy_resolution_state=WatchdogPolicyResolutionState.RESOLVED.value,
                    provider_id=provider_id,
                    model_id="review-model",
                    inference_mode="think",
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
            session.add(
                GitHubWatchdogReviewInputSnapshot(
                    snapshot_id="wri_" + review_attempt_id[-32:],
                    review_attempt_id=review_attempt_id,
                    installation_id="42",
                    repository_id="99",
                    repository_full_name="octo/example",
                    pull_request_number=17,
                    capture_state="captured",
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
                    changed_files_json=[
                        {
                            "filename": "src/app.py",
                            "previousFilename": None,
                            "status": "modified",
                            "additions": 2,
                            "deletions": 1,
                            "changes": 3,
                            "patch": "+x",
                        }
                    ],
                    captured_patch_bytes=2,
                    snapshot_sha256="e" * 64,
                    block_error_code=None,
                    captured_at=now,
                )
            )
            session.commit()
        return review_attempt_id

    def enqueue(self, review_attempt_id: str) -> dict[str, str]:
        sent: list[dict[str, str]] = []
        result = GitHubWatchdogReviewDispatchService(
            session_factory=self.Session,
            enqueue_fn=lambda **payload: sent.append(payload),
        ).dispatch_review_attempt(review_attempt_id)
        assert result.dispatch_state == "queued"
        return {
            "task_id": result.queue_task_id,
            "type": GITHUB_WATCHDOG_REVIEW_TASK_TYPE,
            "dispatch_id": result.dispatch_id,
            "review_attempt_id": review_attempt_id,
            "created_at": sent[0]["created_at"],
        }

    def dispatch(self, review_attempt_id: str) -> GitHubWatchdogReviewDispatch:
        with self.Session() as session:
            row = session.scalar(
                select(GitHubWatchdogReviewDispatch).where(
                    GitHubWatchdogReviewDispatch.review_attempt_id == review_attempt_id
                )
            )
            assert row is not None
            return row

    def result(self, review_attempt_id: str) -> GitHubWatchdogReviewResult | None:
        with self.Session() as session:
            return session.scalar(
                select(GitHubWatchdogReviewResult).where(
                    GitHubWatchdogReviewResult.review_attempt_id == review_attempt_id
                )
            )

    def supersede(self, review_attempt_id: str) -> None:
        with self.Session() as session:
            attempt = session.get(GitHubWatchdogReviewAttempt, review_attempt_id)
            assert attempt is not None
            attempt.attempt_state = "superseded"
            attempt.superseded_by_attempt_id = "wra_replacement"
            session.commit()

    def add_running_result(self, review_attempt_id: str) -> str:
        now = datetime.now(timezone.utc)
        result_id = "wrr_" + review_attempt_id[-32:]
        with self.Session() as session:
            attempt = session.get(GitHubWatchdogReviewAttempt, review_attempt_id)
            assert attempt is not None
            attempt.attempt_state = "running"
            session.add(
                GitHubWatchdogReviewResult(
                    result_id=result_id,
                    review_attempt_id=review_attempt_id,
                    review_input_snapshot_id="wri_" + review_attempt_id[-32:],
                    snapshot_sha256="e" * 64,
                    result_state="running",
                    schema_version=WATCHDOG_REVIEW_RESULT_SCHEMA_VERSION,
                    prompt_version="github-watchdog-review-v1",
                    prompt_sha256="p" * 64,
                    invoked_provider_id="local",
                    invoked_model_id="review-model",
                    inference_mode="think",
                    requested_max_output_tokens=4096,
                    raw_output_text=None,
                    raw_output_sha256=None,
                    raw_output_bytes=None,
                    structured_review_json=None,
                    provider_input_tokens=None,
                    provider_output_tokens=None,
                    provider_total_tokens=None,
                    provider_request_id=None,
                    terminal_error_code=None,
                    started_at=now,
                    completed_at=None,
                )
            )
            session.commit()
        return result_id


@pytest.fixture()
def harness() -> WorkerHarness:
    return WorkerHarness()


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _valid_review() -> str:
    return json.dumps(
        {
            "schemaVersion": WATCHDOG_REVIEW_RESULT_SCHEMA_VERSION,
            "assessment": "no_findings",
            "summary": "No actionable defects.",
            "findings": [],
        }
    )


def _worker(
    harness: WorkerHarness,
    model_invoker,
    *,
    settings: SimpleNamespace | None = None,
    dequeue_fn=None,
) -> GitHubWatchdogReviewWorker:
    return GitHubWatchdogReviewWorker(
        session_factory=harness.Session,
        execution_service=GitHubWatchdogReviewExecutionService(
            session_factory=harness.Session,
            settings=settings or _settings(),
            model_invoker=model_invoker,
        ),
        dequeue_fn=dequeue_fn,
        worker_id="watchdog-review:test:1",
    )


def test_worker_maps_completed_result_and_duplicate_delivery_invokes_once(
    harness: WorkerHarness,
) -> None:
    attempt_id = harness.create_attempt()
    envelope = harness.enqueue(attempt_id)
    calls = 0

    def invoke(_messages, **_kwargs):
        nonlocal calls
        calls += 1
        return ModelResponse(_valid_review())

    payloads = [envelope, envelope]
    worker = _worker(
        harness,
        invoke,
        dequeue_fn=lambda **_kwargs: payloads.pop(0) if payloads else None,
    )
    worker.process_once()
    worker.process_once()

    dispatch = harness.dispatch(attempt_id)
    result = harness.result(attempt_id)
    assert calls == 1
    assert dispatch.dispatch_state == "completed"
    assert dispatch.worker_id == "watchdog-review:test:1"
    assert dispatch.review_result_id == result.result_id  # type: ignore[union-attr]


def test_malformed_or_identity_mismatched_envelope_spends_zero_model_calls(
    harness: WorkerHarness,
) -> None:
    attempt_id = harness.create_attempt()
    envelope = harness.enqueue(attempt_id)
    calls = 0

    def invoke(_messages, **_kwargs):
        nonlocal calls
        calls += 1
        return ModelResponse(_valid_review())

    worker = _worker(harness, invoke)
    worker.process_envelope({"type": GITHUB_WATCHDOG_REVIEW_TASK_TYPE})
    forged = dict(envelope)
    forged["review_attempt_id"] = "wra_forged"
    worker.process_envelope(forged)

    assert calls == 0
    assert harness.dispatch(attempt_id).dispatch_state == "queued"


def test_superseded_before_worker_discards_without_a_model_call(
    harness: WorkerHarness,
) -> None:
    attempt_id = harness.create_attempt()
    envelope = harness.enqueue(attempt_id)
    harness.supersede(attempt_id)
    calls = 0

    def invoke(_messages, **_kwargs):
        nonlocal calls
        calls += 1
        return ModelResponse(_valid_review())

    _worker(harness, invoke).process_envelope(envelope)

    dispatch = harness.dispatch(attempt_id)
    assert calls == 0
    assert dispatch.dispatch_state == "discarded_superseded"


def test_worker_maps_runtime_block_provider_failure_and_invalid_output(
    harness: WorkerHarness,
) -> None:
    blocked_id = harness.create_attempt(review_attempt_id="wra_" + "3" * 32, provider_id="openai")
    blocked_envelope = harness.enqueue(blocked_id)
    calls = 0

    def never_invoke(_messages, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("runtime policy block must not invoke a model")

    _worker(harness, never_invoke).process_envelope(blocked_envelope)
    assert calls == 0
    assert harness.dispatch(blocked_id).dispatch_state == "blocked"

    failed_id = harness.create_attempt(review_attempt_id="wra_" + "4" * 32)
    failed_envelope = harness.enqueue(failed_id)
    _worker(harness, lambda _messages, **_kwargs: (_ for _ in ()).throw(RuntimeError())).process_envelope(failed_envelope)
    assert harness.dispatch(failed_id).dispatch_state == "failed"

    invalid_id = harness.create_attempt(review_attempt_id="wra_" + "5" * 32)
    invalid_envelope = harness.enqueue(invalid_id)
    _worker(harness, lambda _messages, **_kwargs: ModelResponse("not json")).process_envelope(invalid_envelope)
    assert harness.dispatch(invalid_id).dispatch_state == "failed"


def test_superseded_during_execution_maps_discarded_result(
    harness: WorkerHarness,
) -> None:
    attempt_id = harness.create_attempt()
    envelope = harness.enqueue(attempt_id)

    def invoke(_messages, **_kwargs):
        harness.supersede(attempt_id)
        return ModelResponse(_valid_review())

    _worker(harness, invoke).process_envelope(envelope)

    assert harness.dispatch(attempt_id).dispatch_state == "discarded_superseded"
    assert harness.result(attempt_id).result_state == "discarded_superseded"  # type: ignore[union-attr]


def test_existing_running_result_remains_nonterminal_without_another_model_call(
    harness: WorkerHarness,
) -> None:
    attempt_id = harness.create_attempt()
    envelope = harness.enqueue(attempt_id)
    result_id = harness.add_running_result(attempt_id)

    def never_invoke(_messages, **_kwargs):
        raise AssertionError("existing running result must not execute again")

    _worker(harness, never_invoke).process_envelope(envelope)

    dispatch = harness.dispatch(attempt_id)
    assert dispatch.dispatch_state == "running"
    assert dispatch.review_result_id == result_id


def test_supersession_between_worker_claim_and_executor_is_discarded(
    harness: WorkerHarness,
) -> None:
    attempt_id = harness.create_attempt()
    envelope = harness.enqueue(attempt_id)

    class SupersedingExecutor:
        def execute_review_attempt(self, _review_attempt_id: str):
            harness.supersede(attempt_id)
            raise WatchdogReviewExecutionError(
                WatchdogReviewExecutionErrorCode.ATTEMPT_SUPERSEDED
            )

    worker = GitHubWatchdogReviewWorker(
        session_factory=harness.Session,
        execution_service=SupersedingExecutor(),  # type: ignore[arg-type]
        worker_id="watchdog-review:test:1",
    )
    worker.process_envelope(envelope)

    assert harness.dispatch(attempt_id).dispatch_state == "discarded_superseded"


def test_worker_interruption_leaves_durable_running_dispatch(
    harness: WorkerHarness,
) -> None:
    attempt_id = harness.create_attempt()
    envelope = harness.enqueue(attempt_id)

    class ExplodingExecutor:
        def execute_review_attempt(self, _review_attempt_id: str):
            raise RuntimeError("simulated process interruption")

    worker = GitHubWatchdogReviewWorker(
        session_factory=harness.Session,
        execution_service=ExplodingExecutor(),  # type: ignore[arg-type]
        worker_id="watchdog-review:test:1",
    )
    worker.process_envelope(envelope)

    dispatch = harness.dispatch(attempt_id)
    assert dispatch.dispatch_state == "running"
    assert dispatch.completed_at is None
