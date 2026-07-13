# Shared Presence Protocol

## Title and Metadata

- Title: `Shared Presence Protocol`
- Classification: `architecture contract / future capability`
- Status: `proposal`
- Last updated: `2026-06-30`
- Source anchors:
  - `/docs/architecture/00-current-state.md`
  - `/docs/architecture/system-overview.md`
  - `/docs/architecture/flows.md`
  - `/docs/architecture/data-and-storage.md`
  - `/docs/architecture/modules-and-ownership.md`
  - `/docs/architecture/runtime-protocol-token-contract.md`
  - `/docs/architecture/canonical-token-philosophy.md`
  - `/docs/architecture/account-export-restore-contract.md`
  - `/docs/architecture/self-extending-agent-plugin-system.md`
  - `/docs/architecture/pi-invocation-boundary-contract.md`
  - `/docs/architecture/codexify_workspace_surface_spec_v_1.md`
- ADR impact:
  - Classification: requires future ADR before runtime implementation
  - Governing ADRs/contracts:
    - Current-state release boundary
    - Runtime Protocol Token Contract
    - Canonical Token Philosophy
    - Account Export + Restore Contract
    - Self-Extending Agent Plugin System
    - Pi Invocation Boundary Contract
    - existing queue/worker/chat runtime contracts where relevant
  - Reason:
    - Shared Presence introduces future session semantics, participant roles, permission and control boundaries, event vocabularies, and transport abstractions. This document defines the proposal boundary only and does not claim implementation.

## Purpose

Shared Presence Protocol defines a future synchronous co-working layer where humans and AI agents can inhabit the same operational session. The goal is to make the live working state shared, observable, and permissioned without collapsing presence into identity or transport into product meaning.

VNC may be a Phase 1 bootstrap transport, but it is not the canonical product abstraction. The product concept is shared operational presence: multiple humans and AI participants observing common state, collaborating against the same live session, and optionally receiving scoped control.

This document is docs-only. It does not widen the supported beta promise, and it does not claim runtime behavior that is not yet present on `main`.

## Product Thesis

Codexify should allow multiple humans and AI participants to inhabit the same working environment synchronously. Shared Presence establishes a common operational reality so discussion, execution, observation, and assistance occur against the same live state rather than separate reconstructed contexts.

## Non-Goals

- no runtime implementation
- no route changes
- no worker orchestration
- no VNC integration
- no WebRTC integration
- no CRDT implementation
- no schema migration
- no release support claim
- no autonomous agent loop expansion
- no identity or memory mutation
- no new supported beta surface

## Core Principles

- Shared reality: participants should see and reason about the same working session.
- Presence is separate from identity: a session can know who or what is here without redefining durable identity.
- Observation before control: observation is the default; control is a higher-trust action.
- Control is permissioned, scoped, and revocable: any control grant must name its surface, limit its reach, and be removable.
- AI participants are participants, not hidden background actors: they must be visible as participants with explicit scope.
- Transport is abstract: pixel transport, event transport, and semantic state transport are different layers.
- Shared pixels are not shared truth: pixels can bootstrap a shared experience without proving semantic state.
- Runtime proof is required before release claims: docs do not convert future capability into supported behavior.

## Canonical Terms

| Term | Definition |
|---|---|
| `Shared Presence Protocol` | The future canonical contract for shared operational presence across sessions, participants, surfaces, events, permissions, and receipts. |
| `Presence Session` | A bounded shared working session with a roster, one or more shared surfaces, event history, and control policy. |
| `Participant` | Any human, AI, system, or guardian-scoped actor recorded as present in a session. |
| `Human Participant` | A human user participating in the session under their own durable identity. |
| `AI Participant` | An AI- or agent-mediated participant that can observe, suggest, or act only within explicit scope. |
| `Observer` | A participant role that can view presence and session state without inheriting control authority. |
| `Shared Surface` | A bounded working surface that can be shared within a presence session, such as desktop, browser, editor, or terminal. |
| `Presence Event` | A session event that records a presence-related action, observation, lifecycle transition, or control change. |
| `Control Lease` | A scoped, revocable authorization that allows a participant to act on a surface for a limited time or purpose. |
| `Transport Adapter` | A bounded mapping layer that converts a transport mechanism into presence events, receipts, and session updates. |
| `Pixel Transport` | A transport that moves pixels or screen frames rather than semantic working state. |
| `State Transport` | A transport that moves semantic state, object state, or collaborative structure rather than pixels alone. |
| `Annotation` | A user-visible note, pointer, comment, or marker attached to a session or surface. |
| `Presence Receipt` | A structured record that confirms a presence event, control grant, lifecycle transition, or observation acknowledgement. |

