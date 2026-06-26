# Continuity Storage Schema Proposal

> Classification: docs-only storage schema proposal
> Status: proposed
> Implementation status: no migrations, models, tables, or runtime writes exist
> Normative language: "must", "must not", "should", "candidate", "proposed", and "Phase A/B" are intentional.

Purpose: Define the proposed Postgres storage schema for future persisted Continuity Protocol Suite records after the pure contracts and deterministic compiler harness. This is a docs-only proposal. It does not add migrations, SQLAlchemy models, tables, routes, workers, runtime persistence, compiler wiring, UI, browser capture, graph writes, sync, or provider-routing behavior.

Last updated: 2026-06-25

## Purpose

The Continuity Protocol Suite currently exists as:
- A docs-only architecture contract (`continuity-protocol-suite.md`)
- A candidate token-domain proposal (`continuity-token-domain-proposal.md`)
- Pure backend dataclass contracts (`guardian/continuity/contracts.py`)
- A deterministic compiler harness (`guardian/continuity/compiler.py`)

What does not yet exist is a proposal for how these structures would be persisted in Postgres. Without a storage schema proposal, a future implementation task could accidentally:

- Collapse raw transcripts, retrieved evidence, compiled state, and UI brief data into one table
- Lose provenance chains that distinguish packet origin from compiled assertion
- Create un-indexed JSONB blobs that defeat purposeful query patterns
- Bundle graph dependencies into baseline storage requirements
- Ignore export/restore provenance obligations
- Add migrations without clear rollback or retention policies

This proposal defines the smallest viable Phase A persistence boundary, optional Phase B normalization, candidate constraints, index strategies, and migration/rollback considerations — all without creating a single migration file.

This is step 4 of ADR-030's approved implementation order (Postgres schema proposal for persisted packet/state records).

## Non-Goals

This proposal does not, and must not be interpreted as:

- creating an Alembic migration
- adding a SQLAlchemy model class
- writing runtime persistence code
- wiring the compiler harness to storage
- adding a worker
- adding an API route
- implementing Project Pulse UI
- implementing browser capture
- enabling graph writes
- implementing sync behavior
- implementing provider-routing changes
- implementing export/restore for continuity records
- widening the supported beta release promise
- creating a database table on disk

## Storage Boundary Model

Continuity storage must preserve distinct boundaries between these conceptual layers. Collapsing them into one table creates provenance loss and query ambiguity.

| Layer | What It Holds | Owned By | Storage Status |
|---|---|---|---|
| Raw messages | Thread conversation history | `chat_messages` (existing) | Implemented |
| Retrieved evidence | Semantic/vector results per turn | Context broker (in-memory) | Ephemeral; some trace snapshots in `eval_trace_snapshots` |
| Context packets | Structured evidence envelopes from all source surfaces | `continuity_context_packets` (proposed) | Not implemented |
| Compiled Reality State | Compiled truth for a scope | `continuity_reality_states` (proposed) | Not implemented |
| Reality Commits | Durable point-in-time snapshots of Reality State | `continuity_reality_commits` (proposed) | Not implemented |
| Compiler proof / run metadata | Determinism keys, input packet sets, errors/warnings per compilation | `continuity_compiler_runs` (proposed Phase B) | Not implemented |
| Project Pulse UI | Rendered brief surfaces from Reality State | Frontend only (read model) | Not implemented; not a storage concern |
| Optional graph enrichment | Relationship traversal, visualization, offline analysis | Neo4j (optional mount) | Not required for baseline; existing graph flags govern |

Postgres owns baseline durable continuity truth. Optional graph mounts may enrich relationship traversal, visualization, and offline analysis but must not become the canonical store of continuity truth. The no-graph Postgres path must remain fully functional for persistence, query, and export.

## Existing Storage Anchors

Per `data-and-storage.md`, the current storage landscape is:

