# Codexify MVP Roadmap and Core Loop Plan (2026-01-25)

## Overview and Goals
- Close six core loops end-to-end: rag, migration, doc-upload, image-gallery, image-gen, doc-gen.
- Prioritize deterministic flows, explicit auth, and local-first defaults.
- Defer non-core features until loops are reliable and testable.

## Core Loop 1: RAG Chat and Context (rag)

### Current State
- Chat completion enqueues a task and returns task_id only. Evidence: guardian/routes/chat.py:L586-L665.
- ContextBroker assembles semantic/memory context; chat worker publishes a trace in task.completed events. Evidence: guardian/context/broker.py:L12-L208; guardian/workers/chat_worker.py:L158-L382.
- UI expects response.data.context but the completion response does not include it. Evidence: frontend/src/features/chat/GuardianChat.tsx:L105-L128.
- Debug endpoint exists for trace retrieval. Evidence: guardian/routes/chat.py:L995-L1038.

### Core Loop Definition
1. User submits a prompt in a thread.
2. UI calls POST /chat/{thread_id}/complete with depth.
3. Backend enqueues chat task.
4. Worker assembles RAG context and calls LLM.
5. Assistant response persists to thread.
6. UI refreshes and displays answer plus RAG trace context.

### Gap Analysis
| Step | Current Implementation (evidence) | Gap | Concrete Fix | Finding IDs |
| --- | --- | --- | --- | --- |
| 6 | guardian/routes/chat.py:L586-L665, guardian/routes/chat.py:L995-L1038, frontend/src/features/chat/GuardianChat.tsx:L105-L128 | UI expects context but response lacks trace; trace only in debug endpoint | Add trace retrieval API tied to task_id or publish trace over events; update UI to consume | FINDING-2026-01-25-011 |

### Implementation Tasks
- Add a supported trace retrieval path (e.g., GET /api/chat/tasks/{task_id}/trace or embed trace in task.completed events).
- Update GuardianChat to fetch trace after completion and store it in UI state.
- Add a minimal integration test for trace retrieval (backend) and/or a Playwright check (frontend).

### Validation Plan
- Manual: POST /api/chat/{thread_id}/complete (with X-API-Key), then GET /debug/rag-trace/{thread_id}/latest and verify trace fields.
- Automated: add/extend test coverage in frontend/src/tests/playwright/guardian-chat-diagnostic.spec.ts.

## Core Loop 2: ChatGPT Migration Import (migration)

### Current State
- Backend exposes POST /api/upload-chatgpt-export with API key requirement and ingest pipeline. Evidence: guardian/routes/migration.py:L28-L44; backend/rag/chatgpt_migration.py:L42-L199.
- UI posts to /upload-chatgpt-export with only X-User-Id. Evidence: frontend/src/components/settings/SettingsView.tsx:L146-L161; frontend/src/components/modals/ChatGPTImportModal.tsx:L47-L63.
- Playwright E2E exists for migration. Evidence: frontend/src/tests/playwright/migration_e2e_import.spec.ts.

### Core Loop Definition
1. User selects a ChatGPT export JSON.
2. UI uploads to canonical /api/upload-chatgpt-export with auth.
3. Backend ingests threads/messages into DB and vector store.
4. UI shows queued/processing state, then refreshes threads list.

### Gap Analysis
| Step | Current Implementation (evidence) | Gap | Concrete Fix | Finding IDs |
| --- | --- | --- | --- | --- |
| 2 | frontend/src/components/settings/SettingsView.tsx:L146-L161; guardian/routes/migration.py:L28-L34 | UI uses legacy path without API key while backend requires auth on canonical path | Use /api/upload-chatgpt-export and attach X-API-Key/Authorization | FINDING-2026-01-25-003 |

### Implementation Tasks
- Update migration upload to hit /api/upload-chatgpt-export and include API key header.
- Reuse a centralized API client that can inject auth outside Vite dev proxy.
- Update Playwright test to assert canonical endpoint and headers.

### Validation Plan
- Manual: curl -H "X-API-Key: ..." -F file=@export.json http://localhost:8888/api/upload-chatgpt-export.
- Automated: pnpm --dir frontend/src exec playwright test migration_e2e_import.spec.ts.

## Core Loop 3: Document Upload and Embedding (doc-upload)

### Current State
- Upload endpoint parses PDF/DOCX/TXT/MD and enqueues embeddings. Evidence: guardian/routes/media.py:L287-L444.
- PDF/DOCX parsing implemented. Evidence: guardian/services/document_parsers/pdf_text_extractor.py:L15-L59; guardian/services/document_parsers/docx_text_extractor.py:L15-L57.
- Chunking logic exists. Evidence: guardian/services/document_chunking.py:L14-L44.
- Embed worker instantiates CodexifyEmbedder (OpenAI default). Evidence: guardian/workers/document_embed_worker.py:L145-L158; guardian/runtime/embed/embedder.py:L53-L103.
- UI upload uses fetch without API key and stores documents in localStorage. Evidence: frontend/src/hooks/useUploader.ts:L109-L120; frontend/src/components/persona/layout/AppShell.tsx:L433-L459.

