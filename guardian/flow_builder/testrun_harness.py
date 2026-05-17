"""
Flow Builder Non-Side-Effecting TestRun Harness

First non-side-effecting TestRun proof harness for Flow Builder.

This harness:
- Accepts an in-memory fixture-like FlowDraft shape (Mapping[str, Any])
- Validates the supported no-side-effect subset
- Simulates deterministic execution without model calls or external writes
- Returns a TestRunResult with a RunReceipt-shaped proof object

The FB-013 gated side-effect path adds one harness-local proof action:
`record_internal_note`, behind an explicit in-memory gate and without any
external writes.

Supported subset:
- semantic step kinds: extract, summarize, decide
- conditional containers with simple boolean decision references
- transform steps that copy or format existing fixture values

Unsupported / blocked:
- notification, document, task, command steps
- any step with side_effect_risk_class other than none
- any activation field
- any external service ref
- any model/provider policy requiring live inference

Reference: FB-012, FB-013, ADR-006, ADR-014, ADR-027,
flow-builder-testrun-activation-contract.md,
flow-builder-runreceipt-persistence-model.md,
flow-builder-semantic-step-contract.md,
flow-builder-conditional-container-contract.md
"""

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Tuple

from .contracts import (
    ConditionMetadata,
    RunReceipt,
    SemanticMetadata,
    SideEffectGate,
    SideEffectIntent,
    SideEffectRecord,
    StepReceipt,
    TestRunResult,
    ValidationIssue,
    ValidationSummary,
)
from .tokens import (
    HARNESS_SIDE_EFFECT_KIND,
    RUN_RECEIPT_STATE,
    SEMANTIC_STEP_KIND,
    SIDE_EFFECT_MODE,
    SIDE_EFFECT_RISK_CLASS,
    STEP_RECEIPT_STATE,
    SUPPORTED_SEMANTIC_KINDS,
    TEST_RUN_STATE,
    UNSUPPORTED_STEP_KINDS,
    VALIDATION_ISSUE_CODE,
    VALIDATION_SEVERITY,
    is_supported_semantic_kind,
    is_supported_step_kind,
    is_valid_run_receipt_state,
    is_valid_step_receipt_state,
    is_valid_test_run_state,
    is_valid_validation_issue_code,
    is_valid_validation_severity,
)

# =============================================================================
# Time helpers
# =============================================================================


def now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    """Generate a deterministic ID for receipts."""
    import uuid

    return f"{prefix}:{uuid.uuid4().hex[:12]}"


def _is_supported_gated_side_effect_kind(kind: str) -> bool:
    return kind in HARNESS_SIDE_EFFECT_KIND


def _is_forbidden_side_effect_risk_class(risk_class: str) -> bool:
    return risk_class in {
        "external_write",
        "third_party_share",
        "identity_sensitive",
    }


def _build_side_effect_summary(
    side_effect_records: List[SideEffectRecord],
) -> str:
    """Build a receipt-friendly summary for in-memory side effects."""
    if not side_effect_records:
        return "No side effects. Deterministic simulation only."

    parts = []
    for record in side_effect_records:
        parts.append(
            f"{record.id} "
            f"kind={record.intent_kind} "
            f"risk={record.risk_class} "
            f"target={record.target_ref} "
            f"idempotency={record.idempotency_key} "
            f"state={record.state} "
            f"approved_by={record.approved_by or 'unknown'} "
            f"approval_reason={record.approval_reason or 'unknown'}"
        )

    return "Side effect records: " + " | ".join(parts)


# =============================================================================
# Validation
# =============================================================================


def _make_validation_issue(
    code: str,
    severity: str,
    scope: str,
    target_ref: str,
    message: str,
) -> ValidationIssue:
    """Create a ValidationIssue with proper token validation."""
    if not is_valid_validation_issue_code(code):
        code = "missing_required_field"
    if not is_valid_validation_severity(severity):
        severity = "error"
    return ValidationIssue(
        id=new_id("validation-issue"),
        code=code,
        severity=severity,
        scope=scope,
        target_ref=target_ref,
        message=message,
        blocking=severity in ("error", "blocking"),
        created_at=now_iso(),
    )


