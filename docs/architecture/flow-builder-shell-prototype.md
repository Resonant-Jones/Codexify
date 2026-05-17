# Flow Builder Shell Prototype

## Purpose

This document describes the fixture-backed Flow Builder shell prototype (`FB-011`).

This is documentation only. It is not runtime truth, not backend implementation, and not release support.

## Classification

- **Type**: frontend fixture prototype
- **Source**: CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- **Task**: FB-011
- **Status**: complete (fixture-backed prototype only)

## Files

| File | Purpose |
|---|---|
| `frontend/src/features/flowBuilder/types.ts` | Frontend-only TypeScript types for fixture rendering. Not backend API contracts. |
| `frontend/src/features/flowBuilder/fixtures.ts` | Representative fixture data. Not runtime proof. No real secrets or user data. |
| `frontend/src/features/flowBuilder/FlowBuilderShell.tsx` | Fixture-backed UI prototype shell. Consumes local fixture only. No API calls. |
| `frontend/src/features/flowBuilder/FlowBuilderShell.css` | Feature-scoped styles using CSS variables. |
| `frontend/src/features/flowBuilder/index.ts` | Feature exports. |
| `frontend/src/features/flowBuilder/__tests__/FlowBuilderShell.test.tsx` | Frontend tests for fixture rendering. |

## What This Prototype Renders

The shell prototype renders these future Flow Builder concepts as fixture-backed UI:

- **Starter Card**: manual starter fixture with kind, label, and approval posture
- **Draft Overview Card**: FlowDraft fixture with title, status, runtime support, and timestamps
- **Ordered Step List**: semantic extract step, semantic summarize step, conditional container with then/else branches, notification action step
- **Variable Chips & Outputs Panel**: typed outputs with value types, scope, and sensitivity indicators
- **Validation Summary Panel**: validation state, eligibility flags, and issue display with severity
- **TestRun & Activation Panel**: test run and activation summaries with state badges
- **RunReceipt & StepReceipt Panel**: run receipt and step receipt summaries with states
- **Activity & Proof Surface Panel**: ordered activity timeline with event types, states, and evidence refs

## What This Prototype Does NOT Include

This prototype is fixture-backed only. It does not include:

- Backend API routes or persistence
- Live execution or TestRun implementation
- Activation, RunReceipt, or StepReceipt implementation
- Export/restore functionality
- Runtime wiring to live backend services

## Test Coverage

Frontend tests verify:

- Shell renders fixture title
- Starter card renders manual starter details
- Semantic steps render correctly
- Conditional container renders with branches
- Variable chips render with sensitivity indicators
- Validation warnings render
- TestRun/Activation summaries render with state badges
- RunReceipt/StepReceipt summaries render with completed/skipped states
- Activity events render in timeline
- Prototype does not expose live execution controls ("Run now", "Activate now", "Execute")
- Disabled prototype-only buttons are present instead

## Non-Goals

- No backend route, schema, migration, SQLAlchemy model, or Pydantic model
- No validation engine, compiler, or execution path
- No TestRun, Activation, RunReceipt, or StepReceipt persistence
- No export/restore implementation
- No live API wiring
- No beta surface widening

## Relationship to ADRs

This prototype aligns with these accepted ADRs:

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract

The prototype renders concepts from these ADRs against fixture data, not runtime implementation.

## Relationship to Campaign Tasks

This prototype completes FB-011 from CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md.

FB-001 through FB-012 are complete as architecture contracts.

FB-013 remains pending for future implementation work.

## Relationship to Backend TestRun Harness

The frontend shell prototype (`FB-011`) is separate from the backend TestRun harness (`FB-012`):

- **Frontend Shell (FB-011)**: `frontend/src/features/flowBuilder/` - fixture-backed UI rendering of future Flow Builder concepts. No execution, no backend wiring.
- **Backend Harness (FB-012)**: `guardian/flow_builder/` - in-memory non-side-effecting TestRun proof harness. Accepts FlowDraft fixture shapes, validates supported subset, simulates execution, and returns RunReceipt-shaped proof. No model calls, no external writes, no persistence.

These are complementary:
- FB-011 renders concepts for UI prototyping
- FB-012 provides backend proof-of-concept for TestRun semantics

Neither implies shipped runtime support, persistence, or beta surface inclusion.

## Validation

Run frontend tests:

```bash
pnpm --dir frontend test -- FlowBuilderShell
```

## Notes

- Fixtures are fabricated sample data only
- No real secrets, credentials, or user data
- Prototype labels are distinct from canonical token values
- Authoring lane is visually separate from proof/activity panels
