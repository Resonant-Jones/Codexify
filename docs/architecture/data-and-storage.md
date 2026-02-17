# Data and Storage

Purpose: Provide an implementation-aligned map of where Codexify data lives, which entities matter most, and what invariants/risk assumptions changes must preserve.
Last updated: 2026-02-17
Source anchors:
- guardian/db/models.py
- guardian/core/pgdb.py
- guardian/core/dependencies.py
- guardian/queue/redis_queue.py
- guardian/queue/task_events.py
- guardian/routes/media.py
- guardian/workers/document_embed_worker.py
- guardian/routes/cron.py
- guardian/routes/websocket.py
- guardian/routes/health.py
- docker-compose.yml
- frontend/src/lib/providerPref.ts

## Storage Systems in Use

| System | Usage in current code | Key anchors |
|---|---|---|
| Postgres (primary system of record) | Threads/messages, projects, media metadata, docs, events outbox, cron jobs/runs, permissions/audit | `guardian/db/models.py`, `guardian/core/pgdb.py`, `guardian/core/dependencies.py` |
| Redis | Async task queues, cancellation set, per-thread turn locks, task event streams | `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py` |
| Vector store (Chroma or FAISS) | Semantic retrieval for chat + ingestion embeddings | `guardian/vector/store.py`, `backend/rag/embedder.py`, `guardian/context/broker.py` |
| Neo4j (optional) | Graph context/logging and federation graph snapshot features | `guardian/context/broker.py`, `guardian/routes/federation.py`, `docker-compose.yml` |
| File/object storage | Uploaded/generated media bytes and TTS outputs (`src_url` references) | `guardian/core/storage.py`, `guardian/routes/media.py` |
| Browser local/session storage | UI preferences/auth token/provider selection | `frontend/src/lib/api.ts`, `frontend/src/lib/providerPref.ts` |

## Key Entities (Most Operationally Relevant)

### Core conversation + memory

| Entity/Table | Why it matters | Notes |
|---|---|---|
| `projects` | Parent grouping for threads/resources | `identity_depth` constrained to `light|deep` |
| `chat_threads` | Primary conversation container | `project_id`, `parent_id`, `archived_at`, profile metadata |
| `chat_messages` | Ordered per-thread conversation records | `thread_id` FK cascade; `kind` defaults `chat` |
| `memory_entries` | Ephemeral/midterm/longterm memory storage | `silo` check constraint enforced |
| `personal_facts` | User-fact memory graph with confidence/status | status + confidence constrained |
| `personal_fact_evidence` | Evidence links to facts and optional source message | fact delete cascades, message link `SET NULL` |
| `personal_fact_revisions` | Audit of fact changes | fact delete cascades |

### Media / documents / generation

| Entity/Table | Why it matters | Notes |
|---|---|---|
| `media_assets` | Canonical content identity and dedupe root | active identity uniqueness index by project/kind/provenance/hash |
| `media_aliases` | Human-facing aliases for canonical assets | alias type constrained |
| `uploaded_images` | User-uploaded image references | soft delete (`deleted_at`) |
| `generated_images` | Generated image references | soft delete (`deleted_at`) |
| `uploaded_documents` | Uploaded docs + parse/embed lifecycle | `embedding_status` constrained (`pending|processing|ready|failed`) |
| `generated_documents` | LLM-generated documents | `format` constrained (`txt|md|docx|pdf|html|json`) |
| `thread_documents` | Thread <-> document linkage | `relation` constrained (`autosave|attached|reference`) |
| `tts_outputs` | Synthesized audio metadata | optional project/thread ownership |

### Events / audit / sharing / jobs

| Entity/Table | Why it matters | Notes |
|---|---|---|
| `events_outbox` | Durable SSE feed source | tenant-scoped outbox polling/deletion |
| `event_graph_events` | Idempotent event lineage/audit | `idempotency_key` unique |
| `audit_log` | Generic mutation audit rows | entity + entity_id indexed |
| `shared_links` | Thread/document share token mapping | `target_type` constrained |
| `collaboration_permissions` | Document-level access control | `(document_id,user_id)` uniqueness index |
| `collaboration_audit_log` | Collaboration action history | document/user indexed |
| `ws_audit_log` | WebSocket RPC request audit | params hash + duration |
| `cron_jobs` | Scheduled job definitions | enabled/status lifecycle through runs |
| `cron_runs` | Durable execution outcomes | status constrained (`queued|running|succeeded|failed`) |
| `connector_configs` | External connector settings | one-to-many runs/raw docs |
| `connector_runs` | Connector sync execution rows | status/error/document_count |
| `raw_documents` | Connector raw payload staging | unique per (`config_id`,`external_id`) |
| `sync_jobs` | Connector sync job bookkeeping | runtime support table for connector orchestration |

