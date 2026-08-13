# Room-First Atlas V0.1 Interaction Contract

> Classification: architecture-impact implementation contract
>
> Status: V0.1 planning and implementation boundary; docs-only
>
> Release posture: this contract does not qualify Hosted Rooms, Atlas, or any collaboration path for the supported beta/release promise. `00-current-state.md` remains the short-horizon release authority.

## Purpose

This contract locks the smallest truthful product model for the first Room-first
Atlas proof. It reconciles the Atlas V0.1 campaign with the discovery audit and
prevents the UI from inventing a parallel Room, transcript, Workspace authority,
or network model before those semantics are accepted and implemented.

The V0.1 product stack is:

```text
Codexify Shell

Room Mode
├── Participants
├── One canonical Thread
├── Existing Guardian behavior where supported
└── Contextual Workspace
    └── resources derived from existing thread/project state

Atlas
└── viewer-relative navigation projection
    └── selects/navigates to Rooms
```

Atlas is not the first implementation dependency. Room Mode must be independently
useful when Atlas is unavailable.

## Source authority and scope

This contract is grounded in the 2026-08-12 discovery audit, current code/model
ownership, and the current chat, storage, portability, and UI contracts. When
sources conflict, authority is:

1. `00-current-state.md` for present release/support claims;
2. governing ADRs and explicit architecture contracts for accepted boundaries;
3. this constrained V0.1 implementation contract;
4. the discovery audit and current code/tests for implementation evidence;
5. broader ThreadSpace, future collaboration, and product-planning documents.

This document does not change runtime code, persistence, migrations, API shape,
authorization, release posture, or the accepted authority model. It also does
not equate the current `HostedRoom` implementation with the permanent form of a
broader future Room concept.

## Current-truth anchors

### True now

- `HostedRoom` is a durable, account-owned collaboration model with an existing
  participant, invitation, guest-session, authorization, and bounded
  host-resident Guardian invocation seam.
- A Hosted Room has exactly one `backing_thread_id` referring to a canonical
  `ChatThread`. The relationship is enforced by a non-null field and a unique
  constraint, not merely by convention.
- `ChatMessage` remains the canonical transcript store. There is no Room
  transcript table: Room messages are canonical message rows selected through
  the backing thread.
- `HostedRoom.id`, `ChatThread.id`, `ChatMessage.id`, participant IDs,
  invitation IDs, request IDs, task IDs, and turn IDs have distinct meanings.
  Participant provenance is structured message metadata and must not be
  flattened into canonical message ownership fields.
- Generic Guardian Chat, thread/sidebar, composer, Workspace drawer, Shelf,
  and Inspector/document/media presentation primitives exist and may be
  composed. No Hosted Room React client, RoomShell, Room participant UI,
  invitation flow, guest UI, Room composer, or Room navigation currently
  exists.
- Generic thread/project/document/media relationships can expose contextual
  resources. There is no current Room-scoped resource table, resource ACL,
  Room Workspace authority, or shared Room semantic KB.
- Existing federation seams exchange experimental manifests, relay sessions,
  document diffs, graph data, and context/search data. They are not canonical
  Room chat, cross-node Room posting, or Room authority protocol.
- The current release posture remains local-first beta hardening. Hosted Room
  behavior is outside the supported beta/release promise.

### Not yet true

- A Room containing multiple canonical threads.
- Room-owned Workspace state, shared resource persistence, resource ACLs, or a
  Room semantic KB.
- A personal Guardian binding for each participant, remote Guardian invocation,
  or participant-node intelligence routing.
- Cross-node Room posting, a Room Protocol, or a federation-backed Room chat
  protocol.
- HomeBase persistence or authority; Spaces; Galaxy; shared Room themes; or an
  Atlas runtime implementation.

### May be assumed by subsequent V0.1 tasks

- Existing Hosted Room is the V0.1 compatibility substrate.
- Existing canonical chat persistence and lifecycle behavior remain the
  conversation authority.
- Generic Workspace presentation can be composed around existing backing-thread
  and project resources without changing their authority.
- Atlas may project authorized Rooms and navigate to them without becoming their
  owner, identity, message, resource, or network authority.

## Canonical V0.1 product model

### Room V0.1

For V0.1, a user-facing Room is implemented through the existing Hosted Room
substrate. It is a persistent shared collaboration context around:

- participants;
- one canonical backing conversation thread;
- existing host-resident Guardian behavior where the current bounded seam
  supports it; and
- contextual resources derived from existing canonical thread/project
  relationships.

