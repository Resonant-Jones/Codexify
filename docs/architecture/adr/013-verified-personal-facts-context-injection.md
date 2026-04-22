---
status: accepted
date: 2026-04-22
---

# ADR-013: Verified Personal Facts Context Injection

## Context

Codexify already stores personal-fact lifecycle state in Postgres and already assembles provider-ready chat context through the backend broker and prompt builders. What was missing was a canonical decision about whether verified personal facts may enter that provider-ready path, how they are bounded, and how diagnostics should prove what was injected.

This change is runtime-impacting because it introduces a new context source into completion assembly. It does not add a new retrieval mode and it does not change the existing retrieval-router doctrine.

## Decision

Allow only verified, active, user-scoped personal facts to enter the chat completion context path.

The injection seam must:

- stay backend-only
- remain scoped to the resolved user identity
- exclude candidate, disputed, and inactive facts from provider-ready context
- keep evidence bodies out of the prompt in this first pass
- render a bounded, deterministic verified-personal-facts block only when eligible facts exist
- surface included verified fact ids in diagnostics so operators can prove what was used
- preserve the existing queue-backed completion flow and current retrieval-router policy

The broker is the authoritative read seam for eligible facts. Prompt assembly consumes the broker-provided verified-facts slice instead of inventing a separate truth source.

## Consequences

- Verified facts can now contribute identity context without becoming a new retrieval mode.
- Candidate or disputed facts remain non-authoritative and do not reach provider-ready context.
- Diagnostics can show the exact verified fact ids that were used for a completion attempt.
- The chat runtime can explain identity context without exposing evidence text or adding a UI surface.

## Non-Goals

- No automatic promotion from candidate to verified
- No evidence-body injection
- No new write path
- No cross-user leakage
- No UI fact-management surface
- No change to the existing retrieval-router doctrine

## Governing Contracts

- [Retrieval Policy as Control Plane](./004-retrieval-policy-as-control-plane.md)
- [Imprint UI Deprecation and Identity Ownership](./005-imprint-ui-deprecation-and-identity-ownership.md)
- [Chat Runtime Contract](../chat-runtime-contract.md)
- [Data and Storage](../data-and-storage.md)

## Related Notes

- [Critical Flows](../flows.md)
- [Current State](../00-current-state.md)
