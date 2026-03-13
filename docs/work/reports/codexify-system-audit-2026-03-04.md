# Codexify System Audit (2026-03-04)

## Metadata
- Repo: /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
- Branch: codex/add-import-progress-ui-feedback
- Commit: 32e3aa822dca797811df9058b8ae1a89b9694625
- Date: 2026-03-04 (America/New_York)
- Agent: Axis (GPT-5 via Codex CLI)
- Execution: Read-only code review; tests not executed in this run.

## Runner-Ready Findings Manifest (authoritative)
```yaml
- finding_id: FINDING-2026-03-04-001
  area: core-loop
  severity: RISK
  title: LLM provider defaults to local but LOCAL_BASE_URL is required
  description: Chat/doc-gen paths default provider to `local`; if `LOCAL_BASE_URL` is unset the backend returns HTTP 400, blocking completions and document generation by default.
  evidence:
    - file: guardian/core/ai_router.py
      lines: "18-30"
    - file: guardian/core/ai_router.py
      lines: "142-147"
  relates_to_core_loop: rag
  suggested_task_outcome: LOCAL_BASE_URL (or a cloud provider) configured and health-checked; chat completion and /api/documents/generate succeed without 400.
  suggested_commands:
    - GUARDIAN_API_KEY=test curl -s -X POST http://localhost:8000/api/chat/1/complete -H "X-API-Key: $GUARDIAN_API_KEY" -H "content-type: application/json" -d '{}' | jq .
  dependencies:
    - GUARDIAN_API_KEY
    - LOCAL_BASE_URL
    - Redis queue
  notes: Set LOCAL_BASE_URL/LOCAL_LLM_MODEL or switch provider + allowlist; add a startup check that fails fast when missing.

- finding_id: FINDING-2026-03-04-002
  area: sovereignty
  severity: WARN
  title: Cloud egress blocked by default; allowlist required for OpenAI/Groq/minimax
  description: Egress guard denies cloud targets unless CODEXIFY_LOCAL_ONLY_MODE is false and CODEXIFY_EGRESS_ALLOWLIST/ALLOW_CLOUD_PROVIDERS are set, so cloud-backed chat or image-gen calls return 403 even before reaching providers.
  evidence:
    - file: guardian/core/egress.py
      lines: "65-80"
    - file: guardian/core/ai_router.py
      lines: "473-520"
    - file: guardian/image_gen/providers/openai.py
      lines: "18-67"
  relates_to_core_loop: doc-gen
  suggested_task_outcome: Documented egress toggle and allowlist applied for chosen providers; 403 no longer returned for configured clouds while remaining deny-by-default otherwise.
  suggested_commands:
    - GUARDIAN_API_KEY=test IMAGE_GEN_PROVIDER=openai IMAGE_GEN_MODEL=dall-e-3 curl -s -X POST http://localhost:8000/api/media/generate/image -H "X-API-Key: $GUARDIAN_API_KEY" -H "content-type: application/json" -d '{"prompt":"ping","project_id":1,"thread_id":1}' | jq .
  dependencies:
    - CODEXIFY_LOCAL_ONLY_MODE
    - CODEXIFY_EGRESS_ALLOWLIST
    - ALLOW_CLOUD_PROVIDERS
  notes: Keep deny-by-default posture; document minimal allowlist values per provider.

- finding_id: FINDING-2026-03-04-003
  area: core-loop
  severity: RISK
  title: Image generation lacks local implementation and requires provider/model env
  description: Local image generator raises 503 and router demands IMAGE_GEN_PROVIDER/MODEL, so the image-gen loop cannot run out-of-the-box without external provider credentials and egress approval.
  evidence:
    - file: guardian/image_gen/providers/local.py
      lines: "17-22"
    - file: guardian/image_gen/router.py
      lines: "18-42"
    - file: guardian/routes/media.py
      lines: "1223-1330"
  relates_to_core_loop: image-gen
  suggested_task_outcome: Ship a working offline provider (or documented OpenAI/Stability config) with automated test exercising real bytes -> asset persistence.
  suggested_commands:
    - IMAGE_GEN_PROVIDER=local GUARDIAN_API_KEY=test curl -s -X POST http://localhost:8000/api/media/generate/image -H "X-API-Key: $GUARDIAN_API_KEY" -H "content-type: application/json" -d '{"prompt":"test","project_id":1,"thread_id":1}' | jq .
  dependencies:
    - IMAGE_GEN_PROVIDER
    - IMAGE_GEN_MODEL
    - CODEXIFY_EGRESS_ALLOWLIST
  notes: Current tests mock ImageGenRouter.generate; add an integration path once a real provider is wired.

- finding_id: FINDING-2026-03-04-004
  area: core-loop
  severity: WARN
  title: Media routes fall back to Postgres DSN on db host; no sqlite/local default
  description: `_get_db()` defaults to `postgresql://guardian:guardian@db:5432/guardian` when DATABASE_URL is unset; uploads/lists fail if that service is down, and there is no sqlite fallback for media routes.
  evidence:
    - file: guardian/routes/media.py
      lines: "205-223"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: Document required DATABASE_URL for media stack or add a deterministic local fallback used by tests/dev harness.
  suggested_commands:
    - DATABASE_URL=postgresql://localhost:9999/absent GUARDIAN_API_KEY=test python - <<'PY'\nfrom guardian.routes import media\nprint(media._get_db().engine.url)\nPY
  dependencies:
    - DATABASE_URL
  notes: Chat routes can run without DB, but media/doc/image flows cannot.

