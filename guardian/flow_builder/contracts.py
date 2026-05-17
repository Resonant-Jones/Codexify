"""
Flow Builder Contracts (Harness-Local)

Pure dataclass contracts for the Flow Builder TestRun proof harness.

This module defines receipt-shaped contracts only. It does NOT:
- Import database models
- Import FastAPI
- Import Redis
- Import model providers
- Import command bus
- Import task event emitters

Reference: ADR-027, flow-builder-runreceipt-persistence-model.md,
flow-builder-testrun-activation-contract.md, flow-builder-semantic-step-contract.md,
flow-builder-conditional-container-contract.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Mapping, Optional

# =============================================================================
# Validation Contracts
# =============================================================================


@dataclass
class ValidationIssue:
    """
    Structured validation finding for FlowDraft.

    Mirrors candidate FB-004 ValidationIssue contract.
    """

    id: str
    code: str  # VALIDATION_ISSUE_CODE token
    severity: str  # VALIDATION_SEVERITY token
    scope: str  # flow | starter | step | variable_binding | typed_output | conditional_container
    target_ref: str
    message: str
    blocking: bool
    created_at: str


@dataclass
class ValidationSummary:
    """
    Aggregated validation state for a FlowDraft.

    Mirrors candidate FB-004 ValidationSummary contract.
    """

    state: str  # VALIDATION_SEVERITY token
    eligible_for_test_run: bool
    eligible_for_activation: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    blocking_count: int = 0
    warning_count: int = 0
    validated_at: str = ""
    validator_version: str = "1.0.0-harness"


# =============================================================================
# Semantic Metadata Contracts
# =============================================================================


@dataclass
class SemanticMetadata:
    """
    Bounded semantic evidence for AI-assisted steps.

    Mirrors candidate flow-builder-semantic-step-contract.md receipt metadata.
    """

    semantic_step_kind: str  # SEMANTIC_STEP_KIND token
    uncertainty_outcome: str  # known | unknown | low_confidence | insufficient_evidence
    model_policy_ref: Optional[str] = None
    allowed_sources_snapshot: Optional[str] = None
    redaction_summary: Optional[str] = None
    failure_reason: Optional[str] = None


@dataclass
class ConditionMetadata:
    """
    Branch evaluation evidence for conditional containers.

    Mirrors candidate flow-builder-conditional-container-contract.md receipt metadata.
    """

    condition_ref: str
    condition_result: bool
    evaluated_inputs: List[str] = field(default_factory=list)
    selected_branch: str = "then"  # then | else
    skipped_step_refs: List[str] = field(default_factory=list)
    executed_step_refs: List[str] = field(default_factory=list)
    uncertainty_outcome: Optional[str] = None


# =============================================================================
# Step Receipt Contract
# =============================================================================


@dataclass
class StepReceipt:
    """
    Step-level execution evidence for a specific step attempt.

    Mirrors candidate FB-008 StepReceipt contract.
    """

    id: str
    source_step_ref: str
    source_branch_ref: Optional[str] = None
    state: str = "pending"  # STEP_RECEIPT_STATE token
    input_refs: List[str] = field(default_factory=list)
    output_refs: List[str] = field(default_factory=list)
    value_summary: str = ""
    semantic_metadata: Optional[SemanticMetadata] = None
    condition_metadata: Optional[ConditionMetadata] = None
    side_effect_refs: List[str] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    skipped_at: Optional[str] = None
    failure_reason: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        """Check if this receipt state is terminal."""
        return self.state in ("completed", "failed", "skipped", "blocked")

    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate duration in milliseconds if timestamps available."""
        if self.completed_at and self.started_at:
            start = datetime.fromisoformat(
                self.started_at.replace("Z", "+00:00")
            )
            end = datetime.fromisoformat(
                self.completed_at.replace("Z", "+00:00")
            )
            return int((end - start).total_seconds() * 1000)
        return None


# =============================================================================
# Side Effect Contracts
# =============================================================================


@dataclass
class SideEffectIntent:
    """
    Parsed intent for a harness-local side effect.

    This is an FB-013 in-memory proof artifact only. It is not a general
    runtime execution contract.
    """

    kind: str
    risk_class: str
    target_ref: str
    payload_summary: str
    idempotency_key: str
    requires_gate: bool = True


@dataclass
class SideEffectRecord:
    """
    In-memory side-effect proof record.

    Mirrors the FB-013 gated harness evidence surface only.
    """

    id: str
    intent_kind: str
    risk_class: str
    target_ref: str
    idempotency_key: str
    state: str = "recorded"
    payload_summary: str = ""
    created_at: str = ""
    failure_reason: Optional[str] = None
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None


@dataclass
class SideEffectGate:
    """
    Explicit harness-local gate for the FB-013 proof path.
    """

    enabled: bool
    mode: str
    allowed_kinds: List[str] = field(default_factory=list)
    approved_by: str = ""
    approval_reason: str = ""


# =============================================================================
# Run Receipt Contract
# =============================================================================


@dataclass
class RunReceipt:
    """
    Run-level execution proof surface.

    Mirrors candidate FB-008 RunReceipt contract.
    """

    id: str
    flow_draft_id: str
    compiled_plan_id: Optional[str] = None
    test_run_id: Optional[str] = None
    activation_id: Optional[str] = None
    initiator_ref: str = "test-harness"
    trigger_ref: Optional[str] = None
    state: str = "queued"  # RUN_RECEIPT_STATE token
    validation_snapshot: str = ""
    permission_snapshot: str = ""
    step_receipts: List[StepReceipt] = field(default_factory=list)
    semantic_metadata_summary: Optional[str] = None
    side_effect_summary: str = ""  # "No side effects."
    provenance: str = ""
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    failure_reason: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        """Check if this receipt state is terminal."""
        return self.state in ("completed", "failed", "cancelled", "blocked")

    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate duration in milliseconds if timestamps available."""
        if self.completed_at and self.started_at:
            start = datetime.fromisoformat(
                self.started_at.replace("Z", "+00:00")
            )
            end = datetime.fromisoformat(
                self.completed_at.replace("Z", "+00:00")
            )
            return int((end - start).total_seconds() * 1000)
        return None

    @property
    def step_counts(self) -> Mapping[str, int]:
        """Count steps by receipt state."""
        counts = {
            "pending": 0,
            "running": 0,
            "skipped": 0,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
        }
        for receipt in self.step_receipts:
            if receipt.state in counts:
                counts[receipt.state] += 1
        return counts


# =============================================================================
# Test Run Result Contract
# =============================================================================


@dataclass
class TestRunResult:
    """
    Complete result from a non-side-effecting test run harness.

    Aggregates test run metadata with run receipt and validation summary.
    """

    id: str
    flow_draft_id: str
    state: str  # TEST_RUN_STATE token
    validation_summary: ValidationSummary
    run_receipt: Optional[RunReceipt] = None
    side_effect_records: List[SideEffectRecord] = field(default_factory=list)
    initiated_by: str = "test-harness"
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None

    @property
    def is_eligible_for_test_run(self) -> bool:
        """Check if this test run result indicates test run eligibility."""
        return self.validation_summary.eligible_for_test_run

    @property
    def is_blocked(self) -> bool:
        """Check if this test run result is blocked due to validation failures."""
        return (
            self.state in ("failed", "cancelled", "blocked")
            or self.validation_summary.blocking_count > 0
        )

    @property
    def side_effect_count(self) -> int:
        """Count side effect refs across all step receipts."""
        if not self.run_receipt:
            return 0
        return sum(
            len(sr.side_effect_refs) for sr in self.run_receipt.step_receipts
        )
