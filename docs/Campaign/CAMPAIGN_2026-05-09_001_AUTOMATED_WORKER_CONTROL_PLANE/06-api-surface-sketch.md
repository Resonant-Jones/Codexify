# 06 API Surface Sketch (Proposed)

## Purpose
Sketch possible future backend routes for the worker control plane. These routes are proposed only and are not implemented.

## Route list (all proposed)

### `POST /api/coding/work-orders`
- Proposed purpose: create a `WorkOrder` with objective, scope, dependency metadata, and policy constraints.
- Proposed output: accepted work-order envelope and initial state.

### `GET /api/coding/work-orders`
- Proposed purpose: list work orders with state filters, campaign filters, and dependency/readiness metadata.
- Proposed output: paginated work-order summaries.

### `GET /api/coding/work-orders/{id}`
- Proposed purpose: fetch one work order with lifecycle history, dependencies, receipts, and active gates.
- Proposed output: detailed work-order record.

### `POST /api/coding/work-orders/{id}/runs`
- Proposed purpose: request or authorize run creation for a work order, including lease acquisition path.
- Proposed output: run identity, lease identity (if granted), and task-event stream reference.

### `POST /api/coding/work-orders/{id}/cancel`
- Proposed purpose: request cancellation for active/queued work order execution.
- Proposed output: cancellation acceptance and resulting lifecycle state.

### `GET /api/coding/runs/{id}/receipt`
- Proposed purpose: return the terminal structured `WorkerReceipt` plus bounded validation evidence.
- Proposed output: receipt payload.

### `GET /api/coding/orchestrator/next`
- Proposed purpose: recommendation-only endpoint for next safe task selection.
- Proposed output: ranked recommendation list + decision reasons.

### `POST /api/coding/orchestrator/dispatch`
- Proposed purpose: policy-authorized dispatch endpoint that turns a recommendation into execution.
- Proposed output: dispatch decision record, created run, and event references.

## Proposed guardrails
1. Route acceptance must not be interpreted as completion.
2. All responses should expose canonical state tokens and decision reasons.
3. Dispatch endpoints must preserve idempotency and lineage identity.
4. Receipt endpoints must return bounded normalized evidence only.

## Implementation status
No routes in this file are live runtime claims.
