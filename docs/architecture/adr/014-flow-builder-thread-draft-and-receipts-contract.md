---
tags:
* architecture
* adr
* flow-builder
* guardian-thread
* receipts
* provenance
  aliases:
* ADR-014
* Flow Builder Thread, Draft, and Receipts Contract
---

# ADR-014: Flow Builder Thread, Draft, and Receipts Contract

## Status

Accepted

## Date

2026-04-22

## Context

Codexify already has a durable Guardian-thread chat runtime, a pre-execution Flow Builder seam, provenance-aware export/restore doctrine, and a separate post-completion inspection layer. What it does not yet have is a canonical contract that keeps conversation state, authored flow state, Builder presentation state, and run evidence from collapsing into one another.

Without that contract, future work can easily drift into one of three bad shapes:

- a separate chat system for Builder
- duplicate draft models for different authoring surfaces
- mixed conversation history and run-history semantics

That drift would make the system harder to reason about, harder to export safely, and easier to break during future Builder/runtime work.

## Problem Statement

Flow Builder needs to behave like a different view over the same system, not a new subsystem with its own chat model. The architecture must answer, in a stable and enforceable way:

- what is the canonical conversation container
- what is the canonical flow artifact
- how Builder chat relates to that conversation container
- how non-Builder surfaces represent the same flow when the graph cannot be shown inline
- how run evidence stays separate from ordinary chat messages
- how provenance survives from origin thread and message into the draft and into receipts

## Decision

Codexify establishes a thread-first, artifact-second contract:

- `GuardianThread` is the canonical conversation container.
- `FlowDraft` is the canonical authored flow artifact.
- `FlowBuilderView` is an alternate graph-centered view over one `FlowDraft`.
- Flow Builder chat is a real `GuardianThread` view with a Builder support-lane role.
- `FlowRunReceipt` is separate operational evidence for a flow run and is not a chat message.

Flow Builder is therefore not a separate system. It is a different presentation and interaction mode over the same underlying flow artifact and the same Guardian-thread conversation substrate.

## Canonical Terms

| Term | Canonical meaning |
|---|---|
| `GuardianThread` | The durable conversation container for Guardian chat. It is the canonical authorship lane and the only canonical chat history container in this contract. |
| `FlowDraft` | The canonical authored flow artifact. It captures the flow being shaped, edited, validated, and later run. It is not a chat transcript. |
| `FlowBuilderView` | The Builder presentation of a `FlowDraft`. Its center is the graph/canvas; the chat lane is a secondary support lane. |
| `FlowRunReceipt` | An immutable operational record that summarizes a single run attempt or other run evidence for a `FlowDraft`. It is distinct from ordinary chat messages. |
| Origin provenance | The preserved link from a `FlowDraft` or `FlowRunReceipt` back to the source `GuardianThread` and source message scope that birthed or informed it. |

## Relationship Model

The intended cardinalities are:

| Relationship | Cardinality | Rule |
|---|---|---|
| `GuardianThread` -> `FlowDraft` | `0..N` | One origin thread may spawn zero to many flow drafts. |
| `FlowDraft` -> origin thread/message scope | `1` | Each draft links back to one canonical origin thread/message scope. |
| `FlowDraft` -> active Builder support thread binding | `0..1` | A draft may have at most one active support-thread binding at a time. |
| `FlowDraft` -> `FlowRunReceipt` | `0..N` | Each flow owns its own receipt stream. |
| `FlowBuilderView` -> `FlowDraft` | `1` | The Builder view projects exactly one canonical draft at a time. |

Interpretation rules:

- A flow may be born in Guardian chat and later opened in Builder without changing the underlying flow identity.
- Builder chat is a real Guardian thread view, but it is semantically a support lane, not a separate chat store.
- Manual authoring, parameter-rail authoring, chat-driven drafting, and node rearrangement all converge on one `FlowDraft`.
- A receipt stream belongs to the draft, not to the general thread transcript.

## Explicit Answers

### Is Flow Builder chat a real Guardian thread view?

Yes. It must be backed by the normal Guardian-thread conversation model, not by a separate chat persistence system. The Builder chat lane is a role on top of a `GuardianThread`.

### Can a flow be born in Guardian chat and then opened in Builder without changing underlying identity?

Yes. The canonical flow identity is the `FlowDraft`, and opening the same draft in Builder must not mint a second draft identity.

### How do non-Builder surfaces represent a flow when the full graph cannot be shown inline?

They must degrade to a compact draft card, outline, or similar summary projection derived from the same `FlowDraft`. They must not invent a second draft object or pretend to be the interactive graph.

### Can one origin thread spawn multiple flows?

Yes. One `GuardianThread` may originate zero to many `FlowDraft`s. Each draft must still retain its own origin provenance chain.

### Does each flow own its own receipt stream?

Yes. Each `FlowDraft` owns zero to many `FlowRunReceipt`s, and those receipts are scoped to that draft's run history.

