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


## Completion Summary (Runner)

- Status: success

- Summary: Locked down env templates and docs so `VITE_GUARDIAN_API_KEY` stays local-only and tracked files contain placeholders only.

- Implementation commit hash: c48d3adc2cbe33610fa45516525c8fcbbbe71fc1

- Receipt update commit hash: a6a7d9a5e4ef495eed8669c201d3e3b05071e6d7

- Tests ran: git ls-files .env, git check-ignore -v .env, . "rg -n \"(GUARDIAN_API_KEY=|VITE_GUARDIAN_API_KEY=|POSTGRES_PASSWORD=|NEO4J_PASSWORD=)\" -S .gitignore .env.example .env.template README.md docs || true", . "git status --porcelain -uall"

- Notes: **Env Guardrails**
- `.env.template:1` and `.env.example:1` now start with an explicit security banner, swap in placeholder-only secrets (`GUARDIAN_API_KEY=dev-local-only-change-me` at lines 21 and `POSTGRES_PASSWORD=replace-with-postgres-password` at lines 38-40), and leave `VITE_GUARDIAN_API_KEY` blank with instructions to mirror the backend key only on localhost.

**Docs & Warnings**
- `README.md:75` adds an “Env Security Guardrails” block spelling out that `.env` stays untracked, `GUARDIAN_API_KEY` must be rotated, and `VITE_GUARDIAN_API_KEY` cannot ship on hosted deployments (pointing to the remote auth boundary doc).
- `docs/infra/dev-setup.md:60` now explicitly states “Never ship or publish the value of VITE_GUARDIAN_API_KEY” and ties remote deployments to `GUARDIAN_AUTH_MODE=remote`/session auth so the warning shows up in the canonical env workflow doc.

**Secrets Scrubbed**
- Replaced the literal 64-hex `GUARDIAN_API_KEY` in `docs/MVP ROADMAP/codexify-mvp-roadmap.md:1475` with `<dev-local-api-key>`.
- Sanitized the historical verification note in `docs/tasks/TASK_2026_01_17_002_frontend_env_file.md:65` so it references `<dev-only-same-as-backend>` instead of a real token.

**Checks**
- `git ls-files .env` (empty) and `git check-ignore -v .env` → `.gitignore:12` confirmed `.env` stays ignored; re-ran `git status --porcelain -uall` pre/post to satisfy the STOP condition (only allowed files are touched).
- Executed the mandated `rg -n "(GUARDIAN_API_KEY=|VITE_GUARDIAN_API_KEY=|POSTGRES_PASSWORD=|NEO4J_PASSWORD=)" -S .gitignore .env.example .env.template README.md docs || true`, yielding only placeholder values after the scrub.

**Next Steps**
1. Rotate any real `GUARDIAN_API_KEY`/`VITE_GUARDIAN_API_KEY` values already in circulation so the newly documented hygiene is enforced operationally.
2. If you host Codexify anywhere public, flip `GUARDIAN_AUTH_MODE=remote` and wire session/JWT issuance before exposing the UI.

<details>
<summary>Structured task_result.json</summary>

```json
{
  "status": "success",
  "summary": "Locked down env templates and docs so `VITE_GUARDIAN_API_KEY` stays local-only and tracked files contain placeholders only.",
  "tests_ran": [
    "git ls-files .env",
    "git check-ignore -v .env",
    ". \"rg -n \\\"(GUARDIAN_API_KEY=|VITE_GUARDIAN_API_KEY=|POSTGRES_PASSWORD=|NEO4J_PASSWORD=)\\\" -S .gitignore .env.example .env.template README.md docs || true\"",
    ". \"git status --porcelain -uall\""
  ],
  "commit_hash": "c48d3adc2cbe33610fa45516525c8fcbbbe71fc1",
  "implementation_commit_hash": "c48d3adc2cbe33610fa45516525c8fcbbbe71fc1",
  "receipt_update_commit_hash": "a6a7d9a5e4ef495eed8669c201d3e3b05071e6d7",
  "notes": "**Env Guardrails**\n- `.env.template:1` and `.env.example:1` now start with an explicit security banner, swap in placeholder-only secrets (`GUARDIAN_API_KEY=dev-local-only-change-me` at lines 21 and `POSTGRES_PASSWORD=replace-with-postgres-password` at lines 38-40), and leave `VITE_GUARDIAN_API_KEY` blank with instructions to mirror the backend key only on localhost.\n\n**Docs & Warnings**\n- `README.md:75` adds an \u201cEnv Security Guardrails\u201d block spelling out that `.env` stays untracked, `GUARDIAN_API_KEY` must be rotated, and `VITE_GUARDIAN_API_KEY` cannot ship on hosted deployments (pointing to the remote auth boundary doc).\n- `docs/infra/dev-setup.md:60` now explicitly states \u201cNever ship or publish the value of VITE_GUARDIAN_API_KEY\u201d and ties remote deployments to `GUARDIAN_AUTH_MODE=remote`/session auth so the warning shows up in the canonical env workflow doc.\n\n**Secrets Scrubbed**\n- Replaced the literal 64-hex `GUARDIAN_API_KEY` in `docs/MVP ROADMAP/codexify-mvp-roadmap.md:1475` with `<dev-local-api-key>`.\n- Sanitized the historical verification note in `docs/tasks/TASK_2026_01_17_002_frontend_env_file.md:65` so it references `<dev-only-same-as-backend>` instead of a real token.\n\n**Checks**\n- `git ls-files .env` (empty) and `git check-ignore -v .env` \u2192 `.gitignore:12` confirmed `.env` stays ignored; re-ran `git status --porcelain -uall` pre/post to satisfy the STOP condition (only allowed files are touched).\n- Executed the mandated `rg -n \"(GUARDIAN_API_KEY=|VITE_GUARDIAN_API_KEY=|POSTGRES_PASSWORD=|NEO4J_PASSWORD=)\" -S .gitignore .env.example .env.template README.md docs || true`, yielding only placeholder values after the scrub.\n\n**Next Steps**\n1. Rotate any real `GUARDIAN_API_KEY`/`VITE_GUARDIAN_API_KEY` values already in circulation so the newly documented hygiene is enforced operationally.\n2. If you host Codexify anywhere public, flip `GUARDIAN_AUTH_MODE=remote` and wire session/JWT issuance before exposing the UI."
}
```

</details>
