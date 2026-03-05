# Codexify MVP Roadmap & Core Loop Plan (2026-03-04)

## Overview & Goals
Close six core loops end-to-end for local MVP under the rule: “works locally with documented env vars/services configured” is sufficient. Every gap below maps to a Runner-Ready Finding in the audit manifest.

### Core Loop Status Snapshot
| Core Loop | Code Present | Loop Closed | Notes |
| --- | --- | --- | --- |
| RAG Chat (`rag`) | complete | no | Needs LOCAL_BASE_URL + Redis worker health (FINDING-2026-03-04-001, -007). |
| ChatGPT Migration (`migration`) | complete | yes | API-key protected import path (guardian/routes/migration.py). |
| Document Upload (`doc-upload`) | complete | no | Postgres/embedding required; UI caches mock docs (FINDING-2026-03-04-004, -006, -010). |
| Image Gallery (`image-gallery`) | partial | no | Demo fallback masks backend state (FINDING-2026-03-04-005). |
| Image Generation (`image-gen`) | partial | no | Local provider stub, provider/model env required (FINDING-2026-03-04-003, -002). |
| Document Generation (`doc-gen`) | complete | no | Shares LLM provider gap with chat/doc-gen (FINDING-2026-03-04-001, -002). |

---

## Core Feature 1: RAG Chat (`rag`)
**Current State (evidence):**
- Chat routes enforce API key and enqueue completion tasks (guardian/routes/chat.py:768-1157).
- Worker persists assistant messages and emits task.completed events (guardian/workers/chat_worker.py:134-165).
- Frontend expects task_id async flow (frontend/src/features/chat/GuardianChat.tsx:534-579).

**Core Loop Definition**
1. User creates/selects thread.
2. User posts message (persisted to DB).
3. Completion task enqueued and processed by worker.
4. Assistant message persisted and events emitted.
5. UI reloads from backend list/events.

**Gap Analysis**
| Loop step | Current implementation | Gap | Concrete fix (Finding) |
| --- | --- | --- | --- |
| 3-4 | Provider defaults to `local`; missing LOCAL_BASE_URL returns 400 | Loop blocked by default env | Add startup check + sample env for LOCAL_BASE_URL/LOCAL_LLM_MODEL or allowlisted cloud provider (FINDING-2026-03-04-001). |
| 3 | Completion hard-depends on Redis enqueue | No graceful local fallback | Add sync mode for dev harness or health gate in core-loop runner (FINDING-2026-03-04-007). |
| 3-5 | Cloud providers 403 without allowlist | Cloud path unusable by default | Document minimal allowlist; add cloud profile tests (FINDING-2026-03-04-002). |

**Implementation Tasks**
1. Add startup validation for LOCAL_BASE_URL (fail-fast with actionable message).  
2. Implement `QUEUE_MODE=sync` for dev harness to bypass Redis when unavailable.  
3. Document cloud allowlist snippet and add env sample for Groq/OpenAI.  

**Validation Plan**
- Manual:  
  - `GUARDIAN_API_KEY=test LOCAL_BASE_URL=http://localhost:11434 curl -s -X POST http://localhost:8000/api/chat/1/complete -H "X-API-Key: $GUARDIAN_API_KEY" -H "content-type: application/json" -d '{}'`  
- Automated:  
  - `pytest -q tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`  
  - `bash scripts/validate_core_loops.sh --dry-run` to verify selectors.

## Core Feature 2: ChatGPT Migration (`migration`)
**Current State:** Authenticated import route returns stats and writes messages/embeddings (guardian/routes/migration.py:30-52; backend/rag/chatgpt_migration.py:1020-1073). Tests cover canonical and legacy paths (tests/routes/test_migration_routes.py:76-207).

**Core Loop Definition**
1. User uploads ChatGPT export.
2. Backend parses, creates threads/messages.
3. Stats returned.
4. Imported threads visible via `/api/chat/threads`.

**Gap Analysis**
| Loop step | Current implementation | Gap | Concrete fix (Finding) |
| --- | --- | --- | --- |
| 1-3 | Legacy rag_upload module exists | Unauth duplicate could be mounted accidentally | Remove/quarantine rag_upload.py (FINDING-2026-03-04-008). |