### How must provenance be carried from origin thread/message into draft and runs?

Provenance must survive as explicit links, not as implied context.

Implementations must be able to carry, at minimum, the following canonical provenance values:

- `origin_thread_id`
- `origin_message_id` or a bounded `origin_message_scope`
- `origin_project_id` when the originating thread is project-scoped
- `origin_request_id` or equivalent attempt identity when a draft is born from an assistant or tool-backed action
- `created_from` or equivalent source mode that explains whether the draft came from chat, Builder, parameter rails, or rearrangement

These values must flow from the origin conversation into the `FlowDraft`, and from the `FlowDraft` into each `FlowRunReceipt` that is generated from that draft.

## Provenance Rules

- Provenance is additive and must not replace canonical identity.
- A `FlowDraft` must retain its origin thread/message lineage even when its view changes.
- A `FlowRunReceipt` must reference the draft it belongs to and the origin provenance needed to explain why that run exists.
- Run evidence must not erase or overwrite the authored flow lineage.
- Chat history remains chat history; run receipts remain run receipts; neither may silently impersonate the other.

## Builder Presentation Rules

- The center of `FlowBuilderView` is the graph or canvas.
- The chat lane is secondary, right-sided, and dismissible.
- The chat lane supports flow authoring and clarification, but it does not become the primary representation of the Builder.
- Outside Builder, the system must present a compact derivative of the same `FlowDraft` rather than trying to inline the full interactive graph.
- A representation that cannot show the full graph must be honest about that limitation.

## Separation of Concerns

This contract separates three different kinds of state:

| State kind | What it represents | Canonical home |
|---|---|---|
| Authorship conversation | The discussion, questions, clarifications, and edits that led to a flow | `GuardianThread` |
| Flow artifact state | The current authored shape of the flow | `FlowDraft` |
| Execution/run evidence | The observed outcome of running the flow or attempting to run it | `FlowRunReceipt` |

This separation exists so that conversation history does not get confused with authored structure, and authored structure does not get confused with execution evidence.

## Non-Goals

This ADR does not:

- define the exact database schema
- define the exact frontend component composition
- define the exact graph engine or drag-drop implementation
- define the exact execution compiler or runtime
- claim runnable compile/execute support that the current runtime does not already prove
- collapse Persona Studio's non-conversational boundary into Flow Builder semantics
- merge run receipts into the ordinary chat transcript model
- introduce a separate Builder chat persistence system

## Deferred Implementation Items

The following are intentionally deferred:

- storage shape for `FlowDraft` and `FlowRunReceipt`
- how Builder support-thread bindings are represented in persistence
- how graph snapshots or outline projections are rendered in the frontend
- how draft editing operations are synchronized across authoring modes
- how execution receipts are emitted, indexed, and surfaced
- how a future compiler/runtime consumes the canonical draft

These are implementation concerns, not contract uncertainties.

## Migration and Compatibility Notes

This contract is designed to coexist with the current thread-based chat runtime and the current Flow Builder pre-execution seam.

- The existing Guardian-thread chat runtime remains the canonical conversation substrate.
- The current Builder seam may continue to act as a pre-execution/spec-first surface while `FlowDraft` becomes the canonical artifact contract.
- No separate chat history model is introduced here.
- No claim is made that the runtime already persists `FlowDraft` or `FlowRunReceipt` as first-class entities.
- Future implementation must preserve thread/message lineage and export/restore safety rather than rewriting chat history into run history.
- This ADR is compatible with ADR-006: it narrows how authored structure is bound to threads and receipts without changing the upstream elicitation doctrine.

## Consequences

### Positive

- One canonical flow artifact can be opened from different surfaces without identity drift.
- Builder support chat stays anchored to the same Guardian-thread runtime as the rest of Codexify.
- Run evidence becomes easier to audit because it is not mixed into the transcript.
- Export/restore paths remain more truthful because provenance and receipt history stay explicit.
- Future frontend and backend work can converge on one contract instead of inventing local versions of "the flow."

### Negative

- The system must maintain clearer distinctions between conversation, draft state, and receipts.
- Builder projections will need deliberate degraded representations outside the graph surface.
- New persistence and projection work will be needed before this contract becomes observable at runtime.

## Links

* [[ADR Index]]
* [[006-flow-builder-elicitation-lane|ADR-006 Flow Builder Elicitation Lane]]
* [[chat-runtime-contract|Chat Runtime Contract]]
* [[account-export-restore-contract|Account Export + Restore Contract]]
* [[data-and-storage|Data and Storage]]
* [[flows|Critical Flows]]
* [[system-overview|System Overview]]
* [[00-current-state]]

## Notes

This ADR defines the canonical contract for future implementation. It does not claim the runtime already ships the `FlowDraft`, `FlowBuilderView`, or `FlowRunReceipt` entities described here.