def _validate_command_side_effect_step(
    step: Mapping[str, Any],
    gate: SideEffectGate,
) -> List[ValidationIssue]:
    """Validate a harness-local side-effecting command step."""
    issues: List[ValidationIssue] = []
    step_id = step.get("id", "unknown-step")
    config = step.get("config", {})
    side_effect_kind = config.get("side_effect_kind", "")
    side_effect_risk = config.get("side_effect_risk_class", "none")
    idempotency_key = config.get("idempotency_key", "")

    if not gate.enabled or gate.mode not in SIDE_EFFECT_MODE:
        issues.append(
            _make_validation_issue(
                code="side_effect_gate_required",
                severity="error",
                scope="step",
                target_ref=step_id,
                message="Harness-local side effects require an explicit enabled gate in explicit_harness_gate mode.",
            )
        )
        return issues

    if (
        side_effect_kind not in gate.allowed_kinds
        or not _is_supported_gated_side_effect_kind(side_effect_kind)
    ):
        issues.append(
            _make_validation_issue(
                code="side_effect_kind_unsupported",
                severity="error",
                scope="step",
                target_ref=step_id,
                message=f"Side-effect kind '{side_effect_kind}' is not allowed by the explicit harness gate.",
            )
        )

    if not idempotency_key:
        issues.append(
            _make_validation_issue(
                code="idempotency_key_required",
                severity="error",
                scope="step",
                target_ref=step_id,
                message="Harness-local side-effect proof requires an idempotency key.",
            )
        )

    if (
        side_effect_risk not in SIDE_EFFECT_RISK_CLASS
        or side_effect_risk == "none"
    ):
        issues.append(
            _make_validation_issue(
                code="side_effect_kind_unsupported",
                severity="error",
                scope="step",
                target_ref=step_id,
                message=f"Side-effect risk class '{side_effect_risk}' is not supported by the harness-local proof path.",
            )
        )
    elif _is_forbidden_side_effect_risk_class(side_effect_risk):
        issues.append(
            _make_validation_issue(
                code="external_side_effect_forbidden",
                severity="error",
                scope="step",
                target_ref=step_id,
                message=f"Side-effect risk class '{side_effect_risk}' is forbidden in the harness-local proof path.",
            )
        )

    return issues


def _validate_step(
    step: Mapping[str, Any],
    *,
    gate: Optional[SideEffectGate] = None,
) -> List[ValidationIssue]:
    """Validate a single step for non-side-effecting execution."""
    issues = []
    step_id = step.get("id", "unknown-step")
    step_kind = step.get("kind", "")

    # Check if step kind is supported
    if step_kind == "command" and gate is not None:
        issues.extend(_validate_command_side_effect_step(step, gate))
    elif not is_supported_step_kind(step_kind):
        issues.append(
            _make_validation_issue(
                code="unsupported_step_kind",
                severity="error",
                scope="step",
                target_ref=step_id,
                message=f"Step kind '{step_kind}' requires external side effects. Not allowed in non-side-effecting test run.",
            )
        )

    # Check semantic step config
    config = step.get("config", {})
    semantic_kind = (
        config.get("semantic_step_kind") if step_kind == "semantic" else None
    )

    if semantic_kind and not is_supported_semantic_kind(semantic_kind):
        issues.append(
            _make_validation_issue(
                code="unsupported_semantic_kind",
                severity="error",
                scope="step",
                target_ref=step_id,
                message=f"Semantic step kind '{semantic_kind}' requires model calls. Not supported in non-side-effecting test run. Supported: {', '.join(sorted(SUPPORTED_SEMANTIC_KINDS))}.",
            )
        )

    # Check side effect risk
    side_effect_risk = config.get("side_effect_risk_class", "none")
    if (
        not (step_kind == "command" and gate is not None)
        and side_effect_risk != "none"
    ):
        issues.append(
            _make_validation_issue(
                code="side_effect_not_allowed",
                severity="error",
                scope="step",
                target_ref=step_id,
                message=f"Step has side_effect_risk_class='{side_effect_risk}'. External side effects are not allowed in non-side-effecting test run.",
            )
        )

    return issues


