---
tags:
* architecture
* adr
* continuity
* runtime-gate
* protocol-suite
  aliases:
* ADR-030
* Continuity Protocol Suite Runtime Gate
---

# ADR-030: Continuity Protocol Suite Runtime Gate

## Status

Accepted

## Date

2026-06-25

## Context

`docs/architecture/continuity-protocol-suite.md` defines a candidate architecture vocabulary and protocol family for Codexify's continuity layer: Context Packets, Reality State, Project Reality, Reality Commits, Discovery Commits, Project Pulse, Browser Context Provider, Continuity Cache, and optional Graph Mounts. That document is docs-only and explicitly does not implement runtime behavior.

The Continuity Protocol Suite vocabulary is accepted as architecture direction, but runtime implementation would materially affect:

- **Storage**: Reality State and Context Packets would add new Postgres entities, potentially with new tables, migration files, and cascade/retention rules.
- **Retrieval**: The Continuity Compiler sits between the Context Broker and model inference and would change how evidence is assembled for chat turns.
- **Canonical tokens**: Packet `kind` values, scope descriptors, confidence annotations, trigger types, and sensitivity/retention classifications would become runtime-active protocol tokens.
- **Operator truth surfaces**: Project Pulse would expose compiled continuity to the user; its output must follow UI token/layout law and must not leak diagnostics.
- **Queue/worker behavior**: Reality Commit triggers (semantic-delta, heartbeat, artifact-change, git-adjacent, pause, resume) would add worker paths and queue semantics.
- **Export/restore**: Reality State and Reality Commits must be exportable and restorable with provenance preservation.
- **Graph optionality**: Optional Graph Mounts must remain optional; the no-graph baseline must stay verified.

Without an explicit runtime gate, a future implementation task could accidentally widen the supported beta surface, introduce Neo4j as a required dependency, collapse continuity into identity, invent ad hoc packet tokens, or combine schema, compiler, UI, browser, graph, and sync changes in one unreviewable batch.

This ADR defines the gated path before any runtime implementation lands.

## Decision

Codexify accepts the Continuity Protocol Suite as candidate architecture vocabulary and requires ADR-gated implementation before any runtime behavior lands.

Future runtime implementation must proceed in small, independently provable slices. The first implementation must not combine schema, compiler behavior, UI, browser capture, graph mounts, sync, and provider routing in one task.

## Runtime Gate

Before runtime implementation of any Continuity Protocol Suite surface, the following gates must be passed. Each gate requires explicit review and signoff, not passive assumption.

### 1. Canonical Token / Domain Review

All repeated contract-bearing values — packet `kind`, scope descriptors, confidence levels, trigger types, sensitivity classifications, retention policies, Reality State field enums — must be reviewed for canonical token eligibility per `runtime-protocol-token-contract.md` and `canonical-token-philosophy.md`.

- Confirm no ad hoc literals remain before persistence is added.
- Register packet `kind` and scope tokens in `guardian/protocol_tokens.py` or a continuity-specific bounded registry.
- Add contract tests locking in enumerated values.

### 2. Storage Contract Review

Before any Postgres migration, review:

- Entity lifecycle: creation, update, soft-delete, cascade behavior for Reality State, Context Packets, Reality Commits, and Discovery Commits.
- Retention policies: which entities use `deleted_at` soft-delete vs TTL-based expiry.
- Index strategy: scope-based lookups (`project_id`, `thread_id`), recency-based range queries, packet-source filters.
- Migration rollback: every migration must have a tested downgrade path.

### 3. Provenance and Export/Restore Review

Reality State and Reality Commits must be exportable per `account-export-restore-contract.md`:

- Stable identifiers for state revisions.
- Explicit provenance chains linking compiled assertions to source packets.
- Source provenance must survive re-export and restore cycles.
- Restore must not silently drop Reality State or collapse it into raw message history.

### 4. Retrieval-Router Interaction Review

The Continuity Compiler introduces a compilation step between the Context Broker and model inference. Review:

- The compiler does not replace the Context Broker; it consumes broker output.
- The compiler does not widen retrieval scope or override `router-decision-table.md` intent classes.
- Compiled Reality State fed into chat context must not silently expand retrieval posture beyond policy.
- Retrieval trace payloads must distinguish broker-retrieved evidence from compiler-carried continuity.

