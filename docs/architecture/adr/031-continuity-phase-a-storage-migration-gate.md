---
tags:
* architecture
* adr
* continuity
* migration-gate
* storage
  aliases:
* ADR-031
* Continuity Phase A Storage Migration Gate
---

# ADR-031: Continuity Phase A Storage Migration Gate

## Status

Accepted

## Date

2026-06-25

## Context

ADR-030 defined the Continuity Protocol Suite runtime gate and approved an 11-step implementation order. Steps 1–4 are now complete:

1. Token-domain proposal (`continuity-token-domain-proposal.md`) — complete
2. Pure backend contract types (`guardian/continuity/contracts.py`) — complete
3. Deterministic compiler harness (`guardian/continuity/compiler.py`) — complete
4. Postgres storage schema proposal (`continuity-storage-schema-proposal.md`) — complete

The storage schema proposal defines candidate table boundaries for `continuity_context_packets`, `continuity_reality_states`, `continuity_reality_commits`, and `continuity_state_packet_links`, plus optional Phase B tables. It does not authorize migrations, SQLAlchemy models, persistence adapters, runtime writes, compiler wiring, or any storage side effects.

Implementing Phase A storage would materially affect:

- **Durable state**: Four new Postgres tables with ~25 columns each, each carrying provenance, sensitivity, retention, and token-constrained fields.
- **Token alignment**: Seven columns would be storage-constrained by candidate token domains that are not yet promoted to runtime registries.
- **Provenance obligations**: Every persisted record must carry traceable source chains for future export/restore compatibility.
- **Retention/sensitivity**: Sensitivity (`local`, `private`, `syncable`, `shared`, `restricted`) and retention (`ephemeral`, `session`, `project`, `account`, `exportable`, `expires`) must be enforced at the storage boundary.
- **Export/restore**: Future export must include continuity records as distinct entity families with stable identifiers.
- **Migration risk**: Alembic migrations without explicit rollback strategy, index justification, or graph-off baseline could degrade the supported local Compose path.

A migration gate is required to ensure that Phase A storage implementation is independently reviewable, proof-backed, and does not silently widen the supported beta surface.

## Decision

This ADR creates the explicit Phase A storage migration gate. ADR-030's broader runtime gate remains in effect for all other continuity surfaces (compiler wiring, workers, UI, browser, graph, sync). This ADR governs only the Phase A schema migration boundary.

Phase A storage is migration-eligible only after this ADR's required migration proof is satisfied. Phase A includes only four tables:

- `continuity_context_packets`
- `continuity_reality_states`
- `continuity_reality_commits`
- `continuity_state_packet_links`

Phase B normalization tables remain explicitly deferred:

- `continuity_open_loops`
- `continuity_rejected_paths`
- `continuity_decisions`
- `continuity_compiler_runs`
- `continuity_project_pulse_snapshots`

Schema existence does not authorize runtime writes. Compiler output must not be persisted until a separate persistence adapter and explicit write gate are approved.

## Approved Phase A Migration Boundary

A future migration task may include the following, and only the following:

### Permitted

- Alembic migration for the four Phase A tables (`upgrade` and `downgrade`) following existing Codexify migration conventions.
- SQLAlchemy model definitions consistent with the repo's existing model pattern (`guardian/db/models.py` or a continuity-specific module).
- CHECK constraints or FK-to-lookup-table constraints for token-constrained columns, only after the candidate token values are aligned with a canonical registry.
- Indexes justified by query patterns documented in the storage schema proposal:
  - `ix_cty_packets_project_created`, `ix_cty_packets_thread_created`, etc.
  - `ix_cty_states_scope_compiled`, `ix_cty_states_project_compiled`, etc.
  - `ix_cty_commits_project_created`, `ix_cty_commits_scope_created`, etc.
  - Partial indexes for active (non-deleted) rows.
- Soft-delete `deleted_at` columns with partial indexes following existing Codexify convention.
- JSONB columns for provenance, payload, state, and extracted sub-records.
- Graph-off baseline: migrations must succeed and tables must be queryable with `GraphMountMode = 'disabled'` (Neo4j absent or down).
- Migration tests proving upgrade/downgrade correctness against the supported local Docker Compose path.

### Not Permitted

