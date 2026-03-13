# Codexify Capability Scope Audit
**Date:** March 12, 2026
**Auditor:** Claude Code
**Repository:** /Users/resonant_jones/Keep/Resonant_Constructs/Codexify
**Baseline:** February 2026 "State of Codexify" post

---

## SECTION 1 — Executive Truth

### What a user can genuinely do today

A user running Codexify locally can:

1. **Chat with an AI companion** through a React-based UI with real-time streaming responses
2. **Create and manage chat threads** organized into projects, with thread branching, archival, and metadata editing
3. **Upload and manage documents** (PDF, DOCX, TXT, MD) with automatic text extraction and RAG embedding for context-aware retrieval
4. **Upload and view images** in a media gallery with project/thread scoping
5. **Generate images** via AI (DALL-E integration) when enabled
6. **Organize work into projects** with CRUD operations, including a default "General" project for unscoped threads
7. **Share threads and documents** via secure, expiring shareable links (`/share/{token}`)
8. **Configure identity/persona** through the Imprint system with depth-aware modeling (light/normal/deep modes)
9. **Access synthesized speech** (TTS) for assistant messages when enabled
10. **View diagnostic traces** (RAG trace, system prompt meta) via debug endpoints
11. **Run scheduled automation** via cron jobs (webhook-based, manually triggered or via external scheduler)
12. **Connect to GitHub** for repository issue/PR ingestion (connector framework, GitHub-only)

### What an operator can do today

1. **Manage cron jobs** via API (`/api/cron/jobs`) with create, read, update, delete, and manual trigger
2. **Monitor connector sync** for GitHub via worker stats endpoint
3. **Access health endpoints** for memory, connectors, and system status
4. **Configure identity depth** at project level (light/normal/deep)
5. **Manage browser automation approvals** (create, approve, deny)
6. **View audit logs** for compliance tracking (written to database)

### What is newly real since the February 2026 post

1. **Cron job API and worker** — Full CRUD API exists with a Redis-based worker loop for execution
2. **Browser approval system** — Complete with session management and governance
3. **Media identity system** — Content-addressed storage with deduplication for images and documents
4. **Document generation** — Thread-linked document generation via `/api/documents/generate`
5. **Share links** — Secure token-based sharing for threads and documents
6. **Imprint/Zero persona system** — Draft, accept, reject workflow with system prompt integration
7. **Context depth modes** — Shallow/normal/deep/diagnostic with policy enforcement

### What is still not honest to claim publicly

1. **Scheduled automation is not "set and forget"** — Requires external scheduler or manual triggers; no built-in scheduler daemon
2. **Browser agent is not fully autonomous** — Approval system exists but actual browser automation beyond session management is minimal
3. **Multi-platform messaging adapters** — Not found in codebase (no Slack, Discord, email connectors)
4. **Federation/peer context** — Routes exist but functionality is stubbed/internal
5. **Tauri desktop app** — Bootstrap code exists but runtime integration is incomplete
6. **Management panels** — Only basic API endpoints exist, no comprehensive admin UI

---

## SECTION 2 — Capability Ledger

### A. Core chat and thread system

**Capability:** Thread-based chat with message persistence
**Status:** SHIPPED
**What it actually does today:**
- Full CRUD for threads (`/api/chat/threads`, `/chat/threads`)
- Message posting with role attribution (`/api/chat/{thread_id}/messages`)
- Async completion via queue (`/api/chat/{thread_id}/complete`)
- Thread branching (child threads)
- Thread archival/unarchival
- Project scoping for threads

**Evidence:**
- Routes: `guardian/routes/chat.py` (2,200+ lines), `guardian/routes/threads.py`
- Models: `ChatThread`, `ChatMessage` in `guardian/db/models.py:48-120`
- Worker: `guardian/workers/chat_worker.py`
- Frontend: `frontend/src/components/chat/`, `frontend/src/components/sidebar/ThreadList.tsx`

**User visibility:** Public UI
**Gaps / blockers:** None major
**Safe public wording:** "Full chat threading with project organization, branching, and archival"

---

