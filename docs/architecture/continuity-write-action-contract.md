# Continuity Write-on-Explicit-Action Contract

> Classification: docs-only write-action contract  
> Status: proposed  
> Implementation status: no runtime writes, routes, workers, compiler auto-persistence, UI, browser capture, graph writes, sync, export/restore, or Project Pulse exists  
> Normative language: "must", "must not", "should", "proposed", and "future" are intentional.

Purpose: Define the contract for the first future write-on-explicit-action Continuity MVP: Reality Stamp and Reality Commit behavior. This is a docs-only contract. It does not implement runtime writes, wire the adapter to runtime, add routes, add workers, or widen the supported beta release promise.

Last updated: 2026-06-25

## Purpose

The Continuity Phase A schema is live-proofed. The persistence adapter is live-Postgres proven (136 tests, zero skips as of `e2b676a80`). But adapter proof does not authorize runtime writes. ADR-031's runtime write gate states:

> Schema existence does not authorize runtime writes. Compiler output must not be persisted until a separate persistence adapter and explicit write gate are approved.

ADR-030's approved implementation order lists step 5 as:

> Write-on-explicit-action only Reality Stamp / Reality Commit MVP

This contract defines that explicit-action boundary. It exists to prevent:

- Silent continuity writes triggered by ordinary chat turns
- Automatic compiler persistence wiring that bypasses operator intent
- Heartbeat, semantic-delta, or artifact-change triggers being added without review
- Browser ambient capture leaking into continuity storage
- Project Pulse writes disguised as Reality Commits
- Export/restore writes that bypass provenance requirements

Without this contract, the first runtime write task could accidentally authorize automatic, ambient, or unreviewed persistence behavior across the entire continuity surface.

## Non-Goals

This contract does not, and must not be interpreted as:

- implementing any runtime write behavior
- adding a route
- adding a worker
- adding an API response
- implementing Project Pulse UI
- wiring the command bus to continuity storage
- enabling compiler auto-persistence
- enabling heartbeat-triggered writes
- enabling semantic-delta-triggered writes
- implementing browser capture
- enabling graph writes
- implementing sync behavior
- implementing export/restore inclusion
- implementing shared/dyadic reality runtime
- widening the supported beta release promise

## Canonical Terms

| Term | Meaning |
|---|---|
| **Reality Stamp** | A bounded user/operator-triggered capture of current explicit context into a persisted Context Packet. It stamps "this is what I know right now" without compiling a full RealityState or creating a RealityCommit. |
| **Reality Commit** | A durable state-transition record with scope, kind, trigger, previous/new state references, provenance, and explicit title/summary. It records that a meaningful change in project reality was deliberately captured. |
| **Explicit Write Action** | A named, bounded, user/operator-initiated or explicitly-approved operation that results in one or more continuity writes. No ambient or automatic triggers are allowed. |
| **Write Candidate** | A ContextPacket, RealityState, or RealityCommit object provided to the write path for validation and persistence. It must be explicitly constructed from explicit input, not inferred or auto-generated. |
| **Write Intent** | The declared purpose of a write action — "create a reality stamp," "commit a state transition," "compile state from these packets." The intent determines which validations and writes are performed. |
| **Persisted Continuity Record** | A row in one of the four Phase A continuity tables that has been validated, persisted, and confirmed by the adapter. |
| **Write Receipt** | The result object returned by a write action, containing action identity, success/failure, created record IDs, validation errors, persistence errors, provenance refs, and explicit flags for graph usage and event publication. |
| **Runtime Write Gate** | The set of explicit approvals required before any code writes to continuity tables. This contract is one such gate. |
| **Compiler Auto-Persistence** | The prohibited behavior of automatically writing `compile_reality_state()` output to storage. The compiler remains pure; its output may only be persisted through an explicit write action. |
| **Heartbeat Commit** | A prohibited automatic Reality Commit triggered by a periodic scheduler. Deferred until worker infrastructure is separately approved. |
| **Semantic Delta Commit** | A prohibited automatic Reality Commit triggered by the Continuity Compiler detecting a meaningful change. Deferred until compiler runtime differences are separately approved. |

**Distinctions:**

