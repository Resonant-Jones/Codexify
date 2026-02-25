# Codexify MVP Roadmap and Core Loop Plan (2026-02-24)

## Overview and Goals
This plan closes six core loops end-to-end for local MVP under the constraint:
- "Works locally with documented env vars/services configured" is acceptable.
- Production hardening is deferred unless it blocks deterministic local loop closure.

Authoritative gap references use finding IDs from `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/docs/reports/codexify-system-audit-2026-02-24.md`.

Loop closure requirements for every core loop:
1. Auth outside dev proxy for mutating actions.
2. Persistence via backend list/read API as source of truth.
3. Deterministic validation path (manual script and automated test).

## Core Feature 1: RAG Chat (`rag`)
### Current State
- Async completion endpoint returns `task_id` only (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py:554-628`).
- Worker persists assistant messages and emits events (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/workers/chat_worker.py:323-356`).
- Frontend completion handler still expects immediate `context` (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/features/chat/GuardianChat.tsx:104-120`).
- Chat mutating routes are unauthenticated (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/chat.py:356-742`).

### Core Loop Definition
1. User creates/selects thread.
2. User submits message.
3. Completion is queued and processed.
4. Assistant message persists to DB.
5. UI reflects final assistant response from backend data/events.

### Gap Analysis
| Loop step | Current implementation | Gap | Concrete fix |
|---|---|---|---|
| 2 | `/chat/{thread_id}/messages` accepts writes | No auth boundary | Add `require_api_key` for mutating chat routes (FINDING-2026-02-24-002). |
| 3 | `/chat/{thread_id}/complete` returns `{task_id}` | Frontend expects sync `context` payload | Align contract: either async task flow end-to-end or sync completion; remove hybrid assumptions (FINDING-2026-02-24-007). |
| 5 | Tests assume old behavior and fail without Redis | Validation not deterministic locally | Add explicit queue fixture/mock profile for route tests; keep compose-backed integration profile separately (FINDING-2026-02-24-008). |

### Implementation Tasks
1. Enforce API key dependency on chat mutating handlers.
2. Choose completion contract and update backend + frontend + tests in one atomic change.
3. Add test fixtures to emulate queue publish success/failure deterministically.

### Validation Plan
- Manual:
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8000/chat/threads -H "content-type: application/json" -d '{"title":"mvp"}'`
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8000/chat/<thread_id>/complete -H "content-type: application/json" -d '{}'`
- Automated:
  - `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_chat_routes.py`
  - `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_chat_system_prompt_integration.py`

## Core Feature 2: ChatGPT Migration (`migration`)
### Current State
- Active route: `/upload-chatgpt-export` in `guardian/routes/migration.py` with API key dependency.
- Ingestion return keys do not match route expectations (`threads/messages` vs `threads_imported/messages_imported`).
- Legacy duplicate route remains in `guardian/routes/rag_upload.py`.

### Core Loop Definition
1. User uploads ChatGPT export file.
2. Backend parses and imports threads/messages.
3. Import statistics returned.
4. Imported data visible in chat thread listings.

### Gap Analysis
| Loop step | Current implementation | Gap | Concrete fix |
|---|---|---|---|
| 3 | Route maps wrong stats keys | Runtime failure path | Normalize stats schema in one place; route and ingest function agree (FINDING-2026-02-24-005). |
| 1-4 | Two endpoint implementations exist | Drift/confusion risk | Remove or deprecate `rag_upload` duplicate route (FINDING-2026-02-24-006). |

### Implementation Tasks
1. Standardize migration stats payload shape.
2. Add migration route tests for happy path and malformed file.
3. Remove stale route or make it call canonical implementation.

