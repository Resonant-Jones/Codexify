from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from guardian.agents.events import AgentEventPublisher
from guardian.agents.store import AgentStore
from guardian.workers.agent_worker import (
    AttemptEvaluation,
    process_mutating_step,
)


@dataclass
class _FakeCommitBackend:
    calls: list[tuple[str, bool | None]]

    def commit_mutation(self, *, worktree_path: str, message: str) -> str:
        _ = worktree_path, message
        self.calls.append(("mutation", None))
        return "commit-a-hash"

    def commit_validation_boundary(
        self, *, worktree_path: str, message: str, allow_empty: bool
    ) -> str:
        _ = worktree_path, message
        self.calls.append(("validation", allow_empty))
        return "commit-b-hash"


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "AGENT_MAX_ATTEMPTS": 5,
        "AGENT_MIN_ATTEMPTS_BEFORE_ABORT": 2,
        "AGENT_NO_PROGRESS_WINDOW": 2,
        "AGENT_MAX_SAME_SIGNATURE_REPEATS": 2,
        "AGENT_REGRESSION_LIMIT": 2,
        "AGENT_VALIDATOR_MODEL_ENABLED": False,
        "AGENT_VALIDATION_COMMIT_ALLOW_EMPTY": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _seed_run(telemetry_store: AgentStore) -> str:
    deployment = telemetry_store.create_deployment(
        flow_id="flow-1",
        thread_id=42,
        spec_json={"steps": []},
        spec_hash="spec-hash-1",
    )
    run = telemetry_store.create_run(
        deployment_id=str(deployment["deployment_id"]),
        thread_id=42,
        status="running",
    )
    return str(run["run_id"])


def test_failing_attempts_create_no_commits() -> None:
    telemetry_store = AgentStore()
    event_publisher = AgentEventPublisher()
    run_id = _seed_run(telemetry_store)
    commit_backend = _FakeCommitBackend(calls=[])

    def executor(_attempt_index: int) -> AttemptEvaluation:
        return AttemptEvaluation(
            schema_valid=True,
            tests_passed=False,
            spec_alignment_ok=True,
            fail_count=3,
            fail_signature="sig-fail",
            diff_added=4,
            diff_deleted=1,
            error_category="tests_failed",
        )

    result = process_mutating_step(
        deployment_id="dep-1",
        run_id=run_id,
        step_index=1,
        step_id="step-fail",
        primitive="mutate",
        worktree_path="/tmp/worktree",
        attempt_executor=executor,
        telemetry_store=telemetry_store,
        event_publisher=event_publisher,
        settings=_settings(
            AGENT_MAX_ATTEMPTS=3,
            AGENT_MIN_ATTEMPTS_BEFORE_ABORT=99,
        ),
        commit_backend=commit_backend,
    )

    assert result.status == "failed"
    assert result.commit_a_hash is None
    assert result.commit_b_hash is None
    assert commit_backend.calls == []

    attempts = telemetry_store.list_attempts(run_id=run_id, step_index=1)
    assert len(attempts) == 3
    artifacts = telemetry_store.list_artifacts(run_id=run_id, step_index=1)
    assert artifacts == []


def test_successful_mutating_task_creates_exactly_two_commits_and_persists_hashes() -> (
    None
):
    telemetry_store = AgentStore()
    event_publisher = AgentEventPublisher()
    run_id = _seed_run(telemetry_store)
    commit_backend = _FakeCommitBackend(calls=[])

    def executor(_attempt_index: int) -> AttemptEvaluation:
        return AttemptEvaluation(
            schema_valid=True,
            tests_passed=True,
            spec_alignment_ok=True,
            fail_count=0,
            fail_signature="sig-ok",
            diff_added=2,
            diff_deleted=1,
            error_category="tests_failed",
            diff_risk=0.95,
            model_stability=0.90,
            model_self_confidence=0.66,
        )

    result = process_mutating_step(
        deployment_id="dep-1",
        run_id=run_id,
        step_index=2,
        step_id="step-success",
        primitive="mutate",
        worktree_path="/tmp/worktree",
        attempt_executor=executor,
        telemetry_store=telemetry_store,
        event_publisher=event_publisher,
        settings=_settings(),
        commit_backend=commit_backend,
    )

    assert result.status == "succeeded"
    assert result.commit_a_hash == "commit-a-hash"
    assert result.commit_b_hash == "commit-b-hash"
    assert commit_backend.calls == [
        ("mutation", None),
        ("validation", True),
    ]

    artifacts = telemetry_store.list_artifacts(run_id=run_id, step_index=2)
    by_type = {item["artifact_type"]: item for item in artifacts}
    assert by_type["commit_a_hash"]["content_json"]["hash"] == "commit-a-hash"
    assert by_type["commit_b_hash"]["content_json"]["hash"] == "commit-b-hash"

    confidence_reports = telemetry_store.list_confidence_reports(run_id=run_id)
    scopes = [item["scope"] for item in confidence_reports]
    assert "step" in scopes
    assert "task" in scopes


def test_retry_then_success_still_commits_only_once_per_boundary() -> None:
    telemetry_store = AgentStore()
    event_publisher = AgentEventPublisher()
    run_id = _seed_run(telemetry_store)
    commit_backend = _FakeCommitBackend(calls=[])
    state = {"attempt": 0}

    def executor(attempt_index: int) -> AttemptEvaluation:
        state["attempt"] = attempt_index
        if attempt_index == 1:
            return AttemptEvaluation(
                schema_valid=True,
                tests_passed=False,
                spec_alignment_ok=True,
                fail_count=3,
                fail_signature="sig-fail-1",
                diff_added=6,
                diff_deleted=0,
                error_category="tests_failed",
            )
        return AttemptEvaluation(
            schema_valid=True,
            tests_passed=True,
            spec_alignment_ok=True,
            fail_count=1,
            fail_signature="sig-pass",
            diff_added=1,
            diff_deleted=1,
            error_category="tests_failed",
            diff_risk=0.90,
            model_stability=0.90,
        )

    result = process_mutating_step(
        deployment_id="dep-1",
        run_id=run_id,
        step_index=3,
        step_id="step-retry-success",
        primitive="mutate",
        worktree_path="/tmp/worktree",
        attempt_executor=executor,
        telemetry_store=telemetry_store,
        event_publisher=event_publisher,
        settings=_settings(),
        commit_backend=commit_backend,
    )

    assert result.status == "succeeded"
    assert result.attempts == 2
    assert state["attempt"] == 2
    assert commit_backend.calls == [
        ("mutation", None),
        ("validation", True),
    ]
    attempts = telemetry_store.list_attempts(run_id=run_id, step_index=3)
    assert len(attempts) == 2