- Reality Stamp ≠ Reality Commit — a stamp captures context; a commit records a state transition.
- Reality Commit ≠ Project Pulse — a commit is durable storage; Pulse is a future UI/read surface.
- Write Action ≠ Chat Turn — a write is explicit and bounded; a chat turn is automatic and broad.
- Write Receipt ≠ Task Event — a receipt confirms persistence; a task event signals queue progress.

## Allowed MVP Write Actions

The following four write actions are the only candidate MVP write operations. All are proposed only.

### create_reality_stamp

| Aspect | Value |
|---|---|
| **Purpose** | Capture current explicit context into a persisted Context Packet |
| **Required input** | Explicit scope IDs (project, thread), user-authored note/summary, explicit artifact refs |
| **Required validation** | `validate_context_packet()` |
| **Records it may write** | One `continuity_context_packets` row |
| **Records it must not write** | Reality states, reality commits, packet links, Phase B tables |
| **Required provenance** | Source message IDs if from thread; source artifact IDs if from artifacts; action identity |
| **Failure behavior** | Return Write Receipt with `success=False`, validation errors, no partial writes |
| **Status** | Proposed only |

### create_reality_commit

| Aspect | Value |
|---|---|
| **Purpose** | Persist a durable Reality Commit recording an explicit state transition |
| **Required input** | Scope, kind (`state_update`, `decision_added`, etc.), trigger (`manual`), explicit title, explicit summary, optional source packet IDs, optional previous/new state IDs |
| **Required validation** | `validate_reality_commit()` |
| **Records it may write** | One `continuity_reality_commits` row |
| **Records it must not write** | Context packets (unless explicitly part of the same action), Phase B tables |
| **Required provenance** | Source packet IDs, previous/new state IDs, action identity |
| **Failure behavior** | Return Write Receipt with `success=False`, validation errors, no partial writes |
| **Status** | Proposed only |

### compile_and_save_reality_state_from_explicit_packets

| Aspect | Value |
|---|---|
| **Purpose** | Compile a RealityState from an explicitly provided set of Context Packets and persist it |
| **Required input** | Explicit list of source packet IDs (already persisted), scope |
| **Required validation** | `validate_reality_state()` on compiler output |
| **Records it may write** | One `continuity_reality_states` row + `continuity_state_packet_links` rows (atomic) |
| **Records it must not write** | Context packets (these already exist), commits (unless explicitly requested), Phase B tables |
| **Required provenance** | Source packet IDs, compiler version, action identity |
| **Failure behavior** | Return Write Receipt with `success=False`, roll back state + links atomically |
| **Status** | Proposed only |

### link_state_to_packets

| Aspect | Value |
|---|---|
| **Purpose** | Create explicit provenance links between a Reality State and its contributing packets |
| **Required input** | State ID, explicit list of packet IDs, relationship string |
| **Required validation** | `state_id` and `packet_ids` must be non-empty; adapter-level uniqueness check |
| **Records it may write** | One `continuity_state_packet_links` row per packet (atomic batch) |
| **Records it must not write** | States, packets, commits, Phase B tables |
| **Required provenance** | The links themselves are provenance |
| **Failure behavior** | Duplicate links cause batch rollback; return Write Receipt with failure |
| **Status** | Proposed only |

## Explicit Action Requirement

No continuity write may happen as a side effect of ordinary system behavior. The following triggers are explicitly forbidden for the MVP:

- A chat turn completing
- The compiler producing a RealityState
- Retrieval finding relevant context
- A browser tab being open
- A heartbeat firing on schedule
- A semantic delta being detected by analysis
- A Git commit occurring in a linked repository
- A thread being paused or resumed
- A document being uploaded or generated
- An artifact being created or modified
- A provider lane changing state
- A persona being switched

The MVP write path must require one of:

1. An explicit user/operator action with clearly declared intent
2. An explicitly named internal command approved by a future implementation task

Ambient writes, background writes, and automatic compilation-writes are not allowed.

## Proposed Write Flow

The following is a proposed future write flow. It is not implemented.

