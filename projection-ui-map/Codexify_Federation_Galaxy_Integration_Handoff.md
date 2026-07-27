# Codexify Federation Galaxy Integration Handoff

**Source shard:** NZ + Florida Federation Galaxy prototype discussion
**Date:** 2026-07-15
**Status:** Prototype concept validated; native Codexify integration requested; implementation plan not yet finalized
**Primary instruction from this shard:** **This needs to be integrated into Codexify.**

---

## 1. Purpose of this handoff

This document consolidates the important product, architecture, interaction, and implementation signals from this conversation shard so it can be merged with handoffs from the other parallel discussions.

Use it as an evidence packet, not as a final specification. It separates:

- **Observed implementation** — what the current prototype visibly does.
- **Confirmed direction** — what was explicitly accepted or requested in this thread.
- **Working theory** — integration ideas that still require reconciliation with the other handoffs and the live Codexify codebase.
- **Open questions** — decisions the consolidated analysis must resolve.

The central result of this shard is that the prototype crossed from “illustrative diagram” into a credible interface model for Codexify’s underlying sovereignty, provenance, identity, publication, and federation architecture.

---

## 2. Executive summary

The prototype presents Codexify at two connected scales:

1. **Local Federation / Atlas** — a repo-backed operational workspace containing Homes, Rooms, documents, chat, provenance, public/private boundaries, source control, and bounded compute.
2. **Federation Galaxy** — a separate full-screen map showing the local federation in relation to grounded institutional and community federation archetypes across Aotearoa New Zealand and Florida.

The important design achievement is not merely the visual galaxy. The interface makes distinct authorities legible:

- a source-of-truth Home,
- an agent interpretation Home,
- a collaborator/reviewer Home,
- a Public Pavilion for deliberate publication,
- a source-control node,
- and a bounded compute node.

The graph therefore communicates that identity, interpretation, review, publication, code, and compute are **separate domains with explicit relationships**, rather than one application silently owning everything.

The galaxy view then extends the same grammar outward. It demonstrates how a local Codexify federation could connect to other federations without pretending the prototype contains real partnerships. The persistent disclaimer — “Archetype cards only — grounded reasoning, no actual leads” — is an important epistemic and commercial boundary and should remain part of the integrated product/demo experience.

**Integration thesis:** This should become a native Codexify subsystem, not remain a disconnected static demo. Atlas, Federation, and Galaxy should resolve to the same underlying entities, permissions, events, and provenance data.

---

## 3. What exists now — observed implementation

### 3.1 Prototype container

- Current artifact is a local HTML prototype: `codexify_space_nz_florida_no_autoboot.html`.
- The UI identifies itself as **Codexify.Space — Repo implemented**.
- It loads `codexify_space_draft.zip` and exposes real or repo-derived files, rooms, indexes, provenance receipts, and archive summaries.
- The prototype is interactive rather than a static mockup.

### 3.2 Local Federation / Atlas surface

The local Atlas contains six visible Homes/nodes:

| Home / node | Role | Visible repo-file count |
|---|---|---:|
| Zac Home | Actual uploaded repo; local source-of-truth Home | 41 |
| Luna Home | Agent interpretation layer | 12 |
| Chris Home | Review collaborator | 2 |
| Public Pavilion | Actual public-vault / public projection | 9 |
| Cloud Training Node | Rented, bounded compute | 2 |
| Codexify Repo | Source-control node | 3 |

The Atlas surface includes:

- directional graph relationships,
- a vault/file index,
- Rooms,
- Chat,
- document inspection,
- file-linked messages,
- public/private/shared/linked visibility labels,
- customization controls for card accent and glow,
- and a user identity indicator showing Luna logged into a participant vault.

### 3.3 Repo-backed room model

Zac Home reports **41 files, 6 rooms, and 120 messages**. Its visible rooms are:

- Home Overview
- Chris Review Room
- Public Studio
- Archive Processing Room
- Provenance & Sharing
- Private Workspace

Other visible Rooms include Luna’s Repo Review and Boundary Review, Chris’s Review Notes, Public Pavilion publication rooms, Cloud Repo Extraction, and Repo Source Control.

The Chris Review Room demonstrates the intended interaction model:

