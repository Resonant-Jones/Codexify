# Codexify MVP Roadmap & Core Loop Plan

## 1. Overview & Goals

This document outlines the strict requirements to achieve a fully operational **Codexify MVP**. The goal is to close the "core loops" for 6 non-negotiable features, ensuring end-to-end functionality from UI to Backend to Storage.

**Current Status**:
- **Backend Core**: Strong foundation (FastAPI, Postgres, Neo4j, Context Broker).
- **Frontend Core**: Good UI components (React, Tailwind), but missing wiring for advanced features.
- **Gaps**: Significant gaps in "Generation" features and the frontend side of "Migration".

---

## 2. Core MVP Features

### 2.1 Memory / RAG + Context Broker + Guardian Chat

**Current State**:
- **Backend**: `ContextBroker` (`guardian/context/broker.py`) is well-architected with support for multiple depths (`shallow`, `normal`, `deep`). `guardian/routes/chat.py` integrates it.
- **Storage**: `_vector_store` and `_memory_store` dependencies exist but need robust initialization verification.
- **Frontend**: Chat interface exists (`Composer.tsx`, `ChatBubble.tsx`).

**Core Loop Definition**:
1. User sends a message in Chat.
2. System embeds the message (synchronously or background).
3. `ContextBroker` retrieves relevant context (Vector + Graph + Memory).
4. LLM generates response using context.
5. Response is stored and embedded.

**Gap Analysis**:

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| Embedding | `chat.py::_embed_message` | Synchronous, "best-effort", potential bottleneck. | Move to background task (FastAPI `BackgroundTasks`) or async worker. |
| Retrieval | `ContextBroker.assemble` | Logic exists, but relies on `_vector_store` being healthy. | Add health check for Vector Store on startup. |
| Context | `ContextBroker` | Good, but "diagnostic" depth might be overkill for MVP. | Stick to "normal" depth for MVP default. |

**Implementation Tasks**:
- [ ] **Async Embedding**: Refactor `_embed_message` to use `BackgroundTasks`.
- [ ] **Vector Store Health**: Add startup check in `guardian_api.py` to ensure Chroma/PGVector is ready.
- [ ] **Verify Wiring**: Ensure `ContextBroker` is actually receiving the `vector_store` instance.

**Validation Plan**:
- **Manual**: Send message, check logs for "Retrieved X memory chunks", ask question about previous message.
- **Automated**: Unit test for `ContextBroker.assemble` with mocked vector store.

---

### 2.2 ChatGPT Migration Tool

**Current State**:
- **Backend**: `ingest_chatgpt_export` (`backend/rag/chatgpt_migration.py`) and route `/upload-chatgpt-export` (`guardian/routes/rag_upload.py`) exist and look robust.
- **Frontend**: **MISSING**. `SettingsView.tsx` has no UI to trigger this specific upload.

**Core Loop Definition**:
1. User goes to Settings > Migration.
2. User selects `conversations.json` from ChatGPT export.
3. Frontend POSTs to `/api/upload-chatgpt-export`.
4. Backend parses, creates threads/messages in Postgres, and embeds in Vector Store.
5. Frontend shows success count (Threads/Messages).

**Gap Analysis**:

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| UI Trigger | None | No button/form in Settings to upload export. | Add "Import ChatGPT" section to `SettingsView.tsx`. |
| Feedback | None | User doesn't know if import worked. | Show progress/success modal with stats. |

**Implementation Tasks**:
- [ ] **Frontend UI**: Add `MigrationCard` or section in `SettingsView` with file picker.
- [ ] **API Client**: Add `uploadChatGPTExport` function to `api.ts`.
- [ ] **Wiring**: Connect UI to API and handle loading/success states.

**Validation Plan**:
- **Manual**: Import a small `conversations.json`, verify threads appear in Sidebar.

---

### 2.3 Upload Documents + Embed

**Current State**:
- **Backend**: `/upload/document` (`guardian/routes/media.py`) handles upload + storage + embedding.
- **Frontend**: `DocumentsView.tsx` exists with `useUploader`.

**Core Loop Definition**:
1. User drags PDF/MD to Documents view.
2. Frontend POSTs to `/api/upload/document`.
3. Backend saves file, extracts text, embeds into Vector Store.
4. Document appears in list.
5. Chat can retrieve document context.

**Gap Analysis**:

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| Embedding | `media.py` | Imports `CodexifyEmbedder` inside route (fragile). | Move import to top or dependency injection. |
| Retrieval | `ContextBroker` | Needs to ensure it queries "document" source. | Verify `_search_semantic` includes document chunks. |

