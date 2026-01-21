# TASK_2026_01_20_007_import_refresh_event

TASK-ID: TASK-2026-01-20-007_IMPORT_REFRESH_EVENT
CAMPAIGN-ID: CAMPAIGN-2026-01-20-002_MVP_LOOP_CLOSURE_CHATGPT_MIGRATION

## Context

ChatGPT import currently succeeds, but the Threads sidebar/UI can remain stale until a manual refresh or navigation. This task makes the UI update immediately after a successful import by dispatching a threads refresh signal (consistent with existing frontend event patterns).

Notes:
- Canonical backend import endpoint is **POST /api/upload-chatgpt-export**.
- Legacy alias **POST /upload-chatgpt-export** may still exist; do not remove it.

## Objective

After a successful ChatGPT import, automatically trigger a threads refresh so the imported threads appear without a manual reload.

## Requirements

### Behavior

- On successful import completion (2xx response), dispatch a threads refresh event/signal that the Threads list logic already listens to.
- On failure (non-2xx / exception), do not dispatch the refresh; show an existing error surface (toast/log) if already present.
- Keep changes minimal and localized; no unrelated refactors.

### Files allowed to edit (only)

- `frontend/src/features/settings/SettingsView.tsx`
- `frontend/src/components/modals/ChatGPTImportModal.tsx`
- `frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx`
- `frontend/src/components/persona/hooks/useThreads.ts`
- `frontend/src/lib/events.ts`

> If implementation requires touching any file not listed above, **STOP** and report the exact path(s) needed.

### Tests / commands required

Run these commands and report results in the task artifact:

- `pnpm --dir frontend/src test`
- `pnpm --dir frontend/src lint`

If tests require the backend running, note that explicitly in the report (but still run what you can).

### Commit mode

Two-phase commits:

1) Implementation commit (code changes)
- Commit message template:
  - `TASK-2026-01-20-007_IMPORT_REFRESH_EVENT: refresh threads after import`

2) Task artifact commit (this file updates with results + hashes)
- Commit message template:
  - `TASK-2026-01-20-007_IMPORT_REFRESH_EVENT: finalize task summary`

## Suggested implementation approach

- Prefer a **CustomEvent**-style signal consistent with existing conventions (e.g. `cfy:threads:refresh`), or reuse the exact event name already used elsewhere.
- Dispatch after the import promise resolves successfully.
- If the threads list is driven by a query cache/store, trigger its existing invalidation mechanism instead of inventing a new one.

## Expected Output

- Imported ChatGPT threads appear in the sidebar/threads list immediately after successful import.
- No regressions to existing chat/migration flows.
- Tests above run and pass (or existing baseline warnings only).

## Report (fill in after completion)

### Summary of changes

- 

### Tests

- `pnpm --dir frontend/src test`:
- `pnpm --dir frontend/src lint`:

### git status

- `git status --porcelain`:

### Mapping

- TASK-2026-01-20-007_IMPORT_REFRESH_EVENT -> [<impl_commit_sha>, <artifact_commit_sha>]
