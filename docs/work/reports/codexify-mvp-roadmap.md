# Codexify MVP Roadmap & Core Loop Plan

## 1. Overview & Goals

This document defines the strict MVP scope for Codexify, focusing on closing the "Core Loops" for 6 non-negotiable features. The goal is to get the system fully operational with end-to-end working flows, deferring nice-to-have features to later phases.

**Current Status Summary:**
- **Infrastructure**: Solid (FastAPI, Postgres, Neo4j, Vite/React).
- **Backend**: Core routing and DB layers are good. RAG and Migration are fragmented (SQLite vs Chroma).
- **Frontend**: Component structure is in place, but wiring to backend varies.

---

## 2. Core MVP Features

### 2.1 Memory / RAG + Context Broker + Guardian Chat

**Current State:**
- **Backend**: `guardian/routes/chat.py` implements the chat loop. `ContextBroker` (`guardian/context/broker.py`) attempts to fetch context from `VectorStore` (SQLite) and `MemoryOSRetriever`.
- **Storage**: `VectorStore` (`guardian/vector/store.py`) uses a local SQLite database for embeddings.
- **Gap**: The chat loop uses `VectorStore` (SQLite), but the Migration tool uses `Chroma`. **This is a critical disconnection.** The chat will not see migrated memories.

**Core Loop Definition:**
1. User opens Codexify and selects a persona/Guardian.
2. User asks a question.
3. `ContextBroker` retrieves relevant chunks from **the same store where data is ingested**.
4. System builds prompt with context.
5. Model responds referencing memories.
6. New conversation is saved to DB (and optionally embedded).

**Gap Analysis:**

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| 3. Retrieve Context | `ContextBroker` -> `VectorStore` (SQLite) | Migration writes to Chroma, but Chat reads from SQLite. | **Unify on Chroma.** Update `ContextBroker` and `VectorStore` to use `CodexifyEmbedder` (Chroma wrapper). |
| 4. Build Prompt | `_groq_complete` in `dependencies.py` | Hardcoded to Groq. | Ensure `_groq_complete` handles context injection correctly (it looks mostly correct but needs verification with Chroma results). |
| 6. Save & Embed | `chat.py` / `chatlog_db` | New messages are saved to Postgres but **not embedded** into Vector Store automatically. | Add an event listener or async task to embed new messages into Chroma immediately after save. |

**Implementation Tasks:**
- [ ] **Refactor VectorStore**: Replace SQLite implementation in `guardian/vector/store.py` with a wrapper around `CodexifyEmbedder` (Chroma).
- [ ] **Update ContextBroker**: Ensure it calls the updated `VectorStore` correctly.
- [ ] **Auto-Embed Chat**: Add logic in `chat.py` (or event handler) to embed new user/assistant messages into Chroma.

**Validation Plan:**
- **Manual**: Send a message, verify it appears in Chroma (via CLI or logs). Ask a follow-up question that requires recalling that message.
- **Automated**: Integration test ensuring `ContextBroker.assemble` returns the expected chunks after insertion.

---

### 2.2 ChatGPT Migration Tool

**Current State:**
- **Backend**: `backend/rag/chatgpt_migration.py` is robust. It parses exports and ingests into Neo4j and Chroma.
- **Frontend**: Need to verify `SettingsView` or similar has the UI trigger.
- **Gap**: As noted above, it writes to Chroma, which the Chat loop currently ignores.

**Core Loop Definition:**
1. User goes to Settings/Migration UI.
2. User selects ChatGPT export file (JSON).
3. System parses, saves to Neo4j (graph) and Chroma (vectors).
4. User sees success confirmation and stats.
5. **Crucial**: User goes to Chat, asks about migrated content, and Guardian knows the answer.

**Gap Analysis:**

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| 1. UI Trigger | Unknown (likely missing or disconnected) | Need a clear UI surface for this. | Create/Update `MigrationView` in frontend to POST to `/upload-chat`. |
| 3. Ingest | `ingest_chatgpt_export` | It works but is isolated. | Ensure the API endpoint calls this specific function (currently `/upload-chat` in `guardian_api.py` calls a different `parse_chat_history` function). **Unify this.** |
| 5. Recall | `ContextBroker` | Disconnected from Chroma. | Fixed by 2.1 (Unify on Chroma). |

**Implementation Tasks:**
- [ ] **Unify Ingestion Logic**: Update `guardian_api.py:upload_chat` to use `backend.rag.chatgpt_migration.ingest_chatgpt_export`.
- [ ] **Frontend UI**: Build/Verify a "Import ChatGPT" component in Settings that uploads to this endpoint.

**Validation Plan:**
- **Manual**: Import a small sample export. Check logs for "Chroma import complete". Go to chat, ask a specific question from that export.

---

### 2.3 Upload Documents + Embed

**Current State:**
- **Backend**: `/upload/document` (`guardian/routes/media.py`) saves files to disk and DB. It extracts text but **does not embed it**.
- **Frontend**: `components/documents` likely exists.
- **Gap**: Uploaded documents are "dead" to the RAG system.

**Core Loop Definition:**
1. User uploads a PDF/MD/TXT file via UI.
2. System saves file, extracts text.
3. System **chunks and embeds** the text into Chroma.
4. User asks question about document.
5. Guardian retrieves document chunks and answers.