- conversation remains conversational,
- source files remain separately inspectable,
- messages can link directly to repo documents,
- room visibility is explicit,
- and boundary decisions can be represented inside the room.

A key demonstrated rule is:

> Only Public Pavilion material is eligible for Codexify.Space sync by default.

That rule captures the desired private-to-public projection boundary in a single operational sentence.

### 3.4 Provenance and publication artifacts

The prototype exposes:

- `manifest.yaml`, `home.md`, and `world.jsonl`,
- Atlas room metadata,
- private-vault and public-vault structures,
- provenance JSON receipts for published documents,
- privacy audit and classification reports,
- publication candidates,
- manual-review-required artifacts,
- archive indexes,
- and scripts such as `parse_merged.py`.

The provenance layer is not decorative. It is used to explain where public material came from and why it is eligible for publication.

### 3.5 Demonstrated event lifecycle

The page includes a sequence of events that already resembles a useful canonical lifecycle:

1. Zac shares public documents.
2. Public Pavilion returns publication receipts.
3. Zac grants Luna read access.
4. Luna sends room summaries back.
5. Zac shares a review room with Chris.
6. Chris sends design feedback.
7. The project is linked to the repo.
8. Zac pushes vault and Atlas changes.
9. The repo exposes scripts for compute.
10. Cloud writes build artifacts.
11. The cloud node uses repo data for compute.
12. Zac sends a bounded compute job.
13. Chris can view Public Pavilion documents.
14. Luna proposes public summaries.

This should be treated as a seed for an actual event/receipt contract, not merely demo copy.

### 3.6 Federation Galaxy surface

The Galaxy is entered as a **separate full-screen map** from the local Federation. It includes:

- a return-to-local-federation action,
- pan controls,
- zoom controls,
- selectable cards,
- relationship lines and orbit/category regions,
- a persistent details panel,
- “Why this card exists” rationale,
- representative participant archetypes,
- and an explicit lead-boundary disclaimer.

The visible galaxy contains:

- **1 local Codexify/Luna federation core**,
- **10 Aotearoa New Zealand federation archetypes**, and
- **12 Florida federation archetypes**.

The archetypes span data sovereignty, research, archives, care and consent, emergency/civic coordination, environmental monitoring, libraries, universities, healthcare, ports, maker labs, small-business continuity, and neighborhood adaptation.

The selected-card panel can expose region, relationship type, fit, Homes, Rooms, public documents, status, rationale, and representative participants. For example, the Regional Consents Evidence archetype shows a strong adjacent network with 20 Homes, 66 Rooms, 92 public documents, and a status of publishing decision receipts.

---

## 4. Core product vocabulary established by the prototype

### Home

A sovereign or bounded participant container with its own authority, vault, rooms, documents, events, and publication policy. A Home may represent a person, agent, collaborator, institution, public projection, repository, or compute participant, but those types must remain explicit.

### Room

A scoped collaboration and disclosure boundary. A Room contains messages, linked files, participants, visibility rules, and boundary decisions. Rooms are not merely chat channels; they are permissioned operational contexts.

### Public Pavilion

A deliberate public projection layer. It receives curated material from local Homes, creates or returns publication receipts, and prevents private Home state from being silently synchronized to public infrastructure.

### Repo Node

A source-control authority linked to, but not identical with, a Home. It exposes versioned source and scripts while preserving the distinction between code history and personal/organizational memory.

### Compute Node

A bounded execution participant. It receives explicit jobs and approved inputs, writes artifacts or receipts, and does not become the owner of the originating Home or its identity.

### Federation

A graph of Homes/nodes that cooperate under explicit relationships, permissions, and provenance. The local Federation is an operational trust topology, not a decorative network diagram.

### Galaxy

A higher-order navigation and discovery surface for multiple Federations or federation archetypes. It should expose relationships and fit without flattening all participants into one centrally owned graph.

### Receipt / event

A durable record of access, publication, sharing, compute, review, or transformation. Receipts make the graph explainable over time and provide a foundation for audit, provenance, rollback, and trust.

---

## 5. Why this matters to Codexify

### 5.1 It renders the architecture as an interface

The UI makes abstract principles visible and inspectable. A user can see where the source lives, who can interpret it, what is shared, what is published, where code resides, and where compute occurs.

