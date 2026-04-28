---
tags:
* architecture
* adr
* continuity
* governance
* provenance
* identity-boundary
  aliases:
* ADR-016
* Continuity Governance Surface Contract
---

# ADR-016: Continuity Governance Surface Contract

## Status

Accepted

## Date

2026-04-28

## Context

ADR-015 defines the continuity doctrine: Codexify may have a future continuity layer above thread-first chat, but that layer must stay user-governed, inspectable, reversible, and provenance-aware.

What ADR-015 does not yet define is the user-facing control plane for that continuity layer. Without a canonical governance contract, the system can drift into hidden heuristics, stale snapshot echo-chambers, imported-history overreach, persona/profile confusion, or identity contamination that is difficult to inspect or undo.

The gap is not theoretical:

- continuity doctrine exists
- identity and diary boundaries already exist
- export/restore provenance already matters
- personas already have a separate configuration/runtime role
- but there is no canonical contract for how continuity is configured, inspected, paused, reset, or excluded

This ADR closes that gap by defining the first explicit Continuity Governance Surface for Codexify.

## Problem Statement

If continuity behavior is left undefined, future implementation work can accidentally do one or more of the following:

- silently widen continuity scope beyond what the user intended
- bias the system toward stale or over-recalled snapshots
- contaminate continuity modeling with identity-like claims
- treat imported transcripts as if they were native lived continuity
- collapse persona configuration into ownership of continuity state
- make continuity bias impossible to inspect or reverse

Those failures matter because continuity is not just retrieval. It is a control-plane layer that can influence what the system prefers, surfaces, and reuses across time. If that layer is not explicitly governed, the runtime can become persuasive in ways the user never authorized.

## Decision

Codexify defines the **Continuity Governance Surface** as the canonical architecture layer that governs continuity behavior.

This surface is the user-governed control plane for:

- continuity scope
- continuity intensity
- continuity decay profile
- imported-history treatment
- continuity exclusions
- continuity mirror and inspection behavior
- continuity reset, rollback, disable, and pause behavior

The Continuity Governance Surface is not persona ownership. It is not a chat thread setting. It is not a deep-identity consent toggle. It is the control plane that determines whether continuity bias exists, how broad it is, where it may apply, how it decays, what it must exclude, and what the user can inspect or revoke.

## Canonical Concepts

| Concept | Canonical meaning |
|---|---|
| Continuity scope | The boundary within which continuity may bias context assembly. Scope answers where continuity can apply, such as thread-only, project-local, recent-thread working set, or cross-project personal continuity. Scope is narrower than "all available history" unless the user explicitly chooses that boundary. |
| Continuity intensity | The strength of continuity bias within the chosen scope. Intensity governs how strongly continuity may influence recall, framing, or prioritization. Intensity does not widen scope and does not imply deep identity modeling. |
| Continuity decay profile | The policy that determines how continuity bias cools with disuse, age, or lack of reinforcement. Decay changes activation bias, not canonical history truth by default. |
| Continuity exclusion | A rule that blocks specific content, threads, topics, or projects from continuity modeling even if they remain stored in chat history. Exclusions override convenience retrieval. |
| Continuity import mode | The treatment applied to imported history or imported transcripts. Import mode determines whether imported material is archive-only, recallable as archive, or eligible to seed continuity as a scaffold under explicit governance. |
| Continuity mirror | The inspectability surface for continuity state. It must show active and dormant continuity, provenance, exclusions, intensity, decay state, import treatment, and reset/freeze state in a user-legible way. |
| Continuity reset | An explicit action that clears active continuity bias or reinitializes continuity state according to the chosen reset mode. Reset must be user-legible and must not silently rewrite canonical history. |
| Continuity freeze / pause | A reversible temporary stop on new continuity updates, promotions, or refreshes. Freeze/pause preserves the existing continuity record and must not silently widen or auto-refresh continuity while paused. |
| User-authored continuity preferences | The explicit settings the user chooses for scope, intensity, decay, import treatment, exclusions, and reset behavior. These preferences are canonical user intent, not derived model output. |
| System-derived continuity state | The runtime-computed continuity state produced from user preferences, provenance, and current evidence. System-derived state may be inspected and used, but it must remain separable from the user-authored preference record. |

## Required Control Families

Future runtime and UI work that implements continuity must honor at least the following control families.

### Scope Controls

The minimum supported scope families are:

- thread only
- project-local
- recent-thread working set
- cross-project personal continuity

Scope controls define where continuity may bias context. They do not change canonical history ownership and they do not imply global recall across unrelated content.

### Decay Controls

Decay controls must define how continuity bias cools with disuse.

The contract distinguishes:

- rolloff, which reduces continuity bias or activation strength over time or disuse
- deletion, which removes history or records only when the user explicitly chooses a destructive action

The system may also support optional pinning or hold-close semantics for specific continuity anchors. Pinning may slow or suspend decay for the pinned anchor, but it must remain visible in the mirror and must not erase provenance.

### Import Controls

Imported history must be governed explicitly.

The minimum import modes are:

- archive only: imported material is preserved as history but cannot seed continuity bias
- recallable archive: imported material may be recalled intentionally, but it is not auto-promoted into continuity state
- continuity scaffold: imported material may seed continuity candidates under explicit governance, while remaining provenance-tagged as imported

Imported transcripts are not native lived continuity by default. Any continuity influence they carry must remain visibly imported and user-governed.

### Exclusion Controls

Continuity exclusions must include at least:

- diary exclusion
- sensitive-topic exclusion
- project-level exclusion from continuity modeling
- thread-level exclusion from continuity modeling

