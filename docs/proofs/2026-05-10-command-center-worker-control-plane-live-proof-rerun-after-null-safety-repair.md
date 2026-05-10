# Command Center Worker Control Plane Live Proof Rerun After Null-Safety Repair (2026-05-10)

## Title
Phase 8 live proof rerun for the Command Center worker-control seam after null-safety repair commit `b6aad64732bce1b8bd33cc6e5f637264c2f06a30`.

## Scope
Re-validate supported-path live behavior on local Docker Compose runtime:
- backend work-order API (`create`, `list`, `detail`, `cancel`)
- backend recommendation-only orchestrator API (`GET /api/coding/orchestrator/next`)
- Command Center worker-control panel stability after observability loads
- explicit non-dispatch boundary

Out of scope (must remain false):
- worker dispatch
- lease allocation
- Git branch/worktree allocation
- commit/merge/push automation
- live MiniMax/Codex automated execution

## Relation to previous incomplete proofs
- Initial proof artifact: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof.md` (incomplete).
- Render-repair rerun artifact: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-render-repair.md` (incomplete).
- This rerun verifies whether the null-safety repair removed the post-render TraceWorkbench crash and preserved the non-dispatch boundary.

## Runtime environment
- Local runtime path: Docker Compose
- Backend base: `http://localhost:8888`
- Frontend base: `http://localhost:5173`
- Auth: `X-API-Key` from `scripts/dev/dev-key.sh` (value redacted)

## Branch and commit
- Branch: `codex/map-symphony-spec-to-worker`
- Commit: `b6aad64732bce1b8bd33cc6e5f637264c2f06a30`
- Working tree before proof edits: contained only untracked Playwright snapshots under `.playwright-mcp/`
- Repair ancestry check: `git merge-base --is-ancestor b6aad64732bce1b8bd33cc6e5f637264c2f06a30 HEAD` returned success (`null_safety_repair_commit_present`)

## Exact commands run
```bash
git branch --show-current
git rev-parse HEAD
git status --short
git merge-base --is-ancestor b6aad64732bce1b8bd33cc6e5f637264c2f06a30 HEAD && echo null_safety_repair_commit_present

docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d backend frontend worker-chat worker-coding
docker compose ps

BASE=http://localhost:8888
KEY="$(bash scripts/dev/dev-key.sh)"
curl -fsS -H "X-API-Key: $KEY" "$BASE/health"
curl -fsS -H "X-API-Key: $KEY" "$BASE/health/chat"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/coding/work-orders"

# Pre-proof no-dispatch baseline
docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
docker compose exec db psql -U codexify -d Codexify -Atc "SELECT count(*) FROM coding_worktree_leases;"

# Sentinel create/list/detail/cancel (campaign-phase-8-null-safety-rerun)
/bin/zsh -lc 'BASE=http://localhost:8888; KEY="$(bash scripts/dev/dev-key.sh)"; TS="$(date -u +%Y%m%dT%H%M%SZ)"; curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" "$BASE/api/coding/work-orders" -d "{\"campaign_id\":\"campaign-phase-8-null-safety-rerun\",\"title\":\"phase-8-worker-control-plane-rerun-after-null-safety-repair-2026-05-10-${TS}\",\"objective\":\"Live proof rerun after null-safety repair\",\"scope\":\"proof\",\"priority\":8,\"validation_command\":\"echo phase-8-null-safety-rerun-proof\",\"adapter_kind\":\"mock\",\"max_validation_attempts\":1,\"require_worktree_lease\":false,\"commit_after_validation\":false,\"require_human_review_before_merge\":true,\"file_scope\":[\"frontend/src/features/commandCenter/components/CodingWorkOrdersPanel.tsx\"]}"'
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/coding/work-orders?campaign_id=campaign-phase-8-null-safety-rerun"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/coding/work-orders/wo_39b4334432fd430f"
curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" "$BASE/api/coding/work-orders/wo_39b4334432fd430f/cancel" -d '{"reason":"phase-8-null-safety-rerun-cancel"}'

# Recommendation/skip proof data
/bin/zsh -lc 'BASE=http://localhost:8888; KEY="$(bash scripts/dev/dev-key.sh)"; TS="$(date -u +%Y%m%dT%H%M%SZ)"; curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" "$BASE/api/coding/work-orders" -d "{\"campaign_id\":\"campaign-phase-8-null-safety-rerun\",\"title\":\"phase-8-worker-control-plane-rerun-after-null-safety-repair-ready-orchestrator-${TS}\",\"objective\":\"Rerun orchestrator recommendation target\",\"scope\":\"proof\",\"priority\":9,\"validation_command\":\"echo phase-8-null-safety-rerun-proof\",\"adapter_kind\":\"mock\",\"max_validation_attempts\":1,\"require_worktree_lease\":false,\"commit_after_validation\":false,\"require_human_review_before_merge\":true,\"file_scope\":[\"frontend/src/features/commandCenter/hooks/useOrchestratorRecommendations.ts\"]}"'
/bin/zsh -lc 'BASE=http://localhost:8888; KEY="$(bash scripts/dev/dev-key.sh)"; TS2="$(date -u +%Y%m%dT%H%M%SZ)"; curl -fsS -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" "$BASE/api/coding/work-orders" -d "{\"campaign_id\":\"campaign-phase-8-null-safety-rerun\",\"title\":\"phase-8-worker-control-plane-rerun-after-null-safety-repair-draft-${TS2}\",\"objective\":\"Rerun orchestrator skip target\",\"scope\":\"proof\",\"status\":\"draft\",\"priority\":1,\"validation_command\":\"echo phase-8-null-safety-rerun-proof\",\"adapter_kind\":\"mock\",\"max_validation_attempts\":1,\"require_worktree_lease\":false,\"commit_after_validation\":false,\"require_human_review_before_merge\":true,\"file_scope\":[\"docs/Campaign/CAMPAIGN_2026-05-09_001_AUTOMATED_WORKER_CONTROL_PLANE/07-rollout-plan.md\"]}"'
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/coding/work-orders?campaign_id=campaign-phase-8-null-safety-rerun"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/coding/orchestrator/next?campaign_id=campaign-phase-8-null-safety-rerun&limit=5"
curl -fsS -H "X-API-Key: $KEY" "$BASE/api/coding/work-orders?campaign_id=campaign-phase-8-null-safety-rerun"

# Backend no-dispatch verification
docker compose logs --since 20m backend | rg -n "coding/work-orders|coding/orchestrator/next|coding/orchestrator/dispatch|agents/coding/execute|/api/coding/runs|/api/coding/work-orders/.*/runs"
/bin/zsh -lc 'if docker compose logs --since 20m backend | rg -n "agents/coding/execute|coding/orchestrator/dispatch|/api/coding/runs|/api/coding/work-orders/.*/runs"; then echo unexpected_dispatch_routes_present; else echo no_dispatch_or_run_routes_observed; fi'
docker compose exec redis redis-cli LLEN codexify:queue:coding-execution
docker compose exec db psql -U codexify -d Codexify -Atc "SELECT count(*) FROM coding_worktree_leases;"

# Live browser checks via Playwright MCP
# - navigate: http://localhost:5173/command-center
# - immediate test-id and copy checks
# - wait 14 seconds and re-check
# - console inspection
cat .playwright-mcp/console-2026-05-10T20-51-28-687Z.log
```

