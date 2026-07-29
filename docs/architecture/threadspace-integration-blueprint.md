# ThreadSpace Integration Blueprint

> Classification: architecture planning document
>
> Status: proposed future architecture
>
> This document is not current runtime truth, not an accepted ADR, and not a release claim.

## Purpose

This document preserves the refined integration plan for ThreadSpace, Atlas, and Federated Galaxy after mapping the product concept against Codexify's current runtime, identity, storage, synchronization, UI, and release boundaries.

The plan does not replace the original product direction. It converts that direction into explicit authority boundaries, protocol contracts, state ownership rules, and evidence gates suitable for future ADR and implementation work.

Atlas and Galaxy are presentation modes over a neutral topology projection. They do not own identity, authorization, storage, synchronization, or federation truth.

## Current Boundary

Current Codexify release truth remains governed by `docs/architecture/00-current-state.md`.

Today:

- Codexify is a local-first React, FastAPI, Postgres, and Redis system.
- Postgres remains the system of record for canonical application state.
- Redis remains operational transport and coordination for queues, locks, task events, and worker health.
- `events_outbox` provides a durable event source for existing event surfaces.
- The lightweight sync bus is process-local and is not restart-stable federation truth.
- Federation remains experimental, high-blast-radius, and trust-policy sensitive.
- Shared presence, hosted Rooms, cross-Vault synchronization, Atlas, and Galaxy are not supported release surfaces.

This document must not be used to widen those claims.

## Canonical Vocabulary

### Infrastructure and identity

| Term | Proposed canonical meaning |
| --- | --- |
| `Vault` | A hosted Codexify runtime and storage boundary. A Vault may host multiple accounts and HomeBases. A Vault is infrastructure, not a person. |
| `VaultNode` | A specific canonical-machine or audit-authority role governed by existing architecture contracts. Not every Vault is automatically a VaultNode. |
| `Account` | An authenticated principal on one Vault. Account identifiers are Vault-scoped. |
| `Network Profile` | A user-controlled identity profile that may link accounts across Vaults. It is not a global identity directory. |
| `HomeBase` | A portable, user-owned network namespace. It may be hosted by a Vault but must not be permanently identified by that host. |
| `Home Vault` | The Vault currently hosting the authoritative HomeBase copy and brokering that user's network connections. |

### Collaboration and content

| Term | Proposed canonical meaning |
| --- | --- |
| `Space` | An interactive application or community container with a declarative manifest, admission policy, capability set, and Room directory. |
| `Room` | A bounded membership, authorization, and disclosure context inside a Space. |
| `Conversation` | A private or group chat inside a Room. Existing `chat_threads` may provide a compatibility source for this concept. |
| `Project` | A knowledge, retrieval, and work scope. A Project may be linked to one or more Rooms but is not itself the social access boundary. |
| `Artifact` | A document, image, repository reference, generated output, or other resource linked to a Space, Room, Conversation, or Project. |
| `Capability Endpoint` | An AI, compute, repository, tool, or service endpoint. It may advertise capabilities and produce receipts but does not own identity. |

### Network and presentation

| Term | Proposed canonical meaning |
| --- | --- |
| `ThreadSpace` | The user-facing network plane formed from authorized projections across one or more Vaults. It is not a central database, identity provider, or single global server. |
| `Atlas` | A spatial renderer for local and directly known network topology. |
| `Galaxy` | A discovery-oriented renderer for broader ThreadSpace summaries and explicit archetypes. |
| `Federation` | A specific trust and coordination arrangement among Vaults. It is not synonymous with every remote connection. |
| `Public Pavilion` | A curated public projection backed by explicit, receipt-bearing publication records. |
| `Archetype` | Editorial or synthetic discovery content that must never masquerade as live federation data. |

## Graph-Shaped Ownership

The user interface may present a hierarchy:

```text
HomeBase
  Space
    Room
      Conversation
```

The backend model must remain graph-shaped:

- A HomeBase may link to a Space hosted by another Vault.
- A Space may be owned by one principal and hosted by another Vault.
- A Room may bind a Project without owning all Project content.
- A Conversation may have fewer participants than its parent Room.
- An Artifact linked to a Room may still have narrower visibility.

