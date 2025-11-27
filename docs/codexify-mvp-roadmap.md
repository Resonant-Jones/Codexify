# Codexify MVP Roadmap & Core Loop Analysis

**Version:** 1.0
**Date:** 2025-11-25
**Scope:** MVP-critical features only; focus on end-to-end working loops

---

## 1. Executive Summary & Goals

Codexify has substantial infrastructure in place but several core loops **are incomplete or fragile**. This roadmap identifies:

- **6 non-negotiable core features** for MVP
- **Current state** of each feature (✅ / 🟡 / 🔴)
- **Concrete gaps** blocking each loop
- **Prioritized implementation tasks** grouped into logical milestones
- **Validation strategies** to confirm working end-to-end

### Key Findings

| Feature | Status | Blocker | Effort |
|---------|--------|---------|--------|
| **Memory/RAG + Context Broker + Guardian Chat** | 🟡 Partial | RAG → Chat wiring incomplete; depth selector exists but not fully connected | M |
| **ChatGPT Migration Tool** | 🟡 Partial | CLI exists, but no UI surface; backend dual-engine (Neo4j + Chroma) partially wired | M |
| **Upload Documents + Embed** | 🟡 Partial | UI hook exists, backend routes exist, but no embedding pipeline wired to memory system | M |
| **Upload Images to Gallery** | 🟡 Partial | Backend routes exist, frontend hook works, but gallery not pulling from DB | S |
| **Generate Images** | 🟡 Partial | Modal exists, backend route exists, but provider integration incomplete | S |
| **Generate Documents** | 🔴 Missing | No UI surface; backend route stub exists; no real generation loop | L |

---

## 2. Core MVP Features – Detailed Analysis

### 2.1 Memory / RAG System + Context Broker + Guardian Chat

#### Core Loop Definition (Ideal End-to-End)

1. **User** opens Codexify and selects a Guardian (persona/imprint).
2. **User** asks a question about a topic related to stored memories/documents.
3. **System** receives query via `/api/chat/{thread_id}/messages` and `/api/chat/{thread_id}/complete`.
4. **ContextBroker** (in guardian/context/broker.py) retrieves:
   - Recent messages from thread (shallow/normal/deep/diagnostic modes)
   - Semantic search results from vector store (Chroma) for related content
   - Memory entries from long-term store (if deep/diagnostic mode)
   - Optional sensor snapshots (diagnostic only)
5. **System Prompt Builder** assembles a system message from:
   - Immutable base prompt (`_base_codexify_system_prompt`)
   - Active Imprint (style, grammar, name preferences)
   - Active Persona (user-editable behavior text)
   - System Docs (optional knowledge blocks)
   - RAG depth hints
6. **LLM** (Groq/OpenAI/Claude) receives:
   - System message (from builder)
   - Recent conversation history
   - RAG context bundle (semantic + memory results)
7. **Model** responds with answer referencing those memories/documents.
8. **New content** is optionally re-embedded and stored in memory system.
9. **User** sees response with optional RAG trace (visible in deep/diagnostic modes).

#### Current State

**Backend:**
- ✅ ContextBroker class exists (`guardian/context/broker.py`) with 4 depth modes implemented
- ✅ Chat routes exist (`guardian/routes/chat.py`) with `/api/chat/threads`, `/api/chat/{thread_id}/messages`, `/api/chat/{thread_id}/complete`
- ✅ Vector store integration (Chroma) exists (`backend/vector_store/chroma_store.py`)
- ✅ System prompt builder partially done (`codexify/system_prompt_builder.py`)
- ✅ Imprint/Persona stores mostly done (`codexify/imprints/store.py`, `codexify/personas/store.py`)
- ✅ Database models for memory/documents exist (`guardian/db/models.py`)
- ✅ MemoryOS multi-tier memory system exists (`guardian/memoryos/`)
- 🟡 **ISSUE:** Chat completion not wiring ContextBroker → system prompt builder → LLM in a consistent way
- 🟡 **ISSUE:** RAG context not consistently passed to the model
- 🟡 **ISSUE:** Memory store not being populated from new conversations (embeddings not happening)

**Frontend:**
- ✅ GuardianChat component exists (`frontend/src/features/chat/GuardianChat.tsx`)
- ✅ Depth mode selector implemented (shallow/normal/deep/diagnostic)
- ✅ Thread management (create, branch, archive)
- ✅ Message rendering and infinite scroll working
- ✅ RAG trace visibility (trace button, context browser)
- 🟡 **ISSUE:** Depth selector not wired to backend; always defaults to one mode
- 🟡 **ISSUE:** RAG trace not populated; appears empty

#### Gap Analysis – Core Loop Blockers

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|-----------|
| 1. User opens chat | `GuardianChat.tsx` + thread creation | ✅ Works | None |
| 2. User asks question | `Composer` component, message input | ✅ Works | None |
| 3. Query captured | `/api/chat/{thread_id}/messages` POST | ✅ Works | None |
| 4a. ContextBroker retrieves messages | `ContextBroker.assemble()` → `chatlog_db.list_messages()` | ✅ Implemented | None |
| 4b. Semantic search | `ContextBroker.assemble()` → `MemoryOSRetriever.retrieve()` → Chroma | ✅ Implemented | None – BUT vector store may be empty |
| 4c. Memory search | `ContextBroker.assemble()` → memory search | 🟡 Stub only | Need to populate `memory_entry` table from conversations |
| 5. System prompt assembly | `build_guardian_system_prompt()` in `codexify/system_prompt_builder.py` | 🟡 Partially done | Wiring into `/api/chat/{id}/complete` not consistent |
| 6. LLM receives context | `_groq_complete()` in `guardian/core/ai_router.py` | 🟡 Partial | Context bundle not always passed; system prompt assembly fragmented |
| 7. Model responds | `/api/chat/{thread_id}/complete` → LLM → response | 🟡 Partial | Response streaming may not include RAG context info |
| 8. New content embedded | No automatic embedding of new conversation content | 🔴 Missing | Need to embed new messages + auto-link to memory store |
| 9. RAG trace visible | Frontend trace button exists; `setTrace()` in state | 🟡 Partial | Trace not populated from backend; no trace endpoint |

#### Implementation Tasks – Memory/RAG Feature

**Task 1.1:** Wire ContextBroker depth parameter from frontend to backend
- **Files:** `frontend/src/features/chat/GuardianChat.tsx`, `guardian/routes/chat.py`
- **What:** Pass depth mode from depth selector to `/api/chat/{thread_id}/complete` query param
- **Current:** Depth selector exists but value not sent to API
- **Complexity:** S

**Task 1.2:** Ensure RAG context bundle flows into system prompt assembly
- **Files:** `guardian/routes/chat.py`, `codexify/system_prompt_builder.py`
- **What:** In `chat_complete()`, call `ContextBroker.assemble()` and pass result bundle to `build_guardian_system_prompt()`
- **Current:** Partial; `build_guardian_system_prompt()` can accept bundle but not always called with it
- **Complexity:** M

