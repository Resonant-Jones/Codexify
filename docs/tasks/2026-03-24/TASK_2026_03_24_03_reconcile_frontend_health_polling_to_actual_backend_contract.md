
Task 3: Reconcile frontend health polling to actual backend contract

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Remove or reconcile frontend polling of health endpoints that do not exist in the active backend contract. Frontend health checks must target real backend routes only.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend health/polling/readiness code
 • any backend route declarations only if needed to align contract
 • tests covering offline banner, readiness checks, or health polling

Goal

Stop repeated polling of dead endpoints such as /api/health and /api/health/chat if those routes are not part of the current backend contract.

Required behavior

 1. Audit current frontend health polling targets.
 2. Replace or remove calls to nonexistent routes.
 3. Use only routes that currently exist, such as:
 • /api/health/llm
 • /api/health/embedder
 • other actual routes already implemented in repo
 4. If composite app readiness is required, compute it from valid route results only.
 5. Do not leave silent noisy 404 polling loops in place.
 6. If backend contract should include missing routes instead, implement that in a separate task. This task is for contract reconciliation, not speculative route expansion.

Files to modify

List all files before changes. Likely candidates include:
 • frontend polling/offline banner/readiness hooks
 • frontend API client files
 • related tests

Tests

Run based on scope:
 • Frontend-only:

pnpm test

 • If backend route tests are touched too, run both:

pytest -v
pnpm test

Add or update tests for:
 • no polling to removed/nonexistent endpoints
 • readiness banner behavior still works
 • health state derived from valid endpoints only

Git commands

If checks pass:

git add <modified files>
git commit -m "Align health polling with backend routes"

Output must include
 • Summary of changes
 • files modified
 • routes/hooks touched
 • Test results or explicit note if both suites were required
 • Git commit hash

⸻

# TASK_2026_03_24_03_reconcile_frontend_health_polling_to_actual_backend_contract

## Context

You’re operating on the local Codexify repo.  
Each task must be self-contained, testable, and committed individually.

## Instructions

Perform the described edit only in the specified files.

Remove or reconcile frontend polling of health endpoints that do not exist in the active backend contract. Frontend health checks must target real backend routes only.

This change belongs in:

- frontend health/polling/readiness code
- any backend route declarations only if needed to align contract
- tests covering offline banner, readiness checks, or health polling

## Goal

Eliminate repeated polling of nonexistent endpoints and ensure frontend readiness logic reflects the actual backend contract.

## Required Behavior

1. Audit current frontend health polling targets.

2. Replace or remove calls to nonexistent routes.

3. Use only routes that currently exist, such as:
   - `/api/health/llm`
   - `/api/health/embedder`
   - other actual routes implemented in the repo

4. If composite app readiness is required:
   - compute readiness from valid route results only
   - avoid assumptions about missing endpoints

5. Do not leave silent noisy 404 polling loops in place.

6. If the backend contract should include missing routes instead:
   - do not add them here
   - create a separate task for backend expansion

## Files to Modify

List all files before changes. Likely candidates include:

- frontend polling/offline banner/readiness hooks
- frontend API client files
- related tests

## Run Tests

Run based on scope:

### Frontend-only

```bash
pnpm test
```

### If backend routes are also modified

```bash
pytest -v
pnpm test
```

Add or update tests for:

- no polling to removed/nonexistent endpoints
- readiness banner behavior still works
- health state derived from valid endpoints only

## Git Commands

If checks pass:

```bash
git add <modified files>
git commit -m "Align health polling with backend routes"
```

## Output Must Include

- Summary of changes
- Files modified
- Routes/hooks touched
- Test results (or note if both suites were required)
- Git commit hash