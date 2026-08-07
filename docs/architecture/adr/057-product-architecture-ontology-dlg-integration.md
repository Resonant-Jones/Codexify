# ADR-057: Product Architecture Ontology as a Document Lifecycle Graph Extension

## Status

Proposed.

## Date

2026-08-07

## Acceptance

- Proposed: 2026-08-07
- Human approval: Pending

## Context

Codexify needs a durable way to describe which product program a document or subsystem concerns, which shared platform capabilities it uses or provides, which client surfaces present it, which adapter families connect it to external systems, which dependency directions are permitted, what its current support/ownership/integration/strategic posture is, which architecture relationships currently hold between stable concepts, what authority and evidence support those relationships, and how those relationships have changed over repository history.

A prior product-lane proposal attempted to solve this with an independently maintained `product-lane-registry.toml`. That would create a second machine-readable architecture truth surface beside the accepted Document Lifecycle Graph (DLG), current-state documentation, ADRs, source code, and proof records.

This ADR proposes replacing that design with the Product Architecture Ontology: a versioned vocabulary and assertion layer that would extend the accepted DLG rather than compete with it.

## Decision

### 1. Product Architecture Ontology is a DLG extension

The Product Architecture Ontology is a machine-readable vocabulary defining:

- Stable concept identities (programs, capabilities, clients, adapters, source subsystems).
- Concept types, descriptions, and boundaries.
- Typed relationship predicates and their allowed subject/object types.
- Allowed and forbidden dependency directions.
- Derived projection rules and assertion semantics.

It does not encode current posture, current relationship instances, repository path mappings, or current runtime support. Those remain temporal and evidence-backed.

### 2. DLG remains canonical for document identity and lifecycle

The DLG is canonical for document identity, paths, authority, lifecycle, freshness, disposition, evidence classification, supersession, contradiction, retrieval policy, source selection, and Agent Reading Packets.

Upon acceptance of this ADR, the Product Architecture Ontology would become canonical only for product-program vocabulary, platform-program vocabulary, shared-capability vocabulary, client-surface vocabulary, adapter-family vocabulary, source-subsystem identity pattern, product-architecture relation vocabulary, relationship semantics, dependency-direction doctrine, assertion semantics, and derived product-lane projection rules.

Upon acceptance of this ADR, the Product Architecture Assertion layer would become canonical for reviewed architecture claims such as current posture, current architecture participation, architecture relationship instances, ownership state, integration state, strategy state, and temporal relationship validity.

### 3. Stable concept identity is path-independent

Stable concept IDs use these patterns:

- Product or platform program: `codexify:program:<slug>`
- Shared capability: `codexify:capability:<slug>`
- Client surface: `codexify:client:<slug>`
- Adapter family: `codexify:adapter:<slug>`
- Future source subsystem: `codexify:source:<domain>:<slug>`
- Product-architecture assertion: `codexify:assertion:product-architecture:<stable-id>`

Concept identity must not depend on repository path. Moving code must not change concept identity. Changing current support posture must not change concept identity. Renaming requires an alias or explicit replacement. Merging or splitting requires explicit derivation and supersession lineage.

### 4. Programs are classified, not clients

Five stable programs are defined:

- `codexify:program:digital-cognitive-workspace` — product program
- `codexify:program:node-runtime` — platform program
- `codexify:program:threadspace` — product and network program
- `codexify:program:home-presence` — product and physical-interface program
- `codexify:program:infrastructure-services` — infrastructure program

Clients are a separate architecture concept type. "Clients and Interfaces" is not a product program.

### 5. Shared capabilities are reusable

Ten canonical capabilities are defined, including Identity, Authorization and Policy, Context Retrieval and Assembly, Continuity, Semantic Spaces, Delegation and Coordination, Persistence, Runtime Lifecycle, Events/Receipts/Observability, and Provider/Tool Adapter Interfaces.

Capabilities may support multiple programs and expose contracts consumed by multiple programs. They must not depend directly on product-specific UI implementations.

### 6. Client surfaces do not own identity

Six client surfaces are defined: Web, Desktop, Browser Extension, Browser Host, Mobile, Home Device. Clients may present programs but do not own Codexify user identity, canonical persistence, or policy authority.

### 7. Adapter families connect, not govern

Ten adapter families are defined, including OpenAI-compatible inference, Codex execution, Claude-compatible inference, Local Inference, DeepSeek, Whoosh'd, external agent runtimes, external tools, storage, and networking.

Provider-specific integrations are adapters, not identity authorities. Codexify-native authentication remains distinct from provider authorization. Codex execution is an optional execution lane, not a mandatory product dependency.

### 8. Posture and relationships are temporal assertions

Current posture (support, runtime, ownership, strategy, integration) and current architecture relationship instances are represented through temporal, evidence-backed Product Architecture Assertions. These assertions reference authority and evidence through DLG document identities.

Posture assertions use orthogonal dimensions: support posture, runtime participation, ownership state, strategy state, and integration state. `unowned` and `entangled` are ownership warnings, not maturity statuses.