**Task 1.3:** Populate memory store from new conversation messages
- **Files:** `guardian/memoryos/updater.py`, `guardian/routes/chat.py`, vector store
- **What:** After message appended to thread, auto-embed message content and store in vector DB + memory table
- **Current:** No auto-embedding; messages stay in chatlog only
- **Complexity:** M

**Task 1.4:** Surface RAG trace from backend to frontend
- **Files:** `guardian/context/broker.py`, `guardian/routes/chat.py`, frontend state management
- **What:** Return RAG trace dict alongside response; populate frontend trace state (`contextTrace.ts`)
- **Current:** Broker computes trace but it's not returned to client
- **Complexity:** M

**Task 1.5:** Test end-to-end RAG in chat at each depth level
- **Files:** `tests/integration/test_chat_completion_context.py`
- **What:** Create test threads, ask queries, verify ContextBroker returns correct results per depth
- **Current:** Unit tests exist; integration test incomplete
- **Complexity:** S

#### Validation Plan – Memory/RAG Feature

**Manual Test Script:**

1. Start fresh; ensure Chroma DB is empty or reset.
2. Create a thread and send 3–5 messages establishing a topic (e.g., "AI safety").
3. Wait ~5 sec for auto-embedding to complete (logs should show embedding).
4. Send a query: *"What did we say about X?"*
5. Check:
   - ✅ Response references earlier messages (depth=normal mode)
   - ✅ Trace visible shows 4+ semantic results (if available)
   - ✅ Switching to deep mode shows memory entries too
6. Add a document/memory entry manually via API:
   `POST /api/memory` with content about topic.
7. Ask follow-up: *"Given that memory, what about Y?"*
8. Verify response incorporates both conversation + injected memory.

**Automated Tests:**

- **Unit:** `test_context_broker_depth.py` – depth modes return correct result counts
- **Integration:** `test_chat_completion_context.py` – full chat → broker → response flow
- **E2E:** Cypress test for depth selector interaction + RAG trace visibility

---

### 2.2 ChatGPT Migration Tool

#### Core Loop Definition

1. **User** obtains ChatGPT export (JSON from OpenAI dashboard).
2. **User** triggers migration via UI (button in Settings or dedicated page).
3. **System** shows file picker; user selects export file.
4. **Backend** receives file and:
   - Parses JSON structure (conversations, messages, metadata).
   - Normalizes timestamps, user/assistant roles.
   - Embeds messages using embedder.
   - Stores in dual-engine:
     - **Neo4j**: Graph structure (UserNode → ThreadNode → MessageNode).
     - **Chroma**: Vector embeddings for semantic search.
   - Tags all imported content with source metadata (import_timestamp, original_source).
5. **System** logs progress: X% complete, Y messages processed, Z errors.
6. **User** sees confirmation: *"✅ Imported 247 messages into 12 conversations"* with option to review.
7. **Imported content** becomes searchable/retrievable in RAG queries.

#### Current State

**Backend:**
- ✅ CLI tool exists (`scripts/chatgpt_import/cli_migrate.py`) with Rich UI
- ✅ ChatGPT JSON parser exists (`backend/rag/chatgpt_migration.py`)
- ✅ Neo4j import logic exists (`backend/rag/chatgpt_migration.py` → `import_to_neo4j()`)
- ✅ Chroma embedding logic exists (`backend/rag/chatgpt_migration.py` → `import_embeddings_to_chroma()`)
- ✅ Tests exist (`tests/routes/test_imprint_routes.py`, `guardian/tests/migration/`)
- 🔴 **ISSUE:** No HTTP API endpoint for migration (CLI-only)
- 🔴 **ISSUE:** No frontend UI to trigger migration
- 🔴 **ISSUE:** No progress tracking visible to user during import

**Frontend:**
- 🔴 **MISSING:** No migration UI page/modal
- 🔴 **MISSING:** No file upload form
- 🔴 **MISSING:** No progress bar
- 🔴 **MISSING:** No confirmation/review screen

#### Gap Analysis – ChatGPT Migration

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|-----------|
| 1. User accesses migration | CLI only; no UI | 🔴 Missing | Create settings page or dedicated migration UI |
| 2. User selects file | CLI prompts; no HTTP endpoint | 🔴 Missing | Create `/api/migration/upload-chatgpt` endpoint |
| 3. File sent to backend | CLI reads local file only | 🔴 Missing | HTTP endpoint must accept `multipart/form-data` |
| 4a. JSON parsed | `parse_chatgpt_json()` exists | ✅ Implemented | None |
| 4b. Timestamps normalized | `normalize_timestamp()` exists | ✅ Implemented | None |
| 4c. Stored in Neo4j | `import_to_neo4j()` exists | ✅ Implemented | None – but not accessible via HTTP |
| 4d. Stored in Chroma | `import_embeddings_to_chroma()` exists | ✅ Implemented | None – but not accessible via HTTP |
| 5. Progress visible | CLI uses `rich.progress.Progress` | 🟡 Partial | HTTP endpoint needs background job + WebSocket/SSE for progress |
| 6. Confirmation shown | CLI prints summary | 🟡 Partial | Frontend needs summary screen |
| 7. Content searchable | Chroma + Neo4j populated | ✅ Works | None – if steps 4c/4d complete |

#### Implementation Tasks – ChatGPT Migration

**Task 2.1:** Create HTTP API endpoint for ChatGPT migration
- **Files:** `guardian/routes/migration.py` (or new module)
- **What:** `POST /api/migration/upload-chatgpt` accepting multipart file
- **Current:** Only CLI exists
- **Complexity:** M

**Task 2.2:** Implement background job + progress tracking
- **Files:** `guardian/routes/migration.py`, event bus or job queue
- **What:** Queue migration job; expose progress via `/api/migration/status/{job_id}` or WebSocket
- **Current:** CLI is synchronous; no async job handling
- **Complexity:** L

**Task 2.3:** Create frontend UI for migration
- **Files:** `frontend/src/features/settings/MigrationWizard.tsx` or similar
- **What:** Multi-step form: (1) file picker, (2) progress bar, (3) confirmation summary
- **Current:** No UI exists
- **Complexity:** M

**Task 2.4:** Wire frontend to backend
- **Files:** Frontend migration UI, `guardian/routes/migration.py`
- **What:** Upload file, poll or stream progress, show results
- **Current:** No wiring
- **Complexity:** S

**Task 2.5:** Test end-to-end ChatGPT import
- **Files:** Test migration suite
- **What:** Sample ChatGPT export → import → verify in Neo4j + Chroma
- **Current:** CLI tests exist; HTTP API tests need adding
- **Complexity:** S

#### Validation Plan – ChatGPT Migration

**Manual Test Script:**

1. Obtain sample ChatGPT export JSON (or create minimal mock).
2. Open Settings → Migration section.
3. Click "Import ChatGPT Conversations".
4. Select export file.
5. Confirm:
   - ✅ Progress bar appears and increments
   - ✅ Estimated time shown
   - ✅ No UI freeze (background job)