## Backend health evidence
- `/health`: `200`, payload includes `status: "ok"` and `service: "core"`.
- `/health/chat`: `200`, `ok=true`, queue depth `0`, worker heartbeat fresh.
- `docker compose ps`: backend healthy; frontend/worker services running.

## Work-order API evidence
- Fresh sentinel created with required payload traits:
  - title prefix `phase-8-worker-control-plane-rerun-after-null-safety-repair-2026-05-10-...`
  - `validation_command="echo phase-8-null-safety-rerun-proof"`
  - `require_worktree_lease=false`
  - `commit_after_validation=false`
  - `require_human_review_before_merge=true`
- Sentinel IDs:
  - `wo_39b4334432fd430f` (ready, then cancelled for cancel proof)
  - `wo_cb06b0ae372941f7` (ready recommendation target)
  - `wo_4265da668d2b4e8b` (draft skip target)
- `GET list` included created records.
- `GET detail` returned created ready record.
- `POST cancel` transitioned `wo_39b4334432fd430f` to `cancelled`.

## Orchestrator recommendation evidence
- `GET /api/coding/orchestrator/next?campaign_id=campaign-phase-8-null-safety-rerun&limit=5` returned `200`.
- Recommendation returned:
  - `work_order_id=wo_cb06b0ae372941f7`
  - `rank=1`
  - `reason_codes=["READY_FOR_DISPATCH","HUMAN_REVIEW_REQUIRED"]`
- Skipped reasons returned:
  - `STATUS_NOT_READY` for `cancelled` and `draft` work orders.
- Pre/post list snapshots showed no status mutation from orchestrator reads.

## Command Center UI evidence
Live route: `http://localhost:5173/command-center`

Immediate checks:
- `data-testid="coding-work-orders-panel"` present
- `data-testid="coding-work-order-create-form"` present
- `data-testid="coding-orchestrator-recommendations"` present
- `data-testid="coding-orchestrator-skipped"` present
- explicit non-dispatch copy visible
- no dispatch button present

Stability checks:
- waited 14 seconds to allow observability loads
- panel and child test IDs remained present after wait
- page body remained populated (`bodyLength=30776`)

Console checks:
- no `formatRetrievalPostureHistoryTimestamp is not defined`
- no `Cannot read properties of undefined (reading 'length')`
- no `backend:8888` resolution errors
- fresh console log (`.playwright-mcp/console-2026-05-10T20-51-28-687Z.log`) contained info entries only

## No-dispatch boundary evidence
- Queue depth before proof: `0`
- Queue depth after proof: `0`
- Lease row count before proof: `0`
- Lease row count after proof: `0`
- Backend log scan showed only work-order and orchestrator-next reads/writes.
- Explicit dispatch/run scan returned `no_dispatch_or_run_routes_observed`.
- No application-path branch/worktree/commit/merge/push behavior observed.
- No commit hash produced by this proof flow.

## Result: PASS
This proves Command Center operator visibility and work-order create/list/detail/cancel plus recommendation-only orchestration on the supported local path after the null-safety repair.

This does not prove worker dispatch from UI.
This does not prove lease allocation.
This does not prove live MiniMax/Codex automated execution.
This does not prove merge automation.

## Known limitations
- Browser verification used manual Playwright MCP checks (not committed e2e harness).
- This proof validates operator seam stability and non-dispatch behavior only.

## Follow-up needed
1. Keep dispatch endpoint (`POST /api/coding/orchestrator/dispatch`) unimplemented until explicit future phase.
2. Run a separate proof task if/when dispatch, lease allocation, or live automated coding execution is introduced.
