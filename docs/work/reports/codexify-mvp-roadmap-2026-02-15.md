# Codexify MVP Roadmap & Core Loop Plan (2026-02-15)

## Overview & Goals
- Goal: close all 6 core loops (`rag`, `migration`, `doc-upload`, `image-gallery`, `image-gen`, `doc-gen`) end-to-end for local MVP usage.
- MVP acceptance: local operation is acceptable with documented env vars/services configured.
- Closure gates for every loop:
  1. Auth works outside dev proxy.
  2. Output is persisted and retrievable via backend list endpoint.
  3. Deterministic validation path exists and is executable.
- Authoritative gap source: `docs/work/reports/codexify-system-audit-2026-02-15.md` findings manifest.

---

## 1) RAG Loop (`rag`)
### Current State
- Chat thread/message persistence and async completion worker are implemented (`guardian/routes/chat.py:425-431`, `guardian/routes/chat.py:634-764`, `guardian/workers/chat_worker.py:382-395`).
- RAG trace retrieval exists (`guardian/routes/chat.py:1102-1125`).
- Deterministic integration exists but relies on stubs/monkeypatching (`tests/integration/test_rag_integration_loop.py:21-37`, `tests/integration/test_rag_integration_loop.py:177-197`).

### Core Loop Definition
1. Create/select thread.
2. Post user message.
3. Persist message.
4. Embed message.
5. Request completion.
6. Worker assembles context + generates response.
7. Persist assistant response.
8. List messages and verify retrieved context influenced output.

### Gap Analysis
| Loop step | Current impl | Gap | Concrete fix | Finding |
|---|---|---|---|---|
| 1-2 auth | Frontend API helper | Env/key contract drift breaks non-proxy auth | Unify frontend auth env contract and implement `forceApiKey` behavior | FINDING-2026-02-15-003 |
| 6-8 validation | Deterministic integration test | Uses in-memory stubs, not real stack | Add docker-backed deterministic profile (db+redis+backend worker) | FINDING-2026-02-15-008 |

### Implementation Tasks
- `RAG-1`: Canonicalize frontend auth env (`VITE_GUARDIAN_API_KEY` vs `VITE_GUARDIAN_DEV_API_KEY`) and header injection contract.
- `RAG-2`: Implement `forceApiKey` option in `buildAuthenticatedFetchInit` and add tests.
- `RAG-3`: Add real-stack RAG loop test target under `tests/integration/` using actual API endpoints and persistence reads.

### Validation Plan
Manual:
```bash
curl -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/chat/threads
curl -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8888/chat/1/messages -H 'content-type: application/json' -d '{"role":"user","content":"Remember ORION-42"}'
curl -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8888/chat/1/complete -H 'content-type: application/json' -d '{"provider":"local"}'
curl -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/chat/1/messages
```
Automated:
- Keep: `tests/integration/test_rag_integration_loop.py::test_rag_integration_memory_loop`
- Add: `tests/integration/test_rag_loop_realstack.py` (new)

---

## 2) Migration Loop (`migration`)
### Current State
- Canonical endpoint and legacy alias are registered (`guardian/routes/migration.py:28-34`).
- Ingestion persists threads/messages and embeddings (`backend/rag/chatgpt_migration.py:426-433`, `backend/rag/chatgpt_migration.py:483-503`).
- Frontend modal uses canonical `/api/upload-chatgpt-export` (`frontend/src/components/modals/ChatGPTImportModal.tsx:73-75`).

### Core Loop Definition
1. User selects export JSON file.
2. Upload to migration endpoint.
3. Parse/validate file.
4. Persist threads/messages.
5. Embed imported content.
6. Show import stats.
7. Refresh thread list.

### Gap Analysis
| Loop step | Current impl | Gap | Concrete fix | Finding |
|---|---|---|---|---|
| 2 auth | Frontend modal + API helper | Cross-loop auth contract drift for non-proxy | Same auth contract fix as RAG | FINDING-2026-02-15-003 |
| 7 validation realism | Playwright test | Network is fully intercepted, not real backend | Add backend-connected migration E2E profile | FINDING-2026-02-15-008 |
| legacy path hygiene | Legacy settings component | Still posts `/upload-chatgpt-export` | Remove/align legacy settings component | FINDING-2026-02-15-013 |

