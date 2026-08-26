Purpose: Map where Codexify stores state today, which entities carry the most architectural weight, and which invariants or exposure points change work must preserve.
Last updated: 2026-08-24
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
| Postgres | Projects, threads, messages, Hosted Room metadata, memories, media metadata, durable account-import jobs/checkpoints, documents, audit logs, command runs, cron runs, collaboration data, provider state | `guardian/db/models.py`, `guardian/core/db.py`, `guardian/db/migrations/` |
| Postgres account observability | Guardian-owned invite lineage, pseudonymous guest identities, account metadata, and content-free foreground presence sessions; presence rows and unconverted guest lineage are retention-governed | `guardian/db/models.py`, `guardian/account_observability/`, `guardian/db/migrations/versions/b2c3d4e5f6a7_add_account_observability_foundation.py` |
| Redis | Chat queue, account-import queue, document/chat-embed/cron queues, cancellation set, canonical turn locks, task-event streams, worker heartbeat keys, turn-completion anchor cache, health-probe queue round-trip, queue-depth observation | `guardian/queue/redis_queue.py`, `guardian/queue/account_import_queue.py`, `guardian/queue/task_events.py`, `guardian/queue/turn_lock.py`, `guardian/workers/chat_worker.py`, `guardian/routes/health.py` |
| Vector store | Semantic retrieval corpus for messages and documents | `guardian/vector/store.py`, `guardian/runtime/embed/embedder.py`, `guardian/context/broker.py` |
| File or object storage | Uploaded/generated media bytes and document/image/audio artifacts exposed through the signed media surface | `guardian/core/storage.py`, `guardian/routes/media.py` |
| Private import staging | Complete account-export bytes between browser transfer and worker completion; separate from the signed `/media` root | `guardian/core/storage.py`, `guardian/services/openai_account_import.py`, `docker-compose.yml` |
| Neo4j | Optional graph context/logging and federation graph features | `guardian/context/broker.py`, `guardian/routes/federation.py`, `docker-compose.yml` |
| Browser local/session storage | Auth tokens, runtime overrides, shell state, drafts, UI preferences, cached session spine | `frontend/src/lib/api.ts`, `frontend/src/lib/runtimeConfig.ts`, `frontend/src/state/session/SessionSpine.ts` |
| In-process buses | Fallback event fanout and the lightweight sync subscription bus | `guardian/core/event_bus.py`, `guardian/sync/bus.py` |

### Vector store authority and derived-state retirement

The vector store is a derived retrieval/index artefact, not canonical application authority: Postgres remains the sole source of truth, and semantic retrieval corpus state is never promoted to authority. When a persisted Chroma index cannot be consumed by the supported `chromadb==1.0.15` runtime, [[adr/067-operator-approved-derived-chroma-retirement|ADR-067]] governs the operator-approved preserve-retire-rebuild handling: the historical bytes must be preserved as evidence before the active index is retired, a fresh store is initialised exclusively through the canonical runtime, no records are copied from the retired store into the fresh one, and restoration of the historical store requires a separate ADR-gated task.

## Key Entities and Collections

### Core chat and knowledge entities

| Entity | Why it matters | Key invariants |
|---|---|---|
| `projects` | Top-level ownership and grouping boundary for threads and documents | `identity_depth` constrained to `light` or `deep` |
| `chat_threads` | Primary conversation container | can be archived, nested via `parent_id`, and tied to a project/profile; carries one immutable canonical `origin_system` token (`codexify` / `openai` / `anthropic`) recorded at canonical creation |
| `chat_messages` | Ordered conversation state | hard-linked to thread by FK with cascade delete; assistant rows may carry durable completion breadcrumbs in `extra_meta` |
| `memory_entries` | Stored episodic/semantic memory | `silo` constraint and retrieval policy dependence |
| `personal_facts` | Higher-level fact memory | confidence/status constraints drive fact lifecycle |
| `personal_fact_evidence` | Evidence rows that tie facts back to messages or sources | fact delete cascades; message link may be nullable |
| `personal_fact_revisions` | Fact history | supports auditability of memory changes |

### Account authentication entities

| Entity | Why it matters | Key invariants |
|---|---|---|
| `users` | Canonical account and authentication boundary | `id` remains the durable ownership identifier; `username` is unique; nullable `email` is a normalized, unique login alias only; password material remains one-way hashed. Resolving an email alias must return the existing `users.id` and must not rewrite account ownership, username, role, or password state. |
| `user_profiles` | Account-owned presentation metadata | 1:1 with `users.id`; profile fields do not replace canonical account identity. |

### Hosted Room persistence entities

