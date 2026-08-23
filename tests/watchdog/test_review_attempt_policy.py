"""Focused policy and persistence proof for Watchdog review preparation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db.models import (
    GitHubWatchdogDeliveryReceipt,
    GitHubWatchdogReviewAttempt,
)
from guardian.watchdog.contracts import NormalizedGitHubDelivery
from guardian.watchdog.policy import resolve_automated_review_policy
from guardian.watchdog.review_attempts import GitHubWatchdogReviewAttemptPreparer
from guardian.watchdog.store import GitHubWatchdogDeliveryReceiptStore


class AttemptHarness:
    """A shared durable receipt/attempt store with pure operator settings."""

    def __init__(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        GitHubWatchdogDeliveryReceipt.__table__.create(engine)
        GitHubWatchdogReviewAttempt.__table__.create(engine)
        self.Session = sessionmaker(
            bind=engine, autoflush=False, autocommit=False, future=True
        )
        self.receipts = GitHubWatchdogDeliveryReceiptStore(session_factory=self.Session)
        self.preparer = GitHubWatchdogReviewAttemptPreparer(
            session_factory=self.Session
        )

    def persist_receipt(
        self,
        *,
        delivery_id: str,
        action: str = "opened",
        head_sha: str | None = "a" * 40,
    ) -> str:
        result = self.receipts.persist(
            NormalizedGitHubDelivery(
                github_delivery_id=delivery_id,
                idempotency_key=f"key-{delivery_id}",
                event_name="pull_request",
                action=action,
                installation_id="42",
                repository_id="99",
                repository_full_name="octo/example",
                trigger_actor_id="7",
                trigger_actor_login="octocat",
                pull_request_number=12,
                head_sha=head_sha,
                payload_sha256=f"{delivery_id:0<64}"[:64],
            )
        )
        return result.receipt_id

    def attempts(self) -> list[GitHubWatchdogReviewAttempt]:
        with self.Session() as session:
            return list(
                session.scalars(
                    select(GitHubWatchdogReviewAttempt).order_by(
                        GitHubWatchdogReviewAttempt.created_at,
                        GitHubWatchdogReviewAttempt.review_attempt_id,
                    )
                )
            )


@pytest.fixture()
def harness() -> AttemptHarness:
    return AttemptHarness()


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER": "local",
        "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL": "local-review-model",
        "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_INFERENCE_MODE": "think",
        "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODE": "disabled",
        "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_PROVIDER": None,
        "CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODEL": None,
        "CODEXIFY_LOCAL_ONLY_MODE": True,
        "ALLOW_CLOUD_PROVIDERS": False,
        "CODEXIFY_EGRESS_ALLOWLIST": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_configured_local_policy_resolves_without_external_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from guardian.watchdog import policy

    calls: list[str] = []
    monkeypatch.setattr(
        policy,
        "assert_egress_allowed",
        lambda provider_id, *, settings: calls.append(provider_id),
    )

    snapshot = resolve_automated_review_policy(_settings())

    assert snapshot.policy_resolution_state == "resolved"
    assert snapshot.policy_reason_code is None
    assert snapshot.provider_id == "local"
    assert snapshot.model_id == "local-review-model"
    assert snapshot.inference_mode == "think"
    assert snapshot.model_selection_source == "system_default"
    assert snapshot.escalation_mode == "disabled"
    assert len(snapshot.policy_fingerprint) == 64
    assert calls == []


@pytest.mark.parametrize(
    ("settings", "expected_reason"),
    [
        (
            _settings(CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER=None),
            "configuration_missing",
        ),
        (
            _settings(CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL=None),
            "model_missing",
        ),
        (
            _settings(CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER="unknown"),
            "provider_unknown",
        ),
        (
            _settings(CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER="anthropic"),
            "provider_governance_disabled",
        ),
        (
            _settings(CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER="openai"),
            "local_only_mode_forbids_cloud",
        ),
        (
            _settings(
                CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER="openai",
                CODEXIFY_LOCAL_ONLY_MODE=False,
                ALLOW_CLOUD_PROVIDERS=False,
            ),
            "cloud_providers_disabled",
        ),
        (
            _settings(
                CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_PROVIDER="openai",
                CODEXIFY_LOCAL_ONLY_MODE=False,
                ALLOW_CLOUD_PROVIDERS=True,
            ),
            "egress_policy_forbids_provider",
        ),
    ],
)
def test_policy_blocks_are_bounded_and_fail_closed(
    settings: SimpleNamespace,
    expected_reason: str,
) -> None:
    snapshot = resolve_automated_review_policy(settings)

    assert snapshot.policy_resolution_state == "blocked"
    assert snapshot.policy_reason_code == expected_reason


def test_explicit_only_escalation_is_inert_snapshot_data() -> None:
    snapshot = resolve_automated_review_policy(
        _settings(
            CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODE="explicit_only",
            CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_PROVIDER="openai",
            CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_ESCALATION_MODEL="premium-model",
        )
    )

    assert snapshot.policy_resolution_state == "resolved"
    assert snapshot.escalation_mode == "explicit_only"
    assert snapshot.escalation_provider_id == "openai"
    assert snapshot.escalation_model_id == "premium-model"


def test_review_attempt_preparation_persists_immutable_snapshot(
    harness: AttemptHarness,
) -> None:
    receipt_id = harness.persist_receipt(delivery_id="delivery-opened")
    settings = _settings()

    result = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=receipt_id,
        settings=settings,
    )
    settings.CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL = "changed-model"

    assert result.attempt_state == "prepared"
    assert result.policy_resolution_state == "resolved"
    attempts = harness.attempts()
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.review_attempt_id == result.review_attempt_id
    assert attempt.trigger_receipt_id == receipt_id
    assert attempt.github_delivery_id == "delivery-opened"
    assert attempt.operation == "automated_review"
    assert attempt.attempt_number == 1
    assert attempt.head_sha == "a" * 40
    assert attempt.provider_id == "local"
    assert attempt.model_id == "local-review-model"
    assert attempt.inference_mode == "think"
    assert attempt.model_selection_source == "system_default"
    assert attempt.policy_reason_code is None
    assert attempt.escalation_mode == "disabled"


def test_same_receipt_reuses_its_durable_review_attempt(
    harness: AttemptHarness,
) -> None:
    receipt_id = harness.persist_receipt(delivery_id="delivery-redelivery")

    first = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=receipt_id,
        settings=_settings(),
    )
    second = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=receipt_id,
        settings=_settings(
            CODEXIFY_GITHUB_WATCHDOG_AUTOMATED_REVIEW_MODEL="other-model"
        ),
    )

    assert second.review_attempt_id == first.review_attempt_id
    assert len(harness.attempts()) == 1


def test_missing_head_sha_creates_durable_blocked_attempt(
    harness: AttemptHarness,
) -> None:
    receipt_id = harness.persist_receipt(delivery_id="delivery-no-head", head_sha=None)

    result = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=receipt_id,
        settings=_settings(),
    )

    assert result.attempt_state == "blocked_policy"
    attempt = harness.attempts()[0]
    assert attempt.policy_resolution_state == "blocked"
    assert attempt.policy_reason_code == "head_sha_missing"
    assert attempt.head_sha is None


def test_new_synchronize_head_supersedes_older_prepared_attempt(
    harness: AttemptHarness,
) -> None:
    opened_receipt = harness.persist_receipt(delivery_id="delivery-opened")
    first = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=opened_receipt,
        settings=_settings(),
    )
    sync_receipt = harness.persist_receipt(
        delivery_id="delivery-sync",
        action="synchronize",
        head_sha="b" * 40,
    )
    second = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=sync_receipt,
        settings=_settings(),
    )

    assert second.attempt_state == "prepared"
    attempts = harness.attempts()
    assert len(attempts) == 2
    old_attempt = next(
        item for item in attempts if item.review_attempt_id == first.review_attempt_id
    )
    new_attempt = next(
        item for item in attempts if item.review_attempt_id == second.review_attempt_id
    )
    assert old_attempt.attempt_state == "superseded"
    assert old_attempt.superseded_by_attempt_id == new_attempt.review_attempt_id
    assert new_attempt.head_sha == "b" * 40


def test_same_head_distinct_delivery_creates_a_distinct_attempt(
    harness: AttemptHarness,
) -> None:
    opened_receipt = harness.persist_receipt(delivery_id="delivery-opened")
    reopened_receipt = harness.persist_receipt(
        delivery_id="delivery-reopened", action="reopened"
    )

    first = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=opened_receipt,
        settings=_settings(),
    )
    second = harness.preparer.prepare_from_receipt(
        trigger_receipt_id=reopened_receipt,
        settings=_settings(),
    )

    assert first.review_attempt_id != second.review_attempt_id
    assert [attempt.attempt_state for attempt in harness.attempts()] == [
        "prepared",
        "prepared",
    ]
