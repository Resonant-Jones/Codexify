# Codexify MVP Roadmap & Core Loop Plan

**Date**: 2026-01-23
**Repository**: Codexify
**Branch**: `busy-sinoussi`
**Commit**: `e954ee3724f1a64aca5e5804dd86eafc13c8efa7`

---

## 1. Overview & Goals

### Purpose

This document provides a **brutally pragmatic implementation plan** to close the 6 core feature loops for Codexify MVP. It maps each feature to the actual codebase, defines end-to-end user flows, identifies gaps, and provides concrete next steps.

### Scope: MVP Core Features Only

1. **Memory / RAG System + Context Broker for Chat with Guardian**
2. **ChatGPT Migration Tool**
3. **Upload Documents + Embed**
4. **Upload Images to Gallery**
5. **Generate Images**
6. **Generate Documents (code, literature, diagrams, etc.)**

Everything outside these 6 features is explicitly **deferred to post-MVP**.

---

## 2. Core MVP Features

### 2.1 Memory / RAG + Context Broker + Guardian Chat

#### Current State

**STATUS**: 🟡 **Partially Implemented** - Core infrastructure exists but context injection needs wiring verification

**Key Components Found**:

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **ContextBroker** | `guardian/context/broker.py` | ✅ Implemented | Assembles context bundles with 4 depth modes (shallow/normal/deep/diagnostic) |
| **VectorStore** | `guardian/vector/store.py` | ✅ Implemented | Wraps embedder + storage backend (ChromaDB/PGVector/FAISS) |
| **Embedder** | `backend/rag/embedder.py:103-371` | ✅ Implemented | SentenceTransformers-based, local-only embeddings |
| **MemoryOSRetriever** | `guardian/memoryos/retriever.py` | ✅ Implemented | RAG-based memory search |
| **Chat Route** | `guardian/routes/chat.py` | ✅ Implemented | POST `/api/chat/{thread_id}/complete` with depth parameter |
| **GuardianChat UI** | `frontend/src/features/chat/GuardianChat.tsx` | ✅ Implemented | Depth selector (shallow/normal/deep/diagnostic), trace capture |
| **Auto-embedding** | `guardian/routes/chat.py:142-161` | ✅ Implemented | Messages auto-embedded to vector store via `_embed_message()` |

**How It Works Today**:

1. **Context Assembly** (`guardian/context/broker.py:56-94`):
   - `assemble()` method fetches recent messages, semantic results, memory, graph, sensors based on depth mode
   - Returns `(context, rag_trace)` tuple

2. **Chat Completion** (`guardian/routes/chat.py`):
   - POST `/api/chat/{thread_id}/complete` accepts `depth_mode` query param
   - Creates ContextBroker with chatlog, vector store, memory store, sensors
   - Calls `broker.assemble(thread_id, query, depth_mode=depth)`
   - Passes assembled context to LLM via `chat_with_ai()`
   - Auto-embeds new assistant message via `_embed_message()`

3. **Frontend** (`frontend/src/features/chat/GuardianChat.tsx:105-135`):
   - Depth selector UI component (4 modes)
   - Calls `/api/chat/${tid}/complete` with `depth_mode: depth`
   - Captures RAG trace from response for diagnostics

#### Core Loop Definition

**End-to-End User Story**:
> User opens Guardian chat, selects "deep" context mode, asks "What did I discuss about vector databases?", system retrieves relevant memories from past conversations, Guardian responds with specific references to prior discussions.

**Core Loop Steps**:

1. **[UI]** User opens Guardian chat interface → `GuardianChat.tsx` loads
2. **[UI]** User selects depth mode (shallow/normal/deep/diagnostic) → `setDepth()` called
3. **[UI]** User types message and sends → `POST /api/chat/{thread_id}/messages` (creates user message)
4. **[UI]** System triggers completion → `POST /api/chat/{thread_id}/complete?depth_mode={depth}`
5. **[Backend]** Chat route receives request → `guardian/routes/chat.py:post_complete_thread()`
6. **[Backend]** Creates ContextBroker with all stores → `ContextBroker(chatlog, vector, memory, sensors)`
7. **[Backend]** Assembles context → `broker.assemble(thread_id, query, depth_mode=depth)`
   - Fetches recent messages from thread
   - Performs semantic search via VectorStore
   - Queries memory store (deep/diagnostic only)
   - Optionally fetches graph context (if enabled)
   - Optionally fetches sensor snapshot (diagnostic only)
8. **[Backend]** Passes context to LLM → `chat_with_ai(messages_with_context, model, provider)`
9. **[Backend]** Streams assistant response → Returns via SSE or JSON
10. **[Backend]** Auto-embeds assistant message → `_embed_message(thread_id, "assistant", content, message_id)`
11. **[UI]** Receives response and displays → ChatView updates
12. **[UI]** Captures RAG trace for diagnostics → `setTrace({semantic, memory, depth, threadId})`

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix Needed |
|-----------|----------------------|---------------|---------------------|
| Step 1-3 | ✅ Working | None | - |
| Step 4 | ✅ POST endpoint exists | None | - |
| Step 5-6 | ✅ ContextBroker creation | Verify chatlog_db, vector_store are actually passed | **Test end-to-end** with real query |
| Step 7 | 🟡 Partial | Graph context gated by `GUARDIAN_ENABLE_GRAPH_CONTEXT` flag (default: false) | **Decision**: Enable graph or remove from depth modes |
| Step 7 | 🟡 Partial | Memory store passed but unclear if wired correctly | **Verify** memory store initialization in `guardian/core/dependencies.py` |
| Step 8 | ✅ Working | None | - |
| Step 9 | ✅ Working | Streaming via SSE implemented | - |
| Step 10 | 🟡 Partial | Auto-embed is synchronous, may block | **Low priority** - works but consider async |
| Step 11-12 | ✅ Working | None | - |

**Critical Gaps**:

1. **Graph context disabled by default** - Neo4j integration is scaffolding only (`guardian/db/neo.py` has schema but minimal usage)
2. **Memory store wiring unclear** - Need to verify `_memory_store` in `guardian/core/dependencies.py` is actually initialized
3. **No end-to-end test** - Core loop needs integration test to verify context actually reaches LLM

#### Implementation Tasks

| ID | Task | Files | Complexity | Priority |
|----|------|-------|------------|----------|
| M1.1 | **Verify memory store initialization** | `guardian/core/dependencies.py`, `guardian/memory/memoryos.py` | S | HIGH |
| M1.2 | **Add integration test for context assembly** | `guardian/tests/test_context_broker_e2e.py` (new) | M | HIGH |
| M1.3 | **Decision on graph context** | - | S | HIGH |
| M1.3a | *If keep*: Wire Neo4j into chat pipeline with backfill | `guardian/routes/chat.py`, `guardian/workers/graph_backfill_worker.py` | L | MED |
| M1.3b | *If defer*: Remove "graph" from context and disable in ContextBroker | `guardian/context/broker.py:123-134` | S | MED |
| M1.4 | **Make auto-embed async** | `guardian/routes/chat.py:142-161` | M | LOW |
| M1.5 | **Add "context preview" UI** | `frontend/src/features/chat/components/ContextPreview.tsx` (new) | M | MED |

#### Validation Plan

**Manual Test Script**:

```bash
# 1. Start stack
docker-compose up -d
 
# 2. Open UI at http://localhost:5173
# 3. Navigate to Guardian chat
# 4. Select "deep" depth mode
# 5. Send message: "Tell me about vector databases"
# 6. Verify:
#    - Response references previous conversations (if any)
#    - RAG trace shows semantic results
#    - No errors in browser console or backend logs
 
# 7. Check backend logs for context assembly:
docker-compose logs backend | grep -i "context"
```

**Automated Tests**:

1. **Unit test** - `guardian/tests/test_context_broker.py`:
   - Verify `assemble()` returns correct context structure for each depth mode
   - Mock chatlog_db, vector_store, memory_store

2. **Integration test** - `guardian/tests/test_chat_completion_e2e.py` (new):
   - Create thread, add messages
   - Embed test data into vector store
   - Call `/api/chat/{thread_id}/complete` with depth="deep"
   - Verify response includes retrieved context
   - Check message was auto-embedded

---

### 2.2 ChatGPT Migration Tool

#### Current State

**STATUS**: ✅ **Loop Closed** - Fully working end-to-end

**Key Components Found**:

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Migration UI** | `frontend/src/components/modals/ChatGPTImportModal.tsx` | ✅ Implemented | File picker, upload, progress, success/error states |
| **Backend Route** | `guardian/routes/rag_upload.py:67-182` | ✅ Implemented | POST `/upload-chatgpt-export` with validation |
| **Migration Logic** | `backend/rag/chatgpt_migration.py:42-100+` | ✅ Implemented | Parses JSON, creates threads, embeds messages |
| **Event Emission** | `ChatGPTImportModal.tsx:81-88` | ✅ Implemented | Emits `cfy:threads:refresh` event on success |

**How It Works Today**:

1. User clicks "Import from ChatGPT" in settings
2. `ChatGPTImportModal` opens with file picker
3. User selects `conversations.json` from ChatGPT export
4. Frontend POSTs to `/upload-chatgpt-export` with:
   - `FormData` containing file
   - `X-User-Id` header with user identity
5. Backend validates JSON structure (must be array of conversations)
6. Backend iterates conversations:
   - Creates `ChatThread` with title from export
   - Associates with "Imports" project (creates if missing)
   - Creates `ChatMessage` for each message in thread
   - Embeds messages into vector store via `VectorStore.add_texts()`
7. Returns stats: `{threads_imported: N, messages_imported: M}`
8. Frontend displays success with stats
9. Frontend emits `cfy:threads:refresh` event to update thread list

#### Core Loop Definition

**End-to-End User Story**:
> User exports ChatGPT history as JSON, opens Codexify settings, clicks "Import from ChatGPT", selects file, sees progress indicator, gets confirmation with import stats, navigates to threads and sees imported conversations.

**Core Loop Steps**:

1. **[User]** Export ChatGPT conversations → `conversations.json` file
2. **[UI]** Open Codexify settings → Settings panel loads
3. **[UI]** Click "Import from ChatGPT" → `ChatGPTImportModal` opens
4. **[UI]** Click "Choose File" and select JSON → File name appears
5. **[UI]** Click "Upload & Migrate" → Status changes to "uploading"
6. **[Backend]** Receive POST `/upload-chatgpt-export` → Validate content type
7. **[Backend]** Parse JSON → Extract conversations array
8. **[Backend]** For each conversation:
   - Ensure "Imports" project exists
   - Create thread with title
   - Create messages with role/content
   - Embed each message into vector store
9. **[Backend]** Return stats → `{threads_imported, messages_imported}`
10. **[UI]** Display success message → Show stats
11. **[UI]** Emit refresh event → Thread list updates
12. **[User]** Navigate to threads → See imported conversations

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix Needed |
|-----------|----------------------|---------------|---------------------|
| All steps | ✅ Fully working | None | - |

**No critical gaps** - This feature is complete and ready to use.

**Minor Enhancements (Post-MVP)**:

- Progress bar during large imports
- Duplicate detection (skip already-imported threads)
- Preview mode (show what will be imported before committing)

#### Implementation Tasks

| ID | Task | Files | Complexity | Priority |
|----|------|-------|------------|----------|
| M2.1 | **Add integration test** | `guardian/tests/test_chatgpt_migration_e2e.py` (new) | M | MED |
| M2.2 | **Add error handling for malformed JSON** | `backend/rag/chatgpt_migration.py:73-78` | S | LOW |

#### Validation Plan

**Manual Test Script**:

```bash
# 1. Obtain ChatGPT export (or use test fixture)
cp tests/fixtures/sample_chatgpt_export.json /tmp/test_export.json
 
# 2. Start Codexify
docker-compose up -d
 
# 3. Open UI at http://localhost:5173
# 4. Navigate to Settings
# 5. Click "Import from ChatGPT"
# 6. Select /tmp/test_export.json
# 7. Click "Upload & Migrate"
# 8. Verify:
#    - Progress indicator appears
#    - Success message shows correct stats
#    - Thread list refreshes automatically
#    - Imported threads appear in sidebar
 
# 9. Open an imported thread and verify:
#    - Messages load correctly
#    - Timestamps are preserved
#    - Ask a question about imported content
#    - Verify Guardian can reference imported conversations
```

**Automated Tests**:

1. **Unit test** - `guardian/tests/test_chatgpt_migration.py`:
   - Test `ingest_chatgpt_export()` with valid JSON
   - Test error handling for invalid JSON
   - Verify thread/message counts

2. **Integration test** - `guardian/tests/test_chatgpt_migration_e2e.py` (new):
   - POST sample export to `/upload-chatgpt-export`
   - Verify threads created in database
   - Verify messages embedded in vector store
   - Query vector store to confirm retrieval works

---

### 2.3 Upload Documents + Embed

#### Current State

**STATUS**: 🟡 **Partially Implemented** - Upload works, embedding is best-effort, no UI confirmation

**Key Components Found**:

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Upload Hook** | `frontend/src/hooks/useUploader.ts:15-150` | ✅ Implemented | Handles file selection, validation, upload |
| **DocumentsView** | `frontend/src/components/documents/DocumentsView.tsx` | ✅ Implemented | Drag & drop zone, document grid display |
| **Upload Endpoint** | `guardian/routes/media.py` (inferred from useUploader) | ✅ Implemented | POST `/api/media/upload/document` |
| **Document Parsing** | `guardian/services/document_parsers.py:extract_pdf_text, extract_docx_text` | ✅ Implemented | Extracts text from PDF/DOCX |
| **Document Chunking** | `guardian/services/document_chunking.py:chunk_document_text` | ✅ Implemented | Splits text into chunks |
| **Best-Effort Embed** | `frontend/src/hooks/useUploader.ts:134-137` | 🟡 Partial | Calls `/api/embeddings` but ignores failures |
| **Database Models** | `guardian/db/models.py:UploadedDocument` | ✅ Implemented | Stores document metadata + parsed_text |

**How It Works Today**:

1. User drags document into DocumentsView or clicks upload button
2. `useUploader` hook validates file extension (`.pdf`, `.docx`, `.md`, `.txt`)
3. For documents:
   - Creates FormData with file, project_id, thread_id
   - POSTs to `/api/media/upload/document`
   - Backend extracts text (for PDF/DOCX) or reads directly (MD/TXT)
   - Backend stores in `UploadedDocument` table with parsed_text
   - Returns document metadata
4. Frontend makes **best-effort** call to `/api/embeddings` with parsed text
   - **Ignores failures** - no retry, no error shown to user
5. Document appears in DocumentsView grid

#### Core Loop Definition

**End-to-End User Story**:
> User drags a PDF research paper into Documents view, sees upload progress, document appears in grid, user asks Guardian "What are the key findings from the paper I just uploaded?", Guardian responds with specific references from the PDF.

**Core Loop Steps**:

1. **[UI]** User drags/selects document → `useUploader.handleFiles()` called
2. **[UI]** Validate file extension → Must be .pdf, .docx, .md, .txt
3. **[UI]** Create FormData and POST → `/api/media/upload/document`
4. **[Backend]** Receive upload → `guardian/routes/media.py:upload_document()`
5. **[Backend]** Extract text:
   - PDF: `extract_pdf_text()` via PyPDF2
   - DOCX: `extract_docx_text()` via python-docx
   - MD/TXT: Read directly
6. **[Backend]** Store in database → `UploadedDocument` with parsed_text, metadata
7. **[Backend]** Return document metadata → `{id, src_url, filename, parsed_text, ...}`
8. **[UI]** Receive response → Display document in grid
9. **[UI]** Best-effort embed call → POST `/api/embeddings` with `{texts: [preview]}`
   - **CRITICAL GAP**: No retry, no confirmation, no error handling
10. **[Backend]** Embed endpoint receives request → `guardian/routes/?` (endpoint unclear)
11. **[Backend]** Generate embeddings → Via SentenceTransformers
12. **[Backend]** Store in vector store → ChromaDB/PGVector with metadata
13. **[User]** Open Guardian chat → Ask question about uploaded document
14. **[System]** Semantic search retrieves document chunks → Context passed to LLM
15. **[Guardian]** Responds with references → Cites uploaded document

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix Needed |
|-----------|----------------------|---------------|---------------------|
| Steps 1-8 | ✅ Working | None | - |
| Step 9 | 🔴 **Critical Gap** | Best-effort embed with no confirmation, ignores failures | **Add reliable embedding pipeline** with status tracking |
| Step 10 | 🔴 **Missing** | `/api/embeddings` endpoint may not exist or may not do what's needed | **Verify endpoint exists**, implement if missing |
| Steps 11-12 | 🟡 Partial | Embedding may succeed but no confirmation to user | **Add UI feedback** for embedding status |
| Steps 13-15 | ✅ Working | Assumes embedding worked | **Test end-to-end** with uploaded document query |

**Critical Gaps**:

1. **No reliable embedding pipeline** - `useUploader.ts:134-137` makes fire-and-forget request with no error handling
2. **No embedding status UI** - User has no idea if document is ready for RAG
3. **Endpoint uncertainty** - Need to verify `/api/embeddings` endpoint exists and handles chunked documents correctly
4. **No document chunking strategy** - Large documents may not be chunked optimally for retrieval

#### Implementation Tasks