The persistence foundation governed by [[adr/053-node-hosted-room-access-boundary|ADR-053]] provides storage truth for the bounded Hosted Room owner, guest-session, message, and explicit Guardian-invocation routes. ADR-053 remains `Proposed`; implemented code paths do not establish release qualification or cross-node Hosted Room support.

| Entity | Why it matters | Key invariants |
|---|---|---|
| `hosted_rooms` | Account-owned lifecycle and collaboration boundary | one owner account; one unique canonical `chat_threads` reference; unique slug; status is `active` or `closed`; no access credential |
| `hosted_room_invites` | Room-scoped invitation lineage | one room; status is `pending`, `accepted`, `revoked`, or `expired`; only a unique token hash is stored; intended display name is not identity proof |
| `hosted_room_participants` | Room-scoped human and resident-agent identity | one room; kind is `human` or `agent`; role is `owner`, `member`, or `agent`; state is `active` or `removed`; one invitation resolves to at most one participant; ON DELETE SET NULL from chat_messages |

One Hosted Room maps to exactly one canonical `chat_threads` row. Messages remain exclusively in `chat_messages`; none of the Hosted Room tables is a transcript store. Room metadata is scoped through `owner_account_id`. A guest participant may have no bound Codexify account, while an agent participant must not bind to a user account.

### Chat message Hosted Room provenance

`chat_messages` now carries optional paired provenance fields for room-participant authorship:

- `hosted_room_participant_id` (String(36), nullable, FK → `hosted_room_participants.id` ON DELETE SET NULL)
- `sender_display_name_snapshot` (String(255), nullable, immutable after creation)

Paired-nullability constraint: both fields are NULL (ordinary messages) or both are non-NULL with a non-blank snapshot (room messages). No default provenance is backfilled onto historical messages.

The canonical message-persistence interface treats these fields as one optional
paired contract. Partial pairs, blank participant IDs, and blank or
whitespace-only snapshots are rejected before persistence. The application check
is an early failure boundary; the database paired-provenance constraint remains
authoritative for every supported database path. Valid provenance is written in
the initial `chat_messages` insert, not backfilled or applied by a post-insert
update.

The sender snapshot preserves the participant's display label at send time so transcript readability survives:
- participant display-name changes
- participant removal (SET NULL on FK)
- participant deletion (SET NULL on FK)

The provenance migration includes a narrow database trigger that clears the
paired display snapshot when the foreign key action nulls the participant ID.
This preserves the strict paired-nullability check while retaining the message
row and its content.

The snapshot is presentation metadata only — not global identity proof, not an email field, not a Contact reference, and not a live reference to the participant's current display name.

For a metadata-bearing Hosted Room Guardian completion, the worker validates the
room, source message, actor participant, requester authority, invitation lineage,
and lifecycle state before using this paired contract. The actor participant ID
and `Guardian` display snapshot are present before the initial assistant insert;
there is no post-insert provenance update and no second transcript. Ordinary
messages and ordinary assistant completions omit both values. Provenance is not
backfilled from display names, and database constraints remain the final
authority for paired nullability.

Hosted Room message routes verify:
- participant belongs to the room
- room's backing thread equals the message thread
- participant is active
- room is active
- requester is authorized as that participant or owner

No Contact, presence, IP address, device fingerprint, or telemetry fields exist on chat messages. Export/restore posture: participant provenance is part of canonical transcript metadata; sender snapshots are exportable; participant IDs may require remapping during restore; executable export/restore support remains deferred.

The enabled resident-agent field is a bounded, inspectable list of existing agent identifiers; it is not a second agent registry or a persisted capability-grant set. Contact persistence is not introduced here, so invitation intent retains only an intended display-name snapshot and does not claim Contact identity.

No ambient-presence, device, location, behavioral, or cross-node synchronization state is stored. Bounded owner creation, invitation exchange, room-scoped sessions, authorization, human message operations, and explicit Guardian invocation are implemented. Contacts workflows, RoomShell, management UI, non-Guardian agent invocation, cross-node rooms, and release qualification remain unimplemented.

### Existing-instance migration reconciliation

An existing-instance migration may recognize physical schema that is already
correct for the migration's canonical definition. Recognition requires exact
structural validation of the relevant columns, nullability, constraints,
foreign keys, and indexes; it is not an unconditional `IF NOT EXISTS` skip.
Incompatible structures or existing data that cannot satisfy a new constraint
must fail closed with bounded evidence. Schema/history reconciliation still
occurs through normal Alembic execution and version advancement. Stamping,
direct `alembic_version` edits, and manual schema repair are not substitutes
for migration execution.

### Restored Watchdog and Connections migration lineage