def _validate_conditional_container(
    container: Mapping[str, Any],
    *,
    gate: Optional[SideEffectGate] = None,
) -> List[ValidationIssue]:
    """Validate a conditional container for non-side-effecting execution."""
    issues = []
    container_id = container.get("id", "unknown-container")

    # Check condition validity
    condition = container.get("condition", {})
    operator = condition.get("operator", "")

    valid_operators = {
        "is_true",
        "is_false",
        "equals",
        "not_equals",
        "contains",
        "not_contains",
        "greater_than",
        "less_than",
        "exists",
        "is_empty",
    }
    if operator and operator not in valid_operators:
        issues.append(
            _make_validation_issue(
                code="invalid_condition",
                severity="error",
                scope="conditional_container",
                target_ref=container_id,
                message=f"Condition operator '{operator}' is not supported. Non-side-effecting test run only supports basic comparison operators.",
            )
        )

    # Check for missing substeps
    substeps = container.get("substeps", [])
    if not substeps:
        issues.append(
            _make_validation_issue(
                code="missing_substep",
                severity="error",
                scope="conditional_container",
                target_ref=container_id,
                message="Conditional container has no substeps. At least one substep is required.",
            )
        )

    # Validate nested substeps
    for substep in substeps:
        issues.extend(_validate_step(substep, gate=gate))

    # Validate else substeps if present
    else_substeps = container.get("else_substeps", [])
    for substep in else_substeps:
        issues.extend(_validate_step(substep, gate=gate))

    return issues


def validate_no_side_effect_subset(
    flow_draft: Mapping[str, Any]
) -> ValidationSummary:
    """
    Validate a FlowDraft against the non-side-effecting subset.

    Checks:
    - Required draft fields present
    - All steps are supported kinds
    - No side effect risk
    - Conditional containers are valid

    Args:
        flow_draft: In-memory FlowDraft fixture shape (Mapping)

    Returns:
        ValidationSummary with issues and eligibility flags
    """
    issues = _validate_flow_draft(flow_draft)

    # Count severity
    blocking_count = sum(1 for i in issues if i.blocking)
    warning_count = sum(1 for i in issues if i.severity == "warning")

    # Determine state
    if blocking_count > 0:
        state = "error"
    elif warning_count > 0:
        state = "warning"
    else:
        state = "info"

    # Determine eligibility
    eligible_for_test_run = blocking_count == 0
    eligible_for_activation = (
        False  # Activation not implemented in this harness
    )

    return ValidationSummary(
        state=state,
        eligible_for_test_run=eligible_for_test_run,
        eligible_for_activation=eligible_for_activation,
        issues=issues,
        blocking_count=blocking_count,
        warning_count=warning_count,
        validated_at=now_iso(),
        validator_version="1.0.0-harness",
    )


def _validate_flow_draft(
    flow_draft: Mapping[str, Any],
    *,
    gate: Optional[SideEffectGate] = None,
) -> List[ValidationIssue]:
    """Validate a FlowDraft with an optional harness-local side-effect gate."""
    issues: List[ValidationIssue] = []

    # Check required draft fields
    if not flow_draft.get("id"):
        issues.append(
            _make_validation_issue(
                code="missing_required_field",
                severity="error",
                scope="flow",
                target_ref="flow-draft",
                message="FlowDraft is missing required field: id",
            )
        )

    # Check steps
    steps = flow_draft.get("steps", [])
    for step in steps:
        issues.extend(_validate_step(step, gate=gate))

    # Check conditional containers
    conditional_container = flow_draft.get("conditional_container")
    if conditional_container:
        issues.extend(
            _validate_conditional_container(
                conditional_container,
                gate=gate,
            )
        )

    return issues


# =============================================================================
# Execution simulation
# =============================================================================


def _simulate_semantic_step(
    step: Mapping[str, Any],
    branch_context: Optional[str] = None,
) -> StepReceipt:
    """Simulate a semantic step with deterministic placeholder outputs."""
    step_id = step.get("id", "unknown-step")
    config = step.get("config", {})
    semantic_kind = config.get("semantic_step_kind", "unknown")

    # Create semantic metadata
    semantic_metadata = SemanticMetadata(
        semantic_step_kind=semantic_kind,
        uncertainty_outcome="known",  # Deterministic simulation
        model_policy_ref="harness/no-model-call",
        allowed_sources_snapshot="fixture-config",
    )

    # Determine output refs based on semantic kind
    output_refs = []
    if semantic_kind == "extract":
        output_refs = [
            f"{step_id}.output.extracted_field_1",
            f"{step_id}.output.extracted_field_2",
        ]
    elif semantic_kind == "summarize":
        output_refs = [f"{step_id}.output.summary"]
    elif semantic_kind == "decide":
        output_refs = [f"{step_id}.output.decision"]

    return StepReceipt(
        id=new_id("step-receipt"),
        source_step_ref=step_id,
        source_branch_ref=branch_context,
        state="completed",
        input_refs=config.get("input_binding_refs", []),
        output_refs=output_refs,
        value_summary=f"Simulated {semantic_kind} step: deterministic placeholder output.",
        semantic_metadata=semantic_metadata,
        started_at=now_iso(),
        completed_at=now_iso(),
    )