| ID | Task | Files | Complexity | Priority |
|----|------|-------|------------|----------|
| M3.1 | **Verify/implement `/api/embeddings` endpoint** | `guardian/routes/?` (find or create) | M | **CRITICAL** |
| M3.2 | **Add document embedding worker** | `guardian/workers/document_embed_worker.py` (new) | M | **CRITICAL** |
| M3.3 | **Track embedding status in UploadedDocument model** | `guardian/db/models.py:UploadedDocument` (add `embedding_status` column) | S | HIGH |
| M3.4 | **Add UI embedding status indicator** | `frontend/src/components/documents/DocumentTile.tsx` | M | HIGH |
| M3.5 | **Implement reliable chunking strategy** | `guardian/services/document_chunking.py` | M | MED |
| M3.6 | **Add document-to-chunks table** | `guardian/db/models.py:DocumentChunk` (new model) | M | MED |
| M3.7 | **Add integration test** | `guardian/tests/test_document_upload_e2e.py` (new) | M | HIGH |

#### Validation Plan

**Manual Test Script**:

```bash
# 1. Start stack
docker-compose up -d
 
# 2. Open UI at http://localhost:5173
# 3. Navigate to Documents view
# 4. Drag a PDF file (e.g., research paper) into the view
# 5. Verify:
#    - Upload progress indicator appears
#    - Document appears in grid with filename
#    - Status indicator shows "Processing..." then "Ready"
 
# 6. Open Guardian chat
# 7. Ask: "What are the main topics in the document I just uploaded?"
# 8. Verify:
#    - Guardian responds with references to document content
#    - RAG trace shows document chunks in semantic results
 
# 9. Check backend logs for embedding confirmation:
docker-compose logs backend | grep -i "embed"
```

**Automated Tests**:

1. **Unit test** - `guardian/tests/test_document_parsing.py`:
   - Test PDF extraction
   - Test DOCX extraction
   - Test chunking strategy

2. **Integration test** - `guardian/tests/test_document_upload_e2e.py` (new):
   - POST document to `/api/media/upload/document`
   - Verify database record created
   - Trigger embedding via worker or sync endpoint
   - Query vector store to confirm chunks exist
   - Call `/api/chat/{thread_id}/complete` with query about document
   - Verify response includes document content

---

### 2.4 Upload Images to Gallery

#### Current State

**STATUS**: ✅ **Loop Closed** - Fully working end-to-end

**Key Components Found**:

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **GalleryView** | `frontend/src/components/gallery/GalleryView.tsx` | ✅ Implemented | Displays images, drag & drop, fetches from backend |
| **Upload Hook** | `frontend/src/hooks/useUploader.ts:58-87` | ✅ Implemented | Handles image upload to backend |
| **Upload Endpoint** | `guardian/routes/media.py` (inferred) | ✅ Implemented | POST `/api/media/upload/image` |
| **List Endpoint** | `guardian/routes/media.py` (inferred) | ✅ Implemented | GET `/api/media/images` |
| **Database Model** | `guardian/db/models.py:UploadedImage` | ✅ Implemented | Stores image metadata (src_url, filename, mime_type) |
| **Storage Manager** | `guardian/core/storage.py` | ✅ Implemented | Handles file persistence (local FS or cloud) |

**How It Works Today**:

1. User drags image into GalleryView or clicks upload button
2. `useUploader` validates file extension (`.png`, `.jpg`, `.jpeg`, `.webp`)
3. Creates FormData with file and project_id
4. POSTs to `/api/media/upload/image`
5. Backend:
   - Saves file via StorageManager (generates unique filename)
   - Creates `UploadedImage` record with metadata
   - Returns `{id, src_url, filename, filesize, mime_type, created_at}`
6. Frontend:
   - Adds image to local state
   - Displays in gallery grid
7. On mount, GalleryView fetches `/api/media/images` to hydrate from backend

#### Core Loop Definition

**End-to-End User Story**:
> User drags family photos into Gallery, sees upload progress, images appear in gallery grid, user can view full-size images and see metadata.

**Core Loop Steps**:

1. **[UI]** User drags images into GalleryView → `useUploader.handleFiles()` called
2. **[UI]** Validate file extensions → Must be .png, .jpg, .jpeg, .webp
3. **[UI]** For each image:
   - Create FormData with file, project_id
   - POST to `/api/media/upload/image`
4. **[Backend]** Receive upload → `guardian/routes/media.py:upload_image()`
5. **[Backend]** Generate unique filename → `generate_unique_filename()`
6. **[Backend]** Save file → `StorageManager.save_file()`
7. **[Backend]** Create database record → `UploadedImage` with metadata
8. **[Backend]** Return metadata → `{id, src_url, filename, ...}`
9. **[UI]** Receive response → Add to `backendImages` state
10. **[UI]** Display in grid → `PreviewTile` component renders image
11. **[User]** Click image → Full-size preview opens
12. **[User]** See metadata → Filename displayed in gallery

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix Needed |
|-----------|----------------------|---------------|---------------------|
| All steps | ✅ Fully working | None | - |

**No critical gaps** - This feature is complete and ready to use.

**Minor Enhancements (Post-MVP)**:

- Thumbnail generation for large images
- Delete functionality (currently stubbed: `handleDelete()`)
- Image tagging/categorization
- Image search by content (visual embeddings)

#### Implementation Tasks

| ID | Task | Files | Complexity | Priority |
|----|------|-------|------------|----------|
| M4.1 | **Implement delete endpoint** | `guardian/routes/media.py` (add DELETE route) | S | LOW |
| M4.2 | **Wire delete button in UI** | `frontend/src/components/gallery/PreviewTile.tsx` | S | LOW |
| M4.3 | **Add integration test** | `guardian/tests/test_image_upload_e2e.py` (new) | M | MED |

#### Validation Plan

**Manual Test Script**:

```bash
# 1. Start stack
docker-compose up -d
 
# 2. Open UI at http://localhost:5173
# 3. Navigate to Gallery view
# 4. Drag 3-5 images into the view
# 5. Verify:
#    - Upload indicators appear
#    - Images appear in gallery grid
#    - Clicking image shows full-size preview
#    - Filenames are visible
 
# 6. Refresh page
# 7. Verify:
#    - Images persist (loaded from backend)
#    - Same images appear in grid
 
# 8. Check backend storage:
docker-compose exec backend ls /app/uploads/images/
```

**Automated Tests**:

1. **Unit test** - `guardian/tests/test_storage_manager.py`:
   - Test file saving
   - Test unique filename generation
   - Test metadata extraction

2. **Integration test** - `guardian/tests/test_image_upload_e2e.py` (new):
   - POST image to `/api/media/upload/image`
   - Verify database record created
   - Verify file exists on disk/storage
   - GET `/api/media/images`
   - Verify uploaded image appears in list

---

### 2.5 Generate Images

#### Current State

**STATUS**: 🟡 **Partially Implemented** - Provider abstraction exists, needs UI wiring and testing

**Key Components Found**:

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **ImageGenRouter** | `guardian/image_gen/router.py:59-88` | ✅ Implemented | Provider abstraction (OpenAI/Local/Stability) |
| **OpenAI Provider** | `guardian/image_gen/providers/openai.py` | ✅ Implemented | DALL-E integration |
| **Local Provider** | `guardian/image_gen/providers/local.py` | 🟡 Partial | Placeholder/stub |
| **Stability Provider** | `guardian/image_gen/providers/stability.py` | ✅ Implemented | Stability AI integration |
| **Generation Endpoint** | `guardian/routes/media.py:102-116` | ✅ Implemented | POST `/api/media/generate/image` |
| **Database Model** | `guardian/db/models.py:GeneratedImage` | ✅ Implemented | Stores generated image metadata |
| **UI Modal** | `frontend/src/components/?` | 🔴 **Missing** | No UI for image generation found |

**How It Works Today (Backend)**:

1. POST `/api/media/generate/image` with:
   - `prompt`: Text prompt for generation
   - `model`: Model name (e.g., "dall-e-3")
   - Optional: project_id, thread_id, user_id
2. Backend:
   - Resolves provider from `IMAGE_GEN_PROVIDER` env var
   - Calls `ImageGenRouter.generate(prompt, model)`
   - Provider generates image bytes
   - Saves image via StorageManager
   - Creates `GeneratedImage` record
   - Returns `{id, src_url, prompt, model, created_at}`

#### Core Loop Definition

**End-to-End User Story**:
> User clicks "Generate Image" in Gallery, enters prompt "A serene mountain landscape at sunset", clicks Generate, sees progress indicator, generated image appears in gallery.

**Core Loop Steps**:

1. **[UI]** User clicks "Generate Image" button in Gallery → Modal opens
2. **[UI]** User enters prompt and selects model → Form fields filled
3. **[UI]** User clicks "Generate" → POST `/api/media/generate/image`
4. **[Backend]** Receive request → `guardian/routes/media.py:generate_image()`
5. **[Backend]** Resolve provider → `ImageGenRouter.get_provider()`
6. **[Backend]** Validate model → Check if model supported by provider
7. **[Backend]** Call provider → `provider.generate(prompt, model=model)`
8. **[Backend]** Generate image → Provider-specific API call
9. **[Backend]** Receive image bytes → PNG/JPEG data
10. **[Backend]** Save image → `StorageManager.save_file()`
11. **[Backend]** Create database record → `GeneratedImage` with prompt, model
12. **[Backend]** Return metadata → `{id, src_url, prompt, model, ...}`
13. **[UI]** Receive response → Display generated image in gallery
14. **[UI]** Close modal → User sees new image in grid

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix Needed |
|-----------|----------------------|---------------|---------------------|
| Step 1 | 🔴 **Missing** | No "Generate Image" button in GalleryView | **Add button** to GalleryView header |
| Step 1-2 | 🔴 **Missing** | No UI modal for image generation | **Create `ImageGenModal.tsx`** component |
| Steps 3-12 | ✅ Working | Backend fully implemented | **Test with real provider** |
| Step 13 | 🟡 Partial | Gallery refresh mechanism exists | **Wire modal to onImages callback** |
| Step 14 | ✅ Working | Modal close implemented | - |

**Critical Gaps**:

1. **No UI for image generation** - Need modal component with prompt input, model selector, generate button
2. **Local provider is stub** - Need real local image gen (Stable Diffusion, etc.) or mark as unavailable
3. **No provider configuration guide** - Users need docs for setting API keys

#### Implementation Tasks

| ID | Task | Files | Complexity | Priority |
|----|------|-------|------------|----------|
| M5.1 | **Create ImageGenModal component** | `frontend/src/components/modals/ImageGenModal.tsx` (new) | M | **CRITICAL** |
| M5.2 | **Add "Generate Image" button to Gallery** | `frontend/src/components/gallery/GalleryView.tsx` | S | **CRITICAL** |
| M5.3 | **Wire modal to generation endpoint** | `ImageGenModal.tsx` → POST `/api/media/generate/image` | M | **CRITICAL** |
| M5.4 | **Test OpenAI provider end-to-end** | Manual test with real API key | S | HIGH |
| M5.5 | **Implement local provider OR mark unavailable** | `guardian/image_gen/providers/local.py` | L | LOW |
| M5.6 | **Add provider config docs** | `docs/IMAGE_GENERATION.md` (new) | S | MED |
| M5.7 | **Add integration test** | `guardian/tests/test_image_generation_e2e.py` (new) | M | MED |

#### Validation Plan

**Manual Test Script**:

```bash
# 1. Set IMAGE_GEN_PROVIDER and credentials in .env
echo "IMAGE_GEN_PROVIDER=openai" >> .env
echo "OPENAI_API_KEY=sk-..." >> .env
 
# 2. Start stack
docker-compose up -d
 
# 3. Open UI at http://localhost:5173
# 4. Navigate to Gallery view
# 5. Click "Generate Image" button (once implemented)
# 6. Enter prompt: "A futuristic city with flying cars"
# 7. Select model: "dall-e-3"
# 8. Click "Generate"
# 9. Verify:
#    - Progress indicator appears
#    - Generated image appears in gallery
#    - Image is full resolution
#    - Prompt is stored in metadata
 
# 10. Test error handling:
#     - Enter empty prompt → Verify error message
#     - Invalid API key → Verify helpful error message
```

**Automated Tests**:

1. **Unit test** - `guardian/tests/test_image_gen_router.py`:
   - Test provider resolution
   - Test model validation
   - Mock provider.generate() call

2. **Integration test** - `guardian/tests/test_image_generation_e2e.py` (new):
   - POST to `/api/media/generate/image` with mock provider
   - Verify image saved to storage
   - Verify `GeneratedImage` record created
   - Verify returned src_url is accessible

---

### 2.6 Generate Documents (Code / Literature / Diagrams)

#### Current State

**STATUS**: 🟡 **Partially Implemented** - Backend mostly ready, UI needs wiring

**Key Components Found**:

| Component | File Path | Status | Notes |
|-----------|-----------|--------|-------|
| **Generation Endpoint** | `guardian/routes/documents.py:51-78` | ✅ Implemented | POST `/api/documents/generate` |
| **Document Gen Modal** | `frontend/src/components/DocumentGenModal.tsx` | ✅ Implemented | Captures title, prompt, format |
| **AI Router** | `guardian/core/ai_router.py` | ✅ Implemented | Calls LLM for content generation |
| **Database Model** | `guardian/db/models.py:GeneratedDocument` | ✅ Implemented | Stores generated doc with format, model |
| **Thread Linking** | `guardian/db/models.py:ThreadDocument` | ✅ Implemented | Links generated docs to threads |

**How It Works Today (Backend)**:

1. POST `/api/documents/generate` with:
   - `prompt`: What to generate (e.g., "Python script for sorting CSV")
   - `title`: Optional document title
   - `format`: "markdown" or "plain"
   - `doc_type`: "code" / "literature" / "diagram" (optional)
   - `context`: Additional context (optional)
   - `provider`, `model`: LLM selection (optional)
2. Backend:
   - Constructs system prompt based on doc_type
   - Calls `chat_with_ai()` with prompt
   - Receives generated content
   - Creates `GeneratedDocument` record
   - Optionally links to thread via `ThreadDocument`
   - Returns `{ok, document_id, content, format, title}`

**Frontend Modal** (`DocumentGenModal.tsx`):

- Has form with title, prompt, format selector
- Calls `onSubmit` callback with `{title, prompt, format}`
- **BUT**: onSubmit callback is not wired to backend endpoint

#### Core Loop Definition

**End-to-End User Story**:
> User clicks "Generate Document" in Documents view, selects type "Code", enters prompt "Python script to parse JSON and export to CSV", clicks Generate, sees progress, generated code appears in Documents view, user can open and edit it.

**Core Loop Steps**:

1. **[UI]** User clicks "Generate Document" button → `DocumentGenModal` opens
2. **[UI]** User fills form:
   - Title: "JSON to CSV Parser" (optional)
   - Prompt: "Python script to parse JSON and export to CSV"
   - Format: "plain" (for code) or "markdown" (for prose)
   - Type: "code" (inferred or selected)
3. **[UI]** User clicks "Save Draft" / "Generate" → `onSubmit({title, prompt, format})`
4. **[UI]** POST `/api/documents/generate` with payload
5. **[Backend]** Receive request → `guardian/routes/documents.py:generate_document()`
6. **[Backend]** Construct system prompt:
   - If `doc_type="code"`: "You are a code generator..."
   - If `doc_type="literature"`: "You are a creative writer..."
   - If `doc_type="diagram"`: "You generate Mermaid diagrams..."
7. **[Backend]** Call LLM → `chat_with_ai(messages, model, provider)`
8. **[Backend]** Receive generated content → Extract from assistant message
9. **[Backend]** Create `GeneratedDocument` → Store content, title, format, model
10. **[Backend]** Link to thread (if thread_id provided) → Create `ThreadDocument`
11. **[Backend]** Return metadata → `{ok, document_id, content, format, title}`
12. **[UI]** Receive response → Display success, emit event
13. **[UI]** Document appears in DocumentsView → User can open/view/edit
14. **[User]** Click document → Opens in viewer/editor

#### Gap Analysis

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix Needed |
|-----------|----------------------|---------------|---------------------|
| Step 1 | 🔴 **Missing** | No "Generate Document" button in DocumentsView | **Add button** to DocumentsView header |
| Steps 2-3 | ✅ Working | Modal exists and captures input | - |
| Step 4 | 🔴 **Missing** | Modal `onSubmit` not wired to backend | **Wire to POST `/api/documents/generate`** |
| Steps 5-11 | ✅ Working | Backend fully implemented | **Test with real provider** |
| Step 12 | 🟡 Partial | Need to emit `cfy:documents:add` event | **Add event emission** in modal |
| Step 13 | 🟡 Partial | DocumentsView needs to listen for event | **Add event listener** or refetch |
| Step 14 | 🟡 Partial | Document viewer/editor exists? | **Verify or create** viewer component |

**Critical Gaps**:

1. **No "Generate Document" button** - Users can't trigger generation flow
2. **Modal not wired to backend** - `onSubmit` callback does nothing
3. **No doc_type selector** - User can't specify code vs literature vs diagram
4. **No viewer for generated documents** - Can't open/edit after generation

#### Implementation Tasks

