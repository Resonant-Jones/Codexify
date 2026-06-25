# Continuity Runtime Invocation Boundary Contract

> Classification: docs-only invocation boundary contract  
> Status: proposed  
> Implementation status: no runtime call sites, routes, command bus actions, workers, UI, browser capture, graph writes, sync, export/restore, or Project Pulse exist  
> Normative language: "must", "must not", "should", "allowed", "forbidden", "deferred", and "future" are intentional.

Purpose: Define the boundary for any future runtime invocation of the Continuity explicit write-action service. The service exists and is tested (159 tests, zero skips), but it is not wired into runtime. This contract must decide what caller surface is allowed next, what remains forbidden, and what proof is required before any route, command bus, worker, UI, or diagnostic surface can invoke continuity writes.

Last updated: 2026-06-25

## Purpose

The Continuity write-action service (`guardian/continuity/write_actions.py`) implements four explicit write actions: `create_reality_stamp`, `compile_and_save_reality_state_from_explicit_packets`, `create_reality_commit`, and `link_state_to_packets`. It is proven correct against live Postgres (159 tests, zero skips). But it is a library seam — it writes only when directly invoked with explicit input and an explicit adapter dependency.

Tested direct service invocation is not the same as runtime authorization. Without an explicit invocation boundary, a future task could accidentally:

- Wire continuity writes to ordinary chat completion (`POST /api/chat/{thread_id}/complete`)
- Register a command bus action that calls `create_reality_commit` as a side effect of tool execution
- Add a UI button that creates Reality Commits without explicit actor/scope input
- Create a background worker that runs `compile_and_save` on a heartbeat
- Wire browser tab activity to `create_reality_stamp` without consent review
- Confuse write receipts with task events, leading to false UI "confirmation" of durable writes
- Bypass the explicit-action requirement by wrapping automatic behavior in a thin explicit facade

This contract exists to prevent that. It defines the gate between "the service exists" and "the service is called from runtime."

## Non-Goals

This contract does not, and must not be interpreted as:

- implementing any runtime call site
- adding a route
- adding command bus integration
- adding a worker
- adding UI
- implementing Project Pulse
- implementing browser capture
- enabling graph writes
- implementing sync behavior
- changing provider routing
- implementing export/restore inclusion
- enabling heartbeat-triggered writes
- enabling semantic-delta-triggered writes
- enabling compiler auto-persistence
- implementing shared/dyadic reality runtime
- widening the supported beta release promise

## Current Implemented Seam

The following modules exist and are tested. None are wired into runtime.

### guardian/continuity/contracts.py

- **What it does**: Defines pure dataclasses (`ContextPacket`, `RealityState`, `RealityCommit`, etc.), candidate token aliases, candidate value tuples, and pure validation helpers.
- **What it does not do**: Persist data, call providers, call Redis, call Neo4j, call routes, call workers, call the compiler.

### guardian/continuity/compiler.py

- **What it does**: Provides `compile_reality_state()` — a pure, deterministic function that transforms explicit `ContextPacket` inputs into a `RealityState` output.
- **What it does not do**: Persist data, call models, call retrieval, call routes, call workers, auto-run on chat turns.

### guardian/continuity/persistence.py

- **What it does**: Provides `ContinuityPersistenceAdapter` — an explicit persistence seam that requires an explicit SQLAlchemy session. Validates input before writes, preserves provenance, and handles transaction boundaries.
- **What it does not do**: Create sessions internally, call routes, workers, providers, Redis, Neo4j, or the compiler.

### guardian/continuity/write_actions.py

- **What it does**: Provides `ContinuityWriteActionService` — an explicit write-action seam that requires an explicit `ContinuityPersistenceAdapter`. Implements four write actions with explicit input dataclasses and explicit write receipts.
- **What it does not do**: Create adapters internally, create DB sessions, call routes, workers, providers, Redis, Neo4j, graph APIs, or auto-invoke the compiler outside the `compile_and_save_reality_state_from_explicit_packets` action.
- **Direct explicit invocation exists only as a service seam.** No runtime code path calls these methods.

## Invocation Boundary Principle

Continuity writes may only be invoked under the following conditions:

1. **Named authorized caller surface**: The caller must be a named, bounded, explicitly approved invocation surface — not an ambient runtime path.
2. **Explicit action input**: The caller must construct and pass an explicit action input dataclass (`RealityStampInput`, `RealityStateWriteInput`, `RealityCommitWriteInput`, or `StatePacketLinkInput`). No implicit construction from ambient state.
3. **Preserve actor identity and scope**: The caller must carry an explicit `ContinuityActionActor` with `actor_id` and `actor_kind`. The actor represents who or what requested the write, not an inferred identity.
4. **Return or record a write receipt**: Every invocation must return or persist a `ContinuityWriteReceipt`. The receipt is the canonical result of the write action.
5. **No ambient-to-intent translation**: The caller must not translate ambient runtime completion (chat turn finished, provider responded, retrieval returned results) into write intent.
6. **No model inference as write authorization**: The caller must not use a model's output as implicit permission to write continuity records. Only explicit, structured action input is valid.

## Candidate Caller Surfaces

| Caller Surface | Status for MVP | Why |
|---|---|---|
| `internal_diagnostic_command` | **Allowed candidate** | Smallest safe seam. An internal-only CLI or script that an operator explicitly invokes with explicit input. No route, no worker, no UI. |
| `developer_operator_route` | **Allowed candidate** | If the repo already has an authenticated diagnostic/operator route pattern, a narrowly scoped `POST` endpoint that requires explicit credentials and explicit action input is the next-smallest seam. |
| `user_visible_ui_action` | **Deferred** | Requires UI design, Project Pulse integration, accessibility review, and explicit visual confirmation of write intent. Premature for MVP. |
| `command_bus_action` | **Deferred** | The command bus has its own invoke/policy/idempotency surface. Continuity writes would need command-specific policy, actor derivation, and receipt semantics. Deferred until command bus continuity policy is explicit. |
| `worker_action` | **Forbidden for MVP** | Workers imply automatic, background, or scheduled execution. Heartbeat, semantic-delta, and artifact-change triggers are explicitly forbidden by ADR-030 and the write-action contract. |
| `chat_turn_hook` | **Forbidden for MVP** | Chat turns are ambient by nature. Wiring continuity writes to turn completion violates the explicit-action requirement and would produce silent, unreviewed continuity state. |
| `browser_context_action` | **Forbidden for MVP** | Browser capture requires consent/scope architecture that does not exist. Tab visibility or DOM events must not trigger continuity writes. |
| `project_pulse_action` | **Forbidden for MVP** | Project Pulse is a read/UI surface. It must not cause writes. Pulse implementation requires separate task. |

### Required Proof Before Any Implementation

| Caller Surface | Minimum Proof Required |
|---|---|
| `internal_diagnostic_command` | Invocation script exists; explicit input supplied; receipt returned; no runtime wiring; no auto-triggers |
| `developer_operator_route` | Route exists behind existing auth pattern; explicit action input mapping; receipt serialized; no worker/chat UI/graph dependencies |
| `user_visible_ui_action` | UI spec; user consent flow; explicit confirmation; Pulse boundary; accessibility; deferred |
| `command_bus_action` | Command bus policy; actor derivation; idempotency semantics; receipt integration; deferred |
| Any forbidden surface | Must not be implemented; if attempted, must be rejected at review |

## Approved Next Caller Boundary

**Recommendation: `developer_operator_route`**

The smallest safe runtime seam that provides operator-visible proof of continuity writes is a developer/operator-only diagnostic route. Codexify already has an authenticated backend with existing diagnostic surfaces (health checks, debug RAG traces, operator Scout surfaces). Adding a narrowly scoped continuity diagnostic route aligns with existing patterns.

### Exact future caller class

A single `POST` endpoint that:

- Requires the existing backend auth/API-key boundary (same `GUARDIAN_API_KEY` or equivalent)
- Accepts explicit action input (one of the four action input dataclass shapes)
- Constructs a `ContinuityPersistenceAdapter` from the route's DB session dependency
- Invokes the corresponding `ContinuityWriteActionService` method
- Returns the `ContinuityWriteReceipt` as JSON
- Does not publish task events, SSE, or UI notifications
- Does not integrate with chat, retrieval, providers, graph, browser, or workers

### What action kinds it may invoke

All four currently implemented action kinds:

- `create_reality_stamp`
- `compile_and_save_reality_state_from_explicit_packets`
- `create_reality_commit`
- `link_state_to_packets`

### What remains deferred

- `user_visible_ui_action`
- `command_bus_action`
- `worker_action`
- `chat_turn_hook`
- `browser_context_action`
- `project_pulse_action`

### Authentication / session / identity requirements

- Must use existing backend auth boundary (`GUARDIAN_API_KEY` or equivalent)
- Actor identity must be explicit in the request payload, not derived from the session
- Project/thread scope must be explicit in the request payload
- No write-as-another-user behavior
- Service accounts or system actors require future policy

### Why ordinary chat completion must not invoke it

Chat completion is ambient, provider-driven, and turn-scoped. Continuity writes are explicit, operator-scoped, and cross-session. Wiring them together would produce silent, unreviewed Reality Commits on every chat turn — the exact anti-pattern this contract exists to prevent.

## Explicit Input Requirements

Every future runtime caller must supply the following explicit input for each write action:

| Field | Required? | Notes |
|---|---|---|
| `action_id` | Yes | Unique action identifier; caller-generated |
| `actor_id` | Yes | Who or what requested the write |
| `actor_kind` | Yes | `"user"`, `"operator"`, `"system"` (future policy for system actors) |
| User/account scope | Yes when applicable | `user_id` or equivalent scope |
| Project ID | Yes for project-scoped actions | Explicit project reference |
| Thread ID | Yes for thread-scoped actions | Explicit thread reference |
| Explicit packet/state/commit payload fields | Yes | Per the action input dataclass contract |
| Source/provenance refs | Yes when available | Source packet, commit, message, artifact IDs |
| Sensitivity | Yes | `"local"` or `"private"` for MVP |
| Retention | Yes | `"session"` or `"project"` for MVP |
| Request/created timestamp | Yes | ISO-8601 |

These values must not be silently inferred from ambient runtime state. If the caller cannot provide an explicit value, that field must be documented as unavailable — not backfilled with an assumption.

## Identity and Session Boundary

- Actor identity must be explicit in the action input. The caller must not write as another user.
- Project/thread scope must be authorized by the existing scope authorization rules (user owns the project, user is a member of the thread, etc.).
- `team`, `dyad`, `shared` semantics remain deferred. No multi-user scope authorization exists.
- In local/developer mode, the actor must still be explicitly recorded. `"local"` as a default user_id is acceptable for the `ContinuityPersistenceAdapter` scope defaults, but the action input's `actor_id` must be explicit.
- Service accounts or system actors require a future policy defining their authority, audit trail, and action kinds.

## Receipt and Operator Truth

Every runtime invocation must return or record a `ContinuityWriteReceipt` with the following guarantees:

| Receipt Field | Guarantee |
|---|---|
| `action_id` | Matches the caller's action ID |
| `action_kind` | Matches the invoked action kind |
| `success` | `True` only if all records were persisted and confirmed |
| `created_*_ids` | Populated with adapter-returned record IDs on success |
| `validation_errors` | Non-empty when input validation failed before write |
| `persistence_errors` | Non-empty when DB write failed after validation passed |
| `graph_used` | Always `False` for MVP |
| `runtime_event_published` | Always `False` for MVP |
| `created_at` | ISO-8601 timestamp of receipt creation |

Additional rules:

- Receipt success must be backed by adapter persistence result. The receipt is not a "best effort" signal.
- Receipt must not be confused with task event publication. Task events are queue/worker lifecycle signals. Write receipts are persistence confirmation signals.
- Receipt must not be confused with route acceptance. HTTP 200 + `"success": false` in the receipt body is a valid response — the route accepted the request, but the write failed.
- Operator-visible diagnostics must make failures explicit. A failed receipt must surface its `validation_errors` and `persistence_errors` in any operator surface.

## Runtime Event Policy

No runtime events are approved by this contract:

- No `task.created`, `task.completed`, or continuity-specific task events may be emitted by write actions.
- Write receipts are not task events and must not be published on `codexify:task:{task_id}:events` or equivalent event streams.
- If future event publication is desired, a separate token/event contract review is required. That review must define:
  - Event type tokens
  - Event payload shape
  - Whether events are durable or transient
  - Whether events imply write success or merely write attempt
  - How events relate to the existing task event infrastructure
