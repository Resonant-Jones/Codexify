docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md

# CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP

**Date**: 2026-01-23  
**Repo**: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify  
**Branch**: chore/post-skip-hook-fixes  
**Source audit**: docs/reports/audit-mvp-codexify-2026-01-23.md  
**Commit mode**: Manual commits only (index.lock may block)  
**Two-phase protocol**:

- Commit A: implementation/test/config changes
- Commit B: docs finalize (task artifact + campaign mapping update)

## Purpose

Close the remaining **CORE LOOP** gaps called out in the audit:

- Secrets hygiene in docker-compose (env-driven, no hardcoded secrets)
- Confirm/implement embeddings endpoint used by frontend uploader
- Implement reliable document embedding pipeline with status tracking
- Wire Image Generation UI to backend endpoint
- Wire Document Generation UI to backend endpoint
- Verify memory store initialization + add context broker integration test
- Make an explicit decision on graph context (Neo4j) for CORE LOOP scope
- (Optional) tighten docs drift if still relevant after CORE LOOP closure

## Rules / Guardrails (Runner Protocol enforcement)

- Stop immediately if `git status --porcelain -uall` is dirty with **out-of-scope** files.
- Never expand Allowed Files without creating a campaign task to do so.
- If Playwright or other tooling generates reports/artifacts, **revert/remove them immediately** before proceeding.
- Always provide explicit manual commit commands and request hashes.
- Never “decide later”: decisions become tasks with explicit outcomes.

---

## Task List (execute in order)

### TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE

Goal: Remove hardcoded secrets from docker-compose and enforce env-driven configuration.

- Task artifact: `docs/tasks/TASK_2026_01_23_001_secrets_docker_compose_hygiene.md`
- Task mapping: `TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT

Goal: Verify `/api/embeddings` exists and matches frontend expectations; implement/fix if missing.

- Task artifact: `docs/tasks/TASK_2026_01_23_002_verify_or_implement_embeddings_endpoint.md`
- Task mapping: `TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN

Goal: Add embedding status tracking to `UploadedDocument` (DB + migrations).

- Task artifact: `docs/tasks/TASK_2026_01_23_003_add_document_embedding_status_column.md`
- Task mapping: `TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER

Goal: Replace fire-and-forget embedding with a reliable queue/worker pipeline and status transitions.

- Task artifact: `docs/tasks/TASK_2026_01_23_004_document_embed_pipeline_worker.md`
- Task mapping: `TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR

Goal: Expose embedding status in the Documents UI (and ensure the backend list payload contains it).

- Task artifact: `docs/tasks/TASK_2026_01_23_005_documents_ui_embed_status_indicator.md`
- Task mapping: `TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING

Goal: Create ImageGenModal + add “Generate Image” button and wire to POST `/api/media/generate/image`.

- Task artifact: `docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md`
- Task mapping: `TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING

Goal: Add “Generate Document” button in Documents view and wire DocumentGenModal submit to POST `/api/documents/generate`.

- Task artifact: `docs/tasks/TASK_2026_01_23_007_document_gen_ui_button_and_submit_wiring.md`
- Task mapping: `TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS

Goal: Add doc_type selector (code/literature/diagram) + emit/update UI events to refresh documents list.

- Task artifact: `docs/tasks/TASK_2026_01_23_008_document_gen_add_doc_type_and_events.md`
- Task mapping: `TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT

Goal: Verify memory store initialization in dependencies and fix wiring if needed.

