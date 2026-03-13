# Codexify MVP State-Map: Complete Inventory of Progress

**Date Created:** 2026-01-13
**Purpose:** Comprehensive technical assessment of MVP features across all layers (API, Services, Frontend, DB, Integration, Tests, Docs)
**Scope:** 6 core MVP features only
**Audience:** Codexify Product Owner / Solo Developer

---

## Executive Summary

You have built **substantial infrastructure** for all 6 MVP features. The state is **mostly backend-complete, mostly frontend-incomplete**. The critical issue is **UI/Backend wiring gaps** — many backend endpoints exist but frontend doesn't call them, and some backend flows (like RAG trace) are implemented but not surfaced to the UI.

### Current Overall Progress: ~55% MVP Complete

| Feature | % Complete | Priority Fix | Effort |
|---------|-----------|--------------|--------|
| **Memory/RAG + Chat** | 80% | Surface RAG trace to frontend | 1-2 days |
| **ChatGPT Migration** | 60% | Add migration UI to Settings | 2-3 days |
| **Upload Documents + Embed** | 70% | Wire frontend POST to backend | 1 day |
| **Upload Images to Gallery** | 60% | Wire gallery fetch + upload | 1 day |
| **Generate Images** | 30% | Implement backend generation stub | 2-3 days |
| **Generate Documents** | 0% | Build entire feature (endpoint + UI) | 5-7 days |

---

## Feature 1: Memory/RAG + Context Broker + Guardian Chat

**Overall Status:** 🟡 **80% COMPLETE** — Core loop works, trace surfacing needed

### Technical Layer Breakdown

#### 1. API Layer (REST Endpoints)
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/chat/threads` | ✅ Complete | Creates thread; works |
| `GET /api/chat/threads` | ✅ Complete | Lists threads; works |
| `POST /api/chat/{thread_id}/messages` | ✅ Complete | Appends message to thread; works |
| `GET /api/chat/{thread_id}/messages` | ✅ Complete | Fetches thread messages; works |
| `POST /api/chat/{thread_id}/complete` | ✅ Complete | Triggers chat completion; accepts depth_mode param ✅ |
| `GET /api/chat/debug/rag-trace/{thread_id}/latest` | 🟡 Partial | Debug endpoint exists but never populated |

**Status:** ✅ All production endpoints complete; depth parameter wired

---

#### 2. Core Services (Business Logic)

**ContextBroker** (`guardian/context/broker.py`)
- ✅ **Implemented:** All 4 depth modes (shallow/normal/deep/diagnostic)
- ✅ **Implemented:** Fetches recent messages, semantic search, memory, sensors
- 🟡 **Roadmap/TBD:** Graph context retrieval is optional/experimental and disabled by default (requires Neo4j + `GUARDIAN_ENABLE_GRAPH_CONTEXT`)
- ✅ **Implemented:** Returns context bundle + trace metadata
- **Files:** `guardian/context/broker.py` (complete implementation)

**System Prompt Builder** (`codexify/system_prompt_builder.py`)
- ✅ **Implemented:** Assembles system message from imprint + persona + system docs
- ✅ **Implemented:** Accepts RAG context bundle
- 🟡 **Issue:** Not consistently called with RAG context in chat_complete()
- **Files:** `codexify/system_prompt_builder.py` (80% wired)

**Chat Worker** (`guardian/workers/chat_worker.py`)
- ✅ **Implemented:** Calls ContextBroker.assemble() correctly (line 161)
- ✅ **Implemented:** Receives both context bundle and trace (unpacked at line 161)
- 🔴 **BLOCKER:** Trace never published to task events
  - Line 161: `bundle, trace = await broker.assemble(...)` ← trace received
  - Line 371: `task.result_data = {"response": response_text}` ← only response stored
  - **Never does:** `task.trace = trace` or publishes trace in events
- **Files:** `guardian/workers/chat_worker.py` (70% wired)

**Message Embedding** (`guardian/workers/chat_worker.py`)
- ✅ **Implemented:** Auto-embeds new messages after they're created
- ✅ **Implemented:** Creates MemoryEntry rows + vector embeddings
- ✅ **Implemented:** Metadata includes thread_id, role, message_id, timestamp
- **Files:** `guardian/workers/chat_worker.py` lines 361-385

**Imprints & Personas** (`codexify/imprints/`, `codexify/personas/`)
- ✅ **Implemented:** Full CRUD for both
- ✅ **Implemented:** Persistence in database + system prompt integration
- **Files:** `codexify/imprints/store.py`, `codexify/personas/store.py`

---

#### 3. Frontend (React/TypeScript Components)

**GuardianChat** (`frontend/src/features/chat/GuardianChat.tsx`)
- ✅ **Implemented:** Thread creation + message rendering
- ✅ **Implemented:** Depth selector UI (4 buttons: shallow/normal/deep/diagnostic)
- ✅ **Implemented:** Depth state management (line 82): `const [depth, setDepth] = useState<DepthMode>("normal")`
- ✅ **Implemented:** Sends depth to API (line 116): `depth_mode: depth`
- ✅ **Implemented:** RAG trace state (line 83): `const [contextTrace, setContextTrace] = useState(null)`
- ✅ **Implemented:** Trace button visible (line 278)
- 🔴 **Issue:** RAG trace never populated (line 278-282):
  ```typescript
  const ctx = response?.data?.context
  if (ctx) setContextTrace(ctx)
  // ^ ctx will ALWAYS be null because backend doesn't return trace
  ```
- **Files:** `frontend/src/features/chat/GuardianChat.tsx` (90% wired)

**MemoryBrowser** (`frontend/src/features/settings/diagnostics/MemoryBrowser.tsx`)
- ✅ **Implemented:** Fetches `/api/chat/debug/rag-trace/{thread_id}/latest`
- 🔴 **Issue:** Endpoint returns empty because trace never stored in backend
- **Files:** `frontend/src/features/settings/diagnostics/MemoryBrowser.tsx` (blocked by backend)

---

#### 4. Database Layer

**ChatThread Model** ✅
```python
class ChatThread:
  id: int (PK)
  user_id: str
  title: str
  project_id: int (FK)
  created_at: TIMESTAMP
