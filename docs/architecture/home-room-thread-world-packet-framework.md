# Codexify HomeBase, Space, Room, Thread, and World Packet Framework

**Classification:** Architecture-impacting product and production integration framework  
**Status:** Proposed living framework, documentation only  
**Runtime claim:** This document does not claim that first-class HomeBases, Spaces, Rooms, visitor joins, collaborator presence, World Packet synchronization, selective Project disclosure, Atlas federation, or Codexify.Space discovery are implemented.  
**Design lineage:** Zac originated the Home / Room / Chat / World Spine interaction model and the spatial prototype that revealed this product shape. Production integration must preserve the useful interaction behavior and record where implementation necessarily diverges from the prototype.

## 1. Canonical hierarchy

Codexify should translate the prototype through this hierarchy:

```text
User or Organization
└── HomeBase
    └── Spaces
        └── Rooms
            └── Threads
                └── Messages
```

The layers are intentionally different:

- **HomeBase** is the sovereign ownership and administration root.
- **Space** is the website-like interactive experience a visitor enters.
- **Room** is a bounded shared context inside a Space.
- **Thread** is a durable multi-participant conversation inside a Room.
- **Message** is a durable authored turn inside a Thread.

Zac commonly calls a Thread a **Chat**. Codexify should preserve that product language in the interface while retaining `chat_threads` and `chat_messages` as the existing backend conversation model.

## 2. Executive decisions

1. A User or Organization owns one HomeBase identity boundary.
2. A HomeBase may be served by one or more Nodes.
3. A HomeBase may publish many Spaces.
4. A Space is an interactive application or website-like experience, not merely a folder.
5. A Space may contain many Rooms.
6. A Room may contain many Threads.
7. A Thread may contain many simultaneous participants.
8. A Room is initially a host-governed projection of selected Project state.
9. The Project remains the authoritative backend work container during the first production phases.
10. JSONL is an approved synchronization transport and projection format, not the durable database authority.
11. Atlas renders reduced packet state. Atlas does not own canonical state.
12. Codexify.Space may coordinate discovery, rendezvous, relay, and public projection without becoming private HomeBase authority.

## 3. Current-truth boundary

Before implementation, read:

1. `docs/architecture/00-current-state.md`
2. `docs/architecture/README.md`
3. `docs/architecture/adr/ADR Index.md`
4. `docs/architecture/system-overview.md`
5. `docs/architecture/data-and-storage.md`
6. `docs/architecture/flows.md`
7. `docs/architecture/modules-and-ownership.md`
8. `docs/architecture/account-export-restore-contract.md`
9. `docs/architecture/canonical-token-philosophy.md`
10. `docs/architecture/runtime-protocol-token-contract.md`

Current truth:

- The supported runtime path remains local Docker Compose.
- Postgres is the durable application system of record.
- Redis owns queues, locks, task-event transport, cancellation, and worker heartbeat, not durable Room history.
- Projects currently organize Threads and resources.
- Threads and Messages remain the durable conversation model.
- Documents, artifacts, retrieval indexes, audit records, and outbox events already exist.
- Hosted Spaces, Room synchronization, remote mounting, general participant-node attachment, and federation are not part of the supported release promise.

Not yet true:

- HomeBase is not yet a first-class runtime entity.
- Space is not yet a first-class runtime entity.
- Room is not yet a first-class runtime entity.
- Projects do not yet publish governed Room projections.
- A World Packet is not yet a supported synchronization contract.
- Joining a Room does not yet hydrate a client from a transport packet.
- Room rules and moderator notices are not yet enforced through a canonical join protocol.
- Atlas does not yet render live remote topology from canonical World Packets.
- Codexify.Space is not authority for private HomeBase or Project state.

## 4. Canonical vocabulary

### HomeBase

A HomeBase is the sovereign identity, ownership, administration, and publication root for one User or Organization.

A HomeBase may coordinate:

- profile and identity state;
- private Vault material;
- Projects;
- hosted Spaces;
- attached Nodes;
- assistants and agents;
- publication policy;
- synchronization policy;
- invitations and trust relationships;
- activity, receipts, and audit evidence.

A HomeBase is not one physical computer. Multiple authorized Nodes may serve the same HomeBase, but one Node must not silently impersonate another authority.

### Space

A Space is a host-defined interactive experience published by a HomeBase.

A Space may behave like:

- a website;
- community portal;
- documentation system;
- marketplace;
- research environment;
- developer portal;
- game or simulation;
- business dashboard;
- Atlas explorer;
- public pavilion.

The Space owns the experience shell, navigation, visual grammar, Room directory, discovery posture, and Space-wide policies. Different Spaces may render the same underlying protocol through entirely different interfaces.

