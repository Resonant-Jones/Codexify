"""Typed models for the provider-free Campaign Engine runtime.

These are runtime-owned envelopes and records, not Campaign Engine schema
entities. The `campaign-engine/v0` schemas remain authoritative for every
entity the runtime writes; the envelopes here carry exactly the statements
the schemas cannot encode (provider/source-mutation counts, commit/merge/
durable-ingestion flags, lineage references, and structured acceptance
criteria), per ADR-066 and the Campaign Engine contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class CampaignClock(Protocol):
    """Deterministic-time seam. Tests inject a fixed clock; production uses UTC."""

    def now(self) -> datetime:
        """Return the current instant, timezone-aware (UTC-normalized by callers)."""
        ...


@dataclass(frozen=True)
class SystemClock:
    """Repository-consistent real clock (UTC, second precision)."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc).replace(microsecond=0)


@dataclass(frozen=True)
class FixedClock:
    """Deterministic clock for tests and reproducibility proofs."""

    instant: datetime

    def now(self) -> datetime:
        return self.instant


def clock_iso(clock: CampaignClock) -> str:
    """Render the clock instant in fixture-consistent RFC 3339 form (UTC, Z suffix)."""
    instant = clock.now()
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.astimezone(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


@dataclass(frozen=True)
class SourceContextRecord:
    """Minimum validated shape of a bounded source-selection lineage fixture.

    The runtime validates only the lineage fields ADR-066 requires. It does not
    implement the DLG resolver and does not validate against the full Agent
    Reading Packet schema. Lineage is evidence; it grants no execution
    permission and is never treated as Guardian authority.
    """

    packet_id: str
    repository_revision: str
    graph_revision: str
    authority_profile: str
    question_or_intent: str
    created_at: str | None = None
    stale_warnings: tuple[Any, ...] = ()
    conflicts: tuple[Any, ...] = ()
    proof_gaps: tuple[Any, ...] = ()
    human_decisions_required: tuple[Any, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)

    def as_artifact(self) -> dict[str, Any]:
        """Normalized record written as the source-context artifact."""
        payload: dict[str, Any] = {
            "schema_version": self.raw.get("schema_version", "1.0.0"),
            "packet_id": self.packet_id,
            "repository_revision": self.repository_revision,
            "graph_revision": self.graph_revision,
            "authority_profile": self.authority_profile,
            "question_or_intent": self.question_or_intent,
        }
        if self.created_at is not None:
            payload["created_at"] = self.created_at
        if self.stale_warnings:
            payload["stale_warnings"] = list(self.stale_warnings)
        if self.conflicts:
            payload["conflicts"] = list(self.conflicts)
        if self.proof_gaps:
            payload["proof_gaps"] = list(self.proof_gaps)
        if self.human_decisions_required:
            payload["human_decisions_required"] = list(self.human_decisions_required)
        return payload


@dataclass(frozen=True)
class AcceptanceCriterionResult:
    """One structured acceptance criterion result recorded in the run envelope."""

    criterion: str
    result: str
    basis: str


PROVIDER_FREE_CLASSIFICATION = "provider_free"
LIVE_EXECUTOR_CLASSIFICATION = "live_executor"
PROVIDER_CALLS_ZERO = 0
PROVIDER_CALLS_LIVE = 1
SOURCE_MUTATIONS_ZERO = 0
DECISION_GATES_OPENED_ZERO = 0
COMMIT_PERFORMED = False
MERGE_PERFORMED = False
DURABLE_INGESTION_PERFORMED = False


@dataclass(frozen=True)
class CampaignRunResult:
    """Structured result envelope required by the Campaign Engine runtime contract."""

    campaign_id: str
    run_id: str
    campaign_state_id: str
    final_campaign_state: str
    task_id: str
    final_task_state: str
    attempt_id: str
    attempt_state: str
    evaluation_id: str
    evaluation_verdict: str
    receipt_id: str
    binding_ids_by_role: dict[str, str]
    output_dir: Path
    classification: str
    provider_calls: int
    source_mutations: int
    decision_gates_opened: int
    commit_performed: bool
    merge_performed: bool
    durable_ingestion_performed: bool
    acceptance_criteria: tuple[AcceptanceCriterionResult, ...]
    hashes: dict[str, str]
    source_context: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "campaign-engine-runtime/v0",
            "classification": self.classification,
            "campaign_id": self.campaign_id,
            "run_id": self.run_id,
            "campaign_state_id": self.campaign_state_id,
            "created_at": self.created_at,
            "final_campaign_state": self.final_campaign_state,
            "task_id": self.task_id,
            "final_task_state": self.final_task_state,
            "attempt_id": self.attempt_id,
            "attempt_state": self.attempt_state,
            "evaluation_id": self.evaluation_id,
            "evaluation_verdict": self.evaluation_verdict,
            "receipt_id": self.receipt_id,
            "binding_ids_by_role": dict(self.binding_ids_by_role),
            "output_dir": str(self.output_dir),
            "provider_calls_performed": self.provider_calls,
            "source_mutations_performed": self.source_mutations,
            "decision_gates_opened": self.decision_gates_opened,
            "commit_performed": self.commit_performed,
            "merge_performed": self.merge_performed,
            "durable_ingestion_performed": self.durable_ingestion_performed,
            "source_context": dict(self.source_context),
            "acceptance_criteria": [
                {
                    "criterion": item.criterion,
                    "result": item.result,
                    "basis": item.basis,
                }
                for item in self.acceptance_criteria
            ],
            "hashes": dict(self.hashes),
        }


