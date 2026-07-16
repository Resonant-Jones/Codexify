# Codexify Home, Room, Thread, and World Packet Framework

**Classification:** Architecture-impacting product and production integration framework  
**Status:** Proposed living framework, documentation only  
**Runtime claim:** This document does not claim that Rooms, visitor joins, collaborator presence, World Packet synchronization, selective Project disclosure, Atlas navigation, Public Pavilion publication, or Codexify.Space federation are implemented.  
**Design lineage:** Zac originated the Home / Room / Chat / World Spine interaction model and the spatial prototype that revealed this product shape. Production integration must preserve the useful interaction behavior and record where implementation necessarily diverges from the prototype.

## 1. Executive decision

Codexify should translate the prototype through this hierarchy:

```text
User
└── Home
    └── Rooms
        └── Threads
```

Zac commonly calls a Thread a **Chat**. Codexify should preserve that product language in the interface while retaining `chat_threads` and `chat_messages` as the existing backend conversation model.

The central translation is:

> A Room is a host-governed shared context projected from a Project and composed from selectively disclosed Project data streams.

The Project remains the authoritative backend work container during the first production phases. The Room is the collaboration, navigation, and disclosure projection presented to visitors and collaborators.

A Room may contain multiple Threads. It is not a renamed Thread.

A Room may expose selected Threads, documents, artifacts, Knowledge Base material, repository references, activity, receipts, participant state, Room rules, collaboration policy, and optional public projections. The Host decides what the Room discloses, who may enter, and which actions each participant may perform.

## 2. Why this fits Codexify

Codexify already has a durable Project, Thread, Message, document, retrieval, audit, and event substrate. Production integration should extend those systems rather than create a parallel filesystem application.

```text
Home         -> account-owned sovereign navigation root
Project      -> authoritative backend work context
Room         -> governed projection of selected Project state
Thread       -> durable conversation inside the Room
Message      -> durable authored turn inside the Thread
World Packet -> scoped synchronization and Room-entry transport
Atlas        -> navigable projection of reduced current state
```

The prototype proves that these relationships can be presented as a place people enter and inhabit. It does not prove that its storage mechanics are safe production authority.

## 3. Current-truth boundary

Before implementation, read:

1. `docs/architecture/00-current-state.md`
2. `docs/architecture/README.md`
3. `docs/architecture/adr/adr-index.md`
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
- Hosted Rooms, participant-node attachment, general Room synchronization, and federation are not part of the supported release promise.

Not yet true:

- A Room is not yet a first-class runtime entity.
- Projects do not yet publish governed Room projections.
- A World Packet is not yet a supported synchronization contract.
- Joining a Room does not yet hydrate a client from a transport packet.
- Room rules and moderator notices are not yet enforced through a canonical join protocol.
- Codexify.Space is not authority for private Home or Project state.

## 4. Canonical vocabulary

### Home

A Home is the User's sovereign root and navigation boundary. A Home may coordinate profile state, private memory, assistants, tools, attached Nodes, Projects, hosted Rooms, Vault material, public projections, activity, and receipts.

A Home may contain many Rooms. A Home is not one physical computer. Several Nodes may serve the same Home.

### Project

A Project is the authoritative backend work context during the first production phases. The existing `projects` model remains responsible for durable organization and ownership of Project-bound Threads, documents, and context.

A Project is private unless an explicit disclosure policy creates a Room projection or another sharing surface.

### Room

A Room is a bounded, host-governed shared context and is initially a projection of one Project.

The Room owns the meeting and coordination surface. The Project remains the first authoritative backend for the work being projected.

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

Existing queue, worker, completion, transcript, message-versus-attempt, and retrieval semantics remain attached to Threads and Messages.

### Participant

A Participant is a contextual actor inside a Room. A Participant may be a Host, Collaborator, Visitor, Observer, Guest, Assistant, agent, or authorized Node actor. A Participant record is not automatically equivalent to a canonical User or trusted Node.