Visual containment must never imply ownership, hosting, trust, authority, or permission.

## Core Architecture Invariants

1. Canonical state remains at the authoritative Vault.
2. Atlas, Galaxy, caches, packets, and Session Spine state are projections.
3. Host authority is not identity authority.
4. Infrastructure administration does not automatically grant product-level content access.
5. Space membership does not imply access to every Room.
6. Room membership does not imply access to every Conversation, Project, or Artifact.
7. Unauthorized entities must be removed server-side rather than hidden only in React.
8. Room is a social and authorization boundary; Project is a knowledge and work boundary.
9. Vault and VaultNode remain distinct concepts.
10. Existing event and sync surfaces must be reconciled before introducing another event truth surface.
11. Postgres entity state remains canonical. Events support audit, projection, replay, and synchronization without silently converting the runtime to event sourcing.
12. Remote Space manifests must not inject arbitrary JavaScript, HTML, CSS, routes, renderers, or presentation literals.
13. Remote presentation requests must resolve through bounded local token registries.
14. ThreadSpace must not require a central identity authority.
15. Every cross-Vault write must be idempotent, attributable, authorized, and version-checked.
16. Every remote projection must expose freshness and authority.
17. Graph visualization must not require Neo4j.
18. New entities and relationships must remain portable under the account export and restore contract.
19. Legacy Threadspace material remains quarantined unless a future ADR explicitly reclassifies it.
20. No implementation or documentation artifact may silently widen current release support.

## Architecture Planes

### Authority plane

The authoritative Vault owns:

- entity records
- membership and capability grants
- Room and Conversation ordering
- publication decisions
- revocation
- policy versions
- audit records

### Durable event plane

Committed mutations should emit tenant-scoped events through the existing durable outbox path.

This plane records:

- what changed
- which aggregate changed
- who authorized the change
- which version resulted
- which audiences may receive a projection

Before creating new event infrastructure, implementation work must inspect `events_outbox`, event lineage, retention, cursors, and replay suitability. If outbox retention cannot support projection repair, a downstream durable projection journal may be added without becoming a competing mutation authority.

### Federation transport plane

World Packets transport authorized projections between boundaries. They may carry:

- bounded snapshots
- cursors
- ordered delta segments
- redaction metadata
- issuer and authority identity
- protocol and schema versions
- signatures
- expiry and freshness data

Serialization format is an implementation decision. The architecture contract governs semantics rather than binding the system permanently to one encoding.

### Client projection plane

Session Spine reduces authorized packets into the current viewer state:

- connected Vaults
- active HomeBase
- selected Space, Room, Conversation, Project, or Artifact
- per-Vault cursors
- freshness and gap status
- route continuity
- local layout preferences
- pending write intents

Session Spine is not a canonical account, Room, or federation database.

## State Ownership and Synchronization Categories

| State category | Authority | Synchronization posture |
| --- | --- | --- |
| Shared Room messages and artifacts | Room's authoritative Vault | Shared with authorized participants |
| Memberships, grants, and policies | Resource authority | Shared only as required for enforcement and display |
| User pins, read markers, and saved layout | User's HomeBase | May sync across that user's own clients |
| Active viewport, open drawer, hover, and transient selection | Device Session Spine | Device-local by default |
| Draft text and unsent intents | Device or user-private HomeBase store | Never shared with other participants by default |
| Remote cached state | Client or Home Vault cache | Non-authoritative and freshness-labeled |
| Public discovery records | Publishing authority | Cacheable until expiry |
| Secrets and Vault credentials | Secure credential store | Never placed in topology packets |

A future shared-layout feature must be an explicit collaborative artifact. It must not emerge from accidental synchronization of personal UI state.

## Resource Reference Contract

Local persistence identifiers cannot safely cross Vault boundaries without qualification.

A future canonical resource reference should contain at least:

```ts
type ResourceRef = {
  vaultId: string;
  kind:
    | "network_profile"
    | "homebase"
    | "space"
    | "room"
    | "conversation"
    | "project"
    | "artifact"
    | "capability_endpoint";
  id: string;
};
```

`vaultId` must remain stable across URL changes and should be anchored to a verifiable Vault identity or key rather than the current hostname.

