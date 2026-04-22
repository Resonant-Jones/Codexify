---
status: accepted
date: 2026-04-22
---

# ADR-012: Post-Completion Eval Spine

## Context

Codexify already distinguishes completion acceptance from eventual worker execution, and it already has a durable chat transcript plus transient RAG/debug trace seams. What was missing was a canonical, durable inspection layer that could attach a quality verdict to a specific completion attempt without becoming part of the chat acceptance contract.

## Decision

Add a post-completion eval spine as a derived persistence and inspection layer.

The spine must:

- persist a trace snapshot only after assistant completion has been durably stored
- enqueue a best-effort eval task only after the snapshot exists
- evaluate the persisted snapshot out of band
- store one verdict row per attempt and evaluator
- keep provider runtime state distinct from request/task lifecycle state
- keep provenance and lineage intact via thread, user message, assistant message, request/task, and project identifiers when available

The first shipped evaluator is a deterministic code-based groundedness check. The implementation may add an LLM-judge boundary later, but only as another evaluator kind, not as a replacement for the derived inspection layer.

## Consequences

- Chat completion acceptance stays unchanged: accepted still means the turn lock was acquired and the task was enqueued.
- Eval failure does not roll back chat persistence or change transcript truth.
- Snapshot and verdict records become canonical Postgres artifacts for post-completion diagnostics.
- The runtime now has a durable place to ask what context was used, what the assistant returned, and whether the result was grounded in the persisted trace.
- Operators can inspect quality without polluting the normal chat lane.

## Non-Goals

- No runtime gating of completion on eval success
- No replacement of the chat execution path
- No merging of provider runtime state and request/task state
- No heavy observability stack or external telemetry dependency
- No noisy eval internals inside the primary transcript UI

## Governing Contracts

- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Runtime Protocol Token Contract](../runtime-protocol-token-contract.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)