| ID | Task | Files | Complexity | Priority |
|----|------|-------|------------|----------|
| M6.1 | **Add "Generate Document" button to DocumentsView** | `frontend/src/components/documents/DocumentsView.tsx` | S | **CRITICAL** |
| M6.2 | **Wire modal to generation endpoint** | Wire `DocumentGenModal.onSubmit` → POST `/api/documents/generate` | M | **CRITICAL** |
| M6.3 | **Add doc_type selector to modal** | `frontend/src/components/DocumentGenModal.tsx` (add dropdown) | S | HIGH |
| M6.4 | **Emit document add event after generation** | Modal response handler | S | HIGH |
| M6.5 | **Create/verify document viewer component** | `frontend/src/components/documents/DocumentViewer.tsx` | M | MED |
| M6.6 | **Test end-to-end with real LLM** | Manual test with code/literature/diagram prompts | S | HIGH |
| M6.7 | **Add integration test** | `guardian/tests/test_document_generation_e2e.py` (may exist, verify) | M | MED |

#### Validation Plan

**Manual Test Script**:

```bash
# 1. Start stack
docker-compose up -d
 
# 2. Open UI at http://localhost:5173
# 3. Navigate to Documents view
# 4. Click "Generate Document" button (once implemented)
# 5. Test Code Generation:
#    - Type: "Code"
#    - Prompt: "Python function to calculate Fibonacci sequence"
#    - Format: "plain"
#    - Click Generate
#    - Verify: Python code appears in Documents view
 
# 6. Test Literature Generation:
#    - Type: "Literature"
#    - Prompt: "Short story about a robot learning to paint"
#    - Format: "markdown"
#    - Click Generate
#    - Verify: Formatted story appears in Documents view
 
# 7. Test Diagram Generation:
#    - Type: "Diagram"
#    - Prompt: "Mermaid diagram of microservices architecture"
#    - Format: "markdown"
#    - Click Generate
#    - Verify: Mermaid diagram code appears
 
# 8. Open generated document
# 9. Verify viewer/editor works correctly
```

**Automated Tests**:

1. **Unit test** - `guardian/tests/test_document_generation.py`:
   - Test system prompt construction for each doc_type
   - Test format validation
   - Mock LLM response

2. **Integration test** - `guardian/tests/test_document_generation_e2e.py`:
   - POST to `/api/documents/generate` with real LLM
   - Verify `GeneratedDocument` created
   - Verify content matches expected format
   - Link to thread and verify `ThreadDocument` created

---

## 3. Milestones & Timeline

### Milestone 0: Blockers & Infrastructure (2-3 days)

**Goal**: Fix critical infrastructure gaps that block MVP features

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| M3.1 | Verify/implement `/api/embeddings` endpoint | 4h | 🔴 Critical |
| M1.1 | Verify memory store initialization | 2h | 🟡 High |
| M1.2 | Add integration test for context assembly | 4h | 🟡 High |

**Exit Criteria**:

- `/api/embeddings` endpoint confirmed working
- Memory store verified in dependencies
- Context broker has passing integration test

---

### Milestone 1: RAG + Context Broker (3-4 days)

**Goal**: Close the memory/RAG loop with verifiable end-to-end flow

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| M1.3 | Decision on graph context (keep or defer) | 1h | 🟡 High |
| M1.5 | Add context preview UI | 6h | 🟡 Med |
| M1.4 | Make auto-embed async (optional) | 4h | 🟢 Low |

**Exit Criteria**:

- User can ask Guardian question about past conversations
- RAG trace shows retrieved context
- Context preview UI shows what was retrieved (optional but nice)

---

### Milestone 2: Document Upload + Reliable Embedding (4-5 days)

**Goal**: Close the document upload loop with reliable embedding pipeline

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| M3.2 | Add document embedding worker | 8h | 🔴 Critical |
| M3.3 | Track embedding status in DB | 2h | 🟡 High |
| M3.4 | Add UI embedding status indicator | 4h | 🟡 High |
| M3.5 | Implement reliable chunking strategy | 6h | 🟡 Med |
| M3.7 | Add integration test | 6h | 🟡 High |

**Exit Criteria**:

- User uploads PDF, sees "Processing..." then "Ready" status
- User asks Guardian about uploaded PDF, gets accurate response
- Document chunks appear in RAG trace

---

### Milestone 3: Image Generation (2-3 days)

**Goal**: Close the image generation loop with working UI

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| M5.1 | Create ImageGenModal component | 6h | 🔴 Critical |
| M5.2 | Add "Generate Image" button to Gallery | 1h | 🔴 Critical |
| M5.3 | Wire modal to generation endpoint | 4h | 🔴 Critical |
| M5.4 | Test OpenAI provider end-to-end | 2h | 🟡 High |
| M5.6 | Add provider config docs | 2h | 🟡 Med |

**Exit Criteria**:

- User clicks "Generate Image", enters prompt, sees generated image in gallery
- Works with at least one provider (OpenAI DALL-E recommended)
- Error handling works (invalid prompt, API errors)

---

### Milestone 4: Document Generation (2-3 days)

**Goal**: Close the document generation loop

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| M6.1 | Add "Generate Document" button | 1h | 🔴 Critical |
| M6.2 | Wire modal to generation endpoint | 4h | 🔴 Critical |
| M6.3 | Add doc_type selector to modal | 2h | 🟡 High |
| M6.4 | Emit document add event | 1h | 🟡 High |
| M6.5 | Create/verify document viewer | 6h | 🟡 Med |
| M6.6 | Test end-to-end with real LLM | 2h | 🟡 High |

**Exit Criteria**:

- User generates code, literature, and diagram documents
- Generated documents appear in DocumentsView
- User can open and view generated content

---

### Milestone 5: Polish & Testing (2-3 days)

**Goal**: Verify all loops work, fix bugs, add missing tests

| Task ID | Task | Estimate | Status |
|---------|------|----------|--------|
| M2.1 | Add ChatGPT migration integration test | 4h | 🟡 Med |
| M4.3 | Add image upload integration test | 4h | 🟡 Med |
| M5.7 | Add image generation integration test | 4h | 🟡 Med |
| Various | Bug fixes from manual testing | 8h | 🟢 Low |
| Various | Documentation updates | 4h | 🟢 Low |