### 5. Identity and Consent Review

Confirm:

- Project continuity is not persona identity; Reality State is not an identity claim.
- Compiled continuity does not perform durable trait inference without explicit deep-identity consent.
- Persona switching must not silently inherit another persona's Reality State.
- ADR-016 continuity governance settings (scope, intensity, exclusions) are respected at the compiler boundary.

### 6. Operator Truth Surface Review

Any operator-visible surface (debug traces, compilation logs, packet provenance views) must:

- Stay outside the user-facing Pulse surface.
- Not leak raw source packet content, hidden prompts, or chain-of-thought.
- Distinguish compilation confidence levels in operator views without confusing operators about runtime health.

### 7. Graph Optionality Review

Confirm:

- The no-graph path (Postgres-only) produces valid compiled Reality State.
- Graph mounts enrich but do not own continuity.
- Graph-off tests exist and pass before any optional enrichment is enabled.
- Graph mount errors do not corrupt or block Reality State compilation.
- Consistent with ADR-019, ADR-025, and ADR-026.

### 8. UI / Diagnostics Boundary Review

If Project Pulse or a compilation debug surface is implemented:

- Project Pulse must follow UI token/layout law and not become a diagnostics leak.
- Diagnostics must remain behind the operator boundary.
- Pulse output must be user-governed (dismissible, configurable per ADR-016).
- Low-confidence Pulse suggestions must be visually distinct from high-confidence assertions.

### 9. Migration / Rollback Review

Every schema addition must:

- Have an Alembic migration with a tested upgrade and downgrade path.
- Be verified in the supported local Compose path before merge.
- Not silently add run-once data migrations that assume production state.

### 10. Proof-Surface Definition

Before release claims, each implementation slice must define:

- Pure contract tests for packet/state/enum shapes.
- Compiler determinism tests (same inputs → same compiled output).
- Provenance preservation tests.
- Export-to-restore compatibility tests.
- Graph-off baseline tests.
- Live supported-path proof for end-to-end compilation flow.

## Approved Implementation Order

Future implementation must follow this sequence. Each step may be split into multiple tasks but must not skip or reorder gates.

1. **Token-domain proposal** — Propose canonical token registries for continuity packet `kind`, scope, confidence, trigger type, sensitivity, and retention values. Docs-only; precedes any code.

2. **Pure backend contract types** — Add typed Python/Typescript contracts for Context Packet, Reality State, Reality Commit, and Discovery Commit shapes with no persistence, no routes, and no runtime side effects.

3. **Deterministic compiler I/O shape tests** — Write pure-function tests for compiler input/output contracts with fixed packet inputs and expected Reality State outputs. No persistence, no worker, no provider calls.

4. **Postgres schema proposal** — Propose `continuity_packets`, `reality_state`, `reality_commits`, and `discovery_commits` table shapes in a migration-tracked proposal. Must include downgrade path.

5. **Write-on-explicit-action only Reality Stamp / Reality Commit MVP** — Implement manual Reality Commit persistence only. No heartbeat, no semantic-delta trigger, no automatic compilation. User must explicitly trigger.

6. **Project Reality read model** — Query-able compiled Project Reality from persisted packets and commits. Read-only; no automatic writes.

7. **Project Pulse UI spec** — Define the UI/output surface contract for Project Pulse. Must respect Workspace token law and diagnostics boundary.

8. **Browser packet provider spec** — Define the browser-to-Codexify packet emission contract without implementing browser automation.

9. **Optional Git-backed export** — Export Reality Commits as structured files to a local project reality folder. Postgres remains canonical.

10. **Optional graph mount enrichment** — Add Neo4j relationship traversal for continuity data behind existing graph-write flags. Must not be required for baseline compilation.

11. **Optional sync protocol** — Define federated Reality State synchronization without implementing it.

## Explicitly Deferred

The following are explicitly deferred beyond this ADR and must not proceed without their own ADR or implementation task:

- runtime persistence of Context Packets, Reality State, Reality Commits, or Discovery Commits
- DB migrations for continuity entities
- continuity workers (heartbeat, semantic-delta, artifact-change triggers)
- Reality Commit heartbeat or automatic commit triggers
- browser capture or Browser Context Provider packet emission
- Project Pulse UI rendering
- Reality State sync across federated nodes
- Git-backed Reality Commit storage
- graph writes or graph-backed continuity truth
- provider routing changes to support continuity compilation
- hosted continuity service (cloud)
- encryption or split-trust architecture for continuity data