## Boundary Model

Presence, identity, control, and provenance must remain distinct:

- Presence answers `who or what is here?`
- Identity answers `who owns durable identity?`
- Control answers `who can act?`
- Provenance answers `what happened and where did it come from?`

These concerns may relate, but they must not collapse into one another. A participant can be present without being identity-owning, observing without controlling, and controlling only within a scoped lease.

## Participant Model

Proposed participant classes:

| Class | Proposed permissions | Display requirements |
|---|---|---|
| `human` | May observe, annotate, request control, and receive scoped control if authorized. | Must display a human-owned identity label and a stable participant marker. |
| `guardian` | May observe, annotate, request control, and exercise control only through governed Guardian authority and explicit scope. | Must display as Guardian-linked, not anonymous, and not as a generic human. |
| `coding_agent` | May observe within granted scope, suggest without control, and act only when explicitly granted control. | Must display as AI/agent-mediated, with clear participant and scope labeling. |
| `observer` | May observe only, or observe plus annotate if explicitly allowed. | Must display as read-only or observer-class with no implied control authority. |
| `system` | May emit lifecycle, heartbeat, and receipt events; no human-style control authority. | Must display as system-scoped, not as a user or agent. |

Participant rules:

- Participants must not own identity.
- Participants must not rewrite memory.
- Participants must not bypass Guardian authority.
- Participant role labels must not be treated as hidden permissions.
- A participant class may exist without implying execution power.

## Shared Surface Model

Possible future shared surfaces include:

- desktop
- browser
- editor
- terminal
- document
- workspace
- flow builder
- diagnostics/operator surface

The surface model is intentionally extensible, but it must not become an unbounded plugin loophole. Any new surface class must be explicitly named, bounded, and governed by contract rather than inferred from transport availability.

## Transport Model

| Transport | Fit | Limits | Phase posture |
|---|---|---|---|
| VNC / pixel transport | Good for a quick shared desktop prototype and for proving co-viewing on an existing desktop surface. | Weak for semantic state, object identity, and structured collaboration truth. | Phase 1 bootstrap only. |
| WebRTC screen/data channel | Good for lower-latency browser-native sharing and mixed pixel/data transport. | Still does not establish semantic truth by itself. | Candidate future transport. |
| WebSocket event transport | Good for presence events, annotations, roster updates, and receipts. | Does not carry pixel or object state by itself. | Candidate event backbone. |
| CRDT / state sync | Good for native collaborative objects and mergeable shared state. | Requires explicit object model and conflict policy. | Candidate semantic state layer. |
| Future native Codexify protocol | Desired long-term shape for a native shared presence contract. | Not yet defined. | Target architectural direction. |

VNC is Phase 1 bootstrap only. It may prove shared desktop experience, but it does not define the product boundary.

## Permission and Control Model

Proposed control ladder:

1. `observe`
2. `point`
3. `annotate`
4. `suggest`
5. `request_control`
6. `control_pointer`
7. `control_keyboard`
8. `execute_command`
9. `approve_change`

Control requirements:

- Control must be explicit.
- Control must be revocable.
- Control must be scoped to a surface.
- Control must be auditable.
- Control must not be inferred from observation.
- `request_control` is not the same as granted control.
- `approve_change` is not the same as general device control.

## Presence Event Vocabulary Proposal

The following names are candidate presence events only. They are not runtime tokens yet.

Any implementation must promote contract-bearing names into canonical token registries before use.