## Topology Projection Contract

Atlas and Galaxy must consume a viewer-specific neutral projection contract.

```ts
type TopologyNode = {
  ref: ResourceRef;
  source:
    | "authoritative"
    | "remote_signed"
    | "derived_compat"
    | "archetype"
    | "cached_stale";

  ownerRef?: ResourceRef;
  hostVaultId: string;
  containerRef?: ResourceRef;

  disclosure: "existence" | "summary" | "metadata" | "content";
  version: string;
  lastVerifiedAt: string;

  presentation?: {
    variantToken?: string;
    iconToken?: string;
    densityToken?: string;
  };
};

type TopologyEdge = {
  id: string;
  family:
    | "trust"
    | "membership"
    | "grant"
    | "publication"
    | "service"
    | "lineage";

  relation: string;
  source: ResourceRef;
  target: ResourceRef;
  state: string;
  authorityVaultId: string;
  lastVerifiedAt: string;
  evidenceRef?: ResourceRef;
};

type TopologyProjection = {
  schemaVersion: string;
  projectionId: string;
  viewerRef: ResourceRef;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  cursors: Record<string, string>;
  generatedAt: string;
};
```

Synthetic or compatibility nodes must be labeled `derived_compat`. Archetypes must be labeled `archetype`. Neither may appear canonical.

## Edge Families and Token Domains

The following meanings must not be flattened into one connection enum:

- `trusted` is a trust assertion.
- `shared` is an authorization or collaboration state.
- `published` is a disclosure action.
- `public` is a visibility posture.
- `compute` is a service relationship.
- `repo` is an artifact or integration relationship.

Canonical registries must be bounded by semantic domain in accordance with the canonical token philosophy.

## Connection-State Dimensions

A Vault relationship must expose independent state dimensions.

| Dimension | Example states |
| --- | --- |
| Transport | `resolving`, `connecting`, `connected`, `degraded`, `disconnected` |
| Trust | `unverified`, `verified`, `changed`, `revoked` |
| Authentication | `unauthenticated`, `authenticating`, `authenticated`, `expired`, `denied` |
| Projection | `empty`, `syncing`, `current`, `stale`, `gap_detected`, `repairing`, `failed` |

A reachable Vault may be untrusted. An authenticated principal may lack Room access. A trusted Vault may still hold stale projection state.

## Consistency Model

ThreadSpace must not invent a fictional global clock.

- A Conversation has one authoritative host that assigns canonical message order.
- Room memberships and grant versions are ordered by the authoritative Vault.
- Composite Atlas and Galaxy views are eventually consistent across Vaults.
- Discovery summaries are TTL-bound and may be stale.
- Presence is best-effort and is never proof of membership or authorization.
- Offline writes remain explicit queued intents and must not be silently merged.
- Configuration writes use optimistic concurrency or expected-version checks.
- Cursor gaps fail closed and trigger snapshot repair.

## World Packet Requirements

A future packet envelope should carry:

- `packet_id`
- `protocol_version`
- `schema_version`
- `issuer_vault_id`
- `audience_ref`
- `scope_ref`
- `snapshot_version`
- `from_cursor`
- `next_cursor`
- authorized nodes, records, or events
- redaction metadata
- `issued_at`
- `expires_at`
- signer key identifier
- signature

Binary assets should move through separate authorized asset manifests or content-addressed transfer. They should not be embedded casually into topology packets.

## Space Manifest and Application Safety

The first supported Space model must be declarative.

A Space manifest may name:

- an approved local `renderer_id`
- a manifest contract version
- bounded presentation tokens
- declared capabilities
- admission posture
- Room directory metadata visible to the current viewer

A remote Space manifest must not:

- load scripts or stylesheets
- inject arbitrary HTML
- define application routes
- choose arbitrary colors, shadows, radii, or layout values
- install a renderer
- broaden permissions implicitly
- trigger capability installation

Unknown renderers must fall back to a safe generic local representation.

Future custom Space applications must pass through Codexify's governed extension proposal, sandbox, review, install-gate, capability registry, and runtime binding doctrine. Federation must never become an implicit software installation protocol.

## Provider-Independent AI Capability Model