## Non-Goals

This ADR does not, and must not be interpreted as:

- implementing any runtime behavior
- adding a DB schema or migration
- defining canonical token values (deferred to token-domain proposal task)
- widening the supported beta release promise
- introducing Neo4j or any graph system as a required dependency
- implementing browser automation or browser capture
- creating hidden prompt-only continuity behavior as a substitute for compiled Reality State
- mutating persona identity or deep-identity consent rules
- performing durable trait inference from continuity data
- enabling cross-user shared reality or dyadic continuity behavior

## Invariants

The following invariants govern all future Continuity Protocol Suite implementation:

| Invariant | Rationale |
|---|---|
| Continuity is user-governed | ADR-016 defines scope, intensity, decay, exclusions, inspection, and reset semantics. The compiler must not operate outside user-configured boundaries. |
| Project continuity is not persona identity | Reality State describes project working state, not who the user is. Persona switching must not inherit another persona's Reality State. |
| Compiled state must preserve provenance | Every assertion in Reality State must be traceable to one or more source Context Packets. Provenance survives export/restore cycles. |
| Exported continuity must be inspectable and restorable | When implemented, Reality State export must follow `account-export-restore-contract.md`. Restore must not silently drop compiled truth. |
| Graph mounts enrich but do not own continuity truth | Neo4j is optional. The no-graph Postgres path must produce valid compiled Reality State. Graph-off tests are required. |
| Project Pulse is a UI/output surface, not primary storage | Pulse renders briefs from Reality State; it does not store or compile truth. |
| Reality State is compiled truth, not raw transcript | Reality State is derived from packets, not a mirror of chat history. It is structured, confidence-annotated, and scoped. |
| Prompt/KV cache and pinned model state are runtime optimizations, not durable truth | These are provider/runtime accelerations with ephemeral lifetimes. They must not be confused with Reality State or Continuity Cache. |

## Proof Requirements

Each future implementation slice must satisfy the following proof requirements before any release claim:

| Implementation Slice | Required Proof Surface |
|---|---|
| Token-domain proposal | Documentation-only; verify tokens are registered and no ad hoc literals exist in code |
| Backend contract types | Pure contract tests for packet/state/enum shape validity and serialization round-trips |
| Compiler I/O shapes | Determinism tests (same inputs → same outputs); confidence annotation coverage; empty-input behavior |
| Postgres schema | Migration upgrade + downgrade tests; entity lifecycle tests (create, update, soft-delete, cascade) |
| Reality Commit MVP | Manual commit creation + readback; provenance chain integrity; export/restore compatibility |
| Project Reality read model | Scoped query tests; confidence surface; open-loop/rejected-path integrity |
| Project Pulse UI | UI rendering tests; token-law compliance; diagnostics-boundary verification |
| Browser packet provider | Consent/scoping tests; packet sensitivity enforcement; no-automation verification |
| Git-backed export | Round-trip tests (Postgres → export → re-import); diff-ability verification |
| Graph mount enrichment | Graph-off baseline tests; graph-on enrichment tests; graph-error non-corruption tests |
| Live supported-path proof | End-to-end compilation flow on the supported local Docker Compose path before release claim |

## Consequences

### Positive

- **Prevents architecture drift**: The gate ensures continuity implementation is deliberate, governed, and aligned with existing contracts before any code lands.
- **Lets continuity evolve without model/provider lock-in**: The compiler is above provider routing; models remain replaceable lanes.
- **Keeps Neo4j optional**: Graph mounts are explicitly enrichment only; the no-graph baseline must work.
- **Keeps runtime proof explicit**: Every slice has defined proof surfaces before release claims.

### Tradeoffs

- **Slows first implementation**: The gate adds review points that require time and signoff before code lands.
- **Requires multiple small tasks**: Implementation is deliberately sliced into small, provable units rather than one large change.
- **May duplicate some conceptual material from `continuity-protocol-suite.md`**: The gate restates key invariants and vocabulary to ensure implementation tasks carry them forward.
- **Requires future token and storage governance**: Canonical token registries and schema proposals must be created before persistence.

