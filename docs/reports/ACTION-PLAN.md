# Codexify Action Plan: Taming the Whack-a-Mole

This action plan is derived directly from the `codexify-mvp-roadmap.md`. It is designed to stop the "whack-a-mole" cycle by enforcing a strict, linear order of operations. We will not jump between features. We will finish one layer of the foundation before adding weight to the next.

## The Golden Rule: Unify, Then Build
The root cause of the current instability is **fragmentation**.
- Chat talks to SQLite.
- Migration talks to Chroma.
- Uploads talk to Disk.
- Nothing talks to each other.

We must fix the "Brain" (RAG/Memory) first. Until the brain is unified, every new feature will just add more disconnected limbs.

---

## Phase 1: The Brain Transplant (Infrastructure & Unification)
**Goal:** One single source of truth for memory (ChromaDB). No more SQLite for vectors.

### 1.1 Unify Vector Store
- [ ] **Refactor `VectorStore`**: Modify `guardian/vector/store.py`. Remove the SQLite logic. Replace it with a wrapper around `CodexifyEmbedder` (which uses Chroma).
- [ ] **Update `ContextBroker`**: Ensure `guardian/context/broker.py` calls this new Chroma-backed `VectorStore`.
- [ ] **Verify**: Run a script to insert a memory and retrieve it. If this fails, **STOP**. Do not proceed until this works.

### 1.2 Connect the Chat Loop
- [ ] **Auto-Embed**: In `guardian/routes/chat.py`, ensure that *every* message sent or received is immediately sent to the `VectorStore` to be embedded.
- [ ] **Verify**: Chat with the bot. Restart the server. Ask the bot what you just talked about. If it forgets, **STOP**.

---

## Phase 2: Feeding the Brain (Ingestion & Migration)
**Goal:** Now that the brain works, let's feed it data.

### 2.1 ChatGPT Migration
- [ ] **Backend Wiring**: Connect the `POST /upload-chat` endpoint in `guardian_api.py` to the robust `ingest_chatgpt_export` function in `backend/rag/chatgpt_migration.py`.
- [ ] **Frontend UI**: Create/Verify the "Import ChatGPT" button in Settings.
- [ ] **Verify**: Import a file. Go to Chat. Ask about a specific detail from that file.

### 2.2 Document Uploads
- [ ] **Embed on Upload**: In `guardian/routes/media.py`, inside the `/upload/document` route, add the call to `CodexifyEmbedder`.
- [ ] **Verify**: Upload a PDF. Ask a question about its specific content.

---

## Phase 3: Creative Output (Generation)
**Goal:** Now that the bot knows things, let it create things.

### 3.1 Image Generation
- [ ] **Implement Provider**: Fill in the stub at `/generate/image`. Use OpenAI DALL-E for the MVP (simplest implementation).
- [ ] **Frontend**: Add the "Generate Image" input to the Gallery view.

### 3.2 Document Generation
- [ ] **New Route**: Create `POST /api/documents/generate`.
- [ ] **Frontend**: Add a "Generate" button to the Documents view.

---

## Summary of "Anti-Whack-a-Mole" Strategy
1.  **Do not start Phase 2 until Phase 1 is 100% solid.**
2.  **Validation is not optional.** If a step fails validation, we fix it immediately. We do not "come back to it later."
3.  **One DB to rule them all.** We are betting on Chroma for vectors. Any code trying to use SQLite for embeddings must be ruthlessly removed.
