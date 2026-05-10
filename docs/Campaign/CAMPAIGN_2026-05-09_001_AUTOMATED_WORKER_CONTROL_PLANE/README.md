# Automated Worker Control Plane Campaign

## Goal
Define a repo-native campaign/spec directory for a future Guardian-mediated automated development control plane where workers execute bounded coding work under explicit policy, lineage, and proof requirements.

This campaign is specification-only. It does not implement runtime behavior, persistence schema changes, worker execution changes, routes, UI, or automation.

## Framing Language
Use "air-traffic-control" and "worker docking" as explanatory metaphors only. They are not runtime terms, API names, queue names, or storage model names.

## ADR Impact Classification
- Classification: No ADR impact (for this task)
- Governing ADRs and contracts:
  - [ADR-020](../../architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md)
  - [ADR-022](../../architecture/adr/022-guardian-intent-spine-and-cross-surface-control-plane.md)
  - [Runtime Protocol Token Contract](../../architecture/runtime-protocol-token-contract.md)
- Reason: This campaign introduces planning/spec artifacts only and does not change runtime semantics, queue behavior, worker behavior, schema, or release posture.

## Campaign Phases
1. Phase 0: campaign/spec directory
2. Phase 1: worktree lease contract
3. Phase 2: worktree lease persistence/store
4. Phase 3: coding worker uses leased worktree
5. Phase 4: commit-after-green gate
6. Phase 5: task-board API
7. Phase 6: orchestrator next-task selector
8. Phase 7: inspection/UI surface
9. Phase 8: live MiniMax/Codex proof

## Non-Goals
- No Python or TypeScript implementation.
- No database migrations.
- No API route implementation.
- No worker runtime behavior changes.
- No queue behavior changes.
- No UI implementation.
- No worktree creation automation.
- No commit or merge automation.
- No release-promise expansion.

## Documents in This Campaign
### Core specs
- [00-current-shape.md](./00-current-shape.md)
- [01-domain-model.md](./01-domain-model.md)
- [02-task-state-machine.md](./02-task-state-machine.md)
- [03-worktree-lease-contract.md](./03-worktree-lease-contract.md)
- [04-worker-receipt-contract.md](./04-worker-receipt-contract.md)
- [05-orchestrator-policy.md](./05-orchestrator-policy.md)
- [06-api-surface-sketch.md](./06-api-surface-sketch.md)
- [07-rollout-plan.md](./07-rollout-plan.md)

### Task stubs
- [TASK-001-worktree-lease-contract.md](./tasks/TASK-001-worktree-lease-contract.md)
- [TASK-002-worktree-lease-store.md](./tasks/TASK-002-worktree-lease-store.md)
- [TASK-003-coding-worker-uses-leased-worktree.md](./tasks/TASK-003-coding-worker-uses-leased-worktree.md)
- [TASK-004-commit-after-green-gate.md](./tasks/TASK-004-commit-after-green-gate.md)
- [TASK-005-task-board-api.md](./tasks/TASK-005-task-board-api.md)
- [TASK-006-orchestrator-next-task-selector.md](./tasks/TASK-006-orchestrator-next-task-selector.md)
- [TASK-007-run-ledger-inspection-surface.md](./tasks/TASK-007-run-ledger-inspection-surface.md)

### Proof and decisions
- [proof-template.md](./proofs/proof-template.md)
- [DECISION-001-branch-and-worktree-lifecycle.md](./decisions/DECISION-001-branch-and-worktree-lifecycle.md)

### Related references
- [Symphony Service Specification seed](../../specs/Symphony-Spec-Seed.md) is imported as a reference architecture seed for comparison only.
- Symphony is not normative for Codexify architecture or campaign truth.
- [SYMPHONY_SPEC_ADAPTATION_MATRIX.md](./analysis/SYMPHONY_SPEC_ADAPTATION_MATRIX.md) is the canonical interpretation artifact for this campaign.

## Current-Truth Constraint
This campaign must remain subordinate to [00-current-state.md](../../architecture/00-current-state.md). Route/task acceptance is not completion, and future implementation must preserve Guardian ownership of policy, transcript, lineage, worker events, and result receipts.
