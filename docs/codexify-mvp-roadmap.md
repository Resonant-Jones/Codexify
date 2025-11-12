# Codexify MVP Roadmap & Core Loop Plan

**Generated:** 2025-11-12
**Purpose:** Define what is truly required for Codexify MVP, map to current codebase, identify gaps, and provide concrete implementation plan
**Scope:** 6 Core Features Only - Everything else deferred to Post-MVP

---

## 1. Overview & Goals

### Problem Statement
Codexify has accumulated scope creep. Many cool features have been built, but **core loops for MVP are not clearly closed**. This roadmap identifies exactly what's needed to get Codexify fully operational at MVP level with end-to-end working flows for the 6 core features.

### MVP Definition
A **brutally clear, pragmatic plan** to ship and use Codexify MVP immediately, deferring everything else to later phases.

### Core MVP Features (Non-Negotiable)
1. **Memory / RAG System + Context Broker for Chat with Guardian**
2. **ChatGPT Migration Tool**
3. **Upload Documents + Embed**
4. **Upload Images to Gallery**
5. **Generate Images**
6. **Generate Documents (code, literature, diagrams, etc.)**

### Success Criteria
Each feature must have a **closed end-to-end loop** that can be demonstrated and tested.

---

## 2. Core MVP Features

### 2.1 Memory / RAG + Context Broker + Guardian Chat

#### **Current State**

**✅ What's Working:**
- **Context Broker** (`guardian/context/broker.py`) - Fully implemented with 4 depth modes (shallow/normal/deep/diagnostic)
- **Memory CRUD API** (`guardian/routes/memory.py`) - Complete with 3-tier storage (ephemeral/midterm/longterm)
- **Vector Store** (`guardian/vector/store.py`) - SQLite-based with basic cosine search
- **Chat Integration** (`guardian/routes/chat.py:389-399`) - ContextBroker wired into `/chat/{thread_id}/complete` endpoint
- **Memory Frontend Hook** (`frontend/src/features/memory/useMemory.ts`) - Full CRUD operations

**⚠️ Partial:**
- **Embeddings** - Using deterministic stubs (`guardian/embedding_engine.py`), not real models
- **ChromaDB** - Implemented (`backend/vector_store/chroma_store.py`) but not used by default
- **MemoryOS** - Advanced features exist (`guardian/memoryos/memoryos.py`) but not integrated into main chat flow
- **Sensors** - Basic implementation (`guardian/sensors/state.py`) but lightweight

**❌ Missing:**
- **Real embeddings** - No active sentence-transformers or OpenAI embeddings
- **Retriever** - Stubbed in `guardian/memoryos/retriever.py`, returns empty lists
- **Frontend RAG UI** - No depth parameter selector, no vector search result display, no memory browser
- **RAG modules** - `backend.rag.*` modules referenced but incomplete/missing

#### **Core Loop Definition**

```
1. User opens Codexify and selects Guardian persona
   ↓
2. User asks question about stored memories/documents
   ↓
3. System retrieves relevant embeddings from memory store
   ↓
4. Context Broker assembles prompt with retrieved content
   ↓
5. Model responds with answer referencing memories
   ↓
6. Conversation and new content re-embedded and stored
```

#### **Gap Analysis**

| Loop Step | Current Implementation | Gap/Problem | Concrete Fix |
|-----------|----------------------|-------------|--------------|
| **1. User opens Guardian** | ✅ Working - persona selection in AppShell | None | N/A |
| **2. User asks question** | ✅ Working - chat UI sends to `/chat/{thread_id}/complete` | None | N/A |
| **3. Retrieve embeddings** | ⚠️ Partial - VectorStore.search() works but uses stub embeddings | **Stub embeddings have no semantic meaning** | Switch to real embeddings (sentence-transformers or OpenAI) |
| **4. Context Broker assembles** | ✅ Working - ContextBroker.assemble() with depth modes | **Retriever returns empty** | Implement real retriever in `guardian/memoryos/retriever.py` |
| **5. Model responds** | ✅ Working - LLM integration via ai_router | None | N/A |
| **6. Re-embed and store** | ❌ Missing - no automatic embedding of new messages | **No pipeline to embed chat messages** | Add post-message embedding hook |

#### **Implementation Tasks**

**Priority: HIGH (Core to MVP)**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **Enable Real Embeddings** | Switch from stub to sentence-transformers | `guardian/vector/embeds.py`, `.env` | M | sentence-transformers installed (already in requirements) |
| **Configure ChromaDB** | Set env vars, enable persistence | `.env`, `guardian_api.py` | S | ChromaDB running |
| **Implement Retriever** | Replace stub with actual vector search | `guardian/memoryos/retriever.py` | M | Real embeddings working |
| **Wire MemoryOS to Chat** | Integrate Memoryos retriever into ContextBroker | `guardian/context/broker.py` | M | Retriever implemented |
| **Add Auto-Embedding** | Embed chat messages after creation | `guardian/routes/chat.py` | M | Real embeddings working |
| **Frontend Depth Selector** | Add UI control for depth in chat | `frontend/src/features/chat/` | S | None |
| **Memory Browser UI** | Component to view/search memories | `frontend/src/components/memory/` | L | Memory API working |

#### **Validation Plan**

**Manual Test Script:**
```bash
# Setup
1. Set EMBEDDING_BACKEND=local in .env
2. Set VECTOR_STORE=chroma
3. Restart backend

# Test Flow
4. Open chat, add memory entry via Memory API
5. Ask question related to memory content
6. Verify assistant response references memory
7. Check ChromaDB collection has embeddings
8. Try different depth modes (shallow/normal/deep)
9. Verify context bundle in logs contains retrieved items
```

**Automated Test Recommendations:**
- **Unit Tests:**
  - `tests/vector/test_embedder.py` - Test real embeddings generation
  - `tests/memoryos/test_retriever.py` - Test retrieval accuracy
  - `tests/context/test_broker_integration.py` - Test full RAG pipeline
- **Integration Tests:**
  - End-to-end: message → embed → retrieve → respond
  - Accuracy metrics: retrieval precision/recall
  - Performance: embedding latency, search speed

**Test Locations:**
- `tests/vector/` - Vector store and embedding tests
- `tests/memoryos/` - Memory system tests
- `tests/context/` - Context broker tests

---

### 2.2 ChatGPT Migration Tool

#### **Current State**

**✅ What's Working:**
- **CLI Command** (`scripts/chatgpt_import/cli_migrate.py`) - Fully functional with `codexify migrate`, `validate`, `history`
- **Neo4j Import** (`scripts/chatgpt_import/import_chatgpt.py`) - Idempotent graph creation with Thread/Message nodes
- **Chroma Embeddings** - Batch-optimized embedding generation with OpenAI
- **Progress UI** - Rich terminal UI with progress bars, spinners, time remaining
- **Logging** - JSON summaries to `logs/migration_summary.json`, error logs to `logs/migration_skipped.json`
- **Testing** - 40+ comprehensive tests covering all flows

**⚠️ Partial:**
- **Documentation** - Excellent README in `scripts/chatgpt_import/README.md` but not linked from main docs

**❌ Missing:**
- **Frontend UI** - No UI to trigger migrations, view imported threads, or search imported data
- **API Endpoints** - No REST API to access Neo4j/Chroma imported data
- **Data Bridge** - No sync between Neo4j imported threads and Postgres ChatThread model
- **Search UI** - Semantic search via Chroma not exposed in UI
- **HTML Export** - Only JSON supported, no HTML parser

#### **Core Loop Definition**

```
1. User exports ChatGPT conversations to JSON
   ↓
2. User runs `codexify migrate conversations.json`
   ↓
3. CLI parses JSON, validates structure
   ↓
4. System imports threads/messages to Neo4j graph
   ↓
5. System generates embeddings and stores in ChromaDB
   ↓
6. Migration summary displayed in terminal
   ↓
7. User can view/search imported threads in UI
```

