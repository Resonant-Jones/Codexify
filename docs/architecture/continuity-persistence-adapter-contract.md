# Continuity Persistence Adapter Contract

> Classification: docs-only adapter contract
> Status: proposed
> Implementation status: no adapter code, runtime writes, routes, workers, compiler persistence, graph writes, browser capture, sync, export/restore, or UI exists
> Normative language: "must", "must not", "should", "proposed", and "future" are intentional.

Purpose: Define the contract for a future Continuity Phase A persistence adapter after the schema migration has been live-proofed. This is a docs-only contract. It does not implement the adapter, create runtime writes, wire the compiler to storage, add routes, add workers, or widen the supported beta release promise.

Last updated: 2026-06-25

## Purpose

The Phase A continuity storage schema has been live-proofed on the supported local Docker Compose path (`2026-06-25-continuity-phase-a-storage-migration-proof-rerun.md` — PASS). Four tables (`continuity_context_packets`, `continuity_reality_states`, `continuity_reality_commits`, `continuity_state_packet_links`) exist in Postgres with verified indexes, constraints, and insert/readback behavior.

Schema existence does not authorize runtime writes. ADR-031's runtime write gate explicitly states:

> Schema existence does not authorize runtime writes. Compiler output must not be persisted until a separate persistence adapter and explicit write gate are approved.

This contract defines the adapter boundary before any code writes to continuity tables. It specifies:

- Which contract types the adapter must accept
- Which validation must be performed before writes
- What transaction boundaries apply
- What provenance must be preserved
- What the write authorization gate requires
- What read behavior is allowed
- What error shapes the adapter must produce

Without this contract, a future implementation task could bypass validation, write unstructured ad hoc dictionaries, silently drop provenance, break atomicity on state-packet links, or wire compiler output directly to storage without gating.

This contract is governed by ADR-030 (runtime gate), ADR-031 (migration gate), the Phase A migration proof rerun, and the existing pure backend contracts in `guardian/continuity/contracts.py` and `guardian/continuity/compiler.py`.

## Non-Goals

This contract does not, and must not be interpreted as:

- implementing the adapter
- creating runtime write paths
- wiring compile_reality_state() to storage
- adding a route
- adding a worker
- adding an API response
- implementing Project Pulse UI
- implementing browser capture
- enabling graph writes
- implementing sync behavior
- implementing export/restore inclusion
- normalizing Phase B tables
- enabling shared/dyadic reality runtime
- widening the supported beta release promise

## Storage Surfaces Governed

The future adapter governs writes to four Phase A tables. Each table has specific write rules:

### continuity_context_packets

- **What the adapter may write:** Structured `ContextPacket` envelope rows with indexed kind, sensitivity, retention, scope IDs, source metadata, payload JSONB, provenance JSONB, and soft-delete timestamp.
- **What it must validate first:** `validate_context_packet()` from `guardian.continuity.contracts`. Invalid packets must be rejected without partial writes.
- **What provenance must be retained:** `provenance_json` must carry source packet IDs, commit IDs, message IDs, and artifact IDs when present.
- **What it must not infer:** The adapter must not infer packet content from summary text, create packets automatically from thread activity, or capture browser context without an approved browser consent/scope contract.

### continuity_reality_states

- **What the adapter may write:** Compiled `RealityState` snapshots with scope, compiled_at, source_packet_ids, full `state_json`, extracted JSON sub-records, confidence, provenance, and decay timestamp.
- **What it must validate first:** `validate_reality_state()` from `guardian.continuity.contracts`. States with no source packet IDs must be rejected. Confidence outside 0.0–1.0 must be rejected (NULL is valid).
- **What provenance must be retained:** `provenance_json` must carry source packet IDs. `source_packet_ids_json` must remain consistent with `state_json`.
- **What it must not infer:** The adapter must not compile Reality State from raw thread messages without the Continuity Compiler. It must not auto-generate state snapshots on schedule or heartbeat unless separately approved.

### continuity_reality_commits