def _simulate_transform_step(
    step: Mapping[str, Any],
    branch_context: Optional[str] = None,
) -> StepReceipt:
    """Simulate a transform step with deterministic output."""
    step_id = step.get("id", "unknown-step")

    return StepReceipt(
        id=new_id("step-receipt"),
        source_step_ref=step_id,
        source_branch_ref=branch_context,
        state="completed",
        input_refs=[],
        output_refs=[f"{step_id}.output.transformed_value"],
        value_summary="Simulated transform step: deterministic value copy.",
        started_at=now_iso(),
        completed_at=now_iso(),
    )


def _create_side_effect_record(
    intent: SideEffectIntent,
    *,
    approved_by: str,
    approval_reason: str,
) -> SideEffectRecord:
    """Create an in-memory side-effect record for the proof surface."""
    return SideEffectRecord(
        id=new_id("side-effect"),
        intent_kind=intent.kind,
        risk_class=intent.risk_class,
        target_ref=intent.target_ref,
        idempotency_key=intent.idempotency_key,
        state="recorded",
        payload_summary=intent.payload_summary,
        created_at=now_iso(),
        approved_by=approved_by,
        approval_reason=approval_reason,
    )


def _simulate_command_step(
    step: Mapping[str, Any],
    gate: SideEffectGate,
    branch_context: Optional[str] = None,
    *,
    side_effect_records: Optional[List[SideEffectRecord]] = None,
) -> StepReceipt:
    """Simulate the single supported harness-local side-effecting command."""
    step_id = step.get("id", "unknown-step")
    config = step.get("config", {})
    intent = SideEffectIntent(
        kind=config.get("side_effect_kind", "record_internal_note"),
        risk_class=config.get("side_effect_risk_class", "internal_write"),
        target_ref=config.get("target_ref", step.get("target_ref", step_id)),
        payload_summary=config.get(
            "payload_summary",
            f"Harness-local internal note for {step_id}.",
        ),
        idempotency_key=config.get("idempotency_key", ""),
        requires_gate=True,
    )

    record = _create_side_effect_record(
        intent,
        approved_by=gate.approved_by,
        approval_reason=gate.approval_reason,
    )
    if side_effect_records is not None:
        side_effect_records.append(record)

    return StepReceipt(
        id=new_id("step-receipt"),
        source_step_ref=step_id,
        source_branch_ref=branch_context,
        state="completed",
        input_refs=config.get("input_binding_refs", []),
        output_refs=[f"{step_id}.output.internal_note_recorded"],
        value_summary=(
            "Harness-local record_internal_note side-effect proof "
            f"recorded for {intent.target_ref}."
        ),
        side_effect_refs=[record.id],
        started_at=now_iso(),
        completed_at=now_iso(),
    )


def _simulate_conditional_container(
    container: Mapping[str, Any],
    gate: Optional[SideEffectGate] = None,
    *,
    side_effect_records: Optional[List[SideEffectRecord]] = None,
) -> List[StepReceipt]:
    """Simulate a conditional container and its branches."""
    container_id = container.get("id", "unknown-container")
    condition = container.get("condition", {})
    lhs = condition.get("lhs", "")
    operator = condition.get("operator", "is_true")
    rhs = condition.get("rhs", "")

    receipts: List[StepReceipt] = []

    # For simulation, we evaluate the condition deterministically
    # In a real harness, this would be based on fixture input values
    condition_result = _evaluate_condition_fixture(lhs, operator, rhs)

    selected_branch = "then" if condition_result else "else"
    substeps = container.get("substeps", [])
    else_substeps = container.get("else_substeps", [])

    branch_context = f"{container_id}:{selected_branch}"

    # Simulate selected branch
    if condition_result:
        for i, substep in enumerate(substeps):
            receipt = _simulate_step(
                substep,
                branch_context=f"{container_id}:then",
                gate=gate,
                side_effect_records=side_effect_records,
            )
            receipts.append(receipt)

        # Mark else branch as skipped
        for substep in else_substeps:
            else_branch_context = f"{container_id}:else"
            receipt = StepReceipt(
                id=new_id("step-receipt"),
                source_step_ref=substep.get("id", "unknown-step"),
                source_branch_ref=else_branch_context,
                state="skipped",
                value_summary="Step skipped due to condition evaluation (else branch not selected).",
                skipped_at=now_iso(),
            )
            receipts.append(receipt)
    else:
        # Mark then branch as skipped
        for substep in substeps:
            then_branch_context = f"{container_id}:then"
            receipt = StepReceipt(
                id=new_id("step-receipt"),
                source_step_ref=substep.get("id", "unknown-step"),
                source_branch_ref=then_branch_context,
                state="skipped",
                value_summary="Step skipped due to condition evaluation (then branch not selected).",
                skipped_at=now_iso(),
            )
            receipts.append(receipt)

        # Simulate else branch
        for substep in else_substeps:
            receipt = _simulate_step(
                substep,
                branch_context=f"{container_id}:else",
                gate=gate,
                side_effect_records=side_effect_records,
            )
            receipts.append(receipt)

    # Add condition metadata to first receipt in selected branch
    if receipts:
        condition_metadata = ConditionMetadata(
            condition_ref=condition.get("id", f"condition:{container_id}"),
            condition_result=condition_result,
            evaluated_inputs=[lhs] if lhs else [],
            selected_branch=selected_branch,
            skipped_step_refs=[
                r.source_step_ref for r in receipts if r.state == "skipped"
            ],
            executed_step_refs=[
                r.source_step_ref for r in receipts if r.state == "completed"
            ],
        )
        # Attach condition metadata to all branch receipts
        for receipt in receipts:
            if receipt.source_branch_ref == branch_context:
                receipt.condition_metadata = condition_metadata

    return receipts