## Relationship to Existing Contracts

### `continuity-protocol-suite.md`

This ADR is the runtime gate for the protocol suite. The protocol suite defines the vocabulary; this ADR defines the rules for turning vocabulary into runtime behavior.

### ADR-015: Continuity Engine Working Set and Decay Contract

ADR-015 defines the user-governed continuity layer above thread-first chat. The Continuity Protocol Suite extends that direction with packet-level vocabulary and compilation semantics. This ADR gates the runtime implementation of that extension.

### ADR-016: Continuity Governance Surface Contract

ADR-016 defines the user-facing control plane for continuity scope, intensity, decay, import treatment, exclusions, inspection, and reset. The Continuity Compiler must respect these governance settings at the compilation boundary. This ADR's gate includes an explicit identity-and-consent review tied to ADR-016.

### `chat-runtime-contract.md`

Continuity compilation sits above turn-level completion. It does not change provider runtime states, request lifecycle states, or message-versus-attempt identity. This ADR's retrieval-router gate ensures the compiler does not silently alter chat completion semantics.

### `runtime-protocol-token-contract.md`

All continuity-related repeated literals (packet `kind`, scope, confidence, trigger types) must be promoted to canonical tokens before runtime use. This ADR's token-domain gate enforces that requirement.

### `canonical-token-philosophy.md`

The continuity packet vocabulary is a textbook case for canonical tokenization: repeated across surfaces (browser, thread, git, artifact, persona, provider), contract-bearing (code branches on kind, tests assert enums), and dangerous to rename casually. This ADR applies the canonical token philosophy to the continuity domain.

### `account-export-restore-contract.md`

When Reality State persistence is implemented, it must be exportable and restorable. This ADR's provenance gate ensures that compiled truth preserves source packet links and survives re-export cycles.

### `router-decision-table.md`

The Continuity Compiler consumes Context Broker output. It does not replace or widen retrieval intent. This ADR's retrieval-router gate ensures the compiler does not silently change retrieval behavior.

### `data-and-storage.md`

Future continuity tables must respect existing storage invariants: Postgres as system of record, soft-delete conventions where applicable, and FK-driven cascade semantics. This ADR's storage gate enforces alignment.

### `self-extending-agent-plugin-system.md`

Future plugins may emit Context Packets. Plugin-emitted packets must follow the Context Packet Protocol envelope. This ADR's token-domain and identity gates ensure plugin continuity does not bypass governance.

### `codexify_workspace_surface_spec_v_1.md`

Project Pulse is a future UI surface not yet integrated into Workspace. When Pulse UI is implemented, it must follow Workspace token/layout law, card hierarchy, and view-specific rules. This ADR's UI gate defers Pulse to its own spec task.

## Follow-Up Tasks

The following tasks are explicitly not implemented by this ADR and must proceed as separate work items:

| Task | Description | Dependencies |
|---|---|---|
| Continuity token-domain proposal | Propose canonical token registries for packet `kind`, scope, confidence, trigger type, sensitivity, and retention values | This ADR |
| Backend contract types | Add typed Python contracts for Context Packet, Reality State, Reality Commit, and Discovery Commit with no persistence | Token-domain proposal |
| Compiler I/O shape tests | Pure-function determinism tests for compiler input/output | Backend contract types |
| Reality Stamp contract | Define the minimal write-on-explicit-action Reality Commit persistence contract | Backend contract types |
| Discovery Commit contract | Define the Discovery Commit persistence shape and mental-model-change detection contract | Reality Stamp contract |
| Project Reality read model | Query-able compiled Project Reality from persisted packets and commits | Reality Stamp contract |
| Project Pulse UI spec | Define the UI/output surface contract for Project Pulse | Project Reality read model |
| Browser Context Provider spec | Define the browser-to-Codexify packet emission contract without automation | Token-domain proposal |
| Git-backed Reality Commit export | Export Reality Commits as structured files to a local project reality folder | Reality Stamp contract |
| Optional graph mount contract | Define Neo4j relationship traversal for continuity behind existing graph-write flags | Reality Stamp contract |
| Reciprocal/shared reality contract | Define how Reality State may be shared or synchronized across users; explicitly future work | All of the above |
