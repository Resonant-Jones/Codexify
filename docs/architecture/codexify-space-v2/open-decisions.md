# Codexify.Space v2 Open Decisions

**Status:** Architecture decision register  
**Purpose:** Keep unresolved product and protocol questions visible before implementation turns them into accidental doctrine.

## Decision classes

Use these classifications:

- **Required before ADR:** must close before the governing ADR is accepted.
- **Required before migration:** may remain open during doctrine work but must close before schema changes.
- **Required before synchronization proof:** must close before World Packet implementation or two-node testing.
- **Deferred program:** intentionally outside the initial architecture program.

## D-001: HomeBase cardinality

**Class:** Required before ADR  
**Question:** Does one canonical User identity own exactly one HomeBase, while Organizations own separate organization HomeBases?  
**Current leaning:** Yes. Avoid the original many-Homes-per-user model that makes personal identity resemble ownership of a small municipality. Use Spaces for multiple experiences under one sovereign root.  
**Must prove:** account migration, organization membership, delegated administration, export and restore.

## D-002: Node authority

**Class:** Required before ADR  
**Question:** Can multiple Nodes serve one HomeBase, and which Node may issue canonical writes when more than one is online?  
**Current leaning:** Multiple Nodes may serve one HomeBase, but write authority must be explicit and conflict-safe. Execution location does not imply identity authority.  
**Must prove:** failover, stale Node behavior, revocation, key rotation, and split-brain handling.

## D-003: Space persistence

**Class:** Required before migration  
**Question:** Which Space properties require first-class durable tables, and which remain versioned manifests or projections?  
**Current leaning:** Persist identity, ownership, lifecycle, visibility, and policy references. Keep renderer hints and presentation metadata versioned and replaceable.  
**Must prove:** deterministic export, restore, manifest rebuild, and backward-compatible renderer negotiation.

## D-004: Room-to-Project cardinality

**Class:** Required before migration  
**Question:** Is a Room backed by exactly one Project in the first implementation?  
**Current leaning:** Yes. One authoritative Project per Room keeps disclosure, mutation, deletion, and lineage comprehensible. Multi-Project Rooms should be a later explicit design.  
**Must prove:** Room deletion without Project deletion, selective disclosure, Room-originated Project mutation, and complete lineage.

## D-005: Project-to-Room cardinality

**Class:** Required before migration  
**Question:** May one Project publish multiple Rooms with different disclosure policies?  
**Current leaning:** Yes, provided each Room has independent policy, membership, and projection versioning.  
**Must prove:** no cross-Room leakage and independent revocation.

## D-006: Thread membership

**Class:** Required before synchronization proof  
**Question:** Does Room membership automatically allow participation in every visible Thread?  
**Current leaning:** No. Room discovery and Thread read, post, create, moderate, and invite capabilities should remain separable.  
**Must prove:** effective capability inspection and denial receipts.

## D-007: World Packet boundaries

**Class:** Required before synchronization proof  
**Question:** Is a World Packet scoped to a Space, Room, participant, session, or some combination?  
**Current leaning:** Packets should always identify HomeBase and Space scope, and normally be participant-specific and Room-specific when carrying private collaboration state. Public discovery packets may be broader and read-only.  
**Must prove:** no undisclosed content, deterministic filtering, replay safety, and revocation.

## D-008: JSONL segmentation

**Class:** Required before synchronization proof  
**Question:** How are JSONL event segments bounded, rotated, named, compressed, signed, and garbage-collected?  
**Current leaning:** Use immutable bounded segments with explicit cursors, hashes, schema versions, and snapshot checkpoints. Do not depend on one indefinitely growing file.  
**Must prove:** gap detection, resume, replay, corruption quarantine, and repair.

## D-009: Ordering and conflicts

**Class:** Required before synchronization proof  
**Question:** Which operations require total ordering, and which can use causal or per-aggregate ordering?  
**Current leaning:** Preserve canonical ordering per aggregate or authority stream. Avoid pretending federation has one global clock.  
**Must prove:** concurrent posts, edits, deletes, membership changes, policy changes, and offline reconciliation.

## D-010: Atlas renderer contract

**Class:** Required before synchronization proof  
**Question:** What minimum reduced state can every compatible Atlas renderer rely on?  
**Current leaning:** Define a stable topology and resource projection independent of coordinates, animation, layout engine, or visual theme. Spatial placement remains client-local unless deliberately published.  
**Must prove:** equivalent spatial and flat views, deterministic IDs, accessibility, and stale-state labeling.