**Exit Criteria**:

- All 6 core features have passing integration tests
- Manual test scripts pass for all features
- README updated with MVP feature checklist

---

## 4. Risks, Assumptions & Dependencies

### Critical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Vector store not initialized properly** | M1, M3 blocked | Verify `guardian/core/dependencies.py:_vector_store` init logic |
| **Embedding endpoint missing or broken** | M3 blocked | Implement M3.1 first (verify/create endpoint) |
| **LLM provider not configured** | M1, M6 degraded | Test with local provider fallback, add config validation |
| **Neo4j not running** | M1 degraded if graph enabled | Disable graph context for MVP (`GUARDIAN_ENABLE_GRAPH_CONTEXT=false`) |

### Assumptions

1. **Database migrations applied** - All tables exist (ChatThread, UploadedDocument, GeneratedImage, etc.)
2. **Docker services running** - Postgres, Redis, (optionally Neo4j) healthy
3. **At least one LLM provider configured** - Groq or OpenAI API key set
4. **Local embeddings working** - SentenceTransformers model downloaded (`bge-large-en-v1.5`)
5. **Storage configured** - `STORAGE_BACKEND` set (local filesystem by default)

### External Dependencies

| Dependency | Required For | Fallback |
|------------|--------------|----------|
| **Groq API Key** | Guardian chat (M1) | Use OpenAI or local provider |
| **OpenAI API Key** | Image generation (M5, optional M1) | Use Stability AI or skip image gen |
| **Postgres** | All features | **Blocker** - must be running |
| **Redis** | Chat completion workers | Sync completion (slower) |
| **Neo4j** | Graph context (M1, optional) | Disable graph context |

---

## 5. Deferred Features (Post-MVP Parking Lot)

### Phase: Post-MVP (v1.1)

- **Plugins system** - Mature plugin architecture exists but not needed for core loops
- **Federation** - Cross-instance search/context (`GUARDIAN_ENABLE_FEDERATION=false`)
- **TTS Output** - Text-to-speech synthesis routes exist but not core
- **Connector framework** - GitHub/GDrive/Notion sync (routes exist, workers disabled)
- **Neo4j graph context** - If decision is to defer (M1.3b)
- **Collaboration/WebSocket** - Real-time document editing (`guardian/realtime/collaboration.py`)
- **Advanced RAG** - Hybrid search, reranking, query expansion
- **Document versioning** - Track changes, diffs, rollback

### Phase: v1.2+

- **Multi-user RBAC** - Roles, permissions, row-level security
- **Advanced image generation** - Local Stable Diffusion, fine-tuning
- **Document editing** - Rich text editor for generated documents
- **Visual embeddings** - Image search by content
- **Audio transcription** - Upload audio, transcribe, embed
- **Mobile app** - Native iOS/Android client
- **Cloud sync** - Backup to S3/GCS/Azure Blob
- **Advanced analytics** - Usage dashboards, conversation insights

---

## 6. Implementation Checklist (Priority Order)

Use this checklist to tackle MVP tasks in optimal order:

### 🔴 Critical Path (Must Do First)

- [ ] **M3.1** - Verify/implement `/api/embeddings` endpoint (4h)
- [ ] **M1.1** - Verify memory store initialization (2h)
- [ ] **M1.2** - Add integration test for context assembly (4h)
- [ ] **M5.1** - Create ImageGenModal component (6h)
- [ ] **M5.2** - Add "Generate Image" button to Gallery (1h)
- [ ] **M5.3** - Wire modal to generation endpoint (4h)
- [ ] **M6.1** - Add "Generate Document" button to DocumentsView (1h)
- [ ] **M6.2** - Wire DocumentGenModal to generation endpoint (4h)

### 🟡 High Priority (Core Loop Completion)

- [ ] **M3.2** - Add document embedding worker (8h)
- [ ] **M3.3** - Track embedding status in UploadedDocument model (2h)
- [ ] **M3.4** - Add UI embedding status indicator (4h)
- [ ] **M1.3** - Decision on graph context (keep or defer) (1h)
- [ ] **M6.3** - Add doc_type selector to DocumentGenModal (2h)
- [ ] **M6.4** - Emit document add event after generation (1h)
- [ ] **M5.4** - Test OpenAI provider end-to-end (2h)
- [ ] **M6.6** - Test document generation end-to-end (2h)
- [ ] **M3.7** - Add document upload integration test (6h)

### 🟢 Medium Priority (Polish & Testing)

- [ ] **M1.5** - Add context preview UI (6h)
- [ ] **M3.5** - Implement reliable chunking strategy (6h)
- [ ] **M6.5** - Create/verify document viewer component (6h)
- [ ] **M5.6** - Add provider config docs (2h)
- [ ] **M2.1** - Add ChatGPT migration integration test (4h)
- [ ] **M4.3** - Add image upload integration test (4h)
- [ ] **M5.7** - Add image generation integration test (4h)

### 🔵 Low Priority (Nice to Have)

- [ ] **M1.4** - Make auto-embed async (4h)
- [ ] **M4.1** - Implement delete endpoint for images (S)
- [ ] **M4.2** - Wire delete button in UI (S)
- [ ] **M3.2** - Add error handling for malformed migration JSON (S)

---

## 7. Next Steps

1. **Read this roadmap** - Understand the 6 core loops and current state
2. **Start with Critical Path** - Tackle M3.1 (verify embeddings endpoint) first
3. **Work through milestones sequentially** - M0 → M1 → M2 → M3 → M4 → M5
4. **Test as you go** - Use manual test scripts after each milestone
5. **Ship MVP** - Once all 6 core loops are closed, you have a usable MVP
6. **Gather feedback** - Use MVP yourself, identify real pain points
7. **Iterate** - Tackle post-MVP features based on actual usage needs

---

**End of MVP Roadmap**

*This document is a living plan. Update it as implementation progresses and new information is discovered.*
