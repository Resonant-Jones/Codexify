# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_MVP_CORE_LOOP_CLOSURE
- Task ID: 004
- Title: Drive active gallery UI from backend /api/media/images
- Finding: FINDING-2026-02-10-007
- Risk: MED

## Allowed Files
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/components/gallery/GalleryView.tsx
- frontend/src/tests/playwright/gallery_persistence.spec.ts

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }
4. rg -n 'cfy.gallery|/api/media/images' frontend/src/components/persona/layout/AppShell.tsx frontend/src/components/gallery/GalleryView.tsx
5. cd frontend && npx playwright test src/tests/playwright/gallery_persistence.spec.ts
6. for f in $(git diff --name-only); do case $f in frontend/src/components/persona/layout/AppShell.tsx|frontend/src/components/gallery/GalleryView.tsx|frontend/src/tests/playwright/gallery_persistence.spec.ts) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- AppShell gallery render path uses backend image list as primary truth.
- Reload behavior reflects persisted backend state, not localStorage-only cache.
- Gallery persistence Playwright test passes.

## Rollback / Cleanup
- git restore --staged frontend/src/components/persona/layout/AppShell.tsx frontend/src/components/gallery/GalleryView.tsx frontend/src/tests/playwright/gallery_persistence.spec.ts || true
- git restore frontend/src/components/persona/layout/AppShell.tsx frontend/src/components/gallery/GalleryView.tsx frontend/src/tests/playwright/gallery_persistence.spec.ts || true
- rm -f frontend/src/tests/playwright/gallery_persistence.spec.ts

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v npx >/dev/null
- test -n ${GUARDIAN_API_KEY:-} || { echo 'Missing GUARDIAN_API_KEY'; exit 1; }


---

# Task 004 — Frontend: Settings Migration Uses Canonical Authenticated Endpoint (FINDING-2026-02-16-004)

Preflight: git status --porcelain -uall must be empty

## STOP Conditions
1) If preflight is not empty, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

2) If any out-of-scope files appear at any point, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

## Finding
- ID: `FINDING-2026-02-16-004`
- Severity: `WARN` (map to task risk: MED)
- Title: Migration loop has conflicting client behavior: SettingsView uses legacy route without API key

## Outcome (must be observable)
- All migration UI entry points use the canonical endpoint `/api/upload-chatgpt-export` via an authenticated API client (includes `X-API-Key` or the project’s standard auth mechanism).
- No user-facing UI path posts to legacy `/upload-chatgpt-export` without auth.

## Allowed Files (strict)
- `frontend/src/components/settings/SettingsView.tsx`
- `frontend/src/components/modals/ChatGPTImportModal.tsx`
- `frontend/src/**/*.ts`
- `frontend/src/**/*.tsx`
- `frontend/src/tests/playwright/migration_e2e_import.spec.ts`
- `docs/**/*.md`

## Command Checklist
1) Preflight:
- `git status --porcelain -uall`

2) Locate all callers (audit-suggested):
- `rg -n "upload-chatgpt-export" frontend/src guardian/routes/migration.py -S`

3) Implement:
- Update `SettingsView.tsx` so it routes imports through the same canonical path and authenticated client used elsewhere (e.g., behavior consistent with `ChatGPTImportModal`).
- Ensure required headers are included (at minimum align with app’s API client patterns).
- If Playwright expectations need adjustment, update `migration_e2e_import.spec.ts` to reflect canonical behavior (only if tests fail due to this change).

4) Verify (static verification):
- Re-run: `rg -n "upload-chatgpt-export" frontend/src guardian/routes/migration.py -S`
- Confirm SettingsView no longer references legacy `/upload-chatgpt-export`.

5) Scope check:
- `git status --porcelain -uall`

## Expected Outputs (success signals)
- `rg` shows no SettingsView usage of legacy `/upload-chatgpt-export`.
- Canonical `/api/upload-chatgpt-export` is used consistently.
- `git status --porcelain -uall` shows modifications only within Allowed Files.

## Rollback / Cleanup Commands
- `git restore --source=HEAD --staged --worktree -- frontend/src/components/settings/SettingsView.tsx`
- `git restore --source=HEAD --staged --worktree -- frontend/src/components/modals/ChatGPTImportModal.tsx`
- `git restore --source=HEAD --staged --worktree -- frontend/src/tests/playwright/migration_e2e_import.spec.ts`
- `git restore --source=HEAD --staged --worktree -- frontend/src`
- `git restore --source=HEAD --staged --worktree -- docs`
- `git clean -fd`


## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_COMPILED_AUDIT

- Task ID: 004

- Head before: ecc0d69c4fc0f1e679f681b1edf0811512c1df84