@dataclass(frozen=True)
class LiveExecutorPreparation:
    """Immutable preparation record for one live Executor Campaign run.

    Two-phase authority boundary:

    - the preparation is computed entirely by Campaign Engine using the
      locked Executor RoleBinding and the input Campaign document;
    - Guardian authorization is then bound to those immutable values by
      the caller outside the preparation;
    - the execution phase re-derives every material value and fails
      closed on any drift.
    """

    campaign_id: str
    task_id: str
    run_id: str
    attempt_id: str
    evaluation_id: str
    receipt_id: str
    campaign_state_id: str
    created_at: str

    executor_binding_id: str
    executor_binding_revision: int
    expected_provider_id: str
    expected_model_id: str
    adapter_id: str
    configuration_hash: str

    target_path: Path
    target_repository_identity: str
    allowed_file_paths: tuple[str, ...]
    requested_permissions: tuple[str, ...]
    granted_permissions: tuple[str, ...]
    operator_consent_reference: str

    source_context_reference: str
    source_context_hash: str

    prompt: str
    prompt_sha256: str
    expected_output_contract: str

    target_baseline_hash: str
    target_baseline_git_head: str
    target_baseline_file_hashes: tuple[tuple[str, str], ...]
    campaign_input_hash: str

    def as_payload(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "evaluation_id": self.evaluation_id,
            "receipt_id": self.receipt_id,
            "campaign_state_id": self.campaign_state_id,
            "created_at": self.created_at,
            "executor_binding_id": self.executor_binding_id,
            "executor_binding_revision": self.executor_binding_revision,
            "expected_provider_id": self.expected_provider_id,
            "expected_model_id": self.expected_model_id,
            "adapter_id": self.adapter_id,
            "configuration_hash": self.configuration_hash,
            "target_path": str(self.target_path),
            "target_repository_identity": self.target_repository_identity,
            "allowed_file_paths": list(self.allowed_file_paths),
            "requested_permissions": list(self.requested_permissions),
            "granted_permissions": list(self.granted_permissions),
            "operator_consent_reference": self.operator_consent_reference,
            "source_context_reference": self.source_context_reference,
            "source_context_hash": self.source_context_hash,
            "prompt_sha256": self.prompt_sha256,
            "expected_output_contract": self.expected_output_contract,
            "target_baseline_hash": self.target_baseline_hash,
            "target_baseline_git_head": self.target_baseline_git_head,
            "target_baseline_file_hashes": [
                {"path": rel, "sha256": sha256}
                for rel, sha256 in self.target_baseline_file_hashes
            ],
            "campaign_input_hash": self.campaign_input_hash,
        }