6. Wait for completion.
7. Confirm summary: *"Imported X conversations, Y messages"*
8. Query chat with depth=deep; confirm imported content shows up in RAG results.
9. Check Neo4j/Chroma directly: `curl localhost:7687/...` or Chroma UI.

**Automated Tests:**

- **Unit:** Parsing, timestamp normalization tests
- **Integration:** HTTP upload → Neo4j/Chroma population
- **E2E:** Full migration workflow in test

---

### 2.3 Upload Documents + Embed

#### Core Loop Definition

1. **User** opens Documents view or Composer in chat.
2. **User** clicks "Upload" button or drags file (PDF, MD, TXT, DOCX).
3. **Frontend** (`useUploader` hook) reads file, converts to base64.
4. **Frontend** dispatches `cfy:documents:upload` event with file metadata.
5. **Backend** receives upload via `/api/media/upload-document`:
   - Stores file (filesystem or S3).
   - Parses content (text extraction from PDF if applicable).
   - Embeds parsed text into vector store.
   - Creates `UploadedDocument` DB row with source + metadata.
6. **System** tags document with:
   - Upload timestamp
   - Source (user/connector)
   - Optional project/thread association
7. **Document** becomes retrievable in RAG queries (semantic search).
8. **User** sees confirmation: *"✅ Document added to memory"* with preview.
9. **Next query** in chat retrieves and references uploaded document.

#### Current State

**Backend:**
- ✅ Upload route exists (`guardian/routes/media.py` → `upload_document()`)
- ✅ Storage abstraction exists (`guardian/core/storage.py`)
- ✅ File parsing exists (text extraction, MIME detection)
- ✅ Database model for uploaded docs exists (`guardian/db/models.py::UploadedDocument`)
- 🟡 **ISSUE:** Route doesn't automatically embed document into vector store
- 🟡 **ISSUE:** No link created to thread/project
- 🟡 **ISSUE:** `/api/embeddings` endpoint may not exist or be incomplete

**Frontend:**
- ✅ `useUploader` hook exists and works (`frontend/src/hooks/useUploader.ts`)
- ✅ Calls `/api/embeddings` on text files (but this endpoint may not exist)
- ✅ Dispatches `cfy:documents:add` event for UI updates
- 🟡 **ISSUE:** No confirmation that document was embedded; UI doesn't show memory status
- 🟡 **ISSUE:** No preview of uploaded content

#### Gap Analysis – Document Upload

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|-----------|
| 1. User opens UI | Documents view + Composer | ✅ Works | None |
| 2. User triggers upload | Uploader button/drag-drop | ✅ Works | None |
| 3. File read (frontend) | `useUploader.handleFiles()` → FileReader | ✅ Works | None |
| 4. Event dispatched | `cfy:documents:upload` event | ✅ Works | None |
| 5a. File received (backend) | `/api/media/upload-document` | ✅ Works | None |
| 5b. File stored | `StorageManager.save()` | ✅ Works | None |
| 5c. Content parsed | PDF/MD/TXT extraction | ✅ Works | None |
| 5d. **Content embedded** | No embedding call in route | 🔴 **Missing** | Call embedder + store in vector DB |
| 6. Metadata tagged | DB row created but minimal metadata | 🟡 Partial | Ensure project_id, thread_id, tags stored |
| 7. Retrievable in RAG | If vector DB populated, yes | 🟡 Depends on 5d | Completion of 5d fixes this |
| 8. Confirmation shown | No real confirmation; just UI event | 🟡 Partial | Backend should return status; frontend should show success + preview |
| 9. Used in next query | Only if step 7 works | 🟡 Depends | Completion of 5d, 7 fixes this |

#### Implementation Tasks – Document Upload

**Task 3.1:** Add embedding call to upload-document route
- **Files:** `guardian/routes/media.py`
- **What:** After parsing, embed chunks into vector store (Chroma); store embeddings with source metadata
- **Current:** Route stores file but doesn't embed
- **Complexity:** S

**Task 3.2:** Link uploaded document to thread/project
- **Files:** `guardian/routes/media.py`, `guardian/db/models.py`
- **What:** Accept optional `thread_id`, `project_id` in upload request; create `ThreadDocument` link
- **Current:** Not linked
- **Complexity:** S

**Task 3.3:** Create `/api/embeddings` endpoint (if not present)
- **Files:** `guardian/routes/` (new or existing)
- **What:** POST endpoint accepting text; returns embedding vector (for frontend usage or manual embedding)
- **Current:** Frontend calls it but unclear if implemented
- **Complexity:** S

**Task 3.4:** Improve frontend feedback
- **Files:** `frontend/src/hooks/useUploader.ts`, Document components
- **What:** Show upload success with preview, embedding status, memory system confirmation
- **Current:** Just shows generic "uploaded" message
- **Complexity:** S

**Task 3.5:** Test document upload → RAG integration
- **Files:** Test suite
- **What:** Upload doc → query chat → verify content in RAG results
- **Current:** No integration tests
- **Complexity:** S

#### Validation Plan – Document Upload

**Manual Test Script:**

1. Create a markdown file: `test.md` with content about a specific topic.
2. Open Documents view.
3. Click upload; select `test.md`.
4. Confirm:
   - ✅ Success message appears
   - ✅ Document listed in Documents view
   - ✅ File size shown
5. Open Chat.
6. Ask a question about the topic in the document.
7. Set depth=normal or deep.
8. Confirm:
   - ✅ Response references the uploaded document
   - ✅ RAG trace shows document in results

**Automated Tests:**

- **Unit:** File parsing, chunk creation
- **Integration:** Upload → embedding → retrieval in ContextBroker
- **E2E:** Upload form → chat query → RAG results

---

### 2.4 Upload Images to Gallery

#### Core Loop Definition

1. **User** opens Gallery view or Composer.
2. **User** clicks "Upload" button or drags image file (PNG, JPG, WEBP).
3. **Frontend** reads image, converts to data URL or sends file.
4. **Backend** receives image via `/api/media/upload-image`:
   - Stores image file (filesystem or S3).
   - Generates UUID for image ID.
   - Creates `UploadedImage` DB row with metadata (filename, MIME type, created_at).
5. **System** returns image URL.
6. **Frontend** receives URL and updates Gallery view.
7. **User** sees image in Gallery with thumbnail and metadata.
8. **User** can click image to view full size or open in thread.

#### Current State

**Backend:**
- ✅ Upload route exists (`guardian/routes/media.py` → `upload_image()`)
- ✅ Storage system works
- ✅ Database model exists (`guardian/db/models.py::UploadedImage`)
- ✅ File retrieval route exists (`get_image()`)
- ✅ Delete route exists
- ✅ List images route exists (`list_images()`)

**Frontend:**
- ✅ Gallery component exists (`GalleryView.tsx`)
- ✅ Uploader hook works for images
- ✅ Displays demo gallery items
- 🟡 **ISSUE:** Gallery not pulling from backend; only shows demo/hardcoded items
- 🟡 **ISSUE:** No integration with uploaded images from backend API