| System | Current Role | Continuity Impact |
|---|---|---|
| Postgres | System of record for projects, threads, messages, memories, documents, audit, command runs, cron runs | Future continuity tables join here |
| Redis | Queue transport, turn locks, task events, worker heartbeats | Continuity workers would use existing Redis infrastructure; no new Redis keys proposed in this schema |
| Vector store | Semantic retrieval corpus for messages and documents | Context packets may be indexed for retrieval; not part of Phase A schema |
| File/object storage | Raw media bytes | Packet payloads may reference file artifacts; references only in Phase A |
| Neo4j | Optional graph context/logging | Not required for baseline continuity storage; enrichment only |
| Browser storage | Auth, runtime overrides, UI state | Client-local state only; not part of this schema |

New continuity tables extend the existing Postgres system-of-record role. They do not replace Redis, vector, file storage, or graph systems. They add envelope records with indexed envelope fields and JSONB payloads.

## Proposed Phase A Tables

Phase A is the smallest viable persistence layer. It stores only envelope records — the envelope fields are explicitly columnar; the variable-structured content lives in JSONB. Phase A does not normalize decisions, open loops, rejected paths, or compiler runs into their own tables.

| Table | Purpose | Phase |
|---|---|---|
| `continuity_context_packets` | Persisted Context Packet envelopes with indexed kind, scope, sensitivity, retention | A |
| `continuity_reality_states` | Compiled Reality State snapshots with extracted JSON sub-records | A |
| `continuity_reality_commits` | Durable Reality Commit records with trigger, kind, and provenance | A |
| `continuity_state_packet_links` | Many-to-many provenance link between states and their contributing packets | A |

All tables are proposed only. No implementation exists.

## Proposed Table: continuity_context_packets

### Purpose

Persist structured evidence envelopes from any source surface (thread, browser, git, artifact, persona, provider, plugin). Envelope fields are explicit columns; variable packet payloads live in JSONB.

### Proposed Columns

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `UUID` or `SERIAL` | NOT NULL | Primary key |
| `schema_version` | `VARCHAR(32)` | NOT NULL | Packet schema version |
| `kind` | `VARCHAR(64)` | NOT NULL | From `ContextPacketKind` candidate domain |
| `user_id` | `VARCHAR(128)` | NOT NULL | Scoping user |
| `project_id` | `VARCHAR(128)` | NULL | Project scope |
| `thread_id` | `VARCHAR(128)` | NULL | Thread scope |
| `task_id` | `VARCHAR(128)` | NULL | Task scope |
| `tab_id` | `VARCHAR(128)` | NULL | Browser tab scope |
| `persona_id` | `VARCHAR(128)` | NULL | Persona scope |
| `node_id` | `VARCHAR(128)` | NULL | Node scope (federation) |
| `team_id` | `VARCHAR(128)` | NULL | Team scope (candidate only) |
| `dyad_id` | `VARCHAR(128)` | NULL | Dyad scope (candidate only) |
| `source_system` | `VARCHAR(128)` | NOT NULL | Emitting system |
| `source_plugin` | `VARCHAR(128)` | NULL | Plugin identifier |
| `source_provider` | `VARCHAR(128)` | NULL | Provider identifier |
| `origin_ref` | `VARCHAR(256)` | NULL | External reference |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Packet creation time |
| `summary` | `TEXT` | NOT NULL | Human-readable summary |
| `payload_json` | `JSONB` | NOT NULL | Structured evidence payload |
| `metadata_json` | `JSONB` | NULL | Source-specific metadata |
| `provenance_json` | `JSONB` | NULL | Source chain (packet IDs, commit IDs, message IDs, artifact IDs) |
| `sensitivity` | `VARCHAR(32)` | NOT NULL | From `ContextPacketSensitivity` candidate domain; default `local` |
| `retention` | `VARCHAR(32)` | NOT NULL | From `ContextPacketRetention` candidate domain; default `session` |
| `integrity_json` | `JSONB` | NULL | Content hash or integrity marker |
| `deleted_at` | `TIMESTAMPTZ` | NULL | Soft delete marker |