### Implementation Tasks
- `MIG-1`: Reuse auth contract fix across migration modal.
- `MIG-2`: Add realstack migration test using test export fixture and verify persisted thread/message lists.
- `MIG-3`: Delete or refactor `frontend/src/components/settings/SettingsView.tsx` legacy migration call path.

### Validation Plan
Manual:
```bash
curl -H "X-API-Key: $GUARDIAN_API_KEY" -F "file=@test_chatgpt_export.json" -H "X-User-Id: default" http://localhost:8888/api/upload-chatgpt-export
curl -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/chat/threads
```
Automated:
- Keep: `tests/routes/test_migration_routes.py::test_migration_route_executes_real_ingest_and_embeds`
- Keep (UI behavior): `frontend/src/tests/playwright/migration_e2e_import.spec.ts`
- Add: backend-connected Playwright profile (no global route interception)

---

## 3) Document Upload Loop (`doc-upload`)
### Current State
- Upload endpoint persists document metadata and queues embedding (`guardian/routes/media.py:671-681`, `tests/routes/test_media_routes.py:275-336`).
- Backend list endpoint exists (`guardian/routes/media.py:1601-1667`).
- Frontend uploader integrates upload path and fallback handling (`frontend/src/hooks/useUploader.ts:391-487`).

### Core Loop Definition
1. Select document file.
2. Upload with project/thread scope.
3. Persist metadata/file.
4. Parse text and queue embedding.
5. List documents from backend.
6. Open document in UI context.

### Gap Analysis
| Loop step | Current impl | Gap | Concrete fix | Finding |
|---|---|---|---|---|
| 2 auth | `buildAuthenticatedFetchInit` callsites | forceApiKey contract currently ignored | Implement force-api-key behavior and align env contract | FINDING-2026-02-15-003 |
| 2-5 ownership | user_id supplied by caller | No server-derived ownership boundary | Derive user scope from auth principal; reject caller override | FINDING-2026-02-15-005 |
| 4 validation realism | Route tests patch DB/storage/embed | No realstack deterministic profile | Add compose-backed document upload test | FINDING-2026-02-15-008 |

### Implementation Tasks
- `DOCU-1`: Apply auth contract fix in uploader path.
- `DOCU-2`: Remove caller-trusted user ownership for media routes.
- `DOCU-3`: Add realstack upload->list->search deterministic test.

### Validation Plan
Manual:
```bash
curl -H "X-API-Key: $GUARDIAN_API_KEY" -F "file=@test.txt" -F "project_id=1" -F "thread_id=1" http://localhost:8888/api/media/upload/document
curl -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8888/api/media/documents?project_id=1&thread_id=1"
```
Automated:
- Keep: `tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_upload_document_enqueues_embedding_with_asset_metadata`
- Add: `tests/integration/test_document_upload_loop_realstack.py` (new)

---

## 4) Image Gallery Loop (`image-gallery`)
### Current State
- Backend list endpoint supports uploaded/generated filtering (`guardian/routes/media.py:1507-1598`).
- Frontend gallery reads backend list and supports source tabs (`frontend/src/components/gallery/GalleryView.tsx:69-82`, `frontend/src/components/gallery/GalleryView.tsx:140-148`).
- Deterministic route test exists (`tests/routes/test_media_routes.py:378-409`).

### Core Loop Definition
1. Upload or generate image.
2. Persist media asset.
3. Fetch list by tag/project/thread.
4. Render in gallery.

### Gap Analysis
| Loop step | Current impl | Gap | Concrete fix | Finding |
|---|---|---|---|---|
| 1/3 auth | Gallery fetch/uploader calls auth helper | Shared auth env drift + forceApiKey no-op | Same cross-loop auth fix | FINDING-2026-02-15-003 |
| 2 ownership | list filters accept caller user_id | Ownership not server-derived | Enforce server-side user scoping | FINDING-2026-02-15-005 |
| 3 validation realism | unit-style deterministic test | Not full stack | Add gallery realstack smoke test | FINDING-2026-02-15-008 |

