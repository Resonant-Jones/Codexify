# Codexify MVP Roadmap & Core Loop Plan

## 1. Overview & Goals
- MVP goal: close six core loops end-to-end (rag, migration, doc-upload, image-gallery, image-gen, doc-gen) with deterministic, authenticated flows.
- Current stack: FastAPI backend, React/Vite frontend, Playwright/Vitest, Postgres/Neo4j/Redis via docker-compose. Evidence: docker-compose.yml:L1-L200; frontend/src/package.json:L5-L12.
- Guardrails: no scope expansion beyond core loop closure; anything else is deferred.

## 2. Core MVP Features

### 2.1 Memory / RAG + Context Broker + Guardian Chat

**Current State**
- ContextBroker assembles messages + semantic + memory context; uses MemoryOSRetriever (vector search) when available. Evidence: guardian/context/broker.py:L12-L208; guardian/memoryos/retriever.py:L12-L102.
- Vector store initialized at startup and used for semantic search. Evidence: guardian/core/dependencies.py:L256-L268; guardian/vector/store.py:L8-L27.
- Chat completion endpoint enqueues a task and returns task_id only. Evidence: guardian/routes/chat.py:L586-L665.
- Chat worker publishes task.completed events with trace, but UI expects response.data.context at completion time. Evidence: guardian/workers/chat_worker.py:L158-L382; frontend/src/features/chat/GuardianChat.tsx:L105-L128.
- Debug endpoint exposes last trace via /debug/rag-trace/{thread_id}/latest. Evidence: guardian/routes/chat.py:L995-L1038.

**Core Loop Definition**
1. User submits a chat prompt in a thread.
2. UI calls POST /chat/{thread_id}/complete.
3. Backend enqueues a task and returns task_id.
4. Worker assembles context via ContextBroker + vector store.
5. Assistant response is stored to the thread.
6. UI refreshes the thread and displays answer plus trace context.

**Gap Analysis**
| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| --- | --- | --- | --- |
| 6 | guardian/routes/chat.py:L586-L665; frontend/src/features/chat/GuardianChat.tsx:L105-L128 | UI expects context in response, but response has only task_id | Add trace retrieval API keyed by task_id or expose trace via SSE events, then wire UI to consume |

**Implementation Tasks**
- Add a supported trace endpoint keyed by task_id or thread_id (S). Files: guardian/routes/chat.py.
- Wire UI to fetch trace after completion (S). Files: frontend/src/features/chat/GuardianChat.tsx.
- Optional: add a focused Playwright check for trace visibility (S). Files: frontend/src/tests/playwright/guardian-chat-diagnostic.spec.ts.

**Validation Plan**
- Manual: POST /api/chat/{thread_id}/complete, then GET /debug/rag-trace/{thread_id}/latest and verify documents/graph arrays are non-empty.
- Automated: Playwright - add a trace assertion in guardian-chat-diagnostic.spec.ts (if trace is surfaced in UI).

### 2.2 ChatGPT Migration Tool

**Current State**
- Backend accepts /api/upload-chatgpt-export and requires API key. Evidence: guardian/routes/migration.py:L28-L34.
- Migration pipeline ingests threads/messages into DB and vector store. Evidence: backend/rag/chatgpt_migration.py:L42-L199.
- UI posts to legacy /upload-chatgpt-export without API key. Evidence: frontend/src/components/settings/SettingsView.tsx:L146-L161; frontend/src/components/modals/ChatGPTImportModal.tsx:L47-L63.
- Playwright E2E exists for migration. Evidence: frontend/src/tests/playwright/migration_e2e_import.spec.ts:L1-L199.

**Core Loop Definition**
1. User selects ChatGPT export file.
2. UI uploads to canonical /api/upload-chatgpt-export with auth.
3. Backend ingests data and returns queued/accepted status.
4. UI shows queued/processing state and refreshes threads.

**Gap Analysis**
| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| --- | --- | --- | --- |
| 2 | frontend/src/components/settings/SettingsView.tsx:L146-L161; guardian/routes/migration.py:L28-L34 | UI uses legacy route without API key; backend requires auth on canonical endpoint | Switch to /api/upload-chatgpt-export and include API key header |

**Implementation Tasks**
- Update migration upload to use /api/upload-chatgpt-export and include X-API-Key (S). Files: frontend/src/components/settings/SettingsView.tsx, frontend/src/components/modals/ChatGPTImportModal.tsx.
- Ensure API key is available outside dev proxy (S). Files: frontend/src/lib/api.ts.
- Update migration E2E to assert canonical endpoint (S). Files: frontend/src/tests/playwright/migration_e2e_import.spec.ts.

**Validation Plan**
- Manual: curl -H "X-API-Key: ..." -F file=@export.json http://localhost:8888/api/upload-chatgpt-export.
- Automated: pnpm --dir frontend/src exec playwright test migration_e2e_import.spec.ts.