- Task artifact: `docs/tasks/TASK_2026_01_23_009_verify_memory_store_init.md`
- Task mapping: `TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST

Goal: Add an integration test confirming context broker assembly works end-to-end with a representative query.

- Task artifact: `docs/tasks/TASK_2026_01_23_010_context_broker_integration_test.md`
- Task mapping: `TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST -> [<commitA>, <commitB>]`

---

### TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT

Goal: Make an explicit CORE LOOP decision on graph context (Neo4j) and reflect it in code/docs.

- Task artifact: `docs/tasks/TASK_2026_01_23_011_decision_defer_graph_context.md`
- Task mapping: `TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT -> [<commitA>, <commitB>]`

---

### (Optional) TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP

Goal: Clean up any remaining README/docs claims that conflict with actual CORE LOOP behavior.

- Task artifact: `docs/tasks/TASK_2026_01_23_012_docs_drift_cleanup_core_loop.md`
- Task mapping: `TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP -> [<commitA>, <commitB>]`

⸻

TASK artifact drafts

1) docs/tasks/TASK_2026_01_23_001_secrets_docker_compose_hygiene.md

# TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_001_secrets_docker_compose_hygiene.md

## Goal

Remove any hardcoded secrets from `docker-compose.yml` and ensure secrets are env-driven (or Docker secrets if already used), consistent with “local-first but not careless” CORE LOOP hygiene.

## Allowed Files (strict)

- docker-compose.yml
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_001_secrets_docker_compose_hygiene.md
- (Optional docs-only if needed): docs/*.md

## Command Checklist (exact)

### Preconditions

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

Discovery

rg -n "GUARDIAN_API_KEY|OPENAI_API_KEY|GROQ_API_KEY|ANTHROPIC_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD|POSTGRES_USER|REDIS_PASSWORD" docker-compose.yml

Apply fix (implementation step)
 • Replace hardcoded values with env interpolation patterns (e.g. "${VAR_NAME:-}"), OR reference .env-provided values.
 • Ensure defaults are safe (avoid codexify password default for prod; ok to keep a clearly-labeled dev default if policy allows).

Validate

rg -n "GUARDIAN_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD" docker-compose.yml
docker compose config >/tmp/codexify.compose.rendered.txt
rg -n "GUARDIAN_API_KEY|NEO4J_PASSWORD|POSTGRES_PASSWORD" /tmp/codexify.compose.rendered.txt || true

Expected Outputs (success criteria)
 • rg shows no plaintext secret literals committed in compose (e.g., no 64-hex guardian key hardcoded).
 • docker compose config renders without errors.
 • Repo remains functional in dev: compose still supports .env or environment injection.

Rollback / Cleanup

git checkout -- docker-compose.yml
rm -f /tmp/codexify.compose.rendered.txt

Dependencies / Prereqs
 • Docker Compose available (docker compose version works).
 • Secrets provided via environment or .env (gitignored).

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE: remove hardcoded secrets

Manual commands:

git status --porcelain -uall
git add docker-compose.yml
git commit -m "TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE: remove hardcoded secrets"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_001_secrets_docker_compose_hygiene.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

In the campaign file, set:
TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE_HYGIENE -> [<commitA>, <commitB>]

Notes

If any tooling produces out-of-scope artifacts (reports/logs), revert/remove them immediately before commits.

---

## 2) `docs/tasks/TASK_2026_01_23_002_verify_or_implement_embeddings_endpoint.md`

```md
# TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_002_verify_or_implement_embeddings_endpoint.md

## Goal

Confirm `/api/embeddings` exists and behaves as expected by `frontend/src/hooks/useUploader.ts` (document upload embedding call). If missing or mismatched, implement/fix it.

## Allowed Files (strict)

- guardian/routes/**/*.py
- guardian/guardian_api.py (or the single authoritative FastAPI wiring file used)
- backend/rag/embedder.py (only if needed for request/response adaptation)
- guardian/vector/store.py (only if needed)
- guardian/tests/**/*.py
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_002_verify_or_implement_embeddings_endpoint.md
- (Optional) frontend/src/hooks/useUploader.ts (only if the endpoint contract must be aligned)

## Command Checklist (exact)

### Preconditions
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

Locate frontend usage + backend route

rg -n "/api/embeddings|embeddings" frontend/src/hooks/useUploader.ts
rg -n "api/embeddings|/embeddings|Embeddings" guardian/routes guardian/guardian_api.py backend | head -n 200

Verify via OpenAPI (if backend running)

# If stack is already running:
curl -s http://localhost:8888/openapi.json | rg -n "\"/api/embeddings\"" -n || true

Minimal endpoint verification (if endpoint exists)

# Replace payload keys to match actual contract once discovered
curl -s -X POST http://localhost:8888/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"texts":["hello world"],"namespace":"test","metadata":{"source":"task-002"}}' | head -n 60

Expected Outputs (success criteria)
 • There is a reachable POST endpoint at /api/embeddings (or an explicitly documented replacement that the frontend uses).
 • The endpoint returns a 2xx response and persists embeddings to the configured vector store.
 • Contract is documented in this task artifact (request + response shape).

Rollback / Cleanup

