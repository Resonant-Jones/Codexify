# Signal Acquisition and Growth Role

> Classification: conceptual product/architecture doctrine<br>
> Runtime impact: none<br>
> Release promise: none<br>
> Interpretation rule: if this conflicts with `docs/architecture/00-current-state.md`, current-state wins.

Grounding note: this spec maps to retrieval policy. In current doctrine, retrieval decisions belong in the orchestration layer before ContextBroker assembly, not in prompt text or UI controls. The Signal Digest inspection also provides a candidate workflow loop for scheduled/manual trigger, source fetch, normalization, relevance scoring, ranking, digest composition, and delivery while separating supported, thin-helper, and unproven surfaces.

## Purpose

Define the Codexify equivalent of the "Head of Growth" role.

In Codexify, growth is not merely marketing. It is the system function that acquires, filters, ranks, and routes high-quality signal.

## Codexify Translation

The Head of Growth maps to:

- retrieval router
- ContextBroker
- source ingestion
- Signal Digest workflows
- research/crawl primitives
- lead/signal candidate normalization
- relevance scoring
- evidence ranking
- scoped context widening

## System Responsibility

This role answers:

- What information should enter the system?
- Which source should be consulted first?
- Is this conversation-only, local, project, workspace, or global?
- What evidence is sufficient?
- When should retrieval stop?
- Which signals become candidates for action?
- Which signals should be ignored?

## Design Interpretation

In an AI-native system, growth becomes signal routing.

The system does not simply "get more attention." In this framing, it improves the quality of context entering the decision loop.

## Core Loop

```text
source input
  -> fetch
  -> normalize
  -> classify intent
  -> retrieve / enrich
  -> rank
  -> threshold
  -> compose result
  -> route to human or workflow
```

## Related Existing Surfaces

- Retrieval Router Decision Table
- ContextBroker
- workspace-local retrieval
- document ingestion
- vector store
- Signal Digest
- Flow Builder
- Job Intelligence Layer
- campaign/marketing curation pipeline

## Invariants

- Retrieval scope must be explicit.
- Retrieval should start local unless the user or policy justifies wider scope.
- Prompt text must not smuggle retrieval policy.
- UI controls must not become independent policy engines.
- Graph context remains optional and feature-flagged unless current truth says otherwise.
- Evidence must remain distinguishable from generated interpretation.

## Failure Modes

| Failure | Consequence |
| --- | --- |
| Retrieval policy in prompt text | Hidden behavior drift |
| Over-broad retrieval | Noise, latency, privacy risk |
| No stop condition | Context bloat |
| Signal treated as truth | False certainty |
| Ranking not explainable | Operator distrust |

## Product Language

This role is the system's "signal intake and routing layer."

It turns attention into evidence, and evidence into actionable context.