### 5.2 It protects identity boundaries

The prototype does not imply that Luna owns Zac’s Home, that the Public Pavilion owns the private vault, or that cloud compute owns the data it processes. Personas and services participate through bounded relationships.

### 5.3 It makes provenance a normal product interaction

Files, messages, rooms, publication receipts, and source-control changes are linked instead of collapsed into a single opaque feed. This supports Codexify’s larger goal of traceable, user-owned continuity.

### 5.4 It creates a coherent multi-scale navigation model

The user can move from:

- galaxy,
- to federation,
- to Home,
- to Room,
- to message or document,
- to provenance receipt or raw event.

That is a plausible information architecture for Codexify itself.

### 5.5 It communicates product-market shapes without fabricating customers

The institutional archetypes are grounded enough to demonstrate relevance while the lead-boundary language prevents the demo from masquerading as a partnership pipeline.

### 5.6 It gives Codexify a distinct visual and conceptual language

The “galaxy” metaphor works because it resolves into operational implementation. It is not merely cosmic decoration; it provides a map of authority, relation, and disclosure.

---

## 6. Confirmed direction from this thread

The following should be treated as confirmed for the merge analysis:

1. **The prototype is valuable enough to integrate into Codexify.**
2. **The local Federation and Galaxy belong to one product model.**
3. **The Galaxy should remain a distinct, full-screen navigation context rather than being squeezed into the ordinary Atlas canvas.**
4. **Repo-backed Homes, Rooms, files, chat, and provenance are the credibility anchor.**
5. **Public/private projection must remain explicit.**
6. **Source Home, agent interpretation, collaborator review, public projection, source control, and compute must remain separate authorities.**
7. **Archetype cards must remain clearly labeled as archetypes, not actual leads or partnerships.**
8. **The integrated version should preserve inspectability rather than becoming a purely visual marketing layer.**

---

## 7. Candidate integration target — working theory

This is a proposed framing for synthesis with the other handoffs, not a final decision.

Codexify should gain a first-class **Atlas / Federation / Galaxy subsystem** backed by the same canonical graph and event data.

### Atlas

The local operational view of Homes, Rooms, files, conversations, permissions, and active relationships.

### Federation

The trust and exchange model connecting local Homes/nodes through explicit relationship contracts.

### Galaxy

The higher-order map of known, discoverable, simulated, or archetypal Federations. It should consume real Federation summaries when available and clearly mark simulated/archetype entries.

The prototype should not be integrated by embedding the current HTML wholesale. Its behaviors and visual grammar should be reimplemented against Codexify’s real routing, identity, storage, graph, event, and permission layers.

---

## 8. Proposed phased integration plan

### Phase 0 — Consolidate and freeze the prototype contract

- Collect all six conversation handoffs.
- Inventory the current HTML, ZIP, screenshots, repo schema, and generated sample data.
- Record which behaviors are functional, mocked, or hard-coded.
- Reconcile the visible local count discrepancy: the Galaxy core card says 8 Homes while the local Atlas currently shows 6 visible Homes/nodes.
- Freeze a reference build and screenshot set before refactoring.

**Exit criterion:** one agreed inventory of existing behavior and one authoritative list of confirmed product decisions.

### Phase 1 — Define canonical entities and boundaries

Define stable contracts for:

- Home
- Home type / authority type
- Room
- Participant and role
- Document / attachment
- Visibility and disclosure policy
- Public projection
- Node
- Relationship / edge
- Federation
- Galaxy entry
- Event
- Receipt
- Compute job and artifact
- Provenance chain

The contract must identify the source of truth for every field and distinguish actual runtime data from demo/archetype metadata.

**Exit criterion:** versioned schemas and explicit authority rules.

### Phase 2 — Integrate the local Atlas first

- Rebuild the local Atlas inside the Codexify application shell.
- Connect Homes and Rooms to real project/vault data.
- Preserve file inspection and room-linked conversations.
- Implement visibility badges from actual policy data.
- Make graph edges inspectable and explain why each relationship exists.
- Keep the interface useful without the Galaxy enabled.

**Exit criterion:** the repo-backed local Federation works natively in Codexify.

### Phase 3 — Formalize sharing, publication, and receipts