### Proposed Indexes

| Index | Columns | Purpose |
|---|---|---|
| `ix_cty_packets_project_created` | `project_id, created_at DESC` | Latest packets per project |
| `ix_cty_packets_thread_created` | `thread_id, created_at DESC` | Latest packets per thread |
| `ix_cty_packets_user_created` | `user_id, created_at DESC` | Latest packets per user |
| `ix_cty_packets_kind_created` | `kind, created_at DESC` | Packets by kind over time |
| `ix_cty_packets_retention` | `retention` | Retention policy filtering |
| `ix_cty_packets_sensitivity` | `sensitivity` | Sensitivity filtering |
| `ix_cty_packets_active` | Partial index: `WHERE deleted_at IS NULL` | Exclude soft-deleted rows |

### Retention and Export Notes

- `sensitivity = 'local'` or `'private'`: Export only in full-account export.
- `sensitivity = 'restricted'`: Never export without explicit opt-in.
- `retention = 'ephemeral'`: May be evicted without persistence (implementation choice).
- `retention = 'expires'`: Additional `expires_at` column may be added in implementation.
- `deleted_at` follows existing Codexify soft-delete convention (matching `media_assets`, `uploaded_documents`, etc.).

## Proposed Table: continuity_reality_states

### Purpose

Persist compiled Reality State snapshots. This is the canonical compiled truth surface for any scope. It holds the full serialized state plus extracted JSON sub-records for queryability.

### Proposed Columns

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `UUID` or `SERIAL` | NOT NULL | Primary key |
| `schema_version` | `VARCHAR(32)` | NOT NULL | State schema version |
| `scope` | `VARCHAR(32)` | NOT NULL | From `RealityScope` candidate domain |
| `user_id` | `VARCHAR(128)` | NOT NULL | Scoping user |
| `project_id` | `VARCHAR(128)` | NULL | Project scope ID |
| `thread_id` | `VARCHAR(128)` | NULL | Thread scope ID |
| `task_id` | `VARCHAR(128)` | NULL | Task scope ID |
| `node_id` | `VARCHAR(128)` | NULL | Node scope ID |
| `team_id` | `VARCHAR(128)` | NULL | Team scope ID (candidate only) |
| `dyad_id` | `VARCHAR(128)` | NULL | Dyad scope ID (candidate only) |
| `compiled_at` | `TIMESTAMPTZ` | NOT NULL | Compilation timestamp |
| `active_branch` | `VARCHAR(256)` | NULL | Active conceptual branch |
| `source_packet_ids_json` | `JSONB` | NOT NULL | Ordered list of contributing packet IDs |
| `state_json` | `JSONB` | NOT NULL | Full serialized RealityState snapshot |
| `accepted_decisions_json` | `JSONB` | NULL | Extracted DecisionRecord array for queryability |
| `open_loops_json` | `JSONB` | NULL | Extracted OpenLoopRecord array for queryability |
| `rejected_paths_json` | `JSONB` | NULL | Extracted RejectedPathRecord array for queryability |
| `active_artifacts_json` | `JSONB` | NULL | Extracted active artifact references |
| `assumptions_json` | `JSONB` | NULL | Extracted assumption strings |
| `risks_json` | `JSONB` | NULL | Extracted risk strings |
| `next_actions_json` | `JSONB` | NULL | Extracted next-action strings |
| `confidence` | `FLOAT` | NULL | Overall compilation confidence (0.0–1.0 or NULL) |
| `provenance_json` | `JSONB` | NULL | Source chain from contributing artifacts |
| `expires_or_decays_at` | `TIMESTAMPTZ` | NULL | Expiry/decay timestamp |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Row creation time |
| `deleted_at` | `TIMESTAMPTZ` | NULL | Soft delete marker |

### Proposed Indexes