#### Gap Analysis – Image Upload

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|-----------|
| 1. User opens gallery | `GalleryView.tsx` | ✅ Works | None |
| 2. User uploads | Uploader in Composer/Documents | ✅ Works | None |
| 3. Image read | `useUploader.handleFiles()` | ✅ Works | None |
| 4a. Backend receives | `/api/media/upload-image` | ✅ Works | None |
| 4b. Stored | `StorageManager.save()` | ✅ Works | None |
| 4c. DB row created | `UploadedImage` model | ✅ Works | None |
| 5. URL returned | Response includes `src_url` | ✅ Works | None |
| 6. Frontend updates | `cfy:gallery:add` event dispatched | ✅ Works | None |
| 7. Gallery displays | `GalleryView` only shows demo items | 🟡 **ISSUE** | Gallery needs to fetch + display real uploaded images from backend |
| 8. User interaction | View/delete buttons exist but logic incomplete | 🟡 Partial | Wire gallery interactions to API |

#### Implementation Tasks – Image Gallery

**Task 4.1:** Wire Gallery to fetch images from backend
- **Files:** `frontend/src/components/gallery/GalleryView.tsx`
- **What:** On component load, call `GET /api/media/images` to fetch uploaded images; merge with demo
- **Current:** Only shows hardcoded demo images
- **Complexity:** S

**Task 4.2:** Display uploaded images in gallery grid
- **Files:** `GalleryView.tsx`
- **What:** Render thumbnails for uploaded images; show metadata (filename, created_at)
- **Current:** Demo-only
- **Complexity:** S

**Task 4.3:** Wire image selection/viewing
- **Files:** `GalleryView.tsx`, modal or lightbox component
- **What:** Click image → view full size; option to open in thread or copy URL
- **Current:** Stub only
- **Complexity:** S

**Task 4.4:** Test image upload → gallery display
- **Files:** Test suite
- **What:** Upload image → verify appears in gallery
- **Current:** No tests
- **Complexity:** S

#### Validation Plan – Image Gallery

**Manual Test Script:**

1. Select an image file (PNG or JPG).
2. Open Composer in Chat.
3. Click upload image button.
4. Select file and confirm upload.
5. Confirm:
   - ✅ Success message shown
   - ✅ Image appears in Gallery view as thumbnail
   - ✅ Metadata (filename, size) visible
6. Click image to view full size.
7. Confirm full image displayed clearly.

**Automated Tests:**

- **Unit:** Image file validation, MIME type detection
- **Integration:** Upload → DB → retrieval in list endpoint
- **E2E:** Upload form → gallery display

---

### 2.5 Generate Images

#### Core Loop Definition

1. **User** opens Gallery, Chat, or dedicated Generation panel.
2. **User** clicks "Generate Image" button.
3. **Frontend** shows modal with text input for image prompt.
4. **User** types prompt and clicks "Generate".
5. **Backend** receives request via `/api/media/generate-image`:
   - Validates prompt (length, content filters if applicable).
   - Sends to image provider (DALL-E, Stability, Ollama, etc.) based on configuration.
   - Waits for generated image.
6. **Generated image** is:
   - Stored to filesystem/S3.
   - `GeneratedImage` DB row created with source model, prompt, generation_time.
   - UUID assigned.
7. **System** returns image URL + metadata.
8. **Frontend** receives URL and shows generated image in modal.
9. **User** confirms image; it's added to Gallery.
10. **Next time** Gallery is opened, generated image is visible.

#### Current State

**Backend:**
- ✅ Route exists (`guardian/routes/media.py` → `generate_image()`)
- ✅ Database model exists (`GeneratedImage`)
- 🔴 **ISSUE:** Provider integration incomplete (stubs only; no real API calls)
- 🔴 **ISSUE:** No default provider configured
- 🔴 **ISSUE:** Route may fail if provider not set up

**Frontend:**
- ✅ Modal exists (`ImageGenModal.tsx`)
- ✅ Prompt input works
- ✅ Calls `/api/media/generate-image`
- 🟡 **ISSUE:** Hardcoded default `project_id=1`, `thread_id=1`, `user_id="default"`
- 🟡 **ISSUE:** No error handling for provider unavailable
- 🟡 **ISSUE:** No loading spinner (generating can take 5–30 sec)

#### Gap Analysis – Image Generation

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|-----------|
| 1. User opens UI | Modal in Composer, Gallery, etc. | ✅ Works | None |
| 2. User submits prompt | Modal form with textarea | ✅ Works | None |
| 3. Backend receives | `/api/media/generate-image` | ✅ Works | None |
| 4a. Prompt validated | Basic length check | ✅ Works | None |
| 4b. **Provider called** | Stub only; no real API integration | 🔴 **Missing** | Configure provider (DALL-E or Ollama) + make real request |
| 5. Image generated | Depends on 4b | 🔴 Blocked | Completion of 4b required |
| 6a. Image stored | `StorageManager.save()` exists | ✅ Works | Depends on 4b |
| 6b. DB row created | `GeneratedImage` model | ✅ Works | Depends on 4b |
| 7. URL returned | Response includes `src_url` | ✅ Works | Depends on 4b |
| 8. Frontend shows | Modal displays image | ✅ Works | Depends on 4b |
| 9. Added to gallery | `cfy:gallery:add` event | ✅ Works | Depends on 4b |
| 10. Gallery updated | If step 4.1 completed | 🟡 Partial | Depends on task 4.1 |

#### Implementation Tasks – Image Generation

**Task 5.1:** Configure image provider
- **Files:** `guardian/core/config.py`, `.env`
- **What:** Choose provider (DALL-E, Stability, Ollama, etc.); store API key; create client
- **Current:** No provider configured
- **Complexity:** S (assuming one provider choice; L if supporting multiple)

**Task 5.2:** Implement provider API integration
- **Files:** `guardian/routes/media.py` or new `guardian/services/image_generation.py`
- **What:** Call provider with prompt; wait for image; handle errors
- **Current:** Stub only
- **Complexity:** M (depends on provider complexity)

**Task 5.3:** Improve frontend UX
- **Files:** `ImageGenModal.tsx`
- **What:** Show loading spinner; better error handling; pass real user/project/thread context
- **Current:** Basic modal; hardcoded IDs
- **Complexity:** S

**Task 5.4:** Test image generation
- **Files:** Test suite
- **What:** Mock provider; test request → response flow
- **Current:** No tests
- **Complexity:** S

#### Validation Plan – Image Generation

**Manual Test Script (Requires Provider Setup):**

1. Configure provider (e.g., set `OPENAI_API_KEY` for DALL-E).
2. Start backend.
3. Open Gallery or Chat → click "Generate Image".
4. Enter prompt: *"A serene mountain landscape at sunset"*.
5. Click "Generate".
6. Confirm:
   - ✅ Loading spinner appears
   - ✅ After 10–30 sec, image appears
   - ✅ No error message (unless provider actually fails)