git checkout -- guardian/routes guardian/guardian_api.py backend/rag/embedder.py guardian/vector/store.py frontend/src/hooks/useUploader.ts

Dependencies / Prereqs
 • Backend runnable locally (docker-compose or uvicorn).
 • Vector store configured (Chroma/PGVector/FAISS) and embedder available.

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT: ensure embeddings endpoint exists

Manual commands:

git status --porcelain -uall
git add \
  guardian/routes \
  guardian/guardian_api.py \
  backend/rag/embedder.py \
  guardian/vector/store.py \
  guardian/tests \
  frontend/src/hooks/useUploader.ts
git commit -m "TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT: ensure embeddings endpoint exists"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_002_verify_or_implement_embeddings_endpoint.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-002_VERIFY_OR_IMPLEMENT_EMBEDDINGS_ENDPOINT -> [<commitA>, <commitB>]

---

## 3) `docs/tasks/TASK_2026_01_23_003_add_document_embedding_status_column.md`

```md
# TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_003_add_document_embedding_status_column.md

## Goal

Add durable embedding status tracking to `UploadedDocument` so the UI and pipeline can reflect:
- pending / processing / ready / failed (exact enum decided in-task and documented).

## Allowed Files (strict)

- guardian/db/models.py
- backend/migrations/versions/*.py
- guardian/routes/media.py (only if required to set initial status)
- guardian/tests/**/*.py (optional)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_003_add_document_embedding_status_column.md

## Command Checklist (exact)

### Preconditions
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

Inspect model + existing migrations

rg -n "class UploadedDocument|UploadedDocument" guardian/db/models.py
ls -1 backend/migrations/versions | tail -n 20

Create migration (alembic workflow must match repo)

# Use the repo’s standard migration command (examples; choose the one that exists):
rg -n "alembic|migrations" Makefile README.md pyproject.toml

Validate schema locally (choose one path that exists)

# Option A: if compose runs migrations service
docker compose up -d postgres
# then run the project’s migration command (document the exact command used)

# Option B: if alembic is available directly
# alembic upgrade head

Expected Outputs (success criteria)
 • UploadedDocument includes a persisted status field (documented in this task).
 • A migration exists and applies cleanly.
 • New uploads can set status to an initial value (e.g., pending) deterministically.

Rollback / Cleanup

git checkout -- guardian/db/models.py
git checkout -- backend/migrations/versions

Dependencies / Prereqs
 • Database migrations are the authoritative schema mechanism (Alembic).
 • Local DB available for migration validation.

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN: add embedding status to uploaded documents

Manual commands:

git status --porcelain -uall
git add guardian/db/models.py backend/migrations/versions
git commit -m "TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN: add embedding status to uploaded documents"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_003_add_document_embedding_status_column.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-003_ADD_DOCUMENT_EMBEDDING_STATUS_COLUMN -> [<commitA>, <commitB>]

---

## 4) `docs/tasks/TASK_2026_01_23_004_document_embed_pipeline_worker.md`

```md
# TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_004_document_embed_pipeline_worker.md

## Goal

Implement a reliable document embedding pipeline:
- Upload sets embedding_status to `pending`
- A worker consumes jobs and transitions status through `processing` → `ready` or `failed`
- Failures are recorded deterministically and visible to UI

This replaces “best-effort fire-and-forget” behavior.

## Allowed Files (strict)

- guardian/routes/media.py
- guardian/workers/*.py
- guardian/queue/**/*.py
- guardian/db/models.py (only if needed beyond Task 003)
- backend/rag/embedder.py (only if needed)
- guardian/vector/store.py (only if needed)
- guardian/tests/**/*.py
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_004_document_embed_pipeline_worker.md

## Command Checklist (exact)

### Preconditions
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

Inspect existing queue/workers patterns

ls -1 guardian/workers || true
rg -n "enqueue|Redis|queue|worker" guardian/queue guardian/workers guardian/routes | head -n 200

Verify upload flow

rg -n "upload_document|/api/media/upload/document|UploadedDocument" guardian/routes/media.py frontend/src/hooks/useUploader.ts

Run targeted backend tests

# choose the project’s test invocation that exists:
rg -n "pytest" Makefile README.md pyproject.toml
# then run the relevant tests, e.g.:
# pytest -q guardian/tests/test_document_*.py

Out-of-scope artifact prevention