#### **Gap Analysis**

| Loop Step | Current Implementation | Gap/Problem | Concrete Fix |
|-----------|----------------------|-------------|--------------|
| **1. User exports** | ✅ External (ChatGPT export) | None | Document export process in README |
| **2. User runs CLI** | ✅ Working - `codexify migrate` | None | N/A |
| **3. Parse & validate** | ✅ Working - JSON validation, error handling | None | N/A |
| **4. Import to Neo4j** | ✅ Working - MERGE operations, idempotent | None | N/A |
| **5. Generate embeddings** | ✅ Working - OpenAI batch processing | None | N/A |
| **6. Summary displayed** | ✅ Working - Rich terminal output | None | N/A |
| **7. View in UI** | ❌ Missing - no frontend access | **Imported data isolated from main app** | Add API endpoints + frontend modal |

#### **Implementation Tasks**

**Priority: MEDIUM (CLI works, UI is nice-to-have for MVP)**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **Add Legacy Thread API** | Create endpoints to query Neo4j imported threads | `guardian/routes/legacy_threads.py` (new) | M | Neo4j driver |
| **Wire Frontend Modal** | Connect LegacyThreadsModal to new API | `frontend/src/components/modals/LegacyThreadsModal.tsx` | M | API endpoints |
| **Add Semantic Search** | Expose Chroma `chatgpt_messages` collection via API | `guardian/routes/search.py` | M | ChromaDB |
| **Search UI** | Add search bar in LegacyThreadsModal | `frontend/src/components/modals/` | S | Search API |
| **HTML Parser** | Add support for ChatGPT HTML exports | `scripts/chatgpt_import/parsers/` (new) | M | BeautifulSoup |
| **Data Sync Tool** | Optional: migrate Neo4j → Postgres ChatThread | `scripts/chatgpt_import/sync_to_postgres.py` (new) | L | Both DBs |

#### **Validation Plan**

**Manual Test Script:**
```bash
# Setup
1. Export ChatGPT conversations to JSON
2. Ensure Neo4j and ChromaDB running
3. Set OPENAI_API_KEY in .env

# Test CLI Flow
4. Run: codexify migrate conversations.json
5. Verify progress bars show completion
6. Check logs/migration_summary.json for stats
7. Run: codexify validate
8. Verify Neo4j has Thread/Message nodes
9. Verify ChromaDB has chatgpt_messages collection
10. Run: codexify history

# Test UI Flow (after implementation)
11. Open Codexify UI, click "Legacy Threads"
12. Verify imported threads listed
13. Search for keyword from imported conversation
14. Click thread to view messages
15. Verify graph visualization shows relationships
```

**Automated Test Recommendations:**
- **Unit Tests:** ✅ Already have 40+ tests
- **Integration Tests:**
  - `tests/api/test_legacy_threads.py` - API endpoint tests (new)
  - `tests/frontend/test_legacy_modal.cy.ts` - Cypress E2E tests (new)
- **Accuracy Tests:**
  - Verify imported thread count matches export
  - Verify message relationships preserved
  - Verify embeddings retrieve relevant messages

**Test Locations:**
- `tests/scripts/` - Existing CLI tests (comprehensive)
- `tests/api/` - New API endpoint tests
- `frontend/src/cypress/e2e/` - New E2E tests

---

### 2.3 Upload Documents + Embed

#### **Current State**

**✅ What's Working:**
- **Frontend Upload UI** (`frontend/src/hooks/useUploader.ts`) - Drag-drop, file picker functional
- **Backend Upload API** (`guardian/routes/media.py`) - Saves files, stores metadata in `uploaded_documents` table
- **File Storage** (`guardian/core/storage.py`) - Local filesystem with soft delete
- **Vector Storage** - ChromaDB, SQLite VectorStore, PGVector all implemented
- **RAG in Chat** (`guardian/context/broker.py`) - ContextBroker integrates vector search
- **CLI Embed Tools** (`guardian/cli/ingest_cli.py`) - Manual ingestion functional

**⚠️ Partial:**
- **Text Extraction** - Only .txt/.md, no PDF/DOCX parsing
- **Frontend Optional Ingestion** - Controlled by localStorage flags, not enabled by default

**❌ Missing:**
- **Document Embedding Pipeline** - Frontend calls `/api/embeddings` but endpoint doesn't exist
- **Document Chunking** - No text splitter implementation
- **PDF/DOCX Processing** - No parser for these formats
- **Background Processing** - No async job queue for large files
- **Document-to-Vector Linkage** - No vector_id in `uploaded_documents` table

#### **Core Loop Definition**

```
1. User clicks "Upload Document" in UI
   ↓
2. User selects file (PDF, DOCX, MD, TXT)
   ↓
3. File uploaded to backend storage
   ↓
4. Backend extracts text from document
   ↓
5. Text chunked into semantic segments
   ↓
6. Each chunk embedded and stored in ChromaDB
   ↓
7. Document metadata saved with vector IDs
   ↓
8. User asks question in chat
   ↓
9. RAG retrieves relevant document chunks
   ↓
10. Assistant responds using document context
```

#### **Gap Analysis**

| Loop Step | Current Implementation | Gap/Problem | Concrete Fix |
|-----------|----------------------|-------------|--------------|
| **1-2. User uploads** | ✅ Working - drag-drop, file picker | None | N/A |
| **3. File storage** | ✅ Working - saved to `/app/media/documents/` | None | N/A |
| **4. Extract text** | ⚠️ Partial - only .txt/.md | **No PDF/DOCX parsing** | Add PyPDF2, python-docx |
| **5. Chunk text** | ❌ Missing | **No chunking strategy** | Implement RecursiveCharacterTextSplitter |
| **6. Embed chunks** | ❌ Missing | **No `/api/embeddings` endpoint** | Create endpoint, wire to vector store |
| **7. Save metadata** | ⚠️ Partial - saves doc, but no vector_ids | **Can't link docs to embeddings** | Add vector_ids JSON column |
| **8. User asks** | ✅ Working | None | N/A |
| **9. RAG retrieves** | ✅ Working - ContextBroker searches vectors | **Searches stubs, not real doc embeddings** | Fix steps 4-6 |
| **10. Responds** | ✅ Working | None | N/A |

#### **Implementation Tasks**

**Priority: HIGH (Core to MVP)**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **Create `/api/embeddings` Endpoint** | Accept doc text, chunk, embed, store | `guardian/routes/embeddings.py` (new) | M | Real embeddings |
| **Implement Document Processors** | PDF: PyPDF2, DOCX: python-docx | `guardian/processing/parsers.py` (new) | M | Libraries installed |
| **Add Chunking Strategy** | Recursive character splitter with overlap | `guardian/processing/chunker.py` (new) | M | langchain-text-splitters |
| **Link Docs to Vectors** | Add vector_ids JSON column to uploaded_documents | DB migration | S | None |
| **Wire Frontend to Embed** | Call `/api/embeddings` after upload | `frontend/src/hooks/useUploader.ts` | S | Embeddings endpoint |
| **Background Processing** | Async job queue for large files | `guardian/workers/` (new) | L | Celery or Dramatiq |

#### **Validation Plan**

**Manual Test Script:**
```bash
# Setup
1. Enable real embeddings (EMBEDDING_BACKEND=local)
2. Ensure ChromaDB running
3. Restart backend

# Test Upload Flow
4. Open Documents view, drag-drop a PDF
5. Verify file appears in upload list
6. Check backend logs for embedding job
7. Verify ChromaDB has new embeddings (count increased)
8. Go to chat, ask question about PDF content
9. Verify assistant response references document
10. Check context bundle includes document chunks

# Test Different Formats
11. Upload .txt, .md, .docx files
12. Repeat steps 8-10 for each
```