Local versus cloud AI remains a provider-routing and policy concern, not a Space identity concern.

A Space or Room may declare capability needs such as:

- `inference.chat`
- `inference.embed`
- `inference.image`
- `artifact.summarize`

The Vault's provider registry resolves those capabilities to allowed providers. Provider credentials remain inside the Vault boundary.

The safest first shared-Room execution policy is:

> The Room's authoritative Vault executes and persists shared assistant turns.

Future participant-home execution may be considered only with explicit execution receipts, provenance, and policy rules.

## Access and Disclosure Model

Roles may remain convenient bundles, but enforcement should resolve capabilities.

Candidate capability domains include:

- `space.discover`
- `space.enter`
- `room.discover`
- `room.enter`
- `conversation.discover`
- `conversation.read`
- `conversation.post`
- `artifact.read`
- `artifact.attach`
- `participant.invite`
- `participant.remove`
- `content.moderate`
- `resource.publish`
- `capability.execute`
- `policy.administer`

A grant should preserve:

- subject reference
- resource reference
- capability set
- issuing authority
- policy version
- creation and expiry
- revocation state
- constraints
- invite or provenance reference

Effective access is the intersection of:

1. Room or Conversation grants
2. Project or Artifact visibility
3. publication policy
4. current revocation state
5. authenticated subject
6. Vault exposure and egress policy

Private Conversation existence, participant counts, and activity must not leak through Room-wide topology projections.

## React and AppShell Integration Posture

ThreadSpace should be a sibling route inside the existing frontend and AppShell, not a second frontend shell.

A future route may distinguish:

```text
/threadspace
  ?scope=homebase
  ?scope=circles
  ?scope=public
  &view=atlas|galaxy|list
```

The exact route contract remains an implementation decision.

UI posture:

- Keep one primary topology surface.
- Reuse the existing Workspace Inspector for user-facing details and actions.
- Keep protocol diagnostics in opt-in diagnostic surfaces rather than the normal Workspace drawer.
- Selecting a Room or Conversation should open the existing chat surface.
- Selecting an Artifact should open the existing document or gallery surface.
- Preserve the return path, filters, and viewport when navigating away.
- Build accessible list parity alongside or before the spatial renderer.
- Treat canvas position as viewer-owned UI state.
- Preserve existing AppShell token, surface, and layout law.

## Recommended First Multi-Vault Transport Posture

The recommended first implementation uses Home Vault brokerage:

```text
Client
  -> Home Vault
    -> Remote Vaults
```

The frontend may model multiple logical Vault connections while maintaining one primary authenticated control connection.

This posture reduces early complexity around:

- browser cross-origin rules
- duplicated credentials
- direct peer trust material in the browser
- independent reconnect policies
- many simultaneous transport implementations

The client-facing connection registry should remain transport-agnostic so direct browser-to-Vault connections can be introduced later without redefining topology contracts.

## Staged Execution Plan

Calendar estimates must not substitute for dependency and proof gates.

### Stage 0: Evidence and governance reconciliation

- Inventory prototype behaviors as functional, simulated, hardcoded, or visual-only.
- Inspect current Session Spine, runtime configuration, auth client, live events, `events_outbox`, event lineage, sync API, federation routes, collaboration permissions, and identity scoping.
- Reconcile the ADR index and any numbering or naming collisions.
- Classify related documents as current contract, proposal, historical, or prototype reference.
- Produce a terminology and authority decision ledger.

**Gate:** No runtime changes. Every claim is labeled as live-runtime proven, test-proven, code-path only, documented contract, or working theory.

### Stage 1: Umbrella authority and projection ADR

Define:

- Vault versus VaultNode
- Account versus Network Profile
- HomeBase ownership versus hosting
- Space, Room, Conversation, and Project relationships
- ThreadSpace as a decentralized projection plane
- Atlas and Galaxy as renderers
- authoritative Vault rule
- qualified resource references
- brokered versus direct connection abstraction
- access non-inheritance
- authority, event, transport, and client projection planes
- legacy Threadspace quarantine
- release boundary

**Gate:** ADR accepted and indexed. Renderer geometry and styling remain outside architecture law.

### Stage 2: Versioned contracts and fixtures