7. Confirm:
   - ✅ Image added to Gallery on refresh
   - ✅ Metadata (prompt, generation_time) stored

**Automated Tests:**

- **Unit:** Prompt validation
- **Mock Integration:** Provider mocked; test request/response flow
- **E2E:** Full generation workflow (with mock provider)

---

### 2.6 Generate Documents (Code, Literature, Diagrams)

#### Core Loop Definition

1. **User** opens "Generate" panel or button in Chat.
2. **User** selects document type (e.g., "Code Snippet", "Narrative", "Outline/Diagram").
3. **User** enters a prompt describing what to generate.
4. **User** optionally sets parameters (language for code, tone for narrative, etc.).
5. **Backend** receives request via `/api/media/generate-document`:
   - Selects appropriate system prompt for document type.
   - Sends prompt + context to LLM (Claude, GPT, etc.).
   - Waits for generation.
6. **Generated document** is:
   - Stored as file (filesystem/S3) or DB row (`GeneratedDocument`).
   - Tagged with source model, generation_time, document_type, prompt.
7. **System** returns document URL + preview.
8. **Frontend** shows generated content inline or opens editor.
9. **User** can:
   - View/edit document
   - Save to workspace or export
   - Re-generate with modified prompt
10. **Document** is searchable/retrievable in future RAG queries if content is relevant.

#### Current State

**Backend:**
- ✅ Route stub exists (`guardian/routes/media.py` → `generate_document()` placeholder)
- ✅ Database model exists (`GeneratedDocument`)
- 🔴 **ISSUE:** No implementation; function likely returns stub error
- 🔴 **ISSUE:** No document type differentiation (code vs. narrative vs. diagram)
- 🔴 **ISSUE:** No system prompt template per document type

**Frontend:**
- 🔴 **MISSING:** No UI component for document generation
- 🔴 **MISSING:** No document type selector
- 🔴 **MISSING:** No prompt input form
- 🔴 **MISSING:** No generated document viewer/editor

#### Gap Analysis – Document Generation

| Loop Step | Current Implementation | Gap / Problem | Fix Needed |
|-----------|------------------------|---------------|-----------|
| 1. User opens UI | None exists | 🔴 **Missing** | Create Generation panel or modal |
| 2. Select type | No UI | 🔴 **Missing** | Add document type selector (code/narrative/outline) |
| 3. Enter prompt | No UI | 🔴 **Missing** | Create text input for generation prompt |
| 4. Set parameters | No UI | 🔴 **Missing** | Optional language/tone/style inputs |
| 5. Backend receives | Route stub exists | 🟡 Incomplete | Implement generation logic |
| 6a. System prompt | No type-specific prompts | 🔴 **Missing** | Create prompt templates per document type |
| 6b. **LLM called** | No implementation | 🔴 **Missing** | Use existing LLM routing (ai_router.py) |
| 7. Document stored | DB model exists | 🟡 Partial | Wire to actual storage |
| 8. Frontend shows | No UI | 🔴 **Missing** | Create viewer/editor component |
| 9. User actions | No UI | 🔴 **Missing** | Save, export, re-generate buttons |
| 10. Retrievable in RAG | Could work if #7 done + document embedded | 🟡 Depends | Depends on completing prior steps + task 3.1 (embedding) |

#### Implementation Tasks – Document Generation

**Task 6.1:** Create frontend UI for document generation
- **Files:** `frontend/src/components/modals/DocumentGenModal.tsx` or `frontend/src/features/generation/DocumentGenerator.tsx`
- **What:** Modal/panel with document type selector, prompt input, parameters
- **Current:** No UI
- **Complexity:** M

**Task 6.2:** Implement backend document generation route
- **Files:** `guardian/routes/media.py`, new `guardian/services/document_generation.py`
- **What:** Accept document type + prompt; call LLM with type-specific system prompt; return generated content
- **Current:** Stub only
- **Complexity:** M

**Task 6.3:** Create system prompt templates per document type
- **Files:** `codexify/prompts.py` or new `codexify/generation_prompts.py`
- **What:** Three templates: code (focus: syntax, completeness), narrative (focus: coherence, tone), outline (focus: structure, clarity)
- **Current:** None
- **Complexity:** S

**Task 6.4:** Wire document storage and retrieval
- **Files:** `guardian/routes/media.py`, `GuardianDB`
- **What:** Store generated content in DB; return document ID; allow viewing/editing
- **Current:** Model exists but not wired
- **Complexity:** S

**Task 6.5:** Create document viewer/editor
- **Files:** `frontend/src/components/DocumentViewer.tsx` or similar
- **What:** Display generated document; allow inline editing; save/export buttons
- **Current:** No component
- **Complexity:** M

**Task 6.6:** Test document generation end-to-end
- **Files:** Test suite
- **What:** Request generation → backend → LLM → storage → retrieve and display
- **Current:** No tests
- **Complexity:** M

#### Validation Plan – Document Generation

**Manual Test Script:**

1. Open Generation panel.
2. Select "Code Snippet".
3. Enter prompt: *"Python function to calculate fibonacci"*.
4. Click "Generate".
5. Confirm:
   - ✅ Loading indicator
   - ✅ After 5–10 sec, code appears in editor
   - ✅ Code syntax-highlighted (Python)
6. Test other types:
   - Select "Narrative" → *"Story about an AI waking up"* → confirm prose generated
   - Select "Outline" → *"Outline for MVP roadmap"* → confirm structured outline
7. Click "Save to Workspace".
8. Confirm:
   - ✅ Document appears in Documents view
   - ✅ File downloadable
9. Edit generated document; click "Save".
10. Confirm:
    - ✅ Changes persisted
    - ✅ Document shows "Edited" timestamp

**Automated Tests:**

- **Unit:** Prompt template rendering
- **Mock Integration:** LLM calls mocked; test request/response flow
- **E2E:** Full generation → storage → retrieval workflow

---

## 3. Milestones & Implementation Roadmap

### Philosophy
- **Milestone 0:** Fix blockers / wiring issues that prevent core loops from closing
- **Milestone 1–6:** Implement the 6 core features in order of dependency and effort
- **Definition of "Done":** Feature loop closes end-to-end + passes validation test

### Milestone 0: Blockers & Infrastructure (Effort: 1 week)

**Objective:** Unblock downstream milestones by fixing critical wiring issues.

#### Tasks

1. **0.1** – Verify PostgreSQL + Chroma are running
   - Start containers: `docker-compose up postgres chroma`
   - Confirm migrations applied: `python -m alembic upgrade head`
   - Complexity: S

2. **0.2** – Wire depth mode from frontend to backend
   - Pass `depth` query param in `/api/chat/{thread_id}/complete`
   - Ensure backend ContextBroker uses it
   - Test: depth selector changes result count in RAG
   - Complexity: S