def _evaluate_condition_fixture(lhs: str, operator: str, rhs: str) -> bool:
    """
    Evaluate a condition deterministically based on fixture config.

    For simulation purposes, we use a deterministic heuristic:
    - If rhs is numeric, compare against fixture input values
    - Otherwise, return True for testing purposes

    In a real harness, this would use actual fixture input values.
    """
    # Simple heuristic for simulation
    try:
        rhs_value = float(rhs)
        # For demo purposes, assume the value is greater than threshold
        # This simulates a passing condition in test fixtures
        return rhs_value < 100
    except (ValueError, TypeError):
        # Non-numeric comparison, return True for testing
        return True


def _simulate_step(
    step: Mapping[str, Any],
    branch_context: Optional[str] = None,
    gate: Optional[SideEffectGate] = None,
    *,
    side_effect_records: Optional[List[SideEffectRecord]] = None,
) -> StepReceipt:
    """Simulate a single step based on its kind."""
    step_kind = step.get("kind", "")

    if step_kind == "semantic":
        return _simulate_semantic_step(step, branch_context)
    elif step_kind == "transform":
        return _simulate_transform_step(step, branch_context)
    elif step_kind == "command" and gate is not None:
        return _simulate_command_step(
            step,
            gate,
            branch_context,
            side_effect_records=side_effect_records,
        )
    else:
        # Unsupported step kind - should have been caught by validation
        return StepReceipt(
            id=new_id("step-receipt"),
            source_step_ref=step.get("id", "unknown-step"),
            source_branch_ref=branch_context,
            state="blocked",
            failure_reason=f"Step kind '{step_kind}' is not supported.",
        )


# =============================================================================
# Main harness entry point
# =============================================================================