**Automated Test Recommendations:**
- **Unit Tests:**
  - `tests/processing/test_parsers.py` - Test PDF/DOCX text extraction
  - `tests/processing/test_chunker.py` - Test chunking logic
  - `tests/routes/test_embeddings.py` - Test embeddings endpoint
- **Integration Tests:**
  - End-to-end: upload → parse → chunk → embed → retrieve
  - Accuracy: retrieval precision for uploaded docs
  - Performance: embedding latency for large files

**Test Locations:**
- `tests/processing/` - New parsing and chunking tests
- `tests/routes/` - Embeddings endpoint tests
- `tests/integration/` - E2E upload+RAG tests

---

### 2.4 Upload Images to Gallery

#### **Current State**

**✅ What's Working:**
- **Backend API** (`guardian/routes/media.py`) - Full CRUD for images (upload, list, get, delete)
- **File Storage** (`guardian/core/storage.py`) - Local filesystem working
- **Database Schema** (`guardian/db/models.py`) - UploadedImage and GeneratedImage models complete
- **Static File Serving** (`guardian_api.py:665`) - `/media` endpoint mounted
- **Gallery Display** (`frontend/src/components/persona/layout/AppShell.tsx:1260-1330`) - Grid view working

**⚠️ Partial:**
- **Frontend Upload** (`frontend/src/hooks/useUploader.ts`) - Reads files locally as Data URLs, **doesn't call backend API**
- **Image Processing** - PIL imported but no thumbnail generation

**❌ Missing:**
- **Frontend-Backend Connection** - useUploader doesn't POST to `/api/media/upload/image`
- **Persistence** - Images only stored in localStorage, lost on cache clear
- **Thumbnail Generation** - Full images loaded, no optimization
- **Metadata Display** - Can't see filename, upload date in UI
- **Search/Filter** - No way to filter gallery
- **Tests** - Zero test coverage

#### **Core Loop Definition**

```
1. User opens Gallery view
   ↓
2. User drags image or clicks "Upload"
   ↓
3. File sent to backend `/api/media/upload/image`
   ↓
4. Backend saves to `/app/media/images/`
   ↓
5. Metadata stored in `uploaded_images` table
   ↓
6. Thumbnail generated (256x256)
   ↓
7. Image URL returned to frontend
   ↓
8. Frontend adds to gallery state and localStorage
   ↓
9. Gallery grid refreshes with thumbnail
   ↓
10. User clicks image to view full size
```

#### **Gap Analysis**

| Loop Step | Current Implementation | Gap/Problem | Concrete Fix |
|-----------|----------------------|-------------|--------------|
| **1. User opens Gallery** | ✅ Working | None | N/A |
| **2. User uploads** | ✅ Working - drag-drop functional | None | N/A |
| **3. Send to backend** | ❌ Missing | **useUploader doesn't call API** | Add POST to `/api/media/upload/image` |
| **4. Backend saves** | ✅ Working - endpoint implemented | None | N/A |
| **5. Metadata stored** | ✅ Working - database schema complete | None | N/A |
| **6. Thumbnail generated** | ❌ Missing | **No PIL thumbnail generation** | Add thumbnail creation on upload |
| **7. URL returned** | ✅ Working - response includes src_url | None | N/A |
| **8. Frontend adds** | ⚠️ Partial - adds Data URL, not backend URL | **Uses local Data URL instead** | Use src_url from response |
| **9. Gallery refreshes** | ✅ Working | None | N/A |
| **10. View full size** | ⚠️ Partial - no lightbox | **Inline only** | Add lightbox modal |

#### **Implementation Tasks**

**Priority: MEDIUM (UI works, backend exists, just needs wiring)**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **Wire useUploader to API** | Add POST to `/api/media/upload/image` | `frontend/src/hooks/useUploader.ts` | S | None |
| **Add Thumbnail Generation** | Use PIL to create 256x256 thumbnails | `guardian/routes/media.py` | M | PIL/Pillow |
| **Store Thumbnail Paths** | Add thumbnail_url to UploadedImage | DB migration | S | None |
| **Serve Thumbnails** | Return thumbnail URL in API response | `guardian/routes/media.py` | S | Thumbnails exist |
| **Lightbox Modal** | Full-screen image viewer | `frontend/src/components/gallery/` | M | None |
| **Metadata Display** | Show filename, date, size in UI | `frontend/src/components/gallery/GalleryView.tsx` | S | None |
| **Write Tests** | Integration tests for upload flow | `tests/routes/test_media.py` | M | None |

#### **Validation Plan**

**Manual Test Script:**
```bash
# Setup
1. Start full stack (docker-compose up)
2. Open browser to http://localhost:5173

# Test Upload Flow
3. Navigate to Gallery view
4. Drag-drop an image file
5. Verify upload progress indicator
6. Verify image appears in gallery grid
7. Refresh page - verify image persists
8. Check browser DevTools Network tab - verify POST to /api/media/upload/image
9. Check database: SELECT * FROM uploaded_images;
10. Check filesystem: ls /app/media/images/
11. Click image - verify lightbox opens (after implementation)
12. Right-click - verify metadata shown
```

**Automated Test Recommendations:**
- **Integration Tests:**
  - `tests/routes/test_media.py`:
    - test_upload_image_success
    - test_upload_image_invalid_format
    - test_list_images
    - test_get_image_by_id
    - test_delete_image
    - test_thumbnail_generation
- **Frontend Tests:**
  - `frontend/src/cypress/e2e/gallery.cy.ts`:
    - test_upload_via_drag_drop
    - test_upload_via_file_picker
    - test_gallery_displays_thumbnails
    - test_lightbox_opens_on_click

**Test Locations:**
- `tests/routes/test_media.py` - API endpoint tests (new)
- `frontend/src/cypress/e2e/gallery.cy.ts` - E2E tests (new)

---

### 2.5 Generate Images

#### **Current State**

**✅ What's Working:**
- **Frontend Modal** (`frontend/src/components/modals/ImageGenModal.tsx`) - Polished UI with prompt input, loading states
- **Database Schema** (`guardian/db/models.py`) - GeneratedImage model complete
- **Storage System** (`guardian/core/storage.py`) - Ready for image storage
- **Gallery Integration** - Modal triggers from Dashboard, Chat, Gallery

**⚠️ Partial:**
- **Backend Endpoint** (`guardian/routes/media.py:302-341`) - Tracking-only stub, comment says: "NOTE: This endpoint doesn't actually generate images (yet)"

**❌ Missing:**
- **Provider Implementations** - No `guardian/image_gen/` directory, no DALL-E/Stability/Ollama integrations
- **Provider Routing** - No image generation router (only LLM chat router exists)
- **Configuration** - Missing all env vars (IMAGE_GEN_PROVIDER, API keys)
- **Image Generation Logic** - No actual API calls to generation providers
- **Tests** - Zero test coverage

#### **Core Loop Definition**

```
1. User clicks "Generate" in Gallery or Chat
   ↓
2. ImageGenModal opens with prompt input
   ↓
3. User enters prompt, clicks "Generate"
   ↓
4. POST to `/api/media/generate/image`
   ↓
5. Backend routes to configured provider (DALL-E/SD)
   ↓
6. Provider generates image from prompt
   ↓
7. Image data downloaded and saved to storage
   ↓
8. Metadata saved to `generated_images` table
   ↓
9. Image URL returned to frontend
   ↓
10. Gallery refreshes with new generated image
```

#### **Gap Analysis**

| Loop Step | Current Implementation | Gap/Problem | Concrete Fix |
|-----------|----------------------|-------------|--------------|
| **1-2. User opens modal** | ✅ Working | None | N/A |
| **3. User submits** | ✅ Working - form validation | None | N/A |
| **4. POST to API** | ✅ Working - endpoint exists | None | N/A |
| **5. Route to provider** | ❌ Missing | **No provider routing logic** | Create provider factory |
| **6. Generate image** | ❌ Missing | **No provider integrations** | Implement OpenAI DALL-E provider |
| **7. Save to storage** | ⚠️ Stub - creates placeholder URL | **Doesn't save actual image** | Download and save image bytes |
| **8. Save metadata** | ✅ Working - DB insert happens | None | N/A |
| **9. Return URL** | ⚠️ Returns placeholder | **URL points to non-existent file** | Return real storage URL |
| **10. Gallery refreshes** | ✅ Working - event system | None | N/A |