- finding_id: FINDING-2026-03-04-005
  area: core-loop
  severity: WARN
  title: Gallery UI silently falls back to demo images when backend fetch fails
  description: Gallery fetch errors clear to an empty list and the view renders DEMO_GALLERY_ITEMS when `showDemoGallery` is true, so backend persistence issues are masked and the loop is not validated against `/api/media/images`.
  evidence:
    - file: frontend/src/components/gallery/GalleryView.tsx
      lines: "70-108"
    - file: frontend/src/components/gallery/GalleryView.tsx
      lines: "176-182"
  relates_to_core_loop: image-gallery
  suggested_task_outcome: Backend list is authoritative in MVP mode; demo toggle behind explicit dev flag or separate route.
  suggested_commands:
    - pnpm --dir frontend run dev  # start UI, then stop backend and open gallery to observe demo fallback despite failed fetch
  dependencies:
    - frontend dev server
  notes: Add a visible “backend offline” state and disable demo assets during MVP validation.

- finding_id: FINDING-2026-03-04-006
  area: core-loop
  severity: WARN
  title: Documents UI preloads mock/cached docs, hiding backend regressions
  description: AppShell seeds documents with mock entries and cached localStorage state before backend load; if `/api/media/documents` fails, mock docs remain, obscuring true persistence state.
  evidence:
    - file: frontend/src/components/persona/layout/AppShell.tsx
      lines: "557-624"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: Backend list becomes source of truth for MVP mode; mock docs only via explicit demo switch.
  suggested_commands:
    - pnpm --dir frontend run dev  # start UI with backend down to confirm mock docs remain in documents view
  dependencies:
    - frontend dev server
  notes: Pair with a lightweight “documents source” banner to flag cached/demo data.

- finding_id: FINDING-2026-03-04-007
  area: performance
  severity: WARN
  title: Chat completion hard-depends on Redis queue without graceful fallback
  description: `/api/chat/{thread_id}/complete` enqueues to `codexify:queue:chat`; on enqueue failure it returns 503 and leaves no sync fallback, so RAG loop requires Redis + worker running.
  evidence:
    - file: guardian/routes/chat.py
      lines: "1123-1143"
    - file: guardian/workers/chat_worker.py
      lines: "134-165"
  relates_to_core_loop: rag
  suggested_task_outcome: Deterministic local profile that runs completions synchronously when queue unavailable, or explicit health gate in validation harness.
  suggested_commands:
    - GUARDIAN_API_KEY=test redis-cli shutdown || true
    - GUARDIAN_API_KEY=test curl -s -X POST http://localhost:8000/api/chat/1/complete -H "X-API-Key: $GUARDIAN_API_KEY" -H "content-type: application/json" -d '{}' | jq .
  dependencies:
    - Redis
    - chat worker
  notes: Document required services in the core loop harness runner.