### Host

The Host is the Home or authorized operator that publishes and governs the Room projection. The Host selects the backing Project, disclosed streams, participant policy, rules, moderator notice, publication posture, and effective capability envelope.

### World Packet

A World Packet is a bounded synchronization and Room-entry transport artifact. It carries the minimum state and event information needed for an authorized client to enter or refresh a Room projection.

It is not the Host database, private Vault, whole Project archive, Redis state, or unrestricted event history.

### World Spine

The World Spine is the durable event identity, lineage, replay, and reduction contract from which World Packets may be produced.

Production does not define the World Spine as one permanently growing `world.jsonl` authority. Postgres-backed domain and outbox records remain authoritative. JSONL is a transport, replay, export, debugging, and offline-exchange format.

### Atlas

Atlas is a navigable projection over current reduced state. It may present Homes, Rooms, Threads, participants, files, Nodes, activity, and public projections spatially. Atlas is not canonical state and must not be the only usable interface.

### Space

`Space` is not required as a mandatory hierarchy level for the first implementation. It may later become a grouping of Rooms, community boundary, discovery namespace, or federation domain. No task should insert it between Home and Room until the simpler model is proven insufficient and the design change is reviewed with Zac.

## 5. Core invariants

1. A Home may contain many Rooms.
2. A Room may contain many Threads.
3. A Room is not a Thread.
4. A Room is initially a governed projection of one authoritative Project.
5. A Room identifies its backing Project and Host authority.
6. A Room exposes only explicitly selected data streams.
7. Project-private material remains private unless selected by disclosure policy.
8. Membership does not grant ambient access to the Project, Home, Node, filesystem, private memory, or unrelated Knowledge Bases.
9. Visitor, Collaborator, Observer, Assistant, publication, editing, execution, and administration rights remain separate capabilities.
10. Postgres remains authoritative during compatibility and first production phases.
11. Redis operational state must not be synchronized as Room content.
12. JSONL begins as transport and projection, not competing writable authority.
13. No phase may silently dual-write Postgres, JSONL, and Markdown.
14. Eligible Room events must originate through an explicit transactional or outbox-backed boundary.
15. Every applied transport event requires stable identity, idempotency, scope, provenance, and observable failure state.
16. A joining client receives only the World Packet authorized for that participant and Room.
17. Room rules must be visible before or at entry.
18. A moderator notice is part of the Room-entry contract, not decorative copy.
19. Atlas and Room files remain rebuildable projections.
20. Export and restore preserve Project, Room, Thread, artifact, participant, publication, and event lineage.
21. Repeated contract-bearing values use canonical token registries.
22. This document and the prototype do not widen the release promise.

## 6. Room as a Project projection

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

Candidate disclosed stream families include Room metadata, Thread index, Thread messages, document metadata/content, artifact metadata/content, knowledge references, Code Base references, activity events, receipts, participant roster, presence, and publication state.

These are candidate concepts only. Runtime values require canonical token review.

Each Room projection should declare:

- Room ID;
- Host authority reference;
- backing Project ID;
- projection version;
- selected stream families;
- participant policy;
- Visitor and Collaborator admission posture;
- rules and moderator-notice versions;
- retention posture;
- publication posture;
- World Packet schema version;
- canonical event cursor or watermark.

Deleting a Room must not delete the Project. Hiding a Thread or document from a Room must not delete its canonical record. Room-originated Project mutations must pass through explicit Project-domain commands and capability checks.

## 7. Participant capability separation

Initial presentation classes may include Host, Collaborator, Visitor, Observer, Assistant, and Suspended. These labels are not sufficient authority by themselves.

Capabilities should be evaluated separately for actions such as:

- enter Room;
- read metadata;
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
- administer or close the Room.

A friendly role label is presentation. Capability grants are authority.

## 8. Room join and World Packet protocol

A client may request entry through an invite, shared link, discovery record, direct Room reference, or mounted Room identity.