- Until that review, the durable database record and the adapter result remain the sole proof of write success.

## Forbidden Invocation Paths

The following invocation paths are explicitly forbidden for MVP and must not be implemented:

- **Ordinary chat-turn completion** — `POST /api/chat/{thread_id}/complete` must not write continuity records
- **Provider response completion** — Model output must not trigger continuity writes
- **Retrieval hit** — Context broker results must not trigger continuity writes
- **Compiler output alone** — `compile_reality_state()` returning a result must not auto-persist
- **Heartbeat** — No periodic scheduler may trigger continuity writes
- **Semantic delta detection** — No change-detection analysis may trigger continuity writes
- **Background worker loop** — No worker dequeue may independently decide to write continuity records
- **Browser tab visibility** — No browser event may trigger continuity writes
- **Graph enrichment** — Neo4j traversal results must not trigger continuity writes
- **Project Pulse rendering** — Pulse UI must not cause continuity writes
- **Export/restore operation** — Export and import must not create continuity records as side effects
- **Sync operation** — Federation must not create continuity records on the receiving node
- **Persona/style mutation** — Profile changes must not trigger continuity writes

## Transaction and Session Boundary

The future caller must manage DB sessions according to the following rules:

- Obtain a DB session through the repo's approved runtime DB dependency pattern (existing `get_db` or equivalent).
- Session ownership must be explicit — the caller creates or receives the session, passes it to the adapter, and commits or rolls back.
- The caller must not create global or module-level sessions.
- The caller must not leave transaction boundaries ambiguous. If a write action spans multiple adapter calls (state save + link batch), the caller must ensure the transaction boundary is consistent.
- The receipt must distinguish validation failure (pre-write) from persistence failure (post-write) through its `validation_errors` vs `persistence_errors` fields.
- No partial state/link/commit bundle may be reported as success. If the adapter returns failure for any record in a multi-record action, the receipt must be `success=False`.

## Graph-Off Baseline

Runtime invocation must work with graph disabled:

- Graph writes are forbidden.
- Graph receipts are forbidden.
- Graph IDs must not be required for write success.
- The receipt's `graph_used` field must be `False`.
- Optional graph enrichment requires a separate future contract and must not be wired through the invocation boundary without explicit approval.

## Export/Restore Boundary

Runtime invocation does not implement export inclusion:

- The caller must preserve enough provenance in the created records for future manifest-based export.
- Local DB IDs are not portable export identity by default.
- No restore behavior is implemented.
- When export/restore continuity inclusion is implemented, it must handle remapping of local IDs and re-linking of state-packet relationships.

## Project Pulse Boundary

Project Pulse remains a read/UI surface only:

- Project Pulse must not cause continuity writes. No "save as Reality Commit" button hidden in Pulse.
- Read-after-write confirmation in the write-action service is not Project Pulse — it is write verification.
- Project Pulse implementation requires a separate task with its own UI spec, accessibility review, and read-model contract.
- If Pulse later surfaces write receipts, it must clearly distinguish write confirmation from state display.

## Browser Context Boundary

Browser capture remains deferred:

- Tab visibility must not imply write authorization.
- Selected text or DOM digest capture requires an explicit future consent/scope contract.
- Browser context packets are not part of MVP runtime invocation.
- The `kind = 'browser'` ContextPacket kind is candidate vocabulary only — no runtime code may construct or save browser packets until the consent/scope contract is approved.

## Required Tests for Future Caller Implementation

When the runtime caller is implemented, the following tests must pass:

| Test Category | Required Tests |
|---|---|
| Authorized invocation | Explicit call with valid action input returns success receipt with created IDs |
| Unauthorized invocation | Call without valid auth returns appropriate error (not a receipt) |
| Missing actor | Action input without actor_id is rejected before write |
| Missing scope | Required scope IDs absent → rejection |
| Invalid action input | Validation errors returned in receipt; no write occurs |
| Adapter failure | DB error returns failure receipt with persistence_errors |
| No chat-turn auto-write | Chat completion does not call write-action service |
| No worker auto-write | Worker dequeue does not call write-action service |
| No compiler auto-persistence | Compiler output is not auto-saved by the caller surface |
| No runtime events | No task events published by write invocation |
| No graph usage | `graph_used` is `False` in all receipts |
| No browser capture | No browser module imports or calls in caller module |
| No provider/retrieval trigger | No provider or retrieval module imports in caller module |
| Receipt shape correct | Receipt includes action_id, action_kind, success, created IDs, and `graph_used`/`runtime_event_published` = `False` |

