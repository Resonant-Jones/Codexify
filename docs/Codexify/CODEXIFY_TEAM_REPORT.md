# Codexify — Internal Team Report

**Audience:** the team. Anyone who hasn't touched the codebase yet, plus anyone who has and wants a single shared mental model.
**Date:** 2026-06-07
**Status of the project at time of writing:** v0.9.0 series, actively developed. Beta-tagged in places, with some surfaces explicitly stubbed (see *Honest Caveats* below).

---

## 1. TL;DR

Codexify is a **local-first AI conversation and knowledge workspace**. It pairs a FastAPI backend called **Guardian** with a React/TypeScript UI, runs a real Postgres + Redis + (optional) Neo4j stack, and gives you a single app for chat, memory, documents, retrieval, and scheduled jobs — with the LLM provider, embedding model, and storage all swappable and all running on your own machine by default.

It's not a thin wrapper around someone else's API. It's a full multi-tier system with its own queue, its own runtime contract, its own command bus, and its own desktop shell. If you've ever wished for "ChatGPT-quality UX but with my data, my model, my memory, and a real API underneath," Codexify is what this team built.

**Why we built it (the short version):** every off-the-shelf "local AI" tool we tried collapsed in one of three ways — (1) it leaked data to a cloud we didn't approve, (2) it had no real persistence or retrieval story, or (3) it had no extensibility surface, so we ended up writing glue code around the glue code. Codexify is the answer to all three.

---

## 2. What Codexify Actually Is

Strip away the marketing and Codexify is a four-piece system:

| Layer | What it is | Where it lives in the repo |
|---|---|---|
| **Guardian backend** | A FastAPI service. Owns routing, auth, queue, persistence, the LLM provider registry, the command bus, the federation surface. | `guardian/` |
| **Workers** | Background processes for chat, chat embeddings, document embeddings, and warmup. They consume the Redis queue and write back to Postgres. | `guardian/workers/`, `codex_runner/` |
| **Web + Desktop UI** | React + Vite + Tailwind frontend. Same code runs in the browser (port 5173) and inside a Tauri desktop shell. | `frontend/src/`, `src-tauri/` |
| **Infra** | Postgres (system of record), Redis (queues, task events, locks, heartbeats), optional Neo4j (graph context), local embedding model under `./models`, optional vector store (FAISS or Chroma). | `docker-compose.yml`, `backend/` |

It's a **multi-tier event-driven** system, in the words of our own architecture docs (`docs/architecture/system-overview.md`):

> frontend → route → queue → worker → persistence → events

The most important sentence in that sequence: **any step may succeed while downstream steps fail or lag.** The team has been disciplined about not conflating "request accepted" with "request completed," or "event published" with "UI received." That's the foundation of the runtime contract — see §5.

The supported way to run the whole thing is **Docker Compose**. The repo ships a single `docker compose up --build` that brings up Postgres, Redis, Neo4j, the backend, all four workers, the frontend, the TTS microservice, the warmup worker, and the one-shot migrator / graph-init / model-prep services. There is no Kubernetes or Nomad story in the repo — it's intentionally Compose-first.

---

## 3. What You Can Do With It Today

The README's own list of implemented features is the cleanest starting point, so I'll restate and group it.

### 3.1 Chat that actually behaves like a product

- Threaded conversations with **parent/child hierarchies**, archival, and project-based organization.
- **Message roles** (user / assistant / system), with thread summaries and pagination.
- **Streaming responses over Server-Sent Events** from `/api/events` and `/api/tasks/{task_id}/events`.
- **Multi-provider routing** at the backend, with a live provider registry:
  - **Local first:** Ollama, LM Studio, Whoosh'd (MLX on Apple Silicon). This is the default.
  - **Cloud when explicitly enabled:** OpenAI, Groq, Alibaba DashScope, **MiniMax** (Anthropic-compatible by default, with prompt caching and thinking-block preservation).
  - **Disabled but classified:** Anthropic, Gemini — they exist in the registry but won't be routed.