The join flow distinguishes discovery, invitation, authentication, admission, synchronization, rule acknowledgement, and active participation.

```text
Client resolves Room reference
  -> Host authenticates or classifies participant
  -> Host evaluates admission policy
  -> Host resolves capabilities
  -> Host selects authorized streams
  -> Host produces Room Entry Manifest
  -> Host produces scoped World Packet
  -> Client validates identity, schema, event IDs, and integrity
  -> Client reduces packet into local Room projection
  -> UI presents rules / moderator notice
  -> Participant acknowledges when required
  -> Client opens the Room in the allowed posture
  -> Incremental event delivery begins at packet cursor
```

The Room Entry Manifest should identify Room and Host, participant class, effective capabilities, disclosed streams, packet schema, projection version, snapshot timestamp, event cursor, rules version, moderator notice, acknowledgement requirements, privacy summary, content resolution policy, integrity metadata, and resynchronization method.

A World Packet may contain a bounded Room snapshot, Thread index, selected transcript windows or message events, selected file and artifact metadata, authored content or references, participant roster appropriate to the viewer, rules, activity events, receipts, provenance, publication metadata, and an incremental cursor.

It must not contain unrelated Project data, Home-private memory, participant-private context, undisclosed files, credentials, Redis state, hidden prompts, unrestricted audit logs, or capability data outside the viewer's effective scope.

A joining client normally needs both a bounded snapshot and an event cursor:

```text
Room Entry Manifest
+ bounded snapshot
+ world.jsonl event segment
+ content references or bounded payloads
+ integrity metadata
```

The exact container remains open. The semantic contract matters more than the filename.

Join and sync fail closed when authority is uncertain. Unsupported schema, integrity mismatch, missing mandatory rules, revoked access, or event gaps must block or quarantine rather than guess. When the Host is offline, the client may retain the last valid projection but must label it stale.

## 9. Room rules and moderator notice

Room entry should present a concise notice containing:

- Room purpose;
- Host identity;
- participant posture;
- data shared into the Room;
- data remaining private;
- allowed and prohibited actions;
- retention or recording posture;
- publication posture;
- tool or agent restrictions;
- escalation path;
- rules version and effective date.

The notice may be informational, acknowledgement-required, or require re-acknowledgement after a material rules change.

A rules acknowledgement receipt should record Room ID, participant ID, rules version, notice version, timestamp, acknowledgement posture, provenance, and integrity fields where required. Acknowledgement does not create capabilities that were not already granted.

## 10. JSONL transport and Event Spine

JSONL is useful because it is append-oriented, inspectable, streamable, segmentable, and friendly to offline exchange. Production use requires more than appending lines to a file.

The Event Spine should use:

1. canonical state in Postgres;
2. transactional outbox behavior for Room-eligible mutations;
3. normalized, scope-aware event records;
4. segmented JSONL for transport, replay, export, debugging, and offline exchange;
5. durable sync inbox and apply receipts;
6. deterministic reducers;
7. visible lag, gaps, rejection, and replay state.

Disallowed:

```text
write Postgres
then append JSONL
then write Markdown
then hope all three succeeded
```

Required posture:

```text
validated command
  -> one Postgres transaction mutates canonical state
  -> same transaction appends eligible event/outbox row
  -> projector emits JSONL idempotently
  -> receiver stores inbox record
  -> policy validates event
  -> reducer applies event idempotently
  -> receipt records apply, reject, or quarantine
```

Every transport event requires stable event identity, schema version, event type, origin, Room scope, actor, idempotency key, causation/correlation references, payload, provenance, and integrity metadata.

Candidate event families include Room lifecycle, projection-policy changes, rules changes, participant lifecycle, capability grants/revocations, Thread disclosure, message events, document/artifact disclosure, Knowledge Base binding changes, publication changes, packet delivery/apply results, and synchronization gaps.

Not every application mutation belongs in the Room Event Spine. Eligibility must be explicit and scope-aware.

## 11. Prototype evidence