- Implement Public Pavilion as an actual projection workflow.
- Require explicit publication candidates and approval state.
- Generate publication receipts.
- Track read grants, room shares, review decisions, transformations, and revocations.
- Ensure public sync cannot traverse into private Home state by default.

**Exit criterion:** the core private-to-public boundary is enforced by code, not just copy.

### Phase 4 — Formalize repo and bounded-compute nodes

- Link repository state through a source-control adapter.
- Define compute-job manifests, approved inputs, outputs, status, and receipts.
- Prevent compute providers from being treated as identity authorities.
- Surface artifacts and failures in Rooms/Atlas without importing provider ownership semantics.

**Exit criterion:** repo and compute relationships are operational and auditable.

### Phase 5 — Add Federation summaries

- Produce a compact, privacy-preserving Federation summary from local canonical data.
- Define what may be exposed outside a Federation.
- Include counts, capabilities, status, public endpoints, and relationship offers only when explicitly authorized.
- Support real, local-only, simulated, and archetype Federation modes.

**Exit criterion:** the Galaxy has a safe data contract to consume.

### Phase 6 — Integrate the Galaxy

- Rebuild the full-screen Galaxy as a route/modal state inside Codexify.
- Preserve return-to-local behavior and user viewport state.
- Drive cards and details from Federation summaries/archetype definitions.
- Make category regions, relationship types, and fit criteria data-driven.
- Preserve the explicit archetype/lead disclaimer.
- Add search, filtering, and accessible non-canvas navigation before adding more visual density.

**Exit criterion:** Galaxy navigation is native, data-backed, and clearly distinguishes reality from simulation.

### Phase 7 — Performance, accessibility, and product hardening

- Test large graphs and zoom extremes.
- Add keyboard navigation and screen-reader summaries.
- Resolve inspector/control overlap.
- Improve contrast and avoid clipped card content at high zoom.
- Add responsive layouts.
- Persist layout positions deliberately rather than accidentally.
- Add empty, loading, error, offline, and stale-data states.
- Add telemetry only if it respects local-first and consent boundaries.

**Exit criterion:** the subsystem is stable enough for real projects and public demos.

---

## 9. Draft data model for reconciliation

The consolidated architecture analysis should test a model similar to the following.

### Home

- `home_id`
- `name`
- `home_type`
- `owner_id`
- `authority`
- `node_id`
- `storage_backend`
- `root_uri`
- `default_visibility`
- `public_projection_enabled`
- `status`

### Room

- `room_id`
- `home_id`
- `name`
- `purpose`
- `visibility`
- `participant_roles`
- `linked_resource_ids`
- `policy_id`
- `created_at`
- `archived_at`

### Relationship

- `relationship_id`
- `source_entity_id`
- `target_entity_id`
- `relationship_type`
- `direction`
- `scope`
- `policy_id`
- `status`
- `created_by`
- `created_at`
- `revoked_at`

### Event / receipt

- `event_id`
- `event_type`
- `actor_id`
- `source_id`
- `target_id`
- `room_id`
- `resource_ids`
- `policy_snapshot`
- `timestamp`
- `result`
- `receipt_hash`
- `parent_event_id`

### Federation

- `federation_id`
- `name`
- `mode` — actual, local-only, simulated, archetype
- `home_ids`
- `relationship_ids`
- `public_summary_policy`
- `region`
- `status`
- `summary_version`

### Galaxy entry

- `entry_id`
- `federation_id` or `archetype_id`
- `display_category`
- `relationship_to_local`
- `fit_label`
- `position`
- `public_metrics`
- `rationale`
- `lead_boundary_label`
- `last_verified_at`

This schema is intentionally incomplete. The merge analysis should map it to existing Codexify ontology and storage rather than creating redundant parallel entities.

---

## 10. Product principles that should survive integration

1. **Identity is infrastructure.** A Home’s authority cannot be inferred from visual proximity or delegated implicitly to an agent.
2. **Personas borrow access; they do not own the source identity.**
3. **Public state is a projection, not a mirrored default.**
4. **Every meaningful boundary crossing should be explainable.**
5. **Provenance should be inspectable by ordinary users, not reserved for an audit console.**
6. **Compute is a participant with bounded scope, not a sovereign owner.**
7. **The graph must remain useful when offline or local-only.**
8. **Archetypes and simulations must never be presented as verified external relationships.**
9. **The metaphor must resolve into actual files, policies, events, and permissions.**
10. **The local operational loop takes priority over visual expansion.**

