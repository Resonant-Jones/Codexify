Codexify Task Prompt

TASK-ID

TASK-2026-01-20-005_MIGRATION_ENDPOINT_SOURCE_OF_TRUTH

Context

You’re operating on the local Codexify repo.

We have ambiguity and drift around the ChatGPT Migration endpoint (“upload-chatgpt-export” / migration router). This is causing confusion and breaks MVP loop closure. We need one canonical backend entrypoint and one canonical endpoint path, and we must ensure the route is registered on the app that actually runs.

Canonical backend entrypoint is: guardian/guardian_api.py

Objective

Make the ChatGPT migration endpoint reachable and unambiguous by enforcing a single “source of truth” for router inclusion and endpoint path registration, using guardian/guardian_api.py as canonical.

Requirements
 • Ensure the ChatGPT migration endpoint is actually registered on the running FastAPI app.
 • Prefer one canonical endpoint path for the UI to call.
 • Preserve backwards compatibility where reasonable (aliases okay) but prevent “double-prefix” bugs (e.g., /api/api/...).
 • Do not refactor unrelated code.
 • Follow docs/Ops/Runner_Protocol.md two-phase commit pattern:
 • Commit A: implementation only
 • Commit B: task artifact only
 • Include TASK-ID in both commit messages.
 • Never use git commit --amend.

Commit-hash paradox handling:
In the task artifact doc you may write:
 • Finalize-artifact hash: (reported in final mapping)
…and in final output you MUST include both hashes.

Files allowed to edit (only)

Backend (canonical entrypoint and migration route wiring):
 • guardian/guardian_api.py
 • guardian/routes/migration.py

Backend tests (minimal route registration check):
 • tests/routes/test_migration_routes.py

Frontend (ONLY if needed to align endpoint base path and avoid /api/api drift):
 • frontend/src/lib/api.ts
 • frontend/src/features/migration/ChatGPTImportModal.tsx
 • frontend/src/features/migration/SettingsView.tsx

Docs:
 • docs/tasks/TASK_2026_01_20_005_migration_endpoint_source_of_truth.md

Implementation Notes
 1. Confirm current migration router shape

 • In guardian/routes/migration.py, identify the router prefix and route decorators.
 • Determine the intended canonical path:
 • Prefer /api/migration/... or /api/upload-chatgpt-export (pick one, consistent with existing naming).
 • If there are multiple competing endpoints, establish a single canonical path and optionally keep the old path as an alias route that delegates to the canonical handler.

 2. Register router in the canonical app

 • In guardian/guardian_api.py, ensure migration.router is included exactly once.
 • Ensure it is included in a way that matches the canonical prefix decision (avoid prefix="/api" + router already using /api/... duplication).

 3. Guard against double /api in frontend

 • If frontend calls are currently creating /api/api/... via api.ts baseURL + hardcoded /api/... paths, fix only the minimum needed so migration calls resolve correctly.
 • Prefer the “canonical baseURL approach” used elsewhere:
 • baseURL /api
 • paths begin with /migration/... or /chat/... (no extra /api in the call sites)

 4. Add/adjust a minimal test
 • Add or update a backend test that verifies the canonical migration endpoint returns a non-404 response.
 • Use the allowed test file: tests/routes/test_migration_routes.py.
 • Keep it simple: route exists + returns a response (status != 404) is enough for this task.

Checks to run (required)

Backend:
 • pytest -v

Frontend (ONLY if any of the allowed frontend files were edited):
 • pnpm --dir frontend/src test
 • pnpm --dir frontend/src lint (warnings ok, errors not ok)

Git:
 • git status --porcelain (must be empty at end)

Git steps (two-phase)

Commit A (implementation)
 1. git status --porcelain
 2. Make scoped changes per above
 3. Run required checks (see above)
 4. git status --porcelain (verify only allowed files changed)
 5. git add <allowed files that changed>
 6. git commit -m "TASK-2026-01-20-005_MIGRATION_ENDPOINT_SOURCE_OF_TRUTH: canonicalize migration endpoint wiring"

Commit B (finalize task artifact)
 1. Update docs/tasks/TASK_2026_01_20_005_migration_endpoint_source_of_truth.md with:
 • Task Prompt (verbatim)
 • Summary:
 • files changed
 • commands run + results
 • git status confirmation
 • Commit mode: two-phase (no amend)
 • Implementation hash: <hash A>
 • Finalize-artifact hash: (reported in final mapping)
 2. git add docs/tasks/TASK_2026_01_20_005_migration_endpoint_source_of_truth.md
 3. git commit -m "TASK-2026-01-20-005_MIGRATION_ENDPOINT_SOURCE_OF_TRUTH: finalize task summary"

Output required

After finishing, output:
 • Summary of changes
 • Commands run + pass/fail
 • git status --porcelain (must be empty)
 • Mapping:
 • TASK-2026-01-20-005_MIGRATION_ENDPOINT_SOURCE_OF_TRUTH -> [<impl_hash>, <finalize_hash>]

Acceptance Criteria

✅ Migration endpoint is reachable (no 404) via the canonical path
✅ Router inclusion is correct in guardian/guardian_api.py (single source of truth)
✅ No /api/api drift introduced
✅ Tests pass; working tree clean