### Implementation Tasks
- `GALL-1`: Apply auth contract fix for gallery list/upload calls.
- `GALL-2`: Enforce server-side ownership in list/write paths.
- `GALL-3`: Add realstack gallery validation (upload image -> list tag=uploaded).

### Validation Plan
Manual:
```bash
curl -H "X-API-Key: $GUARDIAN_API_KEY" -F "file=@test.jpg" -F "project_id=1" -F "thread_id=1" http://localhost:8888/api/media/upload/image
curl -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8888/api/media/images?project_id=1&thread_id=1&tag=uploaded"
```
Automated:
- Keep: `tests/routes/test_media_routes.py::TestUploadDedupeAndResolve::test_list_images_generated_tag_returns_generated`
- Add: `tests/integration/test_gallery_loop_realstack.py` (new)

---

## 5) Image Generation Loop (`image-gen`)
### Current State
- API route implemented (`guardian/routes/media.py:1128-1132`).
- OpenAI provider implemented; local/stability providers return 503 (`guardian/image_gen/providers/openai.py:14-76`, `guardian/image_gen/providers/local.py:17-23`, `guardian/image_gen/providers/stability.py:17-23`).
- Frontend modal posts generation request and emits gallery event (`frontend/src/components/modals/ImageGenModal.tsx:122-149`).

### Core Loop Definition
1. Submit prompt/model/scope.
2. Generate image via provider.
3. Persist generated image row.
4. List generated images.
5. Display in gallery.

### Gap Analysis
| Loop step | Current impl | Gap | Concrete fix | Finding |
|---|---|---|---|---|
| 1 auth | API helper path | Shared auth contract drift | Same cross-loop auth fix | FINDING-2026-02-15-003 |
| 2 provider | router supports 3 providers | local/stability not implemented | Implement one local provider path or mark cloud-only explicitly | FINDING-2026-02-15-006 |
| 1 scope integrity | backend/frontend default IDs to 1 | Scope pollution, non-determinism | Require explicit valid scope or derive from thread context | FINDING-2026-02-15-007 |
| 2-5 validation realism | mocked route tests | no real provider + persistence loop proof | Add deterministic provider stub mode + persistence/list verification | FINDING-2026-02-15-008 |

### Implementation Tasks
- `IMG-1`: Fix auth contract.
- `IMG-2`: Implement local provider or formalize cloud-only MVP requirement in docs/env.
- `IMG-3`: Remove silent project/thread fallback to `1`.
- `IMG-4`: Add loop test: generate -> list tag=generated -> render in gallery.

### Validation Plan
Manual:
```bash
curl -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8888/api/media/generate/image -H 'content-type: application/json' -d '{"prompt":"city skyline","model":"dall-e-3","project_id":1,"thread_id":1,"user_id":"default"}'
curl -H "X-API-Key: $GUARDIAN_API_KEY" "http://localhost:8888/api/media/images?tag=generated&project_id=1&thread_id=1"
```
Automated:
- Keep: `tests/routes/test_media_routes.py::TestImageGeneration::test_generate_image_success`
- Add: `tests/integration/test_image_gen_loop_realstack.py` (new)

---

## 6) Document Generation Loop (`doc-gen`)
### Current State
- Generation endpoint requires API key and persists generated document + thread link (`guardian/routes/documents.py:253-257`, `guardian/routes/documents.py:355-373`).
- Thread document list route exists but is unauthenticated (`guardian/routes/documents.py:396-397`).
- Frontend triggers generation via `api.post("/documents/generate", payload)` (`frontend/src/App.tsx:136-145`).

### Core Loop Definition
1. Open thread.
2. Submit document generation request.
3. Generate content.
4. Persist generated document and thread linkage.
5. List thread documents.
6. Open generated document in workspace.