- Runtime write paths (INSERT, UPDATE, DELETE from API routes, workers, or compiler).
- Compiler persistence wiring (calling `compile_reality_state` and writing the result to storage).
- Worker emission (queue-backed heartbeat, semantic-delta, or artifact-change triggers).
- API routes (GET/POST endpoints for continuity records).
- UI surfaces (Project Pulse, continuity inspector, admin panels).
- Browser capture (packet emission from browser context).
- Graph writes (Neo4j enrichment or graph-backed continuity truth).
- Sync protocol (federated Reality State synchronization).
- Export/restore implementation (continuity record inclusion in export artifacts).
- Project Pulse read model or pre-computed briefs.

## Required Migration Proof

Before a Phase A migration is accepted, the following proof must be provided by the implementation task:

### Structural Proof

| Requirement | Proof |
|---|---|
| Clean-start migration succeeds | `alembic upgrade head` on a freshly created DB produces all four tables, indexes, and constraints without errors |
| Existing-instance upgrade succeeds | `alembic upgrade head` on the current migration floor (latest existing migration before continuity tables) succeeds without errors |
| Downgrade removes continuity tables | `alembic downgrade -1` (or specified target) drops continuity tables and indexes without errors |
| Table existence verified | `SELECT COUNT(*)` or schema introspection confirms table presence, column types, and nullable constraints |
| Indexes and constraints exist | Schema introspection confirms named indexes and CHECK/FK constraints match the proposal |
| Minimal valid rows insertable | Migration or model tests can INSERT a valid `continuity_context_packets` row with all required envelope fields; this is test-only and does not create a runtime write path |

### Behavioral Proof

| Requirement | Proof |
|---|---|
| Graph-off baseline | Migration succeeds and tables are queryable with Neo4j absent, `GUARDIAN_ENABLE_GRAPH_CONTEXT=false`, or equivalent |
| No runtime writes occur | `git diff` of the migration task shows no INSERT/UPDATE/DELETE in routes, workers, core services, or compiler modules |
| No route/worker/provider changes | `git diff` shows no changes to `guardian/routes/`, `guardian/workers/`, `guardian/core/ai_router.py`, `guardian/context/broker.py`, or `guardian/queue/` |
| No release promise widened | `00-current-state.md` unchanged; no new supported path claims |

## Token Constraint Policy

Token-constrained columns must align with `continuity-token-domain-proposal.md`. The following policy governs constraint implementation:

- If candidate token values have been promoted to a canonical runtime registry (e.g., `guardian/continuity/tokens.py` or `guardian/protocol_tokens.py`) before the migration task, CHECK constraints must reference the registered values.
- If candidate token values are not yet promoted, constraints must be conservative:
  - Use `VARCHAR` without CHECK (accept any string, defer validation to application logic).
  - Or use a CHECK constraint with a limited, safe subset of candidate values that are well-understood (e.g., `kind IN ('thread', 'project_reality', 'browser', 'git', 'artifact', 'persona', 'provider', 'retrieval', 'discovery', 'open_loop', 'rejected_path')` for the kinds that are uncontroversially stable).
  - `dyad`, `team`, `shared`, and `restricted` values must not appear in CHECK constraints until multi-user Reality State synchronization and trust-policy integration are architected.
- Storage constraints must not create drift from future registry-backed tokens. If a CHECK constraint uses different values than the registry, the migration must be rejected.
- Repeated storage-visible values must not be invented ad hoc in migration code. All constraint values must originate from the token-domain proposal.

## Provenance and Export/Restore Policy

Phase A tables must preserve provenance JSON fields even though export/restore inclusion is deferred:

- `continuity_context_packets.provenance_json`
- `continuity_reality_states.provenance_json`
- `continuity_reality_commits.provenance_json`

When continuity export is implemented in a future task:

- The export manifest must enumerate continuity records as distinct entity families.
- Restore must preserve semantic equivalence of continuity records even if local DB IDs are remapped.
- Restore must not silently drop continuity lineage.
- `continuity_state_packet_links` must be re-linked with remapped state and packet IDs during restore.
- `continuity_reality_commits.previous_state_id` / `new_state_id` must be re-linked with remapped state IDs during restore.
- Local database IDs (`SERIAL` or `UUID`) must not be treated as portable identity across instances unless the export manifest semantics explicitly support that mapping.

## Retention, Sensitivity, and Consent Policy

- `sensitivity` and `retention` columns must be present in `continuity_context_packets`.
- `shared`, `team`, `dyad`, and `restricted` semantics remain candidate-only and do not imply shared runtime support. These values may be stored but must not be enforced as fully supported scopes or sensitivity levels.
- Browser packet capture (`kind = 'browser'`, `tab_id`, `tab_binding`) remains deferred and requires explicit consent/scope review before any `kind = 'browser'` packets are written to storage.
- Durable trait inference from continuity data is out of scope.
- Persona identity mutation from continuity data is out of scope.
- Project continuity is not persona identity. Reality State is not an identity claim.

