# TASK-2026-02-04-001_secrets_untrack_env_and_align_templates

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-001_secrets_untrack_env_and_align_templates

## Title

Untrack committed .env, rotate local secrets, align env templates

## Audit Link / Finding

- FINDING-2026-02-04-001

## Allowed Files List (ONLY)

- .gitignore
- .env.example
- .env.template
- README.md
- (git index only) remove `.env` from tracking (no content edits to `.env` in git history beyond untracking)

## Command Checklist

Preflight:

- git status --porcelain -uall
- git ls-files .env || true

Implementation (untrack + ignore):

- git rm --cached .env
- printf "\n# local env files\n.env\n" >> .gitignore

Template alignment:

- diff -u .env.example .env.template || true
- rg -n "GUARDIAN_API_KEY|VITE_GUARDIAN_API_KEY|LOCAL_BASE_URL|VAULTNODE_BASE_URL" .env.example .env.template README.md || true
- Edit .env.example + .env.template so they:
  - do NOT contain real keys
  - contain consistent variable sets
  - contain safe placeholder values

Docs:

- Update README to explain:
  - `.env` is local-only and must never be committed
  - templates are the source of truth

Verification:

- git status --porcelain -uall
- git check-ignore -v .env || true

## Expected Outputs (Success Criteria)

- `git ls-files .env` produces no output (file no longer tracked)
- `.env` appears in `.gitignore`
- `.env.example` and `.env.template` are aligned (diff is empty or intentional + documented)
- README explicitly states `.env` must not be committed

## Rollback / Cleanup Commands

- If you accidentally modified/created out-of-scope files:
  - git restore --staged <path>
  - git restore <path>
- If you need to undo untracking:
  - git reset HEAD -- .env
  - git checkout -- .env

## Dependencies / Prereqs

- none (git + ripgrep assumed)

## Commit Plan (MANUAL — Two Phase)

### Commit A (implementation/config)

Commit A message EXACT:

- "TASK-2026-02-04-001_secrets_untrack_env_and_align_templates: untrack .env and sanitize templates"

Commands:

- git status --porcelain -uall
- git add .gitignore .env.example .env.template README.md
- git rm --cached .env
- git status --porcelain -uall
- git commit --no-verify -m "TASK-2026-02-04-001_secrets_untrack_env_and_align_templates: untrack .env and sanitize templates"
- git log -1 --oneline

Record:

- CommitA=c3e306f1
- DocsCommit=a3f54735

### Docs Commit (docs finalize: task artifact + campaign mapping)

Docs Commit message EXACT:

- "TASK-2026-02-04-001_secrets_untrack_env_and_align_templates: finalize task docs and campaign mapping"

Commands:

- git add docs/tasks/TASK_2026_02_04_001_secrets_untrack_env_and_align_templates.md docs/Campaign/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-001_secrets_untrack_env_and_align_templates: finalize task docs and campaign mapping"
- git log -1 --oneline

Campaign mapping update EXACT:

- TASK-2026-02-04-001_secrets_untrack_env_and_align_templates -> [<commitA>] DocsCommit=<docsCommit>

## Stop Conditions

- If git status shows out-of-scope files, STOP and revert/remove them first.