- finding_id: FINDING-2026-03-04-008
  area: security
  severity: WARN
  title: Legacy rag_upload route is unauthenticated and duplicates migration surface
  description: `guardian/routes/rag_upload.py` exposes upload-chatgpt-export without API-key dependency; if registered it bypasses auth and duplicates the canonical migration route, increasing attack surface.
  evidence:
    - file: guardian/routes/rag_upload.py
      lines: "70-159"
  relates_to_core_loop: migration
  suggested_task_outcome: Remove or explicitly quarantine rag_upload.py; ensure only `guardian/routes/migration.py` is mounted.
  suggested_commands:
    - rg -n "rag_upload" guardian/guardian_api.py
  dependencies: []
  notes: Currently appears unmounted; keep it dead or delete.

- finding_id: FINDING-2026-03-04-009
  area: security
  severity: INFO
  title: Media URL signing is optional and skipped when secret is unset
  description: `sign_media_url` returns raw paths if GUARDIAN_MEDIA_URL_SECRET/SESSION_SECRET/API_KEY are absent, so media URLs may be unprotected if served directly from /media without additional access control.
  evidence:
    - file: guardian/core/media_signing.py
      lines: "14-89"
  relates_to_core_loop: image-gallery
  suggested_task_outcome: Enforce media signing in environments that expose /media, or document that /media is behind API auth only.
  suggested_commands:
    - GUARDIAN_API_KEY=test python - <<'PY'\nfrom guardian.core.media_signing import sign_media_url\nprint(sign_media_url('/media/test.png'))\nPY
  dependencies:
    - GUARDIAN_MEDIA_URL_SECRET
  notes: If static file serving is disabled externally, this may be low risk; verify deployment path.

- finding_id: FINDING-2026-03-04-010
  area: core-loop
  severity: WARN
  title: Embedding backend requires local model or fallback flag; failures abort uploads
  description: Default embeddings backend is SentenceTransformer; missing model or missing `CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK` raises runtime errors, causing document upload embedding to fail.
  evidence:
    - file: backend/rag/embedder.py
      lines: "54-80"
    - file: backend/rag/embedder.py
      lines: "182-193"
  relates_to_core_loop: doc-upload
  suggested_task_outcome: Bundle/test a local embedding model path or set fallback to mock in dev harness; ensure upload route handles embed failure gracefully.
  suggested_commands:
    - CODEXIFY_EMBEDDINGS_BACKEND=sentence_transformer CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=0 python - <<'PY'\nfrom backend.rag.embedder import Embedder\nEmbedder(store='faiss')\nprint('embedder initialized')\nPY
  dependencies:
    - CODEXIFY_EMBEDDINGS_BACKEND
    - CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK
  notes: Pair with tests in tests/routes/test_media_routes.py to ensure deterministic behavior.