### 2.3 Upload Documents + Embed

**Current State**
- Document upload endpoint parses PDF/DOCX/TXT/MD and queues embed. Evidence: guardian/routes/media.py:L287-L444.
- PDF/DOCX parsing implemented. Evidence: guardian/services/document_parsers/pdf_text_extractor.py:L15-L59; guardian/services/document_parsers/docx_text_extractor.py:L15-L57.
- Chunking implemented. Evidence: guardian/services/document_chunking.py:L14-L44.
- Embed worker uses CodexifyEmbedder (defaults to OpenAI use). Evidence: guardian/workers/document_embed_worker.py:L145-L158; guardian/runtime/embed/embedder.py:L53-L103.
- UI upload uses fetch without auth headers and locally stores documents. Evidence: frontend/src/hooks/useUploader.ts:L109-L120; frontend/src/components/persona/layout/AppShell.tsx:L433-L459.
- API requires auth on /api/media. Evidence: guardian/routes/media.py:L63-L72.

**Core Loop Definition**
1. User uploads a document via UI.
2. UI POSTs to /api/media/upload/document with auth headers.
3. Backend stores file, extracts text, and queues embeddings.
4. Embed worker indexes chunks and sets status.
5. UI fetches /api/media/documents and shows status; chat uses embeddings.

**Gap Analysis**
| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| --- | --- | --- | --- |
| 2 | frontend/src/hooks/useUploader.ts:L109-L120; guardian/routes/media.py:L63-L72 | No API key header on upload requests | Use authenticated API client for uploads |
| 2 | frontend/src/hooks/useUploader.ts:L88-L166 | totalFailed increment before initialization triggers runtime error | Initialize totalFailed before use |
| 3 | frontend/src/hooks/useUploader.ts:L179-L193 | Optional ingestion endpoint can exfiltrate base64 file bytes | Gate behind explicit config + consent |
| 4 | guardian/workers/document_embed_worker.py:L145-L158; guardian/runtime/embed/embedder.py:L53-L103 | Embeddings default to OpenAI; fails without key or violates local-first | Default to local embeddings when configured |
| 5 | frontend/src/components/persona/layout/AppShell.tsx:L433-L459; guardian/routes/media.py:L692-L744 | UI list uses localStorage, not backend list | Fetch /api/media/documents and reconcile |

**Implementation Tasks**
- Add auth headers for /api/media/upload/document (S). Files: frontend/src/hooks/useUploader.ts.
- Fix totalFailed initialization (S). Files: frontend/src/hooks/useUploader.ts.
- Gate ingestion endpoint (M). Files: frontend/src/hooks/useUploader.ts.
- Make embedder backend explicit and local-first (M). Files: guardian/workers/document_embed_worker.py, guardian/runtime/embed/embedder.py.
- Replace localStorage document list with backend list (M). Files: frontend/src/components/persona/layout/AppShell.tsx.

**Validation Plan**
- Manual: upload a PDF and verify embedding status appears in /api/media/documents.
- Automated: add a backend test for upload + embed status in guardian/tests (note pytest.ini ignores guardian/tests by default: pytest.ini:L1-L3).

### 2.4 Upload Images to Gallery

**Current State**
- Backend supports image upload/list under /api/media. Evidence: guardian/routes/media.py:L263-L279; guardian/routes/media.py:L648-L689.
- UI lists images with fetch /api/media/images (no auth). Evidence: frontend/src/components/gallery/GalleryView.tsx:L50-L76.
- Upload via useUploader uses fetch without auth headers. Evidence: frontend/src/hooks/useUploader.ts:L70-L86.
- /api/media requires API key. Evidence: guardian/routes/media.py:L63-L72.

**Core Loop Definition**
1. User uploads an image.
2. UI POSTs /api/media/upload/image with auth headers.
3. Backend stores image and returns URL.
4. UI displays image in gallery list.

**Gap Analysis**
| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| --- | --- | --- | --- |
| 2-4 | frontend/src/components/gallery/GalleryView.tsx:L50-L76; frontend/src/hooks/useUploader.ts:L70-L86 | No API key headers for list/upload calls | Use authenticated API client |
| 2 | frontend/src/hooks/useUploader.ts:L88-L166 | totalFailed initialization bug | Initialize totalFailed before use |

**Implementation Tasks**
- Add auth headers for image list/upload (S). Files: frontend/src/components/gallery/GalleryView.tsx, frontend/src/hooks/useUploader.ts.
- Fix totalFailed initialization (S). Files: frontend/src/hooks/useUploader.ts.

**Validation Plan**
- Manual: upload an image and verify it appears in gallery; verify /api/media/images returns it.
- Automated: add a focused UI test for gallery list after upload (Playwright).

### 2.5 Generate Images

