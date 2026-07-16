# Codexify Space Runtime and Federated Experience Architecture

**Classification:** Architecture-impacting product and protocol framework  
**Status:** Proposed living architecture, documentation only  
**Runtime claim:** This document does not claim that first-class HomeBases, Spaces, Rooms, World Packet synchronization, remote Space mounting, Atlas federation, public discovery, transactional commerce, or business-operated Nodes are implemented or supported.  
**Design lineage:** Zac originated the Home / Room / Chat / World Spine interaction model and the spatial prototype that revealed this product shape. Resonant Jones translated Home into HomeBase, preserved Space as the interactive experience layer, and defined Room as the shared Project-backed context inside that experience.

## 1. Product thesis

Codexify.Space is not one centralized application. It is a protocol-compatible environment in which people and organizations may host their own interactive experiences from infrastructure they control.

```text
User or Organization
└── HomeBase
    └── Spaces
        └── Rooms
            └── Threads
```

A HomeBase owns authority. A Space presents an experience. A Room gathers shared context. A Thread carries conversation.

The long-term product is a federated application runtime, not merely a collaborative editor.

## 2. Space as an application container

A Space is comparable to a website, application, portal, or interactive venue. It may define its own layout, navigation, tools, Room directory, public posture, and interaction model while sharing the same underlying identity, policy, event, synchronization, and receipt protocols.

Examples include:

- developer portal;
- research workspace;
- public website;
- community forum;
- documentation library;
- marketplace;
- design studio;
- simulation or game;
- local business presence;
- civic or neighborhood hub;
- Atlas discovery experience.

A Space is not constrained to one visual shell. Two Spaces may consume compatible World Packets while presenting entirely different experiences.

## 3. Space and Room boundary

The Space owns:

- experience identity;
- navigation and visual grammar;
- Room discovery;
- Space-wide rules;
- renderer requirements;
- public and invitation posture;
- capability declarations;
- discovery metadata;
- synchronization entrypoints.

The Room owns:

- shared files and artifacts;
- selected Project context;
- Threads and Messages;
- participant roster;
- Room rules and moderator notice;
- collaboration permissions;
- Room-scoped activity and receipts;
- bounded World Packet state.

The Space is where the interactive experience lives. The Room is where people gather around shared context.

## 4. Project-backed Rooms

During the first production phases, an existing Codexify Project remains the authoritative backend for work state. A Room is a governed projection of that Project.

The Host chooses which streams are disclosed:

- selected Threads;
- selected documents;
- selected artifacts;
- selected knowledge scope;
- selected repository references;
- selected activity and receipts;
- participant-visible presence;
- publication eligibility.

This lets a Host expose a useful collaborative surface without publishing the entire Project, filesystem, Vault, or private assistant context.

## 5. HomeBase hosting model

Each User or Organization owns a HomeBase identity boundary. A HomeBase may be served by one or more authorized Nodes.

Zac's core hosting principle is preserved:

> The experience should live under the authority of the participant or organization hosting it, whether that is my machine, his machine, or a dedicated server they control.

A HomeBase may use:

- a personal computer;
- home server;
- collaborator machine;
- dedicated business server;
- cloud instance;
- trusted community infrastructure;
- optional relay services.

Execution location and identity authority must remain distinct. A Node may host a Space without becoming the owner of the HomeBase.

## 6. Space manifest

Each Space should expose a signed or otherwise integrity-protected manifest containing public or participant-authorized metadata such as:

- Space ID;
- HomeBase and Host authority reference;
- title, description, and experience type;
- renderer compatibility;
- public, private, invite-only, or discoverable posture;
- Room directory policy;
- capability declarations;
- navigation hints;
- content resolution policy;
- synchronization endpoints;
- schema and protocol versions;
- integrity metadata;
- discovery tags and geographic hints when intentionally published.

The manifest describes an experience. It does not grant authority. Effective capabilities must be resolved by authenticated policy evaluation.

## 7. World Packet protocol

A World Packet is the bounded synchronization artifact used to hydrate or refresh a Space or Room projection.

```text
World Packet
├── bounded snapshot
├── event cursor
├── incremental event segment
├── capability and policy envelope
├── content references or bounded payloads
└── integrity metadata
```

JSONL is the initial event transport serialization. The contract must remain transport-aware but serialization-independent so future encodings can coexist.

The production path is:

```text
Postgres mutation
  -> transactional outbox
  -> normalized World Spine event
  -> scoped JSONL packet
  -> authenticated ingest
  -> idempotent reducer
  -> local projection
  -> renderer
```

The UI may read reduced Room State derived from JSONL packets. The UI must not treat a mutable shared JSONL file as the transactional source of truth.

## 8. Atlas as renderer

Atlas is a renderer over reduced topology and content state. It is not a database and not the only possible Space interface.

Atlas can represent:

- HomeBases;
- Nodes;
- Spaces;
- Rooms;
- Threads;
- participants;
- trust and federation relationships;
- public documents;
- search results;
- articles and bookmarks;
- nearby businesses;
- available services;
- active Nodes accepting Guests;
- remote communities and digital villages.

A visual card may correspond to a real remote authority, not merely a decorative graph node.

## 9. Local Atlas

Local Atlas presents the immediate sovereign environment:

- the current HomeBase;
- attached Nodes;
- private and public boundaries;
- hosted Spaces;
- Rooms and Threads;
- trusted peers;
- current health and activity;
- available local services.

Local Atlas should remain useful without federation or Codexify.Space availability.

## 10. Federated Atlas

Federated Atlas presents discoverable remote topology:

- other HomeBases;
- businesses and organizations;
- public Spaces;
- community clusters;
- joinable Rooms;
- public resources;
- network trust posture;
- availability and guest policy;
- search and recommendation results;
- geographic or thematic neighborhoods.

