# TASK-2026-02-05-005_wire_document_embed_worker: wire document embed worker in compose

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-005_wire_document_embed_worker
Task title: wire document embed worker in compose
Task artifact path: docs/tasks/TASK_2026_02_05_005_wire_document_embed_worker.md
Risk: HIGH
Allowed files list:
- docker-compose.yml
- README.md
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "document_embed|document-embed" docker-compose.yml guardian/workers/document_embed_worker.py
- docker compose config
- git status --porcelain -uall
Expected outputs:
- docker-compose.yml defines a document-embed worker service.
- README.md documents how to run the worker and required env vars.
- docker compose config exits 0.
Rollback/cleanup commands:
- git checkout -- docker-compose.yml README.md
Dependencies/Prereqs (commands):
- docker compose version

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-005_wire_document_embed_worker: add document embed worker service"
Commit B message EXACT:
"TASK-2026-02-05-005_wire_document_embed_worker: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-005_wire_document_embed_worker -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add docker-compose.yml README.md
- git commit --no-verify -m "TASK-2026-02-05-005_wire_document_embed_worker: add document embed worker service"
- git log -1 --oneline
- git add docs/tasks/TASK_2026_02_05_005_wire_document_embed_worker.md docs/Campaign/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-005_wire_document_embed_worker: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.
