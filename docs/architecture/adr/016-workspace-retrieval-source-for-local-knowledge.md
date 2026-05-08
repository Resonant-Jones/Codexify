---
status: accepted
date: 2026-04-27
---

# ADR-016: Workspace Retrieval Source for Local Knowledge

## Context

Codexify already had a thread-first completion path, a broker that can assemble local context, and a retrieval doctrine that distinguishes conversation, project, personal knowledge, and Obsidian-only source modes. What was missing was a live backend meaning for `retrievalSource="workspace"` on the chat path.

The risk here is semantic drift. Without a canonical contract, `workspace` could collapse into `project`, leak into global search, or become a vague label that means different things in the route, broker, and debug surfaces.

## Decision

`workspace` is now a first-class live source mode for chat completions.

Its meaning is:

- user-bounded
- local-first
- able to widen beyond the active thread into the user-owned local working set
- allowed to include Obsidian-backed notes and other local retrieval contributions
- not allowed to become global search
- not allowed to introduce a new storage model, queue, or connector subsystem

The completion route preserves `workspace` instead of normalizing it away. The completion service and broker treat it as a real retrieval posture and emit canonical trace evidence for the final completion attempt.

## Consequences

- A chat completion can now be intentionally influenced by ingested local notes during the actual assistant response path.
- The latest retrieval-posture snapshot can distinguish `workspace` from `thread`, `project`, `personal_knowledge`, and `obsidian_only`.
- The broker keeps the same-user boundary explicit, so `workspace` remains local without becoming global.
- Obsidian support now has a live chat seam instead of only an ingest-to-retrieve proof surface.

## Non-Goals

- No sync automation
- No first-class Obsidian connector UX
- No new queue or background worker
- No global retrieval widening
- No replacement for thread, project, or personal-knowledge source modes
- No claim that live Compose proof is already complete

## Governing Contracts

- [Retrieval Router Decision Table](../router-decision-table.md)
- [Critical Flows](../flows.md)
- [System Overview](../system-overview.md)
- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Data and Storage](../data-and-storage.md)

## Related Notes

- [Current State](../00-current-state.md)
- [ADR Index](./adr-index.md)
