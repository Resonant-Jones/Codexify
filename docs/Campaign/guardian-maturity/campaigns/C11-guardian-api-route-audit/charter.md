# C11: Guardian API Route Audit and Scaffold

## Metadata

- **Campaign ID**: C11
- **Title**: Guardian API Route Audit and Scaffold
- **Wave**: 0
- **Status**: `planned`
- **Owner**: resonant_jones
- **Risk**: MED
- **Architecture Impact**: no (read-only audit; scaffold creation has no runtime behavior)
- **Governing ADRs/Contracts**:
  - [00-current-state.md](../../../architecture/00-current-state.md)
  - [Config and Ops](../../../architecture/config-and-ops.md)
  - [Chat Runtime Contract](../../../architecture/chat-runtime-contract.md)
  - [Agent Tool Loop Contract](../../../architecture/agent-tool-loop-contract.md)
  - [Pi Invocation Boundary Contract](../../../architecture/pi-invocation-boundary-contract.md)
  - [ADR-020: Guardian Mediated Coding Agent Execution Contract](../../../architecture/adr/020-guardian-mediated-coding-agent-execution-contract.md)

## Purpose

Audit what Guardian API routes exist, map gaps against the campaign map's needs, and scaffold missing route registration patterns. This campaign is read-only for the audit phase; route scaffolding (if any) must be registration-only with no behavior implementation.

## Current Truth Anchors

What is true now:
- `guardian/api/` contains `auth.py`, `deprecated-guardian_api.py`, and `schemas.py`.
- `guardian/guardian_api.py` is the central FastAPI app with router inclusion.
- `guardian/routes/` contains route modules for chat, codex, agent orchestration, delegations, command bus, and more.
- Health logic exists in `guardian/core/health_service.py` and `guardian/core/provider_truth.py`.
- Pi invocation validation exists in `guardian/pi/` (backend-only, no routes).

What is not yet known (targets for this audit):
- Exact health route registration location
- Work order CRUD route presence/absence
- Command run listing route presence/absence
- Invocation validation route presence/absence
- Execution ledger route presence/absence
- Auth/session operator status route presence/absence

## Non-Goals

- This campaign does **not** implement backend behavior.
- This campaign does **not** create working endpoints.
- This campaign does **not** modify existing route behavior.
- This campaign does **not** change provider routing, queue semantics, or worker orchestration.

## Invariants

- Do not implement behavior during audit.
- Do not register routes that would expose unimplemented behavior.
- Do not claim route presence proves runtime support.
- Do not modify `guardian/guardian_api.py` router inclusion unless a registration-only scaffold is explicitly required and approved.

## Dependencies

- C00 (Truth Gate) — needs worktree/runtime truth baseline

Campaigns that this campaign enables:
- C01 (Command Center) — needs verified health routes
- C03 (Coding Delegation Spine) — needs verified work order CRUD route surface
- C05 (Command Bus Observability) — needs verified command bus routes
- C04 (Pi/Coder Invocation Boundary) — needs verified invocation validation route surface
- C07 (Persona Studio) — needs verified config API routes
- C09 (Execution Ledger) — needs verified ledger route surface

## Route Audit Targets

The following route surfaces must be audited for presence, registration, and contract alignment:

### Health Routes
- `/health` — overall system health
- `/health/chat` — chat queue/worker health
- `/health/llm` — LLM provider health
- `/api/health/llm` — alternate LLM health path (per config-and-ops.md)
- `/api/health/retrieval` — retrieval health

### Provider and Catalog Routes
- `/api/llm/catalog` — provider/model inventory
- `/api/llm/catalog?include=all` — full inventory including hidden providers

### Coding Work Order Routes
- POST/GET/PATCH for coding work orders (verify presence/absence)
- Work order listing and detail endpoints

### Command Bus Routes
- Command run listing and detail endpoints
- Tool turn state endpoints

### Pi/Coder Invocation Routes
- Invocation envelope validation endpoint (verify presence/absence)
- Invocation preview endpoint (verify presence/absence)

### Execution Ledger Routes
- Ledger row listing and detail endpoints (verify presence/absence)
- Proof artifact endpoints (verify presence/absence)

### Auth/Session Routes
- Operator identity/status endpoint
- Session state endpoint

### Task Event / SSE Routes
- `/api/tasks/<task_id>/events` — task event stream
- SSE route registration

## Proof Gates

| Category | Required Evidence |
|----------|-------------------|
| Docs proof | Route audit report documents presence/absence of each target |
| Backend seam proof | Each existing route is verified with a test request |
| Backend seam proof | Missing routes are explicitly documented as gaps |

## Done-When

The campaign is done when:
1. All route audit targets have been inspected.
2. Existing routes are verified (presence + response shape).
3. Missing routes are documented as gaps with dependency mapping.
4. Route audit report is recorded in `proof-pack.md`.
5. Gate decision is recorded in `decision-log.md`.
6. No route scaffolding is created unless explicitly required and approved by a follow-up task.

## Risks

- **False positives**: A route may be registered but not wired to the correct backend service. Verify response shape, not just HTTP status.
- **Route naming conventions**: Paths may vary from expected. Audit must inspect `guardian/guardian_api.py` router inclusion to find actual paths.

## Task Queue

Tasks are tracked in [`backlog.md`](./backlog.md).
