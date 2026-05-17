# Flow Builder TestRun Harness

## Purpose

This document describes the non-side-effecting Flow Builder TestRun proof harness (`FB-012`).

This is harness documentation only. It is not runtime truth, not API support, and not release support.

## Classification

- **Type**: backend pure-contract proof harness
- **Source**: CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- **Task**: FB-012
- **Status**: complete (in-memory non-side-effecting harness only)

## Files

| File | Purpose |
|---|---|
| `guardian/flow_builder/tokens.py` | Harness-local token registries for Flow Builder. Bounded sets. Separate from global runtime protocol tokens. |
| `guardian/flow_builder/contracts.py` | Pure dataclass contracts for ValidationIssue, ValidationSummary, StepReceipt, RunReceipt, TestRunResult. No DB imports. |
| `guardian/flow_builder/testrun_harness.py` | Main harness: `validate_no_side_effect_subset()` and `run_non_side_effecting_test()`. |
| `guardian/flow_builder/__init__.py` | Module exports. |
| `tests/flow_builder/test_testrun_harness.py` | 50+ tests covering validation, execution, immutability, import isolation, receipt shape, and token boundedness. |

## What This Harness Does

The TestRun harness:

1. **Validates** FlowDraft against non-side-effecting subset:
   - semantic step kinds: `extract`, `summarize`, `decide` (supported)
   - `transform` steps (supported)
   - `conditional` containers with basic condition operators (supported)
   - `notification`, `document`, `task`, `command` (blocked)

2. **Simulates** deterministic execution:
   - No model calls
   - No external writes
   - No Redis/queue operations
   - No command bus integration
   - Placeholder outputs for semantic steps

3. **Produces** TestRunResult with RunReceipt-shaped proof:
   - ValidationSummary with issues and eligibility flags
   - RunReceipt with step receipts
   - Semantic metadata for AI-assisted steps
   - Condition metadata for conditional branches
   - Side effect summary showing zero side effects

## Supported Subset

| Step Kind | Supported | Notes |
|---|---|---|
| `semantic` (extract, summarize, decide) | Yes | No model calls. Deterministic placeholder output. |
| `transform` | Yes | Copy or format existing fixture values. |
| `conditional` | Yes | Basic boolean operators. Skips non-selected branch. |
| `notification` | No | Blocked. Requires external write. |
| `document` | No | Blocked. Requires external write. |
| `task` | No | Blocked. Requires external write. |
| `command` | No | Blocked. Requires external write. |

## What This Harness Does NOT Include

- No API routes
- No database persistence
- No Redis queues
- No cron integration
- No command bus integration
- No model provider calls
- No Activation implementation
- No side-effecting execution

## Test Coverage

Tests verify:

- **Token validation**: Supported/unsupported step kinds, semantic kinds, states, severity, codes
- **Validation**: Valid fixtures pass, missing fields block, side-effecting steps block, unsupported semantic kinds block
- **Execution**: Completed results, step receipts with semantic metadata, skipped branch steps, transform steps
- **Immutability**: Input FlowDraft not mutated after harness runs
- **Import isolation**: No database, API, Redis, model provider, or command bus imports
- **Receipt shape**: Required fields present, semantic metadata for semantic steps, condition metadata for conditional branches
- **Token boundedness**: Flow Builder tokens separate from global runtime protocol tokens

## Usage

```python
from guardian.flow_builder import validate_no_side_effect_subset, run_non_side_effecting_test

# Create FlowDraft fixture
draft = {
    "id": "flow-draft:test-001",
    "steps": [
        {"id": "step:extract-001", "kind": "semantic", "config": {"semantic_step_kind": "extract", "side_effect_risk_class": "none"}},
    ],
}

# Validate
validation_summary = validate_no_side_effect_subset(draft)
print(f"Eligible: {validation_summary.eligible_for_test_run}")

# Run test
result = run_non_side_effecting_test(draft)
print(f"State: {result.state}")
print(f"Side effects: {result.side_effect_count}")
```

## Relationship to ADRs

Aligns with accepted ADRs:

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- `flow-builder-testrun-activation-contract.md`
- `flow-builder-runreceipt-persistence-model.md`
- `flow-builder-semantic-step-contract.md`
- `flow-builder-conditional-container-contract.md`

## Relationship to Campaign Tasks

- FB-011: Frontend fixture shell (separate)
- FB-012: This harness (complete)
- FB-013: Pending side-effecting execution (future)

## Validation

Run backend tests:

```bash
pytest -v tests/flow_builder/test_testrun_harness.py
```

## Non-Goals

- No runtime execution engine
- No persistence layer
- No API support
- No model provider integration
- No command bus wiring
- No supported beta feature