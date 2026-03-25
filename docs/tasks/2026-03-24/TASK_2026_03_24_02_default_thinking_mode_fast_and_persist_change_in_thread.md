⸻

Task 2: Default thinking mode to Fast and persist per thread

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Implement thread-scoped thinking mode persistence so FAST is the default for threads with no explicit selection, and the selected mode does not reset after each sent message.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend/src/features/chat/... thinking mode UI/state files
 • any thread metadata/state persistence layer used by chat preferences
 • tests near existing GuardianChat catalog/session/profile coverage

Required behavior

 1. Default behavior:
 • new thread or thread with no stored mode defaults to FAST
 2. Allowed selectable modes:
 • FAST
 • AUTO
 • DEEP
or the repo’s exact canonical equivalents if naming differs
 3. After user selects a mode for a thread:
 • selection persists for that thread
 • sending a message must not reset it
 • re-rendering the composer must not reset it
 4. Switching threads:
 • each thread restores its own stored thinking mode
 • threads with no saved value still default to FAST
 5. Provider/profile integration:
 • if request assembly depends on thinking mode, ensure the persisted value is what gets sent
 • do not silently downgrade selected mode during normal submit flow
 6. Preserve future profile support:
 • this change should not block thread-level model/profile-specific overrides later

Files to modify

List all files before changes. Likely candidates include:
 • frontend/src/features/chat/...
 • any thread state model/store
 • tests for session tabs, shortcuts, catalog options, or chat preferences

Tests

Run:

pnpm test

Add or update tests for:
 • default mode is FAST
 • selection persists after submit
 • selection persists across re-render
 • thread A and thread B can hold different selections
 • restored thread without saved setting defaults to FAST

Git commands

If checks pass:

git add <modified files>
git commit -m "Persist thread thinking mode with fast default"

Output must include
 • Summary of changes
 • files modified
 • components/hooks/state touched
 • Test results
 • Git commit hash

⸻

# TASK_2026_03_24_02_default_thinking_mode_fast_and_persist_change_in_thread

## Context

You’re operating on the local Codexify repo.  
Each task must be self-contained, testable, and committed individually.

## Instructions

Perform the described edit only in the specified files.

Implement thread-scoped thinking mode persistence so `FAST` is the default for threads with no explicit selection, and the selected mode does not reset after each sent message.

This change belongs in:

- `frontend/src/features/chat/...` thinking mode UI/state files
- any thread metadata/state persistence layer used by chat preferences
- tests near existing GuardianChat catalog/session/profile coverage

## Goal

Thinking mode must behave as a stable thread-level preference, not ephemeral UI state.  
Users should never lose their selected mode unintentionally.

## Required Behavior

1. Default behavior:
   - new thread or thread with no stored mode defaults to `FAST`

2. Allowed selectable modes:
   - `FAST`
   - `AUTO`
   - `DEEP`
   - or repo-specific canonical equivalents if naming differs

3. After user selects a mode for a thread:
   - selection persists for that thread
   - sending a message must not reset it
   - re-rendering the composer must not reset it

4. Switching threads:
   - each thread restores its own stored thinking mode
   - threads with no saved value still default to `FAST`

5. Provider/profile integration:
   - if request assembly depends on thinking mode, ensure the persisted value is what gets sent
   - do not silently downgrade or override selected mode during normal submit flow

6. Preserve future profile support:
   - this change must not block thread-level model/profile-specific overrides later

## Files to Modify

List all files before changes. Likely candidates include:

- `frontend/src/features/chat/...`
- any thread state model/store
- tests for session tabs, shortcuts, catalog options, or chat preferences

## Run Tests

Because this is frontend-only work, run:

```bash
pnpm test
```

Add or update tests for:

- default mode is `FAST`
- selection persists after submit
- selection persists across re-render
- thread A and thread B can hold different selections
- restored thread without saved setting defaults to `FAST`

## Git Commands

If checks pass:

```bash
git add <modified files>
git commit -m "Persist thread thinking mode with fast default"
```

## Output Must Include

- Summary of changes
- Files modified
- Components/hooks/state touched
- Test results
- Git commit hash