3. **0.3** – Verify LLM provider is configured
   - Check `.env` for `OPENAI_API_KEY` or `GROQ_API_KEY`
   - Test: `curl /api/chat/{id}/complete` → returns LLM response (or error if key missing)
   - Complexity: S

4. **0.4** – Populate vector store with test data
   - Create sample documents in Chroma (or run embedder on dummy messages)
   - Verify `/api/rag/search` returns results
   - Complexity: S

#### Exit Criteria
- ✅ Depth selector functional (shallow/normal/deep/diagnostic modes work)
- ✅ LLM responds to chat completions (with or without RAG)
- ✅ Vector store is non-empty and searchable

---

### Milestone 1: Memory/RAG + Context Broker + Guardian Chat (Effort: 2 weeks)

**Objective:** Close the core loop for RAG-enhanced chat with full depth support and memory population.

#### Tasks

1. **1.1** – Wire ContextBroker depth parameter (Task 1.1)
   - Frontend depth selector → backend query param
   - Complexity: S

2. **1.2** – Ensure RAG bundle flows into system prompt (Task 1.2)
   - `chat_complete()` calls `ContextBroker.assemble()` and passes bundle to `build_guardian_system_prompt()`
   - Complexity: M

3. **1.3** – Auto-embed new messages into memory (Task 1.3)
   - After message appended to thread, embed it into vector store
   - Create `MemoryEntry` row
   - Complexity: M

4. **1.4** – Surface RAG trace to frontend (Task 1.4)
   - Return trace dict from `/api/chat/{id}/complete`
   - Populate frontend trace state
   - Complexity: M

5. **1.5** – Test end-to-end RAG (Task 1.5)
   - Integration test: thread → query → ContextBroker → response with trace
   - Complexity: S

#### Exit Criteria
- ✅ User asks question; response includes RAG-sourced content
- ✅ Depth mode selector changes results (shallow < normal < deep < diagnostic)
- ✅ RAG trace visible (semantic + memory results shown)
- ✅ New messages auto-embedded and searchable in next query

---

### Milestone 2: ChatGPT Migration Tool (Effort: 2 weeks)

**Objective:** Users can import ChatGPT conversations via UI with progress visibility.

#### Tasks

1. **2.1** – Create HTTP API endpoint (Task 2.1)
   - `POST /api/migration/upload-chatgpt` accepting file
   - Complexity: M

2. **2.2** – Implement background job + progress (Task 2.2)
   - Queue migration; expose status endpoint
   - Complexity: L

3. **2.3** – Create frontend migration UI (Task 2.3)
   - Multi-step form: file picker → progress → confirmation
   - Complexity: M

4. **2.4** – Wire frontend to backend (Task 2.4)
   - Upload file; poll progress; display results
   - Complexity: S

5. **2.5** – Test ChatGPT import (Task 2.5)
   - Sample export → import → verify in RAG
   - Complexity: S

#### Exit Criteria
- ✅ User can upload ChatGPT export via Settings UI
- ✅ Progress bar visible during import
- ✅ Imported conversations searchable in RAG queries
- ✅ No data loss or corruption during import

---

### Milestone 3: Upload Documents + Embed (Effort: 1.5 weeks)

**Objective:** Users can upload documents (PDF, MD, TXT, DOCX) and retrieve them in RAG queries.

#### Tasks

1. **3.1** – Add embedding to upload-document route (Task 3.1)
   - Embed parsed content into vector store
   - Complexity: S

2. **3.2** – Link document to thread/project (Task 3.2)
   - Accept optional `thread_id`, `project_id`; create `ThreadDocument` link
   - Complexity: S

3. **3.3** – Create `/api/embeddings` endpoint (Task 3.3)
   - POST endpoint accepting text; return embeddings
   - Complexity: S

4. **3.4** – Improve frontend feedback (Task 3.4)
   - Show upload success with preview + memory status
   - Complexity: S

5. **3.5** – Test document upload + RAG (Task 3.5)
   - Upload doc → query chat → verify in RAG results
   - Complexity: S

#### Exit Criteria
- ✅ User uploads document; it appears in Documents view
- ✅ Document retrievable in RAG queries at normal/deep depth
- ✅ Frontend shows memory status (embedding in progress / complete)

---

### Milestone 4: Upload Images to Gallery (Effort: 1 week)

**Objective:** Users can upload images and view them in Gallery.

#### Tasks

1. **4.1** – Wire Gallery to fetch from backend (Task 4.1)
   - `GET /api/media/images` → fetch uploaded images
   - Complexity: S

2. **4.2** – Display images in gallery grid (Task 4.2)
   - Render thumbnails + metadata
   - Complexity: S

3. **4.3** – Wire image interactions (Task 4.3)
   - Click to view, delete, copy URL
   - Complexity: S

4. **4.4** – Test image upload + gallery (Task 4.4)
   - Upload image → appears in gallery
   - Complexity: S

#### Exit Criteria
- ✅ User uploads image; appears in Gallery immediately
- ✅ Thumbnail + metadata (filename, size) displayed
- ✅ Can view full-size image
- ✅ Can delete image from gallery

---

### Milestone 5: Generate Images (Effort: 1 week)

**Objective:** Users can generate images via modal; images stored and accessible in Gallery.

#### Tasks

1. **5.1** – Configure image provider (Task 5.1)
   - Choose provider (DALL-E, Stability, Ollama); set API key
   - Complexity: S

2. **5.2** – Implement provider integration (Task 5.2)
   - Call provider; handle response; store image
   - Complexity: M

3. **5.3** – Improve frontend UX (Task 5.3)
   - Loading spinner; error handling; real context (user/project)
   - Complexity: S

4. **5.4** – Test image generation (Task 5.4)
   - Mock provider; test request/response flow
   - Complexity: S

#### Exit Criteria
- ✅ User enters prompt; image generated in 5–30 sec
- ✅ Generated image stored and appears in Gallery
- ✅ Can regenerate with modified prompt
- ✅ No errors if provider temporarily unavailable (graceful fallback)

---

### Milestone 6: Generate Documents (Code, Literature, Diagrams) (Effort: 2 weeks)

**Objective:** Users can generate code, narrative, or outline documents; documents viewable and editable.

#### Tasks

1. **6.1** – Create frontend UI (Task 6.1)
   - Document type selector; prompt input; parameters
   - Complexity: M

2. **6.2** – Implement backend generation (Task 6.2)
   - Accept type + prompt; call LLM; store result
   - Complexity: M

3. **6.3** – Create system prompts per type (Task 6.3)
   - Code, narrative, outline templates
   - Complexity: S

4. **6.4** – Wire storage + retrieval (Task 6.4)
   - Store generated content; return for viewing/editing
   - Complexity: S

5. **6.5** – Create document viewer/editor (Task 6.5)
   - Display generated content; edit; save; export
   - Complexity: M

6. **6.6** – Test document generation (Task 6.6)
   - Request generation → storage → retrieval
   - Complexity: M