| Index | Columns | Purpose |
|---|---|---|
| `ix_cty_states_scope_compiled` | `scope, compiled_at DESC` | Latest state per scope type |
| `ix_cty_states_project_compiled` | `project_id, compiled_at DESC` | Latest project reality |
| `ix_cty_states_thread_compiled` | `thread_id, compiled_at DESC` | Latest thread reality |
| `ix_cty_states_user_compiled` | `user_id, compiled_at DESC` | Latest states per user |
| `ix_cty_states_expires` | `expires_or_decays_at` | States nearing expiry |
| `ix_cty_states_active` | Partial index: `WHERE deleted_at IS NULL` | Exclude soft-deleted rows |

### Notes

- `state_json` is the canonical full serialized contract snapshot in Phase A. It is the source of truth for the compiled state at that point in time.
- Extracted JSON columns (`accepted_decisions_json`, `open_loops_json`, etc.) support inspection and query without normalizing every nested record into its own table immediately. They are derived from `state_json` at write time and must remain consistent with it.
- Phase B may normalize decisions, open loops, and rejected paths into their own tables if query patterns justify it.

## Proposed Table: continuity_reality_commits

### Purpose

Persist durable Reality Commit records. Each commit captures a point-in-time Reality State snapshot along with the trigger, kind, and provenance that explain why it was created.

### Proposed Columns

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `UUID` or `SERIAL` | NOT NULL | Primary key |
| `schema_version` | `VARCHAR(32)` | NOT NULL | Commit schema version |
| `scope` | `VARCHAR(32)` | NOT NULL | From `RealityScope` candidate domain |
| `kind` | `VARCHAR(64)` | NOT NULL | From `RealityCommitKind` candidate domain |
| `trigger` | `VARCHAR(64)` | NOT NULL | From `RealityCommitTrigger` candidate domain |
| `title` | `TEXT` | NOT NULL | Human-readable commit title |
| `summary` | `TEXT` | NOT NULL | Human-readable commit summary |
| `user_id` | `VARCHAR(128)` | NOT NULL | Scoping user |
| `project_id` | `VARCHAR(128)` | NULL | Project scope ID |
| `thread_id` | `VARCHAR(128)` | NULL | Thread scope ID |
| `task_id` | `VARCHAR(128)` | NULL | Task scope ID |
| `node_id` | `VARCHAR(128)` | NULL | Node scope ID |
| `team_id` | `VARCHAR(128)` | NULL | Team scope ID (candidate only) |
| `dyad_id` | `VARCHAR(128)` | NULL | Dyad scope ID (candidate only) |
| `source_packet_ids_json` | `JSONB` | NULL | Contributing packet IDs |
| `previous_state_id` | `UUID` or `VARCHAR` | NULL | FK to `continuity_reality_states.id` |
| `new_state_id` | `UUID` or `VARCHAR` | NULL | FK to `continuity_reality_states.id` |
| `provenance_json` | `JSONB` | NULL | Source chain (packet, commit, message, artifact IDs) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Commit creation time |
| `deleted_at` | `TIMESTAMPTZ` | NULL | Soft delete marker |

### Proposed Indexes

| Index | Columns | Purpose |
|---|---|---|
| `ix_cty_commits_project_created` | `project_id, created_at DESC` | Commit history per project |
| `ix_cty_commits_thread_created` | `thread_id, created_at DESC` | Commit history per thread |
| `ix_cty_commits_scope_created` | `scope, created_at DESC` | Commit history per scope type |
| `ix_cty_commits_kind_created` | `kind, created_at DESC` | Commits by kind over time |
| `ix_cty_commits_trigger_created` | `trigger, created_at DESC` | Commits by trigger over time |
| `ix_cty_commits_new_state` | `new_state_id` | Reverse lookup from state → commit |
| `ix_cty_commits_active` | Partial index: `WHERE deleted_at IS NULL` | Exclude soft-deleted rows |

### Notes