A Space is not a Project. A Project may supply authoritative data to one or more Rooms inside a Space.

### Project

A Project is the authoritative backend work context during the first production phases. The existing `projects` model remains responsible for durable organization and ownership of Project-bound Threads, documents, artifacts, and retrieval context.

A Project is private unless an explicit disclosure policy creates a Room projection or another sharing surface.

### Room

A Room is a bounded, host-governed shared context inside a Space. It is initially a projection of one Project.

A Room may contain:

- multiple Threads;
- shared context;
- participant roster;
- Visitor and Collaborator policy;
- Room-visible files and artifacts;
- selected Knowledge Base material;
- selected Code Base references;
- activity and receipt streams;
- moderator notices and rules;
- optional presence;
- optional public projection state.

A Room must not silently expose the whole Project.

### Thread / Chat

A Thread is the durable backend conversation container. A Chat is the user-facing term for participating in a Thread.

```text
Room
├── Thread: Main discussion
├── Thread: Architecture review
├── Thread: Design decisions
└── Thread: Agent work log
```

Multiple authorized people, assistants, and agents may participate in the same Thread. Existing queue, worker, completion, transcript, message-versus-attempt, and retrieval semantics remain attached to Threads and Messages.

### Node

A Node is a compute and hosting participant capable of serving some authorized portion of a HomeBase, Space, or Room experience.

A Node may be:

- a personal computer;
- home server;
- trusted collaborator machine;
- dedicated business server;
- community relay;
- hosted infrastructure instance.

A Node is not automatically a HomeBase and does not own identity merely because it executes workloads.

### World Packet

A World Packet is a bounded synchronization and entry transport artifact. It carries the minimum authorized state and event information needed for a client to render or refresh a Space or Room projection.

A World Packet is conceptually:

```text
Snapshot
+ Event Cursor
+ Event Segment
+ Integrity Metadata
+ Capability and Policy Envelope
```

JSONL is the initial approved event serialization because it is append-oriented, inspectable, streamable, segmentable, and friendly to offline exchange.

### World Spine

The World Spine is the durable event identity, lineage, replay, and reduction contract from which World Packets may be produced.

Production does not define the World Spine as one permanently growing `world.jsonl` authority. Postgres-backed domain and outbox records remain authoritative. JSONL is transport, replay, export, debugging, and offline-exchange material.

### Atlas

Atlas is a navigable renderer over reduced current state.

Atlas may present:

- local HomeBase topology;
- Spaces and Rooms;
- Threads and participants;
- Nodes and trust relationships;
- public businesses and communities;
- search results;
- articles and bookmarks;
- nearby or relevant services;
- joinable remote experiences;
- federation clusters and digital villages.

Atlas is not canonical state and must not be the only usable interface.

## 5. Room as a Project projection

```text
Authoritative Project
├── Threads
├── Messages
├── Documents
├── Generated artifacts
├── Project-linked knowledge
├── Repository references
├── Activity and receipts
└── Private Project state
        |
        | Host disclosure policy
        v
Room Projection
├── selected Threads
├── selected documents and artifacts
├── selected knowledge scope
├── selected repository references
├── selected activity and receipts
├── participant roster
├── visitor/collaborator capabilities
├── Room rules and moderator notice
└── public projection eligibility
```

The Host controls which Project streams become Room-visible. Deleting a Room must not delete the Project. Hiding a Thread or document from a Room must not delete its canonical record. Room-originated Project mutations must pass through explicit Project-domain commands and capability checks.

## 6. Space runtime relationship

A Space is the experience container around one or more Rooms.

```text
HomeBase
└── Space: Developer Portal
    ├── Space manifest
    ├── Navigation and experience shell
    ├── Space-wide policy
    ├── Room directory
    ├── Room: Architecture
    │   ├── Threads
    │   ├── files
    │   └── shared context
    └── Room: Releases
        ├── Threads
        ├── artifacts
        └── receipts
```

The Space manifest may declare:

- Space identity and Host authority;
- experience type and renderer compatibility;
- public, invite-only, or private posture;
- Room directory policy;
- visual shell and navigation hints;
- supported capabilities;
- content resolution rules;
- discovery metadata;
- synchronization endpoints;
- integrity and version metadata.

The manifest must not grant authority. Effective capabilities come from authenticated policy evaluation.

## 7. Participant capability separation

Friendly role labels are presentation. Capability grants are authority.

Capabilities should be evaluated separately for actions such as:

- discover Space;
- enter Space;
- list Rooms;
- enter Room;
- read Room metadata;
- list Threads;
- read or post to a Thread;
- create a Thread;
- read or attach files;
- edit shared material;
- consume Room Knowledge Base context;
- invoke tools;
- invite participants;
- change rules or disclosure policy;
- publish material;
- transact;
- administer or close the Room or Space.

Membership does not grant ambient access to the Project, HomeBase, Node, filesystem, private memory, credentials, or unrelated Knowledge Bases.

## 8. Join and synchronization protocol

A client may request entry through an invite, shared link, discovery record, direct Space or Room reference, or mounted remote identity.

```text
Client resolves Space or Room reference
  -> Host authenticates or classifies participant
  -> Host evaluates admission policy
  -> Host resolves capabilities
  -> Host selects authorized streams
  -> Host produces Entry Manifest
  -> Host produces scoped World Packet
  -> Client validates authority, schema, event IDs, and integrity
  -> Client reduces packet into local projection
  -> UI presents rules and moderator notice
  -> Participant acknowledges when required
  -> Client opens the allowed experience
  -> Incremental event delivery begins at packet cursor
```

The Entry Manifest should identify:

- HomeBase, Space, Room, and Host authority;
- participant class and effective capabilities;
- disclosed streams;
- packet schema and projection version;
- snapshot timestamp and event cursor;
- rules version and moderator notice;
- acknowledgement requirements;
- privacy summary;
- content resolution policy;
- integrity metadata;
- resynchronization method.

Join and sync fail closed when authority is uncertain. Unsupported schema, integrity mismatch, missing mandatory rules, revoked access, or event gaps must block or quarantine rather than guess. When the Host is offline, a client may retain the last valid projection but must label it stale.

## 9. JSONL transport and Atlas reduction

The initial rendering path is:

```text
Canonical Postgres mutation
  -> transactional outbox event
  -> normalized World Spine event
  -> scoped JSONL packet segment
  -> authenticated client ingest
  -> idempotent reducer
  -> local reduced projection
  -> Atlas or Space-specific renderer
```

The Room State viewed by a client must be refreshed through bounded snapshots and incremental event segments. A renderer must not scrape arbitrary Host files or treat a mutable shared JSONL file as a transactional database.

Every transport event requires:

- stable event identity;
- schema version;
- HomeBase, Space, and Room scope where applicable;
- actor and authority references;
- causation and correlation identity;
- idempotency semantics;
- payload or content reference;
- integrity metadata;
- cursor or ordering information;
- observable apply, reject, quarantine, and repair state.

## 10. Atlas projection families

Atlas should support at least two projection families.

### Local Atlas

Shows the user's immediate topology:

- HomeBase;
- attached Nodes;
- hosted Spaces;
- Rooms and Threads;
- trusted peers;
- private and public projection boundaries;
- current activity and health.

### Federated Atlas

Shows discoverable network topology:

- remote HomeBases;
- businesses and organizations;
- public Spaces;
- community clusters;
- digital villages;
- joinable Rooms;
- trusted or nearby Nodes;
- search results, articles, bookmarks, services, and offers;
- relationship, trust, availability, and policy posture.

A card in Federated Atlas represents a remote authority or projection, not merely a visual object. Selecting it may reveal more Spaces, Rooms, public resources, or an authenticated join path.

## 11. Federation model

Each HomeBase may host its own Spaces on its own authorized Nodes. Groups of HomeBases may form federations or digital villages by agreeing on discovery, trust, relay, moderation, and synchronization rules.

Larger businesses use the same protocol family as individuals. Their differences are scale, policy, availability, and service commitments, not a separate sovereignty model.

Codexify.Space may provide optional:

- discovery and directory services;
- rendezvous and invitation exchange;
- relay and NAT traversal assistance;
- public metadata indexing;
- trust bootstrap and reputation signals;
- protocol capability negotiation;
- public projection hosting.

Codexify.Space must not become required private-state authority.

## 12. Commerce and transactions

The protocol may later support shopping, bookings, subscriptions, service requests, or other transactions inside Spaces. This is vision, not current implementation.

Any transaction layer must preserve:

- explicit seller and buyer authority;
- auditable offers and acceptance;
- capability checks;
- price and policy versioning;
- receipts and dispute evidence;
- clear external payment-provider boundaries;
- no ambient financial authority granted by Room membership.

Commerce must be introduced as a separate architecture-impacting contract and proof surface.

## 13. Core invariants