#### Exit Criteria
- ✅ User selects document type; enters prompt; document generated
- ✅ Generated document displayed inline with syntax highlighting (for code)
- ✅ Can edit and save modified document
- ✅ Document appears in Documents view
- ✅ Can export document

---

## 4. Risks, Assumptions & Dependencies

### Assumptions

1. **PostgreSQL is running** and schema is migrated (Alembic)
2. **Chroma vector store** is operational (or pgvector backend configured)
3. **At least one LLM provider** is configured and API keys available (Groq, OpenAI, Claude)
4. **Frontend and backend** are on same or CORS-friendly domains
5. **File storage** (filesystem or S3) is accessible by backend
6. **User can run `docker-compose`** or has manual service setup

### Dependencies

- **Milestone 0** must complete before any other milestone
- **Milestone 1** must complete before **Milestone 2** (RAG needed to ingest ChatGPT)
- **Milestones 3–6** can run in parallel after Milestone 1
- **Milestone 5** requires image provider API key
- **Milestone 6** requires LLM provider already working (from Milestone 1)

### Known Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| LLM provider API unavailable | M | Graceful fallback; cache responses; use Groq as fallback if OpenAI down |
| Vector store (Chroma) corruption | H | Backup Chroma data; implement versioning; test recovery procedure |
| Long documents fail to parse/embed | M | Chunking strategy; size limits; error logging |
| Image generation timeout (30+ sec) | M | Timeout handling; queuing strategy; async jobs |
| Migration from ChatGPT loses metadata | M | Test with real ChatGPT exports; validate timestamp/user consistency |
| Frontend/backend version mismatch | M | Versioned API endpoints; compatibility tests |

---

## 5. Deferred Features (Post-MVP Parking Lot)

These are valuable but **NOT** MVP-critical. Defer to v1.1 or v2.

### 5.1 Realtime Collaboration

**What:** Multiple users editing same thread simultaneously; WebSocket sync.
**Status:** WebSocket scaffolding exists in codebase.
**Defer To:** v1.1
**Effort:** L

### 5.2 Federation / Peer Sync

**What:** Sync conversations across federated Codexify instances.
**Status:** Routes + trust engine partially implemented.
**Defer To:** v2.0
**Effort:** XL

### 5.3 Connectors (Notion, Google, Slack, GitHub)

**What:** Ingest data from external services into Codexify memory.
**Status:** Connector routes exist; no implementation.
**Defer To:** v1.1
**Effort:** L (per connector)

### 5.4 Text-to-Speech (TTS)

**What:** Synthesize responses to audio.
**Status:** Route exists (`POST /api/media/tts`); no provider integration.
**Defer To:** v1.1
**Effort:** S

### 5.5 GraphQL API

**What:** Alternative to REST for complex queries.
**Status:** Not started.
**Defer To:** v2.0
**Effort:** L

### 5.6 Plugins / Custom Extensions

**What:** Allow users to extend Codexify with custom logic.
**Status:** Not started.
**Defer To:** Post-v1.0
**Effort:** XL

### 5.7 Advanced RAG (Re-Ranking, Fusion)

**What:** Sophisticated ranking of semantic results; multi-modal fusion.
**Status:** Not started.
**Defer To:** v1.1
**Effort:** L

### 5.8 Diary & Identity Persistence

**What:** Track evolution of Guardian identity over time.
**Status:** Database flags exist; UI not built.
**Defer To:** v1.1
**Effort:** M

---

## 6. Testing Strategy – Full Coverage Map

### Test Organization

```
tests/
├── core/
│   ├── test_context_broker_depth.py       # RAG depth modes
│   └── test_system_prompt_builder.py     # Prompt assembly
├── integration/
│   ├── test_chat_completion_context.py   # Chat + RAG + system prompt
│   └── test_migration_end_to_end.py      # ChatGPT import → RAG
├── routes/
│   ├── test_chat_routes.py               # Chat API endpoints
│   ├── test_media_routes.py              # Image + document upload/generation
│   ├── test_imprint_routes.py            # Imprint/persona APIs
│   └── test_migration_routes.py          # Migration HTTP endpoint
└── e2e/
    ├── test_rag_chat_loop.cy.ts          # Full chat + RAG loop (Cypress)
    └── test_migration_ui.cy.ts           # Migration UI workflow
```

### MVP Test Coverage

#### Unit Tests (Fast, Isolated)

- **ContextBroker depth modes** (`test_context_broker_depth.py`)
  - ✅ Existing; comprehensive (depth selection + result counts)

- **System prompt builder** (`test_system_prompt_builder.py`)
  - ✅ Existing; covers imprint + persona + system docs

- **Imprint/persona stores** (`codexify/imprints/store.py`, etc.)
  - ✅ Existing; CRUD tests

- **Image/document upload** (new `test_media_routes.py`)
  - File parsing (PDF, MD, TXT)
  - MIME type detection
  - Storage backend interaction

- **ChatGPT parser** (existing `tests/migrations/`)
  - ✅ Existing; roundtrip tests

#### Integration Tests (Database + Services)

- **Chat + RAG + system prompt** (`test_chat_completion_context.py`)
  - 🟡 Existing but incomplete; needs update to verify embedding flow

- **Document upload + embedding + RAG** (new)
  - Upload document → parse → embed → search in chat

- **ChatGPT migration + RAG** (new `test_migration_end_to_end.py`)
  - Upload export → Neo4j + Chroma → search results

- **Image upload + gallery listing** (new)
  - Upload → DB → list → frontend display

- **Image generation** (new, with mocked provider)
  - Request → LLM → storage → retrieval

#### E2E Tests (Full Workflow, UI + Backend)

- **Chat + RAG loop** (`test_rag_chat_loop.cy.ts`, Cypress)
  1. Create thread
  2. Send message
  3. Set depth mode
  4. Verify RAG results in response
  5. Check trace visibility

- **ChatGPT migration UI** (`test_migration_ui.cy.ts`)
  1. Open Settings → Migration
  2. Upload sample export
  3. Verify progress bar
  4. Confirm completion summary
  5. Ask chat question; verify imported content in RAG results

- **Document upload + search** (new)
  1. Open Documents view
  2. Upload file
  3. Open Chat
  4. Ask question about file content
  5. Verify RAG results include uploaded document

- **Image generation + gallery** (new, with mocked provider)
  1. Open Gallery
  2. Click "Generate Image"
  3. Enter prompt, generate
  4. Verify image appears in gallery
  5. Refresh page; image still there

### Test Execution

```bash
# Unit tests only (fast)
pytest tests/core tests/system_prompt -xvs

# Integration tests (slower, requires DB)
pytest tests/integration -xvs

# E2E tests (requires frontend running)
cypress run --spec "tests/e2e/**"

# Full test suite
make test
```

---

## 7. Validation Checklist – MVP Definition

**To declare MVP "complete", these must all pass:**

### Memory/RAG + Context Broker