- **Tool use, but bounded.** If a model emits a structured tool decision, the completion service executes *exactly one* command through the command bus, reinjects the result, and asks for one final assistant answer. One turn. Not an open-ended agent loop.

### 3.2 Memory, with a real model

- **Three-tier memory silos** — `ephemeral`, `midterm`, `longterm` — with heat-based eviction, semantic indexing, and a CR(UD) API.
- **Tagging and pinning** so a memory entry doesn't get pruned just because it's old.
- **Memory retrieval is part of the chat context**, not a separate feature. The context broker calls the memory retriever alongside vector search and document lookup.

### 3.3 Documents and knowledge

- **Upload images and documents.** Metadata goes to Postgres (`uploaded_images`, `uploaded_documents`); bytes go to disk.
- **Autosave + share documents** with secure share tokens.
- **Embed and search** via FAISS or Chroma. First boot auto-downloads the default local embedding model (bge-large-en-v1.5) into `./models`.
- **Project + thread document links** with a typed relation (`autosave`, `attached`, `reference`).
- **Workspace-source mode** widens retrieval to user-bounded local knowledge, including Obsidian-backed notes, while keeping the user boundary explicit.

### 3.4 Extensibility

- **Command bus** (`guardian/command_bus/`) — derives callable commands from the OpenAPI spec, enforces policy and idempotency, exposes a single invoke surface, and supports loopback HTTP for same-process calls.
- **Cron and scheduled jobs** with run history (`guardian/cron/`, `guardian/workers/cron_worker.py`).
- **Plugin architecture** with manifest-based loading. Ships with pattern-analyzer, memory-analyzer, and system-diagnostics plugins. You can scaffold your own with `make init-plugin`.
- **Connectors** for GitHub, Google Drive, Notion, and a ChatGPT history importer (CLI profile).
- **Federation / sync** for peer-node context sharing, with relay, diff, and context endpoints.

### 3.5 Surfaces

- **Web UI** at `http://localhost:5173`.
- **API** at `http://localhost:8888` (with auto-generated docs at `/docs`).
- **Tauri desktop shell** (macOS-first). Same frontend code; manual build/release gate, not a CI artifact.
- **Live event stream** the UI subscribes to for real-time updates.

---

## 4. The Runtime Topology (What Boots When You Run It)

This is the part most people underestimate. The Compose default is not a single backend container — it's a small fleet.

**Always-on services:**
- `db` — Postgres 15
- `redis` — queues, task events, locks, heartbeats
- `neo4j` — graph store, started by default but **graph usage is feature-flagged** (`GUARDIAN_ENABLE_GRAPH_CONTEXT`, `GUARDIAN_ENABLE_GRAPH_LOGGING`)
- `backend` — FastAPI app on port 8888
- `frontend` — Vite dev server on port 5173
- `worker-chat` — consumes chat completion tasks
- `worker-chat-embed` — backfills embeddings for chat messages
- `worker-warmup` — warms up local models on boot
- `tts` — separate FastAPI TTS microservice on port 8000 *(see caveats: not integrated into the main API)*

**One-shot services (run, then exit):**
- `migrator` — Alembic migrations + `seed_defaults.py`
- `graph-init` — Neo4j constraints and seed nodes
- `model-prep` — ensures the embedding model is present, downloads on first boot

**Profiles (off by default):**
- `cli` → `chatgpt-migrate` (ChatGPT import)
- `backfill` → `embedding-backfill`, `graph-backfill`

**Startup order matters:** Postgres + Neo4j → graph-init → migrator → model-prep → backend (verifies required tables and re-seeds) → workers. This is wired in `docker-compose.yml` with `depends_on` and healthchecks. If you ignore it you'll get cryptic failures — the README has a "if something fails to start" section for a reason.

---

## 5. The Chat Runtime Contract (Why This Is More Than a Toy)

The most important architectural decision in the project is the **separation of provider state from request state**. From `docs/architecture/chat-runtime-contract.md`:

**Provider runtime states:**
`OFFLINE`, `CONNECTING`, `RUNTIME_AVAILABLE`, `MODEL_WARMING`, `READY`, `GENERATING`, `DEGRADED`, `ERROR`

**Request lifecycle states:**
`QUEUED`, `DISPATCHING`, `AWAITING_ACK`, `AWAITING_MODEL`, `AWAITING_FIRST_TOKEN`, `STREAMING`, `COMPLETED`, `CANCELLED`, `TIMED_OUT`, `FAILED_RETRYABLE`, `FAILED_FATAL`, `ORPHANED`, `REPLAYED`

Three rules that come out of this:

1. **A slow or warming model is not offline.** The UI distinguishes "connecting" / "warming" / "ready" — it doesn't collapse to a binary dot. Anyone who's watched a "loading" spinner for 45 seconds knows why this matters.
2. **A timed-out request may still complete later.** The state machine tracks `ORPHANED` vs `COMPLETED` explicitly. The transcript stays intact; we never quietly drop content.
3. **Retries are new attempts, not new messages.** `messageId` is the stable authored turn identity; `requestId` is the execution attempt identity. A replayed attempt is `attemptNumber = 2`, not a second user message.

This is genuinely unusual discipline for an app of this size. Most "local AI" tools do not model these states at all, and it shows in their UX (you'll see "something went wrong" banners that don't tell you whether the model is slow, the request timed out, or the worker died). Codexify's UI has typed status presentations for each of the 13 request states.

---

## 6. How a Chat Completion Actually Flows

If you've ever debugged a stuck AI request and wanted to know which layer to blame, this is the part you'll want to remember. The full chat completion path, end to end:

1. **Frontend** creates a durable thread via `POST /api/chat/threads` (first-send flow), then posts the first user message to `POST /api/chat/{thread_id}/messages`, then queues completion.
2. **Route** (`guardian/routes/chat.py`) validates the thread, checks depth context, acquires a Redis turn lock, and enqueues a `ChatCompletionTask`.
3. **Chat worker** (`guardian/workers/chat_worker.py`) pulls the task, calls the completion service.
4. **Completion service** (`guardian/core/chat_completion_service.py`) builds the message bundle via the **context broker**: recent messages, vector matches, project/thread documents, memory retrieval, optional graph/federated context. If `source_mode="workspace"`, it widens to Obsidian-backed local notes while preserving the user boundary.
5. **Provider call** — through the provider registry, which validates against the configured provider, the egress allowlist, and the live model inventory (for `discovery_backed` providers like Alibaba and MiniMax).
6. **Optional tool turn** — if the model emits a structured tool decision, the worker executes exactly one command through the command bus, reinjects the result, and requests one final assistant answer.
7. **Persist** the assistant message.
8. **Emit** task events and outbox events; UI consumes both.

When you're staring at a request that isn't completing, the failure modes to distinguish are:
- **Queue backlog** — Redis is up but workers are saturated.
- **Worker stall** — Redis is up, queue is empty, but the worker is dead or wedged.
- **Provider degraded** — model is reachable but slow/warming.
- **Request timeout** — request timed out client-side; the worker may still complete and persist (orphaned attempt).
- **Persistence lag** — worker finished, write hasn't committed yet.

These are all *different bugs* with *different fixes*. The runtime contract is what lets you tell them apart.

---

## 7. Why It's Worth Trying

Here's the honest pitch for a teammate who's on the fence.

**1. You can actually keep your data local.** This is the headline. Postgres, Redis, the embedding model, the local LLM endpoint — all of it runs on your machine. The default profile is `CODEXIFY_LOCAL_ONLY_MODE=true` and the egress allowlist is empty. The cloud path is opt-in per-provider and gated by `ALLOW_CLOUD_PROVIDERS`. If you've been told "private AI" by a SaaS vendor and didn't believe them, this is the alternative.

