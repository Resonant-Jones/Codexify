# Codexify MVP Roadmap & Core Loop Plan

**Document Version:** 2.0 (Complete Codebase Audit)
**Date:** 2026-01-20
**Author:** Technical Product Lead + Staff Engineer Audit (Claude Code)
**Scope:** MVP Feature Completeness Analysis & Implementation Plan

---

## 1. Overview & Goals

### 1.1 Executive Summary

This document provides a comprehensive audit of the Codexify codebase against the six core MVP features, identifies implementation gaps, and defines a concrete roadmap to achieve a fully operational MVP.

**Current Status:** Codexify is **75-85% complete** at MVP level. Most core infrastructure is production-ready, but several critical integration gaps prevent end-to-end workflows from being fully operational.

**Primary Objective:** Close all core feature loops to enable immediate dogfooding and production use.

### 1.2 MVP Philosophy

The MVP is defined by these principles:
- **End-to-end working loops** for all 6 core features
- **No scope creep** - defer everything not critical to core loops
- **Pragmatic over perfect** - working beats polished for MVP
- **Testable & verifiable** - each loop must have clear validation steps

### 1.3 Audit Methodology

This audit was conducted via systematic exploration using specialized agents:
1. **Memory/RAG exploration** - analyzed vector stores, embeddings, context broker, retrieval systems
2. **ChatGPT migration exploration** - examined ingestion logic, UI, API endpoints, documentation
3. **Document upload exploration** - investigated upload pipelines, parsing, embedding, storage
4. **Image gallery exploration** - reviewed upload/display/storage systems
5. **Image generation exploration** - assessed provider integrations, UI, database tracking
6. **Document generation exploration** - examined existing infrastructure and missing features

**Key Finding:** Excellent infrastructure exists, but wiring gaps and missing UI components prevent end-to-end loops from closing.

---

## 2. Core MVP Features

### 2.1 Memory / RAG + Context Broker + Guardian Chat

#### Current State

**Status:** 🟡 **85% Complete - Mostly Working**

The memory/RAG system has excellent infrastructure but needs integration testing and some wiring fixes.

**What Exists:**

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Vector Stores** | `backend/vector_store/chroma_store.py` | ✅ Complete | ChromaDB with persistence, namespace support |
| | `backend/vector_store/pgvector_store.py` | ✅ Complete | Postgres/pgvector, production-ready |
| | `backend/vector_store/factory.py` | ✅ Complete | Factory pattern for store selection |
| **Embeddings** | `guardian/memoryos/embedders/local_embedder.py` | ✅ Complete | SentenceTransformers with LRU cache (1024) |
| | `guardian/memoryos/embedders/openai_embedder.py` | ✅ Complete | OpenAI API with caching |
| | `guardian/runtime/embed/embedder.py` | ✅ Complete | Unified CodexifyEmbedder |
| **Context Broker** | `guardian/context/broker.py` | ✅ Complete | Multi-depth context assembly (shallow/normal/deep/diagnostic) |
| **Retriever** | `guardian/memoryos/retriever.py` | ✅ Complete | Vector-based semantic search |
| **MemoryOS** | `guardian/memoryos/memoryos.py` | 🟡 Mostly Done | Short/mid/long-term memory, needs edge case testing |
| **Chat DB** | `guardian/chat/chat.py` | 🟡 Basic | SQLite-based, limited features |
| **Memory Routes** | `guardian/routes/memory.py` | 🟡 Partial | Memory silos implemented, needs better error handling |
| **Graph Context** | `guardian/graph/*` | 🟡 Optional | Neo4j integration gated by `GUARDIAN_ENABLE_GRAPH_CONTEXT` |

**Environment Variables:**
```bash
VECTOR_STORE=pgvector|chroma                    # Backend vector store
CODEXIFY_VECTOR_STORE=faiss|chroma              # Runtime vector store
LOCAL_EMBED_MODEL=bge-large-en-v1.5             # Local embedding model
OPENAI_API_KEY=sk-...                           # For OpenAI embeddings
OPENAI_EMBED_MODEL=text-embedding-3-small       # OpenAI model
MEMORY_RETENTION_DAYS=90                        # Memory retention policy
GUARDIAN_ENABLE_GRAPH_CONTEXT=False             # Neo4j graph context
```

#### Core Loop Definition

**End-to-End Flow:**

1. **User Opens Codexify** → Selects Guardian persona/thread
2. **User Asks Question** → "What did we discuss about the authentication system?"
3. **Query Routing** → Chat message sent to backend chat endpoint
4. **Context Assembly** → Context Broker (`broker.py`) assembles context:
   - Recent messages from thread
   - Semantic search via MemoryOS retriever (vector store query)
   - Optional: Graph context from Neo4j
   - Optional: Federated peer search
5. **RAG Augmentation** → Retrieved memories merged into prompt context
6. **LLM Response** → Guardian responds using augmented context
7. **Memory Update** → New Q&A embedded and stored in vector store
8. **Conversation Continuity** → Memory updater processes short→mid-term transitions

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|------------|
| **1. User opens chat** | Frontend chat interface exists | Guardian persona selection working | None |
| **2. User asks question** | Composer component working | ✅ Working | None |
| **3. Query routing** | `guardian/guardian_api.py` or `guardian/routes/chat.py` | Multiple chat endpoints, unclear canonical | Consolidate to single `/api/chat/send` endpoint |
| **4. Context assembly** | `guardian/context/broker.py` | ✅ Well implemented | Test with real queries |
| **5. RAG augmentation** | MemoryOS retriever | ✅ Working | Verify retrieval quality |
| **6. LLM response** | Guardian API integrations | ✅ Working (OpenAI, Groq) | None |
| **7. Memory update** | `backend/rag/embedder.py` | Embedding is async/non-blocking | Add confirmation feedback |
| **8. Continuity** | `guardian/memoryos/updater.py` | Memory tier transitions working | Test edge cases (branching) |

#### Implementation Tasks

**Milestone 1: Verify & Test Core RAG Loop**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **RAG-1** | Create end-to-end integration test for RAG retrieval | `tests/integration/test_rag_loop.py` | M | ChromaDB/PGVector running |
| **RAG-2** | Document chat API endpoint conventions | `docs/api/chat-endpoints.md` | S | None |
| **RAG-3** | Add embedding success/failure feedback in UI | `frontend/src/features/chat/*` | M | Backend event system |
| **RAG-4** | Test MemoryOS tier transitions with sample data | `tests/integration/test_memoryos.py` | M | None |
| **RAG-5** | Verify Context Broker depth modes (shallow/normal/deep) | `tests/integration/test_context_broker.py` | S | None |
| **RAG-6** | Add health check endpoint for vector store status | `guardian/routes/health.py` | S | None |