- **What the adapter may write:** Durable `RealityCommit` records with scope, kind, trigger, title, summary, previous/new state references, source packet IDs, and provenance.
- **What it must validate first:** `validate_reality_commit()` from `guardian.continuity.contracts`. Commits with no source packet IDs or provenance references must be rejected. Empty titles must be rejected.
- **What provenance must be retained:** `provenance_json` must carry source packet IDs, commit IDs, message IDs, and artifact IDs. `previous_state_id` and `new_state_id` must be valid state references when present.
- **What it must not infer:** The adapter must not auto-create commits on heartbeat, semantic delta, artifact change, git commit, thread pause, or thread resume unless those triggers are separately approved. Write-on-explicit-action only until further gating.

### continuity_state_packet_links

- **What the adapter may write:** Many-to-many provenance links between states and their contributing packets.
- **What it must validate first:** Both `state_id` and `packet_id` must reference existing rows. The `relationship` value must be a non-empty string.
- **What provenance must be retained:** The link itself is provenance — it documents which packets contributed to which state.
- **What it must not infer:** The adapter must not create links for relationships it hasn't been explicitly asked to record. Duplicate `(state_id, packet_id, relationship)` triples must be rejected (uniqueness constraint enforced at DB level).

## Contract Types

The future adapter must accept and return the existing pure backend contract types from `guardian.continuity.contracts`. It must not accept unstructured ad hoc dictionaries.

| Pure Contract Type | Module | Adapter Role |
|---|---|---|
| `ContextPacket` | `guardian.continuity.contracts` | Accepted for write; returned on read |
| `RealityState` | `guardian.continuity.contracts` | Accepted for write; returned on read |
| `RealityCommit` | `guardian.continuity.contracts` | Accepted for write; returned on read |
| `ContinuityProvenance` | `guardian.continuity.contracts` | Embedded in all persisted records |
| `ContinuityScope` | `guardian.continuity.contracts` | Determines scope ID columns on writes |
| `ContinuitySource` | `guardian.continuity.contracts` | Embedded in context packet writes |
| `ContinuityCompileResult` | `guardian.continuity.compiler` | Adapter does NOT call the compiler; compiler output is passed to the adapter by a future write gate |

The adapter must be able to serialize and deserialize these contract types to/from JSONB columns without data loss. The canonical serialization is the dataclass field layout as JSON.

## Proposed Adapter Boundary

The following methods are proposed for the future adapter implementation. Names and signatures are candidates; actual implementation must match the contract types defined above.

```python
def save_context_packet(
    packet: ContextPacket,
    *,
    session: Session,
) -> StoredContinuityRecord:
    """Validate and persist a single Context Packet. Returns result record."""


def save_reality_state(
    state: RealityState,
    *,
    session: Session,
    link_packet_ids: Sequence[str] | None = None,
    link_relationship: str = "contributed",
) -> StoredContinuityRecord:
    """Validate and persist a RealityState snapshot. Optionally creates
    state-packet links in the same transaction. Returns result record."""


def save_reality_commit(
    commit: RealityCommit,
    *,
    session: Session,
) -> StoredContinuityRecord:
    """Validate and persist a single RealityCommit. Returns result record."""


def link_state_packets(
    state_id: str,
    packet_ids: Sequence[str],
    relationship: str,
    *,
    session: Session,
) -> StoredContinuityRecord:
    """Create state-packet provenance links. Duplicates rejected by uniqueness constraint."""


def load_reality_state(
    state_id: str,
    *,
    session: Session,
) -> RealityState | None:
    """Load a single RealityState by ID. Returns None if not found or soft-deleted."""


def load_latest_reality_state(
    scope: RealityScope,
    scope_ids: ContinuityScope,
    *,
    session: Session,
) -> RealityState | None:
    """Load the most recent non-deleted RealityState for a given scope."""


def list_reality_commits(
    scope_ids: ContinuityScope,
    *,
    session: Session,
    limit: int = 50,
) -> Sequence[RealityCommit]:
    """List RealityCommits for a given scope, most recent first."""
```