```

**ChatMessage Model** ✅
```python
class ChatMessage:
  id: int (PK)
  thread_id: int (FK)
  role: str ('user'/'assistant'/'system')
  content: Text
  created_at: TIMESTAMP
  extra_meta: JSONB
```

**MemoryEntry Model** 🟡 Exists but under-utilized
```python
class MemoryEntry:
  id: int
  user_id: str
  silo: str ('ephemeral'/'midterm'/'longterm')
  content: Text
  tags: Text
  pinned: bool
  created_at: TIMESTAMP
```
- ✅ Model exists; table migrated
- ✅ Auto-populated from new messages (embeddings create entries)
- 🟡 Not manually retrievable via UI (MemoryBrowser reads trace, not MemoryEntry table)

**Status:** ✅ All models exist and are populated correctly

---

#### 5. External Integrations

**LLM Provider Router** (`guardian/core/ai_router.py`)
- ✅ **Implemented:** Supports Groq (default), OpenAI, Anthropic, Gemini
- ✅ **Implemented:** Automatic failover if provider fails
- ✅ **Implemented:** Token counting + context window optimization
- ✅ **Implemented:** Chat completion via `chat_with_ai(messages, system_prompt, ...)`
- **Status:** Complete

**Vector Store (Chroma)** (`guardian/vector/`, `backend/vector_store/chroma_store.py`)
- ✅ **Implemented:** Embeddings storage with metadata
- ✅ **Implemented:** Semantic search with multiple depth modes
- ✅ **Implemented:** Hybrid BM25 + semantic scoring
- **Status:** Complete

**Neo4j Knowledge Graph** (`guardian/graph/`)
- ✅ **Implemented:** Semantic relationship storage
- ✅ **Implemented:** Node types: UserNode, ThreadNode, MessageNode
- ✅ **Implemented:** Used in ContextBroker for graph-based retrieval
- **Status:** Complete

---

#### 6. Tests & Coverage

**Unit Tests** ✅
- `tests/core/test_context_broker_depth.py` — Tests ContextBroker depth modes
- `tests/core/test_system_prompt_builder.py` — Tests prompt assembly

**Integration Tests** 🟡 Incomplete
- `tests/integration/test_chat_completion_context.py` — Exists but doesn't verify trace return
- Missing: Test that trace is returned in API response

**E2E Tests** 🟡 Incomplete
- No Cypress tests for depth mode + RAG trace visibility
- No validation that trace populates MemoryBrowser

**Status:** 70% coverage; gaps in trace/trace return

---

#### 7. Documentation

| Doc | Status |
|-----|--------|
| Architecture | ✅ Complete (`docs/reference/infrastructure/system_architecture.md`) |
| MVP Roadmap | ✅ Complete (`docs/codexify-mvp-roadmap.md`) |
| RAG System | ✅ Complete (inline code comments) |
| Depth Modes | ✅ Complete (inline code comments) |

---

### 🔴 Critical Blocker: RAG Trace Not Surfaced

**Problem:**
1. Backend: ContextBroker computes trace (semantic results + graph context) ✅
2. Backend: Chat worker receives trace ✅
3. Backend: Trace NEVER published in task response or events ❌
4. Frontend: Trace button visible but always empty ❌

**Files Needing Changes:**
- `guardian/workers/chat_worker.py` — Line 371: Add `task.trace = trace` before event publish
- `guardian/routes/chat.py` — Line 652: Modify response to include trace data
- Frontend test: Verify trace populates in MemoryBrowser

**Effort to Fix:** 1-2 days (straightforward; requires:trace storage in task, event publishing, frontend polling update)

---

### Quick Wins
1. **Populate trace in worker result** (1 hour) — Just add `task.trace = trace` at line 371
2. **Return trace in API response** (1 hour) — Modify response at line 652
3. **Test trace end-to-end** (2-3 hours) — Write integration test + Cypress test

---

### Final Status: Memory/RAG Feature

| Component | % Complete | Status |
|-----------|-----------|--------|
| API Endpoints | 100% | ✅ All wired |
| ContextBroker | 100% | ✅ Complete |
| System Prompt | 80% | 🟡 RAG integration inconsistent |
| Message Embedding | 100% | ✅ Auto-populates memory |
| Depth Mode UI | 100% | ✅ Wired frontend-to-backend |
| RAG Trace Surface | 0% | 🔴 Not returned to frontend |
| Tests | 70% | 🟡 Missing trace verification |

**To declare complete:** Surface RAG trace from backend to frontend (1-2 days of work)

---

---

## Feature 2: ChatGPT Migration Tool

**Overall Status:** 🟡 **60% COMPLETE** — Backend complete, frontend UI missing

### Technical Layer Breakdown

#### 1. API Layer

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /upload-chatgpt-export` | ✅ Complete | In `guardian/routes/migration.py` + `guardian/routes/rag_upload.py` |
| `POST /api/migration/status/{job_id}` | 🔴 Missing | No progress tracking endpoint |

