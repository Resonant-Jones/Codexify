# Codexify Senior Architect System Audit (2026-02-24)

## Metadata
- Repository: `/Users/resonant_jones/.codex/worktrees/ae18/Codexify`
- Audit date: 2026-02-24
- Auditor: Axis (Codex, GPT-5)
- Runner: Codex desktop, local shell (`zsh`)
- Branch: `HEAD` (detached)
- Commit: `ba6989034d9f0eedd2dc2967134366887c481f81`
- Worktree baseline command: `git status --porcelain -uall`

## Executive Summary
Codexify has strong building blocks for local MVP (durable tool jobs, queue worker, startup migration hard-fail, default-project dedup), but the six MVP core loops are not fully closed. Most closure failures are contract drift and auth boundary gaps rather than missing infrastructure.

Top concerns:
1. [RISK] Unauthenticated write endpoints across chat/media/projects allow state mutation without API key checks (FINDING-2026-02-24-002, FINDING-2026-02-24-003).
2. [RISK] ChatGPT migration route is currently broken by response-key mismatch (`threads/messages` vs `threads_imported/messages_imported`) (FINDING-2026-02-24-005).
3. [RISK] Sensitive files are tracked in git (`guardian/secrets/*`, large conversation export), creating direct confidentiality/sovereignty risk (FINDING-2026-02-24-014).
4. [WARN] Chat completion contract drift (`task_id` async backend vs frontend expecting immediate `context`) leaves RAG loop non-deterministic in practice (FINDING-2026-02-24-007).
5. [WARN] Document and gallery UX still rely on localStorage/demo fallback, so persistence is not consistently backend-authoritative (FINDING-2026-02-24-009, FINDING-2026-02-24-011).

