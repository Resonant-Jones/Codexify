# TASK-2026-02-04-002_security_require_api_key_documents_and_share

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-002_security_require_api_key_documents_and_share

## Title

Require API key for documents + share creation endpoints

## Audit Link / Finding

- FINDING-2026-02-04-012

## Allowed Files List (ONLY)

- guardian/routes/documents.py
- guardian/routes/share.py
- guardian/core/dependencies.py (only if needed to reuse existing dependency)
- guardian/guardian_api.py (only if router wiring must change)
- tests/*or guardian/tests/* (ONLY tests directly related to documents/share auth)
- README.md (ONLY if behavior must be documented)

## Command Checklist

Preflight:

- git status --porcelain -uall

Locate current router dependencies:

- rg -n "APIRouter\\(" guardian/routes/documents.py guardian/routes/share.py
- rg -n "require_api_key" guardian/routes/documents.py guardian/routes/share.py guardian/core/dependencies.py

Implement:

- Ensure create/update actions on documents are protected by API key dependency
- Ensure share-link creation endpoints are protected by API key dependency
- Ensure share retrieval by token remains token-based (do NOT break public-by-token semantics)

Tests:

- rg -n "documents|share" tests guardian/tests || true
- python -m pytest -q (or a targeted subset if suite is large)

Verification:

- Start API (if needed) and confirm 401 without key / 200 with key for protected endpoints.

## Expected Outputs (Success Criteria)

- Protected endpoints return 401/403 when missing API key
- Token-based share retrieval remains functional (as designed)
- Tests updated/added covering auth enforcement

## Rollback / Cleanup Commands

- git restore --staged <paths>
- git restore <paths>

## Dependencies / Prereqs

- Working GUARDIAN_API_KEY in local environment for manual testing (do NOT commit it)
- pytest available for tests

## Commit Plan (MANUAL — Two Phase)

### Commit A message EXACT

"TASK-2026-02-04-002_security_require_api_key_documents_and_share: enforce auth on documents/share"

Commands:

- git status --porcelain -uall
- git add guardian/routes/documents.py guardian/routes/share.py guardian/core/dependencies.py guardian/guardian_api.py tests guardian/tests README.md
- git commit --no-verify -m "TASK-2026-02-04-002_security_require_api_key_documents_and_share: enforce auth on documents/share"
- git log -1 --oneline
Record CommitA=24b6f81b

### Commit B message EXACT

"TASK-2026-02-04-002_security_require_api_key_documents_and_share: finalize task docs and campaign mapping"

Commands:

- git add docs/tasks/TASK_2026_02_04_002_security_require_api_key_documents_and_share.md docs/Campaign/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-002_security_require_api_key_documents_and_share: finalize task docs and campaign mapping"
Record CommitB=<hash>

Campaign mapping update EXACT:

- TASK-2026-02-04-002_security_require_api_key_documents_and_share -> [<commitA>, <commitB>]

## Stop Conditions

- Dirty tree with out-of-scope files => STOP.