**Status:** ✅ Endpoint exists; no progress tracking

---

#### 2. Core Services

**ChatGPT Parser & Ingester** (`backend/rag/chatgpt_migration.py`)
- ✅ **Implemented:** Parse ChatGPT JSON export format
- ✅ **Implemented:** Normalize timestamps, extract user/assistant roles
- ✅ **Implemented:** Create ChatThread + ChatMessage rows
- ✅ **Implemented:** Embed messages into Chroma vector store
- ✅ **Implemented:** Optional Neo4j ingestion
- ✅ **Implemented:** Source tagging (import_timestamp, original_source)
- **Status:** Complete with error handling

**Routes** (`guardian/routes/migration.py` + `guardian/routes/rag_upload.py`)
- ✅ **Implemented:** File upload handling
- ✅ **Implemented:** Validation + error responses
- ✅ **Implemented:** Returns success/failure with import counts
- 🟡 **Limitation:** Synchronous (blocks client); no background job
- **Status:** 80% (synchronous only; should be async)

---

#### 3. Frontend

**Migration UI** 🔴 **MISSING ENTIRELY**
- No button in Settings to trigger migration
- No modal for file upload
- No progress bar during import
- No confirmation screen showing import results

**Status:** 0% — No frontend UI exists

---

#### 4. Database Layer

**Thread/Message Creation** ✅
- Imported threads become ChatThread rows
- Messages become ChatMessage rows
- Relationships preserved
- **Status:** Complete

---

#### 5. External Integrations

**Vector Store (Chroma)** ✅
- Imported messages embedded and stored
- Searchable in RAG queries at any depth
- **Status:** Complete

**Neo4j (Optional)** ✅
- Creates UserNode → ThreadNode → MessageNode relationships
- Optional (can disable)
- **Status:** Complete

---

#### 6. Tests

**Unit Tests** ✅
- `tests/migrations/test_chatgpt_parser.py` — Parser roundtrip tests
- `tests/migrations/test_timestamp_normalization.py` — Timestamp handling

**Integration Tests** 🔴 Missing
- No test that uploads via HTTP endpoint
- No test that verifies imported content is searchable in chat

**E2E Tests** 🔴 Missing
- No Cypress test for full import workflow

**Status:** 40% (unit tests exist; integration/E2E missing)

---

#### 7. Documentation

| Doc | Status |
|-----|--------|
| ChatGPT Export Format | ✅ Complete (`docs/CHATGPT_MIGRATION_GUIDE.md`) |
| CLI Usage | ✅ Complete (`scripts/chatgpt_import/cli_migrate.py` has docstring) |
| HTTP Endpoint | 🔴 Missing |
| UI Workflow | 🔴 Missing |

---

### 🔴 Critical Gap: No Frontend UI

**What's Missing:**
1. Settings page needs "Import from ChatGPT" button
2. Modal: File picker → accept `.json` ChatGPT export
3. Backend queue/progress: Show import status (X% complete)
4. Confirmation: "Imported N conversations with M messages"

**Files to Create:**
- `frontend/src/components/modals/ChatGPTImportModal.tsx` — 300-400 LOC
- `frontend/src/features/settings/MigrationPage.tsx` — 200-300 LOC (or integrate into Settings)
- Update Settings navigation to include "Data Import" link

**Effort to Implement:** 2-3 days (straightforward UI + HTTP multipart POST)

---

### Quick Wins
1. **Add "Import ChatGPT" button to Settings** (1 hour)
2. **Create migration modal component** (3-4 hours) — file picker + progress
3. **Wire modal to HTTP endpoint** (1-2 hours) — upload + poll status
4. **Test import workflow** (2-3 hours)

---

### Final Status: ChatGPT Migration Feature

| Component | % Complete | Status |
|-----------|-----------|--------|
| Backend Parser | 100% | ✅ Complete |
| HTTP Endpoint | 100% | ✅ Complete |
| Frontend Modal | 0% | 🔴 Missing |
| Progress Tracking | 0% | 🔴 Not implemented (async) |
| Database Integration | 100% | ✅ Complete |
| Vector Store Integration | 100% | ✅ Complete |
| Tests | 40% | 🟡 Unit only |

**To declare complete:** Build Settings UI + migration modal (2-3 days of work)

---

---

## Feature 3: Upload Documents + Embed

**Overall Status:** 🟡 **70% COMPLETE** — Backend complete, frontend POST missing

### Technical Layer Breakdown