#### **Implementation Tasks**

**Priority: HIGH (Commonly requested feature, infrastructure ready)**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **Create Provider Base** | Abstract ImageProvider interface | `guardian/image_gen/image_service.py` (new) | S | None |
| **Implement DALL-E Provider** | OpenAI DALL-E 3 integration | `guardian/image_gen/providers/openai_provider.py` (new) | M | OpenAI API key |
| **Add Provider Factory** | get_provider() based on env config | `guardian/image_gen/providers/__init__.py` (new) | S | Providers implemented |
| **Wire Backend Endpoint** | Replace stub with real generation | `guardian/routes/media.py:311` | M | Provider factory |
| **Add Configuration** | IMAGE_GEN_PROVIDER, API keys | `.env.example`, config | S | None |
| **Download and Save** | Download image bytes, save to storage | `guardian/routes/media.py` | M | requests library |
| **Write Tests** | Mock provider, test endpoint | `tests/routes/test_media_generation.py` (new) | M | pytest-mock |

**Optional (Post-MVP):**
- Stability AI provider
- Ollama local models
- Model selection UI
- Advanced parameters (size, quality, style)

#### **Validation Plan**

**Manual Test Script:**
```bash
# Setup
1. Set IMAGE_GEN_PROVIDER=openai in .env
2. Set OPENAI_API_KEY=sk-... in .env
3. Restart backend

# Test Generation Flow
4. Open Gallery view, click "Generate"
5. Enter prompt: "A serene mountain landscape at sunset"
6. Click "Generate", verify loading spinner
7. Wait for completion (~10-30 seconds)
8. Verify generated image appears in gallery
9. Check database: SELECT * FROM generated_images;
10. Check filesystem: ls /app/media/generated/
11. Click image - verify it displays correctly
12. Check prompt is stored in metadata

# Test Error Handling
13. Set invalid OPENAI_API_KEY
14. Try generating - verify friendly error message
15. Check logs for detailed error
```

**Automated Test Recommendations:**
- **Unit Tests:**
  - `tests/image_gen/test_openai_provider.py` - Test provider with mocked API
  - `tests/image_gen/test_provider_factory.py` - Test provider selection
- **Integration Tests:**
  - `tests/routes/test_media_generation.py`:
    - test_generate_image_success
    - test_generate_image_invalid_prompt
    - test_generate_image_provider_error
    - test_generated_image_stored_correctly
- **E2E Tests:**
  - `frontend/src/cypress/e2e/image_generation.cy.ts`:
    - test_generate_from_modal
    - test_image_appears_in_gallery
    - test_error_handling

**Test Locations:**
- `tests/image_gen/` - Provider unit tests (new)
- `tests/routes/` - Endpoint integration tests
- `frontend/src/cypress/e2e/` - E2E tests

---

### 2.6 Generate Documents (Code / Literature / Diagrams)

#### **Current State**

**✅ What's Working:**
- **Database Schema** (`guardian/db/models.py`) - GeneratedDocument model with format support (txt/md/docx/pdf/html/json)
- **Autosave** (`guardian/routes/documents.py`) - POST `/api/documents/autosave` working for session notes
- **Collaborative Editing** (`frontend/src/components/editor/CollaborativeNote.tsx`) - Real-time WebSocket editing
- **Document Storage** - PostgreSQL with proper schema
- **Document Retrieval** - GET `/api/threads/{thread_id}/documents` working
- **Document Sharing** - Shareable links with expiry

**⚠️ Partial:**
- **Document UI** - Display components exist, no generation UI

**❌ Missing:**
- **LLM-Powered Generation** - No prompt-based document creation
- **Generation API Endpoint** - No `/api/documents/generate`
- **Document Type Selector** - No UI for choosing doc types
- **Generation Modal** - No DocumentGenModal (unlike ImageGenModal)
- **Templates** - No generation templates or formatting logic
- **Chat Integration** - No inline generation from chat
- **Tests** - No tests for generation (autosave is tested)

#### **Core Loop Definition**

```
1. User clicks "Generate Document" in UI
   ↓
2. Modal opens with document type selector
   ↓
3. User selects type (code/markdown/diagram)
   ↓
4. User enters prompt or description
   ↓
5. POST to `/api/documents/generate`
   ↓
6. Backend routes to LLM with type-specific system prompt
   ↓
7. LLM generates formatted content
   ↓
8. Content saved to `generated_documents` table
   ↓
9. Document linked to current thread
   ↓
10. Document displayed in DocumentsView
   ↓
11. User can open, edit, or regenerate
```

#### **Gap Analysis**

| Loop Step | Current Implementation | Gap/Problem | Concrete Fix |
|-----------|----------------------|-------------|--------------|
| **1. User clicks** | ❌ Missing | **No "Generate Document" button** | Add to Documents view |
| **2. Modal opens** | ❌ Missing | **No DocumentGenModal component** | Create modal component |
| **3. Select type** | ❌ Missing | **No type selector UI** | Add dropdown for doc types |
| **4. Enter prompt** | ❌ Missing | **No prompt input** | Add textarea in modal |
| **5. POST to API** | ❌ Missing | **No `/api/documents/generate` endpoint** | Create endpoint |
| **6. Route to LLM** | ❌ Missing | **No LLM integration for docs** | Use existing ai_router |
| **7. Generate content** | ❌ Missing | **No generation logic** | Call LLM with type-specific prompts |
| **8. Save to DB** | ⚠️ Partial - autosave works | **No 'generated' relation type** | Reuse GeneratedDocument model |
| **9. Link to thread** | ✅ Working - ThreadDocument model | None | N/A |
| **10. Display** | ✅ Working - DocumentsView | None | N/A |
| **11. Edit/regenerate** | ⚠️ Partial - edit works, no regen | **No regeneration logic** | Add "Try Again" button |

#### **Implementation Tasks**

**Priority: MEDIUM (Infrastructure exists, needs generation logic)**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **Create DocumentGenModal** | Modal with type selector and prompt | `frontend/src/components/modals/DocumentGenModal.tsx` (new) | M | None |
| **Add Generate Button** | Trigger modal from Documents view | `frontend/src/components/documents/DocumentsView.tsx` | S | Modal component |
| **Create Generation Endpoint** | POST `/api/documents/generate` | `guardian/routes/documents.py` | M | ai_router |
| **Type-Specific Prompts** | System prompts for code/markdown/diagrams | `guardian/prompts/document_templates.py` (new) | M | None |
| **LLM Integration** | Call ai_router with type-specific context | `guardian/routes/documents.py` | M | Existing ai_router |
| **Format Validators** | Validate generated content format | `guardian/validators/document_formats.py` (new) | S | None |
| **Regenerate Function** | "Try Again" button to regenerate | `frontend/src/components/documents/` | S | Generation endpoint |
| **Write Tests** | Mock LLM, test generation flow | `tests/routes/test_document_generation.py` (new) | M | pytest-mock |

**Document Types to Support (MVP):**
- **Code Snippet** - Generates code with syntax highlighting
- **Markdown Document** - Generates formatted markdown
- **Mermaid Diagram** - Generates diagram DSL (rendered later)

**Optional (Post-MVP):**
- PDF export
- DOCX export
- HTML export
- Custom templates
- Multi-file generation (e.g., full repo)

#### **Validation Plan**