**Implementation Tasks**:
- [ ] **Refactor Import**: Fix `CodexifyEmbedder` import in `media.py`.
- [ ] **Frontend Wiring**: Ensure `useUploader` targets `/api/upload/document` correctly.

**Validation Plan**:
- **Manual**: Upload unique text file, ask chat about its content.

---

### 2.4 Upload Images to Gallery

**Current State**:
- **Backend**: `/upload/image` (`guardian/routes/media.py`) exists.
- **Frontend**: `GalleryView.tsx` exists but relies on parent props. `SettingsView` has wallpaper upload.

**Core Loop Definition**:
1. User uploads image via Gallery or Chat.
2. Image stored in `media/images`.
3. Metadata saved to DB.
4. Image appears in Gallery grid.

**Gap Analysis**:

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| Upload UI | `SettingsView` (Wallpaper) | No direct upload in Gallery. | Add "Upload" button to `GalleryView` header. |
| List UI | `GalleryView` | Uses `items` prop. | Wire `GalleryView` to fetch from `/api/images`. |

**Implementation Tasks**:
- [ ] **Gallery API**: Wire `GalleryView` to `useQuery` or `useEffect` fetching `/api/images`.
- [ ] **Upload Button**: Add upload trigger to `GalleryView`.

**Validation Plan**:
- **Manual**: Upload image, verify it appears in grid and persists on refresh.

---

### 2.5 Generate Images

**Current State**:
- **Backend**: `/generate/image` (`guardian/routes/media.py`) is a **placeholder** ("TODO: Integrate...").
- **Frontend**: Missing.

**Core Loop Definition**:
1. User enters prompt in "Generate" UI (or Chat command).
2. Backend calls Provider (DALL-E/Local).
3. Image saved to storage + DB.
4. Image appears in Gallery.

**Gap Analysis**:

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| Generation | Placeholder | No actual generation logic. | Implement basic wrapper for OpenAI/Stability API. |
| UI | None | No interface. | Add "Generate" tab/modal to `GalleryView`. |

**Implementation Tasks**:
- [ ] **Backend Logic**: Implement `ImageGenerator` class (wrapper for API).
- [ ] **Frontend UI**: Add basic "Prompt -> Generate" flow in Gallery.

**Validation Plan**:
- **Manual**: Generate "red ball", verify image created and shown.

---

### 2.6 Generate Documents

**Current State**:
- **Backend**: Missing. `autosave` exists but is for manual edits.
- **Frontend**: Missing.

**Core Loop Definition**:
1. User selects "New Document" > "Generate".
2. User provides prompt ("Write a spec for X").
3. Backend LLM generates markdown.
4. Document saved as `GeneratedDocument`.
5. Document opens in Editor.

**Gap Analysis**:

| Loop Step | Current Implementation | Gap / Problem | Concrete Fix |
| :--- | :--- | :--- | :--- |
| Endpoint | None | No route for doc gen. | Create `/api/documents/generate`. |
| UI | None | No trigger. | Add "Generate" button to `DocumentsView`. |

**Implementation Tasks**:
- [ ] **Backend Route**: Add `/generate` to `documents.py` using `chat_with_ai`.
- [ ] **Frontend UI**: Add generation modal to `DocumentsView`.

**Validation Plan**:
- **Manual**: Generate "Python script for fibonacci", verify doc created.

---

## 3. Milestones & Timeline

### Milestone 0: Infrastructure & Wiring (Immediate)
- Fix `_embed_message` (async).
- Verify Vector Store health check.
- Ensure `useUploader` points to correct endpoints.

### Milestone 1: Migration & RAG (Critical)
- Implement `SettingsView` Migration UI.
- Verify end-to-end ChatGPT import.
- Verify RAG retrieval in Chat.

### Milestone 2: Media & Gallery
- Wire `GalleryView` to real API data.
- Add Image Upload button to Gallery.
- Implement basic Image Generation backend (OpenAI DALL-E is easiest MVP).

### Milestone 3: Document Generation
- Create Document Generation endpoint.
- Add UI trigger in `DocumentsView`.

---

## 4. Risks & Assumptions

- **Assumption**: User has valid API keys (OpenAI/Groq) in `.env`.
- **Risk**: Vector Store (Chroma/PGVector) might be flaky in Docker.
- **Risk**: Large ChatGPT exports might timeout (need async processing for large files).

## 5. Deferred Features (Post-MVP)

- **Graph Visualization**: `ProjectsOverlay.tsx` exists but graph sync is complex.
- **Voice/TTS**: `tts` routes exist but not critical for MVP.
- **Plugins**: `plugin_manager.py` exists but scope is too large for MVP.
- **Federation**: `federation` module is definitely Post-MVP.
