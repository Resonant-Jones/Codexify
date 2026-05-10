# TASK-007 Run Ledger Inspection Surface

## Objective
Implement Phase 7 by adding a Command Center worker-control panel that surfaces durable work-order state and recommendation-only orchestration output.

## Scope
- Add a Guardian-visible Command Center panel for:
  - listing work orders
  - creating work orders
  - cancelling work orders
  - viewing recommendation-only next-task results
- Keep explicit non-dispatch boundaries visible in the UI.
- Preserve operator-safe truth semantics: acceptance/state visibility does not imply execution.

## Files likely to edit
- `frontend/src/features/commandCenter/types.ts`
- `frontend/src/features/commandCenter/hooks/useCodingWorkOrders.ts`
- `frontend/src/features/commandCenter/hooks/useOrchestratorRecommendations.ts`
- `frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx`
- `frontend/src/features/commandCenter/components/__tests__/CodingWorkOrdersPanel.test.tsx`
- `frontend/src/features/commandCenter/CommandCenterPage.tsx`
- campaign docs for Phase 7 status updates

## Validation expectations
- Frontend panel tests prove:
  - render of work orders/recommendations/skipped reasons
  - create/cancel API actions
  - loading/error states
  - explicit non-dispatch boundary
- Existing backend route/policy tests remain green.
- Docs validation and diff hygiene checks pass.

## Validation commands
- `pnpm --dir frontend test -- CodingWorkOrdersPanel`
- `./.venv/bin/python -m pytest -v guardian/tests/routes/test_coding_work_orders.py`
- `./.venv/bin/python -m pytest -v guardian/tests/agents/test_orchestrator_policy.py`
- `./.venv/bin/python scripts/validate_docs.py`
- `git diff --check`

## Non-goals
- No worker dispatch from UI.
- No lease allocation.
- No run creation.
- No Git branch/worktree creation.
- No commit/merge/push behavior.
- No orchestrator dispatch endpoint.
- No live MiniMax/Codex proof.

## Dependencies
- TASK-005 task-board API.
- TASK-006 orchestrator selector.

## Completion criteria
- Command Center exposes durable work-order visibility and create/cancel control.
- Command Center exposes recommendation-only next-task output with explicit skip reasons.
- UI explicitly states dispatch/lease allocation/merge automation are not enabled.

## Proof follow-through (Phase 8)
- Live proof artifact: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof.md`.
- Live proof rerun artifact after render repair: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-render-repair.md`.
- Live proof rerun artifact after null-safety repair: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-null-safety-repair.md`.
- Backend API seam (create/list/detail/cancel + recommendation-only next-task) was proven live on Compose runtime.
- No-dispatch boundary remained explicit (no dispatch endpoint calls, no lease allocation evidence, no queue growth).
- UI route proof is now stable on rerun after null-safety repair: worker-control panel remains visible after observability load wait, while dispatch stays disabled and unimplemented.