**Manual Test Script:**
```bash
# Setup
1. Ensure LLM provider configured (GROQ_API_KEY or OPENAI_API_KEY)
2. Start full stack

# Test Code Generation
3. Open Documents view, click "Generate Document"
4. Select "Code Snippet" type
5. Enter prompt: "Python function to calculate Fibonacci sequence"
6. Click "Generate"
7. Verify code appears in document list
8. Click to open - verify syntax highlighting
9. Edit code in CollaborativeNote - verify save works

# Test Markdown Generation
10. Generate document, select "Markdown Document"
11. Enter prompt: "Write a technical blog post about RAG systems"
12. Verify markdown rendered correctly
13. Check for proper formatting (headers, lists, code blocks)

# Test Diagram Generation
14. Generate document, select "Mermaid Diagram"
15. Enter prompt: "Create a flowchart for user authentication"
16. Verify Mermaid syntax generated
17. Verify diagram can be rendered (if viewer implemented)

# Test Error Handling
18. Generate with empty prompt - verify validation error
19. Generate with very long prompt - verify truncation or error
20. Check logs for generation metrics (latency, tokens)
```

**Automated Test Recommendations:**
- **Unit Tests:**
  - `tests/prompts/test_document_templates.py` - Test prompt construction
  - `tests/validators/test_document_formats.py` - Test format validation
- **Integration Tests:**
  - `tests/routes/test_document_generation.py`:
    - test_generate_code_snippet
    - test_generate_markdown_document
    - test_generate_mermaid_diagram
    - test_invalid_document_type
    - test_generation_error_handling
    - test_document_stored_correctly
- **E2E Tests:**
  - `frontend/src/cypress/e2e/document_generation.cy.ts`:
    - test_generate_from_modal
    - test_document_appears_in_list
    - test_open_and_edit_generated_doc

**Test Locations:**
- `tests/prompts/` - Prompt template tests (new)
- `tests/routes/` - Generation endpoint tests (new)
- `frontend/src/cypress/e2e/` - E2E tests (new)

---

## 3. Milestones & Timeline

### Milestone 0: Blockers & Infrastructure (1-2 days)

**Goal:** Fix critical blockers that prevent other work

- [ ] Enable real embeddings (EMBEDDING_BACKEND=local)
- [ ] Configure ChromaDB persistence (CHROMA_PERSIST_DIRECTORY)
- [ ] Verify Neo4j running and accessible
- [ ] Verify PostgreSQL migrations applied
- [ ] Install missing dependencies (PyPDF2, python-docx)
- [ ] Run test suite - ensure all passing

**Deliverables:**
- `.env` properly configured
- All services running (docker-compose up)
- Test suite green

---

### Milestone 1: Memory + Context Broker + Guardian Chat Loop Closed (3-5 days)

**Goal:** RAG system fully operational with real embeddings

**Tasks:**
- [x] Infrastructure verified (from Milestone 0)
- [ ] Implement Retriever (replace stub)
- [ ] Wire MemoryOS to ContextBroker
- [ ] Add auto-embedding of chat messages
- [ ] Add frontend depth selector in chat UI
- [ ] Create memory browser UI component
- [ ] Write integration tests for RAG pipeline
- [ ] Manual validation (end-to-end test script)

**Acceptance Criteria:**
- User can add memory entry
- Chat question retrieves relevant memories
- Assistant response references memories
- All depth modes work (shallow/normal/deep/diagnostic)
- Tests pass with >80% coverage

**Effort:** ~3-5 developer days

---

### Milestone 2: ChatGPT Migration Working with UI Confirmation (2-3 days)

**Goal:** Imported ChatGPT data accessible from UI

**Tasks:**
- [x] CLI working (already done)
- [ ] Create `/api/legacy/threads` endpoint
- [ ] Create `/api/legacy/search` endpoint
- [ ] Wire LegacyThreadsModal to API
- [ ] Add search bar in modal
- [ ] Add thread click → view messages
- [ ] Write API endpoint tests
- [ ] Manual validation (import + view flow)

**Acceptance Criteria:**
- User runs `codexify migrate` successfully
- User opens "Legacy Threads" in UI
- Imported threads listed with metadata
- User can search imported threads
- User can view conversation messages
- Graph visualization shows relationships (optional)

**Effort:** ~2-3 developer days

---

### Milestone 3: Document Upload + Embed Usable in Chat (3-4 days)

**Goal:** Uploaded documents retrievable via RAG in chat

**Tasks:**
- [x] Real embeddings working (from Milestone 1)
- [ ] Implement PDF parser (PyPDF2)
- [ ] Implement DOCX parser (python-docx)
- [ ] Create chunking strategy (RecursiveCharacterTextSplitter)
- [ ] Create `/api/embeddings` endpoint
- [ ] Wire useUploader to call endpoint
- [ ] Add vector_ids to uploaded_documents schema
- [ ] Verify RAG retrieves document chunks
- [ ] Write processing tests (parsers, chunker)
- [ ] Manual validation (upload → chat flow)

**Acceptance Criteria:**
- User uploads PDF document
- Document text extracted and chunked
- Chunks embedded in ChromaDB
- User asks question about document
- Assistant responds with document context
- Source attribution shown (nice-to-have)

**Effort:** ~3-4 developer days

---

### Milestone 4: Image Gallery + Generate Image (3-4 days)

**Goal:** Full image upload and generation workflows

**Tasks:**
- [ ] Wire useUploader to `/api/media/upload/image`
- [ ] Add thumbnail generation (PIL)
- [ ] Add thumbnail_url to database schema
- [ ] Implement OpenAI DALL-E provider
- [ ] Create provider factory
- [ ] Wire `/api/media/generate/image` to provider
- [ ] Add IMAGE_GEN_PROVIDER env vars
- [ ] Add lightbox modal for full image view
- [ ] Write media tests (upload, generate)
- [ ] Manual validation (upload + generate flows)

**Acceptance Criteria:**
- User uploads image - persists after refresh
- User generates image from prompt
- Generated image appears in gallery
- Thumbnails displayed for performance
- Lightbox opens on image click
- Tests pass for both workflows

**Effort:** ~3-4 developer days

---

### Milestone 5: Document Generation Flow (2-3 days)

**Goal:** Minimal but working document generation

**Tasks:**
- [ ] Create DocumentGenModal component
- [ ] Add "Generate Document" button to UI
- [ ] Create `/api/documents/generate` endpoint
- [ ] Create type-specific prompt templates (code/markdown/diagram)
- [ ] Wire endpoint to ai_router
- [ ] Add format validators
- [ ] Write generation tests
- [ ] Manual validation (generate all types)

**Acceptance Criteria:**
- User clicks "Generate Document"
- User selects type and enters prompt
- Code snippet generated with syntax
- Markdown document formatted correctly
- Diagram DSL generated (Mermaid)
- Document appears in DocumentsView
- Tests pass for all document types

**Effort:** ~2-3 developer days

---

### **Total MVP Timeline: 13-21 Developer Days (~3-4 weeks)**

**Critical Path:**
1. Milestone 0 (blockers) → Milestone 1 (RAG) → Milestone 3 (documents)
2. Milestones 2, 4, 5 can be parallelized if multiple developers

**Recommended Order (Single Developer):**
1. Milestone 0 - blockers
2. Milestone 1 - RAG (highest priority)
3. Milestone 3 - doc upload (depends on M1)
4. Milestone 4 - images (independent)
5. Milestone 2 - ChatGPT UI (polish)
6. Milestone 5 - doc generation (nice-to-have)

---

## 4. Risks, Assumptions & Dependencies

### **Risks**

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Real embeddings too slow** | Poor UX with long waits | Use OpenAI API for speed, add progress indicators |
| **PDF parsing fails on complex PDFs** | Some docs can't be embedded | Add fallback to OCR (Tesseract), graceful degradation |
| **DALL-E API costs too high** | Budget exceeded quickly | Set daily limits, add cost warnings in UI |
| **ChromaDB persistence issues** | Data loss on restart | Use mounted volumes, add health checks |
| **Neo4j data isolated from main app** | Fragmented user experience | Document workaround: use CLI for migrations, add sync tool later |
| **Scope creep returns** | MVP never ships | Ruthlessly defer features not on this roadmap |

