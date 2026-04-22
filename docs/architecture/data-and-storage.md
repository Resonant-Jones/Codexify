Purpose: Map where Codexify stores state today, which entities carry the most architectural weight, and which invariants or exposure points change work must preserve.
Last updated: 2026-04-22
Source anchors:
- guardian/db/models.py
- guardian/db/migrations/
- guardian/core/db.py
- guardian/core/storage.py
- guardian/core/event_bus.py
- guardian/core/outbox.py
- guardian/queue/
- guardian/routes/
- guardian/workers/
- guardian/context/
- guardian/vector/
- guardian/runtime/embed/
- guardian/command_bus/
- guardian/realtime/
- guardian/sync/
- docker-compose.yml
- frontend/src/

# Data and Storage

## Storage Systems in Use

| System | What it stores today | Key anchors |
|---|---|---|
| Postgres | Projects, threads, messages, memories, media metadata, documents, audit logs, command runs, cron runs, collaboration data, provider state | `guardian/db/models.py`, `guardian/core/db.py`, `guardian/db/migrations/` |
| Redis | Chat queue, document/chat-embed/cron queues, cancellation set, canonical turn locks, task-event streams, worker heartbeat keys, turn-completion anchor cache, health-probe queue round-trip, queue-depth observation | `guardian/queue/redis_queue.py`, `guardian/queue/task_events.py`, `guardian/queue/turn_lock.py`, `guardian/workers/chat_worker.py`, `guardian/routes/health.py` |
| Vector store | Semantic retrieval corpus for messages and documents | `guardian/vector/store.py`, `guardian/runtime/embed/embedder.py`, `guardian/context/broker.py` |
| File or object storage | Raw uploaded/generated media bytes and document/image/audio artifacts | `guardian/core/storage.py`, `guardian/routes/media.py` |
| Neo4j | Optional graph context/logging and federation graph features | `guardian/context/broker.py`, `guardian/routes/federation.py`, `docker-compose.yml` |
| Browser local/session storage | Auth tokens, runtime overrides, shell state, drafts, UI preferences, cached session spine | `frontend/src/lib/api.ts`, `frontend/src/lib/runtimeConfig.ts`, `frontend/src/state/session/SessionSpine.ts` |
| In-process buses | Fallback event fanout and the lightweight sync subscription bus | `guardian/core/event_bus.py`, `guardian/sync/bus.py` |

## Key Entities and Collections

### Core chat and knowledge entities

| Entity | Why it matters | Key invariants |
|---|---|---|
| `projects` | Top-level ownership and grouping boundary for threads and documents | `identity_depth` constrained to `light` or `deep` |
| `chat_threads` | Primary conversation container | can be archived, nested via `parent_id`, and tied to a project/profile |
| `chat_messages` | Ordered conversation state | hard-linked to thread by FK with cascade delete |
| `eval_trace_snapshots` | Durable post-completion trace snapshots for derived inspection | attempt-scoped, thread-linked, and persisted only after assistant completion |
| `eval_verdicts` | Attempt-scoped evaluator verdicts | each row links back to one trace snapshot and one evaluator run |
| `memory_entries` | Stored episodic/semantic memory | `silo` constraint and retrieval policy dependence |
| `personal_facts` | Higher-level fact memory | confidence/status constraints drive fact lifecycle |
| `personal_fact_evidence` | Evidence rows that tie facts back to messages or sources | fact delete cascades; message link may be nullable |
| `personal_fact_revisions` | Fact history | supports auditability of memory changes |

### Documents, media, and generated artifacts

| Entity | Why it matters | Key invariants |
|---|---|---|
| `media_assets` | Canonical dedupe root for uploaded/generated assets | uniqueness is scoped by active identity fields with `deleted_at IS NULL` |
| `media_aliases` | Alternate references to canonical assets | alias type constrained |
| `uploaded_documents` | Parsed text, embedding lifecycle, storage reference | `embedding_status` drives RAG availability |
| `generated_documents` | LLM-produced docs linked to users/threads/projects | `format` constrained |
| `thread_documents` | Thread-to-document linkage for RAG and UI | `relation` constrained to known link semantics |
| `project_document_links` | Project-level document scope for context assembly | used by `ContextBroker` to widen doc context |
| `uploaded_images` | User-uploaded image metadata | soft delete via `deleted_at` |
| `generated_images` | AI-generated image metadata | soft delete via `deleted_at` |
| `tts_outputs` | Synthesized audio outputs | may be connected back to thread/project/message context |
| `message_audio_assets` | Message-to-audio attachment map | lets chat output pick up voice artifacts |

