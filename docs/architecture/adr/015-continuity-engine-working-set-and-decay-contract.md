---
tags:
* architecture
* adr
* continuity
* retrieval
* provenance
* identity-boundary
  aliases:
* ADR-015
* Continuity Engine Working Set and Decay Contract
---

# ADR-015: Continuity Engine Working Set and Decay Contract

## Status

Accepted

## Date

2026-04-22

## Context

Codexify's current chat runtime is thread-first. Completion assembly starts from the active thread and widens through retrieval, memory, and document paths. That gives the system useful local continuity, but it does not give it a governed cross-thread continuity layer.

The architecture already has the ingredients around the edges:

- thread/message provenance is canonical
- retrieval widening is explicit
- identity is separated from chat history
- export/restore already preserves lineage and imported-source metadata

What is missing is a first-class continuity contract that can preserve useful continuity across thread switches, project switches, and imported histories without pretending the system is the user and without trapping the user inside a stale snapshot.

## Problem Statement

The current gap is precise:

- thread-local continuity exists
- retrieval widening exists
- provenance and identity contracts exist
- but there is no cross-thread working-set continuity layer

That gap produces disconnected behavior when the user moves between threads, between projects, or between imported and native conversational history. The runtime can still answer, but it lacks a user-governed continuity substrate that can bias what matters now without silently collapsing everything into a permanent identity claim.

In practice, this means the system can preserve records but still fail to preserve continuity of attention, unless the user re-anchors the thread manually or the retrieval path happens to widen in the right direction.

## Decision

Codexify defines the **Continuity Engine** as a future architecture layer above the current thread-first chat runtime.

Its four responsibilities are:

1. **Activation** - determine what enters the continuity working set and why.
2. **Decay** - reduce continuity bias when items fall out of use.
3. **Provenance** - preserve where continuity came from and whether it is native or imported.
4. **Governance** - keep the layer user-governed, inspectable, and reversible.

The Continuity Engine is not identity ownership. It is a continuity-control layer that can bias retrieval and framing while remaining subordinate to canonical thread/message truth, request-state truth, provider-state truth, and export/restore lineage.

## Canonical Terms

| Term | Canonical meaning |
|---|---|
| Working set | The user-governed continuity scope that is eligible to bias retrieval, framing, and continuity-aware context assembly. It may include threads, projects, imported transcripts, pinned facts, and other approved anchors, but it is not a replacement for canonical records. |
| Continuity activation | The act of promoting a source, anchor, or lineage into the working set so it can influence continuity-aware retrieval. Activation is a governance decision, not a claim of identity ownership. |
| Continuity decay | The reduction of continuity bias over time or disuse. Decay changes weighting and visibility priority; it does not delete the underlying history by default. |
| Dormant continuity | Continuity state that remains preserved and inspectable but is no longer strongly biasing retrieval or framing. |
| Active continuity | Continuity state that is currently biasing retrieval or framing because it is relevant, pinned, recently used, or explicitly governed on. |
| Continuity provenance | The explicit lineage that explains how a continuity item entered the working set, where it came from, whether it is native or imported, and which thread/message or source artifact anchors it. |
| Continuity scaffold | Imported conversation history or imported history fragments that may seed continuity but must not be treated as proof of uninterrupted native continuity. |
| Continuity governance | The control plane that lets the user inspect, enable, pin, decay, scope, or revoke continuity influence. |
| Continuity mirror | The inspectability surface that shows the current continuity working set, provenance, activation state, decay state, and governance decisions without pretending to be the user or rewriting the underlying history. |

## Continuity Doctrine

- Continuity is not equivalent to identity ownership.
- Continuity must not trap the user inside a stale snapshot.
- Disuse should reduce retrieval bias without deleting underlying history by default.
- Imported conversations may participate as continuity scaffolds, but they must not be treated as proof of uninterrupted native continuity.
- Continuity must remain user-governed, inspectable, and reversible.
- Continuity must not silently promote sensitive diary material into durable identity structure.
- Persona behavior may borrow continuity only under the existing identity-boundary doctrine; personas do not own user identity.
- Continuity must not pretend that a rebuilt or imported record is the same thing as uninterrupted lived continuity.

## Non-Negotiable Invariants

- Thread/message provenance remains canonical.
- Export/restore must preserve continuity provenance and relationship semantics if this layer is later implemented.
- Imported and native lineage must remain distinguishable.
- Diary exclusions and opt-in deep identity boundaries remain intact.
- Continuity retrieval bias must decay with disuse.
- Continuity must never claim false uninterrupted memory.
- Continuity does not replace thread-local chat history, request-state truth, or provider-state truth.
- Continuity must not collapse provider runtime state, request execution state, and continuity state into one status story.

## Initial Architecture Shape

The likely future seams are:

| Seam | Responsibility |
|---|---|
| Continuity working-set builder | Assemble and rank continuity anchors from governed sources, then hand a candidate working set to context assembly. |
| Continuity provenance model | Record origin thread/message lineage, import source details, activation reason, and decay state. |
| Continuity governance control plane | Expose user-governed activation, decay, pinning, scoping, and revocation semantics. |
| Continuity mirror / inspectability surface | Present the active and dormant continuity state, provenance, and reason codes in a read-only or settings-style view. |
| Import-aware continuity framing in context assembly | Distinguish native history from imported scaffolds while preserving a truthful continuity bias. |

These seams describe a future control plane shape. They do not prescribe database tables, component trees, or a specific ranking algorithm.

## Implementation Boundaries

This ADR does not implement:

- runtime retrieval changes
- schema migrations
- new token registries
- UI surfaces
- import pipeline changes
- automatic identity inference expansion
- provider/runtime state changes
- request-state vocabulary changes

The contract may shape those future changes, but it does not claim they already exist.

## Relationship to Current Docs

This ADR is a future-direction contract layered over the current architecture corpus.

- `00-current-state.md` remains the source of truth for present release reality.
- `chat-runtime-contract.md` remains the normative request/provider-state contract.
- `router-decision-table.md` remains the retrieval-policy doctrine that continuity-aware widening must respect.
- `account-export-restore-contract.md` remains the lineage and restore contract continuity must not contradict.
- `tech-debt-and-risks.md` remains the place to record any implementation risk introduced later by continuity work.

Current runtime truth stays thread-first. No Continuity Engine is live today.

## Consequences

### Positive

- The system can preserve useful continuity without claiming to be the user.
- Imported histories can participate in continuity without being mislabeled as native lived continuity.
- Continuity decay gives the user a way to shed stale bias without erasing records.
- Provenance stays inspectable, which makes export/restore and auditability more truthful.

### Negative

- The system must keep a sharper distinction between continuity, identity, and history.
- Continuity mirrors can be confusing if they are presented like memory ownership rather than bias control.
- Future implementation will need explicit governance UI and context-assembly seams to stay honest.

## Links

* [[ADR Index]]
* [[router-decision-table|Retrieval Router Decision Table]]
* [[chat-runtime-contract|Chat Runtime Contract]]
* [[account-export-restore-contract|Account Export + Restore Contract]]
* [[system-overview|System Overview]]
* [[tech-debt-and-risks|Tech Debt and Risks]]
* [[00-current-state]]

## Notes

This ADR defines the first explicit continuity contract for Codexify. It intentionally keeps continuity, diary/history, and identity separate, and it does not claim the runtime already implements any continuity engine behavior.
