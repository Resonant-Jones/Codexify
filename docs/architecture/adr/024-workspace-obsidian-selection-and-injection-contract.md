---
status: accepted
date: 2026-05-06
---

# ADR-024: Workspace Obsidian Selection and Injection Contract

## Context

ADR-016 made `retrievalSource="workspace"` a live backend meaning for local knowledge, including Obsidian-backed notes. ADR-023 then made the live workspace proof harness canonical so the runtime seam could be validated end to end on the supported local Compose path.

What was still missing was a truthful contract for the evidence gap between:

- a note being searchable in the live vector store
- the broker selecting that note as workspace-local evidence
- the completion service injecting that evidence into the real assistant context
- the assistant reflecting that evidence in the response

Without that distinction, workspace proof could collapse into a weaker claim and overstate completion-time influence.

## Decision

Codexify now treats workspace Obsidian evidence as a multi-step runtime contract:

- searchable in the live substrate
- eligible for workspace retrieval under the same-user boundary
- selected by the broker as workspace-local evidence
- injected into the completion context bundle
- reflected in the assistant output

The broker may preserve Obsidian hits through its same-user filtering when the vector store omits explicit ownership metadata for a result that is already scoped to the resolved request user. That preservation must remain user-bound and must not widen workspace retrieval into global search.

The completion service must surface completion-time evidence truthfully:

- `obsidian_count` reflects workspace-local Obsidian evidence selected for completion
- `obsidian_injected` reflects whether that evidence actually entered the completion context
- workspace-local proof remains canonical only when the proof harness sees searchability, selection, injection, and reflection all line up

Searchability alone is weaker than completion-context inclusion and is not sufficient release evidence.

## Consequences

- Workspace proof can now explain whether failure happened at search, broker selection, injection, or assistant reflection.
- A searchable note is no longer mistaken for a proven completion-context influence.
- The workspace retrieval seam remains local-first and user-scoped.
- The live proof harness remains the canonical validator for this seam.

## Non-Goals

- No new retrieval subsystem
- No sync or connector UX addition
- No global search widening
- No separate truth surface for retrieval evidence
- No weakening of user-boundary isolation

## Governing Contracts

- [ADR-016: Workspace Retrieval Source for Local Knowledge](./016-workspace-retrieval-source-for-local-knowledge.md)
- [ADR-023: Workspace E2E Proof Harness Contract](./023-workspace-e2e-proof-harness-contract.md)
- [Critical Flows](../flows.md)
- [System Overview](../system-overview.md)
- [Retrieval Router Decision Table](../router-decision-table.md)

## Related Notes

- [Current State](../00-current-state.md)
- [ADR Index](./adr-index.md)