## Runner-Ready Findings Manifest (authoritative)
```yaml
- finding_id: FINDING-2026-02-24-001
  area: other
  severity: WARN
  title: Worktree drift present during audit
  description: >-
    The worktree is dirty (`:memory:` and `data/trust_registry.json`). Per audit policy,
    no cleanup was applied. This can bias test and diff interpretation if not normalized.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/:memory:
      lines: "unknown"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/data/trust_registry.json
      lines: "unknown"
  relates_to_core_loop: none
  suggested_task_outcome: "Worktree is clean before next implementation sprint starts."
  suggested_commands:
    - "git status --porcelain -uall"
    - "git restore -- ':memory:' data/trust_registry.json"
  dependencies: []
  notes: "Observed directly from git status; cleanup intentionally not performed in this audit."

- finding_id: FINDING-2026-02-24-002
  area: security
  severity: RISK
  title: Chat mutation endpoints are unauthenticated
  description: >-
    Core chat thread/message endpoints are mounted without `Depends(require_api_key)`.
    This permits unauthenticated mutation in environments where network boundary is open.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py
      lines: "L315-L357"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py
      lines: "L408-L556"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py
      lines: "L631-L742"
  relates_to_core_loop: rag
  suggested_task_outcome: "All chat write endpoints reject missing/invalid API keys with HTTP 401/403."
  suggested_commands:
    - "rg -n \"@router\\.(post|patch|delete)\\(\" guardian/routes/chat.py"
    - "rg -n \"Depends\\(require_api_key\\)\" guardian/routes/chat.py"
    - "pytest -v tests/routes/test_chat_routes.py"
  dependencies: []
  notes: "Public ingress architecture is not fully mapped; validate reverse-proxy controls if intentionally open."

- finding_id: FINDING-2026-02-24-003
  area: security
  severity: RISK
  title: Projects and media write paths are unauthenticated
  description: >-
    Project mutation and media upload/generation routes have no explicit API-key dependency.
    This violates closure requirement of auth outside dev proxy for doc/image loops.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/projects.py
      lines: "L55-L126"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py
      lines: "L133-L141"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py
      lines: "L257-L266"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py
      lines: "L385-L406"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: "Projects/media mutating routes enforce API key checks consistently."
  suggested_commands:
    - "rg -n \"@router\\.(post|patch|delete)\\(\" guardian/routes/projects.py guardian/routes/media.py"
    - "rg -n \"Depends\\(require_api_key\\)\" guardian/routes/projects.py guardian/routes/media.py"
    - "pytest -v tests/routes"
  dependencies: []
  notes: "Read-only media list endpoints may remain public if explicitly documented."

- finding_id: FINDING-2026-02-24-004
  area: security
  severity: WARN
  title: Connector admin endpoints mostly unauthenticated
  description: >-
    Connector create/update/sync/status/test endpoints are open; only `/api/connectors/{name}/ingest`
    requires API key. This creates a configuration tampering and data egress surface.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/connectors.py
      lines: "L581-L679"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/connectors.py
      lines: "L682-L697"
  relates_to_core_loop: none
  suggested_task_outcome: "Connector admin and execution endpoints require auth except explicitly public health checks."
  suggested_commands:
    - "rg -n \"@router\\.(get|post|patch|delete)\" guardian/routes/connectors.py"
    - "rg -n \"Depends\\(require_api_key\\)\" guardian/routes/connectors.py"
  dependencies: []
  notes: "If this is intentionally internal-only, document ingress isolation and network policy."

- finding_id: FINDING-2026-02-24-005
  area: core-loop
  severity: RISK
  title: ChatGPT migration endpoint and ingestion function have incompatible response keys
  description: >-
    `/upload-chatgpt-export` route reads `stats[\"threads\"]` and `stats[\"messages\"]`,
    while `ingest_chatgpt_export` currently returns `threads_imported/messages_imported`.
    This is a deterministic runtime failure path for migration loop.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/migration.py
      lines: "L40-L44"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/backend/rag/chatgpt_migration.py
      lines: "L153-L156"
  relates_to_core_loop: migration
  suggested_task_outcome: "Migration route returns 200 with valid imported counts for a fixture export file."
  suggested_commands:
    - "pytest -v tests/routes -k migration"
    - "rg -n \"threads_imported|messages_imported|stats\\[\\\"threads\\\"\]\\|stats\\[\\\"messages\\\"\]\" guardian/routes/migration.py backend/rag/chatgpt_migration.py"
  dependencies:
    - DATABASE_URL
    - vector store backend
  notes: "This can be fixed either by route translation or ingest return-shape normalization."

- finding_id: FINDING-2026-02-24-006
  area: docs-drift
  severity: WARN
  title: Duplicate legacy migration endpoint exists outside active router wiring
  description: >-
    `guardian/routes/rag_upload.py` still defines `/upload-chatgpt-export`, while `guardian_api.py`
    comments that redundant upload endpoint was removed and mounts `migration.router`.
    This is a drift source for docs and future refactors.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/rag_upload.py
      lines: "L66-L87"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/guardian_api.py
      lines: "L445-L445"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/guardian_api.py
      lines: "L672-L672"
  relates_to_core_loop: migration
  suggested_task_outcome: "Single canonical migration endpoint implementation remains and stale route is removed or clearly marked unused."
  suggested_commands:
    - "rg -n \"upload-chatgpt-export\" guardian/routes"
    - "rg -n \"include_router\(migration\.router\)\" guardian/guardian_api.py"
  dependencies: []
  notes: "Runtime impact depends on router inclusion; currently appears mostly maintenance drift."

- finding_id: FINDING-2026-02-24-007
  area: core-loop
  severity: WARN
  title: Chat completion API/frontend contract drift (async task vs immediate context)
  description: >-
    Backend `/api/chat/{thread_id}/complete` returns only `{task_id}` while frontend expects
    `response.data.context` for trace capture. This weakens deterministic loop behavior and
    obscures user feedback when queueing succeeds but context path is absent.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py
      lines: "L554-L628"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/features/chat/GuardianChat.tsx
      lines: "L104-L120"
  relates_to_core_loop: rag
  suggested_task_outcome: "Frontend and backend use one explicit completion contract (async task polling/SSE or sync response) with tests."
  suggested_commands:
    - "rg -n \"task_id|context\" guardian/routes/chat.py frontend/src/features/chat/GuardianChat.tsx"
    - "pytest -v tests/routes/test_chat_routes.py"
  dependencies:
    - REDIS_URL
    - worker-chat service
  notes: "Outbox SSE may still close loop if frontend subscribes correctly to message events."

- finding_id: FINDING-2026-02-24-008
  area: testing
  severity: WARN
  title: Chat route tests fail when Redis queue is unavailable
  description: >-
    Local `pytest -v` run produced failures in chat completion tests tied to queue availability
    and host resolution for Redis (`redis:6379`). Current API behavior returns `queue_unavailable`
    when enqueue fails, which is deterministic but not test-hermetic for local runs without redis.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py
      lines: "L607-L610"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_chat_routes.py
      lines: "L287-L391"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_chat_system_prompt_integration.py
      lines: "L51-L59"
  relates_to_core_loop: rag
  suggested_task_outcome: "Chat completion tests pass in hermetic mode using queue stub/fixture or explicit compose-backed integration profile."
  suggested_commands:
    - "pytest -v tests/routes/test_chat_routes.py"
    - "pytest -v tests/routes/test_chat_system_prompt_integration.py"
    - "docker compose up -d redis worker-chat"
  dependencies:
    - REDIS_URL
    - worker-chat service
  notes: "Exact failing assertion lines can change; failure class observed in this audit run."

- finding_id: FINDING-2026-02-24-009
  area: core-loop
  severity: WARN
  title: Document upload UI persists mainly to local state/localStorage
  description: >-
    Frontend uploader creates local document records and optional ingestion POST to a configurable
    endpoint, but does not enforce backend `/api/media/upload/document` as source of truth.
    This leaves doc-upload loop partially closed for persistence.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/hooks/useUploader.ts
      lines: "L46-L117"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/persona/layout/AppShell.tsx
      lines: "L414-L431"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/persona/layout/AppShell.tsx
      lines: "L800-L803"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: "Upload path writes to backend media API and reloads from `/api/media/documents` list as canonical state."
  suggested_commands:
    - "rg -n \"useUploader|cfy:documents:add|localStorage\.getItem\\(\\\"cfy.documents\\\"\" frontend/src"
    - "curl -s http://localhost:8000/api/media/documents | jq ."
  dependencies:
    - backend service
    - database service
  notes: "Optional ingestion endpoint can remain as extension path if clearly secondary."

- finding_id: FINDING-2026-02-24-010
  area: core-loop
  severity: WARN
  title: Dashboard expects wrong shape from `/api/media/documents`
  description: >-
    Dashboard treats `res.data` as an array, but backend returns object `{documents, count}`.
    This causes recent-doc rendering drift and weakens deterministic validation of document persistence.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/dashboard/DashboardView.tsx
      lines: "L103-L106"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py
      lines: "L607-L622"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: "Dashboard loads `res.data.documents` and integration test asserts rendered recent docs from backend payload."
  suggested_commands:
    - "rg -n \"api/media/documents|res\\?\\.data\" frontend/src/components/dashboard/DashboardView.tsx"
    - "pytest -v tests -k documents"
  dependencies:
    - backend service
  notes: "UI may silently show empty state today, masking backend data presence."

- finding_id: FINDING-2026-02-24-011
  area: core-loop
  severity: WARN
  title: Image gallery loop can fall back to demo/local data instead of backend persistence
  description: >-
    Gallery and dashboard include demo images and localStorage-backed state. This reduces confidence
    that generated/uploaded images are truly persisted and reloadable from backend list endpoints.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/gallery/GalleryView.tsx
      lines: "L10-L53"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/dashboard/DashboardView.tsx
      lines: "L12-L36"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/persona/layout/AppShell.tsx
      lines: "L699-L720"
  relates_to_core_loop: image-gallery
  suggested_task_outcome: "Gallery default state derives from `/api/media/images` with optional explicit demo toggle only in dev."
  suggested_commands:
    - "rg -n \"DEMO_GALLERY_ITEMS|cfy.gallery|/api/media/images\" frontend/src"
    - "curl -s http://localhost:8000/api/media/images | jq ."
  dependencies:
    - backend service
  notes: "Demo UX is useful for onboarding but should not be implicit in MVP validation paths."

- finding_id: FINDING-2026-02-24-012
  area: core-loop
  severity: RISK
  title: Image generation endpoint is still placeholder logic
  description: >-
    `/api/media/generate/image` explicitly notes it does not generate images and returns a synthetic
    path. This means image-gen core loop is stubbed, not end-to-end.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py
      lines: "L385-L405"
  relates_to_core_loop: image-gen
  suggested_task_outcome: "Image generation endpoint calls a real provider/local model and stores resulting assets retrievable by `/api/media/images`."
  suggested_commands:
    - "rg -n \"generate/image|doesn't actually generate images\" guardian/routes/media.py"
    - "curl -s -X POST http://localhost:8000/api/media/generate/image -H 'content-type: application/json' -d '{\"prompt\":\"test\",\"project_id\":1,\"thread_id\":1}'"
  dependencies:
    - image generation provider or local runtime
  notes: "There is separate provider code under `guardian/image_gen`, but no direct integration proven in this route."

- finding_id: FINDING-2026-02-24-013
  area: core-loop
  severity: WARN
  title: No explicit document generation API loop (only autosave/linking)
  description: >-
    Generated document storage model exists and autosave route exists, but there is no explicit
    `/api/documents/generate` style endpoint to close prompt->generated-doc loop deterministically.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/documents.py
      lines: "L63-L197"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/db/models.py
      lines: "L532-L564"
  relates_to_core_loop: doc-gen
  suggested_task_outcome: "Document generation endpoint exists, persists `GeneratedDocument`, and is covered by route tests."
  suggested_commands:
    - "rg -n \"api/documents/autosave|GeneratedDocument|generate\" guardian/routes guardian/db/models.py"
    - "pytest -v tests -k document"
  dependencies:
    - LLM provider/local model
    - database service
  notes: "Autosave solves session notes, not prompt-based document generation."

- finding_id: FINDING-2026-02-24-014
  area: security
  severity: RISK
  title: Sensitive files appear tracked in repository
  description: >-
    OAuth client secret, token material, and a large conversation export are present in tracked files.
    This introduces immediate confidentiality risk and undermines sovereignty controls.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/secrets/client_secret_oauth.json
      lines: "unknown"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/secrets/token.json
      lines: "unknown"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/temp/conversations.json
      lines: "unknown"
  relates_to_core_loop: none
  suggested_task_outcome: "Secrets removed from git history/tracked paths; runtime loads from env/secret manager only."
  suggested_commands:
    - "git ls-files guardian/secrets/client_secret_oauth.json guardian/secrets/token.json guardian/temp/conversations.json"
    - "rg -n \"guardian/secrets|token.json|client_secret_oauth\" .gitignore"
  dependencies: []
  notes: "History rewrite may be required beyond deleting current tracked files."

- finding_id: FINDING-2026-02-24-015
  area: security
  severity: RISK
  title: Hardcoded API keys in compose and permissive default auth keys
  description: >-
    Docker compose includes fixed API key values, and dependency fallback logic allows
    deterministic default keys (`invalid-by-default`, `changeme`) when env is unset.
    This weakens auth in misconfigured environments.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml
      lines: "L232-L232"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml
      lines: "L476-L476"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/dependencies.py
      lines: "L92-L92"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/dependencies.py
      lines: "L178-L188"
  relates_to_core_loop: none
  suggested_task_outcome: "No hardcoded keys in compose; startup fails fast when auth keys are missing outside explicit test mode."
  suggested_commands:
    - "rg -n \"GUARDIAN_API_KEY|VITE_GUARDIAN_API_KEY|changeme|invalid-by-default\" docker-compose.yml guardian/core/dependencies.py"
  dependencies: []
  notes: "Test profile can keep deterministic keys if isolated via explicit test env flag."

- finding_id: FINDING-2026-02-24-016
  area: privacy
  severity: WARN
  title: Connector settings may store and return tokens in plain JSON fields
  description: >-
    Connector `settings` are persisted as config JSON and serialized back through API responses.
    Without explicit redaction/encryption controls, tokens may be exposed to operators or logs.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/pgdb.py
      lines: "L1356-L1443"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/connectors.py
      lines: "L182-L204"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/connectors.py
      lines: "L603-L640"
  relates_to_core_loop: none
  suggested_task_outcome: "Sensitive connector fields are encrypted/redacted at rest and masked in API responses."
  suggested_commands:
    - "rg -n \"settings\" guardian/routes/connectors.py guardian/core/pgdb.py"
    - "pytest -v tests/routes -k connector"
  dependencies:
    - database service
  notes: "Schema-level encryption not observed in inspected files; verify DB-side controls if present elsewhere."

- finding_id: FINDING-2026-02-24-017
  area: docs-drift
  severity: WARN
  title: Config and docs drift increases operator error risk
  description: >-
    The codebase contains multiple config systems (`guardian/config/core.py`, `guardian/core/config.py`,
    `guardian/config/settings.py`) and docs/README references to outdated paths and alembic commands.
    This causes onboarding and runbook ambiguity.
  evidence:
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/config/core.py
      lines: "L1-L357"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/config.py
      lines: "L1-L201"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/README.md
      lines: "L204-L208"
    - file: /Users/resonant_jones/.codex/worktrees/ae18/Codexify/README.md
      lines: "L425-L437"
  relates_to_core_loop: none
  suggested_task_outcome: "Single canonical config path documented; stale docs and path references removed."
  suggested_commands:
    - "rg -n \"from guardian\\.config\\.core|from guardian\\.core\\.config\" guardian -g '*.py'"
    - "rg -n \"alembic upgrade head|guardian/server|guardian/api\" README.md docs -g '*.md'"
  dependencies: []
  notes: "Drift is DX-critical for MVP velocity even if runtime continues to function."
```

## System Overview
### Subsystem status
- Backend API routing: **Implemented** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/guardian_api.py:400-447`)
- Chat async queue worker: **Implemented** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py:554-628`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/workers/chat_worker.py:323-356`)
- Tool execution durability: **Implemented** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/tools.py:145-256`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/db/models.py:333-361`)
- Startup migration hard-fail path: **Implemented** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/backend/Dockerfile:104`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml:118-121`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml:314`)
- Default project alias dedup and row reassignment: **Implemented** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/backend/scripts/seed_defaults.py:297-362`)
- Media upload/list APIs: **Partial** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:133-367`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:538-622`)
- Image generation: **Stubbed** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:394-405`)
- Document generation: **Stubbed** (autosave exists, generation endpoint not found; `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/documents.py:63-197`)
- Frontend persistence from backend lists: **Partial** (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/persona/layout/AppShell.tsx:414-431`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/hooks/useUploader.ts:46-117`)

## Core Loop Closure Scorecard
| Core loop | Code Present | Loop Closed | Closure requirements status |
|---|---|---|---|
| `rag` | partial | no | Auth outside dev proxy: **no** (FINDING-2026-02-24-002). Persistence via backend list: **yes** (messages persisted by worker). Deterministic validation path: **no** (FINDING-2026-02-24-007, FINDING-2026-02-24-008). |
| `migration` | partial | no | Auth outside dev proxy: **yes** (`require_api_key` in route). Persistence via backend list: **partial**. Deterministic validation path: **no** due key mismatch (FINDING-2026-02-24-005). |
| `doc-upload` | partial | no | Auth outside dev proxy: **no** (FINDING-2026-02-24-003). Persistence via backend list: **partial** (FINDING-2026-02-24-009, FINDING-2026-02-24-010). Deterministic validation path: **no**. |
| `image-gallery` | partial | no | Auth outside dev proxy: **no** (FINDING-2026-02-24-003). Persistence via backend list: **partial** (FINDING-2026-02-24-011). Deterministic validation path: **no**. |
| `image-gen` | stubbed | no | Auth outside dev proxy: **no**. Persistence via backend list: **no** (placeholder). Deterministic validation path: **no** (FINDING-2026-02-24-012). |
| `doc-gen` | stubbed | no | Auth outside dev proxy: **n/a** until endpoint exists. Persistence via backend list: **no**. Deterministic validation path: **no** (FINDING-2026-02-24-013). |

## Security, Privacy, and Sovereignty
### Secrets management
- Tracked secret-like files detected: `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/secrets/client_secret_oauth.json`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/secrets/token.json`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/temp/conversations.json` (FINDING-2026-02-24-014).
- Hardcoded API keys in compose: `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml:232`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml:476` (FINDING-2026-02-24-015).
- Fallback auth defaults include deterministic weak keys (`changeme`, `invalid-by-default`) in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/dependencies.py:92`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/dependencies.py:178-188` (FINDING-2026-02-24-015).