Selecting a card may reveal more Spaces and Rooms hosted by that authority or begin an authenticated join flow.

Federated Atlas should provide equivalent flat, searchable, keyboard-accessible views. Spatial presentation is a projection choice, not a usability gate.

## 11. Digital villages

A digital village is a voluntary federation of HomeBases or Nodes that agree to shared discovery, trust, moderation, relay, and participation rules.

Examples may include:

- maker communities;
- research consortia;
- local business networks;
- family and friend networks;
- open-source teams;
- schools and learning communities;
- civic groups;
- professional associations.

A village is not a superuser over member HomeBases. Each authority decides what it publishes and which capabilities it accepts.

## 12. Business and institutional Nodes

Businesses participate through the same protocol family as individuals.

A business HomeBase may publish Spaces for:

- public presence;
- customer support;
- catalog browsing;
- bookings;
- community discussion;
- documentation;
- private client Rooms;
- staff collaboration;
- public demonstrations;
- marketplace activity.

A larger operator may provide dedicated uptime, moderation, and service commitments, but it does not receive a privileged sovereignty model.

## 13. Codexify.Space role

Codexify.Space may act as an optional coordination layer providing:

- discovery and directory services;
- rendezvous and invitation exchange;
- relay and NAT traversal assistance;
- public metadata indexing;
- trust bootstrap;
- protocol negotiation;
- public projection hosting;
- federation navigation.

Codexify.Space must not become required authority for private HomeBase, Project, Room, or participant state.

The product should win through convenience, trust, and interoperability rather than lock-in.

## 14. Search and discovery

Atlas may become a new way to represent search results and recommendations.

A result may be:

- a public Space;
- a Room open to Guests;
- an article;
- a bookmark;
- a business;
- a service;
- a product offer;
- a person or organization;
- an active Node;
- a community federation;
- a public artifact.

Search results must preserve provenance, authority, freshness, public posture, and the distinction between an indexed description and live remote state.

## 15. Transactions and commerce

The architecture leaves room for shopping, bookings, subscriptions, and service transactions inside Spaces. This is future vision, not current runtime truth.

Any commerce protocol must be introduced through its own architecture-impacting contract and must include:

- explicit offer identity;
- seller and buyer authority;
- price and policy versioning;
- acceptance receipts;
- dispute evidence;
- payment-provider boundaries;
- revocation and refund semantics;
- no ambient financial authority from merely entering a Space or Room.

## 16. Security boundaries

The protocol must enforce:

- authenticated Host identity;
- explicit participant capability resolution;
- least-privilege disclosure;
- signed or integrity-protected manifests and packets;
- replay and idempotency controls;
- schema negotiation;
- revocation and stale-state handling;
- no credential or private prompt synchronization;
- no filesystem traversal through content references;
- no automatic trust transfer across federation edges;
- visible rules and moderator notices before participation.

## 17. Current truth and non-claims

Current truth:

- Codexify is a local-first FastAPI, React, Postgres, and Redis system.
- Projects, Threads, Messages, documents, artifacts, retrieval, queues, and outbox records already exist.
- Postgres remains the durable application authority.
- Redis remains operational infrastructure rather than federated durable state.

Not yet true:

- HomeBase and Space are not first-class runtime entities.
- Space manifests are not implemented.
- remote Space mounting is not implemented.
- World Packet synchronization is not a supported protocol.
- Atlas federation and business discovery are not implemented.
- transactions and commerce are not implemented.
- Codexify.Space is not a public federation authority.

## 18. Invariants

1. HomeBase owns authority.
2. Space owns the interactive experience.
3. Room owns bounded shared context.
4. Thread owns durable conversation.
5. Project remains authoritative for first-phase Room-backed work state.
6. Nodes host; they do not silently acquire identity ownership.
7. JSONL transports events; it does not replace Postgres.
8. Atlas renders reduced state; it does not own canonical truth.
9. discovery metadata is not equivalent to authenticated live state.
10. public visibility never implies write, tool, transaction, or administration capability.
11. federation is optional.
12. Codexify.Space is coordination infrastructure, not mandatory private authority.
13. spatial interfaces must have accessible non-spatial equivalents.
14. commerce remains separately governed and unimplemented until approved.
15. this document does not widen the supported release promise.

## 19. Delivery path

1. Canonicalize vocabulary and ADRs.
2. Render one local Space containing one Project-backed Room.
3. Define Space and Room manifests.
4. Define World Packet event schema and reducer behavior.
5. Prove idempotent local packet rendering.
6. Prove participant capabilities and moderator notice flow.
7. Prove two-node Room synchronization.
8. Support multiple Space renderers over the same protocol.
9. Add bounded discovery records and Federated Atlas.
10. Prove one voluntary digital village.
11. Add organization-grade hosting posture.
12. Treat commerce as a separate future program.

## 20. ADR impact

**Classification:** Requires new ADR before runtime implementation.

The governing ADR must define:

- HomeBase ownership and Node hosting boundaries;
- Space application-container semantics;
- Room and Project projection semantics;
- manifest and packet authority;
- Atlas renderer boundaries;
- Codexify.Space authority limits;
- federation discovery and trust posture;
- coexistence with the current Project and Thread runtime.

## 21. Relationship to the Codexify.Space v2 volume

This document defines the product and protocol vision for interactive Spaces and federation.

Use `docs/architecture/home-room-thread-world-packet-framework.md` for the collaboration, synchronization, and Project-projection substrate.

Use `docs/architecture/codexify-space-v2/README.md` as the volume entrypoint and `docs/architecture/codexify-space-v2/open-decisions.md` for unresolved architecture questions.