1. **Receive explicit write action**: The action carries an action kind, explicit input, and an explicit caller identity.
2. **Construct Write Candidate from explicit input only**: No hidden model inference, no ambient transcript summarization, no browser DOM, no background retrieval, no graph expansion, no inferred persona traits.
3. **Validate the candidate**: Use existing `validate_*` helpers from `guardian.continuity.contracts`.
4. **Optionally compile**: If the action is `compile_and_save_reality_state_from_explicit_packets`, call `compile_reality_state()` with the explicit packet set. The compiler remains pure — this is an explicit invocation, not automatic.
5. **Validate the compiled state**: If a state was compiled, validate it.
6. **Construct commit if requested**: If the action includes a state transition, construct the `RealityCommit` candidate.
7. **Persist via adapter**: Use `ContinuityPersistenceAdapter` in a bounded DB transaction. All records for one action must be in one transaction.
8. **Return explicit Write Receipt**: The receipt carries action identity, success/failure, created IDs, errors, warnings, provenance refs, and explicit flags.
9. **Publish no runtime event**: Event publication is not approved by this contract. If future event semantics are desired, a separate token/event contract task must approve them.

## Input Boundaries

### Allowed Input Sources for MVP

- Selected thread ID (explicit, user-chosen)
- Selected project ID (explicit, user-chosen)
- Explicit user/operator note or summary text
- Explicit artifact IDs (user-chosen)
- Explicit source packet IDs (already persisted, user-chosen or action-derived)
- Explicit current branch/task identity if already available in the calling context
- Explicit summary text supplied by the action caller

### Disallowed Input Sources for MVP

- Hidden model inference output
- Automatic transcript summarization
- Browser DOM capture
- Background retrieval sweep results
- Graph expansion output
- Inferred persona traits
- Unreviewed semantic delta analysis
- Ambient memory recall
- Provider state changes
- Export/restore artifacts

## Validation Requirements

Future implementation must satisfy the following validation requirements for every write action:

| Requirement | Applies To |
|---|---|
| Call `validate_context_packet()` before writing any packet | create_reality_stamp |
| Call `validate_reality_state()` before writing any state | compile_and_save_reality_state_from_explicit_packets |
| Call `validate_reality_commit()` before writing any commit | create_reality_commit |
| Reject invalid candidates before persistence (no partial writes) | All actions |
| Preserve validation errors in the Write Receipt | All actions |
| Never describe a partial state/link/commit write as success | All multi-record actions |
| Never infer missing facts from summaries, prose, or ambient context | All actions |

## Transaction and Atomicity Rules

| Write Scenario | Atomicity Rule |
|---|---|
| Single Context Packet write | Single-record transaction sufficient |
| Reality State + state-packet links | Must be one transaction. If any link insert fails, the state INSERT must roll back. |
| Reality Commit with previous/new state references | If the referenced states are created in the same action, the commit must be in the same transaction. |
| Link batch | All links in the batch must be in one transaction. Duplicate link must roll back the entire batch. |

Additional rules:

- Failure must return explicit error information in the Write Receipt.
- No partial write may be reported as success.
- The receipt's `success` field must be `False` if any record in the transaction failed.

## Write Receipt Contract

The Write Receipt is the canonical result object for any write action. The following fields are proposed only.

```python
@dataclass(frozen=True)
class ContinuityWriteReceipt:
    action_id: str               # Unique action identifier
    action_kind: str             # "create_reality_stamp", "create_reality_commit", etc.
    success: bool                # True if all records were persisted
    created_packet_ids: tuple[str, ...] = ()
    created_state_ids: tuple[str, ...] = ()
    created_commit_ids: tuple[str, ...] = ()
    created_link_ids: tuple[str, ...] = ()
    validation_errors: tuple[ContinuityPersistenceError, ...] = ()
    persistence_errors: tuple[ContinuityPersistenceError, ...] = ()
    warnings: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    graph_used: bool = False             # Always False for MVP
    runtime_event_published: bool = False # Always False for MVP
    created_at: str = ""                  # ISO-8601
```

## Runtime Event Policy

No runtime events are approved by this contract:

- No `task.created`, `task.completed`, or continuity-specific task events may be emitted by write actions.
- Write Receipts are not task events and must not be published on event streams.
- Future event publication requires a separate token/event contract review.
- Event publication must not be treated as proof of durable write unless backed by persistence confirmation from the adapter.

## Read-after-Write Policy

Future implementation may read back written records to confirm persistence:

- Use adapter read methods (`load_reality_state()`, etc.) for confirmation.
- Readback confirmation is not Project Pulse — it is write verification only.
- Readback must not expose soft-deleted records by default.
- Readback must not query Neo4j or graph mounts.
- Readback confirmation is internal to the write action; it does not produce user-visible output.

## Provenance Requirements

Every persisted record must carry provenance:

- **Source packet IDs**: Which packets contributed to this record.
- **Source commit IDs**: Which prior commits are referenced (for chained commits).
- **Source message IDs**: Which chat messages provided context.
- **Source artifact IDs**: Which artifacts are linked.
- **Action provenance**: Which action created this record, with action kind and action ID.
- **Schema version**: The schema version at write time.
- **Sensitivity and retention**: Preserved from the write candidate.

Additionally:

- User-authored notes must be distinguishable from model-generated summaries in provenance metadata.
- Provenance must survive serialization/deserialization through the adapter's JSONB columns.

## Retention, Sensitivity, and Consent

- MVP writes must not introduce `shared`, `dyad`, `team`, or `restricted` behavior.
- `sensitivity = 'local'` or `sensitivity = 'private'` are the only safe defaults for MVP.
- Browser-captured packets remain deferred until a separate consent/scope contract is approved.
- Durable trait inference from continuity data is out of scope.
- Persona identity mutation from continuity data is out of scope.
- Project continuity is not persona identity.

## Graph-Off Baseline

MVP write behavior must work with graph disabled:

- Graph writes are not allowed.
- Graph receipts are not allowed.
- Optional graph enrichment remains a future task gated by its own contract.
- Graph IDs must not be required for write success.
- The Write Receipt's `graph_used` field must be `False`.

## Export/Restore Boundary

Export/restore continuity inclusion remains deferred:

- Write implementation must preserve enough provenance for future manifest-based export.
- Local DB IDs must not be treated as portable export identity.
- No restore behavior is implemented by the MVP write contract.
- When export/restore continuity inclusion is implemented, it must handle remapping of local IDs, relinking of state-packet relationships, and preserving commit chains.

## Operator Truth Surface

A future operator or developer proof surface for the write MVP must expose:

| Signal | What It Shows |
|---|---|
| Write action attempted | Action kind, action ID, timestamp |
| Write action accepted or rejected | `success` flag in Write Receipt |
| Validation result | `validation_errors` in receipt |
| Persistence result | `persistence_errors` and created IDs in receipt |
| Graph usage | Always `false` for MVP |
| Runtime event publication | Always `false` for MVP |
| Compiler auto-persistence | Must not occur; operator surface can confirm compiler was never auto-invoked |

This surface is diagnostic/operator only, not user-facing Project Pulse.

## Forbidden Write Paths

The following write paths are explicitly forbidden for the MVP and must not be implemented by the MVP write task:

- **Chat-turn automatic writes**: No write triggered by `POST /api/chat/{thread_id}/complete`
- **Compiler automatic writes**: No write triggered by `compile_reality_state()` returning a result
- **Heartbeat writes**: No write triggered by a periodic scheduler
- **Semantic-delta writes**: No write triggered by change detection
- **Browser ambient capture**: No write triggered by browser tab activity
- **Retrieval-triggered writes**: No write triggered by context broker assembly
- **Graph-triggered writes**: No write triggered by graph enrichment
- **Provider-triggered writes**: No write triggered by provider lane state changes
- **Project Pulse writes**: No write triggered by Pulse UI rendering or pre-computation
- **Sync-triggered writes**: No write triggered by federation or peer sync
- **Export/restore-triggered writes**: No write triggered by export or import operations
- **Worker background writes**: No write from a background worker unless separately approved by a future task

## Required Tests for Future Implementation

When the write-action MVP is implemented, the following tests must pass:

| Test Category | Required Tests |
|---|---|
| Explicit packet write | `create_reality_stamp` writes one packet; invalid packet rejected before write |
| Explicit state compile + write | `compile_and_save_reality_state_from_explicit_packets` creates state + links atomically; invalid state rejected |
| Explicit commit write | `create_reality_commit` writes one commit; invalid commit rejected; prev/new state IDs preserved |
| Link atomicity | Duplicate link in batch causes full rollback; no partial links |
| No auto-persistence | Chat turn does not write to continuity tables; compiler output not auto-persisted |
| No runtime imports | Write module does not import routes, workers, providers, graph, browser, or Redis |
| Graph-off | All write actions succeed with Neo4j absent |
| Receipt correctness | Write Receipt includes action_id, success flag, created IDs, errors |
| Read-after-write | Written records are readable via adapter read methods |
| Transaction rollback | DB error during multi-record write rolls back all records in the transaction |