**Capability:** Context depth modes
**Status:** SHIPPED
**What it actually does today:**
- Four modes: shallow, normal, deep, diagnostic
- Depth policy enforcement based on project `identity_depth`
- Downgrade reasons tracked when deep mode requested but not allowed

**Evidence:**
- `guardian/depth.py` — depth resolution logic
- `guardian/routes/chat.py:1382-1479` — depth mode handling in completion
- `guardian/cognition/identity_policy.py` — policy enforcement

**User visibility:** API parameter (`depth_mode`), backend enforcement
**Gaps / blockers:** UI for selecting depth mode may be limited
**Safe public wording:** "Context depth modes with policy-based enforcement"

---

### B. Context and retrieval

**Capability:** RAG document retrieval
**Status:** SHIPPED
**What it actually does today:**
- Scoped document retrieval (project + thread level)
- Document excerpts injected into context based on depth mode
- RAG trace debug endpoint for visibility

**Evidence:**
- `guardian/routes/chat.py:986-1018` — `_build_doc_context_override()`
- `guardian/context/broker.py` — ContextBroker
- `guardian/routes/chat.py:1961-2042` — debug RAG trace endpoint

**User visibility:** Backend-only (debug endpoint for devs)
**Gaps / blockers:** No user-facing RAG configuration UI
**Safe public wording:** "Automatic document retrieval based on conversation context"

---

### C. Memory systems

**Capability:** Three-tier memory (ephemeral, midterm, longterm)
**Status:** ROUGH
**What it actually does today:**
- Ephemeral memory (in-memory only, per-process)
- Midterm/longterm via database with 90-day retention
- Memory CRUD via API
- GitHub-specific memory search

**Evidence:**
- `guardian/routes/memory.py` — full CRUD endpoints
- Models: `MemoryEntry` in `guardian/db/models.py`
- GitHub search: `guardian/routes/memory.py:394-454`

**User visibility:** API only, minimal UI
**Gaps / blockers:** Ephemeral memory is not shared across processes; no clear UI for memory management
**Safe public wording:** "Memory system with persistent storage for midterm and longterm entries"

---

### D. Documents and generated artifacts

**Capability:** Document upload and RAG embedding
**Status:** SHIPPED
**What it actually does today:**
- PDF, DOCX, TXT, MD upload with text extraction
- Content-addressed storage with deduplication
- Async embedding queue integration
- Thread-document linking

**Evidence:**
- `guardian/routes/media.py:826-1252` — upload_document endpoint
- `guardian/queue/document_embed_queue.py`
- Models: `UploadedDocument`, `MediaAsset` in `guardian/db/models.py`

**User visibility:** Public UI (Documents view)
**Gaps / blockers:** None major
**Safe public wording:** "Document upload with automatic text extraction and embedding for RAG"

---

**Capability:** Document generation
**Status:** SHIPPED
**What it actually does today:**
- Generate documents from prompts using LLM
- Link to threads
- Markdown/plain text formats

**Evidence:**
- `guardian/routes/documents.py:253-393` — `/api/documents/generate`
- Frontend: `frontend/src/components/DocumentGenModal.tsx`

**User visibility:** Public UI
**Gaps / blockers:** None major
**Safe public wording:** "AI-powered document generation from conversation context"

---

### E. Media / images / vision

**Capability:** Image upload and gallery
**Status:** SHIPPED
**What it actually does today:**
- PNG, JPG, WebP upload with deduplication
- Media grid UI with filtering
- Content-addressed storage

**Evidence:**
- `guardian/routes/media.py:464-819` — upload_image, get_image, delete_image
- Frontend: `frontend/src/components/media/MediaGrid.tsx`, `frontend/src/components/gallery/`

**User visibility:** Public UI
**Gaps / blockers:** Vision/multimodal not implemented
**Safe public wording:** "Image upload and gallery management"

---

**Capability:** Image generation
**Status:** ROUGH
**What it actually does today:**
- DALL-E integration via `ImageGenRouter`
- Generated image tracking with prompt storage
- Feature-flagged (`CODEXIFY_ENABLE_MEDIA_GENERATION_ROUTES`)