### Core Loop Definition
1. User uploads a document.
2. UI POSTs to /api/media/upload/document with auth.
3. Backend stores file, extracts text, enqueues embedding.
4. Embedding worker indexes chunks.
5. UI lists documents from backend with embedding status.

### Gap Analysis
| Step | Current Implementation (evidence) | Gap | Concrete Fix | Finding IDs |
| --- | --- | --- | --- | --- |
| 2 | frontend/src/hooks/useUploader.ts:L109-L120; guardian/routes/media.py:L63-L72 | Upload requests lack API key header | Add API key header in client or reuse authenticated API client | FINDING-2026-01-25-004 |
| 2 | frontend/src/hooks/useUploader.ts:L88-L166 | totalFailed increment happens before declaration | Initialize totalFailed before any increment | FINDING-2026-01-25-006 |
| 3 | frontend/src/hooks/useUploader.ts:L179-L193 | Optional ingestion endpoint can exfiltrate base64 file data | Gate/disable ingestion or require explicit consent | FINDING-2026-01-25-007 |
| 4 | guardian/workers/document_embed_worker.py:L145-L158; guardian/runtime/embed/embedder.py:L53-L103 | Embedding defaults to OpenAI, failing without key or violating local-first | Make embedder backend explicit; default to local when configured | FINDING-2026-01-25-008 |
| 5 | frontend/src/components/persona/layout/AppShell.tsx:L433-L459; guardian/routes/media.py:L692-L744 | UI list is localStorage-backed instead of backend | Fetch /api/media/documents and reconcile local mocks | FINDING-2026-01-25-009 |

### Implementation Tasks
- Add auth headers to /api/media/upload/document and /api/media/documents calls.
- Fix totalFailed initialization and add regression test.
- Remove or gate ingestion endpoint behind explicit config and consent.
- Default embeddings to local or require explicit OpenAI config.
- Replace localStorage document list with backend list + caching.

### Validation Plan
- Manual: curl -H "X-API-Key: ..." -F file=@doc.pdf -F project_id=1 -F thread_id=1 http://localhost:8888/api/media/upload/document.
- Manual: curl -H "X-API-Key: ..." http://localhost:8888/api/media/documents.
- Automated: add backend test in guardian/tests (note pytest.ini ignores guardian/tests by default) and add frontend unit test for useUploader failure paths.

## Core Loop 4: Image Gallery (image-gallery)

### Current State
- Backend lists images via /api/media/images. Evidence: guardian/routes/media.py:L648-L689.
- UI fetches /api/media/images without auth and uses useUploader for image uploads. Evidence: frontend/src/components/gallery/GalleryView.tsx:L50-L76; frontend/src/hooks/useUploader.ts:L70-L86.

### Core Loop Definition
1. User uploads an image.
2. UI POSTs to /api/media/upload/image with auth.
3. Backend stores image and returns URL.
4. UI lists images from backend.

### Gap Analysis
| Step | Current Implementation (evidence) | Gap | Concrete Fix | Finding IDs |
| --- | --- | --- | --- | --- |
| 2-4 | frontend/src/components/gallery/GalleryView.tsx:L50-L57; frontend/src/hooks/useUploader.ts:L70-L86; guardian/routes/media.py:L63-L72 | No API key headers on list/upload calls | Use authenticated API client for /api/media | FINDING-2026-01-25-005 |
| 2 | frontend/src/hooks/useUploader.ts:L88-L166 | Upload failure counter can throw | Initialize totalFailed before use | FINDING-2026-01-25-006 |

### Implementation Tasks
- Attach API key headers for list/upload calls in production clients.
- Fix totalFailed bug and add test coverage.

### Validation Plan
- Manual: curl -H "X-API-Key: ..." http://localhost:8888/api/media/images.
- Manual: upload an image via UI and verify it appears in GalleryView.

## Core Loop 5: Image Generation (image-gen)

### Current State
- Backend endpoint /api/media/generate/image calls ImageGenRouter. Evidence: guardian/routes/media.py:L476-L539.
- UI posts to /api/media/generate/image using api client. Evidence: frontend/src/components/modals/ImageGenModal.tsx:L62-L69; frontend/src/lib/api.ts:L7-L25.
- Local and Stability providers return placeholder PNGs. Evidence: guardian/image_gen/providers/local.py:L8-L27; guardian/image_gen/providers/stability.py:L8-L27.

