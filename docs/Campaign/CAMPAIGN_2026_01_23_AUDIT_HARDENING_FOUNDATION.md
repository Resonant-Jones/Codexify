# CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION

## Metadata

- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Repo root: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Branch: chore/post-skip-hook-fixes
- Runner Protocol: Runner_Protocol.md
- Git limitation: `.git/index.lock` may block staging/commits in Runner env → **ALL COMMITS MANUAL**
- Two-phase commit protocol:
  - Commit A = implementation/test/config changes
  - Commit B = docs finalize (task artifact summary + campaign mapping)

## Source Audit (authoritative)

- docs/reports/codexify-systems-audit-2026-01-23.md

## Purpose

Convert the audit findings into small, mergeable tasks that harden secrets handling, validate/close MVP wiring gaps, and add minimal verification tests—without introducing new features outside audit scope.

## Global Constraints

- Out-of-scope discipline:
  - Do not generate/commit reports/artifacts outside allowed files.
  - If Playwright/Vitest generates `frontend/src/playwright-report/**` or `frontend/src/test-results/**`, revert/remove immediately before continuing.
- Stop if working tree contains out-of-scope changes.

## Task List (execute in order)

### ✅ TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE

Goal: Remove hardcoded secrets and credentials from docker-compose.yml; ensure env-driven configuration.

- Task artifact: `docs/tasks/TASK_2026_01_23_001_secrets_docker_compose.md`
- Task mapping: `TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE -> [94c10071, 6af53567]`

### ✅ TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT

Goal: Verify the embeddings endpoint exists and matches frontend expectations; implement or correct if missing/mismatched.

- Task artifact: `docs/tasks/TASK_2026_01_23_002_verify_embeddings_endpoint.md`
- Task mapping: `TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT -> [9f9b1c3b, 0efbb2fb]`

### ✅ TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA

Goal: Add durable embedding status tracking for uploaded documents (schema + API surface).

- Task artifact: `docs/tasks/TASK_2026_01_23_003_doc_embed_status_schema.md`
- Task mapping: `TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA -> [f2e6acdd, b097a557]`

### ✅ TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE

Goal: Replace fire-and-forget embedding with a reliable worker-based pipeline that updates status.

- Task artifact: `docs/tasks/TASK_2026_01_23_004_doc_embed_worker_pipeline.md`
- Task mapping: `TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE -> [0b64306b, 1e2c22b8]`

### ✅ TASK-2026-01-23-005_DOC_EMBED_UI_STATUS

Goal: Show embedding readiness in the UI (and block retrieval until ready if needed).

- Task artifact: `docs/tasks/TASK_2026_01_23_005_doc_embed_ui_status.md`
- Task mapping: `TASK-2026-01-23-005_DOC_EMBED_UI_STATUS -> [97da98ff, ]`

### ✅ TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING

Goal: Wire Image Generation UI to the existing backend endpoint (modal + button + request).

- Task artifact: `docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md`
- Task mapping: `TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING -> [<commitA>, <commitB>]`

### ✅ TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING

Goal: Wire DocumentGenModal submit to POST /api/documents/generate and add the missing UI entry point.

- Task artifact: `docs/tasks/TASK_2026_01_23_007_document_gen_ui_wiring.md`
- Task mapping: `TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING -> [<commitA>, <commitB>]`

### ✅ TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST

Goal: Verify memory store initialization and add an integration test for ContextBroker end-to-end.

- Task artifact: `docs/tasks/TASK_2026_01_23_008_memory_init_and_context_integration_test.md`
- Task mapping: `TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST -> [<commitA>, <commitB>]`

### ✅ TASK-2026-01-23-009_NEO4J_DECISION_DOC

Goal: Make an explicit decision: defer Neo4j graph context (or wire minimal enrichment) and update docs accordingly.

- Task artifact: `docs/tasks/TASK_2026_01_23_009_neo4j_decision_doc.md`
- Task mapping: `TASK-2026-01-23-009_NEO4J_DECISION_DOC -> [<commitA>, <commitB>]`

### ✅ TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL

Goal: Optional cleanup of README claims that contradict implementation (audit items).

- Task artifact: `docs/tasks/TASK_2026_01_23_010_docs_drift_cleanup_optional.md`
- Task mapping: `TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL -> [<commitA>, <commitB>]`

## Final Mapping (authoritative; update as tasks complete)

- TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE -> [94c10071, 6af53567]
- TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT -> [9f9b1c3b, 0efbb2fb]
- TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA -> [f2e6acdd, b097a557]
- TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE -> [0b64306b, 1e2c22b8]
- TASK-2026-01-23-005_DOC_EMBED_UI_STATUS -> [97da98ff, ]
- TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING -> [<commitA>, <commitB>]
- TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING -> [<commitA>, <commitB>]
- TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST -> [<commitA>, <commitB>]
- TASK-2026-01-23-009_NEO4J_DECISION_DOC -> [<commitA>, <commitB>]
- TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL -> [<commitA>, <commitB>]

⸻

# TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE

## Metadata

- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE
- Title: Remove hardcoded secrets from docker-compose.yml
- Task artifact: docs/tasks/TASK_2026_01_23_001_secrets_docker_compose.md
- Branch: chore/post-skip-hook-fixes

## Objective

Remove hardcoded credentials/secrets in docker-compose.yml and ensure secrets are provided via environment variables (or Docker secrets if already supported), without changing runtime behavior beyond configuration safety.

## Scope

### In-scope

- Replace hardcoded values (e.g., GUARDIAN_API_KEY, postgres/neo4j passwords) with env-substitution.
- Update `.env.example` / `.env.template` if necessary to reflect required variables.
- Add/adjust documentation in the task artifact for how to run locally.

### Out-of-scope

- Implementing a full Vault/Secrets Manager integration.
- Changing authentication semantics or adding new auth features.

## Allowed files (STRICT)

- docker-compose.yml
- .env.example
- .env.template
- docs/tasks/TASK_2026_01_23_001_secrets_docker_compose.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs

- None (config-only change). Do not require external services.

## Command checklist

```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

# 0) ensure clean tree
git status --porcelain -uall

# 1) locate hardcoded secrets
rg -n "GUARDIAN_API_KEY:|POSTGRES_PASSWORD:|NEO4J_PASSWORD:|OPENAI_API_KEY:" docker-compose.yml

# 2) after edits, verify no hardcoded secrets remain
rg -n "GUARDIAN_API_KEY:\s*[0-9a-f]{16,}|POSTGRES_PASSWORD:\s*\S+|NEO4J_PASSWORD:\s*\S+" docker-compose.yml || true

# 3) verify compose still parses
docker compose config >/dev/null

Expected outputs (success)
 • rg shows NO literal hardcoded secret values in docker-compose.yml (env-substitution is acceptable).
 • docker compose config exits 0.

Rollback / cleanup

git checkout -- docker-compose.yml .env.example .env.template
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation/config)

Message (EXACT):
 • TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE: remove hardcoded secrets

Commands:

git add docker-compose.yml .env.example .env.template
git commit -m "TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE: remove hardcoded secrets"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_001_secrets_docker_compose.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-001_SECRETS_DOCKER_COMPOSE -> [94c10071, 6af53567]

Summary (fill after completion)
 • Hardcoded secrets removed from docker-compose.yml; env-driven vars documented.
 • Commands run + outputs captured.
 • Mapping updated with real hashes.

---

```md
# TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT
- Title: Verify/implement embeddings endpoint used by frontend
- Task artifact: docs/tasks/TASK_2026_01_23_002_verify_embeddings_endpoint.md
- Branch: chore/post-skip-hook-fixes

## Objective
Confirm the embeddings endpoint exists, matches frontend usage, and functions (returns success + predictable shape). If missing/mismatched, implement/correct it.

## Scope
### In-scope
- Identify frontend call sites and expected route/path.
- Ensure backend route exists and is wired into FastAPI app.
- Add/adjust a minimal backend test for endpoint contract.

### Out-of-scope
- Rebuilding the entire embedding architecture (handled in later tasks).
- Changing vector store semantics.

## Allowed files (STRICT)
- guardian/guardian_api.py
- guardian/routes/*.py (ONLY files touched for the endpoint; keep minimal)
- guardian/tests/test_*.py (ONLY the new/updated test for this endpoint)
- frontend/src/**/*.ts
- frontend/src/**/*.tsx
- docs/tasks/TASK_2026_01_23_002_verify_embeddings_endpoint.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- Python env capable of running pytest (use existing repo conventions).

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# 1) find frontend usage
rg -n "/api/embeddings|embeddings" frontend/src

# 2) find backend route or stub
rg -n "embeddings|/api/embeddings" guardian/routes guardian/guardian_api.py

# 3) run minimal backend tests (or a focused one you add)
pytest -q guardian/tests -k "embedding or embeddings" || true