### **Assumptions**

- **Services Running:** Docker Compose runs Postgres, Neo4j, ChromaDB reliably
- **API Keys Available:** User provides OPENAI_API_KEY or GROQ_API_KEY for embeddings/generation
- **Local Development:** Primary deployment is local-first (not cloud)
- **Single User:** MVP is single-user, no auth/RBAC needed yet
- **English Only:** No i18n/l10n in MVP
- **Modern Browser:** Chrome/Firefox/Safari latest versions

### **Dependencies**

**External Services:**
- PostgreSQL 15
- Neo4j 5
- ChromaDB (via Python client)
- OpenAI API (for embeddings and DALL-E)
- Groq API (alternative for chat LLM)

**Python Libraries (already in requirements.txt):**
- sentence-transformers (local embeddings)
- PyPDF2 or pdfplumber (PDF parsing)
- python-docx (DOCX parsing)
- langchain-text-splitters (chunking)
- PIL/Pillow (image processing)

**System Requirements:**
- Docker 20.10+
- Docker Compose v2.0+
- 8GB RAM minimum (16GB recommended)
- 10GB disk space

### **Blockers Requiring User Action**

1. **API Keys:** User must obtain and configure:
   - `OPENAI_API_KEY` (for embeddings and DALL-E)
   - Or `GROQ_API_KEY` (for chat LLM)

2. **Service Configuration:**
   - Set `EMBEDDING_BACKEND=local` or `openai`
   - Set `VECTOR_STORE=chroma`
   - Set `IMAGE_GEN_PROVIDER=openai`

3. **Database Initialization:**
   - Run `docker-compose up` to start services
   - Run `alembic upgrade head` if migrations not auto-applied

---

## 5. Deferred Features (Post-MVP Parking Lot)

### **Phase 1.1 (Polish & Optimization)**

**Memory/RAG Enhancements:**
- [ ] Memory consolidation UI (trigger manual consolidation)
- [ ] Memory tagging and organization
- [ ] Advanced RAG: hybrid search (vector + BM25)
- [ ] Conversation branching UI
- [ ] Memory heat visualization

**Upload Enhancements:**
- [ ] Batch upload (multiple files at once)
- [ ] Upload progress bars
- [ ] Background processing queue (Celery)
- [ ] OCR for scanned PDFs
- [ ] Audio transcription (Whisper integration)

**Gallery Enhancements:**
- [ ] Image search by description
- [ ] Image tagging and collections
- [ ] Bulk delete
- [ ] Sort/filter options (date, size, project)
- [ ] Share gallery view

**Generation Enhancements:**
- [ ] Stability AI provider (Stable Diffusion)
- [ ] Ollama local models (images and LLMs)
- [ ] Model selection UI (DALL-E 2 vs 3, etc.)
- [ ] Generation history and favorites
- [ ] Remix/variations for images

### **Phase 1.2 (Advanced Features)**

**Multi-User & Permissions:**
- [ ] User authentication (OAuth, SAML)
- [ ] Role-based access control (RBAC)
- [ ] Team workspaces
- [ ] Sharing permissions

**Connectors & Integrations:**
- [ ] GitHub connector (issues, PRs, code)
- [ ] Google Drive connector (docs)
- [ ] Notion connector (pages)
- [ ] Slack connector (messages)
- [ ] Custom connector SDK

**Plugin System:**
- [ ] Plugin marketplace
- [ ] Plugin discovery UI
- [ ] Plugin sandboxing and security
- [ ] Plugin analytics and telemetry

**Graph Features:**
- [ ] Knowledge graph UI (interactive visualization)
- [ ] Relationship exploration
- [ ] Graph-based search
- [ ] Entity extraction and linking

### **Phase 2.0 (Enterprise Features)**

**Scalability:**
- [ ] Multi-node deployment
- [ ] Kubernetes manifests
- [ ] Horizontal scaling guides
- [ ] Load balancing

**Cloud Storage:**
- [ ] S3 storage provider (complete)
- [ ] GCS storage provider (complete)
- [ ] Azure Blob storage
- [ ] CDN integration

**Monitoring & Observability:**
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Error tracking (Sentry)

**Security & Compliance:**
- [ ] Encryption at rest
- [ ] Audit log export
- [ ] GDPR compliance tools
- [ ] SOC 2 certification

### **Phase 3.0 (AI Capabilities)**

**Advanced AI:**
- [ ] Fine-tuning support for local models
- [ ] Custom embedding models
- [ ] Multi-modal RAG (images, audio, video)
- [ ] Agent orchestration (LangGraph integration)
- [ ] Tool calling and function execution

**Document Intelligence:**
- [ ] Document comparison and diff
- [ ] Automatic summarization
- [ ] Key point extraction
- [ ] Citation and reference management

**Collaboration:**
- [ ] Real-time co-editing for all docs
- [ ] Commenting and annotations
- [ ] Review workflows
- [ ] Version control and branching

### **Features to Explicitly Avoid (Not Aligned with MVP)**

- ❌ Mobile apps (iOS, Android)
- ❌ Browser extensions
- ❌ Video/audio generation
- ❌ 3D model generation
- ❌ Blockchain/Web3 features
- ❌ Cryptocurrency payments
- ❌ Social media features (likes, follows, feeds)
- ❌ Gamification (badges, achievements)

---

## 6. Implementation Quick Reference

### **Priority Matrix**

| Feature | Priority | Complexity | Effort | Dependency |
|---------|----------|------------|--------|------------|
| **Enable Real Embeddings** | 🔴 CRITICAL | Low | 0.5d | None |
| **RAG Loop (Memory + Context)** | 🔴 CRITICAL | Medium | 3-5d | Real embeddings |
| **Doc Upload + Embed** | 🔴 CRITICAL | Medium | 3-4d | Real embeddings |
| **Image Upload (wire frontend)** | 🟡 HIGH | Low | 1d | None |
| **Image Generation (DALL-E)** | 🟡 HIGH | Medium | 3-4d | OPENAI_API_KEY |
| **ChatGPT UI** | 🟢 MEDIUM | Medium | 2-3d | CLI working |
| **Document Generation** | 🟢 MEDIUM | Medium | 2-3d | LLM config |

### **Estimated LOC Changes**

| Component | New Files | Modified Files | Est. LOC |
|-----------|-----------|----------------|----------|
| **Embeddings** | 3 | 5 | ~500 |
| **RAG Loop** | 2 | 4 | ~400 |
| **Doc Upload** | 5 | 3 | ~800 |
| **Image Upload** | 0 | 2 | ~100 |
| **Image Gen** | 6 | 2 | ~600 |
| **ChatGPT UI** | 2 | 3 | ~400 |
| **Doc Gen** | 4 | 2 | ~500 |
| **Tests** | 12 | 0 | ~2000 |
| **Total** | ~34 | ~21 | ~5300 |

### **Key Files to Modify**

**Backend:**
- `guardian/vector/embeds.py` - Enable real embeddings
- `guardian/memoryos/retriever.py` - Implement retrieval
- `guardian/context/broker.py` - Wire MemoryOS
- `guardian/routes/embeddings.py` - NEW: Document embedding endpoint
- `guardian/routes/media.py` - Complete image generation
- `guardian/routes/documents.py` - Add document generation
- `guardian/routes/legacy_threads.py` - NEW: ChatGPT UI API
- `guardian/processing/parsers.py` - NEW: PDF/DOCX parsing
- `guardian/processing/chunker.py` - NEW: Text chunking
- `guardian/image_gen/providers/openai_provider.py` - NEW: DALL-E