- [ ] User asks question; response includes RAG-sourced content
- [ ] Depth selector (shallow/normal/deep/diagnostic) changes result quality
- [ ] RAG trace visible with semantic + memory sources
- [ ] New messages auto-embedded and retrievable in next query
- [ ] Passes integration test: `test_chat_completion_context.py`

### ChatGPT Migration Tool

- [ ] User can upload ChatGPT export via Settings UI
- [ ] Progress bar visible during import
- [ ] Import completes without data loss
- [ ] Imported conversations searchable in RAG queries at deep depth
- [ ] Passes E2E test: `test_migration_ui.cy.ts`

### Upload Documents + Embed

- [ ] User uploads PDF/MD/TXT; appears in Documents view
- [ ] Uploaded document is embedded and retrievable in RAG
- [ ] Chat query retrieves uploaded document content
- [ ] Multiple documents searchable (semantic + full-text)
- [ ] Passes integration test: document upload + embedding + retrieval

### Upload Images to Gallery

- [ ] User uploads image; appears in Gallery with thumbnail
- [ ] Image metadata (filename, size, upload_time) displayed
- [ ] Can view full-size image
- [ ] Can delete image (soft delete in DB)
- [ ] Uploaded images persist after page refresh
- [ ] Passes E2E test: `test_image_upload_gallery.cy.ts`

### Generate Images

- [ ] User can open "Generate Image" modal
- [ ] User enters prompt; image generated in <30 sec
- [ ] Generated image stored and appears in Gallery
- [ ] Can regenerate with modified prompt
- [ ] Graceful error if provider unavailable
- [ ] Passes mock integration test: image generation workflow

### Generate Documents (Code, Literature, Diagrams)

- [ ] User can select document type (code/narrative/outline)
- [ ] User enters prompt; document generated
- [ ] Generated document displayed with appropriate formatting
- [ ] Can edit and save modified document
- [ ] Document appears in Documents view
- [ ] Can export document
- [ ] Passes integration test: document generation workflow

---

## 8. Quick Reference – File Mapping

### Backend Core Files

| File | Purpose | Status |
|------|---------|--------|
| `guardian/context/broker.py` | RAG depth modes | ✅ Works |
| `guardian/routes/chat.py` | Chat API endpoints | 🟡 Partial |
| `codexify/system_prompt_builder.py` | System prompt assembly | 🟡 Partial |
| `codexify/imprints/store.py` | Imprint persistence | ✅ Works |
| `codexify/personas/store.py` | Persona persistence | ✅ Works |
| `guardian/routes/media.py` | Image/document upload routes | 🟡 Partial |
| `scripts/chatgpt_import/cli_migrate.py` | ChatGPT migration CLI | ✅ Works |
| `guardian/routes/migration.py` | Migration HTTP endpoint | 🔴 Missing |
| `guardian/memoryos/memoryos.py` | Memory system | ✅ Works |
| `backend/vector_store/chroma_store.py` | Vector DB integration | ✅ Works |

### Frontend Core Files

| File | Purpose | Status |
|------|---------|--------|
| `frontend/src/features/chat/GuardianChat.tsx` | Main chat component | ✅ Works |
| `frontend/src/features/chat/ChatView.tsx` | Message rendering | ✅ Works |
| `frontend/src/features/chat/components/Composer.tsx` | Message input + upload | ✅ Works |
| `frontend/src/hooks/useUploader.ts` | File upload hook | ✅ Works |
| `frontend/src/components/gallery/GalleryView.tsx` | Gallery display | 🟡 Partial |
| `frontend/src/components/modals/ImageGenModal.tsx` | Image generation modal | 🟡 Partial |
| `frontend/src/components/documents/DocumentsView.tsx` | Documents list | ✅ Works |
| `frontend/src/imprint/ImprintZeroToast.tsx` | Identity onboarding | ✅ Works |

### Database Models

| Model | Purpose | Status |
|-------|---------|--------|
| `ChatThread` | Conversation container | ✅ Works |
| `ChatMessage` | Individual messages | ✅ Works |
| `UploadedDocument` | User-uploaded files | ✅ Works |
| `GeneratedDocument` | AI-generated documents | ✅ Works |
| `UploadedImage` | User-uploaded images | ✅ Works |
| `GeneratedImage` | AI-generated images | ✅ Works |
| `MemoryEntry` | Long-term memory storage | 🟡 Partial (not auto-populated) |
| `Imprint` | Guardian identity | ✅ Works |
| `Persona` | Guardian behavior | ✅ Works |
| `SystemDoc` | Knowledge blocks | ✅ Works |

---

## 9. Implementation Notes & Common Pitfalls

### Threading & Async

- Backend routes are async (FastAPI). Use `await` for DB operations.
- Frontend uploads are non-blocking (FileReader + events).
- Long operations (embedding, image generation) should use background jobs or queues.

### Database Transactions

- All multi-step operations should use transactions to prevent partial updates.
- Example: Document upload should wrap file storage + DB row creation in a transaction.

### API Contract / Versioning

- Keep API responses backward-compatible; add new fields, don't remove.
- Example: `/api/media/upload-document` may return additional metadata (embedding_status); existing clients ignore unknown fields.

### Error Handling

- Return meaningful HTTP status codes:
  - `400` – Invalid input (bad prompt, unsupported file type)
  - `401` – Unauthorized (missing/invalid API key)
  - `503` – Service unavailable (provider down, vector store unreachable)
- Frontend should display user-friendly error messages, not stack traces.

### Testing Isolation

- Use `pytest` fixtures for DB setup/teardown.
- Mock external services (LLM, image provider, file storage) in unit/integration tests.
- E2E tests should use real services or mock servers (e.g., `responses` library).

### Configuration Management

- Keep secrets in `.env`; never commit `.env` to git.
- Use `python-dotenv` or similar for local development.
- Production should use environment variables or secret management system.

---

## 10. Success Metrics (Post-MVP Validation)

Once all 6 core features are implemented and validated:

1. **User can chat with Guardian** using RAG at all depth levels
2. **User can upload ChatGPT conversations** and retrieve them in chat
3. **User can upload documents** and reference them in chat
4. **User can upload and view images** in gallery
5. **User can generate images** from prompts
6. **User can generate code/narrative/outline documents** and edit them
7. **All manual test scripts pass** without errors
8. **All automated tests pass** with >80% code coverage on critical paths
9. **No data loss** in import/upload workflows
10. **System handles provider unavailability gracefully** (e.g., LLM down → fallback or error message)

---

## 11. Next Steps for Product Lead / User

1. **Review this roadmap** in chat (section 2) and markdown file
2. **Prioritize milestones** based on business need (MVP assumes order: 0→1→2→3→4→5→6)
3. **Assign tasks to team members** using the task breakdown in each section
4. **Set up CI/CD** to run test suite on every PR
5. **Schedule validation sessions** at end of each milestone
6. **Defer scope** using parking lot (section 5) to stay on schedule

---

**Document Prepared By:** MVP Analysis & Roadmap Generator
**Status:** Ready for Review & Execution
**Last Updated:** 2025-11-25