If any test/e2e tooling produces artifacts:

git status --porcelain -uall
# revert/remove any generated reports/artifacts NOT in allowed files

Expected Outputs (success criteria)
 • A worker exists that can embed document text deterministically.
 • Upload triggers queueing (or explicit endpoint triggers queueing).
 • Status transitions are observable in DB and returned by relevant APIs.
 • At least one automated test validates the pipeline behavior.

Rollback / Cleanup

git checkout -- guardian/routes/media.py
git checkout -- guardian/workers
git checkout -- guardian/queue
git checkout -- backend/rag/embedder.py guardian/vector/store.py

Dependencies / Prereqs
 • Redis queue is available (or whatever queue backend is used in repo).
 • Embedder can run locally (SentenceTransformers model available).

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER: add document embedding worker pipeline

Manual commands:

git status --porcelain -uall
git add \
  guardian/routes/media.py \
  guardian/workers \
  guardian/queue \
  guardian/tests \
  backend/rag/embedder.py \
  guardian/vector/store.py
git commit -m "TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER: add document embedding worker pipeline"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_004_document_embed_pipeline_worker.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-004_DOCUMENT_EMBED_PIPELINE_WORKER -> [<commitA>, <commitB>]

---

## 5) `docs/tasks/TASK_2026_01_23_005_documents_ui_embed_status_indicator.md`

```md
# TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_005_documents_ui_embed_status_indicator.md

## Goal

Show document embedding readiness in the Documents UI so users know whether the document is usable for RAG:
- “Processing…”
- “Ready”
- “Failed” (with a short hint)

## Allowed Files (strict)

- frontend/src/components/documents/**/*.tsx
- frontend/src/hooks/**/*.ts
- guardian/routes/media.py (only if list payload lacks status)
- guardian/db/models.py (only if serialization needs adjustment)
- frontend/src/tests/**/*.ts(x) (optional)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_005_documents_ui_embed_status_indicator.md

## Command Checklist (exact)

### Preconditions
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

Inspect documents UI + API responses

rg -n "DocumentsView|DocumentTile|UploadedDocument|embedding" frontend/src/components/documents -S
rg -n "/api/media|documents|upload/document" frontend/src/hooks -S
rg -n "list.*documents|GET.*documents|UploadedDocument" guardian/routes/media.py -S

Run checks (choose what exists)

# frontend typecheck/lint (use existing scripts)
rg -n "\"type-check\"|\"lint\"|vitest|playwright" frontend/src/package.json
# then run the relevant command(s), e.g.:
# pnpm --dir frontend/src type-check
# pnpm --dir frontend/src lint

Expected Outputs (success criteria)
 • A visible status indicator exists for each document tile/card.
 • Newly uploaded docs start at pending/processing then become ready after pipeline completes.
 • No new out-of-scope artifacts are committed (ignore reports, test-results, etc.).

Rollback / Cleanup

git checkout -- frontend/src/components/documents frontend/src/hooks

Dependencies / Prereqs
 • Backend exposes embedding_status in the documents listing response (or a per-doc status endpoint exists).

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR: show document embedding status in UI

Manual commands:

git status --porcelain -uall
git add \
  frontend/src/components/documents \
  frontend/src/hooks \
  guardian/routes/media.py \
  guardian/db/models.py \
  frontend/src/tests
git commit -m "TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR: show document embedding status in UI"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_005_documents_ui_embed_status_indicator.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-005_DOCUMENTS_UI_EMBED_STATUS_INDICATOR -> [<commitA>, <commitB>]

---

## 6) `docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md`

```md
# TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md

## Goal

Close the Image Generation core loop by adding:
- A “Generate Image” button in Gallery
- An ImageGenModal with prompt + model selection
- Wiring to POST `/api/media/generate/image`
- UI feedback (loading/error) and add generated image to the gallery grid

## Allowed Files (strict)

- frontend/src/components/gallery/GalleryView.tsx
- frontend/src/components/modals/*.tsx
- frontend/src/lib/**/*.ts (if there’s a centralized API client)
- frontend/src/tests/**/*.ts(x) (optional)
- guardian/routes/media.py (only if endpoint payload/response needs alignment)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md

## Command Checklist (exact)

### Preconditions
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

Locate endpoint + current Gallery UI