Exclusions must override convenience retrieval. If a source is excluded, continuity may not silently reintroduce it just because it is available.

### Inspection Controls

The continuity mirror must reveal enough information for a user to understand what continuity is doing.

At minimum, it must distinguish:

- active continuity versus dormant continuity
- explicit sources versus inferred sources
- imported provenance versus native provenance
- user preferences versus system-derived state
- excluded material versus eligible material

The mirror must be inspectable without pretending to be a memory authority. It is an explanation surface for continuity bias, not a claim that the system owns the user's past.

### Reset Controls

Reset controls must include at least:

- disable new continuity updates
- clear active continuity bias without deleting history
- perform a full continuity reset when the user explicitly chooses it

Reset actions must be explicit and user-legible. They must not silently alter canonical history or provenance.

## Boundary Doctrine

The Continuity Governance Surface obeys the following boundary rules:

- continuity governance belongs to user/runtime continuity control, not persona ownership
- Persona Studio may eventually expose compatible controls, but persona profiles must not become the canonical owner of user continuity state
- continuity settings are not equivalent to deep identity consent
- diary/chat storage is not the same thing as continuity bias
- imported transcripts may be continuity scaffolds only under explicit governance rules
- continuity must remain inspectable, reversible, and provenance-aware
- continuity governance must not silently widen into identity modeling
- continuity governance must not claim uninterrupted native memory where provenance does not support it

Persona configuration can borrow continuity semantics later, but it does not own the continuity control plane.

## Non-Negotiable Invariants

The following invariants are mandatory for any future implementation:

- personas do not own or silently widen user continuity state
- continuity configuration must not silently enable deep identity modeling
- continuity exclusions must override convenience retrieval
- imported and native lineage must remain distinguishable
- rolloff with disuse changes retrieval or activation bias, not canonical history truth by default
- reset and disable actions must be explicit and user-legible
- continuity governance must not claim uninterrupted native memory where provenance does not support it
- export/restore must preserve continuity-governance settings and provenance semantics if later implemented
- continuity-governance state must remain separable from provider-state, request-state, and thread-history truth surfaces

## Relationship to Existing Architecture

This ADR is aligned with, and constrained by, the following contracts:

- ADR-015 for continuity doctrine, working-set decay, provenance, and imported-history scaffolding
- the IDDB policy for chat-history versus identity separation, opt-in deep identity, and diary exclusion
- the account export/restore contract for provenance, lineage, and restore semantics
- the Persona Studio separation-of-concerns doctrine so profile config and user continuity governance do not collapse into one layer

Current runtime truth remains thread-first. This ADR does not claim a live Continuity Engine or a live continuity-governance UI.

## Implementation Boundaries

This ADR does not implement:

- runtime retrieval changes
- persistence or schema changes
- new UI panels or settings pages
- persona profile schema changes
- import pipeline changes
- export/restore payload changes
- automatic deep identity expansion
- new prompt behavior

This contract is architectural. It defines the future seam, not a shipped feature.

## Initial Architecture Shape

The likely future seams are:

| Seam | Responsibility |
|---|---|
| Continuity-governance settings model | Store user-authored continuity preferences, including scope, intensity, decay, exclusions, import mode, and reset state. |
| Continuity policy evaluator | Resolve user preferences, provenance, and current runtime evidence into the continuity state used by context assembly or continuity orchestration. |
| Continuity mirror inspection surface | Present active, dormant, excluded, imported, and inferred continuity state in a user-legible read-only form. |
| Continuity reset / disable actions | Provide explicit user operations that pause, clear, or fully reset continuity state without silently rewriting canonical history. |
| Continuity-aware import framing | Apply explicit import modes so imported transcripts are archive-only, recallable, or eligible to seed continuity scaffolds under governance. |
| Export/restore compatibility seam | Preserve continuity-governance preferences and provenance semantics if and when export/restore grows support for continuity state. |

These seams are intentionally high level. They describe the future control plane without prescribing tables, routes, or ranking algorithms.

## Documentation Routing

This ADR is the follow-on contract after ADR-015 and should be discoverable from the architecture front door.

- `00-current-state.md` remains the short-horizon truth layer for present runtime reality.
- `adr-index.md` should list this ADR immediately after ADR-015.
- `README.md` should point readers from the continuity doctrine to this governance contract when they need the user-facing control plane, not just the doctrine.

## Consequences

### Positive

- Continuity can be user-governed instead of heuristic-only.
- Inspectability becomes part of the contract rather than an afterthought.
- Imported histories can participate without being mislabeled as native continuity.
- Reset and exclusion semantics can be reasoned about before any UI or backend work lands.
- Persona/profile boundaries stay separate from continuity ownership.

### Negative

- Future implementation must keep more state surfaces distinct: continuity, diary/history, identity, persona config, request state, and provider state.
- The continuity mirror must be designed carefully so it explains bias without pretending to be memory ownership.
- Any later backend or UI implementation will need to honor this contract before it can claim continuity behavior is supported.

## Links

- [[ADR Index]]
- [[015-Continuity-Engine-Working-Set-and-Decay-Contract|ADR-015 Continuity Engine Working Set and Decay Contract]]
- [[account-export-restore-contract|Account Export + Restore Contract]]
- [[persona-studio|Persona Studio Architecture]]
- [[system-overview|System Overview]]
- [[data-and-storage|Data and Storage]]
- [[tech-debt-and-risks|Tech Debt and Risks]]
- [[00-current-state]]

## Notes

This ADR defines the canonical user-governed control plane for continuity behavior. It deliberately keeps continuity, diary history, persona configuration, and identity modeling separate, and it does not describe any continuity-governance implementation as already shipped.