---

## 11. Known inconsistencies and UI issues

These are not conceptual failures, but they should be captured before integration:

- The Codexify/Luna Galaxy card reports **8 Homes**, while the visible local Atlas sidebar currently shows **6 Homes/nodes**.
- Galaxy navigation controls can overlap the details panel and representative-participant content.
- At high zoom, cards and labels can extend beyond the viewport or be partially clipped.
- The light “Why this card exists” and participant panels are visually dominant against the dark Galaxy and may need hierarchy refinement.
- Some card copy becomes unreadable at distant zoom levels; the integrated version needs semantic zoom rather than simple scaling alone.
- The difference between actual runtime metrics and illustrative archetype metrics must remain unmistakable.
- Card-position persistence and graph layout authority are not yet defined.
- Mobile and keyboard interaction behavior are not demonstrated.

---

## 12. Risks and anti-patterns

### Metaphor outruns implementation

The Galaxy becomes a beautiful shell disconnected from real policies, events, and data.

**Countermeasure:** local Atlas and receipt contracts must be integrated first.

### Centralization by convenience

A hosted Galaxy service becomes the hidden owner of Federation identity or relationship truth.

**Countermeasure:** publish only authorized Federation summaries; keep Home authority local.

### Archetype confusion

Viewers infer that example organizations are prospects, customers, or partners.

**Countermeasure:** retain persistent, plain-language archetype and lead-boundary labels.

### Graph ambiguity

Edges look meaningful but have no inspectable policy or lifecycle.

**Countermeasure:** every edge should expose type, scope, authority, status, and receipts.

### Permission drift

A Room or public projection changes while cached Galaxy/Atlas data remains stale.

**Countermeasure:** version summaries and show last verification / stale state.

### Decorative provenance

Receipts exist as files but do not enforce behavior.

**Countermeasure:** publication, sharing, review, and compute workflows should emit receipts as part of successful transactions.

### Visual performance collapse

Large federations become unusable on ordinary hardware.

**Countermeasure:** semantic zoom, clustering, virtualized labels, progressive rendering, and non-visual list navigation.

---

## 13. Open questions for the consolidated analysis

1. Is a Home always a storage boundary, always an identity boundary, or a typed combination of both?
2. Should Public Pavilion be a Home subtype, a projection service, or both?
3. Is Luna’s Home a durable agent Home, a persona-scoped interpretation layer, or a session projection?
4. Which existing Codexify entities already cover Home, Room, Node, Document, Event, and Relationship?
5. Which store is authoritative for topology: relational database, event log, graph database, local vault metadata, or a derived view?
6. How are graph changes proposed, consented to, signed, revoked, and synchronized?
7. What exact information may a local Federation publish to a Galaxy service?
8. Can two Federations connect peer-to-peer without a central directory?
9. How should offline Federations be represented and later reconciled?
10. How are archetype cards authored, versioned, reviewed, and distinguished from actual discovered Federations?
11. What is the minimum viable integrated version: local Atlas only, Atlas plus Public Pavilion, or Atlas plus a read-only Galaxy?
12. Should graph layout be user-owned data, generated UI state, or a hybrid?
13. How do search and natural-language navigation coexist with the visual graph?
14. What permissions does a reviewer Home need to inspect linked files without importing the private source archive?
15. How are compute inputs minimized and proven to be within the approved job boundary?
16. Where should the subsystem live in the current desktop/web routing model?
17. What parts of the prototype are production-worthy code versus generated demonstration code?

---

## 14. Decision ledger

### Confirmed

- Integrate this concept into Codexify.
- Treat the repo-backed local Federation as the operational foundation.
- Preserve distinct authorities for source Home, agent, reviewer, public projection, repo, and compute.
- Preserve explicit public/private boundaries and provenance.
- Keep the Galaxy as a separate full-screen navigation context.
- Keep archetype/lead disclaimers explicit.

### Strongly supported, not yet formally decided