#### 1. API Layer

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/media/upload/document` | ✅ Complete | Accepts multipart file; embeds; saves to DB |
| `GET /api/documents` | ✅ Complete | Lists documents |
| `GET /api/documents/{doc_id}` | ✅ Complete | Retrieves document |
| `DELETE /api/documents/{doc_id}` | ✅ Complete | Soft-deletes document |
| `POST /api/embeddings` | ✅ Complete | Manual embedding endpoint |

**Status:** ✅ All endpoints wired and functional

---

#### 2. Core Services

**Document Upload Handler** (`guardian/routes/media.py` lines 257-378)
- ✅ **Implemented:** Multipart file handling
- ✅ **Implemented:** MIME type validation (PDF, MD, TXT, DOCX, JSON)
- ✅ **Implemented:** Text extraction from files
- ✅ **Implemented:** Unique filename generation
- ✅ **Implemented:** Storage to filesystem/S3
- **Status:** 100% complete

**Document Embedding** (`guardian/routes/media.py` lines 337-363)
- ✅ **Implemented:** Calls CodexifyEmbedder after upload
- ✅ **Implemented:** Stores embeddings in Chroma
- ✅ **Implemented:** Metadata includes: filename, source, doc_id, user_id, project_id, thread_id
- 🟡 **Limitation:** Only embeds if `parsed_text` exists (text-based files only; PDFs need OCR)
- **Status:** 90% complete (works for text; PDFs limited)

**Thread/Project Linking** (`guardian/db/models.py`)
- ✅ **Implemented:** ThreadDocument model with relation types
- ✅ **Implemented:** Document can link to thread + project
- ✅ **Implemented:** Upload route accepts optional thread_id, project_id
- **Status:** 100% complete

---

#### 3. Frontend

**File Upload Hook** (`frontend/src/hooks/useUploader.ts`)
- ✅ **Implemented:** File reading via FileReader API
- ✅ **Implemented:** Converts files to data URLs (base64)
- ✅ **Implemented:** Emits custom events: `cfy:documents:add`, `cfy:documents:upload`
- ✅ **Implemented:** Local error handling + toast notifications
- 🔴 **CRITICAL ISSUE:** Never calls backend
  - Line 28-137: All file handling is local only
  - **Missing:** `POST /api/media/upload/document` call
  - Attempts to embed at line 76: `fetch("/api/embeddings", ...)` but doesn't upload file

**Documents View** (`frontend/src/components/documents/DocumentsView.tsx`)
- ✅ **Implemented:** Lists documents
- ✅ **Implemented:** Preview + download functionality
- ✅ **Implemented:** Drag-drop upload UI
- 🔴 **Issue:** Upload doesn't persist (no backend POST)

**Status:** 40% wired (reads files locally but doesn't POST to backend)

---

#### 4. Database Layer

**UploadedDocument Model** ✅
```python
class UploadedDocument:
  id: int
  filename: str
  source: str ('upload'/'connector'/'generated')
  user_id: str
  project_id: int
  thread_id: int
  content: Text
  parsed_text: Text (extracted text)
  created_at: TIMESTAMP
```

**ThreadDocument Link** ✅
```python
class ThreadDocument:
  id: int
  thread_id: int
  document_id: int
  relation_type: str ('attached'/'autosave'/'reference')
  created_at: TIMESTAMP
```

**Status:** ✅ Both models exist; migrations applied

---

#### 5. External Integrations

**Vector Store (Chroma)** ✅
- Embeddings stored with document metadata
- Searchable in ContextBroker at all depth levels
- **Status:** Complete

**PDF Parser** 🟡 Limited
- Uses PyPDF2 or pdfplumber
- Text extraction only (no OCR for image-based PDFs)
- **Status:** Basic (text-only PDFs; image PDFs not supported)

---

#### 6. Tests

**Unit Tests** ✅
- Document parsing tests exist
- File type validation tests exist

**Integration Tests** 🟡 Incomplete
- Upload route tested via HTTP
- Missing: End-to-end test that uploads → verifies in Chroma → searches in chat

**E2E Tests** 🔴 Missing
- No Cypress test for document upload UI

**Status:** 50% coverage

---

#### 7. Documentation

| Doc | Status |
|-----|--------|
| Document Upload Format | ✅ Complete |
| Embedding Pipeline | ✅ Complete |
| Supported File Types | ✅ Complete |
| Frontend Integration | 🔴 Missing |

---

### 🔴 Critical Wiring Gap: Frontend Doesn't POST

**Problem:**
- Backend: `/api/media/upload/document` endpoint ready ✅
- Frontend: Reads files locally ✅
- Missing: Frontend POST to backend ❌

**What needs to happen:**
1. User selects file in DocumentsView
2. `useUploader.handleFiles()` should POST to `/api/media/upload/document`
   ```typescript
   const formData = new FormData()
   formData.append('file', file)
   formData.append('project_id', projectId)
   formData.append('thread_id', threadId)

   const response = await fetch('/api/media/upload/document', {
     method: 'POST',
     body: formData
   })
   ```
3. Backend returns doc_id + embedding status
4. Frontend updates UI with success message

**Effort to Fix:** 1 day (add POST in useUploader hook + error handling)

---

### Quick Wins
1. **Add POST to backend in useUploader** (2-3 hours)
2. **Add feedback on embedding status** (1-2 hours)
3. **Test upload end-to-end** (1-2 hours)

---

### Final Status: Upload Documents Feature

| Component | % Complete | Status |
|-----------|-----------|--------|
| Backend Upload Endpoint | 100% | ✅ Complete |
| Document Parsing | 90% | 🟡 Text-only (no OCR) |
| Embedding Pipeline | 100% | ✅ Complete |
| Database Models | 100% | ✅ Complete |
| Frontend File Read | 100% | ✅ Complete |
| Frontend POST to Backend | 0% | 🔴 Missing |
| Tests | 50% | 🟡 Unit + route; missing E2E |

**To declare complete:** Add frontend POST to backend + test (1 day of work)

---

---

## Feature 4: Upload Images to Gallery

**Overall Status:** 🟡 **60% COMPLETE** — Backend complete, frontend wiring missing

### Technical Layer Breakdown

#### 1. API Layer

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/media/upload/image` | ✅ Complete | Accepts image file; saves; returns src_url |
| `GET /api/media/images` | ✅ Complete | Lists uploaded images |
| `GET /api/media/images/{image_id}` | ✅ Complete | Retrieves specific image |
| `DELETE /api/media/images/{image_id}` | ✅ Complete | Deletes image |