The compatibility relationship is:

```text
HostedRoom.id
  ├── participants, invitations, and guest-session authorization metadata
  └── backing_thread_id ──> ChatThread.id
                              └── ChatMessage.id (canonical transcript)
```

V0.1 rules:

- A Room contains exactly one canonical thread.
- A Room must not invent a second transcript, message store, completion
  pipeline, or canonical message identity.
- `HostedRoom.id` and `ChatThread.id` remain distinct identities and must not
  be collapsed into a generic route token without retaining their source
  meaning.
- Human and Guardian presentation must use canonical participant/message
  provenance and ordinary identity presentation such as name, avatar, or
  header context. It must not rewrite participant provenance into `user_id`,
  message role, or message ownership.
- The current Hosted Room implementation is the compatibility substrate, not a
  declaration that its schema is the permanent/final form of the broader Room
  concept.

### Future multi-thread Room

The intended direction is reserved, not implemented:

```text
Room
├── Thread
├── Thread
├── Thread
├── Participants
└── Shared Workspace
```

Changing from `HostedRoom -> one canonical ChatThread` to `Room -> many
canonical Threads` is a **future architecture/runtime extension**. It requires
a separate architecture-impact decision plus persistence, API, authorization,
runtime, portability, and proof work. Atlas V0.1 must not visually imply that
multi-thread behavior exists today.

## Room Mode

Room Mode is a contextual composition of existing Codexify interaction
primitives, not a separate chat application. A subsequent UI task may compose:

- the existing Guardian Chat message surface;
- the existing composer;
- existing thread/message lifecycle behavior;
- participant display and canonical provenance;
- existing Workspace presentation primitives; and
- existing Inspector/document/media presentation where applicable.

Room Mode must not create a parallel message renderer, second composer,
separate completion pipeline, or second transcript store. It must preserve the
normal distinctions between message identity, request/attempt identity,
participant provenance, and completion acceptance versus completion.

The current host-resident Guardian seam is an existing bounded behavior, not a
promise of personal Guardians for Room participants. Plain mention text remains
content; it must not be treated as an authorization mechanism.

## Room Workspace V0.1

Room Workspace is a presentation concept in V0.1, not a new storage or
authority model. It may surface resources already associated with:

- the canonical backing thread;
- the backing thread's project; and
- existing document, media, and artifact relationships exposed by current APIs.

This is a derived presentation of existing canonical state. It must not claim:

- Room ownership of those resources;
- Room-specific ACLs or persistence;
- Room-scoped semantic ingestion or a shared Room KB; or
- participant-shared scratchpad state.

The preferred V0.1 posture is a tactile resource-browser presentation rather
than a raw filesystem tree. Dense list/tree projections may be added later as
power-user views. Existing Scratchpad browser state remains device-local and
must not become shared state by implication.

Any future resource behavior that is independently Room-visible,
Room-authorized, participant-attributable, shared, or portable outside existing
thread/project relationships requires a separate architecture-impact contract.

## Atlas, HomeBase, and Spaces

### Atlas

Atlas is an optional alternate navigation mode. It answers **"Where can I go?"**
and does not answer **"Who owns this state?"**

The interaction is:

1. A user works normally in Codexify.
2. The user summons Atlas.
3. Atlas presents a viewer-relative map/projection.
4. The user selects a Room.
5. Atlas recedes.
6. Normal Codexify Room Mode becomes active.
7. Summoning Atlas again restores the map context.

Atlas must project existing authorized resources, preserve canonical
Room/thread identities, navigate to normal working surfaces, and remain
optional. It must not become a second application shell or an authority over
Rooms, identity, messages, resources, or networking.

### HomeBase

HomeBase is a viewer-relative Atlas projection root in V0.1. It is not a new
backend entity, persistence record, or authority boundary. It may organize the
current viewer's Room destinations, but it must be visibly treated as derived
presentation rather than shipped runtime state.

### Spaces

Spaces are reserved for future work. V0.1 does not implement Space persistence,
membership, routes, dormant runtime code, or a requirement that a user enter a
Space to reach a Room.

The current directional vocabulary is an optional organizational/governance
layer over Rooms, analogous in abstraction to how Projects organize existing
work:

```text
HomeBase
└── optional Space
    └── Room
        └── Threads
```

This contract does not define or redefine Space as an interactive application
or site. That richer concept remains unresolved and may require a separate
name and decision.

## Product-order doctrine

**Productive first, fun second.** The V0.1 order is:

1. Establish this architecture contract.
2. Expose the existing Hosted Room substrate through a native Codexify Room
   Mode.
3. Prove one real multi-user Room path at the current repository tip.
4. Add Atlas as an alternate navigation surface over real Room destinations.
5. Qualify touch, keyboard, responsive behavior, state restoration, and
   interaction polish.

Atlas must not be required for Room usefulness. A useful Room is the product
dependency; Atlas is a later optional navigation projection over that real
surface.

## Future Room presentation direction

Future Room shared presentation may include bounded metadata such as wallpaper,
accent/theme preset, surface treatment, and approved ambient or motion preset,
so a Room can feel like a shared place.

This is deferred as **`Room shared presentation / themes - V0.2 candidate`**.
Any future implementation must resolve through local Codexify tokens and
components, preserve accessibility and readable contrast, honor reduced-motion
preferences, and forbid arbitrary remote CSS, HTML, or script injection.

## Invariants

1. One current Hosted Room has one canonical backing `ChatThread`.
2. `ChatMessage` remains canonical transcript storage.
3. No duplicate Room transcript exists in V0.1.
4. Atlas owns no Room state.
5. Atlas owns no message state.
6. V0.1 adds no new Room persistence.
7. Existing participant provenance is not message ownership.
8. Existing authorization boundaries remain authoritative.
9. Network reachability never implies Room authorization.
10. Generic thread/project resources must not be relabeled Room-owned without
    a new contract.
11. HomeBase is projection-only in V0.1.
12. Spaces remain optional and future.
13. Atlas remains optional navigation.
14. Room Mode reuses the existing chat interaction system.
15. Supported-release claims remain governed by `00-current-state.md`.
16. Future multi-thread Room behavior requires a separate architecture-impact
    task.
17. Future cross-node behavior must preserve local/remote semantic parity
    without conflating transport, identity, membership, or capability proof.

## Explicit V0.1 non-goals

The following are deferred:

- multi-thread Room persistence and new Room/thread association tables;
- Room-owned shared resource persistence, resource ACLs, and semantic KB;
- personal Guardian-per-participant binding and remote Guardian invocation;
- cross-node Room posting and a Room Protocol implementation;
- Tailscale/LAN/relay transport integration and federation changes;
- Spaces, Galaxy, discovery/recommendation, and edge-event annotations;
- shared Room wallpapers/themes;
- new social feed/post primitives; and
- release qualification of Hosted Rooms.

## Proof obligations for later V0.1 tasks

This task proves only a documentation boundary. It does not prove a runtime
path. A first Room Mode implementation/proof task must separately establish,
at its exact repository tip:

- that the selected supported/test profile registers the required Room routes;
- authenticated owner and invited guest access with lifecycle/revocation
  behavior;
- one canonical backing thread and transcript read/write behavior;
- participant/Guardian provenance without identity flattening;
- normal completion acceptance, execution, persistence, and durable readback;
- native Room UI behavior and generic Workspace derivation without an authority
  expansion; and
- the remaining release posture after evidence is collected.

No passing focused test, prior proof packet, route registration, or UI shell
alone qualifies Hosted Rooms for release.

## ADR impact

**Classification:** Aligned with existing ADR(s); no new ADR is required for
this docs-only compatibility contract.

**Governing ADRs and contracts:**

- `ADR-053: Node-Hosted Room Access Boundary` is the current governing
  Room-access/authority decision. Its status is proposed and it does not by
  itself authorize a release claim, federation, or a change to single-thread
  Hosted Room semantics.
- `ADR-003: Message Identity vs Request Identity` governs the separation of
  canonical message and request/attempt identities used by Room Mode.
- `ADR-055: ThreadSpace ↔ WhisperMesh Managed-Service Boundary` remains a
  proposed future boundary; it confirms that transport/service reachability is
  not Room authority and does not implement cross-node Rooms.
- The Hosted Room discovery audit, chat runtime contract, data/storage
  contract, account export/restore contract, and collaboration identity
  contracts constrain the V0.1 compatibility interpretation.

This contract preserves, rather than changes, the current single-thread Hosted
Room authority model. A proposal to redefine that authority model, introduce a
many-thread Room, or make Room resources independently authoritative requires a
new architecture-impact decision before implementation.

## Documentation follow-through

`README.md` indexes this contract in the Architecture KB Doc Map. No ADR,
current-state document, ThreadSpace blueprint, discovery audit, runtime diagram,
or UI diagram is changed by this docs-only task.