These are proposed names only. They are not implemented.

## Validation Requirements

Before any write, the future adapter must validate input using the existing pure validation helpers from `guardian.continuity.contracts`:

### Packet Writes

- Call `validate_context_packet(packet)`.
- If errors are returned, reject the write without partial persistence.
- Return validation errors in the result.

### State Writes

- Call `validate_reality_state(state)`.
- If errors are returned, reject the write without partial persistence.
- Return validation errors in the result.

### Commit Writes

- Call `validate_reality_commit(commit)`.
- If errors are returned, reject the write without partial persistence.
- Return validation errors in the result.

### General Rules

- Validation must occur before any INSERT.
- No partial writes: if validation fails, the database row must not exist.
- Validation errors must be preservable for diagnostic surfaces (not user-facing Pulse).
- The adapter must preserve provenance, schema_version, sensitivity, and retention from the input contract.
- The adapter must not infer missing facts from summary text, prose, or ambient context.

## Transaction and Atomicity Rules

The adapter must respect the following transaction boundaries:

| Operation | Atomicity Rule |
|---|---|
| Single context packet write | Single-record transaction is sufficient |
| Reality state write with state-packet links | State INSERT + link INSERTs must be in one transaction. If any link fails, the entire transaction rolls back. No state row may exist without its declared links. |
| Reality commit write | Single-record transaction is sufficient unless previous/new state references require additional writes |
| State-packet link batch | All links in the batch must be in one transaction. Partial success is not allowed. |

General rules:

- Transaction failure must return explicit error information: which operation failed, which constraint was violated, and whether the transaction was rolled back.
- The adapter must not swallow DB constraint failures (unique violations, NOT NULL violations, FK violations once FKs are added).
- The adapter must not silently succeed with a partial write.

## Write Authorization Gate

Persistence adapter existence does not authorize runtime writes. The following write gates remain closed:

- **Automatic compiler persistence:** `compile_reality_state()` output must not be written to storage by the adapter until a separate explicit write gate task approves compiler persistence wiring.
- **Heartbeat-triggered commits:** Automatic Reality Commits on schedule or heartbeat require worker infrastructure. This gate remains closed.
- **Semantic-delta and artifact-change triggers:** Requires the Continuity Compiler to detect meaningful changes at runtime. This gate remains closed.
- **Browser-captured packets:** `kind = 'browser'` packet writes require an approved browser consent/scope contract. This gate remains closed.
- **Project Pulse writes:** Pulse is a UI/read surface. The adapter must not write Pulse-specific records. This gate remains closed.
- **Worker and route writes:** Adding routes or workers that call the adapter requires separate task approval. The adapter is a library seam, not an API endpoint.

The adapter may be used for writes **only** by:

1. Developer/tester scripts that explicitly construct validated `ContextPacket`, `RealityState`, or `RealityCommit` objects and call the adapter directly (proof/test only, not production runtime).
2. Future explicitly approved write seams (Reality Stamp MVP, manual commit creation) after their own contract and proof tasks.

## Read Behavior

The adapter must support the following read operations. None are implemented by this contract.

### Allowed Reads

- **Read by explicit ID:** `load_reality_state(state_id)`, `load_reality_commit(commit_id)`, `load_context_packet(packet_id)`.
- **Read latest state by scope:** `load_latest_reality_state(scope, scope_ids)` using `ORDER BY compiled_at DESC LIMIT 1`.
- **List commits by scope and time:** `list_reality_commits(scope_ids, limit=N)` using `ORDER BY created_at DESC`.
- **List packets that contributed to a state:** Join `continuity_state_packet_links` on `state_id` and resolve packet rows.

### Read Filters

- Non-deleted records only by default (`WHERE deleted_at IS NULL`).
- Expose soft-deleted records only through explicit diagnostic or admin read paths if future policy allows.
- Read operations must not mutate state, create side effects, or trigger compilation.

## Provenance Requirements

The future adapter must preserve provenance without silent loss:

- Every persisted `ContextPacket` must carry `provenance_json` with `source_packet_ids`, `source_commit_ids`, `source_message_ids`, and `source_artifact_ids` when present in the input `ContinuityProvenance`.
- Every `RealityState` must carry `provenance_json` and `source_packet_ids_json` that remain consistent with `state_json`.
- Every `RealityCommit` must carry `provenance_json` with its contributing packet, commit, message, and artifact IDs.
- `continuity_state_packet_links` rows are themselves provenance — they must remain explainable. Deleting a state must cascade-delete or soft-delete its links per the delete policy chosen when FKs are added.
- Local database IDs (`UUID` or `SERIAL`) must not be treated as portable identity for export/restore. The export manifest must carry stable, export-scoped identifiers.
- The adapter must prepare for future manifest-based export semantics by keeping provenance fields explicit and structured.

## Retention, Sensitivity, and Consent

- The adapter must persist `sensitivity` and `retention` values for every `ContextPacket`.
- `sensitivity = 'shared'`, `sensitivity = 'restricted'`, `scope = 'dyad'`, and `scope = 'team'` remain candidate-only. The adapter may store these values but must not enforce runtime behavior (sync, sharing, access control) based on them until the relevant architecture is proven.
- Browser packet persistence (`kind = 'browser'`) requires an approved browser consent/scope contract before any browser-sourced packets are written. The adapter must not create or accept browser packets until that gate passes.
- Durable trait inference from continuity data is out of scope.
- Persona identity mutation from continuity data is out of scope.
- Project continuity is not persona identity. Reality State is not an identity claim.

## Graph-Off Baseline

The adapter must work with graph disabled:

- No Neo4j dependency may exist in the adapter module.
- The adapter must not write graph receipts, graph IDs, or graph lineage.
- Graph mount enrichment remains a separate future task gated by its own contract.
- Graph IDs, if added later, must be optional metadata in `provenance_json` only after a future graph boundary ADR/proof.
- Graph-off tests must verify that adapter writes and reads are correct with `GRAPH_MOUNT_MODE = 'disabled'`.

## Error and Result Shape

The future adapter must produce explicit result and error types. The following are proposed shapes only.

### StoredContinuityRecord

```python
@dataclass(frozen=True)
class StoredContinuityRecord:
    record_id: str          # DB-assigned ID
    table: str              # Which table was written to
    operation: str          # "insert", "update"
    success: bool           # True if the write committed
    validation_errors: tuple[str, ...] = ()
    db_errors: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    created_at: str | None = None
```

### ContinuityPersistenceError

```python
@dataclass(frozen=True)
class ContinuityPersistenceError:
    table: str
    operation: str
    message: str
    constraint_name: str | None = None
    detail: str | None = None
```

### ContinuityPersistenceResult

```python
@dataclass(frozen=True)
class ContinuityPersistenceResult:
    records: tuple[StoredContinuityRecord, ...] = ()
    errors: tuple[ContinuityPersistenceError, ...] = ()
    transaction_rolled_back: bool = False
```

These shapes are proposed only. They are not implemented by this contract.

## Testing Requirements for Future Implementation

When the adapter is implemented, the following tests must be provided:

| Test Category | Required Tests |
|---|---|
| Packet write/read | Valid packet survives write + readback; invalid packet rejected |
| State write/read | Valid state survives write + readback; state with no source packets rejected |
| State + link atomicity | State INSERT + link INSERTs in one transaction; failure rolls back both |
| Commit write/read | Valid commit survives write + readback; empty-title commit rejected |
| Uniqueness | Duplicate link triple rejected by DB constraint |
| Soft-delete | Non-deleted filter excludes soft-deleted rows; explicit admin read includes them if policy allows |
| Graph-off | All writes and reads succeed with `GRAPH_MOUNT_MODE = 'disabled'` |
| No runtime imports | Adapter module does not import routes, workers, providers, queues, or graph modules |
| No compiler auto-persistence | Adapter does not call `compile_reality_state()` unless explicitly invoked via a gated write seam |
| Transaction rollback | Partial failure (e.g., link uniqueness violation during state write) rolls back the entire transaction |

