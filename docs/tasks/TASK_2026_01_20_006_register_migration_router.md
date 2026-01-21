# Codexify Task Prompt

TASK-ID: TASK-2026-01-20-006_REGISTER_MIGRATION_ROUTER

## Context

We are executing CAMPAIGN-2026-01-20-002_MVP_LOOP_CLOSURE_CHATGPT_MIGRATION.

TASK-2026-01-20-005 established the canonical migration endpoint:

- Canonical: POST /api/upload-chatgpt-export
- Legacy alias preserved: POST /upload-chatgpt-export

However, we still need to ensure the **migration router is actually registered in the canonical backend entrypoint** so the endpoint cannot “silently disappear” depending on which app module is used.

**Canonical backend entrypoint (source of truth):**

- `guardian/guardian_api.py`

## Objective

Ensure the migration router is registered in `guardian/guardian_api.py` so that:

- `/api/upload-chatgpt-export` is reachable (non-404)
- `/upload-chatgpt-export` remains reachable (non-404)
- Registration is covered by an automated test that imports and exercises the canonical app.

## Requirements

- Use `guardian/guardian_api.py` as the canonical server entrypoint.
- Do not change runtime behavior beyond ensuring router registration.
- Prefer minimal diffs: register only what’s missing.
- Add/extend a backend test that fails if the routes are not registered.
- Follow `docs/Ops/Runner_Protocol.md` exactly:
  - Two-phase commits (A = implementation, B = docs artifact)
  - Include TASK-ID in both commit messages
  - No `--amend`
- Keep git clean at the end.

## Files allowed to edit (only)

- `guardian/guardian_api.py`
- `tests/routes/test_migration_routes.py`
- `docs/tasks/TASK_2026_01_20_006_register_migration_router.md`

## Implementation Notes

- If `guardian/guardian_api.py` already includes `migration.router`, verify that it is included **unconditionally** (not behind env flags) and that import order doesn’t prevent registration.
- The test should import the FastAPI app from `guardian.guardian_api` and assert:
  - `POST /api/upload-chatgpt-export` returns non-404 (200/4xx acceptable, but not 404)
  - `POST /upload-chatgpt-export` returns non-404
- Prefer a light handler patch/stub if the endpoint requires body/auth:
  - The test is for **route registration**, not full behavior.

## Checks to run (required)

- `pytest -v`
- `git status --porcelain` (must be empty at end)

## Git steps (two-phase)

### Commit A (implementation)

1) `git status --porcelain`
2) Make scoped changes to allowed files only
3) `pytest -v` (must pass)
4) `git status --porcelain` (verify only allowed files changed)
5) `git add guardian/guardian_api.py tests/routes/test_migration_routes.py`
6) `git commit -m "TASK-2026-01-20-006_REGISTER_MIGRATION_ROUTER: register migration router in guardian_api"`

Capture Commit A hash.

### Commit B (finalize task artifact)

1) Create/update `docs/tasks/TASK_2026_01_20_006_register_migration_router.md` with:
   - Task Prompt (verbatim)
   - Summary (files changed, commands run + results, git status confirmation)
   - Commit mode: two-phase (no amend)
   - Implementation hash: <hash A>
   - Finalize-artifact hash: (reported in final mapping)
2) `git add docs/tasks/TASK_2026_01_20_006_register_migration_router.md`
3) `git commit -m "TASK-2026-01-20-006_REGISTER_MIGRATION_ROUTER: finalize task summary"`

Capture Commit B hash.

## Output required (in final response)

- Summary of changes (high signal)
- Commands run + pass/fail
- `git status --porcelain` (must be empty)
- Mapping:
  TASK-2026-01-20-006_REGISTER_MIGRATION_ROUTER -> [<impl_hash>, <finalize_hash>]

## Acceptance Criteria

✅ Migration routes are registered via `guardian/guardian_api.py`  
✅ Automated test confirms non-404 for both canonical and legacy endpoints  
✅ `pytest -v` passes  
✅ Working tree clean after finalize commit