## D-011: Space renderer extensibility

**Class:** Required before synchronization proof  
**Question:** Are Spaces rendered by built-in typed clients, declarative manifests, sandboxed plugins, hosted web applications, or several negotiated modes?  
**Current leaning:** Begin with built-in typed renderers and declarative manifests. Do not execute arbitrary remote code in the first protocol.  
**Must prove:** renderer compatibility, isolation, fallback behavior, and unsupported-version handling.

## D-012: Discovery record

**Class:** Required before federation  
**Question:** What public metadata may a HomeBase or Space publish for discovery?  
**Current leaning:** Use a bounded signed record containing identity, title, description, categories, public endpoints, availability, join posture, protocol capabilities, and intentionally published geographic hints.  
**Must prove:** provenance, freshness, removal, abuse handling, and no private identifier leakage.

## D-013: Trust and digital villages

**Class:** Required before federation  
**Question:** What does village membership assert, and what authority does a village gain over members?  
**Current leaning:** Membership asserts a voluntary relationship and shared discovery or moderation policy. A village must not gain ambient access to member HomeBases.  
**Must prove:** joining, leaving, moderation, disputes, member revocation, and independent operation.

## D-014: Codexify.Space dependency

**Class:** Required before federation  
**Question:** Which functions remain possible when Codexify.Space is unavailable?  
**Current leaning:** Local use, direct invitations, known-peer connections, Room rendering, and previously authorized synchronization should continue. Discovery and relay may degrade.  
**Must prove:** local-first continuity and clean recovery after coordination-layer outages.

## D-015: Presence

**Class:** Required before synchronization proof  
**Question:** Is participant presence durable history, ephemeral operational state, or both through separate records?  
**Current leaning:** Live presence is ephemeral. Meaningful joins, leaves, acknowledgements, and moderation actions may produce durable receipts.  
**Must prove:** no Redis state promoted to durable truth and no false online claims after disconnect.

## D-016: Public Pavilion

**Class:** Required before federation  
**Question:** Is a Public Pavilion a Space type, a publication projection, or both?  
**Current leaning:** Treat it as a Space experience backed by explicitly versioned public projections. Never mount the private Vault directly.  
**Must prove:** redaction, lineage, withdrawal, versioning, and private-path isolation.

## D-017: Geographic discovery

**Class:** Required before federation  
**Question:** How precise may location metadata be for nearby businesses, services, and Nodes?  
**Current leaning:** Publication must be explicit, coarse by default, purpose-bound, and independently revocable. Personal Nodes should never leak precise location merely by being discoverable.  
**Must prove:** consent, precision controls, indexing removal, and abuse resistance.

## D-018: Search authority

**Class:** Required before federation  
**Question:** Does Federated Atlas search query a central index, peer indexes, live Nodes, or a hybrid?  
**Current leaning:** Support a hybrid model with clear provenance and freshness labels. Indexed metadata must not masquerade as authenticated live remote state.  
**Must prove:** result provenance, stale detection, ranking transparency, removal, and degraded operation.

## D-019: Commerce

**Class:** Deferred program  
**Question:** How should offers, acceptance, payment, fulfillment, refunds, and disputes work across HomeBases?  
**Current leaning:** Do not answer inside the initial Space runtime. Create a separate architecture program after identity, receipts, federation, and capability boundaries are proven.  
**Must prove later:** legal and payment-provider boundaries, fraud handling, receipts, dispute evidence, and no ambient financial authority.

## D-020: Governance and authorship

**Class:** Required before ADR  
**Question:** How are Zac's originating concepts and subsequent production translations recorded?  
**Current leaning:** Maintain a design-lineage ledger and phase review receipts. Record preserved behavior, changed behavior, reason, feedback, and evidence without making safety or runtime truth subject to ceremonial approval.  
**Must prove:** every architecture-impacting phase has a visible translation record.

## Closure protocol

A decision closes only when it has:

1. a written decision;
2. governing rationale;
3. affected invariants;
4. rejected alternatives;
5. proof requirements;
6. documentation follow-through;
7. ADR linkage when contract-bearing;
8. review status and evidence reference.

Do not close decisions by silently encoding them in migrations, UI components, packet fields, or worker behavior.