The prototype is product-design evidence, not runtime proof. It demonstrates that:

- a Home contains navigable Rooms;
- a Room combines files, participants, and conversation;
- a Room may be Project-backed or repository-backed;
- multiple Threads can belong to one Room even when one Chat is active;
- linked files can be visible beside conversation;
- private and public material can remain visibly distinct;
- provenance explains where disclosed material came from;
- the interface can present a moderator notice;
- presence is visible without implying unrestricted authority;
- Atlas, Rooms, and Chat are alternate projections over related state.

Production should preserve these interaction truths without copying the prototype's storage assumptions unchanged.

## 12. Current codebase mapping

| Current anchor | Current responsibility | Proposed role |
| --- | --- | --- |
| `guardian/db/models.py::User` | Canonical account boundary | Home owner |
| `guardian/db/models.py::UserProfile` | Presentation metadata | Home display metadata |
| `guardian/db/models.py::Project` | Organizes Threads and resources | Authoritative Room backing Project |
| `guardian/db/models.py::ChatThread` | Durable conversation container | Thread / Chat inside Room |
| `guardian/db/models.py::ChatMessage` | Durable authored turns | Thread transcript |
| `guardian/routes/projects.py` | Project CRUD and account scoping | Host Project selection seam |
| `guardian/routes/chat.py` | Thread, Message, completion routes | Existing Thread runtime beneath Rooms |
| `guardian/core/chat_completion_service.py` | Context and execution preparation | Consume Room-scoped context through policy |
| `guardian/context/broker.py` | Retrieval assembly | Disclosure-aware context selection |
| `events_outbox` | Durable event source | Room-eligible event projection source |
| audit and receipt records | Mutation/execution evidence | Provenance and Room receipt inputs |
| document/artifact link tables | Existing scope relationships | Room disclosure-binding inputs |
| `frontend/src/App.tsx` | Route-to-view composition | Future Room entry route |
| `frontend/src/features/workspace/` | Companion workspace | Possible Room files/context surface, not Room domain |

Candidate new module names are provisional and require inspection:

```text
guardian/rooms/contracts.py
guardian/rooms/tokens.py
guardian/rooms/store.py
guardian/rooms/projection_policy.py
guardian/rooms/world_packet.py
guardian/rooms/reducer.py
guardian/rooms/join_service.py
guardian/routes/rooms.py
```

Possible durable entities include Rooms, Room-to-Thread bindings, resource bindings, participants, capability bindings, rules versions, join receipts, projection versions, sync inbox records, and apply receipts.

No migration should be written until cardinality and authority decisions are closed against the current schema.

## 13. Phased delivery

### Phase 0: Doctrine and review receipt

Deliver this framework, a translation ledger preserving Zac's original concepts, unresolved decisions, and a review receipt. No runtime changes.

### Phase 1: Read-only local Room projection

Prove one local Room projected from one existing Project, containing multiple existing Threads and selected files. No visitors, remote sync, or authority migration.

Proof must show undisclosed Project data never appears, existing Chat completion remains unchanged, deleting the projection does not delete Project data, and projection failure is visible.

### Phase 2: First-class local Room policy

Add durable Room identity, backing Project reference, explicit bindings, rules versions, local participant/capability policy, audit, and receipts. Still no network join.

### Phase 3: Local join simulation and World Packet export

Add deterministic entry manifest, bounded World Packet generation, validation, disposable reducer projection, moderator notice, acknowledgement receipt, replay tests, integrity, and gap detection.

### Phase 4: Hosted Visitor and Collaborator slice

Prove one canonical Host serving one Room to an authenticated remote participant, with admission, capabilities, revocation, incremental delivery, stale/offline posture, and resynchronization. No multi-master Project writes.

### Phase 5: Two-node Room synchronization proof

Prove one Host Home, one participant Home, one Room, stable event identity, inbox/apply receipts, reconnect/replay, surfaced conflicts, and Host continuity when Codexify.Space is unavailable.

