# TASK-2026-02-05-006_rag_upload_endpoint_resolution: resolve rag upload endpoint status

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-006_rag_upload_endpoint_resolution
Task title: resolve rag upload endpoint status
Task artifact path: docs/tasks/TASK_2026_02_05_006_rag_upload_endpoint_resolution.md
Risk: MED
Allowed files list:
- guardian/routes/rag_upload.py
- guardian/guardian_api.py
- README.md
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "rag_upload|upload-chat" guardian/guardian_api.py guardian/routes/rag_upload.py
- rg -n "upload-chat" README.md
- printf "No tests required for this task.\n"
- git status --porcelain -uall
Expected outputs:
- The rag upload endpoint is either explicitly wired and functional or explicitly removed and documented.
- README.md reflects the chosen state with no ambiguity.
Rollback/cleanup commands:
- git checkout -- guardian/routes/rag_upload.py guardian/guardian_api.py README.md
Dependencies/Prereqs (commands):
- None.

## Decision
Option A: Implement the missing module and wire the endpoint.
Option B (chosen): Remove or disable the unused endpoint and document the lack of support.

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-006_rag_upload_endpoint_resolution: resolve rag upload endpoint"
Commit B message EXACT:
"TASK-2026-02-05-006_rag_upload_endpoint_resolution: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-006_rag_upload_endpoint_resolution -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add guardian/routes/rag_upload.py guardian/guardian_api.py README.md
- git commit --no-verify -m "TASK-2026-02-05-006_rag_upload_endpoint_resolution: resolve rag upload endpoint"
- git log -1 --oneline
- git add docs/tasks/TASK_2026_02_05_006_rag_upload_endpoint_resolution.md docs/Campaign/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-006_rag_upload_endpoint_resolution: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.