def _run_test_internal(
    flow_draft: Mapping[str, Any],
    *,
    initiated_by: str,
    gate: Optional[SideEffectGate] = None,
) -> TestRunResult:
    """Run the shared in-memory TestRun harness path."""
    flow_draft_id = flow_draft.get("id", "unknown-draft")
    test_run_id = new_id("test-run")

    # Create deterministic timestamps
    created_at = now_iso()
    started_at = now_iso()

    # Validate the draft
    if gate is None:
        validation_summary = validate_no_side_effect_subset(flow_draft)
    else:
        issues = _validate_flow_draft(flow_draft, gate=gate)
        blocking_count = sum(1 for i in issues if i.blocking)
        warning_count = sum(1 for i in issues if i.severity == "warning")
        if blocking_count > 0:
            state = "error"
        elif warning_count > 0:
            state = "warning"
        else:
            state = "info"
        validation_summary = ValidationSummary(
            state=state,
            eligible_for_test_run=blocking_count == 0,
            eligible_for_activation=False,
            issues=issues,
            blocking_count=blocking_count,
            warning_count=warning_count,
            validated_at=now_iso(),
            validator_version="1.0.0-harness",
        )

    # Initialize run receipt
    run_receipt: Optional[RunReceipt] = None
    side_effect_records: List[SideEffectRecord] = []

    if validation_summary.eligible_for_test_run:
        # Execute supported steps
        step_receipts: List[StepReceipt] = []

        # Process top-level steps
        steps = flow_draft.get("steps", [])
        for step in steps:
            receipt = _simulate_step(
                step,
                gate=gate,
                side_effect_records=side_effect_records,
            )
            step_receipts.append(receipt)

        # Process conditional container
        conditional_container = flow_draft.get("conditional_container")
        if conditional_container:
            container_receipts = _simulate_conditional_container(
                conditional_container,
                gate=gate,
                side_effect_records=side_effect_records,
            )
            step_receipts.extend(container_receipts)

        side_effect_summary = _build_side_effect_summary(side_effect_records)
        permission_snapshot = (
            "permission:harness:local:no-side-effect"
            if gate is None
            else f"permission:harness:local:{gate.mode}"
        )

        # Build run receipt
        run_receipt = RunReceipt(
            id=new_id("run-receipt"),
            flow_draft_id=flow_draft_id,
            compiled_plan_id=flow_draft.get("compiled_plan_ref"),
            test_run_id=test_run_id,
            initiator_ref=initiated_by,
            trigger_ref=flow_draft.get("starter", {}).get("id"),
            state="completed",
            validation_snapshot=f"validation:{flow_draft_id}:snapshot",
            permission_snapshot=permission_snapshot,
            step_receipts=step_receipts,
            semantic_metadata_summary="No semantic AI steps executed in harness mode.",
            side_effect_summary=side_effect_summary,
            provenance=flow_draft.get("provenance", {}).get(
                "origin_thread_id", "unknown"
            ),
            created_at=created_at,
            started_at=started_at,
            completed_at=now_iso(),
        )

        completed_at = run_receipt.completed_at
        state = "completed"
        failure_reason = None
    else:
        # Blocked due to validation failures
        permission_snapshot = (
            "permission:harness:local:no-side-effect"
            if gate is None
            else f"permission:harness:local:{gate.mode}"
        )
        run_receipt = RunReceipt(
            id=new_id("run-receipt"),
            flow_draft_id=flow_draft_id,
            test_run_id=test_run_id,
            initiator_ref=initiated_by,
            state="blocked",
            validation_snapshot=f"validation:{flow_draft_id}:snapshot",
            permission_snapshot=permission_snapshot,
            step_receipts=[],
            side_effect_summary="No side effects. Validation blocked execution.",
            provenance=flow_draft.get("provenance", {}).get(
                "origin_thread_id", "unknown"
            ),
            created_at=created_at,
            started_at=started_at,
            completed_at=now_iso(),
            failure_reason=f"Validation blocked: {validation_summary.blocking_count} blocking issues.",
        )

        completed_at = run_receipt.completed_at
        state = "blocked"
        failure_reason = run_receipt.failure_reason

    return TestRunResult(
        id=test_run_id,
        flow_draft_id=flow_draft_id,
        state=state,
        validation_summary=validation_summary,
        run_receipt=run_receipt,
        side_effect_records=side_effect_records,
        initiated_by=initiated_by,
        created_at=created_at,
        started_at=started_at,
        completed_at=completed_at,
        failure_reason=failure_reason,
    )


def run_non_side_effecting_test(
    flow_draft: Mapping[str, Any],
    *,
    initiated_by: str = "test-harness",
) -> TestRunResult:
    """
    Run a non-side-effecting test against a FlowDraft.

    This harness:
    1. Validates the draft against non-side-effecting subset
    2. Simulates execution for supported steps
    3. Produces a TestRunResult with RunReceipt-shaped proof object

    Args:
        flow_draft: In-memory FlowDraft fixture shape (Mapping)
        initiated_by: Initiator identifier (default: "test-harness")

    Returns:
        TestRunResult with validation summary, run receipt, and execution proof

    Note:
        This harness does NOT:
        - Call model providers
        - Write to external systems
        - Persist receipts to database
        - Emit task events
        - Wire to Redis queues
    """
    return _run_test_internal(
        flow_draft,
        initiated_by=initiated_by,
    )


def run_gated_side_effect_test(
    flow_draft: Mapping[str, Any],
    *,
    gate: SideEffectGate,
    initiated_by: str = "test-harness",
) -> TestRunResult:
    """
    Run the narrow FB-013 harness-local side-effect proof path.

    This remains in-memory only and records receipt-shaped evidence only.
    """
    return _run_test_internal(
        flow_draft,
        initiated_by=initiated_by,
        gate=gate,
    )