**Frontend:**
- `frontend/src/hooks/useUploader.ts` - Wire to backend
- `frontend/src/features/chat/GuardianChat.tsx` - Add depth selector
- `frontend/src/components/memory/MemoryBrowser.tsx` - NEW: Memory UI
- `frontend/src/components/modals/LegacyThreadsModal.tsx` - Wire to API
- `frontend/src/components/modals/DocumentGenModal.tsx` - NEW: Doc gen UI

**Configuration:**
- `.env.example` - Add all new env vars
- `guardian/config/settings.py` - Add new settings
- `pyproject.toml` - Ensure dependencies

**Tests:**
- `tests/vector/test_embedder.py` - NEW
- `tests/memoryos/test_retriever.py` - NEW
- `tests/processing/test_parsers.py` - NEW
- `tests/processing/test_chunker.py` - NEW
- `tests/routes/test_embeddings.py` - NEW
- `tests/routes/test_media_generation.py` - NEW
- `tests/routes/test_document_generation.py` - NEW
- `tests/routes/test_legacy_threads.py` - NEW
- `tests/integration/test_rag_e2e.py` - NEW

---

## 7. Success Metrics

### **MVP Acceptance Criteria**

Each core feature must meet these criteria:

1. **Memory/RAG + Guardian Chat:**
   - ✅ User can add memory entries via API
   - ✅ Chat retrieves relevant memories
   - ✅ Assistant responses include memory context
   - ✅ All depth modes functional
   - ✅ Real embeddings (not stubs)

2. **ChatGPT Migration:**
   - ✅ CLI imports conversations successfully
   - ✅ UI shows imported threads
   - ✅ User can search imported data
   - ✅ Migration progress visible
   - ✅ Data persists across restarts

3. **Upload Documents + Embed:**
   - ✅ User uploads PDF/DOCX/TXT/MD
   - ✅ Text extracted and chunked
   - ✅ Chunks embedded in ChromaDB
   - ✅ Chat retrieves document chunks
   - ✅ Assistant uses document context

4. **Upload Images to Gallery:**
   - ✅ User uploads images via UI
   - ✅ Images persist to backend storage
   - ✅ Gallery displays thumbnails
   - ✅ Full images viewable
   - ✅ Metadata accessible

5. **Generate Images:**
   - ✅ User enters prompt in modal
   - ✅ Image generated via DALL-E
   - ✅ Image saved to storage
   - ✅ Image appears in gallery
   - ✅ Error handling graceful

6. **Generate Documents:**
   - ✅ User selects document type
   - ✅ User enters prompt
   - ✅ Document generated via LLM
   - ✅ Document saved and linked
   - ✅ Document viewable/editable

### **Performance Targets**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Embedding Latency** | <2s per document chunk | Time from upload to embed complete |
| **RAG Retrieval** | <500ms | Time for vector search |
| **Image Generation** | <30s | Time from prompt to display |
| **Document Generation** | <10s | Time from prompt to save |
| **Chat Response** | <5s first token | Time to streaming start |
| **Upload** | <1s per MB | File upload throughput |

### **Quality Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Test Coverage** | >80% | pytest --cov |
| **Retrieval Precision** | >0.7 | Relevant results / total results |
| **Uptime** | >99% | Docker health checks |
| **Error Rate** | <1% | Failed requests / total requests |

### **User Experience**

- [ ] No broken UI elements
- [ ] All buttons have clear labels
- [ ] Loading states for async operations
- [ ] Friendly error messages (no stack traces to user)
- [ ] Keyboard navigation works
- [ ] Mobile responsive (nice-to-have)

---

## 8. FAQ & Troubleshooting

### **Q: Why are embeddings stubs by default?**

**A:** To allow the system to run without API keys or large model downloads. For MVP, you must enable real embeddings (`EMBEDDING_BACKEND=local` or `openai`).

### **Q: Can I use Ollama instead of OpenAI?**

**A:** For chat LLMs, yes (Ollama integration exists). For embeddings and image generation, Ollama support is post-MVP.

### **Q: Why is ChatGPT data in Neo4j instead of Postgres?**

**A:** Graph structure (threads → messages → parent/child) fits Neo4j better. A sync tool to Postgres is deferred to post-MVP.

### **Q: Do I need all three databases (Postgres, Neo4j, ChromaDB)?**

**A:** For full MVP, yes. Postgres for app data, Neo4j for ChatGPT migration, ChromaDB for embeddings. You can skip Neo4j if not using ChatGPT migration.

### **Q: What if I don't have an OpenAI API key?**

**A:** Use local embeddings (sentence-transformers) and Groq for chat. Image generation requires OpenAI (or wait for Stability/Ollama support post-MVP).

### **Q: How do I know if embeddings are working?**

**A:** Check logs for "Embedding X documents..." and verify ChromaDB collection grows: `chromadb-client list_collections`.

### **Q: The gallery shows mock images, not my uploads.**

**A:** This is expected until useUploader is wired to backend. See Milestone 4 tasks.

### **Q: Can I deploy this to production?**

**A:** MVP is designed for local-first development. Production deployment (Kubernetes, cloud storage, monitoring) is Phase 2.0.

---

## 9. Next Steps

### **Immediate Actions (Next 24 Hours)**

1. **Read this roadmap thoroughly**
2. **Run the existing test suite:** `pytest guardian/tests/`
3. **Verify services running:** `docker-compose ps`
4. **Check .env configuration:** Ensure API keys set
5. **Pick a starting point:** Recommend Milestone 0 → Milestone 1

### **Week 1 Focus**

- Complete Milestone 0 (blockers)
- Start Milestone 1 (RAG loop)
- Daily check-ins on progress
- Update this roadmap if blockers found

### **Communication**

- **Daily:** Update GitHub Issues/Project Board with progress
- **Weekly:** Review completed milestones, adjust timeline
- **Blockers:** Flag immediately in Slack/Discord/Issues

### **Success = Closed Loops**

Remember: **The goal is not to build everything, but to close the 6 core loops completely**. Every task in this roadmap directly serves that goal. If you find yourself building something not on this list, stop and ask: "Does this close a core loop?"

---

## 10. Appendix

### **A. Technology Stack Reference**

**Backend:**
- Python 3.10+
- FastAPI 0.119.1
- SQLAlchemy 2.0.44
- PostgreSQL 15
- Neo4j 5
- ChromaDB 1.2.1
- sentence-transformers 5.1.2
- OpenAI API (embeddings, DALL-E)
- Groq API (LLM chat)

**Frontend:**
- React 19.1.1
- TypeScript 5.x
- Vite 5.x
- Tailwind CSS 4.1.14
- Monaco Editor 0.53.0

**Infrastructure:**
- Docker & Docker Compose
- Uvicorn 0.38.0
- Alembic 1.17.0 (migrations)

### **B. File Structure Map**