**Gap Analysis:**

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| 3. Embed | None | Text is extracted but not embedded. | Call `CodexifyEmbedder.embed_and_index` inside the `/upload/document` route. |
| 5. Recall | `ContextBroker` | Won't find docs if not embedded. | Once embedded in Chroma, the unified `ContextBroker` (from 2.1) should find them automatically. |

**Implementation Tasks:**
- [ ] **Embed on Upload**: Modify `/upload/document` to call `CodexifyEmbedder` after text extraction.
- [ ] **Frontend**: Ensure upload form handles the response correctly.

**Validation Plan:**
- **Manual**: Upload a unique document (e.g., a specific recipe). Ask Guardian about it.

---

### 2.4 Upload Images to Gallery

**Current State:**
- **Backend**: `/upload/image` (`guardian/routes/media.py`) is implemented and working.
- **Frontend**: `components/gallery` likely exists.
- **Status**: **✅ Loop Closed** (mostly). Just need to verify UI wiring.

**Core Loop Definition:**
1. User uploads image via Gallery UI.
2. System saves to disk/DB.
3. Image appears in Gallery grid.
4. User can view image details.

**Gap Analysis:**

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| 3. Gallery Grid | `list_images` endpoint | Need to verify frontend uses this. | Verify `Gallery` component fetches from `/images`. |

**Implementation Tasks:**
- [ ] **Verify UI**: Check `Gallery` component wiring.

**Validation Plan:**
- **Manual**: Upload image, refresh gallery, click image.

---

### 2.5 Generate Images

**Current State:**
- **Backend**: `/generate/image` is a **stub**. It creates a DB record but generates no image.
- **Frontend**: Unknown.
- **Gap**: No actual generation logic.

**Core Loop Definition:**
1. User enters prompt in "Generate Image" UI.
2. System calls provider (DALL-E / SD / Local).
3. System saves result to Gallery.
4. User sees image in Gallery.

**Gap Analysis:**

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| 2. Generate | None (Stub) | No integration. | Implement `guardian.providers.image_gen` (or similar) and call it in the route. Use OpenAI DALL-E as MVP default (easiest). |
| 1. UI | Unknown | Need a prompt input. | Create `ImageGenerator` component. |

**Implementation Tasks:**
- [ ] **Backend Integration**: Implement DALL-E generation in `/generate/image`.
- [ ] **Frontend UI**: Create a simple prompt input that calls this endpoint and refreshes the gallery.

**Validation Plan:**
- **Manual**: Generate "A red cat". Verify a red cat image appears in Gallery.

---

### 2.6 Generate Documents (Code / Literature / Diagrams)

**Current State:**
- **Backend**: No specific endpoint. `autosave` exists but implies client-side generation or chat-based generation.
- **Gap**: Missing specific "Generate Document" flow.

**Core Loop Definition:**
1. User selects "New Document" -> "Generate".
2. User enters prompt (e.g., "Write a Python script to...").
3. System (LLM) generates content.
4. System saves as a new `GeneratedDocument`.
5. User sees document in list and can edit it.

**Gap Analysis:**

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| 3. Generate | None | No endpoint to "prompt -> document". | Create `POST /api/documents/generate` that calls LLM and saves result. |
| 5. View/Edit | `get_thread_documents` | Need a document editor view. | Verify `DocumentEditor` component exists. |

**Implementation Tasks:**
- [ ] **Backend Route**: Create `/api/documents/generate`.
- [ ] **Frontend UI**: Add "Generate" button to Document view.

**Validation Plan:**
- **Manual**: Generate a poem. Verify it appears in document list.

---

## 3. Milestones & Timeline

### Milestone 0: Infrastructure & Unification (Critical)
- **Goal**: Fix the RAG fragmentation so Chat and Migration use the same brain.
- **Tasks**:
    - Refactor `VectorStore` to use `CodexifyEmbedder` (Chroma).
    - Update `ContextBroker` to use the new `VectorStore`.

### Milestone 1: Chat & Memory Loop
- **Goal**: Working Chat with RAG.
- **Tasks**:
    - Auto-embed new chat messages.
    - Verify `_groq_complete` context injection.

### Milestone 2: Migration & Ingestion
- **Goal**: Import existing knowledge.
- **Tasks**:
    - Wire `/upload-chat` to `ingest_chatgpt_export`.
    - Build/Verify Migration UI.

### Milestone 3: Document Upload & RAG
- **Goal**: Chat with files.
- **Tasks**:
    - Add embedding logic to `/upload/document`.
    - Verify Frontend Upload UI.

### Milestone 4: Image & Document Generation
- **Goal**: Creative tools.
- **Tasks**:
    - Implement DALL-E integration.
    - Create `/api/documents/generate`.
    - Build Generation UIs.

---

## 4. Risks, Assumptions & Dependencies

- **Dependency**: Requires valid `GROQ_API_KEY` and `OPENAI_API_KEY` (for DALL-E/Embeddings).
- **Risk**: ChromaDB local persistence might be flaky in Docker if volumes aren't set right.
- **Assumption**: Frontend components exist or can be quickly scaffolded based on existing patterns.

## 5. Deferred Features (Post-MVP Parking Lot)
- **Federation**: Peer-to-peer context sharing.
- **Complex Graph Sync**: Deep Neo4j synchronization (keep it basic for MVP).
- **Voice/TTS**: Nice to have, but not core loop.
- **Local LLM Inference**: Stick to APIs for MVP stability.
