# Task Receipt

- Campaign: CAMPAIGN_2026_02_10_FOLLOWUP_DRIFT
- Task ID: 001
- Title: Canonicalize SettingsView implementation and deprecate drifted variant
- Finding: FINDING-2026-02-10-011
- Risk: LOW

## Allowed Files
- frontend/src/components/persona/layout/AppShell.tsx
- frontend/src/features/settings/SettingsView.tsx
- frontend/src/components/settings/SettingsView.tsx
- docs/frontend/settings-view-canonical.md

## Command Checklist
1. Preflight: git status --porcelain -uall must be empty
2. if git status --porcelain -uall | rg . >/dev/null; then echo 'STOP: dirty tree'; echo 'Cleanup: git restore --staged . && git restore . && git clean -fd'; exit 1; fi
3. rg -n 'SettingsView|upload-chatgpt-export' frontend/src/components/persona/layout/AppShell.tsx frontend/src/features/settings/SettingsView.tsx frontend/src/components/settings/SettingsView.tsx
4. rg --files frontend/src | rg 'SettingsView.tsx'
5. cd frontend && npx vitest run --passWithNoTests
6. for f in $(git diff --name-only); do case $f in frontend/src/components/persona/layout/AppShell.tsx|frontend/src/features/settings/SettingsView.tsx|frontend/src/components/settings/SettingsView.tsx|docs/frontend/settings-view-canonical.md) ;; *) echo 'STOP: out-of-scope file '$f; echo 'Cleanup: git restore --staged . && git restore .'; exit 1;; esac; done

## Expected Outputs
- Single canonical settings implementation is documented and used by active app flow.
- Legacy settings component is explicitly deprecated or excluded from active build path.
- Drift ambiguity for migration endpoint usage is removed.

## Rollback / Cleanup
- git restore --staged frontend/src/components/persona/layout/AppShell.tsx frontend/src/features/settings/SettingsView.tsx frontend/src/components/settings/SettingsView.tsx docs/frontend/settings-view-canonical.md || true
- git restore frontend/src/components/persona/layout/AppShell.tsx frontend/src/features/settings/SettingsView.tsx frontend/src/components/settings/SettingsView.tsx docs/frontend/settings-view-canonical.md || true
- rm -f docs/frontend/settings-view-canonical.md

## Dependencies / Prereqs
- command -v git >/dev/null
- command -v rg >/dev/null
- command -v npx >/dev/null


---

# Task 001 — Security: Env Hygiene Templates + Docs (FINDING-2026-02-16-001)

Preflight: git status --porcelain -uall must be empty

## STOP Conditions
1) If preflight is not empty, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`
- Re-run: `git status --porcelain -uall`

2) If any out-of-scope files appear at any point, STOP and run:
- `git status --porcelain -uall`
- `git restore --staged --worktree -- .`
- `git clean -fd`

## Finding
- ID: `FINDING-2026-02-16-001`
- Severity: `RISK` (map to task risk: HIGH)
- Title: Local `.env` contains hardcoded API key + service credentials

## Outcome (must be observable)
- The repo provides a safe env workflow via `.env.example` and/or `.env.template` with placeholder values only.
- Docs explicitly warn that `VITE_GUARDIAN_API_KEY` must not be shipped in any non-local / public deployment mode.
- `.env` remains ignored (and untracked), and no real tokens/credentials exist in tracked templates/docs.

## Allowed Files (strict)
- `.gitignore`
- `.env.example`
- `.env.template`
- `README.md`
- `docs/**/*.md`

## Prereqs / Checks
- Confirm `.env` is untracked and ignored:
  - `git ls-files .env || true`
  - `git check-ignore -v .env`

## Command Checklist
1) Preflight:
- `git status --porcelain -uall`

2) Inspect current state (audit-suggested):
- `nl -ba .gitignore | sed -n '8,20p'`
- `nl -ba .env.example | sed -n '1,40p' || true`

3) Implement:
- Ensure `.env.example` and/or `.env.template` exist and contain only placeholder/non-secret values.
- Add/clarify docs (README and/or `docs/`) explaining:
  - `.env` is local-only and must never be shared.
  - `GUARDIAN_API_KEY` rotation guidance (short-lived preferred).
  - `VITE_GUARDIAN_API_KEY` is for strictly local/trusted deployments only; never for public hosting.

4) Verify no secrets in tracked templates/docs:
- `rg -n "(GUARDIAN_API_KEY=|VITE_GUARDIAN_API_KEY=|POSTGRES_PASSWORD=|NEO4J_PASSWORD=)" -S .gitignore .env.example .env.template README.md docs || true`

5) Scope check:
- `git status --porcelain -uall`

## Expected Outputs (success signals)
- `git check-ignore -v .env` shows `.env` is ignored.
- `.env.example`/`.env.template` contain placeholders (no literal keys/passwords).
- `rg` check finds no real secret values in tracked templates/docs (finding matches are either placeholders or explanatory text only).
- `git status --porcelain -uall` shows modifications only within Allowed Files.

## Rollback / Cleanup Commands
- `git restore --source=HEAD --staged --worktree -- .gitignore .env.example .env.template README.md`
- `git restore --source=HEAD --staged --worktree -- docs`
- `git clean -fd`


## Runner Receipt (Start)

- Campaign: CAMPAIGN_2026_02_16_COMPILED_AUDIT

- Task ID: 001

- Head before: 18d87ca5638ea5bab144622c245c14b415f6adf2