## Graph-Off Baseline

Phase A migration must work with Neo4j disabled. Graph writes are not required for storage correctness.

- Graph IDs must not appear as mandatory columns.
- Graph IDs, if added later as optional metadata in JSONB columns, must only be added after a future graph boundary ADR/proof.
- Graph-off tests must verify that all four Phase A tables are correct and queryable with no graph system running.
- Optional graph mounts may enrich future relationship traversal but do not own canonical continuity truth. This is consistent with ADR-019, ADR-025, ADR-026, and the Optional Graph Mount contract in `continuity-protocol-suite.md`.

## Runtime Write Gate

Schema existence does not authorize runtime writes. The following gates remain closed:

- **Compiler persistence**: `compile_reality_state` output must not be written to storage until a persistence adapter and explicit write gate are approved in a separate task. The compiler remains pure and stateless.
- **Reality Stamp / Reality Commit MVP**: Write-on-explicit-action behavior (manual Reality Commit creation) requires its own contract and proof before any `INSERT` into `continuity_reality_commits` or `continuity_reality_states` is permitted.
- **Heartbeat, semantic-delta, artifact-change triggers**: These require worker infrastructure and must not be enabled by the migration task.
- **Project Pulse**: Pulse is a UI/read surface. It must not be implemented as a side effect of migration. It remains a future task after the read model is available.
- **API routes**: No GET/POST/DELETE endpoints for continuity records may be added by the migration task.

## Rejected Alternatives

### Store all continuity data only in JSON files

Rejected. JSON files would bypass Postgres indexing, transactional guarantees, and the existing export/restore infrastructure. The storage proposal and this ADR preserve Postgres as the canonical system of record while allowing future Git-backed export as optional follow-through.

### Make Neo4j the canonical continuity store

Rejected. Neo4j is optional and feature-flagged. The graph-off baseline must work. Continuity truth must be durable and queryable without graph dependencies. Optional graph mounts may enrich but do not own continuity truth.

### Implement schema and runtime writes in one task

Rejected. Combining schema creation with runtime write paths would bundle high-blast-radius changes (persistence, provider calls, worker behavior, API responses) into one unreviewable task. Schema and writes are independently gated.

### Skip token-domain alignment

Rejected. Ad hoc string literals in CHECK constraints would create drift from the token-domain proposal and make future registry alignment a breaking migration. Token-constrained columns must reference canonical values.

### Persist compiler runs before states/packets

Rejected. Compiler runs are Phase B diagnostic records. They depend on states and packets existing. Inverting the dependency would require NULL FK references or premature normalization.

### Implement Project Pulse before storage proof

Rejected. Project Pulse is a UI/read surface that depends on persisted Reality State. Migrating storage is a prerequisite, but the migration task must not implement Pulse. Pulse requires its own spec and UI implementation task.

## Consequences

### Positive

- **Keeps migrations reviewable**: Each Phase A table is independently defined, indexed, and constrained. The migration task is bounded to schema only.
- **Preserves Postgres baseline**: No alternative system of record is proposed or authorized.
- **Protects graph optionality**: Graph-off baseline is an explicit proof requirement. Neo4j is not required.
- **Preserves provenance/export obligations**: Provenance JSON fields are mandatory even though export inclusion is deferred.
- **Prevents runtime drift**: Schema existence does not authorize writes. The runtime write gate is explicit.

### Tradeoffs

- **Adds another gate before visible features**: Phase A schema alone produces no user-visible behavior. Project Pulse, project reality queries, and Reality Commit creation are all behind future tasks.
- **Requires future migration tests**: Every migration must be independently tested with upgrade/downgrade proof on the supported Compose path.
- **May defer useful Project Pulse behavior**: Pulse cannot render until Reality State is readable, which requires the read model and API routes beyond this ADR.
- **Keeps Phase B normalization out of the first storage slice**: Open loops, rejected paths, and decisions remain in JSONB sub-records rather than normalized rows. This is intentional for Phase A simplicity.

## Relationship to Existing Contracts

### `continuity-protocol-suite.md`

The protocol suite defines the vocabulary. This ADR gates the Phase A storage of packets, states, commits, and their links. Phase B tables and optional graph mounts remain deferred.