- Reality Commit is not a Git commit. Git-backed export or storage is future optional follow-through, not Phase A persistence.
- The `previous_state_id` → `new_state_id` chain supports delta reconstruction and history browsing.
- Discovery Commits are a subset of Reality Commits (`kind` discriminates them). They use the same table. Additional Discovery Commit metadata (before/after conceptual state, impact radius) may live in `state_json` of the referenced `new_state_id` or in a Phase B extension.

## Proposed Table: continuity_state_packet_links

### Purpose

Many-to-many provenance link between compiled Reality States and the Context Packets that contributed to them. This link table supports provenance queries and explainability without duplicating packet content inside state records.

### Proposed Columns

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `UUID` or `SERIAL` | NOT NULL | Primary key |
| `state_id` | `UUID` or `VARCHAR` | NOT NULL | FK to `continuity_reality_states.id` |
| `packet_id` | `UUID` or `VARCHAR` | NOT NULL | FK to `continuity_context_packets.id` |
| `relationship` | `VARCHAR(64)` | NOT NULL | Link type (e.g., `contributed`, `replaced`, `superseded`) |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Link creation time |

### Proposed Constraints

- **Unique**: `(state_id, packet_id, relationship)` — no duplicate link triples.
- **FK cascade policy**: Must be decided before migration. Options:
  - `ON DELETE CASCADE` from `state_id` (if deleting a state, remove all its links).
  - `ON DELETE RESTRICT` (if preserving link history, soft-delete links instead).
- **FK references**: `state_id` → `continuity_reality_states.id`, `packet_id` → `continuity_context_packets.id`. Use UUIDs or consistent ID types.

### Notes

- This table exists so that "which packets contributed to this state?" can be answered in a single indexed join without parsing `source_packet_ids_json` inside the state row.
- The `relationship` column allows future expansion (e.g., a packet that was considered but excluded, or a packet that superseded a prior packet).

## Proposed Phase B Tables

Phase B tables are optional normalization steps after Phase A proves useful with real traffic. They should only be created when query patterns, storage size, or operator use-cases justify the additional migration complexity.

| Table | Purpose | Why Deferred | Proof Required |
|---|---|---|---|
| `continuity_open_loops` | Normalize open loops from `open_loops_json` into rows | JSONB extraction is sufficient for Phase A queries; row-per-loop overhead for small datasets | Query latency > acceptable threshold or per-loop lifecycle tracking required |
| `continuity_rejected_paths` | Normalize rejected paths from `rejected_paths_json` into rows | Same rationale as open loops | Path re-opening frequency justifies row-level tracking |
| `continuity_decisions` | Normalize accepted decisions from `accepted_decisions_json` into rows | Decision count is typically low per project | Decision-chaining or cross-project decision queries required |
| `continuity_compiler_runs` | Persist compiler execution metadata for determinism proofs | Compiler is currently pure and stateless; no execution runtime exists | Compiler becomes stateful or operator needs to audit compilation history |
| `continuity_project_pulse_snapshots` | Cache pre-computed Project Pulse briefs for UI | Pulse is a UI read surface, not storage; caches are ephemeral | UI latency requires pre-computed briefs; `continuity_cache_state` governs freshness |

## Proposed Table: continuity_compiler_runs (Phase B)

If Phase B activates compiler run persistence, the following table is proposed.

### Purpose

Persist compiler execution metadata to support determinism proofs, operator audit, and future compiler version upgrades. Compiler runs are proof/diagnostic records and do not replace Reality State.

