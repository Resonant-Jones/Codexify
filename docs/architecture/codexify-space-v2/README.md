# Codexify.Space v2 Architecture Volume

**Status:** Proposed architecture volume, documentation only  
**Purpose:** Provide one canonical entrypoint for the HomeBase, Space, Room, Thread, World Packet, Atlas, and federation model.

## Canonical hierarchy

```text
User or Organization
└── HomeBase
    └── Spaces
        └── Rooms
            └── Threads
                └── Messages
```

## Read order

1. [`../00-current-state.md`](../00-current-state.md) for current release truth.
2. [`../home-room-thread-world-packet-framework.md`](../home-room-thread-world-packet-framework.md) for the collaboration, Project-projection, synchronization, and participant substrate.
3. [`../space-runtime-and-federated-experience-architecture.md`](../space-runtime-and-federated-experience-architecture.md) for the interactive Space runtime, Atlas rendering model, discovery, digital villages, and federation vision.
4. [`open-decisions.md`](./open-decisions.md) for unresolved architecture questions and the required closure path.

## Architecture layers

### HomeBase

The sovereign identity, ownership, administration, publication, and policy root for one User or Organization.

### Space

The website-like interactive application published by a HomeBase. A Space controls experience shell, navigation, Room discovery, and Space-wide policy.

### Room

A bounded shared context inside a Space. During the first production phases, a Room is a governed projection of selected Project state.

### Thread

A durable multi-participant conversation inside a Room. The UI may continue to call this a Chat.

### World Packet

A bounded snapshot, cursor, event segment, policy envelope, and integrity bundle used to hydrate or refresh a Space or Room projection. JSONL is the initial event serialization.

### Atlas

A renderer over reduced topology and content state. Atlas may provide local and federated views, but it is never canonical storage.

### Codexify.Space

An optional discovery, rendezvous, relay, protocol-negotiation, and public-projection layer. It must not become required private-state authority.

## Current-truth anchors

- Postgres remains the durable application system of record.
- Redis remains operational infrastructure for queues, locks, task events, cancellation, and heartbeat.
- Existing Projects, Threads, Messages, documents, artifacts, retrieval, and outbox records remain the current implementation substrate.
- HomeBase, Space, Room, World Packet synchronization, remote mounting, and federation are proposed architecture, not implemented release truth.
- No document in this volume widens the supported beta promise.

## Program sequence

```text
Doctrine and ADR closure
  -> local read-only Project-to-Room projection
  -> first-class local hierarchy
  -> World Packet harness and reducer
  -> hosted collaboration
  -> two-node Room proof
  -> multiple Space renderers
  -> bounded federation discovery
  -> voluntary digital villages
  -> organization-grade hosting
```

Commerce, payments, and transaction protocols remain a separate future architecture program.

## Governing invariants

1. HomeBase owns authority.
2. Space owns the interactive experience.
3. Room owns bounded shared context.
4. Thread owns durable conversation.
5. Projects remain authoritative for first-phase Room-backed work state.
6. Nodes host execution without silently acquiring identity ownership.
7. JSONL transports scoped events without replacing Postgres.
8. Atlas renders projections without becoming truth.
9. Federation remains optional.
10. Public discovery never implies write or execution authority.
11. Spatial interfaces require accessible flat equivalents.
12. Zac's originating design contributions and later production translations remain visible through a design-lineage ledger and review receipts.

## ADR impact

This volume requires a new governing ADR before runtime implementation. The ADR must establish the canonical hierarchy, authority boundaries, Project-to-Room projection doctrine, packet and reducer contract, Atlas renderer boundary, Node hosting rules, and Codexify.Space federation limits.

## Change discipline

Any implementation task derived from this volume must:

- use the architecture-impact workflow;
- name the exact current-truth assumptions;
- preserve the invariants above;
- identify its proof surface;
- update or explicitly defer documentation follow-through;
- avoid combining local hierarchy, synchronization, federation, and commerce into one task.
