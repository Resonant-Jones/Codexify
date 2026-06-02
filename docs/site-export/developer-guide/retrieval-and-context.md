# Retrieval and Context

Retrieval in Codexify is an orchestration concern, not a prompt-text hack or a UI heuristic.

## Retrieval Posture

The runtime supports several broad retrieval modes:

- conversation-only
- local thread or project retrieval
- memory recall
- provenance-oriented retrieval
- explicitly broadened search posture

The router and context assembly layers decide which mode applies.

## Policy Location

Retrieval policy belongs in orchestration because that is where the system can preserve scope, provenance, and widening reasons.

It should not be hidden inside prompt templates or inferred ad hoc from UI state.

## Current Shape

The current architecture docs describe a thread-first path that can widen into thread-local semantic context, project documents, memory, and other supported local evidence depending on policy and request shape.

This guide does not claim live retrieval behavior beyond what the supported docs already state.
It only preserves the doctrine that:

- scope starts narrow
- widening is explicit
- provenance must remain inspectable
- broader search posture must be intentional

## Boundary Rule

Retrieval is user-bound and source-bound.
Cross-boundary evidence, if ever allowed, must be explicit enough that operators can see why the scope widened.