## Relationship to Existing Contracts

### ADR-030: Continuity Protocol Suite Runtime Gate

ADR-030 defines the 11-step implementation order. This contract defines the adapter boundary for step 5 (write-on-explicit-action Reality Stamp / Reality Commit MVP). It does not authorize compiler persistence (step 6) or broader runtime writes.

### ADR-031: Continuity Phase A Storage Migration Gate

ADR-031 gates the schema migration and requires that runtime writes remain separately approved. This contract is the separately approved write gate — it defines the adapter contract that must be satisfied before any write code lands.

### continuity-protocol-suite.md

The protocol suite defines the vocabulary. This contract defines how that vocabulary maps to persistent storage through the adapter.

### continuity-token-domain-proposal.md

Token domains (`kind`, `sensitivity`, `retention`, `scope`, `trigger`, `commit kind`) inform which columns the adapter must validate. The adapter must use candidate token values from the proposal until a canonical token registry is implemented.

### continuity-storage-schema-proposal.md

The storage proposal defines the tables and columns. This contract defines the adapter that writes to those tables and columns.

### 2026-06-25-continuity-phase-a-storage-migration-proof-rerun.md

The migration proof rerun confirms the tables exist and accept inserts. This contract defines the adapter that performs those inserts in a governed, validated, provenance-preserving way.

### account-export-restore-contract.md

When export/restore is implemented, the adapter's provenance preservation ensures continuity records can be exported with semantic equivalence. Local DB IDs are not portable identity.

### data-and-storage.md

The adapter writes to Postgres tables only. It does not replace Redis, vector, file, or graph storage roles.

### config-and-ops.md

No new environment variables are required for the adapter. Future config for retention policies or graph-mount modes is deferred.

### guardian/continuity/contracts.py

The adapter must accept and return the pure contract types defined in this module. It must use the validation helpers. It must not mutate the contracts.

### guardian/continuity/compiler.py

The adapter must not call `compile_reality_state()` automatically. Compiler output may be passed to the adapter by an explicitly approved write seam, but the adapter does not own compilation.

## Required Follow-Up Before Adapter Implementation

Before the adapter is implemented, a future task must:

1. Choose the exact module path (e.g., `guardian/continuity/persistence.py` or `guardian/continuity/adapter.py`).
2. Define the `StoredContinuityRecord`, `ContinuityPersistenceError`, and `ContinuityPersistenceResult` dataclasses concretely.
3. Define the DB session boundary (dependency injection, context manager, or explicit session passing).
4. Define SQLAlchemy model usage (which model classes map to which adapter methods).
5. Define transaction behavior (explicit `session.commit()` / `session.rollback()` boundaries).
6. Define test fixtures (in-memory or test DB, pre-created tables, valid contract fixtures).
7. Keep the runtime write gate closed: no auto-compiler-persistence, no heartbeat triggers, no route/worker writes.
8. Keep the compiler auto-persistence closed: adapter methods must not call `compile_reality_state()`.
9. Keep graph-off baseline tests: all adapter tests must pass with graph disabled.
10. Do not bundle adapter implementation with routes, workers, UI, browser capture, or export/restore.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No adapter code has been created.
- [ ] No runtime write path has been added.
- [ ] No compiler persistence wiring has been added.
- [ ] No routes, workers, UI, or browser behavior has been added.
- [ ] No graph-write enablement has occurred.
- [ ] No export/restore inclusion has been implemented.
- [ ] Phase A tables only (no Phase B normalization).
- [ ] Validation requirements are explicit for packets, states, and commits.
- [ ] Transaction and atomicity rules are explicit.
- [ ] Provenance obligations are explicit.
- [ ] Graph-off baseline is an explicit requirement.
- [ ] Runtime write gate is explicit (adapter does not authorize writes; write seams are separately gated).
- [ ] Required follow-up steps before implementation are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