### Core Loop Definition
1. User enters prompt/model and submits.
2. UI POSTs to /api/media/generate/image with auth.
3. Backend calls configured provider, stores image, returns URL.
4. UI adds image to gallery and shows success toast.

### Gap Analysis
| Step | Current Implementation (evidence) | Gap | Concrete Fix | Finding IDs |
| --- | --- | --- | --- | --- |
| 2 | frontend/src/components/modals/ImageGenModal.tsx:L62-L69; guardian/routes/media.py:L63-L72 | API key headers not attached for /api/media calls | Use authenticated API client or add headers | FINDING-2026-01-25-005 |
| 3 | guardian/image_gen/providers/local.py:L8-L27; guardian/image_gen/providers/stability.py:L8-L27 | Non-OpenAI providers are placeholders | Implement real providers or hide options | FINDING-2026-01-25-010 |

### Implementation Tasks
- Add API key header support to image generation requests.
- Implement or disable stub providers; document supported provider list.

### Validation Plan
- Manual: curl -H "X-API-Key: ..." -H "content-type: application/json" -d '{"prompt":"...","model":"dall-e-3"}' http://localhost:8888/api/media/generate/image.
- Automated: extend frontend/src/tests/image_gen_modal.spec.tsx to assert API call is made with auth.

## Core Loop 6: Document Generation (doc-gen)

### Current State
- Backend provides POST /api/documents/generate and persists generated docs. Evidence: guardian/routes/documents.py:L249-L388.
- Router has no API key dependency. Evidence: guardian/routes/documents.py:L9-L20.
- UI submits /documents/generate and dispatches events to add doc locally. Evidence: frontend/src/App.tsx:L116-L171.
- Documents list is localStorage-backed. Evidence: frontend/src/components/persona/layout/AppShell.tsx:L433-L459.

### Core Loop Definition
1. User opens document generation modal and submits prompt.
2. UI POSTs to /api/documents/generate with auth.
3. Backend generates content and persists document.
4. UI shows generated document and lists it across sessions.

### Gap Analysis
| Step | Current Implementation (evidence) | Gap | Concrete Fix | Finding IDs |
| --- | --- | --- | --- | --- |
| 2 | guardian/routes/documents.py:L9-L20; guardian/routes/documents.py:L249-L254 | Document generation endpoints do not enforce API key auth | Add API key dependency to documents router | FINDING-2026-01-25-015 |
| 4 | frontend/src/components/persona/layout/AppShell.tsx:L433-L459 | UI list is localStorage-backed, not backend | Fetch backend list and reconcile | FINDING-2026-01-25-009 |

### Implementation Tasks
- Add require_api_key (or equivalent) to documents routes.
- Update UI to fetch backend document list and merge with generated docs.
- Add regression tests in frontend/src/tests/document_gen_modal.spec.tsx and frontend/src/tests/document_gen_open_in_editor.spec.tsx.

### Validation Plan
- Manual: curl -H "X-API-Key: ..." -H "content-type: application/json" -d '{"thread_id":1,"prompt":"..."}' http://localhost:8888/api/documents/generate.
- Manual: curl -H "X-API-Key: ..." http://localhost:8888/api/threads/1/documents.
- Automated: pnpm --dir frontend/src test (vitest) for document gen UI tests.

## Milestones and Timeline (M0-M5)
- M0: Security baseline: remove repo secrets (F001), fail-closed API key verification (F002), enforce auth on documents routes (F015), address user identity mapping (F014).
- M1: Auth wiring for frontend core loops: migration and media endpoints (F003, F004, F005).
- M2: Document pipeline reliability: upload error handling (F006), ingestion gating (F007), embedding backend defaults (F008), backend document list integration (F009).
- M3: RAG trace UX closure (F011).
- M4: Image generation provider completeness (F010).
- M5: Docs/test alignment and drift cleanup (F012, F013).

## Risks, Assumptions, Dependencies
- Assumes a safe way to deliver API keys to the frontend outside dev proxy injection (see frontend/src/vite.config.ts:L25-L37 and frontend/src/lib/api.ts:L7-L25).
- External provider calls require valid API keys (OpenAI/Groq). Evidence: guardian/core/ai_router.py:L194-L231; guardian/runtime/embed/embedder.py:L87-L103.
- Backend unit tests under guardian/tests are excluded by default in pytest.ini (pytest.ini:L1-L3).

## Deferred Features (parking lot)
- Connector framework, plugin system, desktop app, and expanded provider support are documented in README but not validated in this audit; defer until core loops are closed. Evidence: README.md:L28-L66.
- Knowledge graph context and other advanced memory features are described but should remain deferred for MVP unless they directly close a core loop. Evidence: README.md:L45-L48 and guardian/context/broker.py:L122-L135.