**Validation Plan:**

**Manual Test Script:**
1. Start Codexify with ChromaDB or PGVector configured
2. Open chat interface, select Guardian persona
3. Send initial message: "Remember: my favorite color is blue"
4. Wait 5 seconds for embedding
5. Open new thread
6. Ask: "What is my favorite color?"
7. Verify: Response includes "blue" from retrieved memory
8. Check logs for Context Broker execution
9. Verify embedding in vector store via `/health/vector`

**Automated Tests:**
- Unit: `guardian/tests/memoryos/test_retriever.py` (✅ exists)
- Integration: `tests/integration/test_rag_loop.py` (❌ create)
- E2E: Playwright test for chat → memory → retrieval flow

---

### 2.2 ChatGPT Migration Tool

#### Current State

**Status:** 🟡 **85% Complete - Mostly Working with Router Wiring Issue**

The ChatGPT migration feature is nearly complete with excellent UI and backend logic, but has a router registration issue.

**What Exists:**

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Ingestion Logic** | `backend/rag/chatgpt_migration.py` | ✅ Complete | Parses JSON, normalizes, stores threads + messages |
| **Migration Router** | `guardian/routes/migration.py` | 🔴 Defined but NOT registered | Router exists but not in `app.py` includes |
| **RAG Upload Router** | `guardian/routes/rag_upload.py` | ✅ Active | Includes duplicate `/upload-chatgpt-export` endpoint |
| **Import Modal UI** | `frontend/src/components/modals/ChatGPTImportModal.tsx` | ✅ Complete | File picker, progress, success/error states |
| **Settings Integration** | `frontend/src/features/settings/SettingsView.tsx` | ✅ Complete | "Import from ChatGPT" button in Data tab (line 383) |
| **CLI Tool** | `scripts/chatgpt_import/import_chatgpt.py` | ✅ Complete | Rich output, timer, statistics |
| **Tests** | `guardian/tests/migration/test_chatgpt_ingest.py` | ✅ Exists | Unit tests for ingestion logic |
| **Documentation** | `docs/CHATGPT_MIGRATION_GUIDE.md` | ✅ Excellent | 932 lines, comprehensive guide |

**Supported Format:** ChatGPT JSON export (conversations.json)

**Environment Variables:**
```bash
DATABASE_URL=postgresql://...           # For thread/message storage
VECTOR_STORE=chroma|pgvector            # For embedding imported messages
OPENAI_API_KEY=sk-...                   # Optional, for embeddings
```

#### Core Loop Definition

**End-to-End Flow:**

1. **User Exports ChatGPT Data** → Downloads `conversations.json` from OpenAI
2. **User Opens Settings** → Navigates to Settings → Data tab
3. **User Clicks "Import from ChatGPT"** → Modal opens
4. **User Selects File** → Chooses `conversations.json`
5. **User Clicks "Upload & Migrate"** → File uploaded to `/upload-chatgpt-export`
6. **Backend Parses JSON** → `ingest_chatgpt_export()` extracts threads and messages
7. **Threads Created** → Each conversation becomes a thread in "Imports" project
8. **Messages Stored** → Messages inserted into `chat_messages` table
9. **Messages Embedded** → Inline embedding to vector store (non-blocking)
10. **Success Response** → Modal shows "Imported 42 threads and 1337 messages"
11. **User Sees Imported Threads** → Threads appear in sidebar under "Imports" project

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|------------|
| **1. Export from ChatGPT** | User manual step | ✅ Documented in guide | None |
| **2. Open Settings** | `SettingsView.tsx` line 383 | ✅ Working | None |
| **3. Click import** | `ChatGPTImportModal` mounted | ✅ Working | None |
| **4. Select file** | File input in modal | ✅ Working | None |
| **5. Upload** | POST to `/upload-chatgpt-export` | 🟡 Works via `rag_upload.py` | Verify which router is active |
| **6. Parse JSON** | `chatgpt_migration.py` line 73 | ✅ Working | None |
| **7. Create threads** | `chatlog_db.create_chat_thread()` | ✅ Working | None |
| **8. Store messages** | `chatlog_db.create_message()` | ✅ Working | None |
| **9. Embed messages** | `_vector_store.add_texts()` | 🟡 Inline embedding, backfill needed for failures | Add backfill trigger |
| **10. Success response** | Modal state update | ✅ Working | None |
| **11. View threads** | Threads in sidebar | 🟡 Requires refresh or event | Add `cfy:threads:refresh` event |

**Critical Issue:**
- **Router Registration:** `guardian/routes/migration.py` is NOT included in `guardian/guardian_api.py` or `guardian/server/app.py`
- **Workaround:** Endpoint likely works via `rag_upload.py` (lines 67-182) which duplicates the functionality
- **Resolution:** Consolidate to single implementation OR register migration router

#### Implementation Tasks

**Milestone 2: Fix Router & Add Progress Tracking**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **MIG-1** | Verify which router serves `/upload-chatgpt-export` | Test both endpoints | S | Running server |
| **MIG-2** | Consolidate migration endpoint (remove duplication) | `guardian/routes/migration.py`, `guardian/routes/rag_upload.py` | M | None |
| **MIG-3** | Register migration router in app.py if not present | `guardian/server/app.py` or `guardian/guardian_api.py` | S | None |
| **MIG-4** | Add progress streaming for large imports | `backend/rag/chatgpt_migration.py` | L | WebSocket or SSE setup |
| **MIG-5** | Add automatic backfill trigger after migration | `backend/rag/chatgpt_migration.py` | M | Embedding worker |
| **MIG-6** | Add thread refresh event after migration success | `frontend/src/components/modals/ChatGPTImportModal.tsx` | S | Event system |
| **MIG-7** | Create E2E test for migration flow | `tests/e2e/test_chatgpt_migration.spec.ts` | M | Playwright |

**Validation Plan:**

**Manual Test Script:**
1. Download sample ChatGPT export (or use `test_chatgpt_export.json`)
2. Open Codexify → Settings → Data tab
3. Click "Import from ChatGPT"
4. Select `conversations.json`
5. Click "Upload & Migrate"
6. Verify: Success message with thread/message counts
7. Navigate to sidebar → "Imports" project
8. Verify: Imported threads appear
9. Open an imported thread
10. Verify: Messages display correctly with timestamps
11. Query vector store: `/api/retrieve` with sample query from import
12. Verify: Imported messages return in search results