## Relationship to Existing Contracts

### ADR-030: Continuity Protocol Suite Runtime Gate

ADR-030 gates all continuity runtime work. This contract defines the invocation gate for step 5 (write-on-explicit-action MVP). It does not authorize steps 6–11 (compiler persistence, read model, Pulse, browser, graph, sync).

### ADR-031: Continuity Phase A Storage Migration Gate

ADR-031 gates schema migration and requires that runtime writes remain separately approved. This contract defines the runtime invocation boundary — the separate approval required before writes are triggered by runtime callers.

### continuity-protocol-suite.md

The protocol suite defines Reality State, Reality Commit, and Project Reality concepts. This contract defines who may invoke the service that creates those records at runtime.

### continuity-write-action-contract.md

The write-action contract defines the four allowed MVP write actions and their validation/transaction/provenance rules. This contract defines who may call those actions from runtime.

### continuity-persistence-adapter-contract.md

The adapter contract defines the adapter interface. The invocation boundary contract defines who may create an adapter at runtime and pass it to the write-action service.

### 2026-06-25-continuity-persistence-adapter-live-db-proof.md

The adapter is proven. The write-action service is proven. This contract gates the first runtime caller that uses both.

### chat-runtime-contract.md

Chat runtime states (provider states, request lifecycle states, message/attempt identity) are not continuity write states. The invocation boundary explicitly forbids chat-turn hooks.

### runtime-protocol-token-contract.md

No runtime events are approved. Write receipts are not task events. Any future event publication requires separate token review.

### account-export-restore-contract.md

Export/restore inclusion is deferred. Created records must preserve provenance for future export.

### data-and-storage.md

The runtime caller writes only to Postgres via the adapter. No Redis, vector, file, or graph storage is used.

### guardian/continuity/write_actions.py

The invocation boundary defines who calls `ContinuityWriteActionService` at runtime. The service itself remains unchanged by this contract.

## Required Follow-Up Before Runtime Caller Implementation

Before runtime caller code is implemented, a future task must:

1. Choose exact module path (e.g., `guardian/routes/continuity_diagnostic.py` or a new diagnostic module).
2. Choose exact caller surface (`developer_operator_route` is recommended).
3. Define auth/session dependency — use existing `GUARDIAN_API_KEY` or equivalent backend auth pattern.
4. Define actor extraction — how `actor_id` and `actor_kind` are derived from the request or explicitly supplied.
5. Define action input mapping — how the HTTP request body maps to the four action input dataclasses.
6. Define receipt handling — how `ContinuityWriteReceipt` is serialized to JSON and returned.
7. Define tests for forbidden ambient writes — chat turns, workers, compiler, heartbeat, browser, retrieval must not trigger writes.
8. Define tests for graph-off behavior — all invocations work with Neo4j absent.
9. Define whether the surface is internal-only, developer-only, or user-callable. For MVP, internal-only or developer-only is recommended.
10. Keep UI, browser, graph, export, and sync modules out of scope. Do not bundle caller implementation with any other surface.

## Acceptance Checklist

Reviewers must confirm all of the following before accepting this contract:

- [ ] This document is docs-only and introduces no runtime behavior.
- [ ] No runtime caller has been implemented.
- [ ] No route has been added.
- [ ] No worker has been added.
- [ ] No command bus integration has been added.
- [ ] No UI or browser behavior has been added.
- [ ] No graph-write enablement has occurred.
- [ ] No export/restore inclusion has been implemented.
- [ ] The approved next caller boundary is explicit (`developer_operator_route` recommended).
- [ ] Forbidden invocation paths are explicitly listed (13 paths).
- [ ] Identity/session boundary is explicit.
- [ ] Receipt and operator truth requirements are explicit.
- [ ] Graph-off baseline is explicit.
- [ ] Required follow-up steps before implementation are explicitly listed.
- [ ] `00-current-state.md` remains the short-horizon release-truth authority.