```
Codexify/
├── guardian/                     # Core Python backend
│   ├── api/                     # DEPRECATED (use routes/)
│   ├── routes/                  # FastAPI route handlers ✅
│   │   ├── chat.py             # Chat completion with RAG
│   │   ├── memory.py           # Memory CRUD API
│   │   ├── media.py            # Image/doc upload, generation
│   │   ├── documents.py        # Document autosave, retrieval
│   │   └── rag_upload.py       # RAG upload (stub)
│   ├── core/                    # Business logic
│   │   ├── ai_router.py        # LLM provider routing
│   │   ├── storage.py          # File storage abstraction
│   │   └── event_bus.py        # Event system
│   ├── context/                 # RAG & context assembly
│   │   └── broker.py           # ContextBroker (depth modes) ✅
│   ├── vector/                  # Vector store
│   │   ├── store.py            # SQLite VectorStore ✅
│   │   └── embeds.py           # Embedder (stub → real)
│   ├── memory/                  # Memory system
│   │   ├── query_memory.py     # MemoryStore ✅
│   │   └── memoryos.py         # Advanced memory (not integrated)
│   ├── memoryos/                # MemoryOS package
│   │   ├── memoryos.py         # Memoryos class ✅
│   │   └── retriever.py        # Retriever (STUB)
│   ├── db/                      # Database models
│   │   ├── models.py           # SQLAlchemy models ✅
│   │   └── neo.py              # Neo4j helpers ✅
│   ├── processing/              # NEW: Document processing
│   │   ├── parsers.py          # NEW: PDF/DOCX parsers
│   │   └── chunker.py          # NEW: Text chunking
│   ├── image_gen/               # NEW: Image generation
│   │   ├── image_service.py    # NEW: Provider base
│   │   └── providers/          # NEW: DALL-E, Stability, etc.
│   ├── cli/                     # Command-line interfaces
│   │   └── ingest_cli.py       # Ingest commands ✅
│   ├── sensors/                 # System diagnostics
│   │   └── state.py            # Sensors ✅
│   └── guardian_api.py          # FastAPI app entry point ✅
│
├── backend/                     # Backend config & services
│   ├── vector_store/            # Vector store backends
│   │   ├── chroma_store.py     # ChromaDB integration ✅
│   │   ├── pgvector_store.py   # PGVector integration
│   │   └── factory.py          # Store factory ✅
│   ├── rag/                     # RAG modules (incomplete)
│   │   └── document_ingest.py  # Document ingest (stub)
│   ├── scripts/                 # Utility scripts
│   │   └── seed_defaults.py    # Database seeding
│   └── Dockerfile               # Backend container
│
├── scripts/                     # Standalone scripts
│   └── chatgpt_import/          # ChatGPT migration ✅
│       ├── cli_migrate.py      # CLI entry point ✅
│       ├── import_chatgpt.py   # Core import logic ✅
│       └── README.md           # Comprehensive docs ✅
│
├── frontend/src/                # React frontend
│   ├── components/              # UI components
│   │   ├── persona/layout/     # Main app shell
│   │   │   ├── AppShell.tsx    # Main container ✅
│   │   │   └── GuardianChatWithSidebar.tsx ✅
│   │   ├── gallery/            # Gallery components
│   │   │   └── GalleryView.tsx # Gallery display ✅
│   │   ├── documents/          # Document components
│   │   │   └── DocumentsView.tsx # Doc browser ✅
│   │   ├── editor/             # Editors
│   │   │   └── CollaborativeNote.tsx # Real-time editor ✅
│   │   ├── modals/             # Modals
│   │   │   ├── ImageGenModal.tsx # Image gen ✅
│   │   │   ├── LegacyThreadsModal.tsx # ChatGPT (stub)
│   │   │   └── DocumentGenModal.tsx # NEW: Doc gen
│   │   └── memory/             # NEW: Memory UI
│   │       └── MemoryBrowser.tsx # NEW: Memory browser
│   ├── hooks/                   # Custom hooks
│   │   └── useUploader.ts      # Upload hook (needs wiring)
│   └── features/                # Feature modules
│       ├── chat/               # Chat features
│       │   └── GuardianChat.tsx # Chat component ✅
│       └── memory/             # Memory features
│           └── useMemory.ts    # Memory hook ✅
│
├── tests/                       # Test suite
│   ├── routes/                  # Route tests
│   │   ├── test_documents_autosave.py ✅
│   │   └── test_thread_documents.py ✅
│   ├── scripts/                 # Script tests
│   │   ├── test_chatgpt_import.py ✅
│   │   └── test_cli_migrate.py ✅
│   ├── vector/                  # NEW: Vector tests
│   ├── memoryos/                # NEW: Memory tests
│   ├── processing/              # NEW: Processing tests
│   └── integration/             # NEW: E2E tests
│
├── docs/                        # Documentation
│   └── codexify-mvp-roadmap.md # THIS FILE
│
├── docker-compose.yml           # Full stack orchestration ✅
├── .env.example                 # Environment template
└── pyproject.toml               # Python project metadata ✅
```

### **C. Environment Variables Reference**

**Copy to `.env` and configure:**

```bash
# Database
DATABASE_URL=postgresql://guardian:guardian@db:5432/guardian
NEO4J_BOLT_URL=bolt://neo4j:guardian@neo4j:7687
NEO4J_URL=bolt://localhost:7687  # For scripts
NEO4J_USER=neo4j
NEO4J_PASS=guardian

# Embeddings (REQUIRED FOR MVP)
EMBEDDING_BACKEND=local  # or "openai"
EMBEDDING_DIM=384  # for sentence-transformers all-MiniLM-L6-v2
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Vector Store (REQUIRED FOR MVP)
VECTOR_STORE=chroma  # or "pgvector"
CHROMA_PERSIST_DIRECTORY=./chroma  # or /app/chroma
CHROMA_PATH=./chroma

# LLM Providers (REQUIRED - choose one or both)
GROQ_API_KEY=gsk_...  # For fast chat LLM
OPENAI_API_KEY=sk-...  # For embeddings and DALL-E
LLM_PROVIDER=groq  # or "openai"

# Image Generation (REQUIRED for Milestone 4)
IMAGE_GEN_PROVIDER=openai  # only option for MVP
# OPENAI_API_KEY already set above

# API
GUARDIAN_API_KEY=001a8ae3c2e7fe3a89c466803beb3449df5989e97f6e170be43856a38e3e9e8e
PORT=8888

# Storage
STORAGE_TYPE=local  # or "s3", "gcs" (post-MVP)
STORAGE_BASE_PATH=/app/media
STORAGE_URL_PREFIX=/media

# Memory
MEMORY_RETENTION_DAYS=90

# Optional
ENABLE_BLIP_MODEL=false  # Image captioning (heavy)
ENABLE_CONNECTOR_WORKER=false  # Connectors (post-MVP)
```

### **D. Common Commands**

```bash
# Start full stack
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend alembic upgrade head

# Run tests
docker-compose exec backend pytest

# ChatGPT migration
docker-compose exec backend codexify migrate /path/to/conversations.json

# Check ChromaDB collections
docker-compose exec backend python -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma')
print(client.list_collections())
"

# Check Neo4j data
docker-compose exec neo4j cypher-shell -u neo4j -p guardian "
MATCH (t:Thread)-[:CONTAINS]->(m:Message)
RETURN count(t) as threads, count(m) as messages;
"

# Restart backend only
docker-compose restart backend

# Clean and rebuild
docker-compose down -v
docker-compose up --build
```

### **E. Useful Links**

- **Codebase:** https://github.com/Resonant-Jones/Codexify
- **API Docs:** http://localhost:8888/docs (when running)
- **Neo4j Browser:** http://localhost:7474 (auth: neo4j/guardian)
- **FastAPI:** https://fastapi.tiangolo.com/
- **ChromaDB:** https://docs.trychroma.com/
- **Sentence Transformers:** https://www.sbert.net/
- **OpenAI API:** https://platform.openai.com/docs/

---

## Summary

This roadmap provides a **concrete, actionable plan** to close the 6 core MVP loops for Codexify. Every task is mapped to specific files, dependencies are identified, and acceptance criteria are clear.

**Key Takeaways:**

1. **RAG loop (Memory + Context)** is highest priority - enables all other features
2. **ChatGPT migration** works via CLI, UI is polish
3. **Document upload** needs embedding pipeline wired
4. **Image upload** just needs frontend-backend connection
5. **Image generation** needs DALL-E provider implemented
6. **Document generation** needs generation endpoint + modal

**Total Effort:** 13-21 developer days (~3-4 weeks) for single developer

**Success = Demonstrable End-to-End Flows** for all 6 features.

---

**Roadmap Version:** 1.0
**Last Updated:** 2025-11-12
**Next Review:** After Milestone 1 completion
**Maintained By:** @Resonant-Jones

---

*"In the convergence of memory and intelligence, we find not just answers, but understanding."*

**Let's ship this MVP! 🚀**
