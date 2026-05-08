---
tags:
* architecture
* adr
* web
* retrieval
* browser
* provenance
aliases:
* ADR-021
* Web Agent Boundary and Retrieval Contract
---

# ADR-021: Web Agent Boundary and Retrieval Contract

## Status

Proposed

## Date

2026-05-03

## Classification

This ADR is architecture-impacting.

## Governing ADRs

- ADR-004: Retrieval Policy as Control Plane
- ADR-010: Self-Extending Agent Plugin System
- ADR-020: Guardian Mediated Coding Agent Execution Contract

## Context

Codexify already distinguishes retrieval policy from prompt text, and it already treats Guardian as the owner of identity, lineage, and transcript truth. The missing piece is a bounded external-information boundary that keeps search, URL reading, extraction, browser automation, and service connectors separate instead of collapsing them into one autonomous web agent.

That boundary also needs to preserve operator truth. External content must remain untrusted data, egress decisions must remain explicit, provenance must survive persistence, and future diagnostics must remain inspectable without turning noisy remote content into hidden instructions.

## Decision

Codexify will model the Web Agent as a governed external retrieval and interaction boundary with distinct modes.

- Search-as-RAG, URL reading, structured extraction, live browser automation, and Google service connectors are separate modes.
- Google APIs may be candidate adapters, not current support promises.
- Remote content is untrusted data.
- Future implementation must use canonical tokens before introducing repeated runtime statuses, events, or errors.

## Consequences

### Positive

- Safer future implementation path
- Cleaner operator truth
- Better provenance and traceability
- A narrower trust boundary for remote content
- A clearer seam for later Google adapter work

### Negative

- No immediate runtime behavior change
- Future implementation tasks are still required
- More contract surfaces must be maintained before code lands

## Non-Goals

- No implementation
- No release widening
- No quota claims
- No unbounded browsing agent

## Links

- [Web Agent Spec v1](../web-agent-spec.md)
- [Retrieval Router Decision Table](../router-decision-table.md)
- [Config and Ops](../config-and-ops.md)
- [Runtime Protocol Token Contract](../runtime-protocol-token-contract.md)
- [Canonical Token Philosophy](../canonical-token-philosophy.md)
- [Account Export + Restore Contract](../account-export-restore-contract.md)
- [Self-Extending Agent Plugin System](../self-extending-agent-plugin-system.md)