**2. The provider story is real, not a marketing checkbox.** There's a **provider governance contract** (`guardian/core/provider_registry.py`) that classifies every provider into `discovery_backed`, `static_authorized`, `local_only`, or `disabled`. The router, the catalog, the health endpoint, and runtime model-selection all derive from this single source of truth. You don't end up with hardcoded provider lists scattered across 12 files. The MiniMax integration alone (Anthropic-compatible default, prompt caching, thinking-block preservation) is a few hundred lines, not a few thousand — because the registry absorbs the variability.

**3. The runtime contract is production-grade.** Provider states, request states, message-vs-attempt identity, replay handling, task events, durable outbox. Most "AI wrapper" projects skip all of this and then spend a year reinventing it badly. We have it on day one.

**4. The extension surface is clean.** The command bus is the canonical invoke path. Cron is real cron, not "setTimeout in a component." Plugins are manifest-loaded and isolated. Connectors are typed. Federation is feature-flagged but the peer session, diff, and context endpoints are implemented. If you need to bolt on a new capability, you bolt it onto one of these seams, not a fresh abstraction.

**5. There are real surfaces, not just a web app.** Web UI, Tauri desktop, the API itself, the event stream. The same frontend bundle is what runs in the desktop shell, and the desktop shell can inject the backend URL and API key — so the "give a teammate a desktop build" path is real. The Tauri build is currently a manual release gate, not a CI artifact, which is a fair tradeoff for a beta.

**6. You can read the docs and trust them.** `docs/architecture/system-overview.md` starts with source anchors for every claim, and the `supported-path-proof-*.md` files in the same directory are dated evidence, not vibes. `docs/architecture/adr/` has ADRs. `docs/help/CODEXIFY_HELP_AND_FAQ.md` is short and won't lie to you. The codebase has its own AGENTS.md and CLAUDE.md enforcing the "smallest truthful fix" discipline.

**7. You can run it in 5 minutes.** `cp .env.template .env` → set `GUARDIAN_API_KEY`, `NEO4J_PASS`, point `LOCAL_BASE_URL` at your Ollama → `docker compose up --build` → open `http://localhost:5173`. The first boot is slow because it downloads the embedding model; every boot after that is fast.

---

## 8. Honest Caveats — What This Is *Not*

I'm not going to oversell this. There are real things that are stubbed, deferred, or beta:

- **TTS in the main API is a mock.** The API returns a sine-wave stub. A separate HuggingFace TTS microservice exists at `backend/tts_service` but **is not integrated into the main API**. If TTS is on your critical path, that's a real gap.
- **RAG upload endpoint `/upload-chat` returns 503.** The README states this explicitly: it requires a missing module (`codexify.rag.enhanced_rag`). Don't depend on it today.
- **Embeddings API `/api/embeddings` returns dummy vectors by default.** Real embeddings are wired in the worker stack, but the public endpoint only returns real vectors when a real backend is configured. The fallback flag exists for testing.
- **Image generation is partial.** The OpenAI path is implemented; `local` and `stability` are deferred and can return 503.
- **Neo4j is wired but optional.** The container starts by default, but graph reads/writes are behind feature flags. Most users won't notice.
- **Federation is sensitive.** Peer session, diff, and context endpoints exist, but the security model is explicit (signature/auth/policy in route code, not prompts). Don't turn it on without reading `docs/architecture/federation*`.
- **RAG trace debug endpoint is in-memory only.** It clears on restart. Don't build tooling that depends on it surviving a reboot.
- **Frontend tests are not wired into the Python test path.** Vitest, Playwright, and Cypress configs exist under `frontend/src/`, but `make test` only runs the backend suite. If you break the UI, run `pnpm test` in `frontend/`.
- **No production deployment story in the repo.** No Kubernetes, no Nomad, no Helm. The supported topology is "Compose on a trusted host." If you need to scale beyond that, you're doing it yourself for now.
- **Beta stability doc still flags real concerns.** The beta changelog (`CHANGELOG.beta.md`) is explicit that "chat-loop dependency coupling," "contract drift in tool primitives," "sync delivery not yet durable," and "federation subscriptions are process-local" are all still open. These are honest warnings, not hidden bugs.