Expected outputs (success)
 • There is exactly one clear route definition for the embeddings endpoint used by frontend.
 • The test for the endpoint passes (or, at minimum, returns 200 and expected JSON shape).
 • Working tree contains ONLY allowed file changes.

Rollback / cleanup

git checkout -- guardian/guardian_api.py guardian/routes frontend/src guardian/tests
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation/test)

Message (EXACT):
 • TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT: verify embeddings endpoint contract

Commands:

git add guardian/guardian_api.py guardian/routes frontend/src guardian/tests
git commit -m "TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT: verify embeddings endpoint contract"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_002_verify_embeddings_endpoint.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-002_VERIFY_EMBEDDINGS_ENDPOINT -> [9f9b1c3b, 0efbb2fb]

Summary (fill after completion)
 • Document the discovered route path + request/response shape.
 • Include test name(s) run and outputs.
 • Record mapping hashes.

---

```md
# TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA
- Title: Add embedding status tracking for uploaded documents (schema + API)
- Task artifact: docs/tasks/TASK_2026_01_23_003_doc_embed_status_schema.md
- Branch: chore/post-skip-hook-fixes

## Objective
Introduce durable status tracking so the system can report whether an uploaded document is pending/processing/ready/failed, enabling reliable UX and worker processing.

## Scope
### In-scope
- Add status fields (and optional error field/timestamps) on the UploadedDocument (or equivalent) model.
- Add migration.
- Add API surface to query status (or include in existing document list endpoint response).
- Add minimal tests for status persistence.

### Out-of-scope
- Implementing the worker pipeline (next task).
- UI indicator (later task).

## Allowed files (STRICT)
- guardian/db/models.py
- backend/migrations/versions/*.py (ONLY the new migration for this task)
- guardian/routes/*.py (ONLY the route(s) touched to surface status)
- guardian/tests/test_*.py (ONLY tests for status contract)
- docs/tasks/TASK_2026_01_23_003_doc_embed_status_schema.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- Alembic migration workflow must already exist in repo (use existing patterns).
- Database is not required to be running during draft; but tests should follow repo norms.

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# 1) find the UploadedDocument model
rg -n "class UploadedDocument|uploaded_document" guardian/db/models.py

# 2) find existing doc list/detail endpoints
rg -n "UploadedDocument|/api/documents" guardian/routes

# 3) run focused tests
pytest -q -k "uploaded_document or document and status" || true

Expected outputs (success)
 • Model contains embedding status fields.
 • Migration exists and is consistent with existing migration conventions.
 • API returns status field (documented in task summary).
 • Tests pass (or at minimum, new tests pass in isolation).

Rollback / cleanup

git checkout -- guardian/db/models.py guardian/routes guardian/tests
git clean -fd backend/migrations/versions
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (schema/api/tests)

Message (EXACT):
 • TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA: add embedding status fields

Commands:

git add guardian/db/models.py backend/migrations/versions guardian/routes guardian/tests
git commit -m "TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA: add embedding status fields"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_003_doc_embed_status_schema.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-003_DOC_EMBED_STATUS_SCHEMA -> [f2e6acdd, b097a557]

---

```md
# TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE
- Title: Worker-based embedding pipeline with status updates
- Task artifact: docs/tasks/TASK_2026_01_23_004_doc_embed_worker_pipeline.md
- Branch: chore/post-skip-hook-fixes

## Objective
Replace fire-and-forget embeddings with a reliable queued worker pipeline that:
- marks status pending → processing → ready/failed
- records errors on failure
- is observable via status API fields introduced in Task 003

## Scope
### In-scope
- Identify the current “fire-and-forget” embedding trigger path.
- Enqueue an embedding job and process it via existing Redis queue/worker patterns.
- Update embedding status in DB throughout lifecycle.
- Add a deterministic test that verifies status transitions (mocking external calls if needed).

### Out-of-scope
- UI status indicator (Task 005).
- Changing vector store behavior beyond what’s needed to run the pipeline reliably.