- Make Atlas, Federation, and Galaxy first-class product concepts.
- Use one canonical data model across all three views.
- Promote the demonstrated event feed into a real event/receipt schema.
- Integrate local Atlas before Galaxy.
- Reimplement the prototype inside the application rather than embedding the standalone HTML.

### Unresolved

- Final entity schema and storage authority.
- Federation discovery and handshake protocol.
- Sync topology and hosted-service role.
- MVP scope and sequencing against other Codexify work.
- Final visual implementation stack and graph library.
- Real versus archetype Galaxy content strategy.

---

## 15. Merge-ready summary

| Dimension | Handoff result |
|---|---|
| Core insight | Codexify can be navigated as a hierarchy of Galaxy → Federation → Home → Room → resource/event. |
| Credibility anchor | The prototype resolves into real repo files, rooms, chat, permissions, provenance, source control, and bounded compute. |
| Primary integration request | Make this a native Codexify subsystem. |
| Highest-priority boundary | Private Home state must not silently become public or cloud-owned. |
| Key visual principle | The metaphor is valid only because every layer resolves into implementation. |
| Recommended first build | Native local Atlas plus enforced Public Pavilion and receipts. |
| Recommended later build | Data-backed full-screen Galaxy consuming authorized Federation summaries and explicit archetypes. |
| Major risk | Shipping a visually impressive graph before canonical identity, policy, and event contracts are real. |
| Immediate reconciliation item | Resolve actual versus illustrative data and the 6-versus-8 Home count. |

---

## 16. Artifacts referenced in this shard

- `codexify_space_nz_florida_no_autoboot.html`
- `codexify_space_draft.zip`
- Galaxy overview and zoom screenshots
- Local Atlas screenshot showing Homes, Rooms, graph edges, vault index, and repo-backed state
- Repo-derived files including Home manifests, room metadata, public/private vault documents, provenance receipts, audits, indexes, and parsing scripts

---

## 17. Suggested instruction for the final consolidation pass

Use the following instruction when combining this handoff with the other conversation handoffs:

> Merge all handoffs into one Codexify Federation/Atlas/Galaxy integration plan. Deduplicate repeated ideas, preserve the difference between observed implementation, confirmed decisions, working theories, and open questions, and flag contradictions instead of silently choosing one version. Map the resulting plan to the current Codexify architecture and identify the smallest end-to-end vertical slice that proves local authority, Room-level sharing, Public Pavilion publication, provenance receipts, repo linkage, and bounded compute before expanding the Galaxy. Produce a decision ledger, canonical entity model, phased implementation plan, migration strategy for the current prototype, risk register, and acceptance criteria.

---

## 18. Compact machine-readable handoff block

```yaml
handoff_id: codexify-federation-galaxy-nz-florida-2026-07-15
scope: prototype evaluation and native integration intent
status: concept_validated_integration_requested
confirmed:
  - integrate_into_codexify
  - local_federation_is_operational_foundation
  - galaxy_is_separate_full_screen_context
  - preserve_distinct_identity_interpretation_review_publication_repo_compute_authorities
  - preserve_public_private_projection_boundary
  - preserve_provenance_and_inspectability
  - archetypes_are_not_actual_leads
observed:
  local_visible_homes: 6
  galaxy_core_reported_homes: 8
  zac_home_files: 41
  zac_home_rooms: 6
  zac_home_messages: 120
  aotearoa_archetypes: 10
  florida_archetypes: 12
  local_core_cards: 1
candidate_workstreams:
  - inventory_and_contract_freeze
  - canonical_entity_and_policy_schema
  - native_local_atlas
  - publication_and_receipts
  - repo_and_bounded_compute
  - federation_summary_contract
  - native_galaxy
  - accessibility_performance_hardening
critical_risks:
  - metaphor_without_enforcement
  - centralization_by_convenience
  - archetype_or_lead_confusion
  - graph_edges_without_policy
  - stale_permission_or_summary_state
  - decorative_provenance
  - large_graph_performance
immediate_questions:
  - resolve_6_vs_8_home_count
  - identify_production_vs_mocked_code
  - map_entities_to_existing_codexify_ontology
  - define_source_of_truth_for_topology_and_events
  - choose_minimum_vertical_slice
```
