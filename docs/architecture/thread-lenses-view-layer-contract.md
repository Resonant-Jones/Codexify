# Thread Lenses View-Layer Contract

## Status

Docs-only architecture and product contract. Defines Thread Lenses as a future view-layer concept over the existing thread graph. Does not implement runtime behavior, routes, UI, retrieval changes, migrations, workers, or write paths. Does not move project membership. Does not widen the supported beta release promise.

**Created:** 2026-06-29
**Branch:** `main`

## Purpose

Thread Lenses describe how users may temporarily or persistently reorganize the same underlying threads for discovery and interpretation without changing durable ownership.

A lens is a view over threads, not a container for them. It can change grouping, ordering, and presentation. It must not change project membership, thread ownership, or account boundaries.

This contract exists to separate two different questions:

- "What is the durable home for this thread?"
- "What view helps me rediscover or reinterpret this thread right now?"

Projects answer the first question. Lenses answer the second.

## Core Invariant

Projects are explicit containment.

Lenses are derived or selected views.

A lens may reveal relationships. It must not silently create, delete, or move project membership.

## Scope

Thread Lenses may conceptually group or display threads across the same underlying graph in ways that support rediscovery, navigation, and interpretation.

They may be:

- temporary
- pinned
- saved
- derived from metadata or user selection

They may span projects when the lens definition allows it.

They must not replace the project graph or imply that the project graph is mutable through lens selection.

## Non-Goals

Thread Lenses are not:

- a replacement for Projects
- an automatic project reassignment system
- a cross-user or cross-account semantic grouping system
- an authoritative truth layer for semantic clustering
- a frontend implementation
- a backend retrieval change
- a write path for thread ownership or project membership

## Lens Categories

### Project Lens

A Project Lens groups threads by project membership.

It is a view of existing project containment, not a second project system. It may help users inspect project structure, but it must not move threads between projects.

### Semantic Lens

A Semantic Lens groups threads by topic, theme, or conceptual proximity.

It may use similarity, tagging, or other derived signals, but those signals remain interpretive. A semantic lens must not become authoritative truth about thread meaning or project assignment.

Semantic lenses must remain scoped to the current user or account.

### Persona Lens

A Persona Lens groups threads by the active persona, profile, or context that was in effect when the thread was created or later annotated.

Persona lenses are interpretive overlays. They may help answer which context was active, but they must not claim durable identity ownership or rewrite thread history.

Persona lenses must remain scoped to the current user or account.

### Timeline Lens

A Timeline Lens groups threads by time window, activity burst, or sequence of work.

It is useful for asking "what was I working on during this period?" and for surfacing adjacent conversations without changing the underlying thread graph.

### Pinned / Saved Lens

A Pinned Lens or Saved Lens is a user-curated view that keeps selected threads or a saved selection rule available for quick return.

Pinned or saved lenses may be temporary or persistent, but they remain view-layer constructs. They must not mutate durable thread ownership or project membership.

## Boundary Rules

1. Lens selection must not move a thread out of its project.
2. Lens selection must not rewrite durable ownership metadata.
3. Lens selection must not create cross-account semantic grouping.
4. Lens behavior must respect current user/account boundaries.
5. Lens explanations must describe the basis of the view, not assert hidden truth.
6. Lens persistence, if added later, must be separate from project containment persistence.

## Relationship to Projects

Projects remain the durable containment layer.

That means:

- a thread can belong to one durable project while appearing in multiple lenses
- a lens may surface threads from multiple projects
- a lens may be temporary without affecting underlying ownership
- a project change requires a project mutation path, not a lens change

This distinction is the core anti-classification-debt rule. Lenses reduce the pressure to force one visible organization scheme onto all conversations.

## Scope and Identity

Thread Lenses must respect the same account and identity boundaries as other Codexify organization surfaces.

For semantic or personalized lenses:

- scope must remain within the current user or account
- no cross-user semantic grouping
- no cross-account persona inference
- no sharing of private organization state unless a future contract explicitly authorizes it

Any future shared or federated lens behavior would require a separate architecture contract and security review.

## Explainability

Every lens should be explainable as a view.

That means future implementations should be able to say:

- why a thread is included
- what rule or selection basis produced the view
- whether the lens is temporary or saved
- what scope it covers

Lenses should not be opaque containers that silently reshape ownership semantics.

## Follow-Up Implementation Specs

The following implementation specs are intentionally separate tasks and are not authorized by this contract:

- lens registry and canonical lens identifiers
- saved-lens persistence model
- query and filtering semantics for each lens category
- UI affordances for switching between lenses
- pinning, naming, and deletion workflows for saved lenses
- explanation strings and provenance fields for lens membership
- backend ranking, retrieval, or semantic clustering behavior
- any federation or sharing protocol for lenses

## Governing Sources

This contract is governed by and must remain aligned with:

- `docs/architecture/00-current-state.md`
- `docs/architecture/identity-and-runtime-mode.md`
- `docs/architecture/account-export-restore-contract.md`
- `docs/architecture/project-pulse-read-only-contract.md`

## Release Boundary

This document does not claim shipped support for Thread Lenses.

It defines a product and architecture concept only. If a future implementation is added, it must do so through separate, scoped tasks and must preserve project containment as the durable source of truth.