## Allowed files (STRICT)
- guardian/workers/*.py (ONLY worker(s) related to embeddings)
- guardian/queue/*.py
- guardian/routes/*.py (ONLY if enqueue behavior is triggered via route)
- backend/rag/*.py and/or backend/vector_store/*.py (ONLY if required to hook into existing embedding logic)
- guardian/tests/test_*.py (ONLY pipeline tests)
- docs/tasks/TASK_2026_01_23_004_doc_embed_worker_pipeline.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- Redis queue exists (per audit).
- Status fields exist (Task 003 must be complete first).

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# 1) find fire-and-forget embedding call path
rg -n "embeddings|embed|enqueue|queue" guardian backend

# 2) find existing workers
ls -la guardian/workers || true
rg -n "Redis|enqueue|worker" guardian/workers guardian/queue

# 3) run focused tests
pytest -q -k "embed and worker" || true

Expected outputs (success)
 • Embedding work is queued and processed by a worker (document in summary with file paths).
 • Status transitions occur and persist.
 • Tests cover the critical path deterministically.

Rollback / cleanup

git checkout -- guardian/workers guardian/queue guardian/routes backend guardian/tests
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation/tests)

Message (EXACT):
 • TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE: add worker-based embedding pipeline

Commands:

git add guardian/workers guardian/queue guardian/routes backend guardian/tests
git commit -m "TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE: add worker-based embedding pipeline"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_004_doc_embed_worker_pipeline.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-004_DOC_EMBED_WORKER_PIPELINE -> [0b64306b, 1e2c22b8]

---

```md
# TASK-2026-01-23-005_DOC_EMBED_UI_STATUS

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-005_DOC_EMBED_UI_STATUS
- Title: Display document embedding status in UI
- Task artifact: docs/tasks/TASK_2026_01_23_005_doc_embed_ui_status.md
- Branch: chore/post-skip-hook-fixes

## Objective
Expose embedding readiness to users:
- show status badge (“Pending / Processing / Ready / Failed”)
- optionally prevent “use for retrieval” until Ready (only if already implied by UX)

## Scope
### In-scope
- Update document list/tile UI to render the status field.
- Ensure frontend fetch includes status from existing API response.
- Add a minimal unit test (Vitest) if repo has established patterns.

### Out-of-scope
- Overhauling UI design system.
- Adding new backend endpoints beyond what’s needed to fetch status.

## Allowed files (STRICT)
- frontend/src/**/*.tsx
- frontend/src/**/*.ts
- frontend/src/components/**/*
- frontend/src/tests/**/*
- docs/tasks/TASK_2026_01_23_005_doc_embed_ui_status.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- Status fields and API response support exist (Task 003).
- Pipeline may be incomplete; UI should still render status if present.

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# find document tiles/views
rg -n "DocumentTile|DocumentsView|UploadedDocument" frontend/src

# run unit tests if present
pnpm --dir frontend/src test || true

# ensure no generated e2e artifacts are dirty
git status --porcelain -uall

Expected outputs (success)
 • UI shows embedding status label/badge.
 • No Playwright report/test-results artifacts are committed.

Rollback / cleanup

git checkout -- frontend/src
git clean -fd frontend/src/playwright-report frontend/src/test-results || true
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (frontend changes)

Message (EXACT):
 • TASK-2026-01-23-005_DOC_EMBED_UI_STATUS: show embedding status in UI

Commands:

git add frontend/src
git commit -m "TASK-2026-01-23-005_DOC_EMBED_UI_STATUS: show embedding status in UI"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-005_DOC_EMBED_UI_STATUS: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_005_doc_embed_ui_status.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-005_DOC_EMBED_UI_STATUS: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-005_DOC_EMBED_UI_STATUS -> [97da98ff, ]

---

```md
# TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING
- Title: Wire Image Generation UI to backend endpoint
- Task artifact: docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md
- Branch: chore/post-skip-hook-fixes

## Objective
Add the missing ImageGen UI entry point (button/modal) and wire it to the existing backend image generation endpoint (as referenced by audit).

## Scope
### In-scope
- Create/finish ImageGenModal component.
- Add “Generate Image” button in appropriate view (Gallery).
- Wire modal submit → POST request to backend endpoint.
- Add minimal frontend test or smoke check (if present).

### Out-of-scope
- Changing backend provider logic.
- Adding new image generation features beyond wiring.

## Allowed files (STRICT)
- frontend/src/**/*.tsx
- frontend/src/**/*.ts
- frontend/src/tests/**/*
- docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- Backend endpoint exists (verify via grep/search).

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# 1) find backend endpoint path referenced by frontend (or locate media generate route)
rg -n "media/generate|image/generate|Generate Image" frontend/src guardian/routes || true

# 2) run frontend unit tests (if configured)
pnpm --dir frontend/src test || true

git status --porcelain -uall

Expected outputs (success)
 • UI has a visible button to open modal.
 • Modal submit triggers correct POST with required payload fields.
 • No unintended artifacts committed.

Rollback / cleanup

git checkout -- frontend/src
git clean -fd frontend/src/playwright-report frontend/src/test-results || true
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (frontend wiring)

Message (EXACT):
 • TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: wire image gen modal to endpoint

Commands:

git add frontend/src
git commit -m "TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: wire image gen modal to endpoint"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_006_image_gen_ui_wiring.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-006_IMAGE_GEN_UI_WIRING -> [, ]

---

```md
# TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING
- Title: Wire DocumentGenModal submit to backend + add UI entry point
- Task artifact: docs/tasks/TASK_2026_01_23_007_document_gen_ui_wiring.md
- Branch: chore/post-skip-hook-fixes

