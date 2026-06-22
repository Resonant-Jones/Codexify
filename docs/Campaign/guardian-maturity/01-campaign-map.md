# Guardian Maturity Campaign Map

## Purpose

Enumerate all campaigns in the Guardian Maturity Program with status, dependencies, risk classification, and one-sentence purpose.

All campaigns are currently in `planned` status. No implementation has begun.

## Campaign Index

| ID | Title | Wave | Status | Primary Domain | Risk | Purpose |
|----|-------|------|--------|----------------|------|---------|
| C00 | Truth Gate and Worktree Classification | 0 | planned | Proof / Audit | LOW | Establish the starting line: classify branch/worktree state, dirty state, runtime proof gaps, and release boundary confirmation before touching runtime or UI. |
| C11 | Guardian API Route Audit and Scaffold | 0 | planned | Backend / Audit | MED | Audit what API routes exist, map gaps against campaign needs, scaffold missing route registration patterns without implementing behavior. |
| C01 | Guardian Command Center | 1 | planned | Frontend / Operator UX | MED | Complete the existing Command Center surface into a unified operator truth surface with "Can I run?" verdicts linked to evidence. |
| C02 | Chat Runtime State and Transcript Integrity | 1 | planned | Frontend / Runtime | MED | Surface the full provider runtime state contract and per-message request lifecycle in the UI; fix slow-warmup false-offline labeling; handle orphaned/replayed states. |
| C03 | Coding Delegation Spine | 2 | planned | Backend + Frontend | HIGH | Make "delegate coding work through Guardian" real but bounded: create structured delegation drafts from threads with source lineage, explicit permissions, and no execution without review. |
| C05 | Command Bus and Tool Turn Observability | 2 | planned | Backend + Frontend | MED | Make bounded tool execution visible and auditable: surface toolTurnId, commandRunId, toolTurnState, loopStopReason, and failure reasons. |
| C06 | Guardian Operator Workspace | 2 | planned | Frontend / UX | LOW | Extend the existing Workspace into an operator surface: Scratchpad, Shelf, Inspector, active task materials, and task notes. |
| C04 | Pi/Coder Invocation Boundary | 3 | planned | Backend + Frontend | HIGH | Turn the Pi invocation contract from backend-only validation into a UI-visible governed invocation seam with envelope preview and validation-only run mode. |
| C07 | Persona Studio and Agent Configuration | 3 | planned | Frontend / Config | MED | Move Guardian configuration from scattered assumptions into an inspectable profile/config surface with explicit tool permissions, retrieval policy, and runtime flags. |
| C08 | Whoosh'd Runtime Setup and Local Model Management | 3 | planned | Backend + Frontend | MED | Make local runtime configuration operator-safe with preset selection, model inventory proof, readiness warnings, and state distinction. |
| C09 | Execution Ledger and Proof Packs | 4 | planned | Backend + Frontend | MED | Give every serious Guardian operation a receipt: execution ledger rows, proof artifacts, acceptance criteria mapping, and gate decision records. |
| C10 | Recovery and Operator Repair | 4 | planned | Backend + Frontend | HIGH | Give operators tools to understand and recover from stuck work: stale lock visibility, worker missing state, queue backlog, orphaned request handling, degraded warnings. |
| C12 | Operator Auth and Session Boundary | 5 | planned | Cross-cutting | LOW | Present and verify operator identity, session state, and authorization in the control surface; audit auth state flow across surfaces. |
| C13 | SSE/Task-Event Reliability and Gap Detection | 5 | planned | Cross-cutting | MED | Audit and harden the SSE event stream for gap detection, replay validation, and silent event loss prevention. |
| C14 | Frontend State Management Audit | 5 | planned | Cross-cutting | LOW | Audit frontend state flows across React state, session state, provider state, inference request state, and runtime route capabilities to prevent state-management conflicts. |

## Dependency Summary

```
C00 ──┬── C11 ──┬── C01 ──┬── C03 ──┬── C04
      │         │         │         ├── C09
      │         │         │         └── C10
      │         │         ├── C05
      │         │         └── C06
      │         └── C02 ──┘
      │
      └── (C12, C13, C14 are cross-cutting, Wave 5)
```

C07 and C08 are partially independent and can be parallelized where backend config surfaces are confirmed.

## Risk Classification Definitions

- **LOW**: Docs-only or UI-only; no backend route, schema, or provider changes.
- **MED**: Involves backend route work, UI changes, or cross-surface integration.
- **HIGH**: Involves new backend routes, provider behavior, queue semantics, or Guardian authority boundaries.