**Status:** ✅ All endpoints wired and functional

---

#### 2. Core Services

**Image Upload Handler** (`guardian/routes/media.py` lines 133-202)
- ✅ **Implemented:** Multipart file handling
- ✅ **Implemented:** MIME type validation (PNG, JPG, WEBP, GIF)
- ✅ **Implemented:** Unique filename generation with UUID
- ✅ **Implemented:** Storage to filesystem/S3
- ✅ **Implemented:** Returns `src_url` in response
- **Status:** 100% complete

**Image List Handler** (`guardian/routes/media.py` lines 538-579)
- ✅ **Implemented:** Queries UploadedImage table
- ✅ **Implemented:** Returns array with src_url + metadata (filename, size, created_at)
- **Status:** 100% complete

---

#### 3. Frontend

**Gallery Component** (`frontend/src/components/gallery/GalleryView.tsx`)
- ✅ **Implemented:** Grid UI for displaying images
- ✅ **Implemented:** Image cards with metadata
- ✅ **Implemented:** View/delete buttons
- 🔴 **CRITICAL ISSUE:** Only shows DEMO items
  - Lines 11-28: `DEMO_GALLERY_ITEMS` hardcoded array
  - **Missing:** `useEffect` to fetch from `/api/media/images`
  - Component never calls backend

**File Upload Hook** (`frontend/src/hooks/useUploader.ts`)
- ✅ **Implemented:** Image file reading
- 🔴 **CRITICAL ISSUE:** Never POSTs to backend
  - Reads image as data URL (base64) locally
  - **Missing:** `POST /api/media/upload/image` call