| Candidate event | Meaning |
|---|---|
| `presence.session.created` | A shared presence session was opened. |
| `presence.session.ended` | A shared presence session was closed. |
| `presence.participant.joined` | A participant joined the session. |
| `presence.participant.left` | A participant left the session. |
| `presence.participant.heartbeat` | A participant presence heartbeat was observed. |
| `presence.surface.opened` | A shared surface became available in the session. |
| `presence.surface.closed` | A shared surface was removed or closed. |
| `presence.cursor.moved` | A participant cursor moved on a shared surface. |
| `presence.selection.changed` | A selection changed on a shared surface. |
| `presence.annotation.created` | An annotation was created. |
| `presence.control.requested` | A control request was issued. |
| `presence.control.granted` | A control lease was granted. |
| `presence.control.revoked` | A control lease was revoked. |
| `presence.ai.observation.created` | An AI participant recorded an observation. |
| `presence.ai.suggestion.created` | An AI participant created a suggestion. |

## Provenance and Audit Expectations

- Presence events must be attributable.
- AI observations must identify participant, session, and surface.
- Control grants must leave receipts.
- Exported or restored state must not silently lose provenance if presence records later become durable.
- Ephemeral-only events must be labeled as ephemeral.
- Presence receipts should preserve enough context to reconstruct what was observed, who acted, and under which scope.

## AI Participant Rules

- AI participants may observe only within granted scope.
- AI participants may suggest without control.
- AI participants may not execute commands unless explicitly granted.
- AI participants may not silently mutate identity, memory, runtime law, or queue/worker semantics.
- Future coding-agent harnesses must remain Guardian-mediated.
- AI participants must not bypass Guardian policy, command authority, provenance, or export/restore obligations.

## Phase Plan

| Phase | What it proves | What it does not prove |
|---|---|---|
| Phase 0: docs-only contract and terminology | The product concept, boundary language, terms, and non-goals can be defined without implementation. | No runtime behavior, no transport, no control model, no release support. |
| Phase 1: shared desktop proof using VNC or equivalent pixel transport | A prototype can expose shared co-viewing on a desktop-like surface. | No semantic state sync, no canonical presence protocol, no product abstraction commitment. |
| Phase 2: presence event stream and observer roster | Presence events and participant visibility can be surfaced separately from shared pixels. | No general shared control, no semantic collaboration state, no native surfaces. |
| Phase 3: shared browser/editor/terminal surfaces | Specific shared surfaces can be supported beyond desktop pixel mirroring. | No native semantic protocol, no AI orchestration, no unsupported beta widening. |
| Phase 4: native Shared Presence Protocol with semantic state sync | A native protocol can carry semantic state and structured collaboration truth. | No claim that all participants can control everything, and no claim of automatic release support. |
| Phase 5: AI participant orchestration and governed control leases | AI participants can operate as visible, scoped participants with governed control. | No autonomous self-modification, no identity mutation, no Guardian bypass, no release claim without proof. |

## Open Questions

- Should presence sessions be project-bound, thread-bound, workspace-bound, or independent?
- Which events are durable versus ephemeral?
- What is the minimum safe control lease?
- How should control conflicts be resolved?
- How should AI participant observations be rendered without polluting chat?
- What proof is required before this becomes beta-supported?

## Invariants

- Presence must not equal identity.
- Observation must not imply control.
- Control must be explicit and revocable.
- Pixel sharing must not be treated as semantic state truth.
- Transport-specific behavior must not leak into canonical product language.
- Shared Presence must not widen the supported beta promise without proof.
- Event names and status strings must follow canonical token discipline before implementation.
- AI participants must not bypass Guardian policy, command authority, provenance, or export/restore obligations.

## Proof Surface for Future Implementation

Future implementation must include:

- backend seam tests for session creation and participant lifecycle
- permission tests for control grants and revocation
- event ordering tests
- reconnect/resume tests
- audit/provenance tests
- UI tests for participant roster and non-invasive presence display
- transport-specific manual proof for VNC/WebRTC if used
- explicit release-boundary update only after live proof

## Documentation Follow-through

- This document must be linked from `/docs/architecture/README.md`.
- A future ADR is required before implementation changes.
- Runtime diagrams must not include Shared Presence as current topology until implementation exists.
- UI diagrams must not include Shared Presence as current UI canon until a UI spec exists.
- This document is a proposal boundary, not a support claim.
