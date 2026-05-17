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
- Usability hardening note (2026-05-10): Command Center layout is now scroll-safe with Worker Control promoted near the top, health details collapsed by default, and observability workbench controls kept explicit while preserving non-dispatch boundaries.
- UI shell hardening note (2026-05-11): Command Center refactored into a shell-with-lenses layout with gesture utility rail (Agent Command / Observability / Runtime Health / Event Console / Deep Settings / Extensions), bottom slide-up drawer scaffold (Terminal / Logs / Receipts / Problems), and left/right rail placement with localStorage persistence. Agent Command is the default lens. Terminal tab is non-executable. No dispatch, lease allocation, plugin runtime, or merge automation implemented.

### Phase 8: live MiniMax/Codex proof
- Scope: end-to-end live proof on supported path for run lifecycle with receipts.
- Proof expectation: durable proof artifact with branch/worktree/commands/validation/cleanup evidence and explicit limitations.
- Prior status (2026-05-10): initial run and render-repair rerun were incomplete due Command Center runtime instability (see `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof.md` and `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-render-repair.md`).
- Rerun status (2026-05-10, post-null-safety-repair): **PASSED** for the non-dispatch Command Center worker-control seam on supported Compose runtime. Backend work-order/orchestrator APIs passed, panel test IDs stayed present after observability load wait, and no-dispatch boundaries held. See `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-null-safety-repair.md`.
- Usability hardening note (2026-05-10): this phase remains non-dispatch; improvements were limited to operator layout/ergonomics (scrolling, hierarchy, and panel compactness) without adding dispatch authority.
- Supported coding-execution note (2026-05-13): the public coding route now accepts explicit adapter kinds (`codex`, `claudecode`, `pi_sdk`, `pi_codex_runner`) and the local Compose worker mounts `./codex_runner` at `/app/codex_runner` so the Pi runner artifact is present when that path is selected.
- Supported coding-execution proof note (2026-05-13): the live supported Compose worker path was rerun successfully on `adapter_kind="codex"` after the worker bootstrap was switched to Guardian DB state and the local compose default adapter command was pointed at a locally available tool-capable Ollama model. The live smoke produced one bounded source-thread `coding_result` message, a terminal run record, and an idempotent replay that did not duplicate delivery.

### Phase 9 (optional): external tracker/workflow adaptation
- Scope:
  - evaluate a repository-owned workflow policy file candidate,
  - issue-tracker ingestion into `WorkOrder` records,
  - reconciliation and explicit stop conditions for tracker-driven state drift,
  - bounded concurrency and retry backoff for dispatch-adjacent orchestration.
- Proof expectation: adaptation-specific policy/contract tests and bounded live proof artifacts that preserve current control-plane invariants.
- Constraint: this phase is optional and is **not required** for current Command Center proof or the initial manual worker-control loop.

## Cross-phase rules
1. Each phase must remain atomic and independently validated.
2. Each phase must preserve "acceptance is not completion" semantics.
3. Each phase must not widen release claims without fresh live evidence.
4. Each phase must preserve Guardian ownership of policy, lineage, and receipts.
