"""
Flow Builder TestRun Harness

First non-side-effecting Flow Builder TestRun proof harness.

This module provides a pure in-memory harness for validating and simulating
Flow Builder execution without external side effects.

Exports:
    validate_no_side_effect_subset: Validate FlowDraft against non-side-effecting subset
    run_non_side_effecting_test: Run non-side-effecting test and produce TestRunResult

Reference: FB-012, ADR-006, ADR-014, ADR-027

Note:
    This harness is NOT:
    - A runtime execution engine
    - An API route
    - A persistence layer
    - A model provider integration
    - A command bus integration
    - A supported beta feature
"""

from .contracts import (
    ConditionMetadata,
    RunReceipt,
    SemanticMetadata,
    StepReceipt,
    TestRunResult,
    ValidationIssue,
    ValidationSummary,
)
from .testrun_harness import (
    run_non_side_effecting_test,
    validate_no_side_effect_subset,
)
from .tokens import (
    ACTION_STEP_KIND,
    RUN_RECEIPT_STATE,
    SEMANTIC_STEP_KIND,
    SIDE_EFFECT_MODE,
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

__all__ = [
    # Tokens
    "TEST_RUN_STATE",
    "RUN_RECEIPT_STATE",
    "STEP_RECEIPT_STATE",
    "VALIDATION_SEVERITY",
    "VALIDATION_ISSUE_CODE",
    "ACTION_STEP_KIND",
    "SEMANTIC_STEP_KIND",
    "SIDE_EFFECT_MODE",
    "UNSUPPORTED_STEP_KINDS",
    "SUPPORTED_SEMANTIC_KINDS",
    "is_supported_step_kind",
    "is_supported_semantic_kind",
    "is_valid_test_run_state",
    "is_valid_run_receipt_state",
    "is_valid_step_receipt_state",
    "is_valid_validation_severity",
    "is_valid_validation_issue_code",
    # Contracts
    "ValidationIssue",
    "ValidationSummary",
    "SemanticMetadata",
    "ConditionMetadata",
    "StepReceipt",
    "RunReceipt",
    "TestRunResult",
    # Harness
    "validate_no_side_effect_subset",
    "run_non_side_effecting_test",
]
