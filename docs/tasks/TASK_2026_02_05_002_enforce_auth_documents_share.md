# TASK-2026-02-05-002_enforce_auth_documents_share: enforce auth on documents and share endpoints

## Task Metadata
Campaign-ID: CAMPAIGN-2026-02-05-CODEXIFY_AUDIT_FOLLOWUP
Task-ID: TASK-2026-02-05-002_enforce_auth_documents_share
Task title: enforce auth on documents and share endpoints
Task artifact path: docs/tasks/TASK_2026_02_05_002_enforce_auth_documents_share.md
Risk: HIGH
Allowed files list:
- guardian/routes/documents.py
- guardian/routes/share.py
- tests/routes/test_documents_autosave.py
- tests/routes/test_share_links.py
- tests/routes/conftest.py
Command checklist (exact commands to run):
- git status --porcelain -uall
- rg -n "require_api_key" guardian/routes/documents.py guardian/routes/share.py
- rg -n "share" tests/routes/test_share_links.py
- python -m pytest tests/routes/test_documents_autosave.py tests/routes/test_share_links.py
- git status --porcelain -uall
Expected outputs:
- Document creation endpoints require API key auth.
- Share-link creation requires API key auth.
- Share retrieval remains token-based only.
- Tests pass or failures are documented in the task summary.
Rollback/cleanup commands:
- git checkout -- guardian/routes/documents.py guardian/routes/share.py tests/routes/test_documents_autosave.py tests/routes/test_share_links.py tests/routes/conftest.py
Dependencies/Prereqs (commands):
- python -m pip install -r requirements.txt

## Commit Plan
Commit A message EXACT:
"TASK-2026-02-05-002_enforce_auth_documents_share: require api key for docs/share"
Commit B message EXACT:
"TASK-2026-02-05-002_enforce_auth_documents_share: docs finalize + mapping"
Campaign mapping format EXACT:
TASK-2026-02-05-002_enforce_auth_documents_share -> [<commitA>, <commitB>]
Manual git commands (explicit file paths):
- git status --porcelain -uall
- git add guardian/routes/documents.py guardian/routes/share.py tests/routes/test_documents_autosave.py tests/routes/test_share_links.py tests/routes/conftest.py
- git commit --no-verify -m "TASK-2026-02-05-002_enforce_auth_documents_share: require api key for docs/share"
- git log -1 --oneline
- git add docs/tasks/TASK_2026_02_05_002_enforce_auth_documents_share.md docs/Campaign/CAMPAIGN_2026_02_05_CODEXIFY_AUDIT_FOLLOWUP.md
- git commit --no-verify -m "TASK-2026-02-05-002_enforce_auth_documents_share: docs finalize + mapping"
- git log -1 --oneline

## Scope Control
- Only modify files in the Allowed files list.
- No mega-tasks; keep changes minimal and observable.
