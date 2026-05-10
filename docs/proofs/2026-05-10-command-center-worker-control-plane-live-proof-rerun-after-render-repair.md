# Command Center Worker Control Plane Live Proof Rerun After Render Repair (2026-05-10)

## Title
Phase 8 rerun live proof for the Command Center worker-control seam after frontend render repair commit `70addf6c1e74a93802067321df57caaf4fec5f10`.

## Scope
Re-validate supported-path live behavior on local Docker Compose runtime:
- backend work-order API (`create`, `list`, `detail`, `cancel`)
- backend recommendation-only orchestrator API (`GET /api/coding/orchestrator/next`)
- Command Center worker-control panel render in live browser shell
- explicit non-dispatch boundary

Out of scope (must remain false):
- worker dispatch
- lease allocation
- Git branch/worktree allocation
- commit/merge/push automation
- live MiniMax/Codex automated execution

## Relation to previous incomplete proof
- Previous artifact: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof.md`
- Previous result: backend seam passed, UI seam incomplete
- This rerun verifies whether the render repair unblocked Phase 8 live UI proof

## Runtime environment
- Local runtime path: Docker Compose
- Backend base: `http://localhost:8888`
- Frontend base: `http://localhost:5173`
- Auth: `X-API-Key` from `scripts/dev/dev-key.sh` (value redacted)

## Branch and commit
- Branch: `codex/map-symphony-spec-to-worker`
- Commit: `ec29cf2fc9e8d87bf001e34bf183065dd23e62e4`
- Working tree before proof edits: clean (`git status --short` empty)
- Repair ancestry check: `git merge-base --is-ancestor 70addf6c1e74a93802067321df57caaf4fec5f10 HEAD` returned success (`repair_commit_present`)

## Exact commands run
```bash
git branch --show-current
git rev-parse HEAD
git status --short
git merge-base --is-ancestor 70addf6c1e74a93802067321df57caaf4fec5f10 HEAD && echo repair_commit_present

docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend frontend worker-chat worker-coding
docker compose ps

BASE=http://localhost:8888
KEY="$(bash scripts/dev/dev-key.sh)"
curl -fsS -H "X-API-Key: $KEY" "$BASE/health"
curl -fsS -H "X-API-Key: $KEY" "$BASE/health/chat"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/coding/work-orders"

# Sentinel work orders for rerun evidence
/bin/zsh -lc 'BASE=http://localhost:8888; KEY="$(bash scripts/dev/dev-key.sh)"; TS="$(date -u +%Y%m%dT%H%M%SZ)"; curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" "$BASE/api/coding/work-orders" -d "{\"campaign_id\":\"campaign-phase-8-rerun\",\"title\":\"phase-8-worker-control-plane-rerun-after-render-repair-2026-05-10-ready-${TS}\",\"objective\":\"Live proof rerun ready work order\",\"scope\":\"proof\",\"priority\":8,\"validation_command\":\"echo phase-8-rerun-proof\",\"adapter_kind\":\"mock\",\"max_validation_attempts\":1,\"require_worktree_lease\":false,\"commit_after_validation\":false,\"require_human_review_before_merge\":true,\"file_scope\":[\"frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx\"]}"'
/bin/zsh -lc 'BASE=http://localhost:8888; KEY="$(bash scripts/dev/dev-key.sh)"; TS="$(date -u +%Y%m%dT%H%M%SZ)"; curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" "$BASE/api/coding/work-orders" -d "{\"campaign_id\":\"campaign-phase-8-rerun\",\"title\":\"phase-8-worker-control-plane-rerun-after-render-repair-2026-05-10-draft-${TS}\",\"objective\":\"Live proof rerun draft work order\",\"scope\":\"proof\",\"status\":\"draft\",\"priority\":1,\"validation_command\":\"echo phase-8-rerun-proof\",\"adapter_kind\":\"mock\",\"max_validation_attempts\":1,\"require_worktree_lease\":false,\"commit_after_validation\":false,\"require_human_review_before_merge\":true,\"file_scope\":[\"docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md\"]}"'
curl -fsS -H "X-API-Key: $KEY" \
  "$BASE/api/coding/work-orders?campaign_id=campaign-phase-8-rerun"
curl -fsS -H "X-API-Key: $KEY" \
  "$BASE/api/coding/work-orders/wo_961b69f08eee450e"
curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  "$BASE/api/coding/work-orders/wo_961b69f08eee450e/cancel" -d '{"reason":"phase-8-rerun-cancel"}'
/bin/zsh -lc 'BASE=http://localhost:8888; KEY="$(bash scripts/dev/dev-key.sh)"; TS="$(date -u +%Y%m%dT%H%M%SZ)"; curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" "$BASE/api/coding/work-orders" -d "{\"campaign_id\":\"campaign-phase-8-rerun\",\"title\":\"phase-8-worker-control-plane-rerun-after-render-repair-2026-05-10-ready-orchestrator-${TS}\",\"objective\":\"Live proof rerun orchestrator recommendation target\",\"scope\":\"proof\",\"priority\":9,\"validation_command\":\"echo phase-8-rerun-proof\",\"adapter_kind\":\"mock\",\"max_validation_attempts\":1,\"require_worktree_lease\":false,\"commit_after_validation\":false,\"require_human_review_before_merge\":true,\"file_scope\":[\"frontend/src/features/commandCenter/hooks/useOrchestratorRecommendations.ts\"]}"'
curl -fsS -H "X-API-Key: $KEY" \
  "$BASE/api/coding/orchestrator/next?campaign_id=campaign-phase-8-rerun&limit=5"
curl -fsS -H "X-API-Key: $KEY" \
  "$BASE/api/coding/work-orders?campaign_id=campaign-phase-8-rerun"

# No-dispatch boundary checks
docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
docker compose exec db psql -U codexify -d Codexify -Atc "SELECT count(*) FROM coding_worktree_leases;"
docker compose logs --since 30m backend | rg -n "coding/work-orders|coding/orchestrator/next|coding/orchestrator/dispatch|agents/coding/execute|/api/coding/runs|worktree-leases"
docker compose logs --since 30m backend | rg -n "agents/coding/execute|orchestrator/dispatch|/api/coding/runs|/api/coding/work-orders/.*/runs"

# Live browser checks via Playwright MCP
# - navigate: http://localhost:5173/command-center
# - immediate DOM evaluate for panel test IDs
# - wait 12 seconds and re-evaluate
# - inspect console for runtime/hostname errors
nl -ba .playwright-mcp/console-2026-05-10T17-29-23-837Z.log | sed -n '1,120p'
```