**Automated Tests:**
- Unit: `guardian/tests/migration/test_chatgpt_ingest.py` (✅ exists)
- API: Test `/upload-chatgpt-export` endpoint (❌ create)
- E2E: Full flow from Settings → Upload → Verify threads

---

### 2.3 Upload Documents + Embed

#### Current State

**Status:** 🟡 **85% Complete - Working but Missing PDF/DOCX Parsing**

Document upload infrastructure is excellent, but PDF/DOCX text extraction is not implemented.

**What Exists:**

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Upload UI** | `frontend/src/components/documents/DocumentsView.tsx` | ✅ Complete | Drag-drop, file picker, grid view |
| **Document Tile** | `frontend/src/components/documents/DocumentTile.tsx` | ✅ Complete | Visual tiles with color coding |
| **Upload Hook** | `frontend/src/hooks/useUploader.ts` | ✅ Complete | Multi-file, type validation |
| **Upload Endpoint** | `guardian/routes/media.py` POST `/upload/document` | ✅ Complete | Validates, stores, embeds |
| **Storage Manager** | `guardian/core/storage.py` | ✅ Complete | Local/S3/GCS abstraction |
| **Database Model** | `guardian/db/models.py` `UploadedDocument` | ✅ Complete | Metadata tracking with `parsed_text` field |
| **Vector Embedding** | `guardian/runtime/embed/embedder.py` | ✅ Complete | Automatic embedding after upload (lines 356-382 in media.py) |
| **Retrieval Endpoint** | `guardian/retrieve/api.py` POST `/api/retrieve` | ✅ Complete | Semantic search |

**Supported Formats:**
- ✅ **Text files** (.txt) - Text extraction working (lines 338-353 in media.py)
- ✅ **Markdown** (.md) - Text extraction working
- 🔴 **PDF** (.pdf) - Upload works, NO text extraction
- 🔴 **DOCX** (.docx) - Upload works, NO text extraction

**Environment Variables:**
```bash
STORAGE_BACKEND=local|s3|gcs                    # Storage backend
STORAGE_BASE_PATH=/app/media                    # Local storage path
AWS_S3_BUCKET=bucket-name                       # S3 bucket
GCP_BUCKET=bucket-name                          # GCS bucket
CODEXIFY_VECTOR_STORE=chroma|faiss              # Vector store
CODEXIFY_MAX_EMBED_CHARS=16000                  # Max text length for embedding
```

#### Core Loop Definition

**End-to-End Flow:**

1. **User Opens Documents View** → Navigates to Documents gallery
2. **User Uploads Document** → Drag-drop or file picker (PDF, DOCX, MD, TXT)
3. **Frontend Validation** → File type checked against allowed extensions
4. **Upload to Backend** → POST `/api/media/upload/document` with FormData
5. **Backend Validates** → MIME type validation
6. **File Stored** → StorageManager saves to `/media/documents/` (or S3)
7. **Text Extraction** → Parse text content (TXT/MD only currently)
8. **Database Record** → `UploadedDocument` created with metadata
9. **Vector Embedding** → Text embedded via CodexifyEmbedder (non-blocking)
10. **Success Response** → Frontend shows success toast
11. **Document Available in Gallery** → Document tile appears
12. **User Queries in Chat** → "What does the authentication spec say?"
13. **RAG Retrieval** → Vector search finds relevant document chunks
14. **Guardian Responds** → Answer cites uploaded document

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|------------|
| **1. Open Documents** | `DocumentsView.tsx` | ✅ Working | None |
| **2. Upload** | Drag-drop + picker | ✅ Working | None |
| **3. Validation** | Frontend type check | ✅ Working | None |
| **4. Upload to backend** | POST `/upload/document` | ✅ Working | None |
| **5. Backend validates** | MIME type validation | ✅ Working | None |
| **6. File stored** | StorageManager | ✅ Working (local), 🟡 S3/GCS stubbed | Implement S3/GCS if needed |
| **7. Text extraction** | Lines 338-353 in media.py | 🔴 Only TXT/MD, no PDF/DOCX | Add PyPDF2 or pdfplumber for PDF, python-docx for DOCX |
| **8. Database record** | `UploadedDocument` model | ✅ Working | None |
| **9. Embedding** | CodexifyEmbedder (lines 356-382) | 🟡 No chunking, whole doc embedded | Add chunking strategy for long docs |
| **10. Success response** | Toast notification | ✅ Working | None |
| **11. Gallery display** | DocumentsView grid | ✅ Working | None |
| **12. Query in chat** | Chat interface | ✅ Working | None |
| **13. RAG retrieval** | `/api/retrieve` | ✅ Working | Test with real documents |
| **14. Guardian responds** | LLM with context | ✅ Working | None |

#### Implementation Tasks

**Milestone 3: Add PDF/DOCX Parsing & Chunking**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **DOC-1** | Add PDF parsing library (PyPDF2 or pdfplumber) | `requirements.txt`, `guardian/core/parsers.py` | M | PDF library installation |
| **DOC-2** | Add DOCX parsing library (python-docx) | `requirements.txt`, `guardian/core/parsers.py` | M | python-docx installation |
| **DOC-3** | Implement PDF text extraction in upload endpoint | `guardian/routes/media.py` lines 340-350 | M | DOC-1 |
| **DOC-4** | Implement DOCX text extraction | `guardian/routes/media.py` | M | DOC-2 |
| **DOC-5** | Add chunking strategy for long documents (>16k chars) | `guardian/core/chunker.py` | L | None |
| **DOC-6** | Update embedder to handle document chunks | `guardian/runtime/embed/embedder.py` | M | DOC-5 |
| **DOC-7** | Add document parsing tests | `tests/unit/test_document_parsers.py` | M | DOC-1, DOC-2 |
| **DOC-8** | Create E2E test for document upload + retrieval | `tests/e2e/test_document_upload.spec.ts` | M | Playwright |

**Validation Plan:**

**Manual Test Script:**
1. Prepare test documents:
   - `test.txt` with sample content
   - `test.md` with markdown content
   - `test.pdf` with text content
   - `test.docx` with text content
