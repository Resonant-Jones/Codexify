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
- Proof expectation: failing validation cannot produce commit hash; passing validation can.

### Phase 5: task-board API
- Scope: work-order CRUD/read surfaces with lifecycle visibility.
- Proof expectation: API contract tests for acceptance semantics, state visibility, and dependency filtering.

### Phase 6: orchestrator next-task selector
- Scope: deterministic recommendation logic with dependency and conflict awareness.
- Proof expectation: policy tests showing deterministic decision reasons and safe blocking on ambiguity.

### Phase 7: inspection/UI surface
- Scope: operator-facing run ledger and receipt inspection surfaces.
- Proof expectation: UI/backend contract tests proving visibility for run, receipt, lease, and gate states.

### Phase 8: live MiniMax/Codex proof
- Scope: end-to-end live proof on supported path for run lifecycle with receipts.
- Proof expectation: durable proof artifact with branch/worktree/commands/validation/cleanup evidence and explicit limitations.

## Cross-phase rules
1. Each phase must remain atomic and independently validated.
2. Each phase must preserve "acceptance is not completion" semantics.
3. Each phase must not widen release claims without fresh live evidence.
4. Each phase must preserve Guardian ownership of policy, lineage, and receipts.
