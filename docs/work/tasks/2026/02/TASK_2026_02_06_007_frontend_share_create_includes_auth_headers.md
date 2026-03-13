# TASK-2026-02-06-007_frontend_share_create_includes_auth_headers
## Metadata

- Task-ID: TASK-2026-02-06-007_frontend_share_create_includes_auth_headers
- Campaign-ID: CAMPAIGN_2026_02_06_GUARDIAN_PARITY_CONTROL_PLANE
- Branch: campaign/2026-02-06/loop-integrity-auth-and-defaults
- Task artifact: docs/work/tasks/2026/02/TASK_2026_02_06_007_frontend_share_create_includes_auth_headers.md
- Owner: resonant_jones
- Risk: HIGH
- Commit mode: two-phase (Commit A = implementation, Commit B = docs finalize + mapping)

## Objective

Share-link creation from the frontend must succeed when `GUARDIAN_API_KEY` is enforced, by ensuring the share-create request includes auth headers (`X-API-Key` at minimum).

## Background / Problem Statement (evidence anchor)

Audit/MR comment indicates:

- Backend now enforces API key on `POST /api/share`.
- Frontend `ShareButton.tsx` uses `fetch('/api/share')` without auth headers, causing 401 in real configs.

## Scope

### In-scope

- Update the frontend share-create call to include auth headers consistently (prefer centralized client/header helper if it exists).
- Add explicit failure signaling/logging so a 401 is observable (no silent failure).

### Out-of-scope

- Any backend auth behavior changes.
- Refactors unrelated to share creation.
- UI redesign.

## Allowed files (STRICT)
>
> Do not modify files outside this list.

- frontend/src/components/ShareButton.tsx
- frontend/src/lib/api.ts
- docs/work/tasks/2026/02/TASK_2026_02_06_007_frontend_share_create_includes_auth_headers.md
- docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

If the correct shared API helper is NOT in `frontend/src/lib/api.ts`, STOP and emit a BLOCKER_PROMPT listing the actual path you need to add.

## Dependencies / Prereqs (NO GUESSING)

Run these and record output (trimmed) in Summary:

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# confirm toolchain
node -v
npm -v

# confirm frontend deps installed
ls -la frontend/node_modules >/dev/null || (cd frontend && npm install)

# confirm expected env var names appear in repo (do not print secrets)
rg -n "VITE_GUARDIAN_API_KEY|GUARDIAN_API_KEY" -S frontend/src guardian || true

Command checklist (copy/paste)

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) REQUIRED: clean tree before starting
git status --porcelain -uall

# 1) locate share create call + existing header pattern
rg -n "fetch\\(['\"]/api/share|/api/share" frontend/src
rg -n "X-API-Key|Authorization|apiKey|VITE_GUARDIAN_API_KEY" frontend/src/lib/api.ts frontend/src -S

# 2) edit ONLY allowed files
# - Ensure POST /api/share includes auth headers (X-API-Key at minimum).
# - Prefer using the centralized API client/header builder in frontend/src/lib/api.ts if present.
# - Ensure failures are observable (e.g., throw on !resp.ok or log + surface error state).

# 3) build check
npm --prefix frontend run build

# 4) (optional but recommended) manual endpoint sanity check if backend is running
# NOTE: do not paste real secrets into logs. This is for local shell use.
# curl -i -X POST "http://localhost:8000/api/share" \
#   -H "Content-Type: application/json" \
#   -H "X-API-Key: $GUARDIAN_API_KEY" \
#   -H "X-User-Id: test_user" \
#   -d '{"target_type":"thread","target_id":1}'

# 5) confirm only allowed files changed
git status --porcelain -uall

Expected outputs (explicit success signals)
 • npm --prefix frontend run build exits 0.
 • The share-create request includes auth headers:
 • Either visibly in code (headers: { "X-API-Key": ... }) OR via a shared helper used by the callsite.
 • Failure is observable:
 • Non-2xx responses are not silently ignored (e.g., throws, returns error state, logs error).
 • git status --porcelain -uall shows changes ONLY in the Allowed files list.

Rollback / cleanup

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# discard changes for this task (if needed)
git restore -- frontend/src/components/ShareButton.tsx frontend/src/lib/api.ts

# verify clean
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation)
 • Commit message (EXACT):
 • TASK-2026-02-06-007_frontend_share_create_includes_auth_headers: send auth headers on share create
 • Manual commands:

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

git add \
  frontend/src/components/ShareButton.tsx \
  frontend/src/lib/api.ts

git commit --no-verify -m "TASK-2026-02-06-007_frontend_share_create_includes_auth_headers: send auth headers on share create"
git log -1 --oneline
git status --porcelain -uall

Commit B (docs finalize + mapping)
 • Commit message (EXACT):
 • TASK-2026-02-06-007_frontend_share_create_includes_auth_headers: docs finalize + mapping
 • Manual commands:

cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

git add \
  docs/work/tasks/2026/02/TASK_2026_02_06_007_frontend_share_create_includes_auth_headers.md \
  docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md

git commit --no-verify -m "TASK-2026-02-06-007_frontend_share_create_includes_auth_headers: docs finalize + mapping"
git log -1 --oneline
git status --porcelain -uall

Campaign mapping line (required)

In docs/work/campaigns/2026/02/CAMPAIGN_2026_02_06_LOOP_INTEGRITY_AUTH_AND_DEFAULTS.md ensure the mapping line uses:

TASK-2026-02-06-007_frontend_share_create_includes_auth_headers -> [<commitA>, <commitB>]

Summary (fill after completion)
 • Files changed:
 • frontend/src/components/ShareButton.tsx
 • Commands run:
 • node -v => v22.17.0
 • npm -v => 10.9.2
 • ls -la frontend/node_modules >/dev/null || (cd frontend && npm install) => deps present
 • rg -n "VITE_GUARDIAN_API_KEY|GUARDIAN_API_KEY" -S frontend/src guardian || true => env key references confirmed
 • git status --porcelain -uall => clean before implementation
 • rg -n "fetch\\(['\"]/api/share|/api/share" frontend/src => share create call located in ShareButton
 • rg -n "X-API-Key|Authorization|apiKey|VITE_GUARDIAN_API_KEY" frontend/src/lib/api.ts frontend/src -S => auth header patterns confirmed
 • npm --prefix frontend run build => PASS
 • git status --porcelain -uall => only ShareButton changed before Commit A
 • Build/test results:
 • npm --prefix frontend run build => PASS
 • Notes:
 • Share create now sends `X-API-Key` when `VITE_GUARDIAN_API_KEY` is set and logs failures (`console.error`) in addition to toast error state.
 • Commit A:
 • 217fb789
 • Commit B:
 • <commitB>
 • Final mapping:
 • TASK-2026-02-06-007_frontend_share_create_includes_auth_headers -> [217fb789, <commitB>]