### Operational and control-plane entities

| Entity | Why it matters | Key invariants |
|---|---|---|
| `audit_log` | Generic mutation audit trail | many routes append here after state changes |
| `events_outbox` | Durable source for `/api/events` | consumers rely on monotonically increasing IDs |
| `event_graph_events` | Idempotent event lineage | `idempotency_key` uniqueness is relied on |
| `inference_providers` | Catalog-backed provider inventory | synced from `/api/llm/catalog` at startup |
| `inference_provider_runtime` | Runtime health and capability state | kept in sync with provider catalog bootstrap |
| `tool_jobs` | Orphaned tool orchestration table | historical migration artifact; ORM model removed, and upgraded databases may still carry inert rows/tables until a dedicated drop migration is applied |
| `command_runs` | Command bus execution record | captures actor, auth subject, status, args hash, idempotency |
| `command_run_events` | Streamable command bus events | ordered by run-local sequence |
| `cron_jobs` | Saved schedules | validation constrains schedule grammar and target types |
| `cron_runs` | Run history for cron executions | status transitions are `queued -> running -> terminal` |
| `sync_jobs` | Connector/sync support bookkeeping | ensured at startup |
| `oauth_connections` | Encrypted token-bearing connection state | uniqueness on `(user_id, provider, mode)` |
| `shared_links` | Share tokens for thread/document access | token leakage is high impact |
| `collaboration_permissions` | Explicit per-document access rules | uniqueness on `(document_id, user_id)` |
| `collaboration_audit_log` | Collaboration activity trace | backs auditability on shared docs |
| `ws_audit_log` | WebSocket RPC audit trail | stores method, hashes, and latency metadata |

## Relationships the Code Relies On

- `chat_threads -> chat_messages`
  - assistant persistence, thread recency ordering, and thread deletion assume this FK remains intact.
- `chat_threads -> eval_trace_snapshots -> eval_verdicts`
  - post-completion eval snapshots and verdicts are derived inspection artifacts; they must stay linked to the original attempt and remain outside the completion acceptance path.
- `projects -> chat_threads`
  - project identity depth affects whether chat can run `deep` retrieval modes.
- `projects -> project_document_links -> uploaded_documents/generated_documents`
  - project-scoped docs are part of normal and deep context assembly.
- `chat_threads -> thread_documents -> uploaded_documents/generated_documents`
  - thread-linked docs flow directly into the RAG path.
- `command_runs -> command_run_events`
  - command bus SSE streaming assumes ordered append-only event sequences.
- `cron_jobs -> cron_runs`
  - scheduler/worker logic assumes a run row exists before execution starts.
- `media_assets -> uploaded_documents/uploaded_images/generated_images`
  - dedupe and alias behavior depend on canonical asset identity outliving individual references.
- `personal_facts -> personal_fact_evidence/personal_fact_revisions`
  - fact mutation and evidence display rely on these dependent rows staying consistent.

## Invariants and Lifecycle Rules

### Hard invariants

- Only one assistant turn should be in flight per thread at a time.
  - Canonical enforcement is the Redis turn-lock path in `guardian/queue/turn_lock.py`, used by `guardian/routes/chat.py` and the chat worker lifecycle.
  - `guardian/queue/redis_queue.py` still contains older helper functions for turn-lock behavior, but that is no longer the main path the chat route relies on.
- Chat completion, cron execution, and document embedding are queue-backed, not fire-and-forget in the API process.
  - Anchors: `guardian/routes/chat.py`, `guardian/routes/cron.py`, `guardian/queue/document_embed_queue.py`
- Post-completion eval is derived and non-gating.
  - assistant message persistence triggers a best-effort trace snapshot + eval enqueue, but completion success still depends only on the existing chat acceptance/persistence path.
- Postgres is the source of truth for conversation, document metadata, command runs, and audit state.
  - Anchors: `guardian/core/db.py`, `guardian/db/models.py`
- Federation and collaboration access are explicit, not ambient.
  - Anchors: `guardian/routes/federation.py`, `guardian/realtime/collaboration.py`, `guardian/db/models.py`

### Soft delete and archival surfaces