**Implementation Tasks**
1. Delete or quarantine `guardian/routes/rag_upload.py`; assert not included in router wiring.  

**Validation Plan**
- Manual: `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" -F "file=@fixtures/chatgpt_export.json" http://localhost:8000/api/upload-chatgpt-export`  
- Automated: `pytest -q tests/routes/test_migration_routes.py::test_migration_route_executes_real_ingest_and_embeds`

## Core Feature 3: Document Upload (`doc-upload`)
**Current State:** Media router requires API key; document upload persists asset and enqueues embed (guardian/routes/media.py:105-1773). Frontend uploader posts to backend and falls back to local preview if upload fails (frontend/src/hooks/useUploader.ts:330-520). Documents view seeds mock/cache before backend list (frontend/src/components/persona/layout/AppShell.tsx:557-724).

**Core Loop Definition**
1. User uploads a document.
2. Backend stores asset + embedding task.
3. List endpoint surfaces stored doc.
4. UI renders backend documents list.

**Gap Analysis**
| Loop step | Current implementation | Gap | Concrete fix (Finding) |
| --- | --- | --- | --- |
| 2 | DB fallback is Postgres at db:5432 | Dev without DB fails silently | Require DATABASE_URL or add sqlite fallback for media routes (FINDING-2026-03-04-004). |
| 2 | Embedding backend requires model | Upload fails if model missing | Ship local model or default mock fallback in dev profile (FINDING-2026-03-04-010). |
| 4 | UI seeds mock/cache docs | Backend failures masked | Add “demo mode” toggle + error banner; disable mock docs in MVP validation (FINDING-2026-03-04-006). |

**Implementation Tasks**
1. Add explicit dev DATABASE_URL sample and health check for media DB.  
2. Bundle a small local embedding model path or set CODEXIFY_ALLOW_EMBEDDINGS_FALLBACK=1 in dev harness.  
3. Add UI flag `CFY_DEMO_DOCS` default false in MVP; surface backend fetch errors.  

**Validation Plan**
- Manual:  
  - `GUARDIAN_API_KEY=test DATABASE_URL=sqlite:///./guardian_media.db curl -s -F "file=@README.md" -F "project_id=1" http://localhost:8000/api/media/upload/document`  
  - `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8000/api/media/documents?limit=10"`  
- Automated:  
  - `pytest -q tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_upload_document_enqueues_embedding_with_asset_metadata`

## Core Feature 4: Image Gallery (`image-gallery`)
**Current State:** Backend list endpoints return uploaded/generated images (guardian/routes/media.py:1611-1702). Gallery view fetches `/api/media/images` but falls back to demo items on failure (frontend/src/components/gallery/GalleryView.tsx:70-182).

**Core Loop Definition**
1. User uploads or generates image.
2. Backend stores and lists images.
3. UI fetches list.
4. UI renders backend-derived items.

**Gap Analysis**
| Loop step | Current implementation | Gap | Concrete fix (Finding) |
| --- | --- | --- | --- |
| 3-4 | Demo fallback on fetch failure | Backend not authoritative | Add explicit demo toggle; fail visibly when fetch fails (FINDING-2026-03-04-005). |

**Implementation Tasks**
1. Add `CFY_DEMO_GALLERY=false` default; show offline banner and empty-state when fetch fails.  
2. Frontend test to assert backend images render when API is up and demo flag off.  

**Validation Plan**
- Manual: `curl -s -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8000/api/media/images?limit=10"`  
- Automated: add Playwright/RTL test that stubs images API and asserts gallery shows backend data, not demo.

## Core Feature 5: Image Generation (`image-gen`)
**Current State:** Route saves generated bytes to storage and links GeneratedImage (guardian/routes/media.py:1223-1410). ImageGenRouter requires IMAGE_GEN_PROVIDER/MODEL; local provider raises 503 (guardian/image_gen/router.py:18-42; providers/local.py:17-22). Tests mock provider (tests/routes/test_media_routes.py:49-118).

**Core Loop Definition**
1. User submits prompt.
2. Image is generated by provider.
3. Asset persisted and listed.
4. Gallery displays generated image.