Read the README's *What This Repo Actually Is* section. It deliberately lists "implemented" vs "wired but off" vs "experimental / stubbed / partially wired." That taxonomy is the source of truth.

---

## 9. How to Get Started

For a teammate who just wants to kick the tires:

```bash
# 1. Get the code
git clone <repo> codexify && cd codexify

# 2. Configure
cp .env.template .env
# Edit .env — at minimum:
#   GUARDIAN_API_KEY=<long random token>
#   NEO4J_PASS=<password>
#   LOCAL_BASE_URL=http://host.docker.internal:11434/v1   # Ollama
#   LOCAL_LLM_MODEL=<your model tag>
#   LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5

# 3. Make sure Ollama is running and has a model pulled
ollama pull llama3.2

# 4. Boot the whole stack
docker compose up --build

# 5. Verify
curl http://localhost:8888/ping
# Open http://localhost:5173
```

First boot takes a few minutes while `model-prep` downloads the embedding model. After that, boot is fast.

**Troubleshooting commands you'll reach for:**
```bash
docker compose ps
docker compose logs backend
docker compose logs worker-chat
docker compose logs worker-document-embed
```

If you want to dig into the code, the high-signal entry points are:
- `guardian/guardian_api.py` — FastAPI wiring
- `guardian/routes/chat.py` — chat endpoints
- `guardian/workers/chat_worker.py` — chat completion worker
- `guardian/context/broker.py` — context assembly
- `guardian/command_bus/` — tool execution
- `frontend/src/features/chat/ChatView.tsx` — chat UI
- `frontend/src/App.tsx` — app shell
- `docs/architecture/system-overview.md` — runtime map

---

## 10. Key Takeaways

- **Codexify is a local-first AI conversation and knowledge workspace**, not a thin wrapper. It runs a real multi-tier system (FastAPI + Postgres + Redis + workers + React + Tauri) on your own machine.
- **It is genuinely local by default.** Local-only mode, no cloud egress, no telemetry to vendors. Cloud is opt-in, per-provider, gated by an egress allowlist.
- **The runtime contract is unusually disciplined for this category of software.** Provider state, request state, message vs attempt identity, replay handling, durable outbox. The UX benefits show up as fewer confusing "is it broken or just slow?" moments.
- **The extension surface is real.** Command bus, cron, plugins, connectors, federation. If you need to add capability, you add it to one of these seams.
- **Multi-provider is the default, not a switch.** Ollama / LM Studio / Whoosh'd locally; OpenAI / Groq / Alibaba / MiniMax in the cloud; Anthropic and Gemini are classified and disabled in the registry. Switching providers does not mean rewriting your app.
- **The web UI, the desktop app, and the API are all first-class surfaces.** Same frontend code in the browser and in the Tauri shell.
- **It is beta, and the team is honest about that.** TTS is a stub, the RAG upload endpoint is 503, image gen is partial, sync isn't durable end-to-end, federation is process-local. The README's "implemented / wired but off / experimental" taxonomy is the source of truth — read it before you promise anything to a customer.
- **You can have it running in five minutes.** That's not a slogan; the only thing slowing down the first boot is the embedding model download.

If you've been looking for an AI workspace you can actually trust with your data, your model choice, and your workflow, this is the project for that. Try it, and bring feedback — the team is shipping fast and the gap between "what's in the README" and "what's in main" is measured in days, not months.

---

*Sources used to write this report: `README.md`, `CLAUDE.md`, `AGENTS.md`, `CHANGELOG.md`, `CHANGELOG.beta.md`, `docs/architecture/system-overview.md`, `docs/architecture/chat-runtime-contract.md`, `docs/architecture/providers.md`, `docs/Codexify/Codexify-Master-Architecture-Report.md`, `docs/Codexify/Codexify-System-Specification.md`, `docs/help/CODEXIFY_HELP_AND_FAQ.md`, `frontend/src/App.tsx`, `guardian/guardian_api.py`, `guardian/providers/`. Repo state as of 2026-06-07.*
