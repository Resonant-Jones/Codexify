
Task 1: Release composer/thread lock on all terminal paths

Context

You’re operating on the local Codexify repo.
Each task must be self-contained, testable, and committed individually.

Instructions

Fix the chat composer/thread lock lifecycle so the active thread is always released when a turn terminates, regardless of whether the turn ends in success, error, timeout, dropped stream, aborted request, or provider switch.

Perform the described edit only in the specified files.

This change belongs in:
 • frontend/src/features/chat/... chat send/request lifecycle files
 • any shared chat state store/reducer used for in-flight composer locking
 • tests near existing GuardianChat/session/chat lifecycle coverage

Goal

The composer must not remain unusable after backend or stream failure.
The thread lock must be treated like a lease with deterministic cleanup, not a one-way gate.

Required behavior

 1. When a chat turn starts:
 • mark the thread/request as in-flight
 • disable composer as currently intended
 2. When a chat turn ends for any terminal reason:
 • success
 • backend error
 • network error
 • timeout
 • dropped SSE/stream
 • abort/cancel
 • provider switch while request is active
the composer lock must be cleared.
 3. If provider is changed during an active request:
 • current in-flight state must be unwound
 • composer becomes usable again
 • thread must not stay locked behind stale request state
 4. If the frontend has a “give up” or abort path, ensure it also clears:
 • thread lock
 • pending indicator
 • any request-scoped abort/controller handles
 5. Avoid double-unlock bugs:
 • cleanup should be idempotent
 • repeated terminal events must not throw or corrupt state

Files to modify

List all files before changes. Likely candidates include:
 • frontend/src/features/chat/...
 • frontend/src/features/chat/__tests__/...
 • any chat store/reducer file that owns in-flight state

Tests

Run the correct test suite based on scope:

pnpm test

Add or update tests for:
 • lock clears on successful completion
 • lock clears on backend error
 • lock clears on dropped stream / aborted request
 • provider change during active request clears lock
 • cleanup is idempotent

Git commands

If checks pass:

git add <modified files>
git commit -m "Release chat thread lock on all terminal states"

Output must include
 • Summary of changes
 • files modified
 • reducer/store/hooks/components touched
 • Test results
 • Git commit hash

# TASK_2026_03_24_01_release_composer_thread_lock_on_all_terminal_paths

## Context

You’re operating on the local Codexify repo.  
Each task must be self-contained, testable, and committed individually.

## Instructions

Perform the described edit only in the specified files.

Fix the chat composer/thread lock lifecycle so the active thread is always released when a turn terminates, regardless of whether the turn ends in success, error, timeout, dropped stream, aborted request, or provider switch.

This change belongs in:

- `frontend/src/features/chat/...` chat send/request lifecycle files
- any shared chat state store/reducer used for in-flight composer locking
- tests near existing GuardianChat/session/chat lifecycle coverage

## Goal

The composer must not remain unusable after backend or stream failure.  
The thread lock must be treated like a lease with deterministic cleanup, not a one-way gate.

## Required Behavior

1. When a chat turn starts:
   - mark the thread/request as in-flight
   - disable composer as currently intended

2. When a chat turn ends for any terminal reason, clear the composer lock:
   - success
   - backend error
   - network error
   - timeout
   - dropped SSE/stream
   - abort/cancel
   - provider switch while request is active

3. If provider is changed during an active request:
   - current in-flight state must be unwound
   - composer becomes usable again
   - thread must not stay locked behind stale request state

4. If the frontend has a give-up or abort path, ensure it also clears:
   - thread lock
   - pending indicator
   - any request-scoped abort/controller handles

5. Avoid double-unlock bugs:
   - cleanup should be idempotent
   - repeated terminal events must not throw or corrupt state

## Files to Modify

List all files before changes. Likely candidates include:

- `frontend/src/features/chat/...`
- `frontend/src/features/chat/__tests__/...`
- any chat store/reducer file that owns in-flight state

## Run Tests

Because this is frontend-only work, run:

```bash
pnpm test
```

Add or update tests for:

- lock clears on successful completion
- lock clears on backend error
- lock clears on dropped stream / aborted request
- provider change during active request clears lock
- cleanup is idempotent

## Git Commands

If checks pass:

```bash
git add <modified files>
git commit -m "Release chat thread lock on all terminal states"
```

## Output Must Include

- Summary of changes
- Files modified
- Reducer/store/hooks/components touched
- Test results
- Git commit hash