### Proposed Columns

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `id` | `UUID` or `SERIAL` | NOT NULL | Primary key |
| `compiler_version` | `VARCHAR(64)` | NOT NULL | Version of compiler used |
| `schema_version` | `VARCHAR(32)` | NOT NULL | Schema version at compile time |
| `input_packet_ids_json` | `JSONB` | NOT NULL | Ordered list of input packet IDs |
| `output_state_id` | `UUID` or `VARCHAR` | NULL | FK to `continuity_reality_states.id` |
| `errors_json` | `JSONB` | NULL | Compilation error messages |
| `warnings_json` | `JSONB` | NULL | Per-packet validation warnings |
| `ignored_packet_ids_json` | `JSONB` | NULL | Packet IDs excluded from compilation |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | Run timestamp |
| `duration_ms` | `INTEGER` | NULL | Compilation wall-clock duration |
| `determinism_key` | `VARCHAR(128)` | NULL | Hash of inputs for determinism verification |
| `provenance_json` | `JSONB` | NULL | Compiler provenance metadata |

### Notes

- Compiler runs are diagnostic records. Operator debug surfaces may consume them. User-facing Pulse must not.
- The `determinism_key` enables re-compilation verification: same inputs + same compiler version → same determinism_key.

## Candidate Constraints and Token Domains

When storage constraints are implemented, they must align with the token-domain proposal. The following columns are storage-constrained and require canonical token alignment:

| Column | Token Domain | Candidate Values Documented In |
|---|---|---|
| `continuity_context_packets.kind` | `ContextPacketKind` | `continuity-token-domain-proposal.md` |
| `continuity_context_packets.sensitivity` | `ContextPacketSensitivity` | `continuity-token-domain-proposal.md` |
| `continuity_context_packets.retention` | `ContextPacketRetention` | `continuity-token-domain-proposal.md` |
| `continuity_reality_states.scope` | `RealityScope` | `continuity-token-domain-proposal.md` |
| `continuity_reality_commits.scope` | `RealityScope` | `continuity-token-domain-proposal.md` |
| `continuity_reality_commits.kind` | `RealityCommitKind` | `continuity-token-domain-proposal.md` |
| `continuity_reality_commits.trigger` | `RealityCommitTrigger` | `continuity-token-domain-proposal.md` |

Actual CHECK constraints or FK-to-lookup-table constraints must not be added until a future migration task aligns them with the canonical token registry (whether in `guardian/protocol_tokens.py` or a continuity-specific registry).

`dyad` and `team` scope values are candidate-only. Do not add constraints that validate them as fully supported scope values until the architecture proves multi-user Reality State synchronization and trust-policy integration.

## Provenance and Export/Restore Requirements

When continuity tables are implemented, the following provenance and export/restore requirements apply per `account-export-restore-contract.md`:

- Every persisted packet, state, and commit must carry explicit provenance (source packet IDs, commit IDs, message IDs, artifact IDs).
- Export must include continuity records as distinct entity families with stable identifiers.
- The export manifest (`manifest.json`) must enumerate `continuity_context_packets`, `continuity_reality_states`, and `continuity_reality_commits` as entity families with counts and integrity hashes.
- Restore must preserve semantic equivalence of continuity records even if local DB IDs are remapped. This includes:
  - Re-linking `continuity_state_packet_links` with remapped IDs.
  - Re-linking `continuity_reality_commits.previous_state_id` / `new_state_id` with remapped IDs.
- If provenance cannot be preserved during restore, the restore must fail closed or report explicit loss per entity.
- Source provenance from imported conversations must survive re-export cycles.
- Continuity storage must not silently drop lineage.

## Retention, Sensitivity, and Consent

### Sensitivity and Retention Enforcement

The `sensitivity` and `retention` fields on `continuity_context_packets` are mandatory. Future runtime must enforce:

- `sensitivity = 'local'`: Never synced across nodes. Export only in full-account export.
- `sensitivity = 'private'`: Scoped to user account. Export only in full-account export.
- `sensitivity = 'syncable'`: May sync across user's trusted nodes. Export included.
- `sensitivity = 'shared'`: May share with collaborators. Requires trust-policy integration. Candidate only.
- `sensitivity = 'restricted'`: Carries sensitive content. Never exported without explicit opt-in. Never synced.

### Candidate-Only Value Warnings