**Evidence:**
- `guardian/routes/media.py:1259-1492` — `/generate/image`
- `guardian/image_gen/router.py`

**User visibility:** API only, may have limited UI
**Gaps / blockers:** Behind feature flag; provider configuration required
**Safe public wording:** "AI image generation (beta, requires configuration)"

---

### F. Projects and organizational scope

**Capability:** Project management
**Status:** SHIPPED
**What it actually does today:**
- Full CRUD for projects
- Default "General" project auto-creation
- Thread ejection on project deletion
- Project-level identity depth

**Evidence:**
- `guardian/routes/projects.py` — full CRUD
- Models: `Project` in `guardian/db/models.py:44-75`
- Frontend: `frontend/src/components/sidebar/ProjectList.tsx`, `frontend/src/components/projects/`

**User visibility:** Public UI
**Gaps / blockers:** None major
**Safe public wording:** "Project-based organization with configurable identity depth"

---

### G. Sharing and public links

**Capability:** Shareable links
**Status:** SHIPPED
**What it actually does today:**
- Secure token-based sharing for threads and documents
- Optional expiration
- Read-only access via `/share/{token}`

**Evidence:**
- `guardian/routes/share.py` — full implementation
- Models: `SharedLink` in `guardian/db/models.py`
- Frontend: `frontend/src/pages/SharePage.tsx`

**User visibility:** Public UI (Share button)
**Gaps / blockers:** None major
**Safe public wording:** "Secure shareable links with optional expiration"

---

### H. Identity / personas / Imprint / system prompt controls

**Capability:** Imprint Zero / Persona system
**Status:** SHIPPED
**What it actually does today:**
- Draft/propose/accept/reject workflow for Guardian identity
- Persona text storage and retrieval
- System prompt building with segments
- Token threshold monitoring

**Evidence:**
- `guardian/routes/imprint.py` — full workflow
- `guardian/cognition/system_prompt_builder.py`
- Models: `Imprint`, `Persona` in `guardian/db/models.py`

**User visibility:** API + partial UI (settings)
**Gaps / blockers:** Full UI for persona management may be limited
**Safe public wording:** "Configurable AI companion identity with system prompt management"

---

### I. Tools / command bus / agent-like execution

**Capability:** Command bus infrastructure
**Status:** INTERNAL
**What it actually does today:**
- Database tables for command bus exist
- Routes file present but minimal implementation

**Evidence:**
- `guardian/routes/command_bus.py`
- Models: `CommandBus*` tables in `guardian/db/models.py`

**User visibility:** None
**Gaps / blockers:** Not wired into runtime
**Safe public wording:** Not safe to claim publicly

---

**Capability:** Agent orchestration
**Status:** PARTIAL
**What it actually does today:**
- Routes exist (`/api/agent/*`)
- Worker infrastructure present
- Actual agent capabilities minimal

**Evidence:**
- `guardian/routes/agent_orchestration.py`
- `guardian/workers/agent_worker.py`

**User visibility:** API only
**Gaps / blockers:** Not fully implemented
**Safe public wording:** Not safe to claim publicly

---

### J. Scheduled automation / cron

**Capability:** Cron job management
**Status:** ROUGH
**What it actually does today:**
- Full CRUD API for cron jobs (`/api/cron/jobs/*`)
- Schedule validation (@hourly, @daily, */N * * * *)
- Manual trigger endpoint
- Run history tracking
- Worker for execution via Redis queue

**Evidence:**
- `guardian/routes/cron.py` — full CRUD
- `guardian/workers/cron_worker.py` — worker loop
- Models: `CronJob`, `CronRun` in `guardian/db/models.py`

**User visibility:** API only, no UI
**Gaps / blockers:** No built-in scheduler daemon; requires external trigger or manual execution
**Safe public wording:** "Scheduled job management with webhook execution (requires external scheduler)"

---

### K. Browser agent / approvals / governance

**Capability:** Browser approval system
**Status:** ROUGH
**What it actually does today:**
- Approval request/approve/deny workflow
- Browser session management (create, get, close)
- Event emission for audit trail

**Evidence:**
- `guardian/routes/browser.py` — approval endpoints
- `guardian/browser/approval.py`
- `guardian/browser/session_manager.py`