```

## Executive Summary (top 5)
- [RISK] LLM provider defaults to local but LOCAL_BASE_URL is mandatory, so chat/doc generation 400s by default (FINDING-2026-03-04-001).
- [RISK] Image generation lacks a working local provider and requires provider/model env + egress, blocking the image-gen loop (FINDING-2026-03-04-003).
- [WARN] Cloud egress is deny-by-default; without allowlist, OpenAI/Groq/minimax calls return 403 and loops relying on them stall (FINDING-2026-03-04-002).
- [WARN] Media stack assumes Postgres at db:5432; no sqlite/dev fallback for uploads/lists (FINDING-2026-03-04-004).
- [WARN] Gallery UI renders demo assets when backend fails, masking persistence issues and preventing loop validation (FINDING-2026-03-04-005).

## System Overview
- **Chat (RAG loop)** – Implemented; async queue worker persists messages and emits task events (guardian/routes/chat.py:768-1147; guardian/workers/chat_worker.py:134-165). Depends on Redis + LLM provider config.
- **Migration (ChatGPT import)** – Implemented with API-key auth and ingestion stats (guardian/routes/migration.py:30-52; backend/rag/chatgpt_migration.py:1020-1073). Duplicate legacy module remains (rag_upload.py).
- **Media Upload (docs/images)** – Implemented with auth dependency and dedupe/signing (guardian/routes/media.py:105-1773). Requires Postgres and embedding backend.
- **Image Generation** – Implemented in API but local provider stubbed; needs provider/model env (guardian/routes/media.py:1223-1410; guardian/image_gen/router.py; providers/local.py).
- **Document Generation** – Implemented with API-key auth and persistence link (guardian/routes/documents.py:253-393); relies on chat_with_ai provider config.
- **Frontend Chat/Gallery/Documents** – Chat UI consumes task_id and live events (frontend/src/features/chat/GuardianChat.tsx:534-579). Gallery and documents views currently fall back to demo/local cache (GalleryView.tsx; AppShell.tsx).
- **Auth** – API key enforced via require_api_key/verify_api_key; media router applies header guard to all routes (guardian/core/dependencies.py:420-447; guardian/routes/media.py:96-105).
- **Storage** – Local storage provider default at /app/media; HMAC signing optional (guardian/core/storage.py:167-215; guardian/core/media_signing.py:14-89).
- **Egress control** – Deny-by-default allowlist with CLOUD toggle (guardian/core/egress.py:65-87) applied in ai_router and image_gen providers.

Subsystem status: Chat (Implemented), Migration (Implemented), Media Upload (Implemented), Image Generation (Partial), Document Generation (Implemented), Gallery UI (Partial), Docs UI (Partial), Egress Control (Implemented), Storage (Implemented), Queue/Workers (Implemented).

## Security / Privacy / Sovereignty
- **Secrets management**: GUARDIAN_API_KEY required at startup; dotenv chain loaded in order (.env, .env.backend.<mode>, .env.local) unless CODEXIFY_DISABLE_DOTENV is set (guardian/core/dependencies.py:64-99, 112-131).
- **Access control**: Chat, migration, media, document routes require API key; legacy rag_upload lacks auth (guardian/routes/rag_upload.py:70-159).
- **Data egress map** (deny-by-default via guardian/core/egress.py):
  | Surface | Target | Gate | Evidence |
  | --- | --- | --- | --- |
  | Chat/doc-gen (ai_router) | Groq | assert_egress_allowed("groq") | guardian/core/ai_router.py:473-506 |
  | Chat/doc-gen (ai_router) | OpenAI | assert_egress_allowed("openai") | guardian/core/ai_router.py:508-525 |
  | Chat/doc-gen (ai_router) | Minimax | assert_egress_allowed("minimax") | guardian/core/ai_router.py:626-632 |
  | Image generation | OpenAI/Stability/local | assert_egress_allowed in provider | guardian/image_gen/providers/openai.py:18-67 |
  | Embeddings | Local/Mock | No cloud calls by default | backend/rag/embedder.py:54-80 |
- **Sovereignty defaults**: CODEXIFY_LOCAL_ONLY_MODE defaults true; ALLOW_CLOUD_PROVIDERS defaults false (guardian/core/egress.py:65-87), keeping traffic local unless explicitly allowed.
- **Media protection**: sign_media_url uses GUARDIAN_MEDIA_URL_SECRET/SESSION_SECRET/API_KEY; if unset, paths are unsigned (guardian/core/media_signing.py:14-70). Static serving policy should enforce auth or enable signing.

## Docs ↔ Code Consistency
- Gallery/doc views ship demo/cached data but docs don’t warn that backend persistence may be masked (frontend/src/components/gallery/GalleryView.tsx:70-182; frontend/src/components/persona/layout/AppShell.tsx:557-624).
- SECURITY.md claims “API key protects endpoints”; true for active routers, but rag_upload.py remains unauthenticated dead code (guardian/routes/rag_upload.py:70-159).
- Recent MVP roadmap (2026-02-24) still lists image-gen as placeholder; code now has provider router but local provider is still a stub (guardian/image_gen/providers/local.py:17-22).

## Code Quality / Testing / DX
- Test harness: `scripts/validate_core_loops.sh` runs six selectors for loops (scripts/validate_core_loops.sh:12-66).
- Unit/integration tests cover migration, media upload, image generation, document generation, RAG loop (tests/routes/test_migration_routes.py; tests/routes/test_media_routes.py; guardian/tests/test_document_gen_persist_and_link.py; tests/integration/test_rag_integration_loop.py).
- DX commands: `make test`, `make lint`, `make dev` (Makefile:1-120). Media tests set DATABASE_URL to sqlite for isolation (tests/routes/test_media_routes.py:13-38).
- Frontend auth helper automatically injects API key or bearer token (frontend/src/lib/api.ts:152-176).

## Performance & Scalability
- Chat completion is queue-driven; latency tied to Redis and worker throughput (guardian/routes/chat.py:1123-1157).
- Embedding pipeline uses FAISS/Chroma via LocalSemanticEmbedder; defaults to sentence-transformer with optional fallback (backend/rag/embedder.py:54-200).
- No explicit rate limiting; SlowAPI not yet integrated.
- Media storage uses local filesystem; S3/GCS providers available via create_storage_from_env (guardian/core/storage.py).

## Risk Register (top issues)
| ID | Severity | Area | Summary | Evidence |
| --- | --- | --- | --- | --- |
| FINDING-2026-03-04-001 | RISK | Core-loop | Chat/doc-gen 400 without LOCAL_BASE_URL; provider defaults to local | guardian/core/ai_router.py:18-30,142-147 |
| FINDING-2026-03-04-003 | RISK | Core-loop | Image-gen lacks local impl; provider/model env required | guardian/image_gen/providers/local.py:17-22; guardian/image_gen/router.py:18-42 |
| FINDING-2026-03-04-002 | WARN | Sovereignty | Cloud egress denied unless allowlist set; cloud loops return 403 | guardian/core/egress.py:65-87; guardian/core/ai_router.py:473-520 |
| FINDING-2026-03-04-004 | WARN | Core-loop | Media routes assume Postgres at db:5432; no sqlite fallback | guardian/routes/media.py:205-223 |
| FINDING-2026-03-04-005 | WARN | Core-loop | Gallery demo fallback hides backend failures | frontend/src/components/gallery/GalleryView.tsx:70-182 |
| FINDING-2026-03-04-006 | WARN | Core-loop | Documents view seeds mock/cache before backend | frontend/src/components/persona/layout/AppShell.tsx:557-624 |
| FINDING-2026-03-04-007 | WARN | Performance | Chat completion hard-depends on Redis queue | guardian/routes/chat.py:1123-1143; guardian/workers/chat_worker.py:134-165 |
| FINDING-2026-03-04-008 | WARN | Security | Legacy rag_upload endpoint lacks auth, duplicates migration | guardian/routes/rag_upload.py:70-159 |
| FINDING-2026-03-04-009 | INFO | Security | Media URL signing skipped when secret unset | guardian/core/media_signing.py:14-89 |
| FINDING-2026-03-04-010 | WARN | Core-loop | Embedding backend fails without model or fallback flag | backend/rag/embedder.py:54-80,182-193 |

## Recommendations (high-level)
1. Wire a deterministic LLM profile: enforce LOCAL_BASE_URL validation at startup or ship a local model + doc to unblock chat/doc-gen (FINDING-2026-03-04-001).
2. Provide an offline image generator or documented OpenAI/Stability profile with allowlist scaffolding; add an integration test that persists a generated asset (FINDING-2026-03-04-003).
3. Harden media stack defaults: require DATABASE_URL in dev env and add health checks; surface failures in UI instead of demo fallbacks (FINDING-2026-03-04-004/005/006).
4. Keep deny-by-default egress but ship minimal allowlist snippets per provider and ensure image-gen/doc-gen validation covers both local and cloud paths (FINDING-2026-03-04-002).
5. Quarantine or delete rag_upload.py; ensure core loop harness asserts only authenticated routes are mounted (FINDING-2026-03-04-008).