@dataclass(frozen=True)
class LiveExecutorRunResult:
    """Structured result envelope for the live Executor Campaign runtime."""

    campaign_id: str
    run_id: str
    attempt_id: str
    attempt_state: str
    evaluation_id: str
    evaluation_verdict: str
    receipt_id: str
    campaign_state_id: str
    binding_ids_by_role: dict[str, str]
    output_dir: Path
    classification: str
    provider_calls: int
    source_mutations: int
    decision_gates_opened: int
    commit_performed: bool
    merge_performed: bool
    durable_ingestion_performed: bool
    acceptance_criteria: tuple[AcceptanceCriterionResult, ...]
    hashes: dict[str, str]
    source_context: dict[str, Any]
    created_at: str
    actual_provider_id: str
    actual_model_id: str
    actual_harness_id: str
    actual_harness_version: str
    identity_verification_result: str
    provider_harness_receipt_reference: str
    pi_receipt_id: str
    pi_harness_result_id: str
    boundary_validation_hash: str
    # Bounded Pi 0.82.1 tool telemetry (evidence only).
    effective_tool_names: tuple[str, ...] | None = None
    write_tool_available: bool | None = None
    tool_execution_start_count: int | None = None
    tool_execution_end_count: int | None = None
    executed_tool_names: tuple[str, ...] | None = None
    assistant_tool_call_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "campaign-engine-runtime/v0",
            "classification": self.classification,
            "campaign_id": self.campaign_id,
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "attempt_state": self.attempt_state,
            "evaluation_id": self.evaluation_id,
            "evaluation_verdict": self.evaluation_verdict,
            "receipt_id": self.receipt_id,
            "campaign_state_id": self.campaign_state_id,
            "binding_ids_by_role": dict(self.binding_ids_by_role),
            "output_dir": str(self.output_dir),
            "provider_calls_performed": self.provider_calls,
            "source_mutations_performed": self.source_mutations,
            "decision_gates_opened": self.decision_gates_opened,
            "commit_performed": self.commit_performed,
            "merge_performed": self.merge_performed,
            "durable_ingestion_performed": self.durable_ingestion_performed,
            "acceptance_criteria": [
                {
                    "criterion": item.criterion,
                    "result": item.result,
                    "basis": item.basis,
                }
                for item in self.acceptance_criteria
            ],
            "hashes": dict(self.hashes),
            "source_context": dict(self.source_context),
            "actual_identity": {
                "provider_id": self.actual_provider_id,
                "model_id": self.actual_model_id,
                "harness_id": self.actual_harness_id,
                "harness_version": self.actual_harness_version,
                "identity_verification_result": self.identity_verification_result,
            },
            "provider_harness_receipt_reference": self.provider_harness_receipt_reference,
            "pi_receipt_id": self.pi_receipt_id,
            "pi_harness_result_id": self.pi_harness_result_id,
            "boundary_validation_hash": self.boundary_validation_hash,
            "created_at": self.created_at,
            # Bounded Pi 0.82.1 tool telemetry (evidence only).
            "tool_telemetry": {
                "effective_tool_names": (
                    list(self.effective_tool_names)
                    if self.effective_tool_names is not None
                    else None
                ),
                "write_tool_available": self.write_tool_available,
                "tool_execution_start_count": self.tool_execution_start_count,
                "tool_execution_end_count": self.tool_execution_end_count,
                "executed_tool_names": (
                    list(self.executed_tool_names)
                    if self.executed_tool_names is not None
                    else None
                ),
                "assistant_tool_call_count": self.assistant_tool_call_count,
            }
            if self.effective_tool_names is not None
            else None,
        }
