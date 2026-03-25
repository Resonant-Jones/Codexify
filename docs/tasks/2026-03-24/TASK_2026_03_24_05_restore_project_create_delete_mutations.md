# TASK_2026_03_24_05_restore_project_create_delete_mutations

## Context

You’re operating on the local Codexify repo.  
Each task must be self-contained, testable, and committed individually.

## Instructions

Perform the described edit only in the specified files.

Fix project mutation flows so users can create and delete projects reliably, with immediate and consistent UI updates.

This change belongs in:

- project management UI
- frontend API client/state for project mutations
- backend project create/delete handlers if needed
- tests covering project CRUD

## Goal

Project create and delete must behave as deterministic mutations with immediate UI consistency and no ghost state.

## Required Behavior

1. Preserve existing read path:
   - `GET /projects` continues to function unchanged

2. Project create must:
   - call correct backend route
   - add created project into UI state immediately on success
   - move to a sensible selected/focused state if current UX expects it

3. Project delete must:
   - call correct backend route
   - remove project from UI state immediately after success
   - safely handle deletion of the currently selected project

4. On create/delete failure:
   - show clear error feedback
   - UI remains consistent
   - do not leave ghost state in UI

5. Avoid stale-cache issues:
   - list reflects result without requiring full app reload

## Files to Modify

List all files before changes. Likely candidates include:

- frontend project feature files
- backend project route/store files
- tests for project list and mutations

## Run Tests

Run based on scope:

### Backend + Frontend (likely)

```bash
pytest -v
pnpm test
```

Add or update tests for:

- create project success
- create project failure
- delete project success
- delete selected project fallback behavior
- delete project failure without ghost removal

## Git Commands

If checks pass:

```bash
git add <modified files>
git commit -m "Fix project create and delete flows"
```

## Output Must Include

- Summary of changes
- Files modified
- Handlers/components touched
- Test results
- Git commit hash