The deployed GitHub Watchdog lineage is represented by the exact historical
revisions 2a6b7c8d9e0f through 6e9f0a1b2c3. Its terminal revision and the
independent Connections revision d2e3f4a5b6c7 share
1c0a2b3c4d5e as their parent. Revision 9c66e490a42b is their sole
metadata-only Alembic merge head: it performs no schema operations and records
that both sibling histories are required.

The associated compatibility proof covers clean, historical-Watchdog,
current-Connections, and backup-derived disposable Postgres databases. It does
not migrate the qualifying database. That database remains at
6e9f0a1b2c3 until a separately authorized live migration window uses the
canonical migrator; manual stamping, direct version-table edits, and manual DDL
remain prohibited.

### Canonical conversation-origin column

`chat_threads.origin_system` is the authoritative conversation-origin truth
surface for every canonical thread. The bounded registry is defined in
`guardian.conversation_origin` and is enforced at the storage layer by a
CHECK constraint on `chat_threads`. The canonical values are exactly:

- `codexify` — the conversation was originally created inside Codexify.
- `openai` — the conversation was originally created in ChatGPT or another
  OpenAI surface.
- `anthropic` — the conversation was originally created in Claude or another
  Anthropic surface.

`origin_system` is set at canonical creation only and is immutable under
ordinary thread mutation. Title change, summary change, project move,
archive, unarchive, persona assignment, retrieval configuration change,
provider switch, and ordinary completion activity must never alter
`origin_system`. The column is the canonical filter surface for owner-scoped
thread queries (for example, the `GET /api/chat/threads?origin_system=...`
route). A composite index on `(user_id, origin_system)` backs that filter.

Legacy product labels — `chatgpt`, `openai`, `claude`, `anthropic`,
`gpt`, `open_ai`, `anthropic_claude` — are not canonical `origin_system`
values and are recognized only at the migration / import-compatibility
boundary. They map deterministically onto the canonical registry:
ChatGPT/OpenAI tokens become `openai`; Claude/Anthropic tokens become
`anthropic`; any thread without explicit historical import provenance
becomes `codexify`. Free-form strings are never canonical values; unknown
external systems must fail closed rather than being silently mapped.

Imported-source product metadata — `import_source`, `import_profile`,
`source_thread_id`, source-message identifiers, raw import envelopes —
remains subordinate provenance for audit and backward compatibility and
must not be used as the authoritative conversation-origin filter after this
invariant is established.

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
| `openai_account_import_jobs` | Account-owned intake manifest, lifecycle counters, bounded diagnostics, and restart checkpoint | status constrained to canonical account-import tokens; owner and declared counts are required |
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
| `user_profiles` | Account-owned presentation metadata | 1:1 with `users.id`; `accent_color` is non-null, constrained to canonical token set `['default','blue','cyan','emerald','amber','rose','violet','slate']`, server default `'default'`. |

## Relationships the Code Relies On

- `chat_threads -> chat_messages`
  - assistant persistence, thread recency ordering, and thread deletion assume this FK remains intact.
- `users -> hosted_rooms -> chat_threads`
  - the owner account scopes each room; each backing thread is unique to one room; deleting a room does not delete the referenced thread or its messages.
- `hosted_rooms -> hosted_room_invites/hosted_room_participants`
  - invitation and participant state is room-scoped; room deletion removes its authority-bearing dependent metadata, while participant removal and room closure retain historical rows.
- `hosted_room_invites -> hosted_room_participants`
  - an invitation may originate at most one participant; deleting an invitation clears that optional lineage reference rather than deleting the participant.
- `chat_messages -> hosted_room_participants`
  - optional structured participant authorship provenance; ON DELETE SET NULL preserves transcript history when a participant is deleted; a durable sender display-name snapshot preserves readability even after participant removal or display-name change.
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
- `openai_account_import_jobs -> media_assets`
  - imported media keeps the job ID, export fingerprint, source-relative path, message/thread identifiers, and append-only import-lineage evidence; deleting a job clears the direct FK without erasing media.
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
- Postgres is the source of truth for account-import lifecycle and restart checkpoints.
  - Redis publication is required for route acceptance but is not the durable lifecycle record.
  - The dedicated worker re-enqueues `queued`/`running` jobs on startup because the shared Redis list dequeue is destructive.
  - Entity batches commit before `account_import.batch_committed` is emitted; an event is not allowed to manufacture persistence truth.
- Imported image provenance is evidence-bound.
  - explicit user-message attachment evidence is `uploaded`
  - explicit assistant/tool generation metadata is `generated`
  - absent or conflicting evidence is `unclassified`
  - filenames alone never establish source provenance