## Objective
Close the document generation loop by ensuring:
- A visible UI entry point exists (“Generate Document” button).
- DocumentGenModal submit calls POST /api/documents/generate and handles response.

## Scope
### In-scope
- Add “Generate Document” button to Documents view/header.
- Ensure DocumentGenModal onSubmit calls the endpoint and stores/opens the result per current patterns.
- Add doc_type selector only if already implied by existing backend API contract or existing UI.

### Out-of-scope
- Expanding document generation features beyond wiring.
- Changes to the backend endpoint (unless endpoint contract mismatch is discovered; then capture as a follow-up task).

## Allowed files (STRICT)
- frontend/src/**/*.tsx
- frontend/src/**/*.ts
- frontend/src/tests/**/*
- docs/tasks/TASK_2026_01_23_007_document_gen_ui_wiring.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- Backend endpoint exists (you already implemented /api/documents/generate earlier).

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# find modal + documents view
rg -n "DocumentGenModal|DocumentsView|/api/documents/generate" frontend/src

pnpm --dir frontend/src test || true
git status --porcelain -uall

Expected outputs (success)
 • A button opens DocumentGenModal.
 • Submitting the modal triggers POST /api/documents/generate.
 • UI does something observable with the returned content (documented in summary).

Rollback / cleanup

git checkout -- frontend/src
git clean -fd frontend/src/playwright-report frontend/src/test-results || true
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (frontend wiring)

Message (EXACT):
 • TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING: wire document gen modal to endpoint

Commands:

git add frontend/src
git commit -m "TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING: wire document gen modal to endpoint"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_007_document_gen_ui_wiring.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-007_DOCUMENT_GEN_UI_WIRING -> [, ]

---

```md
# TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST
- Title: Verify memory store initialization + add ContextBroker integration test
- Task artifact: docs/tasks/TASK_2026_01_23_008_memory_init_and_context_integration_test.md
- Branch: chore/post-skip-hook-fixes

## Objective
Ensure memory store is initialized correctly in app dependencies and add a deterministic integration test that validates ContextBroker returns retrieved context end-to-end.

## Scope
### In-scope
- Verify memory store initialization path (dependencies wiring).
- Add one integration test covering a ContextBroker request with retrieval/memory hooks (mocking external services as necessary).
- Ensure test runs deterministically (no external LLM calls).

### Out-of-scope
- Large refactors of memory subsystem.
- Performance optimizations (async refactors) from audit—those belong to a later campaign.

## Allowed files (STRICT)
- guardian/core/dependencies.py
- guardian/context/*.py
- guardian/memory/*.py (ONLY if needed for initialization fix)
- guardian/tests/test_*.py
- docs/tasks/TASK_2026_01_23_008_memory_init_and_context_integration_test.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- pytest available.

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify

git status --porcelain -uall

# locate initialization wiring
rg -n "Memory|memory store|MemoryStore|get_memory" guardian/core/dependencies.py guardian/memory guardian/context

# run a focused test suite
pytest -q -k "context and broker" || true

Expected outputs (success)
 • Confirmed initialization path is correct (document in summary with code location).
 • Integration test passes.
 • No external network calls required by test.

Rollback / cleanup

git checkout -- guardian/core/dependencies.py guardian/context guardian/memory guardian/tests
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (implementation/tests)

Message (EXACT):
 • TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST: add context broker integration test

Commands:

git add guardian/core/dependencies.py guardian/context guardian/memory guardian/tests
git commit -m "TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST: add context broker integration test"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_008_memory_init_and_context_integration_test.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-008_MEMORY_INIT_AND_CONTEXT_INTEGRATION_TEST -> [, ]

---

```md
# TASK-2026-01-23-009_NEO4J_DECISION_DOC

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-009_NEO4J_DECISION_DOC
- Title: Decide Neo4j status and align docs (explicit choice)
- Task artifact: docs/tasks/TASK_2026_01_23_009_neo4j_decision_doc.md
- Branch: chore/post-skip-hook-fixes