- `dyad` and `team` scope values: Candidate-only. No table constraints should validate these as fully supported scopes until multi-user Reality State synchronization is architected.
- `shared` sensitivity: Candidate-only. Requires trust-policy, collaboration, and consent architecture.
- `restricted` sensitivity: Candidate-only. Requires content classification and access-control architecture.

### Browser Packet Consent

Browser-sourced Context Packets require explicit future consent/scoping review before any `kind = 'browser'` packets are captured and stored. `tab_id`, `tab_binding`, and browser-adjacent scope fields remain nullable and unused until that review passes.

### Identity Boundaries

- Durable trait inference from continuity data is out of scope.
- Persona identity mutation from continuity data is out of scope.
- Project continuity is not persona identity. Reality State is not an identity claim.
- Persona switching must not silently inherit another persona's Reality State.

## Graph-Off Baseline and Optional Graph Mounts

Baseline continuity persistence must work with graph disabled. Graph mounts may enrich relationship traversal, visualization, or offline analysis later per the Optional Graph Mount contract in `continuity-protocol-suite.md` and ADR-030's graph-optionality gate.

- Graph writes must not be required for storage correctness.
- Graph IDs may be stored as optional metadata in `metadata_json` or `provenance_json` only after a future graph boundary ADR/proof.
- Graph-off tests must verify that all Phase A tables are correct and queryable without Neo4j.

## Migration and Rollback Considerations

Before any implementation migration is created, the following must be satisfied:

- **Independently reviewable**: Each migration must be a single, focused change — one table or one constraint set at a time.
- **Rollback policy explicit**: Every `upgrade()` must have a tested `downgrade()`. Soft-delete columns (`deleted_at`) and partial indexes must be included in both paths.
- **Index justification**: Every index must cite the query pattern it supports. The proposed indexes above map to explicit query patterns in the Query Patterns section below.
- **JSONB size considerations**: Payload columns (`payload_json`, `state_json`) may grow large. Consider `jsonb_path_ops` indexes for targeted queries, and size monitoring for retention.
- **Deletion semantics**: Soft-delete via `deleted_at` follows existing Codexify convention. Cascade behavior on hard-delete must be explicit: does deleting a project cascade-delete its continuity packets and states? The answer must be documented before migration.
- **No bundled changes**: No migration may bundle with worker, UI, browser, graph, or provider-routing behavior. Migration tasks are schema-only.

## Query Patterns This Proposal Should Support

The proposed indexes should support the following query patterns. These are candidate queries; actual implementation may optimize further.

| Query Pattern | Supported By |
|---|---|
| Latest Reality State for a project | `ix_cty_states_project_compiled` — `ORDER BY compiled_at DESC LIMIT 1` |
| Latest Reality State for a thread | `ix_cty_states_thread_compiled` — `ORDER BY compiled_at DESC LIMIT 1` |
| Packets that contributed to a state | Join `continuity_state_packet_links` on `state_id` with FK index on `packet_id` |
| Commits for a project over time | `ix_cty_commits_project_created` — `ORDER BY created_at DESC` |
| Open loops for a project | Query `open_loops_json` from latest project Reality State (Phase A); Phase B would index `continuity_open_loops` directly |
| Rejected paths not to reopen | Query `rejected_paths_json` from latest project Reality State; Phase B would index `continuity_rejected_paths` directly |
| Packets by retention policy | `ix_cty_packets_retention` — filter by `retention = 'expires'` |
| Packets by sensitivity | `ix_cty_packets_sensitivity` — filter by `sensitivity` |
| States expiring or decaying soon | `ix_cty_states_expires` — `WHERE expires_or_decays_at < NOW() + INTERVAL` |
| Compiler run proof for a state (Phase B) | Join `continuity_compiler_runs` on `output_state_id` with FK index |

## Relationship to Existing Contracts

### `continuity-protocol-suite.md`

The protocol suite defines the vocabulary (Context Packets, Reality State, Reality Commits, Project Reality, Discovery Commits). This proposal defines how those concepts would be persisted in Postgres. Every proposed table maps to a section in the protocol suite.