### Code-evidenced data egress map
| Source | Destination | Trigger | Data egressed | Evidence |
|---|---|---|---|---|
| LLM router | OpenAI API (`https://api.openai.com`) | chat completion provider=openai | messages, model params | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/ai_router.py:12`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/ai_router.py:232-239` |
| LLM router | Groq API (`https://api.groq.com`) | chat completion provider=groq | messages, model params | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/ai_router.py:13`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/ai_router.py:202-209` |
| Connector sync | GitHub API (`https://api.github.com`) | connector sync/ingest | issues, PR metadata | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/connectors/github.py:10`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/connectors/github.py:58-70` |
| Federation route | arbitrary peer manifest URL | federation health/probe | outbound GET to node manifest | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/federation.py:101`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/federation.py:185` |

### Access control boundaries
- Stronger pattern exists: tools routes require API key (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/tools.py:147`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/tools.py:229`).
- Boundary inconsistency remains in chat/media/projects/connectors admin (FINDING-2026-02-24-002 through FINDING-2026-02-24-004).

## Docs and Code Consistency
### Docs drift (examples)
- README still documents console script alembic usage (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/README.md:204`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/README.md:208`) while runtime now uses module invocation (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/backend/Dockerfile:104`).
- README references old backend path taxonomy (`guardian/server`, `guardian/api`) at `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/README.md:425-437`.
- Legacy docs still reference `Loose Threads` default project semantics (example `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docs/MVP ROADMAP/09-18-25-dailytasks.md:6`).

### Code drift
- Duplicate migration endpoint implementation remains (`FINDING-2026-02-24-006`).
- Multiple config modules coexist (`FINDING-2026-02-24-017`).

## Code Quality, Testing, and DX
- Current test baseline from local run: `7 failed, 490 passed, 13 skipped, 41 xfailed, 3 xpassed` (`pytest -v`), with failures concentrated in chat completion route tests tied to queue/contract assumptions (FINDING-2026-02-24-008).
- Positive: test hermetic guard for dotenv is present in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/conftest.py:4-6`.
- Positive: durable tool-job tests and model/migration are in place (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_tools.py`, `tool_jobs` migration).

How to run (current repo patterns):
- `pytest -v`
- Optional service-backed pass for chat queue tests: `docker compose up -d redis worker-chat && pytest -v tests/routes/test_chat_routes.py`

## Performance and Scalability
Implemented:
- Async queue-based chat completion pipeline decouples request/compute (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py:597-628`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/workers/chat_worker.py:389-430`).
- Durable tool-job indexes (`ix_tool_jobs_created_at`, `ix_tool_jobs_status`) support query scale-up (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/db/migrations/versions/9b3d2d08f7c1_add_tool_jobs_table.py:62-63`).
- Startup embed model lock and shared volume prevent redundant model downloads (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/scripts/ensure_embed_model.py:94-130`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml:225`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml:503-504`).

Theoretical / not yet evidenced:
- No performance test harness evidence found for chat throughput, queue depth SLOs, or media upload latency.
- No explicit rate-limit guards found on heavy mutation endpoints in inspected route files.

## Risk Register
| ID | Severity | Area | Risk | Evidence |
|---|---|---|---|---|
| FINDING-2026-02-24-002 | RISK | security | Unauthenticated chat mutation endpoints | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py:315-357` |
| FINDING-2026-02-24-003 | RISK | security | Unauthenticated projects/media writes | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/projects.py:55-126`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:133-406` |
| FINDING-2026-02-24-005 | RISK | core-loop | Migration route deterministic failure | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/migration.py:40-44` |
| FINDING-2026-02-24-012 | RISK | core-loop | Image generation stubbed | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:394-405` |
| FINDING-2026-02-24-014 | RISK | security | Secret material tracked in repo | `guardian/secrets/*`, `guardian/temp/conversations.json` |
| FINDING-2026-02-24-015 | RISK | security | Hardcoded API keys and weak defaults | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docker-compose.yml:232`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/dependencies.py:178-188` |
| FINDING-2026-02-24-007 | WARN | core-loop | Async completion contract drift | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py:554-628`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/features/chat/GuardianChat.tsx:104-120` |
| FINDING-2026-02-24-008 | WARN | testing | Redis-coupled route tests fail locally | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py:607-610` |
| FINDING-2026-02-24-009 | WARN | core-loop | Doc upload persists via local state | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/hooks/useUploader.ts:46-117` |
| FINDING-2026-02-24-010 | WARN | core-loop | Dashboard docs API shape mismatch | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/dashboard/DashboardView.tsx:103-106` |
| FINDING-2026-02-24-011 | WARN | core-loop | Gallery fallback masks backend truth | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/gallery/GalleryView.tsx:10-53` |
| FINDING-2026-02-24-013 | WARN | core-loop | Missing document generation endpoint | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/documents.py:63-197` |
| FINDING-2026-02-24-016 | WARN | privacy | Connector token handling lacks proven redaction/encryption | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/core/pgdb.py:1356-1443` |
| FINDING-2026-02-24-017 | WARN | docs-drift | Config/docs drift increases operator error | `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/README.md:204-208` |
| FINDING-2026-02-24-001 | WARN | other | Dirty worktree can skew validation | `git status --porcelain -uall` |

## Recommended MVP-first sequencing
1. Close auth boundary consistency for all mutating endpoints in core loops (FINDING-2026-02-24-002/003).
2. Repair migration response contract and remove duplicate route drift (FINDING-2026-02-24-005/006).
3. Choose and enforce one chat completion contract (async or sync) across backend, frontend, and tests (FINDING-2026-02-24-007/008).
4. Make doc/gallery views backend-authoritative and remove implicit demo masking in MVP validation mode (FINDING-2026-02-24-009/010/011).
5. Convert image-gen/doc-gen from stubs to minimal deterministic implementations (FINDING-2026-02-24-012/013).
6. Remove tracked secrets and hardcoded auth material before any wider deployment (FINDING-2026-02-24-014/015/016).
