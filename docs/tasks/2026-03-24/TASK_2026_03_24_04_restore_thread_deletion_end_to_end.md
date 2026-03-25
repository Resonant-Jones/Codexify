
Task 4: Restore thread deletion end to end

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix thread deletion so a user can delete conversations reliably from the UI and the deletion is reflected immediately in thread state.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend thread list / thread actions UI
 • backend thread delete route/handler if needed
 • tests covering thread actions and thread persistence

Required behavior

 1. User can trigger delete from existing thread UI.
 2. The correct backend delete action is called.
 3. On success:
 • thread is removed from visible list
 • if active thread was deleted, UI transitions safely to a valid fallback state
 • composer is not left locked
 • stale deleted thread view is not retained
 4. On failure:
 • user receives clear error feedback
 • UI remains consistent
 • no phantom deletion in local state
 5. If deletion is blocked by active in-flight request:
 • either unwind request first or reject cleanly with clear UX
 • do not deadlock the thread UI

Files to modify

List all files before changes. Likely candidates include:
 • frontend/src/features/chat/...
 • backend thread routes/store if broken there
 • thread action tests

Tests

Run based on scope:
 • frontend-only:

pnpm test

 • if backend thread handlers are modified:

pytest -v
pnpm test

Add or update tests for:
 • delete succeeds and removes thread from UI
 • deleting active thread lands in safe fallback state
 • delete failure preserves consistent UI
 • thread lock is not stranded after delete flow

Git commands

If checks pass:

git add <modified files>
git commit -m "Fix thread deletion flow"

Output must include
 • Summary of changes
 • files modified
 • actions/routes/components touched
 • Test results
 • Git commit hash

⸻

# TASK_2026_03_24_04_restore_thread_deletion_end_to_end

## Context

You’re operating on the local Codexify repo.  
Each task must be self-contained, testable, and committed individually.

## Instructions

Perform the described edit only in the specified files.

Fix thread deletion so a user can delete conversations reliably from the UI and the deletion is reflected immediately in thread state.

This change belongs in:

- `frontend/src/features/chat/...` thread list / thread actions UI
- backend thread delete route/handler if needed
- tests covering thread actions and thread persistence

## Goal

Thread deletion must be a deterministic, user-visible mutation with no residual UI or state artifacts.

## Required Behavior

1. User can trigger delete from existing thread UI.

2. The correct backend delete action is called.

3. On success:
   - thread is removed from visible list
   - if active thread was deleted, UI transitions safely to a valid fallback state
   - composer is not left locked
   - stale deleted thread view is not retained

4. On failure:
   - user receives clear error feedback
   - UI remains consistent
   - no phantom deletion in local state

5. If deletion is blocked by active in-flight request:
   - either unwind request first or reject cleanly with clear UX
   - do not deadlock the thread UI

## Files to Modify

List all files before changes. Likely candidates include:

- `frontend/src/features/chat/...`
- backend thread routes/store if broken there
- thread action tests

## Run Tests

Run based on scope:

### Frontend-only

```bash
pnpm test
```

### If backend thread handlers are modified

```bash
pytest -v
pnpm test
```

Add or update tests for:

- delete succeeds and removes thread from UI
- deleting active thread lands in safe fallback state
- delete failure preserves consistent UI
- thread lock is not stranded after delete flow

## Git Commands

If checks pass:

```bash
git add <modified files>
git commit -m "Fix thread deletion flow"
```

## Output Must Include

- Summary of changes
- Files modified
- Actions/routes/components touched
- Test results
- Git commit hash