**User visibility:** API only
**Gaps / blockers:** Actual browser automation beyond session management is minimal
**Safe public wording:** "Browser automation approval system (governance layer)"

---

### L. External connectors and messaging channels

**Capability:** GitHub connector
**Status:** ROUGH
**What it actually does today:**
- GitHub repository sync for issues/PRs
- Background worker with exponential backoff
- Ingestion endpoint to transform raw docs to memory entries

**Evidence:**
- `guardian/routes/connectors.py` — full implementation
- `guardian/connectors/github.py`
- Worker stats endpoint

**User visibility:** API only
**Gaps / blockers:** Only GitHub supported; OAuth not implemented (uses env token); worker disabled by default
**Safe public wording:** "GitHub connector for repository synchronization (API key based)"

---

**Capability:** Other connectors (Google Drive, Notion, Slack)
**Status:** SPEC ONLY
**What it actually does today:**
- Registry structure exists
- Only GitHub actually implemented

**Evidence:**
- `guardian/routes/connectors.py:81-97` — CONNECTOR_REGISTRY with only "github"
- Comments mention other connectors but no implementation

**User visibility:** None
**Gaps / blockers:** Not implemented
**Safe public wording:** Not safe to claim

---

### M. Sync / federation / peer context

**Capability:** Federation routes
**Status:** INTERNAL
**What it actually does today:**
- Routes exist but functionality is stubbed

**Evidence:**
- `guardian/routes/federation.py`

**User visibility:** None
**Gaps / blockers:** Not implemented
**Safe public wording:** Not safe to claim

---

### N. Desktop / Tauri / runtime bootstrap

**Capability:** Runtime bootstrap
**Status:** ROUGH
**What it actually does today:**
- Docker Compose orchestration
- Health checking and readiness probes
- Welcome screen with gating

**Evidence:**
- `frontend/src/App.tsx` — full bootstrap flow
- `frontend/src/lib/runtimeBootstrap.ts`
- `frontend/src/components/bootstrap/BootstrapGate.tsx`

**User visibility:** Public UI (bootstrap gate)
**Gaps / blockers:** Tauri integration incomplete; local-first runtime requires Docker
**Safe public wording:** "Local-first runtime with Docker Compose bootstrap"

---

### O. Auth / security / operational readiness

**Capability:** API key authentication
**Status:** SHIPPED
**What it actually does today:**
- API key required on all routes
- Dependency injection pattern (`require_api_key`)
- Token validation with configurable backend

**Evidence:**
- `guardian/core/dependencies.py` — auth dependencies
- Applied to all routes via `Depends(require_api_key)`

**User visibility:** Backend only
**Gaps / blockers:** User management UI minimal
**Safe public wording:** "API key authentication on all endpoints"

---

### P. Diagnostics / cognitive inspection surfaces

**Capability:** RAG trace debugging
**Status:** INTERNAL
**What it actually does today:**
- Debug endpoint for RAG trace (`/api/chat/debug/rag-trace/{thread_id}/latest`)
- System prompt summary endpoint

**Evidence:**
- `guardian/routes/chat.py:1961-2042`
- `guardian/routes/imprint.py:444-518`

**User visibility:** Dev-only
**Gaps / blockers:** Not user-facing
**Safe public wording:** Not safe to claim publicly

---

## SECTION 3 — Delta since the February 2026 post

### Still true (from Tier 1 / production-ready)
- Chat + Threads — Still fully implemented and working
- Documents — Fully implemented with RAG
- Gallery / Images — Fully implemented
- Projects — Fully implemented
- Sharing — Fully implemented (share links)
- Settings / Identity — Imprint system working
- Auth — API key auth working
- Context depth modes — Working with policy enforcement

### Newly added or materially advanced
| Feature | Previous State | Current State |
|---------|---------------|---------------|
| Cron jobs | API only | Full worker + execution |
| Browser approvals | API only | Session management added |
| Media identity | Not mentioned | Content-addressed storage implemented |
| Document generation | Not mentioned | `/api/documents/generate` working |
| Share links | Not mentioned | Full implementation with expiration |
| Imprint/Zero | Not mentioned | Complete workflow (draft/accept/reject) |
| TTS | Not mentioned | Routes exist, feature-flagged |
| Connector worker | Manual only | Background worker with backoff |