- `chat_threads.archived_at` archives threads without removing them.
- `media_assets.deleted_at`, `uploaded_documents.deleted_at`, `uploaded_images.deleted_at`, `generated_documents.deleted_at`, and `generated_images.deleted_at` act as soft-delete boundaries.
- Deduplication logic relies on active rows where `deleted_at IS NULL`.

### Cascade and retention behavior

- `chat_messages` delete with their thread.
- `cron_runs` delete with their parent cron job.
- Connector runs and raw documents delete with connector configs.
- `/api/events` can delete durable outbox rows through the last delivered event ID for a tenant, so outbox retention is consumption-shaped rather than archival.
- Memory retention pruning is `Unverified`; a config surface exists, but a repo-scanned maintenance path was not confirmed.

## Data Risk Hotspots

- PII surfaces:
  - `chat_messages.content`
  - `uploaded_documents.parsed_text`
  - `generated_documents.content`
  - `personal_facts` and related evidence
- Secret-bearing surfaces:
  - `oauth_connections` stores encrypted access and refresh token material
  - browser storage can hold session or API key material depending on mode
- Access-control assumptions:
  - API access control is route/auth-layer enforced; the DB schema itself does not encode every user ownership rule
  - collaboration and share-link security depends on token and permission handling, not row-level security
- Durability assumptions:
  - Redis is operationally critical but is configured in Compose without durable persistence guarantees
  - sync bus and some event fanout paths are still process-local
- Encryption at rest:
  - Infra-level encryption for Postgres volumes, Neo4j data, and local media storage is `Unverified` in this repo

## Redis Responsibilities In The Chat Path

Redis currently carries multiple distinct responsibilities for the main chat loop:

- `codexify:queue:chat`
  - primary completion work queue consumed by `guardian/workers/chat_worker.py`
- `turn_lock:{thread_id}`
  - per-thread mutual exclusion so only one assistant turn is in flight
  - canonical implementation lives in `guardian/queue/turn_lock.py`
- `codexify:task:{task_id}:events`
  - task-event stream used for `task.created`, `task.running`, `task.progress`, and terminal task events
- `codexify:queue:cancelled`
  - cancellation membership set checked by the worker before and during execution
- `codexify:worker:chat:heartbeat`
  - worker freshness signal read by `/health/chat` and stale-lock recovery logic
- `codexify:chat:turn-anchor:{thread_id}:{turn_id}`
  - short-lived turn-anchor cache used to correlate a completed assistant message back to a turn when DB metadata lookup is unavailable or delayed
- `codexify:queue:chat-embed`
  - background embedding queue for chat messages adjacent to the main completion path
- health-probe queue keys
  - `/health/chat` creates an ephemeral probe queue and performs a bounded push/pop round trip
  - this proves Redis queue operations are reachable for that probe, not end-to-end completion progress
- queue-depth observation
  - `/health/chat` samples `LLEN(codexify:queue:chat)` and compares it to the previous sample to classify queue progress as `progressing`, `stalled`, or `unknown`
  - this is a heuristic over sampled backlog depth, not proof that a worker has dequeued a specific task

## Canonical Vs Legacy Turn-Lock Helpers

- Canonical path
  - `guardian/queue/turn_lock.py`
  - stores structured lock envelopes with owner task id, turn id, lease token, acquire/renew timestamps, and TTL-derived expiry
  - supports safe conditional release and explicit stale-lock inspection
- Older helper surface
  - `guardian/queue/redis_queue.py` still contains older turn-lock helper functions and constants
  - treat those as compatibility or legacy helper code, not the authoritative architecture path for chat turn ownership

## Health and Queue Observation Boundaries

- `/health/chat` uses Redis for:
  - a bounded enqueue/dequeue probe
  - worker heartbeat inspection
  - queue-depth sampling
- Those checks are useful but limited:
  - the probe queue proves Redis queue round-trip reachability, not that `worker-chat` is consuming `codexify:queue:chat`
  - queue depth only supports a heuristic about forward progress between two samples
  - neither surface proves UI receipt of task events

## Storage Mismatch and Drift Signals

- Vector-store configuration is split:
  - `guardian/vector/store.py` defaults to a configurable store abstraction
  - `guardian/workers/document_embed_worker.py` currently instantiates the runtime embedder with `store="chroma"`
- This means retrieval and embedding paths should be treated as a coupled surface during provider or vector-backend changes.