### Phase 6: Codexify.Space coordination

Only after direct Room proof: discovery, rendezvous, invitation delivery, optional relay, public projection coordination, and delivery receipts. Codexify.Space must not become private Home or Project authority.

### Phase 7: Advanced Atlas

Add richer spatial navigation after list, search, breadcrumb, permission, and synchronization surfaces are stable.

## 14. Design lineage and review covenant

Authorship statement:

> Zac originated the Home / Room / Chat / World Spine interaction model and the spatial prototype that established Rooms as shared, navigable contexts containing conversations, files, participants, provenance, and public/private boundaries.

Maintain a translation ledger for each material concept:

| Concept | Prototype intent | Production translation | Preserved behavior | Divergence | Reason | Zac review | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Home | Sovereign root with Rooms | Account-owned Home | Rooms remain navigable | Home is not a device superclass | Identity safety | Pending | Spec/prototype refs |
| Room | Shared context containing Chats and files | Governed Project projection | Shared context and multiple Threads preserved | Project remains backend authority | Transactional safety | Pending | Spec/code refs |
| Chat | Conversation inside Room | Existing Thread/Message runtime | Chat language preserved | Backend keeps Thread terminology | Compatibility | Pending | Route/model refs |
| World file | Join and sync transport | Versioned World Packet from Event Spine | Inspectable JSONL preserved | File is not sole authority | Recovery/idempotency | Pending | Packet/event refs |
| Rules notice | Visible governance | Versioned notice and acknowledgement receipt | Entry rules visible | Enforcement is capability-backed | Integrity | Pending | UI/protocol refs |

Each phase should produce a review receipt containing the version, concepts reviewed, preserved behaviors, intentional divergences, unresolved questions, runtime proof, documentation follow-through, Zac's response, Chris's decision, date, and evidence references.

The receipt must not imply agreement where no review occurred.

## 15. Open decisions

1. Is one Room backed by exactly one Project, or may future Rooms aggregate several through explicit mounts?
2. Can one Thread appear in several Rooms, or does it have one primary Room plus references?
3. Can a Room contain coordination events that never enter a Thread transcript?
4. Which Project streams are eligible for the first Room disclosure slice?
5. How are large files and historical transcripts referenced instead of embedded?
6. Does the first World Packet contain a reduced snapshot plus event tail, or only events from a known baseline?
7. Which rules changes require re-acknowledgement?
8. Can Visitors post, or is that a separate capability independent of the Visitor label?
9. How does a Collaborator propose Project mutation when the Room is a projection?
10. What retention applies to withdrawn or revoked Room content on participant Nodes?
11. How are deletion, tombstones, and privacy erasure represented across packet history?
12. Does `Space` become useful later as a Room grouping or network namespace?
13. Which prototype interactions are essential to Zac beyond those already documented?

## 16. ADR impact

**Classification:** Requires a new ADR before runtime implementation.

The ADR must decide:

- Home authority and relationship to User/account state;
- Room-as-Project-projection authority;
- Room-to-Thread cardinality;
- disclosure policy and capability boundaries;
- World Packet and Event Spine authority;
- JSONL transport status;
- join, rules, and acknowledgement semantics;
- publication and Codexify.Space boundaries;
- export/restore obligations;
- conflict, deletion, replay, and offline behavior.

This document is planning and consolidation only. It does not alter accepted runtime architecture.

## 17. Near-term recommendation

1. Review this framework with Zac.
2. Record the first translation receipt.
3. Inspect current Project, Thread, document-link, collaboration, outbox, and audit schemas.
4. Close one-Project-per-Room and Thread cardinality decisions.
5. Write the governing ADR.
6. Implement one read-only local Room projection only after those decisions are accepted.

The first vertical slice should prove this sentence and nothing larger:

> One existing Codexify Project can be rendered as one local Room containing several existing Threads and a deliberately selected set of shared context, without changing Project or Thread authority and without exposing undisclosed data.
