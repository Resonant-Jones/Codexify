# Codexify Task Prompt

TASK-ID: TASK-2026-01-20-007_IMPORT_REFRESH_EVENT
CAMPAIGN-ID: CAMPAIGN-2026-01-20-002_MVP_LOOP_CLOSURE_CHATGPT_MIGRATION

## Task Prompt

### Context

ChatGPT import currently succeeds, but the Threads sidebar/UI can remain stale until a manual refresh or navigation. This task makes the UI update immediately after a successful import by dispatching a threads refresh signal consistent with existing frontend event patterns.

Notes:
- Canonical backend import endpoint is POST /api/upload-chatgpt-export.
- Legacy alias POST /upload-chatgpt-export may still exist; do not remove it.

### Instructions

- On successful import completion (2xx response), dispatch a threads refresh event/signal that the Threads list logic listens to.
- On failure (non-2xx / exception), do not dispatch the refresh; keep existing error surfaces (toast/log) as-is.
- Keep changes minimal and localized; avoid unrelated refactors.
- Files allowed to edit (only):
  - frontend/src/features/settings/SettingsView.tsx
  - frontend/src/components/modals/ChatGPTImportModal.tsx
  - frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx
  - frontend/src/components/persona/hooks/useThreads.ts
  - frontend/src/lib/events.ts
- Tests / commands required:
  - pnpm --dir frontend/src test
  - pnpm --dir frontend/src lint
- Commit mode: two-phase.
  - Implementation: TASK-2026-01-20-007_IMPORT_REFRESH_EVENT: refresh threads after import
  - Finalize: TASK-2026-01-20-007_IMPORT_REFRESH_EVENT: finalize task summary
- Suggested approach: use the existing CustomEvent cfy:threads:refresh and dispatch after the import promise resolves successfully.

### Task Description

After a successful ChatGPT import, automatically trigger a threads refresh so the imported threads appear without a manual reload.

### Expected Output

- Imported ChatGPT threads appear in the sidebar/threads list immediately after successful import.
- No regressions to existing chat/migration flows.
- Tests above run and pass (baseline warnings allowed).

## Summary

- Updated frontend/src/components/modals/ChatGPTImportModal.tsx to dispatch cfy:threads:refresh after a successful import.
- Updated frontend/src/components/persona/layout/GuardianChatWithSidebar.tsx to reload threads on refresh/import events.
- Tests: pnpm --dir frontend/src test (pass; baseline warning about baseline-browser-mapping and existing act(...) warnings); pnpm --dir frontend/src lint (pass with existing warnings).
- git status --porcelain: docs/work/tasks/2026/01/TASK_2026_01_20_007_import_refresh_event.md.
- Commit mode: two-phase.
- Implementation hash: 05243462653636dc983f198a20cfbccc33568635.
- Finalize-artifact hash: reported in campaign mapping.
