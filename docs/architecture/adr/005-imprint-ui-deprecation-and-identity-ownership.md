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

Accepted

## Date

2026-04-15

## Context

The Imprint Zero concept was introduced as the durable user substrate underlying persona authoring. Over time, the system has evolved distinct surfaces for:

- **Persona Studio** — non-conversational configuration and observability interface for authored runtime profile / mask composition
- **Settings → Diagnostics** — cognitive inspector surfaces for troubleshooting and audit
- **Personal Facts lifecycle surfaces** — durable identity governance backed by `personal_facts`, `personal_fact_evidence`, and `personal_fact_revisions` in the data model

The original Imprint tab as a standalone UI surface for narrative "imprint draft" authoring is no longer aligned with the current ownership model.

## Problem

Imprint as a first-class user-authored UI module conflates two distinct concerns:

1. The durable user substrate (`Imprint_Zero`, light/deep identity modeling)
2. Persona composition and runtime profile authoring

This conflates the user substrate with authored masks, and creates an ambiguous ownership boundary between:
- Persona Studio (profile composition)
- Settings (identity governance)
- Diagnostics (inspector surfaces)

Without a formal boundary here, UI surface growth risks duplicating functionality and scattering identity ownership across inconsistent surfaces.

## Decision

Codexify establishes the following ownership boundaries:

1. **Imprint is not a first-class user-authored UI module.** The standalone Imprint tab is deprecated as a primary UI pattern.

2. **Durable user modeling belongs under Settings-owned identity governance.** The `personal_facts` family of tables represents the lifecycle-friendly durable identity surfaces. These are governed through Settings, not through a dedicated imprint UI.

3. **Persona Studio owns authored runtime profile / mask composition.** Persona Studio is the surface for composing and observing personas as runtime masks, not for mutating the underlying user substrate.

4. **Derived relational synthesis may still exist internally** as an implementation detail, but does not require a standalone authored Imprint tab.

5. **Heavy inspector surfaces remain in Settings → Diagnostics.** Cognitive inspectors and trace tooling live there, not inside primary authored interaction surfaces.

6. **Do not assume `personal_facts` is part of the current beta promise.** Operational truth as of this ADR date does not confirm end-user-supported beta functionality for Personal Facts surfaces. References to Personal Facts in this ADR describe the data model scope, not a shipping feature.

## Rationale

The IDDB data model already distinguishes:
- chat history
- light/deep identity modeling
- `Imprint_Zero` as the underlying user substrate
- personas as masks that borrow from that substrate

Persona Studio is explicitly defined as a **non-conversational configuration and observability interface** and must not mutate durable identity or memory systems.

Diagnostics canon keeps cognitive inspectors in **Settings → Diagnostics**, not inside primary authored interaction surfaces.

The original Imprint Zero concept has been functionally distributed across more mature system features. The remaining durable identity aspects belong to Settings-governed fact/identity surfaces, not to a standalone UI module.

## Non-goals

- This ADR does not mandate a UI refactor or rewrite of existing surfaces.
- This ADR does not claim Personal Facts is end-user-supported beta functionality.
- This ADR does not describe runtime behavior that is not already documented in the current truth corpus.
- This ADR does not change the data model — it clarifies ownership boundaries around existing structures.

## Consequences

### Positive

- Ownership boundaries are explicit and enforceable.
- Persona Studio scope is clear — authored profile composition, not user substrate mutation.
- Diagnostics stays in Settings where operator-facing tooling belongs.
- Identity governance surfaces are distinguishable from persona authoring surfaces.

### Negative

- Existing Imprint UI surfaces may need future migration work to align with this ownership model.
- Contributors must understand the distinction between durable identity (Settings) and authored masks (Persona Studio).

## Follow-on implementation slices

1. **Align Persona Studio documentation** with the scope defined in this ADR — configuration and observability only, no durable identity mutation.
2. **Audit existing Imprint tab references** in the codebase and UI to determine what wiring may be removed or redirected.
3. **Verify Personal Facts surface readiness** before treating `personal_facts` as a beta-ready feature — do not assume support without current truth confirmation.
4. **Inspect diagnostics placement** in Settings to ensure all cognitive inspectors are correctly located and not duplicated in primary authored surfaces.

## Invariants created by this decision

- Persona Studio must not mutate durable identity or memory systems.
- Imprint_Zero is an internal user substrate, not a primary authored UI surface.
- `personal_facts`, `personal_fact_evidence`, and `personal_fact_revisions` are the durable identity surfaces; their exposure level is determined by Settings-owned governance.
- Cognitive inspectors belong in Settings → Diagnostics, not in primary authored interaction surfaces.
- Derived relational synthesis may exist as an internal implementation detail without a standalone authored Imprint tab.

## Links

* [[ADR Index]]
* [[system-overview|System Overview]]
* [[modules-and-ownership|Modules and Ownership]]
* [[00-current-state]]
* [[chat-runtime-contract|Chat Runtime Contract]]

## Notes

This ADR establishes the doctrine that **identity ownership is Settings-governed, not Imprint-authored**.

Persona Studio is the authored runtime profile surface. Settings is the identity governance surface. Diagnostics is the inspector surface. These are distinct, not interchangeable.