### ADR-030: Continuity Protocol Suite Runtime Gate

This ADR is a sub-gate of ADR-030's broader implementation order. ADR-030 gates all runtime continuity work. This ADR specifically gates the Phase A migration boundary. ADR-030 remains in effect for compiler wiring, workers, UI, browser, graph, and sync.

### `continuity-token-domain-proposal.md`

This ADR's token constraint policy requires alignment with the token-domain proposal before CHECK constraints are added. Candidate-only values (`dyad`, `team`, `shared`, `restricted`) must not appear in constraints until multi-user architecture is proven.

### `continuity-storage-schema-proposal.md`

The storage proposal defines the table shapes, columns, indexes, and query patterns. This ADR accepts that proposal as the Phase A boundary and defines the proof required before migration. The storage proposal's Phase B tables and deferred compiler runs table are explicitly excluded from Phase A scope by this ADR.

### `canonical-token-philosophy.md`

Storage-constrained columns are textbook canonical token candidates. This ADR requires that constraint values originate from the token-domain proposal, not from ad hoc literals.

### `runtime-protocol-token-contract.md`

When token constraints are implemented, values must be registered in a canonical token module. This ADR defers that registration to a future task.

### `account-export-restore-contract.md`

Provenance fields are mandatory even though export inclusion is deferred. When continuity export is implemented, continuity records must be exportable and restorable with provenance preservation.

### `data-and-storage.md`

This ADR extends the existing Postgres system-of-record role. It follows soft-delete conventions, partial-index patterns, and FK-driven relationships. It does not replace Redis, vector, file, or graph storage.

### `modules-and-ownership.md`

Future continuity persistence code belongs in the core-loop cluster near `guardian/continuity/`. Migration files belong in the existing `guardian/db/migrations/` directory.

### `config-and-ops.md`

No new environment variables are required for Phase A migration. Future config for retention policies, JSONB size limits, or graph-mount modes is deferred.

## Follow-Up Tasks

The following tasks are explicitly not implemented by this ADR and must proceed as separate work items:

| Task | Description | Dependencies |
|---|---|---|
| Phase A Alembic migration | Create `upgrade()` and `downgrade()` for the four Phase A tables with indexes, constraints, and soft-delete columns | This ADR; token registry alignment |
| SQLAlchemy models or persistence adapter | Define model classes or adapter classes for continuity tables | Phase A Alembic migration |
| Migration tests | Prove upgrade/downgrade on supported Compose path; graph-off baseline | Phase A Alembic migration |
| Export/restore continuity inclusion policy | Define which continuity families are exported, which are opt-in, which are excluded | Phase A migration proof |
| Write-on-explicit-action Reality Stamp / Reality Commit MVP | Implement manual Reality Commit creation with persistence | Phase A migration proof; compiler harness |
| Compiler persistence adapter | Wire `compile_reality_state` output to `continuity_reality_states` via an explicit adapter seam | Reality Stamp MVP |
| Project Reality read model | Query-able compiled Project Reality from persisted states and commits | Compiler persistence adapter |
| Project Pulse UI spec | Define the UI/output surface contract for Project Pulse | Project Reality read model |
| Browser Context Provider spec | Define the browser-to-Codexify packet emission contract | Token-domain proposal |
| Optional graph mount contract | Define Neo4j relationship traversal for continuity behind existing graph-write flags | Phase A migration proof |
| Sync protocol | Define federated Reality State synchronization | All of the above |
| Shared/dyadic reality contract | Define multi-user Reality State sharing | Sync protocol |

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this ADR:

- [ ] This ADR is docs-only and introduces no runtime behavior.
- [ ] No Alembic migration has been created.
- [ ] No SQLAlchemy model has been added.
- [ ] No runtime write path has been added.
- [ ] No route, worker, UI, or browser behavior has been added.
- [ ] No graph-write enablement has occurred.
- [ ] Phase A boundary is explicit (four tables; five Phase B tables deferred).
- [ ] Token constraint policy is explicit (align with token-domain proposal; candidate-only values excluded from constraints).
- [ ] Provenance/export obligations are explicit (provenance JSON mandatory; export inclusion deferred).
- [ ] Graph-off baseline is an explicit proof requirement.
- [ ] Runtime write gate is explicit (schema does not authorize writes; compiler persistence, Reality Stamp, heartbeat triggers, Pulse, and API routes are all separately gated).
- [ ] Rejected alternatives are documented and reasoned.
- [ ] Follow-up tasks are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