## Objective
Make an explicit decision (no “decide later”):
- Option A (default): Mark Neo4j as experimental/deferred and remove/soften README claims.
- Option B: Wire minimal Neo4j enrichment into context path (only if already near-ready).

This task implements **Option A by default** to match audit risk and MVP focus.

## Scope
### In-scope
- Update README / docs to reflect actual Neo4j usage status.
- Add a short ADR-like note or docs section stating decision: “Neo4j deferred post-MVP” (or minimal wiring if Option B chosen).

### Out-of-scope
- Implementing full graph enrichment logic (that would be a dedicated future campaign).

## Allowed files (STRICT)
- README.md
- docs/**/*.md (ONLY relevant docs)
- docs/tasks/TASK_2026_01_23_009_neo4j_decision_doc.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- None.

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

# locate Neo4j claims
rg -n "Neo4j|knowledge graph" README.md docs || true

git status --porcelain -uall

Expected outputs (success)
 • README/docs no longer claim active Neo4j-powered context reasoning unless it truly exists.
 • Decision is explicitly stated in docs.

Rollback / cleanup

git checkout -- README.md docs
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (docs decision)

Message (EXACT):
 • TASK-2026-01-23-009_NEO4J_DECISION_DOC: defer neo4j and align docs

Commands:

git add README.md docs
git commit -m "TASK-2026-01-23-009_NEO4J_DECISION_DOC: defer neo4j and align docs"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-009_NEO4J_DECISION_DOC: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_009_neo4j_decision_doc.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-009_NEO4J_DECISION_DOC: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-009_NEO4J_DECISION_DOC -> [, ]

---

```md
# TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL

## Metadata
- Campaign-ID: CAMPAIGN-2026-01-23-001_AUDIT_HARDENING_FOUNDATION
- Task-ID: TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL
- Title: Optional docs drift cleanup based on audit
- Task artifact: docs/tasks/TASK_2026_01_23_010_docs_drift_cleanup_optional.md
- Branch: chore/post-skip-hook-fixes

## Objective
Optionally correct documentation claims identified in the audit (WebSocket scope, fine-tuning, RBAC, plugin marketplace) to reflect reality and/or clearly label as roadmap.

## Scope
### In-scope
- Edit README sections to label features as “experimental” or “roadmap” if not implemented.
- Keep changes minimal and consistent with audit.

### Out-of-scope
- Implementing missing features.

## Allowed files (STRICT)
- README.md
- docs/**/*.md (ONLY docs drift corrections)
- docs/tasks/TASK_2026_01_23_010_docs_drift_cleanup_optional.md
- docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md

## Dependencies / Prereqs
- None.

## Command checklist
```bash
cd /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
git status --porcelain -uall

rg -n "RBAC|fine-tuning|marketplace|WebSocket|real-time" README.md docs || true

git status --porcelain -uall

Expected outputs (success)
 • README/docs distinguish implemented vs roadmap clearly (matching audit).
 • No code changes.

Rollback / cleanup

git checkout -- README.md docs
git status --porcelain -uall

Commit plan (MANUAL; index.lock workaround)

Commit A (docs changes)

Message (EXACT):
 • TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL: align docs with implementation

Commands:

git add README.md docs
git commit -m "TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL: align docs with implementation"
git status --porcelain -uall
git log -1 --oneline

Commit B (docs finalize)

Message (EXACT):
 • TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL: finalize task summary

Commands:

git add docs/tasks/TASK_2026_01_23_010_docs_drift_cleanup_optional.md docs/Campaign/CAMPAIGN_2026_01_23_001_AUDIT_HARDENING_FOUNDATION.md
git commit -m "TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL: finalize task summary"
git status --porcelain -uall
git log -1 --oneline

Mapping
 • TASK-2026-01-23-010_DOCS_DRIFT_CLEANUP_OPTIONAL -> [, ]

---

### Notes (already encoded as “no follow-ups” behavior)
- Branch is set to your **current**: `chore/post-skip-hook-fixes`.
- The audit’s “async refactor” / RBAC / audit logging are **not** included as tasks here because they’re substantial and the prompt’s required priority list didn’t include them; they can be a **separate campaign** once MVP wiring + embedding reliability are closed.

If you want this to match your repo’s exact campaign filename style (e.g., you prefer `docs/Campaign/CAMPAIGN_2026_01_23.md` without the `001_...` suffix), rename consistently across the campaign + task artifacts—don’t mix formats.