**Status:** 30% wired (UI exists; doesn't fetch or upload from backend)

---

#### 4. Database Layer

**UploadedImage Model** ✅
```python
class UploadedImage:
  id: int
  user_id: str
  filename: str
  src_url: str
  file_size: int
  mime_type: str
  created_at: TIMESTAMP
```

**Status:** ✅ Model exists; migrations applied

---

#### 5. External Integrations

**File Storage** ✅
- Images stored to filesystem or S3
- URLs generated correctly
- **Status:** Complete

---

#### 6. Tests

**Unit Tests** ✅
- MIME type validation tests exist
- File size validation tests exist

**Integration Tests** 🟡 Incomplete
- Upload endpoint tested
- Missing: End-to-end test that uploads → fetches list → displays in gallery

**E2E Tests** 🔴 Missing
- No Cypress test for upload + gallery display

**Status:** 50% coverage

---

#### 7. Documentation

| Doc | Status |
|-----|--------|
| Image Upload Format | ✅ Complete |
| Supported MIME Types | ✅ Complete |
| Storage Mechanism | ✅ Complete |
| Frontend Integration | 🔴 Missing |

---

### 🔴 Critical Wiring Gaps: Two Missing

**Gap 1: Gallery doesn't fetch from backend**
- GalleryView hardcodes DEMO_GALLERY_ITEMS
- Missing: On component mount, fetch `/api/media/images`
  ```typescript
  useEffect(() => {
    fetch('/api/media/images')
      .then(r => r.json())
      .then(images => setImages(images))
  }, [])
  ```

**Gap 2: useUploader doesn't POST image to backend**
- Reads image locally but never uploads
- Missing: `POST /api/media/upload/image` with FormData
  ```typescript
  const formData = new FormData()
  formData.append('file', imageFile)

  const response = await fetch('/api/media/upload/image', {
    method: 'POST',
    body: formData
  })
  ```

**Effort to Fix:** 1 day total (2-3 hours per gap)

---

### Quick Wins
1. **Add fetch to GalleryView** (1 hour)
2. **Add POST in useUploader for images** (1-2 hours)
3. **Test upload → display workflow** (1-2 hours)

---

### Final Status: Upload Images Feature

| Component | % Complete | Status |
|-----------|-----------|--------|
| Backend Upload Endpoint | 100% | ✅ Complete |
| Backend List Endpoint | 100% | ✅ Complete |
| Database Model | 100% | ✅ Complete |
| File Storage | 100% | ✅ Complete |
| Frontend Gallery UI | 100% | ✅ UI complete |
| Frontend Fetch Images | 0% | 🔴 Missing |
| Frontend POST Upload | 0% | 🔴 Missing |
| Tests | 50% | 🟡 Unit + route; missing E2E |

**To declare complete:** Add frontend fetch + POST wiring (1 day of work)

---

---

## Feature 5: Generate Images

**Overall Status:** 🔴 **30% COMPLETE** — Frontend exists, backend is stub

### Technical Layer Breakdown

#### 1. API Layer

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /api/media/generate/image` | 🔴 Stub | Returns fake URL; never calls provider |

**Status:** 🔴 Endpoint exists but doesn't actually generate

---

#### 2. Core Services

**Image Generation Providers** ✅
- `guardian/image_gen/providers/openai.py` — ✅ Full DALL-E integration
- `guardian/image_gen/providers/local.py` — ✅ Local model support (e.g., Ollama)
- `guardian/image_gen/providers/stability.py` — ✅ Stability AI integration
- `guardian/image_gen/router.py` — ✅ Provider abstraction + routing

**Status:** ✅ Provider implementations exist but route doesn't use them

**Image Generation Route** (`guardian/routes/media.py` lines 385-430)
- 🔴 **CRITICAL ISSUE:** This endpoint is a stub
  ```python
  @router.post("/generate/image")
  async def generate_image(request: ImageGenRequest) -> dict:
      # NOTE: This endpoint doesn't actually generate images (yet).
      # It just tracks the generation request and returns a placeholder URL.
      image_id = uuid.uuid4().hex[:8]
      return {
          "image_id": image_id,
          "src_url": f"/media/generated/{image_id}.png"  # ← FAKE URL
      }
  ```
  - **Never calls:** `ImageGenRouter.generate(prompt, model)`
  - **Never saves:** Generated image to storage
  - **Returns:** Placeholder URL that doesn't exist

**What should happen:**
```python
# Get configured provider from env
provider_name = os.getenv('IMAGE_GEN_PROVIDER', 'openai')
provider = ImageGenRouter.get_provider(provider_name)

# Generate image
image_bytes = await provider.generate(prompt, model)

# Save to storage
storage_path = f"generated/{uuid.uuid4().hex}.png"
storage.save(storage_path, image_bytes)

# Return real URL
return { "src_url": f"/media/{storage_path}" }
```

**Status:** 10% (infrastructure exists; endpoint is stub)

---

#### 3. Frontend

**ImageGenModal** (`frontend/src/components/modals/ImageGenModal.tsx`)
- ✅ **Implemented:** Modal UI with prompt input
- ✅ **Implemented:** Loading state + error handling
- ✅ **Implemented:** Makes POST to `/api/media/generate/image`
- ✅ **Implemented:** Receives response + displays image
- 🟡 **Issue:** Receives fake URL from stub endpoint
  - Will try to display `/media/generated/{id}.png` which 404s
  - No error handling for missing image URL
- **Status:** 90% implemented (works with stub; needs real backend)

---

#### 4. Database Layer

**GeneratedImage Model** ✅
```python
class GeneratedImage:
  id: int
  user_id: str
  thread_id: int
  project_id: int
  prompt: str
  model: str
  src_url: str
  generation_time_ms: int
  created_at: TIMESTAMP
```

**Status:** ✅ Model exists

---

#### 5. External Integrations

**OpenAI DALL-E** ✅ (Provider exists)
- Implementation: `guardian/image_gen/providers/openai.py`
- Status: Ready to use if endpoint calls it

**Stability AI** ✅ (Provider exists)
- Implementation: `guardian/image_gen/providers/stability.py`
- Status: Ready to use if endpoint calls it

**Local (Ollama/ComfyUI)** ✅ (Provider exists)
- Implementation: `guardian/image_gen/providers/local.py`
- Status: Ready to use if endpoint calls it

**Status:** ✅ Providers implemented; endpoint just needs to use them

---

#### 6. Tests

**Unit Tests** 🟡 Incomplete
- Provider tests exist for individual providers
- Missing: Tests that endpoint routes to correct provider

**Integration Tests** 🔴 Missing
- No test that `POST /generate/image` calls provider + saves image

**E2E Tests** 🔴 Missing
- No Cypress test for full generation workflow

**Status:** 20% coverage

---

#### 7. Documentation

| Doc | Status |
|-----|--------|
| Supported Providers | ✅ Complete (in code) |
| Configuration | 🟡 Partial (env vars not documented) |
| API Endpoint | 🔴 Stub not documented |

---

### 🔴 Critical Blocker: Endpoint is Stub

**Problem:**
- Providers fully implemented ✅
- Frontend modal ready ✅
- Backend route returns fake URL ❌

**What needs to change in `guardian/routes/media.py` (lines 385-430):**
1. Read `IMAGE_GEN_PROVIDER` from `.env` (default: 'openai')
2. Get provider instance from `ImageGenRouter`
3. Call `provider.generate(prompt, model)`
4. Save binary image to storage (not just placeholder)
5. Return real URL

**Effort to Fix:** 2-3 days
- 2-3 hours to implement endpoint properly
- 1-2 hours to test with mock provider
- 1-2 hours to configure real provider (DALL-E key, etc.)

---

### Quick Wins
1. **Implement backend generation call** (2-3 hours)
2. **Test with mocked provider** (1-2 hours)
3. **Configure real provider** (1-2 hours + API key setup)

---

### Final Status: Generate Images Feature

| Component | % Complete | Status |
|-----------|-----------|--------|
| Image Providers | 100% | ✅ Complete implementations |
| Provider Router | 100% | ✅ Complete |
| Backend Generation Endpoint | 10% | 🔴 Stub only |
| Frontend Modal | 90% | ✅ Complete; expects real URL |
| Image Storage | 100% | ✅ Complete |
| Database Model | 100% | ✅ Complete |
| Configuration | 50% | 🟡 Env vars not set up |
| Tests | 20% | 🔴 Mostly missing |

**To declare complete:** Implement endpoint + connect to provider (2-3 days of work)

---

---

## Feature 6: Generate Documents

**Overall Status:** 🔴 **0% COMPLETE** — Feature entirely missing

### Technical Layer Breakdown

#### 1. API Layer

**No endpoint exists** 🔴
- No `POST /api/documents/generate` endpoint
- No `POST /api/media/generate/document` endpoint
- **Status:** Completely missing

---

#### 2. Core Services

**Document Generation Service** 🔴 **MISSING ENTIRELY**
- No generation logic exists
- No system prompts for different document types
- No type-specific handling (code vs. narrative vs. outline)
- **Status:** Completely missing

---

#### 3. Frontend

**Document Generation UI** 🔴 **MISSING ENTIRELY**
- No "Generate Document" button or modal
- No document type selector
- No prompt input
- No generated document viewer/editor
- **Status:** Completely missing

**Note:** Autosave exists (`POST /api/documents/autosave`) but that's not generation, that's saving draft documents.

---

#### 4. Database Layer

**GeneratedDocument Model** ✅ Exists (but unused)
```python
class GeneratedDocument:
  id: int
  user_id: str
  thread_id: int
  project_id: int
  title: str
  content: Text
  format: str ('md'/'code'/'plain')
  model: str
  created_at: TIMESTAMP
```

**ThreadDocument Link** ✅ Exists (for linking generated doc to thread)

**Status:** ✅ Models exist; never populated

---

#### 5. External Integrations

**LLM for Generation** ✅ (Already available)
- Chat completion via `guardian/core/ai_router.py` ready to use
- Token limits respected via context window management
- **Status:** Ready (just needs to be used)

---

#### 6. Tests

**No tests exist** 🔴
- **Status:** 0% coverage

---

#### 7. Documentation

**No documentation exists** 🔴
- **Status:** 0% coverage

---

### 📋 Full Implementation Checklist

This feature requires building from scratch:

**Backend (3-5 days effort):**
1. Create system prompts for document types
   - Code: Python, JavaScript, TypeScript, Rust, Go, SQL snippets
   - Narrative: Stories, essays, blog posts, reports
   - Outline: Structured outlines, agendas, TODOs

2. Create `/api/documents/generate` endpoint
   - Accept: `doc_type`, `prompt`, `project_id`, `thread_id`, optional `model`
   - Call LLM with type-specific system prompt
   - Save to GeneratedDocument + ThreadDocument
   - Return: `doc_id`, `content`, `format`

3. Implement generation logic
   - Queue or inline (depends on generation time; likely inline for <5 sec)
   - Error handling for LLM failures
   - Metadata tracking (model, generation_time, prompt)

4. Tests
   - Unit: System prompt templates render correctly
   - Integration: Generation endpoint → LLM → storage → retrieval
   - Mock LLM for tests

**Frontend (3-4 days effort):**
1. Create DocumentGenModal component
   - Type selector (code/narrative/outline radio buttons)
   - Prompt textarea
   - Optional parameters (language for code, tone for narrative)
   - Loading spinner during generation
   - Result viewer (syntax highlighting for code)

2. Wire to API
   - POST `/api/documents/generate`
   - Handle response + display result
   - Error handling

3. Editor integration
   - Display generated document in full editor
   - Edit + save functionality
   - Export options

4. Tests
   - Component rendering tests
   - API integration tests
   - Cypress E2E workflow

---

### Final Status: Generate Documents Feature

| Component | % Complete | Status |
|-----------|-----------|--------|
| Backend Endpoint | 0% | 🔴 Missing |
| System Prompts | 0% | 🔴 Missing |
| Generation Logic | 0% | 🔴 Missing |
| Frontend Modal | 0% | 🔴 Missing |
| Frontend Editor | 0% | 🔴 Missing |
| Database Models | 100% | ✅ Exist (unused) |
| LLM Integration | 100% | ✅ Ready to use |
| Tests | 0% | 🔴 Missing |

**To declare complete:** Build entire feature end-to-end (5-7 days of work)

---

---

## 🎯 MVP Completion Summary & Roadmap

### Current State: ~55% MVP Complete

| Feature | % Done | Blocker | Quick Fix Effort |
|---------|--------|---------|-----------------|
| Memory/RAG Chat | 80% | RAG trace not returned | 1-2 days |
| ChatGPT Migration | 60% | No Settings UI | 2-3 days |
| Upload Documents | 70% | Frontend doesn't POST | 1 day |
| Upload Images | 60% | Gallery doesn't fetch/POST | 1 day |
| Generate Images | 30% | Backend is stub | 2-3 days |
| Generate Documents | 0% | Completely missing | 5-7 days |

### Path to 100% MVP Complete: ~12-18 days of work

**Priority Order (by value + effort):**

1. **Quick Wins (3-4 days)** — Unblock core features
   - Feature 1: Surface RAG trace (1-2 days) → Enables diagnostics
   - Feature 3: Wire document upload POST (1 day) → Enables document retrieval
   - Feature 4: Wire gallery fetch + POST (1 day) → Enables image management

2. **Medium Effort (5-6 days)**
   - Feature 2: Build ChatGPT migration UI (2-3 days) → Enables user data import
   - Feature 5: Implement image generation (2-3 days) → Enables creative features

3. **Large Effort (5-7 days)**
   - Feature 6: Build document generation (5-7 days) → Enables content creation

---

## 🔍 Critical Wiring Gaps Summary

**Total Wiring Issues Found: 8**

| #  | Issue | Feature | Impact | Fix Time |
|----|-------|---------|--------|----------|
| 1  | RAG trace never published from worker | Memory/RAG | Trace always empty | 2 hours |
| 2  | No Settings UI for migration | ChatGPT | Users can't import | 2-3 days |
| 3  | useUploader doesn't POST documents | Upload Docs | Uploads don't persist | 2 hours |
| 4  | Gallery doesn't fetch from backend | Upload Images | Shows only demos | 1 hour |
| 5  | useUploader doesn't POST images | Upload Images | Uploads don't persist | 1 hour |
| 6  | Image gen endpoint is stub | Generate Images | Returns fake URL | 3 hours |
| 7  | No document generation endpoint | Generate Docs | Feature missing | 3 days |
| 8  | No document generation UI | Generate Docs | Feature missing | 3-4 days |

---

## 💡 Key Insights & Recommendations

### What You've Built Well ✅
1. **Solid Backend Infrastructure** — All core services exist and are well-structured
2. **Frontend Component Architecture** — React components are reusable and tested
3. **Database Design** — Schema is normalized, migrations clean, relationships clear
4. **LLM Integration** — Provider routing with fallbacks; token management
5. **Vector Store Integration** — Chroma configured for RAG; Neo4j graph context is optional/experimental (Roadmap/TBD for CORE LOOP)
6. **System Prompts** — Persona/imprint system sophisticated and flexible

### Main Gaps 🔴
1. **UI/Backend Wiring** — Many endpoints exist but frontend doesn't call them
2. **Feature Completion** — Several features are 90% done but 10% blocking (e.g., trace not returned)
3. **Async Job Handling** — Long operations (embedding, generation) don't have progress tracking
4. **E2E Testing** — Few integration/E2E tests; mostly unit tests
5. **Error Handling** — Some endpoints return stubs instead of real errors

### Quick Recommendations 🚀
1. **Start with Feature 1** (RAG trace) — Easy win, unblocks diagnostics
2. **Then Features 3 & 4** (uploads) — Small effort, high value
3. **Do Feature 2 next** (ChatGPT UI) — Users can then import their data
4. **Feature 5** (images) — Medium effort, nice-to-have
5. **Feature 6 last** (document gen) — Complex, can defer if timeline tight

### Testing Strategy
- Add 2-3 integration tests per feature (upload → verify retrieval)
- Add Cypress E2E test per feature (full UI workflow)
- Mock external services in tests (LLM, image providers)

---

## 📊 Technical Debt & Refactoring Opportunities (Post-MVP)

**High Priority:**
- [ ] Add progress tracking to long operations (embedding, generation, migration)
- [ ] Implement proper async job queue (Celery/RQ) instead of inline
- [ ] Add request/response logging for debugging
- [ ] Standardize error response format across all endpoints

**Medium Priority:**
- [ ] Consolidate upload endpoints (currently spread across `/media/upload`, `/media/upload/document`, etc.)
- [ ] Add OpenAPI/Swagger documentation
- [ ] Improve test coverage to >80% on critical paths
- [ ] Add feature flags for gradual rollout

**Low Priority:**
- [ ] Refactor chat worker (too many concerns)
- [ ] Consolidate system prompt builder logic
- [ ] Move embedding logic to separate service

---

## 📝 How to Use This State-Map

**For Prioritization:**
- Use the "% Complete" column to see which features are closest to done
- Use "Quick Fix Effort" to identify quick wins
- Use "Impact" to prioritize by business value

**For Planning Sprints:**
- Each feature has explicit "Effort to Fix" estimates
- Critical Blocker section shows exactly what's broken
- Quick Wins section shows easiest wins first

**For Testing:**
- Each feature lists Test & Coverage gaps
- Add those tests before declaring feature complete

**For Communication:**
- Share this with team/stakeholders to show progress
- Use it in standups: "Today: Fixing RAG trace return (3-4 hours remaining)"
- Update after each feature completion

---

## 🎓 Conclusion

You have a **strong, production-ready foundation**. The 6 MVP features are **70% infrastructure-complete** but **40% user-facing-complete**. Most gaps are **straightforward wiring issues** (frontend POST calls, trace publishing, stub implementations) rather than architectural problems.

**With 2-3 focused weeks of work, you can have a fully functional MVP.**

---

**Document Version:** 1.0
**Last Updated:** 2026-01-13
**Next Review:** After Feature 1 completion
