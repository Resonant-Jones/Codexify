"""Pure Execution Ledger gate-artifact contracts.

These contracts model typed gate artifacts and acceptance criteria for
Execution Ledger planning and proof review. They are intentionally pure and
side-effect-free in this task: no persistence, route wiring, worker wiring,
or runtime behavior changes are performed here.

Contract interpretation guards:
- intent/scope or plan approval does not imply execution started
- completion/proof approval must rely on durable attempt evidence rather than
  task-event visibility alone
"""

from __future__ import annotations

from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardian.agents.execution_ledger_tokens import (
    ACCEPTANCE_CRITERION_RESULT_BLOCKED,
    ACCEPTANCE_CRITERION_RESULT_FAILED,
    ACCEPTANCE_CRITERION_RESULT_PASSED,
    is_valid_acceptance_criterion_result,
    is_valid_acceptance_validation_mode,
    is_valid_gate_decision,
    is_valid_proof_decision,
)


def _clean_required_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("value must be a non-empty string")
    return text


def _clean_optional_text(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _clean_text_list(values: Sequence[object] | None) -> list[str]:
    if not values:
        return []
    return [text for text in (str(item).strip() for item in values) if text]


class AcceptanceCriterionContract(BaseModel):
    """Structured acceptance criterion proof contract for one requirement."""

    criterion_id: str = Field(min_length=1)
    requirement: str = Field(min_length=1)
    validation_mode: str = Field(min_length=1)
    expected_evidence: str | None = None
    observed_evidence: str | None = None
    result: str = Field(min_length=1)
    linked_attempt_id: str | None = None
    linked_run_id: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("criterion_id", "requirement", mode="before")
    @classmethod
    def _validate_required_text(cls, value: object) -> str:
        return _clean_required_text(value)

    @field_validator(
        "expected_evidence",
        "observed_evidence",
        "linked_attempt_id",
        "linked_run_id",
        mode="before",
    )
    @classmethod
    def _validate_optional_text(cls, value: object | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("validation_mode", mode="before")
    @classmethod
    def _validate_validation_mode(cls, value: object) -> str:
        normalized = _clean_required_text(value)
        if not is_valid_acceptance_validation_mode(normalized):
            raise ValueError(
                f"validation_mode must be a valid acceptance validation mode: {normalized}"
            )
        return normalized

    @field_validator("result", mode="before")
    @classmethod
    def _validate_result(cls, value: object) -> str:
        normalized = _clean_required_text(value)
        if not is_valid_acceptance_criterion_result(normalized):
            raise ValueError(
                f"result must be a valid acceptance criterion result: {normalized}"
            )
        return normalized


class IntentScopeGateArtifact(BaseModel):
    """Intent/scope gate artifact.

    Approval of this artifact means the work is bounded enough to plan. It does
    not imply execution has started.
    """

    work_order_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    source_thread_id: str | None = None
    source_message_id: str | None = None
    title: str = Field(min_length=1)
    intent_summary: str = Field(min_length=1)
    scope_statement: str = Field(min_length=1)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    affected_files_or_domains: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterionContract] = Field(
        default_factory=list
    )
    reviewer: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    decision_rationale: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "work_order_id",
        "campaign_id",
        "title",
        "intent_summary",
        "scope_statement",
        "reviewer",
        "decision",
        "decision_rationale",
        "timestamp",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object) -> str:
        return _clean_required_text(value)

    @field_validator("source_thread_id", "source_message_id", mode="before")
    @classmethod
    def _validate_optional_text(cls, value: object | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator(
        "in_scope",
        "out_of_scope",
        "affected_files_or_domains",
        mode="before",
    )
    @classmethod
    def _validate_text_lists(cls, values: Sequence[object] | None) -> list[str]:
        return _clean_text_list(values)

    @field_validator("decision")
    @classmethod
    def _validate_decision(cls, value: str) -> str:
        if not is_valid_gate_decision(value):
            raise ValueError(
                f"decision must be a valid gate decision token: {value}"
            )
        return value


class ImplementationPlanGateArtifact(BaseModel):
    """Implementation-plan gate artifact.

    Approval means execution may be attempted within approved boundaries; it
    does not imply validation passed or completion is proven.
    """

    work_order_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    linked_intent_scope_artifact_id: str = Field(min_length=1)
    expected_files_to_read: list[str] = Field(default_factory=list)
    expected_files_to_modify: list[str] = Field(default_factory=list)
    validation_commands: list[str] = Field(default_factory=list)
    rollback_plan: str = Field(min_length=1)
    risk_notes: str | None = None
    dependency_notes: str | None = None
    reviewer: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    decision_rationale: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "work_order_id",
        "plan_id",
        "linked_intent_scope_artifact_id",
        "rollback_plan",
        "reviewer",
        "decision",
        "decision_rationale",
        "timestamp",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object) -> str:
        return _clean_required_text(value)

    @field_validator(
        "risk_notes",
        "dependency_notes",
        mode="before",
    )
    @classmethod
    def _validate_optional_text(cls, value: object | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator(
        "expected_files_to_read",
        "expected_files_to_modify",
        "validation_commands",
        mode="before",
    )
    @classmethod
    def _validate_text_lists(cls, values: Sequence[object] | None) -> list[str]:
        return _clean_text_list(values)

    @field_validator("decision")
    @classmethod
    def _validate_decision(cls, value: str) -> str:
        if not is_valid_gate_decision(value):
            raise ValueError(
                f"decision must be a valid gate decision token: {value}"
            )
        return value


class CompletionProofGateArtifact(BaseModel):
    """Completion/proof gate artifact.

    Proof approval is a durable-evidence decision. Task-event visibility alone
    is not sufficient proof.
    """

    work_order_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    guardian_run_id: str | None = None
    command_run_id: str | None = None
    completion_receipt_ref: str | None = None
    validation_commands_run: list[str] = Field(default_factory=list)
    validation_result: str = Field(min_length=1)
    changed_files_summary: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterionContract] = Field(
        default_factory=list
    )
    delivery_status: str | None = None
    follow_up_work_order_ids: list[str] = Field(default_factory=list)
    reviewer: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    decision_rationale: str = Field(min_length=1)
    timestamp: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "work_order_id",
        "attempt_id",
        "reviewer",
        "decision",
        "decision_rationale",
        "timestamp",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object) -> str:
        return _clean_required_text(value)

    @field_validator(
        "guardian_run_id",
        "command_run_id",
        "completion_receipt_ref",
        "delivery_status",
        mode="before",
    )
    @classmethod
    def _validate_optional_text(cls, value: object | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator(
        "validation_commands_run",
        "changed_files_summary",
        "follow_up_work_order_ids",
        mode="before",
    )
    @classmethod
    def _validate_text_lists(cls, values: Sequence[object] | None) -> list[str]:
        return _clean_text_list(values)

    @field_validator("decision")
    @classmethod
    def _validate_decision(cls, value: str) -> str:
        if not is_valid_proof_decision(value):
            raise ValueError(
                f"decision must be a valid proof decision token: {value}"
            )
        return value

    @field_validator("validation_result", mode="before")
    @classmethod
    def _validate_validation_result(cls, value: object) -> str:
        normalized = _clean_required_text(value)
        if not is_valid_acceptance_criterion_result(normalized):
            raise ValueError(
                "validation_result must be a valid acceptance criterion "
                f"result token: {normalized}"
            )
        return normalized


def has_passed_acceptance(
    criteria: Sequence[AcceptanceCriterionContract],
) -> bool:
    """Return True when all criteria are explicitly passed."""
    if not criteria:
        return False
    return all(item.result == ACCEPTANCE_CRITERION_RESULT_PASSED for item in criteria)


def has_blocking_acceptance_failure(
    criteria: Sequence[AcceptanceCriterionContract],
) -> bool:
    """Return True when any criterion has a blocking failure result."""
    blocking = {
        ACCEPTANCE_CRITERION_RESULT_FAILED,
        ACCEPTANCE_CRITERION_RESULT_BLOCKED,
    }
    return any(item.result in blocking for item in criteria)


__all__ = [
    "AcceptanceCriterionContract",
    "IntentScopeGateArtifact",
    "ImplementationPlanGateArtifact",
    "CompletionProofGateArtifact",
    "has_passed_acceptance",
    "has_blocking_acceptance_failure",
]
