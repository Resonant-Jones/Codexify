# 06 API Surface Sketch (Proposed)

## Purpose
Track the worker-control-plane backend route surface across rollout phases.

## Route list

### `POST /api/coding/work-orders`
- Proposed purpose: create a `WorkOrder` with objective, scope, dependency metadata, and policy constraints.
- Proposed output: accepted work-order envelope and initial state.
- Implementation status: implemented in Phase 5 as durable create-only work-order intake (no dispatch side effects).

### `GET /api/coding/work-orders`
- Proposed purpose: list work orders with state filters, campaign filters, and dependency/readiness metadata.
- Proposed output: paginated work-order summaries.
- Implementation status: implemented in Phase 5 with `status`, `campaign_id`, `limit`, `offset` filters.

### `GET /api/coding/work-orders/{id}`
- Proposed purpose: fetch one work order with lifecycle history, dependencies, receipts, and active gates.
- Proposed output: detailed work-order record.
- Implementation status: implemented in Phase 5 for durable work-order detail reads.

### `POST /api/coding/work-orders/{id}/runs`
- Proposed purpose: request or authorize run creation for a work order, including lease acquisition path.
- Proposed output: run identity, lease identity (if granted), and task-event stream reference.
- Implementation status: proposed only.

### `POST /api/coding/work-orders/{id}/cancel`
- Proposed purpose: request cancellation for active/queued work order execution.
- Proposed output: cancellation acceptance and resulting lifecycle state.
- Implementation status: implemented in Phase 5 as state transition only (no worker cancellation side effects).

### `GET /api/coding/runs/{id}/receipt`
- Proposed purpose: return the terminal structured `WorkerReceipt` plus bounded validation evidence.
- Proposed output: receipt payload.
- Implementation status: proposed only.

### `GET /api/coding/orchestrator/next`
- Proposed purpose: recommendation-only endpoint for next safe task selection.
- Proposed output: ranked recommendation list + decision reasons.
- Implementation status: implemented in Phase 6 as recommendation-only policy output (no dispatch side effects).

### `POST /api/coding/orchestrator/dispatch`
- Proposed purpose: policy-authorized dispatch endpoint that turns a recommendation into execution.
- Proposed output: dispatch decision record, created run, and event references.
- Implementation status: proposed only.

## Proposed guardrails
1. Route acceptance must not be interpreted as completion.
2. All responses should expose canonical state tokens and decision reasons.
3. Dispatch endpoints must preserve idempotency and lineage identity.
4. Receipt endpoints must return bounded normalized evidence only.

## Implementation status
- Implemented after Phase 5:
  - `POST /api/coding/work-orders`
  - `GET /api/coding/work-orders`
  - `GET /api/coding/work-orders/{id}`
  - `POST /api/coding/work-orders/{id}/cancel`
- Still proposed:
  - `POST /api/coding/work-orders/{id}/runs`
  - `GET /api/coding/runs/{id}/receipt`
  - `POST /api/coding/orchestrator/dispatch`

- Implemented after Phase 6:
  - `GET /api/coding/orchestrator/next`

- Implemented after Phase 7 (UI consumption):
  - Command Center consumes:
    - `POST /api/coding/work-orders`
    - `GET /api/coding/work-orders`
    - `GET /api/coding/work-orders/{id}`
    - `POST /api/coding/work-orders/{id}/cancel`
    - `GET /api/coding/orchestrator/next`
  - Live proof artifact: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof.md`.
  - Live proof rerun artifact after render repair: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-render-repair.md`.
  - Live proof rerun artifact after null-safety repair: `docs/proofs/2026-05-10-command-center-worker-control-plane-live-proof-rerun-after-null-safety-repair.md`.
  - Live backend route proof for these endpoints passed on Compose runtime.
  - Command Center browser rendering proof passed after null-safety repair: panel test IDs remained visible after an observability-load wait window, and prior `undefined.length` / `backend:8888` errors did not recur.
  - Dispatch endpoint remains proposed only.
  - Run/receipt endpoints remain proposed only.
