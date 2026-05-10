# Command Center Worker Control Plane Live Proof (2026-05-10)

## Title
Phase 8 live proof for the Command Center worker-control seam on the supported local Docker Compose runtime.

## Scope
Validate the operator-visible seam only:
- Command Center worker-control panel visibility.
- Live backend work-order API: create, list, detail, cancel.
- Live backend orchestrator recommendation API: next recommendations + skip reasons.
- Explicit non-dispatch boundary.

Out of scope (must remain false in this proof):
- Worker dispatch.
- Lease allocation.
- Git branch/worktree allocation.
- Commit/merge/push automation.
- Live MiniMax/Codex execution.

## Runtime environment
- Local runtime path: Docker Compose.
- Backend: `http://localhost:8888`.
- Frontend: `http://localhost:5173`.
- Auth mode: `X-API-Key` (key sourced from `scripts/dev/dev-key.sh`, value not logged).

## Branch and commit
- Branch: `main`
- Commit: `b983c6144cda9b0a8fc7e1feae9989f0ec8269f4`
- Working tree before proof edits: intentionally scoped with unrelated untracked directories present.

## Exact commands run
```bash
git branch --show-current
git rev-parse HEAD
git status --short

docker compose ps
docker compose up -d db redis neo4j
docker compose run --rm migrator
docker compose up -d --build backend frontend worker-chat worker-coding
docker compose ps

# Health snapshots
KEY="$(bash scripts/dev/dev-key.sh)"
curl -fsS -H "X-API-Key: $KEY" http://localhost:8888/health > /tmp/phase8_health.json
curl -fsS -H "X-API-Key: $KEY" http://localhost:8888/health/chat > /tmp/phase8_health_chat.json

# Live API proof runner (creates /tmp/phase8_live_proof_summary.json)
python - <<'PY'
# bounded runner used in this session; summary captured in /tmp/phase8_live_proof_summary.json
PY

# UI live check (Playwright MCP browser)
# - navigate: http://localhost:5173/command-center
# - evaluate testid presence + no-dispatch button presence
# - inspect .playwright-mcp/console-2026-05-10T15-34-10-155Z.log
# - inspect .playwright-mcp/page-2026-05-10T15-34-10-772Z.yml
```

## Backend health evidence
- `/health`: HTTP 200, `{"status":"ok","service":"core"...}`.
- `/health/chat`: HTTP 200, `ok=true`, queue depth `0`, worker heartbeat fresh.
- `docker compose ps`: backend/frontend/db/redis/neo4j/worker services healthy or running.

## Work-order API evidence
Source: `/tmp/phase8_live_proof_summary.json`
- Auth enforced: invalid API key returned `401`.
- `POST /api/coding/work-orders` (ready sentinel): `200`, `work_order_id=wo_0953bcbc771d4f04`.
- `POST /api/coding/work-orders` (draft sentinel): `200`, `work_order_id=wo_d8230469b43547f6`.
- `GET /api/coding/work-orders?campaign_id=campaign-phase-8-proof`: `200`, includes both IDs.
- `GET /api/coding/work-orders/{id}` (ready): `200`, status `ready`.
- `POST /api/coding/work-orders/{id}/cancel`: `200`, status `cancelled`.

## Orchestrator recommendation evidence
Source: `/tmp/phase8_live_proof_summary.json`
- `GET /api/coding/orchestrator/next?campaign_id=campaign-phase-8-proof&limit=5`: `200`.
- Recommendations count: `1`.
- Skipped count: `1`.
- First recommendation:
  - `work_order_id=wo_0953bcbc771d4f04`
  - `rank=1`
  - `reason_codes=["READY_FOR_DISPATCH", "HUMAN_REVIEW_REQUIRED"]`
- Skip reason codes include: `STATUS_NOT_READY`.
- Non-mutation check: ready work order remained `ready` before and after orchestrator read.

## Command Center UI evidence
Status: **INCOMPLETE** (UI live seam not proven on this run).

Observed on `http://localhost:5173/command-center`:
- Playwright DOM evaluation returned:
  - `coding-work-orders-panel`: `0`
  - `coding-work-order-create-form`: `0`
  - `coding-orchestrator-recommendations`: `0`
  - `coding-orchestrator-skipped`: `0`
- Page snapshot (`.playwright-mcp/page-2026-05-10T15-34-10-772Z.yml`) showed fallback state:
  - `Waiting for the backend`
- Console evidence (`.playwright-mcp/console-2026-05-10T15-34-10-155Z.log`) captured:
  - repeated `ERR_NAME_NOT_RESOLVED` for `http://backend:8888/health*`
  - runtime error: `ReferenceError: formatRetrievalPostureHistoryTimestamp is not defined`

Exact failing surface:
- Command Center route did not render the Phase 7 worker-control panel test IDs in the supported local browser path during this proof run.

## No-dispatch boundary evidence
Source: `/tmp/phase8_live_proof_summary.json`
- Lease count before proof: `0`
- Lease count after proof: `0`
- Queue depth before proof: `0`
- Queue depth after proof: `0`
- No dispatch endpoint was called in the proof command set.
- No Git branch/worktree/commit/merge/push commands were executed by application behavior in this proof.

## Result: INCOMPLETE
Backend API seam proof passed, but Command Center UI seam was not live-proven due frontend/runtime rendering failures on this run.

This proof does **not** mark Phase 8 complete.

## Required boundary wording
- This does not prove worker dispatch from UI.
- This does not prove lease allocation.
- This does not prove live MiniMax/Codex automated execution.
- This does not prove merge automation.

## Known limitations
- Browser proof used manual Playwright inspection (not a committed end-to-end harness).
- Runtime contained pre-existing frontend errors that blocked panel rendering.

## Follow-up needed
1. Fix Command Center runtime blocker(s) on supported Compose path:
   - backend hostname resolution path from browser context (`backend:8888` references).
   - `TraceWorkbench.tsx` runtime error (`formatRetrievalPostureHistoryTimestamp` undefined).
2. Re-run this Phase 8 live proof after fixes.
3. Only then update campaign/architecture status to mark Phase 8 passed.