2. Open Codexify → Documents view
3. Drag and drop all 4 files
4. Verify: All files upload successfully
5. Check database: `SELECT * FROM uploaded_documents ORDER BY created_at DESC LIMIT 4`
6. Verify: `parsed_text` column populated for all 4 files (not just TXT/MD)
7. Open chat interface
8. Ask: "What does the test document say about [topic in uploaded file]?"
9. Verify: Guardian's response cites content from uploaded document
10. Check retrieval: POST `/api/retrieve` with query matching document content
11. Verify: Document appears in search results with good relevance score

**Automated Tests:**
- Unit: PDF/DOCX parser functions
- Integration: Upload → Parse → Embed → Retrieve pipeline
- E2E: Full upload and search flow

---

### 2.4 Upload Images to Gallery

#### Current State

**Status:** ✅ **95% Complete - Production Ready**

The image gallery and upload system is nearly complete and production-ready.

**What Exists:**

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Gallery UI** | `frontend/src/components/gallery/GalleryView.tsx` | ✅ Complete | Responsive grid, drag-drop, demo gallery |
| **Preview Tile** | `frontend/src/components/gallery/PreviewTile.tsx` | ✅ Complete | Image tiles with hover effects |
| **Upload Hook** | `frontend/src/hooks/useUploader.ts` | ✅ Complete | Drag-drop, file picker, paste |
| **Upload Endpoint** | `guardian/routes/media.py` POST `/upload/image` | ✅ Complete | Validation, storage, DB tracking |
| **List Endpoint** | `guardian/routes/media.py` GET `/images` | ✅ Complete | Query filtering by project/thread |
| **Delete Endpoint** | `guardian/routes/media.py` DELETE `/images/{id}` | ✅ Complete | Soft delete |
| **Storage Manager** | `guardian/core/storage.py` | ✅ Complete | Local filesystem working, S3/GCS abstraction ready |
| **Database Model** | `guardian/db/models.py` `UploadedImage` | ✅ Complete | Full metadata tracking (id, project_id, thread_id, user_id, src_url, filename, filesize, mime_type, created_at, deleted_at) |

**Supported Formats:** PNG, JPG, JPEG, WebP

**Environment Variables:**
```bash
STORAGE_BACKEND=local|s3|gcs
STORAGE_BASE_PATH=/app/media
STORAGE_URL_PREFIX=/media
AWS_S3_BUCKET=bucket-name
GCP_BUCKET=bucket-name
```

#### Core Loop Definition

**End-to-End Flow:**

