# 07 Rollout Plan (Proposed)

## Purpose
Define a phased implementation sequence for future work while preserving current-truth boundaries and evidence discipline.

## Phase plan and proof expectations

### Phase 0: campaign/spec directory
- Scope: create planning artifacts only (this campaign).
- Proof expectation: docs validation passes and campaign files are linked and reviewable.

### Phase 1: worktree lease contract
- Scope: introduce canonical lease types/tokens/contracts in code.
- Proof expectation: contract tests for lease state transitions and conflict rules.

### Phase 2: worktree lease persistence/store
- Scope: durable lease storage and lifecycle operations.
- Proof expectation: persistence tests for create/heartbeat/expire/recover/cleanup intent, including `guardian/tests/agents/test_worktree_lease_store.py` coverage for conflict protection and terminal reuse semantics.

### Phase 3: coding worker uses leased worktree
- Scope: worker run path must require and honor lease context.
- Proof expectation: worker tests prove lease-bound adapter/validation cwd (`guardian/tests/workers/test_coding_worker.py`) and lease-linked terminal/result metadata, plus route tests prove lease-field propagation (`guardian/tests/routes/test_agent_orchestration_events.py`).

### Phase 4: commit-after-green gate
- Scope: commit behavior only after passing validation in bounded policy path.
- Proof expectation: commit-gate tests (`guardian/tests/agents/test_commit_gate.py`) prove commit created/no-change/failure behavior, and worker tests (`guardian/tests/workers/test_coding_worker.py`) prove commit runs only on lease-bound passing-validation paths with bounded commit metadata.

### Phase 5: task-board API
- Scope: work-order CRUD/read surfaces with lifecycle visibility.
- Proof expectation: contract/store/route tests (`guardian/tests/agents/test_work_orders.py`, `guardian/tests/agents/test_work_order_store.py`, `guardian/tests/routes/test_coding_work_orders.py`) prove durable create/list/detail/cancel behavior, transition validation, and no-dispatch route semantics.

### Phase 6: orchestrator next-task selector
- Scope: deterministic recommendation logic with dependency and conflict awareness.
- Proof expectation: policy tests (`guardian/tests/agents/test_orchestrator_policy.py`) prove deterministic ranking and skip reasons, and route tests (`guardian/tests/routes/test_coding_work_orders.py`) prove `GET /api/coding/orchestrator/next` reads durable state without dispatch side effects.

### Phase 7: inspection/UI surface
- Scope: operator-facing run ledger and receipt inspection surfaces.
- Proof expectation: Command Center panel tests (`frontend/src/features/commandCenter/components/__tests__/CodingWorkOrdersPanel.test.tsx`) prove work-order list/create/cancel visibility plus recommendation-only rendering and explicit non-dispatch boundaries.
- Live proof status (2026-05-10): attempted through Compose-supported runtime in `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof.md`, but UI route proof was blocked by frontend runtime errors; backend API seam proof passed.

### Phase 8: live MiniMax/Codex proof
- Scope: end-to-end live proof on supported path for run lifecycle with receipts.
- Proof expectation: durable proof artifact with branch/worktree/commands/validation/cleanup evidence and explicit limitations.
- Status (2026-05-10): **INCOMPLETE** for Command Center worker-control seam live proof. Backend task-board/orchestrator API checks passed, but Command Center UI panel test IDs were not present during live runtime proof, so Phase 8 is not complete.

## Cross-phase rules
1. Each phase must remain atomic and independently validated.
2. Each phase must preserve "acceptance is not completion" semantics.
3. Each phase must not widen release claims without fresh live evidence.
4. Each phase must preserve Guardian ownership of policy, lineage, and receipts.