rg -n "/api/media/generate/image|generate_image" guardian/routes/media.py
rg -n "GalleryView|Generate" frontend/src/components/gallery/GalleryView.tsx
ls -1 frontend/src/components/modals || true

Run UI checks (choose what exists)

rg -n "\"type-check\"|\"lint\"|vitest" frontend/src/package.json
# run the matching commands, e.g.:
# pnpm --dir frontend/src type-check
# pnpm --dir frontend/src lint

Out-of-scope artifact discipline

If Playwright/Vitest generates any artifacts:

git status --porcelain -uall
# revert/remove any generated reports/artifacts NOT in allowed files

Expected Outputs (success criteria)
 • Gallery shows a “Generate Image” action that opens a modal.
 • Submitting the modal calls the backend and adds the returned image to UI state.
 • Errors are shown in-modal (no silent failure).
 • No generated reports committed.

Rollback / Cleanup

git checkout -- frontend/src/components/gallery/GalleryView.tsx
git checkout -- frontend/src/components/modals

Dependencies / Prereqs
 • Backend endpoint /api/media/generate/image is present and reachable.
 • Provider configured (even if mocked in dev).

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: add image generation modal and gallery trigger

Manual commands:

git status --porcelain -uall
git add \
  frontend/src/components/gallery/GalleryView.tsx \
  frontend/src/components/modals \
  frontend/src/lib \
  frontend/src/tests \
  guardian/routes/media.py
git commit -m "TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: add image generation modal and gallery trigger"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING -> [<commitA>, <commitB>]

---

## 7) `docs/tasks/TASK_2026_01_23_007_document_gen_ui_button_and_submit_wiring.md`

```md
# TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_007_document_gen_ui_button_and_submit_wiring.md

## Goal

Close the “Generate Documents” loop at minimum:
- Add “Generate Document” button in Documents view
- Wire `DocumentGenModal` submit to POST `/api/documents/generate`
- Show success/failure and add the new document into the list view

## Allowed Files (strict)

- frontend/src/components/documents/DocumentsView.tsx
- frontend/src/components/DocumentGenModal.tsx
- frontend/src/lib/**/*.ts (if API client used)
- guardian/routes/documents.py (only if response contract adjustment needed)
- frontend/src/tests/**/*.ts(x) (optional)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_007_document_gen_ui_button_and_submit_wiring.md

## Command Checklist (exact)

### Preconditions
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

Locate modal + documents view + endpoint

rg -n "DocumentGenModal" frontend/src/components -S
rg -n "DocumentsView" frontend/src/components/documents/DocumentsView.tsx
rg -n "/api/documents/generate|generate" guardian/routes/documents.py

Optional manual verification (if backend running)

curl -s -X POST http://localhost:8888/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Write a 5-line poem about databases","format":"markdown","title":"DB Poem"}' | head -n 80

Run UI checks (choose what exists)

rg -n "\"type-check\"|\"lint\"" frontend/src/package.json
# run the relevant commands, e.g.:
# pnpm --dir frontend/src type-check
# pnpm --dir frontend/src lint

Expected Outputs (success criteria)
 • Documents view exposes a “Generate Document” action.
 • Submitting the modal calls /api/documents/generate and results in a new document visible in the UI.
 • Failure cases surface an error message (no silent no-op submit).

Rollback / Cleanup

git checkout -- frontend/src/components/documents/DocumentsView.tsx
git checkout -- frontend/src/components/DocumentGenModal.tsx

Dependencies / Prereqs
 • Backend endpoint /api/documents/generate present and reachable.
 • At least one LLM provider configured for the environment (or a safe local fallback).

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING: wire document generation modal

Manual commands:

git status --porcelain -uall
git add \
  frontend/src/components/documents/DocumentsView.tsx \
  frontend/src/components/DocumentGenModal.tsx \
  frontend/src/lib \
  frontend/src/tests \
  guardian/routes/documents.py
git commit -m "TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING: wire document generation modal"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_007_document_gen_ui_button_and_submit_wiring.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-007_DOCUMENT_GEN_UI_BUTTON_AND_SUBMIT_WIRING -> [<commitA>, <commitB>]

---

## 8) `docs/tasks/TASK_2026_01_23_008_document_gen_add_doc_type_and_events.md`

```md
# TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_008_document_gen_add_doc_type_and_events.md

## Goal

