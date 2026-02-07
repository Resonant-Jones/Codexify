# TASK_2026_02_06_006_frontend_autosave_includes_auth_headers

## Objective

Restore autosave functionality when Guardian API key auth is enabled.

## Background

`/api/documents/autosave` now requires API key auth.
Frontend autosave requests omit auth headers, causing silent 401 failures.

## Requirements

- Autosave requests must include required auth headers
- Failure must not be silent (console or UI signal)
- Behavior must match other authenticated frontend requests

## Acceptance Criteria

- With `GUARDIAN_API_KEY` set, autosave returns 2xx
- Autosave failures are observable (console or UI)
- No regression when auth is disabled

## Files Likely Touched

- `frontend/src/components/editor/CollaborativeNote.tsx`
- Optional shared fetch helper

## Commit Plan

- Commit A: frontend logic fix
- Commit B: docs/task mapping update
