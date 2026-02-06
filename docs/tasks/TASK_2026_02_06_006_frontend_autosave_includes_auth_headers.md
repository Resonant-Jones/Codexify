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

# TASK_2026_02_06_006_frontend_autosave_includes_auth_headers

## Metadata
- Campaign-ID: CAMPAIGN-2026-02-06-LOOP_INTEGRITY_AUTH_AND_DEFAULTS
- Task-ID: TASK-2026-02-06-006_frontend_autosave_includes_auth_headers
- Risk: HIGH
- Task artifact: docs/tasks/TASK_2026_02_06_006_frontend_autosave_includes_auth_headers.md
- Owner: resonant_jones
- Branch (expected): campaign/2026-02-06/loop-integrity-auth-and-defaults

## Objective
Restore autosave functionality when Guardian API key auth is enabled by ensuring the autosave request includes the same auth headers as other authenticated frontend requests, and make failures observable.

## Scope
### In-scope
- Ensure the `/api/documents/autosave` request includes `X-API-Key` (and any other standard auth headers used in the app).
- Ensure autosave failures are observable (console error and/or UI signal).
- Keep behavior consistent with other frontend API calls.

### Out-of-scope
- Changing backend auth requirements for autosave.
- Refactoring unrelated editor behavior.
- Adding new persistence mechanisms.

## Allowed files (STRICT)
> Do not modify files outside this list.

- frontend/src/components/editor/CollaborativeNote.tsx
- frontend/src/lib/api.ts
- docs/tasks/TASK_2026_02_06_006_frontend_autosave_includes_auth_headers.md
- docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

## Preconditions (NO GUESSING)
Run these to confirm environment + locate relevant call sites.

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# Confirm the autosave endpoint path is referenced from the UI
rg -n "documents/autosave|/api/documents/autosave" frontend/src

# Identify the canonical place auth headers are set
rg -n "X-API-Key|Authorization|VITE_GUARDIAN_API_KEY|GUARDIAN_API_KEY" frontend/src/lib frontend/src
```

Expected signals:
- `git status --porcelain -uall` returns EMPTY.
- `CollaborativeNote.tsx` (or a nearby helper) contains the autosave request.
- There is an existing pattern for attaching auth headers (e.g., axios instance, fetch wrapper, or shared helper).

## Execution plan
### Step-by-step commands (copy/paste)
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 1) confirm clean scope
git status --porcelain -uall

# 2) confirm only allowed files are touched while you work
# (run this repeatedly during implementation)
git status --porcelain -uall

# 3) required frontend check (fast + deterministic)
# If this fails due to known unrelated build issues, capture the error verbatim in Summary.
npm --prefix frontend run build

# 4) optional (if relevant tests exist)
# Find autosave-related tests, then run the smallest relevant subset.
rg -n "autosave" tests guardian/tests || true
```

## Expected results
- With `GUARDIAN_API_KEY` configured server-side, the autosave request includes auth headers and returns **2xx** (verify via browser devtools network tab or server logs).
- Autosave failures are **observable** (console error and/or a visible UI indicator).
- `npm --prefix frontend run build` completes successfully.
- `git status --porcelain -uall` shows changes **only** in the Allowed files list.

## Rollback / cleanup
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# Discard changes to implementation files
git restore -- frontend/src/components/editor/CollaborativeNote.tsx frontend/src/lib/api.ts

# Discard changes to docs (task/campaign)
git restore -- docs/tasks/TASK_2026_02_06_006_frontend_autosave_includes_auth_headers.md docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

# Confirm clean
git status --porcelain -uall
```

## Commit plan (MANUAL; two-phase)
> Note: two-phase avoids the “ouroboros hash” problem by recording the implementation hash in-file and keeping the finalize hash in campaign mapping.

### Commit mode
- two-phase

### Commit A (implementation)
- Commit message (EXACT):
  - `TASK-2026-02-06-006_frontend_autosave_includes_auth_headers: include auth headers on autosave`

Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  frontend/src/components/editor/CollaborativeNote.tsx \
  frontend/src/lib/api.ts

git commit --no-verify -m "TASK-2026-02-06-006_frontend_autosave_includes_auth_headers: include auth headers on autosave"

git log -1 --oneline
```

### Commit B (docs finalize + mapping)
- Commit message (EXACT):
  - `TASK-2026-02-06-006_frontend_autosave_includes_auth_headers: docs finalize + mapping`

Manual commands:
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

git add \
  docs/tasks/TASK_2026_02_06_006_frontend_autosave_includes_auth_headers.md \
  docs/Campaign/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-006_frontend_autosave_includes_auth_headers: docs finalize + mapping"

git log -1 --oneline
```

## Campaign mapping
Update the campaign file mapping line to:
- `TASK-2026-02-06-006_frontend_autosave_includes_auth_headers -> [<commitA>, <commitB>]`

## Notes
- Keep any failure output verbatim in the Summary.

## Summary (fill after completion)
- What changed:
- Commands run + outcomes:
- Commit A:
- Commit B:
- Final mapping line:
  - `TASK-2026-02-06-006_frontend_autosave_includes_auth_headers -> [<commitA>, <commitB>]`