Relationship assertions use typed predicates such as `depends_on_capability`, `presented_through`, `integrates_via`, `supports_program`, `participates_in`, `provides_capability`, `implemented_by`, `bounded_by`, and `classified_by`.

### 9. DLG document identity is the sole ADR/contract identity domain

All governing ADRs, contracts, proofs, and authority sources are referenced through DLG document identities (e.g., `codexify:doc:adr:056-document-lifecycle-graph`). No separate `codexify:adr:*` or `codexify:contract:*` identity namespace is introduced.

### 10. Flat labels are derived, not canonical

Labels like `current_core`, `current_support`, `active_optional`, `strategic_parked`, `experimental`, and `historical` are deterministic derived projections from posture assertions. They are never canonical source assertions.

### 11. Generated projections are derived and rebuildable

Future product-lane registries, graph views, and planning projections (Now, Next, Observatory) must be generated from DLG records, ontology concepts, accepted posture assertions, accepted relationship assertions, and current-state authority. They must not be hand-maintained or independently canonical.

### 12. Dependency direction is explicit

Allowed directions include: client → program contract, product program → capability contract, platform program → capability implementation, capability → adapter interface, adapter → external system, infrastructure → support contract, source subsystem → governing documents.

Forbidden directions include: capability → product-specific UI, adapter → identity authority, provider account → Codexify identity, client → persistence/policy authority, hosted service → hidden ThreadSpace authority, repository path presence → support claim, vector similarity → canonical relation.

### 13. Codexify remains a modular monorepo

Product and platform boundaries will be formalized before any repository splitting. Concept identity is path-independent, so future splits remain possible. No source movement is performed by this ADR.

### 14. Ontology status is proposed

The Product Architecture Ontology is proposed pending human review and acceptance. It does not change runtime behavior, release posture, or current-state truth. `00-current-state.md` remains release authority. No runtime, persistence, migration, Compose, provider, or source-layout behavior changes.

## Governing ADRs and alignment

This ADR aligns with:

- **ADR-056** (Document Lifecycle Graph Control Plane): The ontology extends the DLG without duplicating it.
- **ADR-046** (Axis Node Portable Reasoning Interface Contract): Axis Node provides source-oriented reasoning; the ontology adds product-architecture vocabulary.
- **ADR-005** (Runtime Mode and Account Boundary Invariants): Codexify-native identity remains distinct from provider authorization.
- **ADR-048** (Guardian Three-Channel Delegation Topology): Adapter families for Pi, Codex, and Claude remain peer execution channels under Guardian.
- **ADR-054** (Browser Host Topology and Release Ownership): Browser Host is a client surface, not an identity or policy authority.
- **ADR-053** (Node-Hosted Room Access Boundary): ThreadSpace authority boundaries are preserved; hosted services do not become hidden central authority.
- **ADR-042** (Canonical Audit Evidence Contract): Evidence classification and proof semantics remain in the audit domain.
- **ADR-041** (VaultNode Canonical Machine and Audit Authority): Machine and audit authority are unchanged.
- **ADR-039** (Operator/User Access Boundary): Operator/user distinctions remain governed by their respective ADRs.
- **ADR-055** (ThreadSpace ↔ WhisperMesh Managed-Service Boundary): Infrastructure service boundaries remain sovereign.

All governing ADRs and contracts referenced by the ontology and assertions use DLG document identities.

## Explicitly deferred work

- DLG corpus inventory
- Source-subsystem inventory
- Repository path classification
- Current product-priority assertions
- Accepted posture assertion set
- Accepted relationship assertion corpus
- Current primary-lane projection
- Product-lane registry generation
- Product map generation
- Relationship-history materialization
- Dependency linting and CI enforcement
- Graph query tooling
- Neo4j/Postgres/vector projections
- Agent Reading Packet generation code
- Axis harness loading
- Source-directory moves
- Import changes, runtime refactors, product activation
- Current-state updates

## Non-goals

- No independent TOML registry
- No full product-lane map
- No repository-wide classification
- No source-subsystem record corpus
- No current architecture relationship corpus
- No runtime behavior change
- No API route, worker, queue, migration, database schema, Compose change, provider change, auth change
- No browser, ThreadSpace, Home Presence, hosted-service, or client implementation
- No code movement, repository split, or generated backlog
- No release claim or automatic architecture approval
- No parallel ADR or contract identity domain

## Consequences

### Positive

- If ADR-057 is accepted, stable product vocabulary will exist independently of repository layout.
- Product posture and architecture relationships are explicit, temporal, and evidence-backed.
- DLG remains the single document identity and lifecycle authority.
- No second machine-readable truth store competes with the DLG.
- Concept identity survives code movement and priority changes.
- Dependency direction is explicit and testable.
- Future source mapping, product-lane generation, and agent context are scaffolded.

### Negative

- Two new schemas and an ontology vocabulary require maintenance.
- Assertion records add a new review surface.
- The separation of ontology (what things are) from assertions (what is currently true) requires discipline.
- No current relationship corpus exists yet; the ontology feels incomplete without it.

### Neutral

- Runtime behavior is unchanged.
- Repository layout is unchanged.
- Current release claims are unchanged.
- Axis Node and existing ADRs retain their authority.
