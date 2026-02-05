# TASK-2026-02-05-008_image_gen_placeholder_handling: handle placeholder image providers

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-008_image_gen_placeholder_handling
Task title: handle placeholder image providers
Task artifact path: docs/tasks/TASK_2026_02_05_008_image_gen_placeholder_handling.md
Risk: MED
Allowed files list:
- guardian/image_gen/providers/local.py
- guardian/image_gen/providers/stability.py
- guardian/routes/image_gen.py
- tests/routes/test_media_routes.py
- README.md
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "_PLACEHOLDER_PNG_BASE64" guardian/image_gen/providers
- python -m pytest tests/routes/test_media_routes.py
- git status --porcelain -uall
Expected outputs:
- Local and Stability providers return an explicit error or are gated when not configured.
- README.md documents provider configuration and limitations.
- Tests pass or failures are documented in the task summary.
Rollback/cleanup commands:
- git checkout -- guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py guardian/routes/image_gen.py tests/routes/test_media_routes.py README.md
Dependencies/Prereqs (commands):
- python -m pip install -r requirements.txt

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-008_image_gen_placeholder_handling: gate placeholder providers"
Commit B message EXACT:
"TASK-2026-02-05-008_image_gen_placeholder_handling: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-008_image_gen_placeholder_handling -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add guardian/image_gen/providers/local.py guardian/image_gen/providers/stability.py guardian/routes/image_gen.py tests/routes/test_media_routes.py README.md
- git commit --no-verify -m "TASK-2026-02-05-008_image_gen_placeholder_handling: gate placeholder providers"
- git log -1 --oneline
- git add docs/tasks/TASK_2026_02_05_008_image_gen_placeholder_handling.md docs/Campaign/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-008_image_gen_placeholder_handling: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.