1. **User Opens Gallery** → Navigates to Gallery view
2. **User Uploads Image** → Drag-drop, file picker, or paste in chat
3. **Frontend Validation** → File type checked (PNG/JPG/JPEG/WebP)
4. **Upload to Backend** → POST `/api/media/upload/image` with FormData
5. **Backend Validates** → MIME type validation (image/*)
6. **Image Stored** → StorageManager saves to `/media/images/`
7. **Database Record** → `UploadedImage` created with metadata
8. **Success Response** → Frontend shows toast, broadcasts `cfy:gallery:add` event
9. **Gallery Refreshes** → New image appears in grid
10. **User Views Image** → Click to view full-size (if preview modal exists)

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|------------|
| **1. Open Gallery** | `GalleryView.tsx` | ✅ Working | None |
| **2. Upload** | Drag-drop + picker + paste | ✅ Working | None |
| **3. Validation** | Frontend type check | ✅ Working | None |
| **4. Upload to backend** | POST `/upload/image` | ✅ Working | None |
| **5. Backend validates** | MIME type validation | ✅ Working | None |
| **6. Image stored** | StorageManager (local) | ✅ Working, 🟡 S3/GCS stubbed | Implement cloud storage if needed |
| **7. Database record** | `UploadedImage` model | ✅ Working | None |
| **8. Success response** | Toast + event broadcast | ✅ Working | None |
| **9. Gallery refreshes** | Event listener | ✅ Working | None |
| **10. View image** | Click handler | 🟡 No full-size preview modal | Add image preview modal (optional) |

**Minor Gaps:**
- 🟡 Delete button in UI (endpoint exists but no UI button)
- 🟡 Image metadata editing (tags, description)
- 🟡 Image preview/lightbox modal

#### Implementation Tasks

**Milestone 4: Gallery Polish & Cloud Storage**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **IMG-1** | Add delete button to image tiles (context menu or hover) | `frontend/src/components/gallery/PreviewTile.tsx` | S | None |
| **IMG-2** | Add image preview modal (lightbox on click) | `frontend/src/components/modals/ImagePreviewModal.tsx` | M | None |
| **IMG-3** | Implement S3 storage backend | `guardian/core/storage.py` | L | AWS SDK, S3 bucket configured |
| **IMG-4** | Implement GCS storage backend | `guardian/core/storage.py` | L | GCP SDK, GCS bucket configured |
| **IMG-5** | Add image metadata editing endpoint | `guardian/routes/media.py` PATCH `/images/{id}` | M | None |
| **IMG-6** | Create E2E test for image upload flow | `tests/e2e/test_image_upload.spec.ts` | M | Playwright |

**Validation Plan:**

**Manual Test Script:**
1. Open Codexify → Gallery view
2. Drag and drop an image (PNG or JPG)
3. Verify: Image uploads successfully
4. Verify: Success toast appears
5. Verify: Image appears in gallery grid
6. Check database: `SELECT * FROM uploaded_images ORDER BY created_at DESC LIMIT 1`
7. Verify: Record exists with correct metadata (filename, filesize, mime_type, src_url)
8. Check filesystem: Verify image file exists at `src_url` path
9. Refresh page
10. Verify: Image persists in gallery
11. (Optional) Click image to view full-size
12. (Optional) Delete image via context menu

**Automated Tests:**
- E2E: Full upload and display flow
- Integration: Upload → Storage → DB → Retrieval

---

### 2.5 Generate Images

#### Current State

**Status:** ✅ **95% Complete - Production Ready with OpenAI**

Image generation is fully functional with OpenAI DALL-E. Other providers are stubs.

**What Exists:**

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **OpenAI Provider** | `guardian/image_gen/providers/openai.py` | ✅ Complete | DALL-E 3 integration, uses `openai` library |
| **Stability Provider** | `guardian/image_gen/providers/stability.py` | 🔴 Stub | Returns 1x1 placeholder |
| **Local Provider** | `guardian/image_gen/providers/local.py` | 🔴 Stub | Returns 1x1 placeholder |
| **Image Gen Router** | `guardian/image_gen/router.py` | ✅ Complete | Provider resolution, validation |
| **Generation Endpoint** | `guardian/routes/media.py` POST `/generate/image` | ✅ Complete | Full pipeline (lines 216-276) |
| **Database Model** | `guardian/db/models.py` `GeneratedImage` | ✅ Complete | Tracks id, project_id, thread_id, user_id, src_url, prompt, model, created_at |
| **UI Modal** | `frontend/src/components/modals/ImageGenModal.tsx` | ✅ Complete | Prompt input, loading, error handling |
| **Chat Integration** | `frontend/src/features/chat/components/Composer.tsx` | ✅ Complete | ImagePlus button opens modal |
| **Gallery Integration** | `frontend/src/components/gallery/GalleryView.tsx` | ✅ Complete | Event-driven refresh via `cfy:gallery:add` |

**Supported Models:**
- ✅ DALL-E 3 (OpenAI)
- 🔴 Stable Diffusion (Stability AI) - stubbed
- 🔴 Local models - stubbed

**Environment Variables:**
```bash
IMAGE_GEN_PROVIDER=openai|stability|local
IMAGE_GEN_MODEL=dall-e-3
OPENAI_API_KEY=sk-...
```

#### Core Loop Definition

**End-to-End Flow:**

1. **User Opens Chat or Dashboard** → Navigates to interface with image generation
2. **User Clicks "Generate Image"** → ImagePlus button or "Generate" button
3. **Modal Opens** → ImageGenModal with prompt textarea
4. **User Enters Prompt** → "A sunset over mountains, digital art"
5. **User Clicks "Generate"** → POST `/api/media/generate/image` with prompt
6. **Backend Routes to Provider** → ImageGenRouter selects OpenAI provider
7. **Provider Generates Image** → DALL-E 3 API call, returns image bytes
8. **Image Stored** → StorageManager saves to `/media/generated_images/`
9. **Database Record** → `GeneratedImage` created with prompt, model, src_url
10. **Success Response** → Frontend receives src_url
11. **Event Broadcast** → `cfy:gallery:add` event dispatched
12. **Gallery Updates** → New image appears in gallery
13. **Success Toast** → "Image generated successfully"

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|------------|
| **1. Open interface** | Chat/Dashboard | ✅ Working | None |
| **2. Click generate** | ImagePlus button | ✅ Working | None |
| **3. Modal opens** | `ImageGenModal.tsx` | ✅ Working | None |
| **4. Enter prompt** | Textarea input | ✅ Working | None |
| **5. Submit** | POST `/generate/image` | ✅ Working | None |
| **6. Route to provider** | ImageGenRouter | ✅ Working | None |
| **7. Generate** | OpenAI provider | ✅ Working (DALL-E), 🔴 Stubs for others | Implement Stability/Local if needed |
| **8. Store image** | StorageManager | ✅ Working | None |
| **9. Database record** | `GeneratedImage` model | ✅ Working | None |
| **10. Success response** | src_url returned | ✅ Working | None |
| **11. Event broadcast** | `cfy:gallery:add` | ✅ Working | None |
| **12. Gallery updates** | Event listener | ✅ Working | None |
| **13. Toast** | Success message | ✅ Working | None |

**Minor Gaps:**
- 🔴 Stability AI provider not implemented
- 🔴 Local model provider not implemented
- 🟡 No tests for image generation flow

#### Implementation Tasks

**Milestone 5: Image Generation Polish**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **GEN-1** | Implement Stability AI provider (optional) | `guardian/image_gen/providers/stability.py` | L | Stability AI API key |
| **GEN-2** | Implement local image generation (optional) | `guardian/image_gen/providers/local.py` | L | Local SD model setup |
| **GEN-3** | Add tests for image generation endpoint | `tests/unit/test_image_generation.py` | M | None |
| **GEN-4** | Create E2E test for generation flow | `tests/e2e/test_image_generation.spec.ts` | M | Playwright |
| **GEN-5** | Add generation history view in UI | `frontend/src/pages/GenerationHistoryView.tsx` | M | None |
| **GEN-6** | Add regeneration button (same prompt) | `frontend/src/components/modals/ImageGenModal.tsx` | S | None |

**Validation Plan:**

**Manual Test Script:**
1. Ensure `OPENAI_API_KEY` is configured
2. Open Codexify → Chat or Dashboard
3. Click "Generate Image" button (ImagePlus icon)
4. Enter prompt: "A futuristic cityscape at night"
5. Click "Generate"
6. Verify: Loading spinner appears
7. Wait for generation (10-30 seconds)
8. Verify: Success toast appears
9. Navigate to Gallery
10. Verify: Generated image appears with prompt metadata
11. Check database: `SELECT * FROM generated_images ORDER BY created_at DESC LIMIT 1`
12. Verify: Record exists with prompt, model (dall-e-3), src_url
13. Check filesystem: Verify image exists at src_url path
14. Verify: Image is displayable (not corrupted)

**Automated Tests:**
- Unit: Provider API mocking
- Integration: Full generation pipeline
- E2E: UI → API → Storage → Gallery

---

### 2.6 Generate Documents (Code / Literature / Diagrams)

#### Current State

**Status:** 🔴 **40% Complete - Infrastructure Ready, Feature Missing**

Document infrastructure is excellent, but AI-driven document generation is NOT implemented.

**What Exists:**

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Database Model** | `guardian/db/models.py` `GeneratedDocument` | ✅ Complete | Schema supports id, project_id, thread_id, user_id, title, content, format, model, created_at, deleted_at |
| **Upload Endpoint** | `guardian/routes/media.py` POST `/upload/document` | ✅ Complete | User document uploads working |
| **Autosave Endpoint** | `guardian/routes/documents.py` POST `/autosave` | ✅ Complete | Note autosaving working |
| **Thread-Document Linking** | `guardian/db/models.py` `ThreadDocument` | ✅ Complete | Junction table for relations (autosave, attached, reference) |
| **Document List Endpoint** | `guardian/routes/documents.py` GET `/threads/{id}/documents` | ✅ Complete | Query linked documents |
| **Collaborative Editor** | `frontend/src/components/editor/CollaborativeNote.tsx` | ✅ Complete | Real-time editing with WebSocket |
| **Documents View** | `frontend/src/components/documents/DocumentsView.tsx` | ✅ Complete | Gallery view for documents |
| **Storage Manager** | `guardian/core/storage.py` | ✅ Complete | File storage abstraction |

**What's Missing:**

| Missing Component | Description | Impact |
|-------------------|-------------|--------|
| **Document Generation UI** | Modal or dialog to trigger AI document generation | 🔴 Critical - No way to request generation |
| **Generation Endpoint** | POST `/api/documents/generate` | 🔴 Critical - No backend logic for generation |
| **Document Templates** | Templates for reports, summaries, code, diagrams | 🟡 Optional - Can start with free-form |
| **LLM Integration** | Connect generation to OpenAI/Groq for content creation | 🔴 Critical - Core generation logic |
| **Format Support** | Handle different output formats (MD, HTML, PDF, DOCX) | 🟡 Optional - Start with MD/TXT |

#### Core Loop Definition (Desired)

**End-to-End Flow (NOT IMPLEMENTED):**

1. **User Opens Workspace or Chat** → Navigates to interface
2. **User Clicks "Generate Document"** → Button or menu option
3. **Modal Opens** → DocumentGenModal with prompt and type selection
4. **User Selects Type** → Code, Summary, Report, Diagram spec, etc.
5. **User Enters Prompt** → "Generate a Python class for user authentication"
6. **User Clicks "Generate"** → POST `/api/documents/generate` with prompt + type
7. **Backend Routes to LLM** → OpenAI or Groq API call
8. **LLM Generates Content** → Returns text content
9. **Document Stored** → `GeneratedDocument` created in DB
10. **Thread Linkage** → `ThreadDocument` links document to thread
11. **Success Response** → Frontend receives document ID and content
12. **Document Opens** → Editor or viewer opens with generated content
13. **User Edits/Saves** → Can edit and save via autosave endpoint

**Current Reality:**
- ❌ Steps 2-12 NOT implemented
- ✅ Step 13 (editing/saving) works via autosave

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|------------|
| **1. Open interface** | Workspace/Chat exists | ✅ Working | None |
| **2. Click generate** | ❌ No button/menu option | 🔴 Missing UI trigger | Create DocumentGenModal + button |
| **3. Modal opens** | ❌ No modal component | 🔴 Missing component | Create `DocumentGenModal.tsx` |
| **4. Select type** | ❌ No type selection | 🔴 Missing UX | Add dropdown/radio for doc type |
| **5. Enter prompt** | ❌ No prompt input | 🔴 Missing input | Add textarea for prompt |
| **6. Submit** | ❌ No endpoint | 🔴 Missing API | Create POST `/api/documents/generate` |
| **7. Route to LLM** | Guardian has LLM clients | 🟡 Exists but not wired | Wire existing LLM client to endpoint |
| **8. Generate content** | LLM integration exists | 🟡 Exists but not used for doc gen | Create prompt templates |
| **9. Store document** | `GeneratedDocument` model | ✅ Schema exists | Use existing model |
| **10. Link to thread** | `ThreadDocument` model | ✅ Schema exists | Use existing model |
| **11. Response** | Standard JSON response | ✅ Pattern exists | Follow existing pattern |
| **12. Open document** | Collaborative editor exists | 🟡 Exists but not triggered | Add navigation to editor |
| **13. Edit/save** | Autosave working | ✅ Working | None |

#### Implementation Tasks

**Milestone 6: Implement Document Generation**

| Task | Description | Files | Complexity | Dependencies |
|------|-------------|-------|------------|--------------|
| **DOCGEN-1** | Create DocumentGenModal component | `frontend/src/components/modals/DocumentGenModal.tsx` | M | None |
| **DOCGEN-2** | Add "Generate Document" button to Workspace | `frontend/src/components/workspace/*` | S | DOCGEN-1 |
| **DOCGEN-3** | Create document generation endpoint | `guardian/routes/documents.py` POST `/api/documents/generate` | L | LLM client |
| **DOCGEN-4** | Create document generation service | `guardian/services/document_generator.py` | L | OpenAI/Groq client |
| **DOCGEN-5** | Add prompt templates for different doc types | `guardian/prompts/document_templates.py` | M | None |
| **DOCGEN-6** | Wire generation endpoint to store in GeneratedDocument | `guardian/routes/documents.py` | M | DOCGEN-3 |
| **DOCGEN-7** | Add navigation to editor after generation | `frontend/src/components/modals/DocumentGenModal.tsx` | S | DOCGEN-1 |
| **DOCGEN-8** | Add tests for document generation | `tests/unit/test_document_generation.py` | M | DOCGEN-3, DOCGEN-4 |
| **DOCGEN-9** | Create E2E test for generation flow | `tests/e2e/test_document_generation.spec.ts` | M | Playwright, DOCGEN-1-7 |

**Validation Plan:**

**Manual Test Script (After Implementation):**
1. Open Codexify → Workspace or Chat
2. Click "Generate Document" button
3. Modal opens with:
   - Document type dropdown (Code, Summary, Report, Spec)
   - Prompt textarea
   - Generate button
4. Select type: "Code"
5. Enter prompt: "Create a Python class for user authentication with email and password"
6. Click "Generate"
7. Verify: Loading spinner appears
8. Wait for generation (5-20 seconds)
9. Verify: Success toast appears
10. Verify: Document editor opens with generated code
11. Check database: `SELECT * FROM generated_documents ORDER BY created_at DESC LIMIT 1`
12. Verify: Record exists with title, content, format, model
13. Verify: `ThreadDocument` link created
14. Edit generated content in editor
15. Verify: Autosave triggers after typing
16. Refresh page
17. Verify: Edited content persists

**Automated Tests:**
- Unit: Document generator service logic
- Integration: Generation → Storage → Linking
- E2E: Full UI flow

---

## 3. Milestones & Timeline

### Milestone 0: Foundation & Blockers (Week 1)

**Goal:** Fix critical wiring issues and ensure infrastructure is stable

**Tasks:**
- Verify vector store (ChromaDB/PGVector) is running and healthy
- Verify database (PostgreSQL) is running with all tables
- Fix ChatGPT migration router registration issue (MIG-1, MIG-2, MIG-3)
- Add health check endpoints for critical services
- Document environment variable requirements
- Create sample test data for each feature

**Success Criteria:**
- All services start without errors
- Health checks pass for vector store, DB, storage
- ChatGPT migration endpoint accessible and working
- Test data loaded successfully

---

### Milestone 1: Close RAG + Guardian Chat Loop (Week 2)

**Goal:** Memory/RAG system fully operational end-to-end

**Tasks:**
- RAG-1: Create integration test for RAG retrieval
- RAG-2: Document chat API conventions
- RAG-3: Add embedding feedback in UI
- RAG-4: Test MemoryOS tier transitions
- RAG-5: Verify Context Broker depth modes
- RAG-6: Add vector store health endpoint

**Success Criteria:**
- User can ask question, system retrieves relevant memories, Guardian responds
- Embeddings confirmed via UI feedback
- Context Broker tested with all depth modes
- Manual test script passes 100%

---

### Milestone 2: Close ChatGPT Migration Loop (Week 2-3)

**Goal:** ChatGPT import working reliably

**Tasks:**
- MIG-1 through MIG-7 (router fix, progress tracking, events, tests)

**Success Criteria:**
- User can upload conversations.json and see imported threads
- Threads appear in sidebar immediately (or after refresh)
- Imported messages are searchable via RAG
- Manual test script passes 100%

---

### Milestone 3: Close Document Upload + RAG Loop (Week 3-4)

**Goal:** Document upload working for all file types with RAG retrieval

**Tasks:**
- DOC-1 through DOC-8 (PDF/DOCX parsing, chunking, tests)

**Success Criteria:**
- User can upload PDF/DOCX and retrieve content via chat
- Parsed text confirmed in database
- Document chunks searchable via RAG
- Manual test script passes 100%

---

### Milestone 4: Close Image Gallery Loop (Week 4)

**Goal:** Image upload and gallery fully polished

**Tasks:**
- IMG-1 through IMG-6 (delete UI, preview modal, cloud storage, tests)

**Success Criteria:**
- User can upload, view, delete images
- Gallery updates in real-time
- Cloud storage working (if S3/GCS needed)
- Manual test script passes 100%

---

### Milestone 5: Close Image Generation Loop (Week 4-5)

**Goal:** Image generation working with provider of choice

**Tasks:**
- GEN-1 through GEN-6 (providers, tests, history view)

**Success Criteria:**
- User can generate images via chat or dashboard
- Generated images appear in gallery
- Generation history viewable
- Manual test script passes 100%

---

### Milestone 6: Close Document Generation Loop (Week 5-6)

**Goal:** Document generation working end-to-end

**Tasks:**
- DOCGEN-1 through DOCGEN-9 (modal, endpoint, service, tests)

**Success Criteria:**
- User can generate code/summaries/reports via prompt
- Generated documents open in editor
- Content persists and is editable
- Manual test script passes 100%

---

### Estimated Timeline: 5-6 Weeks

**Assumptions:**
- Single developer, full-time
- No major infrastructure issues
- LLM APIs (OpenAI/Groq) available and working
- Database and vector store setup completed in Milestone 0

**Risk Buffer:** Add 1-2 weeks for unexpected issues

---

## 4. Risks, Assumptions & Dependencies

### 4.1 Critical Dependencies

**Infrastructure:**
- PostgreSQL database running with migrations applied
- ChromaDB or PGVector running for vector storage
- Storage backend configured (local filesystem or S3/GCS)
- LLM API keys (OpenAI or Groq) for chat and generation

**Third-Party Services:**
- OpenAI API for embeddings and image generation
- Optional: Stability AI for image generation
- Optional: Neo4j for graph context

**Environment Configuration:**
```bash
# Core Services
DATABASE_URL=postgresql://user:pass@localhost:5432/codexify
VECTOR_STORE=pgvector|chroma
CODEXIFY_CHROMA_PATH=./.chroma

# Embeddings
OPENAI_API_KEY=sk-...
LOCAL_EMBED_MODEL=bge-large-en-v1.5

# Storage
STORAGE_BACKEND=local
STORAGE_BASE_PATH=/app/media

# Image Generation
IMAGE_GEN_PROVIDER=openai
IMAGE_GEN_MODEL=dall-e-3

# Optional
GUARDIAN_ENABLE_GRAPH_CONTEXT=False
```

### 4.2 Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Vector store performance issues** | Medium | High | Test with realistic data volumes early; switch to PGVector if ChromaDB slow |
| **LLM API rate limits** | Medium | Medium | Implement exponential backoff; add local model fallback |
| **PDF parsing library errors** | Medium | Medium | Test with diverse PDF formats; add error handling and user feedback |
| **S3/GCS storage costs** | Low | Medium | Start with local storage; only implement cloud if needed |
| **Document chunking complexity** | High | Medium | Start with simple fixed-size chunking; iterate later |
| **Integration test flakiness** | High | Low | Use deterministic test data; mock external APIs |
| **Frontend state management bugs** | Medium | Medium | Add comprehensive E2E tests; use React DevTools |

### 4.3 Assumptions

1. **Single User MVP:** Authentication and multi-user features deferred to post-MVP
2. **Local Deployment:** Assumes local Docker or development environment; cloud deployment deferred
3. **English Language Only:** No i18n/l10n for MVP
4. **Desktop UI:** Mobile responsive design deferred
5. **Basic Error Handling:** Advanced retry logic and failure recovery deferred
6. **No Performance Optimization:** Assume small data volumes; optimization deferred
7. **Limited Testing:** Unit + integration tests for core paths; exhaustive coverage deferred

### 4.4 Technical Debt to Address Post-MVP

- Implement repository pattern for database access (currently direct queries in routes)
- Add service layer for business logic (currently mixed in routes)
- Implement comprehensive error handling and user feedback
- Add request throttling and rate limiting
- Implement proper authentication and authorization
- Add comprehensive logging and monitoring
- Implement backup and disaster recovery
- Add performance profiling and optimization
- Implement proper version control for documents
- Add comprehensive API documentation (OpenAPI/Swagger)

---

## 5. Deferred Features (Post-MVP Parking Lot)

### 5.1 Phase 1.1 (Post-MVP, Pre-Production)

**Authentication & Security:**
- User authentication (OAuth, email/password)
- API key management UI
- Role-based access control (RBAC)
- Audit logging

**Collaboration:**
- Multi-user support
- Real-time collaborative editing for all document types
- User presence indicators
- Comment threads on documents

**Search & Discovery:**
- Full-text search across all content
- Advanced filtering (by date, type, project, tags)
- Search suggestions and autocomplete
- Saved searches

### 5.2 Phase 1.2 (Production Hardening)

**Performance:**
- Database query optimization
- Vector store indexing optimization
- CDN for static assets
- Response caching

**Reliability:**
- Retry logic for failed operations
- Background job queue for async tasks
- Dead letter queue for failed jobs
- Circuit breakers for external APIs

**Monitoring:**
- Application metrics (Prometheus)
- Error tracking (Sentry)
- Usage analytics
- Cost tracking

### 5.3 Phase 2.0 (Advanced Features)

**Federation & Sync:**
- Federated context search (mentioned in Context Broker)
- Peer-to-peer sync
- Offline mode with sync
- Conflict resolution

**Graph & Knowledge:**
- Neo4j graph context (currently optional)
- Knowledge graph visualization
- Relationship discovery
- Concept clustering

**Plugins & Extensions:**
- Plugin SDK (partially documented)
- Plugin marketplace
- Custom agent types
- Webhook integrations

**AI Features:**
- Agent orchestration (multi-agent workflows)
- Code execution sandbox
- Tool use / function calling
- Custom fine-tuned models

### 5.4 Nice-to-Have (Future Exploration)

- Mobile app (iOS, Android)
- Desktop app (Electron)
- Browser extension
- Voice interface
- Video processing
- Diagram rendering (Mermaid, PlantUML)
- LaTeX support
- Spreadsheet integration
- Calendar integration
- Email integration

---

## Appendix A: Quick Reference

### A.1 Core Files by Feature

**Memory / RAG:**
- `guardian/context/broker.py` - Context assembly
- `guardian/memoryos/retriever.py` - Semantic search
- `backend/vector_store/chroma_store.py` - Vector storage
- `guardian/routes/memory.py` - Memory API

**ChatGPT Migration:**
- `backend/rag/chatgpt_migration.py` - Ingestion logic
- `guardian/routes/migration.py` - Migration API (check registration)
- `frontend/src/components/modals/ChatGPTImportModal.tsx` - UI

**Document Upload:**
- `guardian/routes/media.py` - Upload endpoints
- `frontend/src/components/documents/DocumentsView.tsx` - UI
- `guardian/core/storage.py` - Storage abstraction

**Image Gallery:**
- `frontend/src/components/gallery/GalleryView.tsx` - Gallery UI
- `guardian/routes/media.py` - Image endpoints

**Image Generation:**
- `guardian/image_gen/providers/openai.py` - DALL-E provider
- `frontend/src/components/modals/ImageGenModal.tsx` - Generation UI

**Document Generation:**
- `guardian/db/models.py` - GeneratedDocument model
- `guardian/routes/documents.py` - Document API
- (Missing: generation endpoint and UI)

### A.2 Environment Variables Checklist

```bash
# Database
DATABASE_URL=postgresql://localhost:5432/codexify

# Vector Store
VECTOR_STORE=pgvector
CODEXIFY_VECTOR_STORE=chroma
CODEXIFY_CHROMA_PATH=./.chroma

# Embeddings
OPENAI_API_KEY=sk-...
LOCAL_EMBED_MODEL=bge-large-en-v1.5
CODEXIFY_USE_OPENAI=1

# Storage
STORAGE_BACKEND=local
STORAGE_BASE_PATH=/app/media

# Image Generation
IMAGE_GEN_PROVIDER=openai
IMAGE_GEN_MODEL=dall-e-3

# Optional
GUARDIAN_ENABLE_GRAPH_CONTEXT=False
MEMORY_RETENTION_DAYS=90
```

### A.3 Testing Commands

```bash
# Unit tests
pytest guardian/tests/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests (Playwright)
cd frontend/src
pnpm playwright test

# Specific test file
pytest guardian/tests/migration/test_chatgpt_ingest.py -v

# With coverage
pytest --cov=guardian --cov-report=html
```

### A.4 Manual Test Data

**Sample ChatGPT Export (test_chatgpt_export.json):**
```json
[
  {
    "title": "Test Conversation",
    "mapping": {
      "msg1": {
        "message": {
          "author": {"role": "user"},
          "content": {"parts": ["Hello, this is a test"]},
          "create_time": 1672531200
        }
      },
      "msg2": {
        "message": {
          "author": {"role": "assistant"},
          "content": {"parts": ["Hi! How can I help?"]},
          "create_time": 1672531260
        }
      }
    }
  }
]
```

**Sample Document (test.md):**
```markdown
# Test Document

This is a test document for upload and RAG retrieval.

## Section 1
Content about authentication systems.

## Section 2
Content about authorization flows.
```

---

## Appendix B: Database Schema Reference

**Key Tables:**

```sql
-- Memory / RAG
CREATE TABLE chat_threads (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    created_at TIMESTAMP
);

CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER REFERENCES chat_threads(id),
    role TEXT,
    content TEXT,
    created_at TIMESTAMP
);

-- Documents
CREATE TABLE uploaded_documents (
    id UUID PRIMARY KEY,
    project_id INTEGER,
    thread_id INTEGER,
    user_id TEXT,
    filename TEXT,
    filesize BIGINT,
    mime_type TEXT,
    src_url TEXT,
    parsed_text TEXT,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE generated_documents (
    id UUID PRIMARY KEY,
    project_id INTEGER,
    thread_id INTEGER,
    user_id TEXT,
    title TEXT,
    content TEXT,
    format TEXT,
    model TEXT,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE thread_documents (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER REFERENCES chat_threads(id),
    document_id UUID,
    relation TEXT,
    created_at TIMESTAMP
);

-- Images
CREATE TABLE uploaded_images (
    id UUID PRIMARY KEY,
    project_id INTEGER,
    thread_id INTEGER,
    user_id TEXT,
    src_url TEXT,
    filename TEXT,
    filesize BIGINT,
    mime_type TEXT,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE generated_images (
    id UUID PRIMARY KEY,
    project_id INTEGER,
    thread_id INTEGER,
    user_id TEXT,
    src_url TEXT,
    prompt TEXT,
    model TEXT,
    created_at TIMESTAMP,
    deleted_at TIMESTAMP
);
```

---

## Appendix C: API Endpoint Reference

**Memory / RAG:**
- `POST /api/chat/send` - Send chat message
- `POST /api/retrieve` - Vector search
- `GET /health/vector` - Vector store health

**ChatGPT Migration:**
- `POST /upload-chatgpt-export` - Import ChatGPT data

**Documents:**
- `POST /api/media/upload/document` - Upload document
- `POST /api/documents/autosave` - Autosave document
- `GET /api/threads/{id}/documents` - List thread documents
- (Missing) `POST /api/documents/generate` - Generate document

**Images:**
- `POST /api/media/upload/image` - Upload image
- `GET /api/media/images` - List images
- `DELETE /api/media/images/{id}` - Delete image
- `POST /api/media/generate/image` - Generate image

**Workspace:**
- `GET /api/workspace/{thread_id}` - Get thread workspace data

---

**End of Document**