### Validation Plan
- Manual:
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" -F "file=@fixtures/chatgpt_export.json" http://localhost:8000/upload-chatgpt-export`
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8000/chat/threads`
- Automated:
  - Add/extend `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_migration_routes.py` (or existing migration test module).

## Core Feature 3: Document Upload (`doc-upload`)
### Current State
- Backend upload/list endpoints exist (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:257-367`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:582-622`).
- Frontend uploader writes local state and optional external ingestion endpoint (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/hooks/useUploader.ts:46-117`).
- App shell persists docs in localStorage (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/persona/layout/AppShell.tsx:414-431`).
- Dashboard consumes wrong response shape for `/api/media/documents`.

### Core Loop Definition
1. User uploads a document.
2. Backend stores metadata/blob reference.
3. Document appears in backend list endpoint.
4. UI reload shows uploaded doc from backend list.

### Gap Analysis
| Loop step | Current implementation | Gap | Concrete fix |
|---|---|---|---|
| 1 | Upload UI often local-only path | Backend persistence optional, not canonical | Route uploads through `/api/media/upload/document` by default (FINDING-2026-02-24-009). |
| 1 | Upload route unauthenticated | Auth closure requirement unmet | Add API key guard for media writes (FINDING-2026-02-24-003). |
| 4 | Dashboard maps `res.data` as array | API shape mismatch hides real docs | Read `res.data.documents` and test response handling (FINDING-2026-02-24-010). |

### Implementation Tasks
1. Make uploader default to backend media endpoint.
2. Harden media mutating routes with auth.
3. Fix dashboard response mapping.
4. Add upload/list integration test.

### Validation Plan
- Manual:
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" -F "file=@README.md" -F "project_id=1" -F "thread_id=1" http://localhost:8000/api/media/upload/document`
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8000/api/media/documents?limit=10"`
- Automated:
  - Extend `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_media_routes.py` for upload+list+auth behavior.

## Core Feature 4: Image Gallery (`image-gallery`)
### Current State
- Backend supports image upload/list (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:133-205`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:538-579`).
- UI uses demo image fallback and localStorage gallery state (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/gallery/GalleryView.tsx:10-53`, `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/frontend/src/components/persona/layout/AppShell.tsx:699-720`).

### Core Loop Definition
1. User uploads or generates image.
2. Backend stores image metadata/reference.
3. Gallery list endpoint returns canonical data.
4. UI gallery renders backend-derived assets.

### Gap Analysis
| Loop step | Current implementation | Gap | Concrete fix |
|---|---|---|---|
| 1 | Upload endpoints no auth | Auth closure requirement unmet | Add API key checks for image mutations (FINDING-2026-02-24-003). |
| 4 | Demo/local fallback can mask persistence issues | Loop appears closed even without backend state | Make backend list authoritative in MVP mode; explicit demo toggle only (FINDING-2026-02-24-011). |

### Implementation Tasks
1. Enforce auth on image upload/delete/generate paths.
2. Load gallery from `/api/media/images` on startup.
3. Keep demo data behind explicit dev-only flag.

### Validation Plan
- Manual:
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8000/api/media/images?limit=20"`
- Automated:
  - Add backend route tests in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_media_routes.py`.
  - Add frontend integration test to assert backend images render when available.

## Core Feature 5: Image Generation (`image-gen`)
### Current State
- Endpoint exists but is explicitly placeholder (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/media.py:394-405`).

### Core Loop Definition
1. User submits prompt.
2. Image is generated by provider/local model.
3. Asset is persisted and listed.
4. Gallery displays generated image.

### Gap Analysis
| Loop step | Current implementation | Gap | Concrete fix |
|---|---|---|---|
| 2 | Placeholder only | No real generation | Integrate provider/local generation module; return real asset URL (FINDING-2026-02-24-012). |
| 3-4 | Synthetic path only | Not persisted/reloadable | Store generated image via same media storage and list APIs. |

### Implementation Tasks
1. Wire route to actual image generator implementation.
2. Persist output through `UploadedImage` pipeline.
3. Add tests for generation success/failure.

### Validation Plan
- Manual:
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8000/api/media/generate/image -H "content-type: application/json" -d '{"prompt":"sunset test","project_id":1,"thread_id":1}'`
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8000/api/media/images`
- Automated:
  - Route tests for generation stub replacement in `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_media_routes.py`.

## Core Feature 6: Document Generation (`doc-gen`)
### Current State
- GeneratedDocument model exists (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/db/models.py:532-564`).
- Autosave endpoint exists for thread notes (`/Users/resonant_jones/.codex/worktrees/ae18/Codexify/guardian/routes/documents.py:63-197`).
- No explicit generation endpoint found.

### Core Loop Definition
1. User requests generated doc from prompt/context.
2. Backend runs generation.
3. Generated document persists as `GeneratedDocument`.
4. Documents list surfaces generated item.

### Gap Analysis
| Loop step | Current implementation | Gap | Concrete fix |
|---|---|---|---|
| 1-2 | No generation endpoint | Core loop cannot start | Add `/api/documents/generate` endpoint (FINDING-2026-02-24-013). |
| 4 | No explicit generated-doc listing contract in UI | No deterministic validation path | Extend document listing/filters for generated docs and test. |

### Implementation Tasks
1. Implement minimal generate endpoint using existing LLM abstraction.
2. Persist records into `GeneratedDocument` + linking table.
3. Add route tests for success/error/auth.

### Validation Plan
- Manual:
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8000/api/documents/generate -H "content-type: application/json" -d '{"thread_id":1,"title":"Summary","prompt":"Summarize this thread"}'`
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8000/api/media/documents`
- Automated:
  - New tests under `/Users/resonant_jones/.codex/worktrees/ae18/Codexify/tests/routes/test_documents_generate.py`.

## Milestones and Timeline
- M0: Security and contract stabilization
  - Close auth gaps for chat/media/projects/connectors admin.
  - Remove/rotate tracked and hardcoded secrets.
- M1: RAG loop closure
  - Unify completion contract, make tests deterministic.
- M2: Migration and doc-upload closure
  - Fix migration stats mismatch; canonicalize endpoint.
  - Backend-authoritative document upload/list UX.
- M3: Image gallery closure
  - Backend-authoritative gallery, demo fallback opt-in only.
- M4: Image generation closure
  - Replace placeholder generation with real provider/local implementation.
- M5: Document generation closure + polish
  - Add document generation endpoint, route tests, and docs alignment.

## Risks, Assumptions, Dependencies
- Assumption: Local compose services (Postgres, Redis, optional workers) are available for integration validation.
- Assumption: API key auth is required for mutating endpoints in MVP outside explicit dev-only contexts.
- Dependency: Queue worker availability for async chat completion path.
- Dependency: LLM/image provider credentials or local model runtime for generation loops.
- Risk: Existing docs/config drift can cause repeated misconfiguration if not fixed early (FINDING-2026-02-24-017).

## Deferred Features (parking lot)
- Multi-tenant RBAC and fine-grained policy engine.
- End-to-end secret management platform integration (Vault/KMS).
- Full production SLO/performance benchmarking suite.
- Advanced provenance/lineage UI for all generated artifacts.
- Non-MVP connectors and federation trust hardening beyond local loop closure.