Add the missing product ergonomics to document generation:
- doc_type selector: code / literature / diagram
- event emission or refetch so documents list refreshes immediately after generation

## Allowed Files (strict)

- frontend/src/components/DocumentGenModal.tsx
- frontend/src/components/documents/**/*.tsx (only if event wiring is here)
- guardian/routes/documents.py (only if doc_type contract needs alignment)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_008_document_gen_add_doc_type_and_events.md

## Command Checklist (exact)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
rg -n "doc_type|diagram|mermaid|code|literature" frontend/src/components/DocumentGenModal.tsx guardian/routes/documents.py -S

Expected Outputs (success criteria)
 • Modal includes doc_type selector with explicit options.
 • Payload includes doc_type (or maps to backend contract).
 • After generation, documents list refreshes (event or refetch) with no manual reload.

Rollback / Cleanup

git checkout -- frontend/src/components/DocumentGenModal.tsx
git checkout -- frontend/src/components/documents

Dependencies / Prereqs
 • Task 007 completed (modal submit wiring exists).

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS: add doc type selector and refresh events

Manual commands:

git status --porcelain -uall
git add \
  frontend/src/components/DocumentGenModal.tsx \
  frontend/src/components/documents \
  guardian/routes/documents.py
git commit -m "TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS: add doc type selector and refresh events"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_008_document_gen_add_doc_type_and_events.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-008_DOCUMENT_GEN_ADD_DOC_TYPE_AND_EVENTS -> [<commitA>, <commitB>]

---

## 9) `docs/tasks/TASK_2026_01_23_009_verify_memory_store_init.md`

```md
# TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_009_verify_memory_store_init.md

## Goal

Verify the memory store is actually initialized and wired into ContextBroker creation, per audit.

## Allowed Files (strict)

- guardian/core/dependencies.py
- guardian/memory/**/*.py
- guardian/context/broker.py (only if wiring fix needed)
- guardian/routes/chat.py (only if wiring fix needed)
- guardian/tests/**/*.py (optional)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_009_verify_memory_store_init.md

## Command Checklist (exact)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
rg -n "_memory_store|MemoryStore|memoryos|dependencies" guardian/core/dependencies.py guardian/memory guardian/context/broker.py guardian/routes/chat.py -S

If backend is runnable, verify no runtime errors occur on chat completion:

# optional: run the repo’s backend startup command (document exact command used)

Expected Outputs (success criteria)
 • Clear, code-evidenced path showing memory store initialization and injection into ContextBroker.
 • If broken, fixed wiring is merged and documented in this task.

Rollback / Cleanup

git checkout -- guardian/core/dependencies.py guardian/memory guardian/context/broker.py guardian/routes/chat.py

Dependencies / Prereqs
 • None beyond local repo; runtime validation requires backend start.

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT: verify memory store wiring

Manual commands:

git status --porcelain -uall
git add \
  guardian/core/dependencies.py \
  guardian/memory \
  guardian/context/broker.py \
  guardian/routes/chat.py \
  guardian/tests
git commit -m "TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT: verify memory store wiring"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_009_verify_memory_store_init.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-009_VERIFY_MEMORY_STORE_INIT -> [<commitA>, <commitB>]

---

## 10) `docs/tasks/TASK_2026_01_23_010_context_broker_integration_test.md`

```md
# TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_010_context_broker_integration_test.md

## Goal

Add an integration test that verifies ContextBroker assembles context for a representative query and returns a trace structure consistent with the UI’s expectations.

## Allowed Files (strict)

- guardian/tests/**/*.py
- guardian/context/broker.py (only if test reveals a bug needing minimal fix)
- guardian/routes/chat.py (only if needed for test harness)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_010_context_broker_integration_test.md

## Command Checklist (exact)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
rg -n "ContextBroker|assemble\\(" guardian/context/broker.py -S
ls -1 guardian/tests | head -n 50

Run tests (choose the invocation that exists):

rg -n "pytest" Makefile README.md pyproject.toml
# then run, e.g.:
# pytest -q guardian/tests/test_context_broker_integration.py

Expected Outputs (success criteria)
 • A deterministic integration test exists and passes locally/CI.
 • The test validates:
 • assemble() returns context + trace
 • at least one retrieval path is exercised (semantic results or recent messages)
 • No out-of-scope artifacts added.

Rollback / Cleanup