### Downgraded after closer inspection
| Feature | Previous Claim | Reality |
|---------|---------------|---------|
| Scheduled automation | "Built but not fully exercisable" | ROUGH — requires external scheduler |
| Browser agent | "Built but not fully exercisable" | ROUGH — governance exists, automation minimal |
| Multi-platform messaging | Mentioned as priority | SPEC ONLY — not implemented |

### Still pending (from "Next priorities")
| Feature | Status |
|---------|--------|
| Scheduler loop | PARTIAL — worker exists but no daemon |
| Browser session routes | DONE — routes exist |
| Inbound channel webhooks | PARTIAL — cron webhooks only |
| Management panels | NOT DONE — no admin UI |

---

## SECTION 4 — Public-safe capability statement

**What you can use today:**

Codexify is a local-first AI companion platform with chat, document management, and project organization. You can:

- Chat with an AI companion in threaded conversations organized by projects
- Upload documents (PDF, DOCX, TXT, MD) for automatic RAG-based retrieval
- Upload and manage images in a gallery
- Generate shareable links to conversations and documents
- Configure your AI companion's identity and system prompts
- Run scheduled jobs via API (requires external scheduler)

**What's real but rough:**

- Image generation (requires configuration, behind feature flag)
- Text-to-speech for assistant messages (requires configuration)
- GitHub connector for syncing issues/PRs (API key based, no OAuth)
- Browser automation governance (approval system, limited automation)

**What's next up:**

- Built-in scheduler daemon for true "set and forget" automation
- Additional connectors (Google Drive, Notion, Slack)
- Management panels for easier administration
- Federation and peer context sharing

---

## SECTION 5 — Internal records version

**Strongest surfaces:**
1. Chat/Thread system — Battle-tested, comprehensive, well-tested
2. Document upload/RAG — Solid implementation with deduplication
3. Project organization — Clean CRUD, sensible defaults
4. Share links — Simple, secure, working
5. Imprint/identity — Good separation of concerns, extensible

**Weakest seams:**
1. **Cron scheduler** — Worker exists but no daemon; requires external trigger
2. **Browser automation** — Governance layer over minimal actual automation
3. **Connectors** — Only GitHub implemented; OAuth missing
4. **Ephemeral memory** — Per-process only, not shared
5. **Tauri integration** — Bootstrap exists but runtime incomplete
6. **Command bus** — Tables exist but not wired into runtime

**Misleading docs/spec areas:**
- Changelog mentions "Google Drive connector with OAuth2 flow" — Not implemented
- Changelog mentions "Notion connector" — Not implemented
- Changelog mentions "Slack connector" — Not implemented
- Browser agent routes imply full automation — Only governance implemented

**Fastest wins to convert PARTIAL → SHIPPED:**
1. Enable cron worker daemon (add scheduler loop trigger)
2. Add OAuth flow UI for GitHub connector
3. Connect ephemeral memory to Redis (shared across processes)
4. Add connector UI to frontend
5. Implement management panel shell

---

## SECTION 6 — Claim hygiene

### Safe public claims
- "Chat threading with project organization and branching"
- "Document upload with automatic RAG embedding"
- "Image gallery and management"
- "Secure shareable links for threads and documents"
- "Configurable AI companion identity with system prompt management"
- "Context depth modes for controlling retrieval scope"
- "GitHub connector for repository synchronization"
- "Local-first architecture with Docker Compose"

### Claims to avoid until verified
- "Scheduled automation with built-in scheduler" → Use "Scheduled job API (external scheduler required)"
- "Browser agent for web automation" → Use "Browser governance and approval system"
- "Multi-platform messaging adapters" → Not implemented
- "Google Drive/Notion/Slack connectors" → Only GitHub exists
- "Desktop app" → Use "Local runtime with Docker"
- "OAuth integration" → Use "API key based authentication"

---

*Audit complete. When in doubt, downgrade the claim. Truth first.*
