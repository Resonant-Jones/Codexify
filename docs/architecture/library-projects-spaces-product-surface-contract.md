# Library, Projects, Spaces, and Product Surface Contract

> Classification: architecture contract / product-surface ontology  
> Status: user-approved product direction; runtime implementation remains unproven  
> Last updated: 2026-10-05

## Purpose

This contract defines how Codexify should distinguish personal resources, private work, shared experiences, and social/network context without turning presentation containers into new authority boundaries.

It refines existing architecture rather than introducing a parallel Space model:

- [Product Lanes and Boundaries](./product-lanes-and-boundaries.md) owns the stable product-program vocabulary.
- [ThreadSpace Integration Blueprint](./threadspace-integration-blueprint.md) already defines Spaces as interactive application or community containers on the ThreadSpace network plane.
- [ADR-045: Space Participant Resolution Model](./adr/045-space-participant-resolution-model.md) governs future Space roster, participant, role, capability, trust, and presence semantics.
- [Hosted Room and Sovereign Node Participation Contract](./hosted-room-sovereign-node-contract.md) preserves the distinction between a shared meeting surface and participant-owned intelligence.
- [Data and Storage](./data-and-storage.md) remains the storage-authority map.

This document does not widen current Beta support, create schema, add routes, rename existing runtime objects, or claim that Library or Spaces are implemented.

## Product surface model

Codexify should present five distinct user-facing concerns:

| Surface | User question | Architectural role |
|---|---|---|
| **Guardian** | What can I ask, understand, or do? | Intelligence and interaction surface over existing authorized context and capabilities. |
| **Library** | What resources do I own or have authorized access to? | Unified user-facing projection over files, documents, images, audio, video, generated artifacts, and other resources. |
| **Projects** | What am I working on? | Inward-facing knowledge, retrieval, and work scope. |
| **Spaces** | What experience am I exposing or sharing with other people? | Outward-facing interactive application, publication, community, and collaboration container. |
| **People / ThreadSpace** | Who am I connected to, and through what bounded relationship? | Relationship and network plane for Contacts, invitations, participants, nodes, presence, and explicit reachability. |

These surfaces may link to the same underlying resource while preserving different authority and disclosure rules.

## Library contract

### Library is a projection, not a new storage authority

**Library** is the canonical user-facing resource surface for Codexify.

It may aggregate or project:

- documents;
- images;
- video;
- audio;
- uploaded files;
- generated artifacts;
- exported or imported resources;
- other future resource classes that have an authoritative backing record.

Library does not replace the canonical storage or ownership model. Postgres, object/file storage, and other governed persistence systems remain authoritative for their respective records and bytes.

A Library entry is therefore a view/reference over an authoritative resource, not a second copy and not a second ownership system.

### Documents and Gallery become Library modes

The current **Documents** and **Gallery** application surfaces should converge into Library presentation modes rather than remain permanent peer application destinations.

Conceptually:

```text
Library
  All
  Documents
  Images
  Video
  Audio
  Generated / Artifacts
  Collections
  Imports
```

This list is product-direction vocabulary, not a canonical runtime token registry. Exact filters, routes, tabs, and storage mappings remain implementation work.

A visual Gallery remains useful as a Library view. Document-oriented list/editor experiences remain useful as Library views. The contract removes the need for each media class to become its own top-level application.

### Library invariants

- Library view state must not redefine resource ownership.
- Library grouping or collections must not silently move, duplicate, or re-scope canonical resources.
- Search/index state remains derived and must not become canonical content authority.
- Linking one resource into multiple Projects or Spaces must preserve one authoritative identity where the underlying resource model supports it.
- Presentation type does not imply disclosure. An image being visible in the owner's Library does not make it visible in a Space.
- Provenance must survive transitions between Library, Project, and Space surfaces.

## Project contract

A **Project** is primarily inward-facing.

Projects organize work, retrieval scope, context, tasks, documents, and conversations around something the user is doing.