git checkout -- guardian/tests guardian/context/broker.py guardian/routes/chat.py

Dependencies / Prereqs
 • Memory/vector store may be stubbed/mocked if true integration is expensive; the test must still validate a coherent assembled output.

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST: add context broker integration test

Manual commands:

git status --porcelain -uall
git add guardian/tests guardian/context/broker.py guardian/routes/chat.py
git commit -m "TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST: add context broker integration test"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_010_context_broker_integration_test.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-010_CONTEXT_BROKER_INTEGRATION_TEST -> [<commitA>, <commitB>]

---

## 11) `docs/tasks/TASK_2026_01_23_011_decision_defer_graph_context.md`

```md
# TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_011_decision_defer_graph_context.md

## Goal

Make the CORE LOOP decision explicit:

**Decision**: Defer graph context (Neo4j) for CORE LOOP closure.  
**Outcome**:
- Graph context remains disabled by default
- Any UI/trace references remain accurate and do not imply graph is active unless enabled
- Docs explicitly mark graph context as deferred/experimental

## Allowed Files (strict)

- guardian/context/broker.py
- guardian/routes/chat.py (only if needed to align trace/flags)
- docs/reports/audit-mvp-codexify-2026-01-23.md (only if updating the audit is allowed; otherwise don’t touch)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_011_decision_defer_graph_context.md
- README.md (optional; only if docs drift is real and small)

## Command Checklist (exact)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
rg -n "graph|Neo4j|GUARDIAN_ENABLE_GRAPH_CONTEXT" guardian/context/broker.py guardian/routes/chat.py README.md -S

Expected Outputs (success criteria)
 • Clear code + docs statement: graph context is deferred for CORE LOOP closure.
 • No misleading “graph is active” implication in UI/trace unless flag is enabled.

Rollback / Cleanup

git checkout -- guardian/context/broker.py guardian/routes/chat.py README.md

Dependencies / Prereqs
 • None.

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT: defer graph context for core loop

Manual commands:

git status --porcelain -uall
git add guardian/context/broker.py guardian/routes/chat.py README.md
git commit -m "TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT: defer graph context for core loop"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_011_decision_defer_graph_context.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-011_DECISION_DEFER_GRAPH_CONTEXT -> [<commitA>, <commitB>]

---

## 12) `docs/tasks/TASK_2026_01_23_012_docs_drift_cleanup_core_loop.md` (optional)

```md
# TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP

**Campaign-ID**: CAMPAIGN-2026-01-23-002_CORE_LOOP_ROADMAP  
**Task-ID**: TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP  
**Branch**: chore/post-skip-hook-fixes  
**Task artifact**: docs/tasks/TASK_2026_01_23_012_docs_drift_cleanup_core_loop.md

## Goal

Align docs with reality for CORE LOOP scope (only where drift is confirmed).

## Allowed Files (strict)

- README.md
- docs/**/*.md (excluding large generated reports)
- docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
- docs/tasks/TASK_2026_01_23_012_docs_drift_cleanup_core_loop.md

## Command Checklist (exact)

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall
rg -n "Neo4j|RBAC|marketplace|fine-tuning|graph context|WebSocket" README.md docs -S

Expected Outputs (success criteria)
 • Docs reflect actual CORE LOOP features and clearly label deferred/experimental areas.
 • No promises that code doesn’t keep.

Rollback / Cleanup

git checkout -- README.md docs

Dependencies / Prereqs
 • Prefer to run this after tasks 001–011 so reality is stable.

Commit Plan (manual; two-phase)

Commit A

Commit A message (exact):
TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP: align docs with core loop reality

Manual commands:

git status --porcelain -uall
git add README.md docs
git commit -m "TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP: align docs with core loop reality"
git log -1 --oneline
git rev-parse HEAD

Commit B

Commit B message (exact):
TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP: finalize task summary

Manual commands:

git add \
  docs/tasks/TASK_2026_01_23_012_docs_drift_cleanup_core_loop.md \
  docs/Campaign/CAMPAIGN_2026_01_23__CORE_LOOP_ROADMAP.md
git commit -m "TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP: finalize task summary"
git log -1 --oneline
git rev-parse HEAD

Campaign Mapping Update (exact format)

TASK-2026-01-23-012_DOCS_DRIFT_CLEANUP_CORE_LOOP -> [<commitA>, <commitB>]

