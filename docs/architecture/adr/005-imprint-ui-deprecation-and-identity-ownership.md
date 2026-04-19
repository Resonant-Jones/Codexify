---

tags:

* architecture
* adr
* imprint
* identity
* persona-studio
* ownership
  aliases:
* ADR-005
* Imprint UI Deprecation and Identity Ownership

---

# ADR-005: Imprint UI Deprecation and Identity Ownership

## Status

Proposed

## Date

2026-04-15

## Context

The Imprint Zero concept was originally introduced as the durable user substrate underlying persona behavior and relational fit. Since then, Codexify has evolved distinct surfaces with clearer responsibilities:

* **Persona Studio**: a non-conversational configuration and observability surface for authored runtime profile and mask composition.
* **Settings → Diagnostics**: the dedicated home for cognitive inspectors, trace surfaces, and troubleshooting views.
* **Durable identity data seams**: lifecycle-shaped identity records represented in the data model by `personal_facts`, `personal_fact_evidence`, and `personal_fact_revisions`.

Recent UI evolution has created overlap between Settings-owned identity surfaces, Persona Studio profile composition, and legacy Imprint authoring patterns. The original Imprint tab, especially as a standalone narrative "imprint draft" authoring surface, no longer matches the current ownership model.

## Problem

Imprint as a first-class user-authored UI module conflates two distinct concerns:

1. The durable user substrate (`Imprint_Zero`, light/deep identity modeling).
2. Persona composition and runtime profile authoring.

This blurs the ownership boundary between:

* **Persona Studio** as the authored runtime profile surface
* **Settings** as the durable identity governance surface
* **Diagnostics** as the inspector surface

Without a formal boundary, UI growth risks duplicating functionality, scattering identity ownership across inconsistent surfaces, and reintroducing confusion between the user substrate and authored masks.

## Decision

Codexify establishes the following ownership boundaries:

1. **Imprint is not a first-class user-authored UI module.**
   The standalone Imprint tab is deprecated as a **primary authored UI pattern**.

2. **Durable user modeling belongs under Settings-owned identity governance, not Persona Studio.**
   The current durable identity data seam is the `personal_facts` family:

   * `personal_facts`
   * `personal_fact_evidence`
   * `personal_fact_revisions`

   These structures represent the current lifecycle-friendly identity data model. Their eventual user-facing exposure remains subject to supported-surface validation and must not be overstated.

3. **Persona Studio owns authored runtime profile and mask composition.**
   Persona Studio is the surface for composing, validating, and observing personas as runtime masks. It is not the owner of durable user substrate mutation.

4. **Derived relational synthesis may still exist internally.**
   Codexify may continue to derive relational or interaction-shaping guidance from durable identity state as an implementation detail, but that does not require a standalone authored Imprint tab.

5. **Heavy inspector surfaces remain in Settings → Diagnostics.**
   Cognitive inspectors, trace tooling, and related introspection surfaces belong there, not inside primary authored interaction surfaces.

6. **Do not assume `personal_facts` is part of the current beta promise.**
   Operational truth at the time of this ADR does not confirm end-user-supported beta functionality for Personal Facts surfaces. References to `personal_facts` in this ADR describe current data-model ownership, not a shipped product claim.

## Rationale

Codexify’s identity model already distinguishes:

* chat history as diary-like conversational record
* light and deep identity modeling
* `Imprint_Zero` as the underlying user substrate
* personas as masks that borrow from that substrate rather than owning it

Persona Studio is explicitly defined as a **non-conversational configuration and observability interface** and must not mutate durable identity or memory systems.

The diagnostics canon separately places cognitive inspectors in **Settings → Diagnostics**, not inside primary authored interaction surfaces.

The original Imprint Zero concept has been functionally distributed across more mature system features. What remains valuable is not a standalone narrative prompt-authoring surface, but a clear distinction between:

* **durable identity governance**
* **runtime mask composition**
* **diagnostic inspection**

This ADR formalizes that distinction.

## Superseded assumptions

The following assumptions should no longer guide design or implementation:

* Imprint should remain a primary narrative prompt-authoring surface.
* Persona Studio is an appropriate owner for durable user substrate mutation.
* Diagnostics may be colocated inside profile-authoring surfaces for convenience.
* The existence of durable identity tables automatically implies a beta-ready end-user feature surface.

## Consequences

### Positive

* Ownership boundaries become explicit and enforceable.
* Persona Studio scope is clearer: authored profile composition, not user substrate mutation.
* Settings retains ownership of durable identity governance.
* Diagnostics remains the correct home for cognitive inspectors and trace tooling.
* Contributors can reason about identity, mask composition, and inspection as distinct system concerns.

### Negative

* Existing Imprint UI surfaces may require future migration or removal work.
* Contributors must learn and preserve the distinction between durable identity state and authored personas.
* Some legacy naming and conceptual residue may remain in code or docs until follow-on cleanup lands.

## Non-goals

This ADR does **not**:

* mandate an immediate UI refactor or rewrite
* claim that Personal Facts is currently an end-user-supported beta feature
* introduce undocumented runtime behavior
* change the data model
* remove internal derived identity synthesis where it remains implementation-useful

## Follow-on implementation slices

1. **Align Persona Studio documentation** with this ownership boundary: configuration and observability only, no durable identity mutation.
2. **Audit existing Imprint references** in the codebase and UI to determine which should be removed, redirected, or retained as internal terminology only.
3. **Verify Personal Facts surface readiness** before treating `personal_facts` as a supported user-facing beta surface.
4. **Review diagnostics placement** to ensure cognitive inspectors remain in Settings and are not duplicated in primary authored surfaces.
5. **Plan UI consolidation in bounded slices** rather than as a single large refactor spanning Settings, Persona Studio, and internal synthesis behavior.

## Invariants created by this decision

* Persona Studio must not mutate durable identity or memory systems.
* `Imprint_Zero` is an internal user substrate, not a primary authored UI surface.
* The `personal_facts` family is the current durable identity data seam; exposure level remains governed by Settings-owned product decisions.
* Cognitive inspectors belong in Settings → Diagnostics, not in primary authored interaction surfaces.
* Derived relational synthesis may exist internally without requiring a standalone authored Imprint tab.

## Links

* [ADR Index](./adr-index.md)
* [System Overview](../system-overview.md)
* [Modules and Ownership](../modules-and-ownership.md)
* [00 Current State](../00-current-state.md)
* [Chat Runtime Contract](../chat-runtime-contract.md)

## Notes

This ADR establishes the doctrine that **identity ownership is Settings-governed, not Imprint-authored**.

In short:

* **Settings** owns durable identity governance.
* **Persona Studio** owns authored runtime profile composition.
* **Diagnostics** owns inspector surfaces.

These are adjacent layers, but they are not interchangeable.

> If this decision has already been formally ratified in-repo, change **Status** from `Proposed` to `Accepted`.