Create backend and frontend contracts for:

- `ResourceRef`
- `VaultDescriptor`
- `TopologyProjection`
- topology node and edge families
- connection-state dimensions
- packet envelope
- canonical tokens and error codes
- version negotiation and unknown-type behavior
- shared golden fixtures

**Gate:** Python and TypeScript round-trip fixtures pass. No routes or migrations yet.

### Stage 3: Read-only local compatibility projection

- Add a neutral topology projection endpoint rather than a renderer-named endpoint.
- Derive nodes from existing accounts, Projects, Threads, documents, collaboration data, and capability state.
- Label virtual HomeBase, Space, and Room nodes as `derived_compat`.
- Add a native React route with accessible list and spatial representations.
- Reuse existing navigation into chat and document surfaces.
- Keep the surface feature-flagged and outside current release support.

**Gate:** Every node traces to real current data or is explicitly compatibility-derived.

### Stage 4: Canonical local HomeBase, Space, and Room model

Introduce explicit entities and relationships, potentially including:

- HomeBases
- Spaces
- Rooms
- HomeBase-Space links
- Room-Project links
- Room-Conversation links
- participant and capability grants
- publication records
- user-owned topology preferences

Use relationship tables rather than embedding Room policy into Projects.

**Gate:** Clean-start, existing-instance, archived-snapshot, downgrade or re-upgrade where supported, export and restore, and existing chat compatibility proofs pass.

### Stage 5: Hosted-account and authorization readiness

Audit and enforce tenant and user scoping across:

- Postgres
- vector search
- media storage
- event delivery
- Redis keys
- workers
- collaboration permissions
- logs and diagnostics

Implement capability resolution, invitations, admission, expiration, revocation, and existence-leak tests.

**Gate:** Host operator, owner, participant, nonparticipant, expired participant, and revoked participant receive distinct correct projections.

### Stage 6: Session Spine v2 and durable projection feed

- Centralize route and topology state behind Session Spine.
- Add a logical Vault connection registry.
- Track transport, trust, authentication, and projection state independently.
- Reuse the durable outbox as the mutation source.
- Add a projection journal only if outbox retention cannot support cursor repair.
- Implement snapshot plus delta reduction, duplicate handling, ordering checks, gap detection, and repair.
- Separate device-local, user-private, and shared state.

**Gate:** Projection continuity survives frontend reload and backend restart without treating the process-local bus as durable truth.

### Stage 7: Multi-Vault read-only connection

- Introduce signed Vault descriptors.
- Define key pinning and rotation posture.
- Implement connection registry and remote summary fetch.
- Use qualified resource references.
- Compose authorized projections.
- Label stale and expired data.
- Establish remote cache, egress, and SSRF boundaries.

**Gate:** Two independent Vaults can display authorized remote summaries while hidden resources remain absent from payloads.

### Stage 8: Cross-Vault Room synchronization

- Resolve or receive a Room reference.
- Authenticate and submit a join request.
- Evaluate admission and issue scoped grants.
- Fetch a Room snapshot and subscribe from a cursor.
- Submit idempotent message and artifact intents.
- Let the authoritative host assign canonical order.
- Recover after disconnect.
- Revoke and tombstone access.
- Fail closed when policy state is uncertain.

Begin read-only, then add posting.

**Gate:** A participant on one Vault can join a Room hosted on another, reconnect after restart, resume from a cursor, post exactly once, and lose access after revocation.

### Stage 9: Publication and Galaxy discovery

- Add explicit publication records.
- Emit signed discovery summaries with expiry and supersession.
- Allow optional untrusted relays or indexes without making them identity authorities.
- Keep archetypes separate from live records.
- Feed Atlas, Galaxy, search, and list views from the same neutral projection.
- Add public abuse and rate-limit policy.

**Gate:** Relays may disappear without breaking local or directly known relationships.

### Stage 10: Capability endpoints

- Add governed AI, repository, and bounded compute endpoints.
- Advertise capabilities.
- Invoke through governed command or capability lanes.
- Preserve execution receipts and artifact lineage.
- Prevent identity ownership and remote auto-installation.

**Gate:** Capability use is permissioned, attributable, receipt-bearing, and isolated from HomeBase identity.

