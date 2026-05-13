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

## Usability hardening follow-through
- Command Center worker-control layout was hardened for operator use without widening authority:
  - page-level vertical scrolling is explicit and resilient
  - Worker Control remains near the top
  - health detail cards are collapsible by default
  - observability panes remain available but no longer bury work-order actions
- Non-dispatch boundary remains unchanged: no dispatch button, no worker launch, no lease allocation, no merge automation.

## Shell/lens hardening follow-through
- Command Center was refactored from a one-page diagnostics-first vertical dashboard into a shell-with-lenses layout:
  - One large rounded parent workspace card contains all content
  - Gesture-based utility rail (VS Code activity bar style) provides lens navigation between Agent Command, Observability, Runtime Health, Event Console, Deep Settings, and Extensions
  - Agent Command is the default active lens containing the worker-control panel
  - Observability, Runtime Health, and Event Console are reachable as dedicated lenses
  - Deep Settings and Extensions display placeholder copy without implementing configuration or plugin runtime
  - Bottom slide-up drawer scaffold provides Terminal, Logs, Receipts, and Problems tabs (Terminal is non-executable)
  - Rail supports left/right placement and pin/unpin with localStorage persistence
- All existing test IDs (coding-work-orders-panel, coding-work-order-create-form, coding-work-order-row, coding-orchestrator-recommendations, coding-orchestrator-skipped) preserved
- No dispatch, no lease allocation, no terminal execution, no plugin runtime, no merge automation, and no live MiniMax/Codex execution are implemented

## Shell ergonomics repair follow-through (2026-05-11)
- Rail side toggle repaired: the parent shell now reads localStorage for rail side preference and applies `flex-row-reverse` to the shell layout, so the rail moves between left and right cleanly without the visible jiggle caused by the rail-only internal flex reversal.
- Lens scrolling repaired: the outer page container changed from `min-h-screen overflow-y-auto` (page-level scroll) to `h-screen overflow-hidden` with a proper flex containment chain (`flex-1 min-h-0 overflow-y-auto` on the lens zone), ensuring each lens scrolls internally instead of the page.
- Workspace card hierarchy strengthened with tokenized surface, border, radius, and elevation.
- Edge button border-radius corrected for both sides.
- Visual polish applied to Agent Command header card, stat summary cards, and bottom drawer tabs.
- Frontend tests prove rail side switching, side preference persistence, lens scroll containment, and no-dispatch boundary preservation.
- RagTracePanel.test.tsx has 3 pre-existing assertion failures unrelated to this repair (loading state, no-trace state, mismatch state — text content search against render output).