## Backend health evidence
- `/health`: `200`, payload includes `status: "ok"` and `service: "core"`.
- `/health/chat`: `200`, `ok=true`, queue depth `0`, worker heartbeat fresh.
- `docker compose ps`: backend service healthy, frontend/worker services running.

## Work-order API evidence
- Fresh sentinel created:
  - `wo_961b69f08eee450e` (`ready` then `cancelled`)
  - `wo_0a2017116b3a4746` (`draft`)
  - `wo_97487fd1208b4ae1` (`ready` for orchestrator recommendation)
- `GET /api/coding/work-orders?campaign_id=campaign-phase-8-rerun` returns all three.
- `GET /api/coding/work-orders/{id}` returns the created row.
- `POST /api/coding/work-orders/{id}/cancel` transitions to `cancelled`.

## Orchestrator recommendation evidence
- `GET /api/coding/orchestrator/next?campaign_id=campaign-phase-8-rerun&limit=5` returned `200`.
- Recommendation returned:
  - `work_order_id=wo_97487fd1208b4ae1`
  - `rank=1`
  - `reason_codes=["READY_FOR_DISPATCH","HUMAN_REVIEW_REQUIRED"]`
- Skipped reasons returned:
  - `STATUS_NOT_READY` for `draft` and `cancelled` work orders
- Post-read list check confirmed no status mutation from orchestrator read path.

## Command Center UI evidence
Live route: `http://localhost:5173/command-center`

Initial check (immediately after load):
- `data-testid="coding-work-orders-panel"`: present
- `data-testid="coding-work-order-create-form"`: present
- `data-testid="coding-orchestrator-recommendations"`: present
- `data-testid="coding-orchestrator-skipped"`: present
- Non-dispatch copy visible:
  - dispatch, lease allocation, merge automation, and worker launch are not enabled
- No dispatch button found

Stability check (after 12 seconds):
- Command Center crashes and DOM collapses:
  - `panelAfterWait=false`
  - `headingsAfterWait=[]`
  - `bodyLength=0`
- Console error:
  - `TypeError: Cannot read properties of undefined (reading 'length')`
  - source: `features/commandCenter/commandCenterObservability.ts` via `TraceWorkbench.tsx`
- Prior blocker checks:
  - no `formatRetrievalPostureHistoryTimestamp is not defined` error observed in this rerun
  - no `backend:8888` browser hostname resolution errors observed in this rerun

## No-dispatch boundary evidence
- Coding queue depth: `0` before/after checks (`LLEN codexify:queue:coding-execution`).
- Lease rows: `0` (`coding_worktree_leases` count remained zero).
- Backend log scan shows only:
  - `POST/GET /api/coding/work-orders...`
  - `GET /api/coding/orchestrator/next...`
- Backend log scan shows no matches for:
  - `/api/agents/coding/execute`
  - `/api/coding/orchestrator/dispatch`
  - `/api/coding/work-orders/{id}/runs`
  - `/api/coding/runs/{id}/receipt`
- No application-path Git branch/worktree/commit/merge/push behavior observed.
- No commit hash produced by this proof flow.

## Result: INCOMPLETE
Backend seam proof passed again, but the Command Center UI seam is still not live-proofed end-to-end because the route crashes after initial render.

Phase 8 remains incomplete.

## Required boundary wording
- This proves Command Center operator visibility and work-order create/list/detail/cancel plus recommendation-only orchestration on the supported local path after the render repair, but not as a stable sustained UI surface.
- This does not prove worker dispatch from UI.
- This does not prove lease allocation.
- This does not prove live MiniMax/Codex automated execution.
- This does not prove merge automation.

## Known limitations
- Browser proof used manual Playwright MCP checks (not committed e2e harness).
- Stability failure is caused by existing TraceWorkbench runtime behavior outside this proof-only task scope.

## Follow-up needed
1. Repair the `TraceWorkbench` runtime crash path (`undefined.length` in `commandCenterObservability.ts`) so the Command Center shell remains stable.
2. Re-run Phase 8 proof after that repair.
3. Do not mark Phase 8 complete until the rerun shows stable panel presence plus no-dispatch boundary evidence.