## Relationship and Invariant Rules the Code Relies On

- `chat_messages.thread_id -> chat_threads.id` uses `ON DELETE CASCADE`; deleting a thread removes its chat messages (`guardian/db/models.py`).
- `chat_threads.updated_at` is bumped when `create_message` succeeds; many UI listings rely on this for recency ordering (`guardian/core/pgdb.py`).
- Turn concurrency invariant: only one assistant completion per thread at a time via Redis lock key `turn_lock:{thread_id}` (`guardian/queue/redis_queue.py`, `guardian/routes/chat.py`, `guardian/workers/chat_worker.py`).
- `uploaded_documents.embedding_status` drives ingestion UX and retry semantics (`guardian/routes/media.py`, `guardian/workers/document_embed_worker.py`).
- Media dedupe invariant depends on `media_assets` active identity unique index with `deleted_at IS NULL` predicate (`guardian/db/models.py`, `guardian/routes/media.py`).
- Outbox consumers assume monotonic `events_outbox.id` for resume/cleanup semantics (`guardian/guardian_api.py`, `guardian/core/event_bus.py`).
- Cron execution assumes `cron_runs` row exists before queue execution and is updated in place through terminal state (`guardian/cron/scheduler.py`, `guardian/workers/cron_worker.py`).
- WebSocket audit assumes a configured DB session factory; otherwise route still runs with noop DB adapter (`guardian/routes/websocket.py`).

## Lifecycle Rules

- Soft-delete surfaces:
  - `uploaded_images.deleted_at`
  - `generated_images.deleted_at`
  - `uploaded_documents.deleted_at`
  - `generated_documents.deleted_at`
  - `media_assets.deleted_at`
- Hard-delete/cascade surfaces:
  - deleting `chat_threads` cascades messages and linked FK rows where defined with `ON DELETE CASCADE`.
  - deleting `cron_jobs` cascades `cron_runs`.
  - deleting `connector_configs` cascades `connector_runs` and `raw_documents`.
- Event outbox retention:
  - `/api/events` consumer deletes events through last delivered id for tenant to prevent unbounded growth (`guardian/guardian_api.py`).
- Memory retention:
  - `MEMORY_RETENTION_DAYS` exists as config flag, but explicit pruning workflow is Unverified from current runtime code scan. Verify in memory worker/maintenance jobs outside scanned paths.

## Data Risk Hotspots

- API auth tokens and session/JWT secrets are environment-driven and can be accepted from multiple secret keys (`GUARDIAN_SESSION_SECRET`, `GUARDIAN_JWT_SECRET`, `GUARDIAN_API_KEY` compatibility path).
  - Evidence: `guardian/core/dependencies.py`.
  - Risk: secret sprawl and mixed-mode auth confusion.
- Raw uploaded content, parsed document text, and generated text are persisted in plaintext columns.
  - Evidence: `uploaded_documents.parsed_text`, `generated_documents.content`, `chat_messages.content` in `guardian/db/models.py`.
- Websocket audit stores method and params hash (not raw params) but identity linkage still exists.
  - Evidence: `guardian/routes/websocket.py`, `ws_audit_log` model.
- Collaboration and share link tables expose document/thread access edges; token leakage is high impact.
  - Evidence: `shared_links`, `collaboration_permissions` in `guardian/db/models.py`.
- Redis queue/event data is operationally critical but non-durable by default configuration (`appendonly no` in Compose).
  - Evidence: `docker-compose.yml` Redis command.
- Encryption at rest assumptions are Unverified for Postgres volume, Chroma path, and media store.
  - Verify via host/cloud disk encryption and storage backend configuration (not represented in this repo).