A Project may consume or reference Library resources. It may later contribute explicit resources to a Space. Neither operation makes the Project itself a social or network authority.

Project membership, retrieval scope, and workspace context must not be inferred from Space membership.

## Space contract

A **Space** is primarily outward-facing: a user-controlled shared environment that selected people can enter and experience.

The existing ThreadSpace definition remains canonical: a Space is an interactive application or community container with a declarative manifest, admission policy, capability set, and Room directory.

This contract makes the intended experience breadth explicit. A Space may present as:

- a site or rich publication;
- a blog or journal;
- a forum or community;
- a mini application;
- a live-event or streaming surface;
- a collaborative workshop;
- a company, team, or family portal;
- an interactive exhibition;
- an immersive or VR environment;
- a front door to explicitly exposed tools or services on a user's node.

These are presentation/application forms of a Space, not separate identity or authority classes.

### Site is a Space presentation

A **Site** should be treated as one possible published presentation of a Space rather than a competing top-level authority model.

A Space may have no site presentation, one site presentation, or multiple bounded presentation modes over the same authorized Space resources.

Publishing a site must not imply that the entire Space, its Rooms, its participants, its private Library references, or its mounted capabilities are public.

### Spaces are not Projects

A Project and a Space may be linked, but they answer different questions:

- **Project:** what am I working on?
- **Space:** what am I intentionally exposing or sharing with others?

A user may publish selected Project outputs into a Space without exposing the Project's complete retrieval corpus, task state, memory, private conversations, or working files.

### Spaces are not ambient network access

A Space may expose tools or services hosted on the owner's home network or another authorized node, but membership must never become generic LAN, filesystem, process, microphone, camera, or device access.

The governing model is capability exposure:

```text
Node capability
  -> explicitly advertised
  -> explicitly granted to Space / participant scope
  -> invoked through governed adapter or command boundary
  -> receipt / provenance returned
```

Capability advertisement is not authorization.

Space membership is not authorization to every advertised capability.

A capability grant is not permission to enumerate unrelated network services.

Infrastructure or vendor integration must not silently become the owner of Space identity, participant identity, content, or capability policy.

## Relationship to ThreadSpace

ThreadSpace is the network plane through which Spaces, participants, invitations, presence, and remote nodes may be discovered or reached under explicit policy.

ThreadSpace is not the Space itself.

The expected relationship is:

```text
People / Contacts / Nodes
          |
      ThreadSpace
          |
        Space
      /   |    \
   Room  Site  Capability endpoints
     |
 Conversation
```

The authoritative model remains graph-shaped. Visual containment must not imply ownership, hosting, trust, or permission.

## Resource movement and publication

Codexify should prefer explicit references and publication records over hidden copying.

Examples:

### Use a Library item in a Project

```text
Library resource
  -> Project reference / work context
```

The resource remains owned by its authoritative source. The Project gains only the scoped relationship needed for work.

### Publish a Library or Project output into a Space

```text
Library resource or Project output
  -> explicit publish/share action
  -> Space-visible resource reference
  -> participant capability / disclosure policy
```

Publication must record what was exposed, to which Space or Room, under which visibility/capability posture, and how revocation is represented.

### Expose a node-hosted tool to a Space

```text
Node service/tool
  -> governed capability endpoint
  -> Space-scoped grant
  -> participant invocation
  -> execution receipt / artifact
```

No step grants ambient access to the node.

## Mobile and application navigation consequences

This contract supports a simpler primary product information architecture.

When the relevant surfaces exist, a compact client may converge toward:

```text
Guardian | Library | Spaces | People | Me
```

This is a product-direction target, not a claim about current routes.

Consequences:

- Documents and Gallery can converge under Library.
- Server status, diagnostics, settings, and account administration do not need permanent peer navigation slots in ordinary user mode.
- Projects remain available as work context and may be entered from Guardian, Library, workspace navigation, or other Project-aware surfaces rather than requiring the same global-navigation posture as Spaces.
- Spaces and People should not appear implemented or release-supported until their own runtime, authorization, privacy, and proof gates are satisfied.