## Relationship to Existing Contracts

### ADR-030: Continuity Protocol Suite Runtime Gate

ADR-030's step 5 is "write-on-explicit-action only Reality Stamp / Reality Commit MVP." This contract defines that explicit-action boundary.

### ADR-031: Continuity Phase A Storage Migration Gate

ADR-031's runtime write gate states that schema does not authorize writes. This contract is the explicit write gate required before any write code lands.

### continuity-protocol-suite.md

The protocol suite defines Reality State, Reality Commit, Context Packet, and Project Reality concepts. This contract defines how write actions create those records.

### continuity-token-domain-proposal.md

Candidate token values (`kind`, `trigger`, `scope`) inform which fields the write action sets. Only stable, well-understood values may be used in MVP.

### continuity-storage-schema-proposal.md

The storage proposal defines the four Phase A tables. This contract defines which write actions target which tables.

### continuity-persistence-adapter-contract.md

The persistence adapter contract defines the adapter interface. This contract defines the write actions that call the adapter.

### 2026-06-25-continuity-persistence-adapter-live-db-proof.md

The adapter is live-Postgres proven. This contract defines the write actions that use the proven adapter.

### chat-runtime-contract.md

Write actions are not chat turns. They have their own action identity (`action_id`), not `turn_id` or `request_id`. They do not change provider runtime states, request lifecycle states, or message/attempt identity.

### runtime-protocol-token-contract.md

No runtime events are approved. If future event publication is desired, a separate token/event contract review is required.

### account-export-restore-contract.md

Export/restore continuation inclusion is deferred. Write actions must preserve enough provenance for future manifest-based export.

### data-and-storage.md

Write actions write only to Postgres. They do not use Redis, vector, file, or graph storage.

### guardian/continuity/contracts.py

Write actions must validate candidates using the existing `validate_*` helpers.

### guardian/continuity/compiler.py

Write actions may explicitly invoke `compile_reality_state()` with explicit packet inputs. The compiler must not be auto-invoked.

### guardian/continuity/persistence.py

Write actions must use `ContinuityPersistenceAdapter` for all persistence. They must not bypass the adapter with direct SQLAlchemy operations.

## Required Follow-Up Before Implementation

Before write-action implementation code is written, a future task must:

1. Choose exact module path (e.g., `guardian/continuity/actions.py` or `guardian/continuity/write_actions.py`).
2. Define the `ContinuityWriteReceipt` dataclass concretely.
3. Define action input dataclasses (`RealityStampInput`, `RealityCommitInput`, `CompileAndSaveInput`, `LinkPacketsInput`).
4. Define DB session boundary — explicit session passed by caller or dependency injection.
5. Define the authorized caller surface: is this internal-only (operator scripts, future CLI), or user-callable via a future API? The MVP may start internal-only.
6. Define tests for no-automatic-writes (chat turn, compiler, heartbeat, browser, retrieval must not trigger writes).
7. Define tests for graph-off behavior.
8. Define whether any diagnostic/operator surface is allowed to inspect write receipts.
9. Keep route, worker, UI, browser, graph, export, and sync modules out of scope.
10. Do not bundle write-action implementation with any other surface.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No runtime write path has been added.
- [ ] No adapter call sites exist in runtime code.
- [ ] No compiler persistence wiring has been added.
- [ ] No routes, workers, UI, or browser behavior has been added.
- [ ] No graph-write enablement has occurred.
- [ ] No export/restore inclusion has been implemented.
- [ ] Explicit action requirement is stated (no ambient, automatic, or background writes).
- [ ] Forbidden write paths are explicitly listed (12 paths).
- [ ] Validation requirements are explicit for all four write actions.
- [ ] Transaction and atomicity rules are explicit.
- [ ] Write Receipt shape is proposed.
- [ ] Provenance obligations are explicit.
- [ ] Graph-off baseline is explicit.
- [ ] Required follow-up steps before implementation are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