- Federation and collaboration access are explicit, not ambient.
  - Anchors: `guardian/routes/federation.py`, `guardian/realtime/collaboration.py`, `guardian/db/models.py`
- Hosted Room storage does not itself grant authority.
  - Invitation exchange, room sessions, and owner/guest route authorization are enforced by their bounded runtime paths; network reachability, UI behavior, cross-node operation, and release qualification remain separate proof surfaces.
  - Invitation values are stored only as hashes, and display names or optional account bindings are not ambient authority.

### Soft delete and archival surfaces

- `chat_threads.archived_at` archives threads without removing them.
- `media_assets.deleted_at`, `uploaded_documents.deleted_at`, `uploaded_images.deleted_at`, `generated_documents.deleted_at`, and `generated_images.deleted_at` act as soft-delete boundaries.
- Deduplication logic relies on active rows where `deleted_at IS NULL`.

### Cascade and retention behavior

- `chat_messages` delete with their thread.
- `hosted_rooms` delete with the owner account or backing thread; deleting a Hosted Room does not cascade upward to its backing thread or transcript.
- `hosted_room_invites` and `hosted_room_participants` delete with their room. Deleting an invite sets an originating participant reference to null so participant history is retained.
- `cron_runs` delete with their parent cron job.
- Connector runs and raw documents delete with connector configs.
- `/api/events` can delete durable outbox rows through the last delivered event ID for a tenant, so outbox retention is consumption-shaped rather than archival.
- Private account-import staging is retained after terminal completion in this slice so job diagnostics and restart evidence are not invalidated. Automated staging garbage collection is deferred and must be account/job aware when added.
- Failed zero-write account-import jobs may be explicitly retried by the owning account through `POST /api/imports/openai-account/{job_id}/retry`. Canonical staging visibility is required; historical paths outside the active staging root are unsupported. Retry does not move or duplicate staged bytes. Original failure receipts remain durable in `error_details`. Retry-attempt evidence is append-only under `checkpoint.retry_attempts`. Zero-write gating protects against duplicate canonical imports; partial-write retry remains unsupported.
- Memory retention pruning is `Unverified`; a config surface exists, but a repo-scanned maintenance path was not confirmed.

## Data Risk Hotspots

- PII surfaces:
  - `chat_messages.content`
  - `uploaded_documents.parsed_text`
  - `generated_documents.content`
  - `personal_facts` and related evidence
  - private staged OpenAI export files, which may contain complete account history and attachments
- Secret-bearing surfaces:
  - `oauth_connections` stores encrypted access and refresh token material
  - browser storage can hold session or API key material depending on mode
  - `hosted_room_invites.token_hash` is a non-plaintext verifier; plaintext invitation credentials must never be persisted
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
- `codexify:queue:account-import`
  - dedicated OpenAI account-export work queue; payloads contain only job/account identity, while file manifests and checkpoints remain in Postgres
  - startup recovery republishes durable `queued`/`running` jobs after worker restart; this is resume support, not exactly-once queue delivery
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

## Account Observability Persistence (Internal Slices 1–3)

Migration `b2c3d4e5f6a7` owns the Guardian tables for invite definitions, pseudonymous guest lineage, canonical account observability metadata, and content-free foreground presence sessions. The runtime writers are `guardian.account_observability.invites` for first-touch invite lineage, `guardian.routes.auth` for registration conversion, and `guardian.account_observability.presence` for explicit foreground heartbeats. Ordinary API, message, model, document, and route traffic does not write presence or account `last_seen_at`.

`POST /api/account-observability/heartbeat` resolves authenticated accounts through Guardian's signed session seam. It resolves guests from the server-issued `codexify_guest_attribution` cookie only after `record_heartbeat` verifies a live canonical guest row; malformed, fabricated, absent, and soft-deleted guest identities fail closed. The writer persists no raw or hashed IP, user-agent, route, page, message, thread, project, content, referrer, device fingerprint, or precise-geography value.

`guardian.account_observability.retention.run_cleanup` owns deterministic row-level cleanup and is exposed through `POST /api/operator/account-observability/retention/cleanup` with dry-run support. It closes open leases whose latest accepted heartbeat is strictly older than 30 minutes, deletes presence rows whose `created_at` is strictly older than 30 days in batches of 500, and soft-deletes guest lineage strictly older than 90 days only when no converted-account metadata requires that lineage. Converted attribution is deferred, invite definitions and canonical account registration metadata are preserved, and each run returns execution/cutoff timestamps plus expired, deleted, and deferred counts.

This is internal capability evidence only. GeoIP, aggregates, operator reporting reads, UI, and supported-path proof remain absent.
