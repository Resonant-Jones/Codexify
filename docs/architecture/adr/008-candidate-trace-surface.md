# ADR-008: Candidate Trace Surface

Status: accepted
Date: 2026-04-19

## Context

Codexify's completion pipeline already distinguishes request/attempt identity from canonical chat messages, and the runtime exposes RAG trace as a post-run diagnostic view. The backend needed a separate place to inspect pre-answer candidate outputs without turning them into canonical assistant messages or exportable artifacts.

## Decision

Introduce `candidate_trace` as a backend-only, non-canonical runtime surface.

The surface must:

- be emitted after candidate generation during completion assembly
- be stored transiently with short TTL semantics
- be keyed by `thread_id` and `request_id`
- remain independent from `chat_messages`
- remain excluded from export/restore lineage
- remain hidden from the UI

The completion service may populate the surface, and the chat debug route may read it. The canonical assistant message remains the only authoritative chat output.

## Consequences

- Operators gain a safe inspection surface for completion candidates.
- Tests can verify candidate emission without relying on chat history.
- The runtime can add future candidate ranking or selection metadata without changing canonical persistence.
- Expiration or cache loss does not affect chat correctness.

## Non-Goals

- No graph write path
- No vector-store write path
- No UI surface
- No export/restore inclusion
- No canonical message duplication

## Governing Contracts

- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)

## Related Notes

- [Candidate Trace Surface](../candidate-trace-surface.md)
- [Completion Pipeline](../completion_pipeline.md)
- [Data and Storage](../data-and-storage.md)