**Current State**
- Backend endpoint /api/media/generate/image exists. Evidence: guardian/routes/media.py:L476-L539.
- UI posts to /api/media/generate/image. Evidence: frontend/src/components/modals/ImageGenModal.tsx:L62-L69.
- Local and Stability providers return placeholder image bytes. Evidence: guardian/image_gen/providers/local.py:L8-L27; guardian/image_gen/providers/stability.py:L8-L27.

**Core Loop Definition**
1. User enters prompt + model.
2. UI POSTs /api/media/generate/image with auth.
3. Backend generates image and stores it.
4. UI shows image in gallery.

**Gap Analysis**
| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| --- | --- | --- | --- |
| 2 | frontend/src/components/modals/ImageGenModal.tsx:L62-L69; guardian/routes/media.py:L63-L72 | API key headers missing for /api/media calls | Add auth headers |
| 3 | guardian/image_gen/providers/local.py:L8-L27; guardian/image_gen/providers/stability.py:L8-L27 | Non-OpenAI providers are placeholders | Implement or hide stub providers |

**Implementation Tasks**
- Add API key headers for image generation (S). Files: frontend/src/components/modals/ImageGenModal.tsx or shared api client.
- Implement at least one real provider (OpenAI or local) and hide stub providers until ready (M-L). Files: guardian/image_gen/providers/*.

**Validation Plan**
- Manual: POST /api/media/generate/image with a real provider key and confirm image appears in gallery.
- Automated: add a Playwright test for the modal with stubbed backend response.

### 2.6 Generate Documents (Code / Literature / Diagrams)

**Current State**
- Backend endpoint /api/documents/generate exists and persists documents. Evidence: guardian/routes/documents.py:L249-L388.
- Router has no API key dependency. Evidence: guardian/routes/documents.py:L9-L20.
- UI submits /documents/generate and emits events to add document. Evidence: frontend/src/App.tsx:L116-L171.
- Document list UI is localStorage-backed. Evidence: frontend/src/components/persona/layout/AppShell.tsx:L433-L459.

**Core Loop Definition**
1. User opens doc generation modal and submits prompt + doc type.
2. UI POSTs /api/documents/generate with auth.
3. Backend generates and persists document, links to thread.
4. UI shows generated document and it reopens later from backend list.

**Gap Analysis**
| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| --- | --- | --- | --- |
| 2 | guardian/routes/documents.py:L9-L20; guardian/routes/documents.py:L249-L254 | Document generation endpoints lack API key enforcement | Add API key dependency |
| 4 | frontend/src/components/persona/layout/AppShell.tsx:L433-L459 | Documents list uses localStorage not backend list | Fetch /api/media/documents and reconcile |

**Implementation Tasks**
- Add require_api_key to documents router (S). Files: guardian/routes/documents.py.
- Update UI to pull document list from backend (M). Files: frontend/src/components/persona/layout/AppShell.tsx.

**Validation Plan**
- Manual: POST /api/documents/generate and verify entry appears in /api/media/documents.
- Automated: update frontend/src/tests/document_gen_modal.spec.tsx to assert request/response and list update.

## 3. Milestones & Timeline

- Milestone 0 - Blockers and infrastructure
  - Remove API key fallbacks or gate them behind explicit dev flag. Evidence: guardian/core/dependencies.py:L77-L174.
  - Ensure API keys available to frontend outside Vite dev proxy (frontend/src/vite.config.ts:L25-L37; frontend/src/lib/api.ts:L7-L25).

- Milestone 1 - RAG loop closure
  - Trace retrieval path wired to UI; add validation.

- Milestone 2 - Migration loop closure
  - Canonical endpoint usage + auth headers; update E2E test.

- Milestone 3 - Document upload + embed loop closure
  - Auth headers, embedding backend defaulting, backend document list UI integration.

- Milestone 4 - Image gallery + generation
  - Auth headers for /api/media; replace stub providers or limit UI to implemented providers.

- Milestone 5 - Document generation loop closure
  - Require auth and reconcile generated docs in UI list.

## 4. Risks, Assumptions & Dependencies
- Assumes API keys are correctly provided in production (dev proxy injects headers only for dev). Evidence: frontend/src/vite.config.ts:L25-L37.
- Embeddings may require external services (OpenAI) or local model cache; ensure configuration is explicit. Evidence: guardian/runtime/embed/embedder.py:L87-L103; backend/rag/embedder.py:L103-L200.
- pytest.ini ignores guardian/tests by default (pytest.ini:L1-L3), so add explicit test commands or update config.
- Docker services (db, redis, neo4j) are required for some flows. Evidence: docker-compose.yml:L4-L200.

## 5. Deferred Features (Post-MVP Parking Lot)
- Connector framework and plugin system described in README (post-MVP). Evidence: README.md:L45-L52.
- Graph context (Neo4j) is optional/experimental; defer unless needed for core loops. Evidence: README.md:L45-L48; guardian/context/broker.py:L122-L135.
- Desktop app and advanced memory consolidation features are non-essential for MVP. Evidence: README.md:L64-L66.
