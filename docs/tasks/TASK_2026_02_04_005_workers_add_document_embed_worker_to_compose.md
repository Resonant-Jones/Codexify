# TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose

## Campaign-ID

CAMPAIGN-2026-02-04-CODEXIFY_AUDIT_EXECUTION

## Task-ID

TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose

## Title

Start document-embed worker in docker-compose so embeddings complete

## Audit Link / Finding

- FINDING-2026-02-04-005

## Allowed Files List (ONLY)

- docker-compose.yml
- guardian/workers/document_embed_worker.py (only if entrypoint/args need changes)
- README.md (document how worker is started)
- tests/*or guardian/tests/* (only if adding a targeted verification test)

## Command Checklist

Preflight:

- git status --porcelain -uall

Confirm worker exists and compose lacks it:

- rg -n "document_embed" docker-compose.yml
- ls -la guardian/workers/document_embed_worker.py
- rg -n "class|main|if __name__" guardian/workers/document_embed_worker.py

Implement:

- Add a compose service for document embedding worker (or an equivalent mechanism)
- Ensure it uses the same env/redis/postgres wiring as other workers

Verify:

- docker compose up -d --build
- Upload a document through API/UI
- Confirm embedding tasks transition to ready (define exact observation: logs, DB status, or endpoint response)

## Expected Outputs (Success Criteria)

- Compose includes a running document embed worker container
- Embedding jobs complete in default stack (not indefinitely queued)

## Rollback / Cleanup Commands

- docker compose down
- git restore --staged docker-compose.yml
- git restore docker-compose.yml

## Dependencies / Prereqs

- Docker Desktop
- Redis + Postgres services in compose
- Embedding backend config present (LOCAL_EMBED_MODEL or OpenAI embeddings config)

## Commit Plan (MANUAL — Two Phase)

### Commit A message EXACT

"TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose: run embed worker in compose"

Commands:

- git add docker-compose.yml guardian/workers/document_embed_worker.py README.md tests guardian/tests
- git commit --no-verify -m "TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose: run embed worker in compose"
Record CommitA=<hash>

### Docs Commit message EXACT

"TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose: finalize task docs and campaign mapping"

Commands:

- git add docs/tasks/TASK_2026_02_04_005_workers_add_document_embed_worker_to_compose.md docs/Campaign/CAMPAIGN_2026_02_04_CODEXIFY_AUDIT_EXECUTION.md
- git commit --no-verify -m "TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose: finalize task docs and campaign mapping"
Record DocsCommit=<hash>

Campaign mapping update EXACT:

- TASK-2026-02-04-005_workers_add_document_embed_worker_to_compose -> [<commitA>] DocsCommit=<docsCommit>

## Stop Conditions

- Dirty tree with out-of-scope files => STOP.
