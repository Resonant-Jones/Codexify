# ADR-089: Open-Ended Project Knowledge and Bounded Document Recall

**Status:** Accepted — 2026-09-24

## Context

Existing retrieval policy, ContextBroker scope, uploaded-document readiness, and completion-context traces define useful seams. They do not yet provide one contract separating Project knowledge membership, request eligibility, executed search and reading, context injection, and evidentiary coverage. Treating a semantic hit limit as a Project KB limit would confuse storage with per-request work; treating larger `topK` as exhaustive review would overstate coverage.

The accepted human decision is that Project documents may continue accumulating subject to real deployment capacity, without an arbitrary document-count ceiling in retrieval doctrine. Every request remains scoped and resource-bounded.

## Decision

Adopt the normative [Document Recall Contract](../document-recall-contract.md): **knowledge membership is open-ended; retrieval execution is bounded**. No fixed Project document-count cap or silent oldest-document eviction is a retrieval rule. Capacity and ingestion limits must be represented honestly.

The contract defines distinct `member`, `eligible`, `searched`, `retrieved`, `read`, `injected`, and `cited` stages; targeted recall, cross-document synthesis, and exhaustive review as coverage obligations orthogonal to retrieval depth; enumerated authorized sources and per-source accounting for exhaustive review; claim-relative authority and derivative provenance; and a future request/attempt-scoped Document Recall Receipt. Semantic `topK` cannot establish exhaustive coverage. Negative claims cannot exceed executed coverage.

Existing user, Project, thread, source, readiness, and provider-disclosure boundaries apply before evidence use. `projects.user_id` remains Project ownership authority; graph traversal and ranking cannot grant access or truth. Current uploaded-document broker eligibility continues to require `embedding_status == "ready"`.

## Alignment and authority

- Extends [ADR-004](./004-retrieval-policy-as-control-plane.md): the existing backend Retrieval Router remains the policy entrypoint; coverage must join that control plane, not prompt logic or a parallel engine.
- Preserves [ADR-059](./059-workspace-obsidian-selection-and-injection-contract.md): searchability, selection, injection, and reflection are distinct proof stages.
- Preserves [ADR-060](./060-workspace-retrieval-source-for-local-knowledge.md): source modes remain user-bounded and local/workspace semantics are unchanged.
- Preserves [ADR-081](./081-project-ownership-authority.md): Project ownership derives from `projects.user_id`, not retrieval relationships.
- Follows [ADR-056](./056-document-lifecycle-graph-control-plane.md): DLG metadata remains source routing and evidence; it cannot create runtime or release proof.

This ADR supersedes none of those decisions.

## Consequences and deferred work

Retrieval budget policy can scale independently of corpus membership. Future exhaustive requests need authorized enumeration, bounded batches, per-source completion accounting, and truthful partial/failure results. Future implementation must add coverage-mode runtime tokens, measured budget envelopes, derivation/authority metadata, receipt persistence and inspection, deletion/revision propagation, and increasing-corpus benchmarks through separate scoped work. No schema, route, UI, provider disclosure policy, or numeric default is decided here.

## Current-truth boundary

This is architecture doctrine only. Current router and broker code do not implement coverage modes or exhaustive-review execution, and no complete recall receipt exists. [Current State](../00-current-state.md) remains authoritative for release support and qualification. This ADR introduces no runtime implementation or release claim.
