"""
Flow Builder Token Registry (Harness-Local)

This module contains bounded token registries for the Flow Builder TestRun proof harness.
These are harness-local Flow Builder tokens pending future shared registry promotion.

These tokens do NOT modify global runtime protocol tokens in guardian/protocol_tokens.py.
They are scoped to the flow_builder harness module only.

Token families:
- TEST_RUN_STATE: ephemeral test run execution states
- RUN_RECEIPT_STATE: durable run receipt states
- STEP_RECEIPT_STATE: per-step receipt states
- VALIDATION_SEVERITY: validation issue severity levels
- VALIDATION_ISSUE_CODE: validation issue machine-readable codes
- ACTION_STEP_KIND: authored step family labels
- SEMANTIC_STEP_KIND: bounded AI step semantic intents
- SIDE_EFFECT_MODE: execution side effect risk modes

Reference: flow-builder-token-domains.md, ADR-027
"""

# =============================================================================
# Test Run State (ephemeral)
# =============================================================================

TEST_RUN_STATE = frozenset(
    {
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
    }
)

# =============================================================================
# Run Receipt State (durable proof surface)
# =============================================================================

RUN_RECEIPT_STATE = frozenset(
    {
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
        "blocked",
    }
)

# =============================================================================
# Step Receipt State (per-step evidence)
# =============================================================================

STEP_RECEIPT_STATE = frozenset(
    {
        "pending",
        "running",
        "skipped",
        "completed",
        "failed",
        "blocked",
    }
)

# =============================================================================
# Validation Severity (eligibility ladder)
# =============================================================================

VALIDATION_SEVERITY = frozenset(
    {
        "info",
        "warning",
        "error",
        "blocking",
    }
)

# =============================================================================
# Validation Issue Codes (machine-readable)
# =============================================================================

VALIDATION_ISSUE_CODE = frozenset(
    {
        "missing_required_field",
        "unsupported_step_kind",
        "side_effect_not_allowed",
        "missing_substep",
        "unsupported_semantic_kind",
        "invalid_condition",
        "incompatible_variable_type",
        "missing_output_declaration",
        "deleted_or_unavailable_reference",
        "unknown_semantic_output",
        "receipt_required",
    }
)

# =============================================================================
# Action Step Kind (authored step family)
# =============================================================================

ACTION_STEP_KIND = frozenset(
    {
        "semantic",
        "conditional",
        "transform",
        "notification",
        "document",
        "task",
        "command",
    }
)

# =============================================================================
# Semantic Step Kind (bounded AI step intent)
# =============================================================================

SEMANTIC_STEP_KIND = frozenset(
    {
        "extract",
        "summarize",
        "classify",
        "decide",
        "transform",
        "route",
    }
)

# =============================================================================
# Side Effect Mode (execution risk classification)
# =============================================================================

SIDE_EFFECT_MODE = frozenset(
    {
        "none",
    }
)

# =============================================================================
# Unsupported Step Kind Set (fail-closed)
# =============================================================================

# Steps that require external writes, connectors, or model calls
UNSUPPORTED_STEP_KINDS = frozenset(
    {
        "notification",
        "document",
        "task",
        "command",
    }
)

# =============================================================================
# Supported Semantic Step Kind Set
# =============================================================================

SUPPORTED_SEMANTIC_KINDS = frozenset(
    {
        "extract",
        "summarize",
        "decide",
    }
)

# =============================================================================
# Validation helpers
# =============================================================================


def is_supported_step_kind(kind: str) -> bool:
    """Check if a step kind is supported for non-side-effecting test run."""
    return kind not in UNSUPPORTED_STEP_KINDS


def is_supported_semantic_kind(kind: str) -> bool:
    """Check if a semantic step kind is supported."""
    return kind in SUPPORTED_SEMANTIC_KINDS


def is_valid_test_run_state(state: str) -> bool:
    """Check if a test run state is valid."""
    return state in TEST_RUN_STATE


def is_valid_run_receipt_state(state: str) -> bool:
    """Check if a run receipt state is valid."""
    return state in RUN_RECEIPT_STATE


def is_valid_step_receipt_state(state: str) -> bool:
    """Check if a step receipt state is valid."""
    return state in STEP_RECEIPT_STATE


def is_valid_validation_severity(severity: str) -> bool:
    """Check if a validation severity is valid."""
    return severity in VALIDATION_SEVERITY


def is_valid_validation_issue_code(code: str) -> bool:
    """Check if a validation issue code is valid."""
    return code in VALIDATION_ISSUE_CODE