**Gap Analysis**
| Loop step | Current implementation | Gap | Concrete fix (Finding) |
| --- | --- | --- | --- |
| 2 | Local provider unimplemented | Loop blocked offline | Implement local generator or ship documented OpenAI/Stability config (FINDING-2026-03-04-003). |
| 2-3 | Cloud egress denied by default | 403 until allowlist set | Provide allowlist templates and env samples (FINDING-2026-03-04-002). |

**Implementation Tasks**
1. Add minimal local generator (e.g., placeholder PNG) for offline validation, gated by CODEXIFY_BETA_CORE_ONLY.  
2. Provide `IMAGE_GEN_PROVIDER=openai` example with allowlist/env sample and add integration test that persists an asset when provider is available.  

**Validation Plan**
- Manual:  
  - Local stub: `IMAGE_GEN_PROVIDER=local curl -s -X POST http://localhost:8000/api/media/generate/image -H "X-API-Key: $GUARDIAN_API_KEY" -H "content-type: application/json" -d '{"prompt":"smoke","project_id":1,"thread_id":1}'`  
  - OpenAI path: set allowlist/env, repeat curl and verify listing shows new image.  
- Automated: extend `tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_success` to run with real provider when configured.

## Core Feature 6: Document Generation (`doc-gen`)
**Current State:** `/api/documents/generate` persists GeneratedDocument + ThreadDocument link with API-key auth (guardian/routes/documents.py:253-393); tests cover persistence (guardian/tests/test_document_gen_persist_and_link.py:61-119). Uses chat_with_ai provider (guardian/core/ai_router.py:104-139).

**Core Loop Definition**
1. User requests generated doc.
2. LLM produces content.
3. Document stored and linked.
4. UI lists generated doc.

**Gap Analysis**
| Loop step | Current implementation | Gap | Concrete fix (Finding) |
| --- | --- | --- | --- |
| 2 | Provider defaults to local; LOCAL_BASE_URL required | 400 by default | Add provider config sample and startup validation (FINDING-2026-03-04-001). |
| 2 | Cloud providers 403 without allowlist | Cloud path blocked | Document allowlist + add cloud profile test (FINDING-2026-03-04-002). |

**Implementation Tasks**
1. Share chat/doc-gen provider bootstrap (LOCAL_BASE_URL or allowlisted cloud) in `.env.example`.  
2. Add doc-gen cloud profile test that asserts 403->200 when allowlist/env provided.  

**Validation Plan**
- Manual: `LOCAL_BASE_URL=http://localhost:11434 GUARDIAN_API_KEY=test curl -s -X POST http://localhost:8000/api/documents/generate -H "X-API-Key: $GUARDIAN_API_KEY" -H "content-type: application/json" -d '{"thread_id":1,"prompt":"draft me a note"}'`  
- Automated: `pytest -q guardian/tests/test_document_gen_persist_and_link.py::test_document_generate_persists_and_links`

---

## Milestones & Timeline (sequence)
- **M0 – Config gate**: Enforce LOCAL_BASE_URL check, add dev DATABASE_URL sample, expose egress allowlist templates (Findings 001, 002, 004).  
- **M1 – Deterministic dev profile**: Queue sync mode, embedding fallback/mock, demo flags default off in UI (Findings 006, 007, 010).  
- **M2 – Migration hygiene**: Remove rag_upload; rerun migration tests and harness (Finding 008).  
- **M3 – Media persistence**: Gallery/doc views honor backend as source of truth; error banners + tests (Findings 005, 006).  
- **M4 – Image generation**: Ship local generator or documented cloud path; add integration test and harness step (Findings 003, 002).  
- **M5 – End-to-end validation**: Run `scripts/validate_core_loops.sh` in both sync and queue modes; add CI target.

## Risks / Assumptions / Dependencies
- Redis + worker required for chat completions unless sync mode added (Finding 007).
- LLM inference endpoint (local or cloud) must be reachable; otherwise chat/doc-gen fail (Finding 001/002).
- Postgres service required for media/doc/image persistence unless sqlite fallback added (Finding 004).
- Embedding model availability gates doc uploads; mock fallback acceptable for MVP (Finding 010).

## Deferred Features (parking lot)
- Rate limiting / SlowAPI integration.
- Production media signing enforcement (Finding 009) once deployment topology is fixed.
- Graph/Neo4j sync beyond current optional hook.