## Authority invariants

1. Library is not a new persistence authority.
2. Project containment is not social membership.
3. Space membership is not access to every Room, Project, Library item, conversation, or capability.
4. A Site is a presentation of explicitly published Space state, not automatic publication of the Space.
5. Capability advertisement is not capability authorization.
6. Capability authorization is scoped; it is not ambient node or network access.
7. Contact, Participant, Account, Node, Space, Room, Project, and resource identity remain distinct.
8. Host authority is not identity authority.
9. Vendor integration does not gain implicit ownership, observation, recording, or disclosure rights merely because a capability is used.
10. Publication, invitation, acceptance, execution, and completion remain distinct events.
11. Revocation must fail closed for future access; it must not be represented as retroactive erasure of information already disclosed.
12. Current release truth remains governed by [00 Current State](./00-current-state.md).

## Implementation sequence

This contract is actionable, but implementation should remain staged.

### Stage 1: Library presentation convergence

- Introduce a Library product surface over existing document/media/artifact sources.
- Preserve existing canonical resource IDs and storage authority.
- Make Gallery and Documents Library modes before deleting legacy routes.
- Add migration-safe navigation aliases and explicit compatibility tests.
- Keep search/index state derived.

**Gate:** existing Documents and Gallery workflows remain reachable and resource identity/provenance is unchanged.

### Stage 2: Shared product navigation convergence

- Align mobile web and Scout around the same semantic application destinations.
- Treat platform-specific navigation as a renderer of one shared information architecture.
- Keep workspace/Project/thread context separate from app-level navigation.

**Gate:** navigation changes do not alter authority, selected Project/thread state, or resource scope.

### Stage 3: Space product contract implementation

- Reuse the existing ThreadSpace, invitation, participant, Room, and capability architecture.
- Define first supported Space persistence and manifest schema through a separately approved architecture-impact task.
- Define publication records and explicit Library/Project-to-Space references.
- Keep unknown renderers and capabilities fail-closed.

**Gate:** Space implementation has explicit owner, admission, roster, publication, revocation, and capability-authority proofs.

### Stage 4: Space applications and node capability exposure

- Add governed renderer/application profiles.
- Add explicitly installable or locally approved mini-app/tool adapters.
- Permit node-hosted capability exposure only through scoped grants and receipts.
- Qualify live-event and immersive/VR surfaces independently rather than treating them as automatic consequences of Space membership.

**Gate:** no Space path creates ambient node/network authority or hidden vendor observation.

## ADR impact

This contract refines product-surface ontology and aligns with existing proposed Space architecture. It does **not** supersede ADR-045, ADR-044, the ThreadSpace blueprint, or Hosted Room contracts.

No new ADR is required merely to record this product-surface distinction.

A new or amended ADR is required before runtime work that introduces or changes:

- canonical Library persistence or ownership semantics;
- first-class Space schema or durable Space identity;
- publication/revocation storage;
- capability grant/token registries;
- node-hosted capability execution;
- cross-node Space synchronization;
- public discovery;
- immersive/VR transport or presence semantics;
- any release-support claim.

## Non-goals

This document does not:

- implement Library;
- delete or rename current Documents/Gallery routes;
- implement Spaces, Sites, Forums, mini apps, streaming, or VR;
- create broad home-network access;
- introduce a vendor plugin marketplace;
- make ThreadSpace a central service;
- grant Guardian ambient access to user resources;
- change current Beta support.

## Bottom line

Codexify's product model should remain simple even as its capability ceiling expands:

- **Guardian** is how the user interacts with intelligence and action.
- **Library** is where the user's resources are presented.
- **Projects** are inward-facing work contexts.
- **Spaces** are outward-facing shared experiences.
- **People / ThreadSpace** are the relationship and network plane.

Projects consume or reference Library resources.

Spaces publish selected resources and expose selected capabilities.

People enter Spaces through explicit relationship, invitation, participant, and authorization boundaries.

The user decides what crosses each boundary.