### Gap Analysis
| Loop step | Current impl | Gap | Concrete fix | Finding |
|---|---|---|---|---|
| 2 auth | frontend API helper | Shared auth contract drift | Same cross-loop auth fix | FINDING-2026-02-15-003 |
| 5 auth consistency | list route without Depends | Access-control inconsistency | Add `Depends(require_api_key)` and auth tests | FINDING-2026-02-15-004 |
| 4 ownership | user identity may default/override | No principal-derived ownership | Derive ownership from auth | FINDING-2026-02-15-005 |

### Implementation Tasks
- `DOCG-1`: Fix frontend auth contract.
- `DOCG-2`: Protect `/api/threads/{thread_id}/documents` with auth dependency.
- `DOCG-3`: Add ownership derivation for generated docs from auth principal.
- `DOCG-4`: Add integration test with authenticated generate + authenticated list retrieval.

### Validation Plan
Manual:
```bash
curl -H "X-API-Key: $GUARDIAN_API_KEY" -X POST http://localhost:8888/api/documents/generate -H 'content-type: application/json' -d '{"thread_id":1,"prompt":"Create a launch brief","format":"markdown"}'
curl -H "X-API-Key: $GUARDIAN_API_KEY" http://localhost:8888/api/threads/1/documents
```
Automated:
- Keep: `guardian/tests/test_document_gen_endpoint.py`
- Keep: `guardian/tests/test_document_gen_persist_and_link.py`
- Extend: add explicit unauthenticated list-route failure test in `tests/routes/test_thread_documents.py`

---

## Milestones & Timeline
- **M0 (Day 0-1): Baseline integrity**
  - Resolve worktree drift hygiene (`FINDING-2026-02-15-001`, `FINDING-2026-02-15-002`).
  - Confirm tracked/clean startup path.
- **M1 (Day 1-3): Cross-loop auth contract closure**
  - Fix env key contract + `forceApiKey` behavior (`FINDING-2026-02-15-003`).
  - Re-run loop smoke checks.
- **M2 (Day 3-5): RAG + Migration hard closure**
  - Add realstack deterministic tests (`FINDING-2026-02-15-008`, `FINDING-2026-02-15-013`).
- **M3 (Day 5-7): Doc-upload + Image-gallery closure**
  - Ownership scoping + realstack tests (`FINDING-2026-02-15-005`, `FINDING-2026-02-15-008`).
- **M4 (Day 7-9): Image-gen + Doc-gen closure**
  - Fix provider/scope issues + protect thread-doc list route (`FINDING-2026-02-15-006`, `FINDING-2026-02-15-007`, `FINDING-2026-02-15-004`).
- **M5 (Day 9-10): Operational stabilization**
  - Outbox cleanup fix, docs alignment, final closure matrix regeneration (`FINDING-2026-02-15-009`, `FINDING-2026-02-15-010`).

## Risks / Assumptions / Dependencies
### Risks
- Auth contract fix may break existing local shortcuts if not migrated carefully.
- Ownership hardening can surface latent data-mixing assumptions.
- Realstack tests increase CI runtime and infra dependency.

### Assumptions
- MVP is local-first and may use cloud APIs where explicitly configured.
- Existing database schema/migrations are stable enough for loop-focused changes.
- Existing app shell remains the active UI surface (`AppShell`).

### Dependencies
- Services: Postgres, Redis, backend API, frontend app.
- Env: `GUARDIAN_API_KEY`, `DATABASE_URL`/`GUARDIAN_DATABASE_URL`, image-gen provider vars.
- Optional for cloud loops: `OPENAI_API_KEY`, `GROQ_API_KEY`.

## Deferred Features (Parking Lot)
Not required for MVP loop closure:
- Full RBAC/multi-tenant authorization model.
- S3/GCS media backend implementation (`FINDING-2026-02-15-012`).
- Federation hardening and external connector production controls.
- Non-essential UI cleanup of dormant legacy components beyond migration-path removal.
- Production-only hardening beyond what blocks local end-to-end closure.