### ADR-030: Continuity Protocol Suite Runtime Gate

This proposal satisfies step 4 of ADR-030's approved implementation order ("Postgres schema proposal for persisted packet/state records"). It does not bypass any gate: token-domain review (step 1), pure contracts (step 2), and compiler harness (step 3) precede it.

### `continuity-token-domain-proposal.md`

The token-domain proposal defines candidate values for `kind`, `sensitivity`, `retention`, `scope`, `commit trigger`, `commit kind`, `open loop status`, `rejected path status`. This proposal identifies which columns would be storage-constrained by those token domains and defers actual CHECK constraints to a future alignment task.

### `canonical-token-philosophy.md`

Storage-constrained columns are textbook candidates for canonical tokens: they appear in multiple layers (DB, API, UI), distinguish lifecycle states, would be dangerous to rename casually, and would be reinvented by future agents. This proposal applies that discipline.

### `runtime-protocol-token-contract.md`

When storage constraints are implemented, the token values they enforce must be registered in a canonical token module before the migration lands. This proposal defers that registration to a future task.

### `chat-runtime-contract.md`

Continuity storage is above turn-level chat completion. It does not change provider runtime states, request lifecycle states, or message/attempt identity. Continuity tables join on `thread_id` and `project_id` but do not replace `chat_messages` or `chat_threads`.

### `account-export-restore-contract.md`

Continuity records must be exportable and restorable. This proposal defines the entity families and the provenance fields that export must preserve. The export manifest must enumerate continuity records as distinct families.

### `data-and-storage.md`

This proposal extends the existing Postgres system-of-record role. It follows soft-delete conventions (`deleted_at`), FK-driven relationships, and partial-index patterns already in use. It does not replace Redis, vector, file, or graph storage roles.

### `modules-and-ownership.md`

Future continuity persistence code belongs in the core-loop cluster (near `guardian/continuity/`). Storage adapters should live near the contracts and compiler, not scattered across routes or workers.

### `config-and-ops.md`

No new environment variables are required for Phase A. Future config may govern retention policies, JSONB size limits, and graph-mount modes, but these are deferred.

## Required Follow-Up Before Migration

Before any schema in this proposal is implemented as an Alembic migration, a future task must:

1. Confirm ADR-030 coverage is sufficient for migration scope, or create a migration-specific ADR.
2. Align token registries with constraint values (create `guardian/continuity/tokens.py` or update `guardian/protocol_tokens.py` with continuity token enums).
3. Define SQLAlchemy model classes or persistence adapter classes.
4. Define export/restore inclusion policy: which continuity families are exported by default, which are opt-in, which are excluded.
5. Define deletion/retention policy: what happens to continuity records when a project is archived or deleted.
6. Define migration/rollback proof: tested `upgrade()` and `downgrade()` for every table, index, and constraint.
7. Define graph-off tests: verify that all queries are correct with `GRAPH_MOUNT_MODE = 'disabled'`.
8. Define fixture data for continuity-specific tests.
9. Run migration tests against the supported local Docker Compose path.
10. Keep runtime writes out of the migration task unless separately scoped and approved.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this proposal:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No Alembic migration has been created.
- [ ] No SQLAlchemy model class has been added.
- [ ] No database table exists on disk.
- [ ] No route, worker, or UI has been added.
- [ ] Postgres baseline is preserved; no alternative system of record is proposed.
- [ ] Graph optionality is preserved; Phase A works without Neo4j.
- [ ] Export/restore provenance requirements are considered and explicitly documented.
- [ ] All token constraints are proposed only; no CHECK constraints or FK-to-lookup-table constraints exist.
- [ ] `dyad`, `team`, `shared`, and `restricted` values remain candidate-only.
- [ ] Project Pulse is not proposed as a storage table; it remains a UI/output surface.
- [ ] Required follow-up steps before migration are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