### Stage 11: Supported-path hardening

- Validate large topology performance.
- Add incremental rendering.
- Deliver mobile list-first behavior.
- Complete keyboard and screen-reader navigation.
- Define encrypted or ephemeral remote cache policy.
- Handle key rotation and trust change.
- Add federation diagnostics and policy-version observability.
- Build a two-Vault live test harness.
- Complete security review.
- Update release profile and current-state truth only after fresh proof lands on `main`.

**Gate:** Supported-profile, health, mounted routes, documentation, and live two-Vault behavior agree.

## Proof Surface

| Proof class | Required evidence |
| --- | --- |
| Contract | Python and TypeScript fixtures encode and decode identically |
| Authorization | Matrix across HomeBase, Space, Room, Conversation, Project, and Artifact scopes |
| Privacy | Hidden existence, names, counts, and activity do not leak |
| Migration | Clean-start, existing-instance, archived snapshot, downgrade and re-upgrade where supported |
| Export and restore | Stable external IDs, grants, relationships, and provenance survive remapping |
| Reducer | Duplicate, out-of-order, replay, cursor gap, and snapshot replacement cases |
| Restart | Projection continuity after client, broker, or remote Vault restart |
| Network failure | Stale labeling and recovery after disconnect |
| Revocation | Writes fail immediately and stale projections cannot authorize |
| Identity | URL change does not alter Vault identity; key change becomes an explicit trust event |
| UI | Spatial and accessible list views expose equivalent authorized information |
| Injection | Remote manifests cannot inject code, CSS, routes, or arbitrary presentation tokens |
| Release | Supported profile, health, routes, and live proof agree before claims widen |

## ADR and Documentation Impact

### Classification

This plan requires a future ADR.

Recommended ADR scope:

> ThreadSpace Multi-Vault Authority, Projection, and Synchronization Contract

Atlas and Galaxy visual design should remain in subordinate UI specifications so rendering can evolve without redefining system authority.

### Governing material

Future ADR work should reconcile and align with:

- operator and user access boundaries
- Network Profile topology resolution
- VaultNode canonical machine and audit authority
- account export and restore
- canonical token philosophy
- current event and sync semantics
- AppShell and Workspace UI canon
- federation and peer-context boundaries
- self-extending plugin governance

### Documentation follow-through

This blueprint does not update:

- `docs/architecture/00-current-state.md`
- the ADR index
- the architecture README routing map
- runtime diagrams
- UI diagrams
- supported-profile claims

Those updates must occur only in the appropriate future atomic task and only when their truth conditions are satisfied.

## Open Questions

1. What exact stable identity and key model should define `vaultId`?
2. Which existing ADR numbers and names collide with the proposed ThreadSpace umbrella contract?
3. Can `events_outbox` retention and cursor behavior support projection repair, or is a downstream journal required?
4. Which current collaboration permission structures can be reused safely for Room grants?
5. How should Network Profile linkage prove user control across Vault accounts?
6. What is the minimum HomeBase export and migration contract?
7. Which remote summary fields may be cached by a Home Vault, and for how long?
8. What admission policies are required for public, invite-only, request-to-join, and private Spaces?
9. Which capability endpoint classes belong in the first supported implementation?
10. What exact fallback representation should appear when a local client does not recognize a Space renderer?
11. Should Public Pavilion remain permanently a publication projection, or later become a Space-shaped interface over publication records?
12. What is the correct transition path from legacy Threadspace terminology to the new ThreadSpace network plane without reviving quarantined architecture?

## Bottom Line

The product direction remains intact:

- Codexify instances are Vaults.
- ThreadSpace is the network plane between them.
- HomeBase is the user's portable personal network namespace.
- Spaces are interactive community or application containers.
- Rooms are bounded collaboration contexts.
- Atlas provides local and directly known network orientation.
- Galaxy provides broader discovery.
- One frontend may represent access to multiple Vaults.
- Local and cloud AI remain provider-independent capability choices.
- Joining one area must not reveal unrelated private areas.

The refined sequence places authority, identity, disclosure, synchronization, portability, and proof beneath the visual experience. The constellation remains. The ceiling is no longer painted.