1. A User or Organization owns one HomeBase identity boundary.
2. A HomeBase may publish many Spaces.
3. A Space may contain many Rooms.
4. A Room may contain many Threads.
5. A Thread may contain many participants.
6. A Space is not a Room.
7. A Room is not a Thread.
8. A Room is initially a governed projection of one authoritative Project.
9. A Room exposes only explicitly selected data streams.
10. Postgres remains authoritative during compatibility and first production phases.
11. Redis operational state must not be synchronized as Room content.
12. JSONL is transport and projection, not competing writable authority.
13. Atlas is a renderer, not canonical storage.
14. No phase may silently dual-write Postgres, JSONL, and Markdown.
15. Eligible events must originate through an explicit transactional or outbox-backed boundary.
16. Every applied event requires stable identity, idempotency, scope, provenance, and observable failure state.
17. A joining client receives only the World Packet authorized for that participant and scope.
18. Room and Space rules must be visible before or at entry.
19. A moderator notice is part of the entry contract, not decorative copy.
20. Export and restore preserve Project, Space, Room, Thread, artifact, participant, publication, and event lineage.
21. Repeated contract-bearing values use canonical token registries.
22. Codexify.Space federation remains optional.
23. This document and the prototype do not widen the supported release promise.

## 14. Phased delivery

### Phase 0: doctrine and ADR closure

- establish canonical HomeBase, Space, Room, Thread, World Packet, and Atlas vocabulary;
- record design lineage and translation decisions;
- create the governing ADR before runtime work;
- close identity, authority, and deletion semantics.

### Phase 1: local read-only compatibility projection

- project one existing Project into one local Room;
- place the Room inside one local Space shell;
- expose a selected Thread and document set;
- render the reduced state in Atlas and a flat accessible view;
- prove rebuild without adding federation.

### Phase 2: first-class local hierarchy

- add only the new durable truth required for HomeBase, Space, Room, and bindings;
- preserve existing Project, Thread, and Message authority;
- add policy, membership, and disclosure records;
- add Room and Space lifecycle receipts.

### Phase 3: World Packet harness

- define canonical event envelope and JSONL serialization;
- implement snapshot plus cursor generation;
- implement idempotent reducer and repair tooling;
- expose lag, gap, reject, quarantine, and replay status.

### Phase 4: local hosted collaboration

- enforce participant capabilities;
- implement rules and moderator notice acknowledgement;
- support multiple participants in a Thread;
- prove selective Project disclosure.

### Phase 5: two-node proof

- synchronize one Room between two authorized Nodes;
- prove disconnect, stale labeling, reconnect, replay, revocation, and recovery;
- preserve Host authority and participant-owned private context.

### Phase 6: Space runtime extensibility

- define renderer and manifest compatibility;
- support at least two distinct Space experiences over the same protocol;
- prove Atlas is one renderer among several.

### Phase 7: federation discovery

- publish bounded discovery records;
- render remote authorities in Federated Atlas;
- support explicit remote Space entry;
- keep private state local to its authority.

### Phase 8: digital villages and business Nodes

- define federation membership and moderation;
- support dedicated organization Nodes;
- add relay and availability postures;
- defer commerce to its own approved contract.

## 15. ADR impact

**Classification:** Requires new ADR before runtime implementation.

The ADR must govern:

- the canonical hierarchy;
- HomeBase identity and Node hosting boundaries;
- Space versus Room semantics;
- Project-to-Room projection authority;
- World Packet and JSONL transport doctrine;
- Atlas renderer boundaries;
- federation and Codexify.Space authority limits;
- migration and coexistence with current Projects and Threads.

## 16. Design review and receipts

Zac remains an originating architect and design peer for this model. Production changes must maintain a translation ledger with:

| Concept | Origin | Preserved behavior | Production translation | Changed behavior | Reason | Status | Zac feedback | Evidence |
|---|---|---|---|---|---|---|---|---|

Each phase should produce a review receipt containing:

- review ID;
- phase ID;
- source-spec version;
- concepts reviewed;
- preserved and changed behaviors;
- production reasons;
- open questions;
- reviewer identity;
- review status;
- feedback and resolution references;
- timestamp.

Safety, privacy, transactional integrity, migration, accessibility, and current runtime truth remain binding even when a prototype behavior must change.

## 17. Documentation follow-through

Runtime implementation must update or explicitly defer:

- `docs/architecture/00-current-state.md`;
- `docs/architecture/README.md`;
- the ADR index and governing ADR;
- `docs/architecture/system-overview.md`;
- `docs/architecture/data-and-storage.md`;
- `docs/architecture/flows.md`;
- `docs/architecture/modules-and-ownership.md`;
- runtime and UI diagrams;
- export and restore contracts;
- canonical token registries;
- operator and security documentation.

This framework is the collaboration and synchronization substrate for the broader Codexify.Space v2 architecture volume.