# TASK-2026-02-05-001_remove_env_and_align_templates: remove committed .env and align templates

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-001_remove_env_and_align_templates
Task title: remove committed .env and align templates
Task artifact path: docs/work/tasks/2026/02/TASK_2026_02_05_001_remove_env_and_align_templates.md
Risk: HIGH
Allowed files list:
- .env
- .env.example
- .env.template
- .gitignore
- README.md
Command checklist (exact commands to run):
- git status --porcelain -uall
- git ls-files .env
- rg -n "GUARDIAN_API_KEY|VITE_GUARDIAN_API_KEY|LOCAL_BASE_URL|VAULTNODE_BASE_URL" .env .env.example .env.template
- rg -n "\.env" README.md
- git rm --cached --ignore-unmatch .env
- git status --porcelain -uall
Expected outputs:
- .env is removed from version control and ignored by .gitignore.
- .env.example and .env.template are aligned and contain sanitized placeholders.
- README.md explains local-only .env usage and points to templates.
Rollback/cleanup commands:
- git restore --staged .env
- git checkout -- .env .env.example .env.template .gitignore README.md
Dependencies/Prereqs (commands):
- None.

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-001_remove_env_and_align_templates: remove committed .env and align templates"
Commit B message EXACT:
"TASK-2026-02-05-001_remove_env_and_align_templates: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-001_remove_env_and_align_templates -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add .env .env.example .env.template .gitignore README.md
- git commit --no-verify -m "TASK-2026-02-05-001_remove_env_and_align_templates: remove committed .env and align templates"
- git log -1 --oneline
- git add docs/work/tasks/2026/02/TASK_2026_02_05_001_remove_env_and_align_templates.md docs/work/campaigns/2026/02/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-001_remove_env_and_align_templates: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.

## Summary
- Status: DONE (already satisfied by prior implementation).
- Implementation: c3e306f1 (removed committed .env, aligned templates, README guidance).
- Tests: Not run (no code changes for this task).
