---
tags:
* architecture
* adr
* execution-ledger
* campaign-runner
* governance
  aliases:
* ADR-028
* Execution Ledger Campaign Runner Contract
---

# ADR-028: Execution Ledger Campaign Runner Contract

## Status

Accepted

## Date

2026-05-15

## Context

AI coding agents need bounded, durable, and reviewable execution units that can be traced from intent through proof. Backlog-style workflows are useful for this, but Codexify must reuse repo-native rails rather than introduce a parallel runtime control plane.

Repo-aware reconnaissance concluded that Execution Ledger should extend existing Campaign Runner surfaces (`campaign_goals`, `campaigns`, `coding_work_orders`, `campaign_execution_attempts`) plus Guardian-mediated execution and lineage seams, rather than create a second canonical runtime truth surface (for example, a standalone `.codexify/tasks/` control plane).

Codexify already has Campaign Runner MVP surfaces, Guardian-mediated coding-agent execution, command bus contracts, Codex/artifact lineage seams, agent run/event stores, and Command Center work-order visibility. The missing architecture contract is a canonical cross-seam definition for task identity, review gates, implementation plans, acceptance criteria, and attempt evidence.

## Current-Truth Anchors

- Codexify currently has Campaign Runner MVP durable surfaces.
- Codexify currently has Guardian-mediated coding-agent execution.
- Codexify currently has command bus, Codex/artifact lineage, agent run/event stores, and Command Center work-order surfaces.
- Supported release posture remains local Docker Compose and local-only unless `docs/architecture/00-current-state.md` explicitly widens that claim.
- Route acceptance is not completion.
- Task-event publication is not UI receipt.
- File artifacts are not canonical runtime truth when current architecture assigns durable truth to Postgres-backed stores.
- Execution Ledger does not introduce release-true autonomous dispatch, merge automation, or hands-free progression through review gates.

## Decision

Execution Ledger is defined as a governed Campaign Runner extension.

1. `campaign_goals` and `campaigns` remain the top-level durable planning containers.
2. `coding_work_orders` are the canonical atomic execution units for ledger-backed implementation work.
3. `campaign_execution_attempts` and Guardian run/attempt records remain the durable execution evidence surface.
4. Guardian-mediated coding execution remains the governed execution path for coding-agent work.
5. Command bus remains the governed command invocation path.
6. Codex/artifact lineage remains the provenance doctrine for source thread/message linkage.
7. Command Center remains the first operator-facing surface for read-only ledger visibility.
8. Docs task artifacts may serve as planning artifacts, but they are not canonical runtime truth.
9. New runtime-visible status/event/error literals must use canonical token governance before use.
10. Execution Ledger must not introduce autonomous dispatch, merge automation, or hidden progression unless a later ADR explicitly widens the contract.

## Canonical Ledger Concepts

- Ledger campaign: a campaign-scoped planning and execution arc rooted in existing campaign entities.
- Ledger work order: the atomic implementation unit mapped to canonical `coding_work_orders` identity.
- Implementation plan: a pre-execution, reviewable plan artifact linked to one ledger work order.
- Acceptance criteria: explicit testable constraints and proof obligations that bound scope and completion claims.
- Intent/scope review gate: pre-plan gate that confirms the work order is correctly framed and bounded.
- Plan review gate: pre-execution gate that approves the implementation plan.
- Completion/proof review gate: post-execution gate that evaluates durable attempt evidence and validation proof.
- Attempt evidence: durable run/attempt records, task events, validation output, and related lineage records.
- Completion receipt: the bounded result record that links task outcome claims to durable attempt evidence.
- Follow-up work order: a newly bounded downstream work order created when proof or scope review identifies remaining work.

## Identity Model

- Campaign identity is durable at the campaign layer.
- Work-order identity is the atomic task identity.
- Attempt identity is separate from work-order identity.
- Guardian run identity is execution-attempt evidence, not the authored task itself.
- Source thread/message lineage must be preserved when ledger artifacts originate from chat or Codex artifacts.
- Message identity versus attempt identity semantics must remain compatible with the chat runtime contract.

## Gate Semantics

Gate approval does not itself prove runtime completion. Completion/proof review must be based on durable attempt evidence, validation output, and a completion receipt.

### 1. Intent/scope review gate

- Purpose: confirm intent, boundaries, and anti-scope-creep constraints before plan authoring.
- Owner: task requester and designated reviewer (human/operator).
- Required input: ledger work-order draft, scope statement, initial acceptance criteria draft.
- Required output: approved or rejected scope decision with rationale.
- Allowed state change: conceptual transition from `scope_draft` to `scope_approved` or `scope_rejected` (contract terms only, not runtime tokens yet).
- Evidence that must be recorded: reviewer decision, timestamp, rationale, and bounded scope artifact reference.
- Must not imply: execution started, runtime completion, or proof satisfied.

### 2. Implementation plan review gate

- Purpose: approve an explicit implementation plan before execution attempts are allowed.
- Owner: implementation reviewer and accountable operator.
- Required input: linked implementation plan artifact, updated acceptance criteria, declared validation plan.
- Required output: approved or rejected plan decision with required revisions when rejected.
- Allowed state change: conceptual transition from `plan_draft` to `plan_approved` or `plan_rejected` (contract terms only, not runtime tokens yet).
- Evidence that must be recorded: plan artifact reference, reviewer decision, rationale, and review timestamp.
- Must not imply: successful execution, tests passed, or delivery complete.

### 3. Completion/proof review gate

- Purpose: determine whether work-order completion claims are supported by durable proof.
- Owner: proof reviewer (human/operator) accountable for completion acceptance.
- Required input: attempt evidence, validation command output, completion receipt, and lineage references.
- Required output: completion decision (`accepted`, `rejected`, or `follow_up_required` as conceptual outcomes pending token governance).
- Allowed state change: conceptual transition from `proof_pending` to `proof_accepted`, `proof_rejected`, or `follow_up_required` (contract terms only, not runtime tokens yet).
- Evidence that must be recorded: attempt/run identifiers, validation outputs, receipt reference, reviewer decision, and rationale.
- Must not imply: UI receipt guarantees, release widening, or autonomous downstream dispatch.

## Acceptance Criteria Semantics

Acceptance criteria are mandatory contract artifacts, not freeform prompt decoration. They define:

- testable scope constraints
- validation expectations
- proof obligations
- anti-scope-creep boundaries

Acceptance criteria must be explicit enough to evaluate completion/proof review using durable evidence.

## Plan Semantics

Implementation plans are:

- explicit pre-execution artifacts
- linked to a work order
- reviewed before execution
- non-authoritative until approved
- not a substitute for runtime proof

An approved plan authorizes execution attempts; it does not claim completion.

## Runtime Boundary

This ADR does not implement runtime behavior. It governs future implementation.

Future runtime work must preserve:

- route acceptance is not completion
- task-event publication is not UI receipt
- Postgres-backed stores remain durable orchestration truth where current architecture says so
- Redis remains operational transport, not canonical ledger truth
- graph writes remain default-off unless separately governed
- command bus and Guardian orchestration policy seams must not be bypassed

## UI Boundary

- Command Center is the first appropriate operator-facing surface.
- Initial UI work should be read-only unless a later task explicitly adds reviewed mutations.
- Execution Ledger must not create a separate diagnostics surface outside approved Command Center and diagnostics doctrine.

## File Artifact Boundary

- `docs/Campaign/` and `docs/tasks/` can remain human-readable planning artifacts.
- File artifacts may link to campaign/work-order IDs.
- File artifacts must not become canonical execution truth unless a later ADR explicitly changes the persistence model.
- A parallel `.codexify/tasks/` runtime control plane is rejected for current Codexify architecture unless a future ADR supersedes this decision.

## Token Governance

- New repeated contract-bearing ledger literals must be canonicalized.
- Candidate token domains include:
  - ledger gate states
  - plan states
  - acceptance-criteria validation statuses
  - completion/proof decisions
  - escalation reasons
- Runtime-visible tokens belong in `guardian/protocol_tokens.py` or another bounded canonical registry approved by later implementation.
- Frontend must mirror backend canon and must not invent independent literals.

## Consequences

### Positive

- avoids duplicate task truth
- reuses Campaign Runner rails
- preserves Guardian ownership of execution
- keeps lineage and attempt evidence coherent
- gives Command Center a clean expansion path

### Tradeoffs

- requires implementation discipline
- may require future schema work
- may require token migration
- slows implementation slightly to prevent drift

## Non-Goals

ADR-028 does not:

- add migrations
- add routes
- add UI
- add MCP tools
- add CLI commands
- add autonomous dispatch
- add merge automation
- change Campaign Runner behavior
- change work-order behavior
- change command bus behavior
- change Guardian coding execution behavior
- change provider routing
- change retrieval routing
- change identity or persona modeling

## Invariants

- no unreviewed architecture drift
- no prompt-only control plane
- no duplicate canonical truth surface
- no private identity/persona leakage into public task artifacts
- no durable trait inference through task artifacts
- no bypass of command bus or Guardian-mediated orchestration policy seams
- no runtime statuses outside canonical token governance
- no release-promise widening
- no acceptance/completion collapse
- no event-publication/UI-receipt collapse

## Follow-Up Work

1. Add Execution Ledger docs contract for gate artifacts and acceptance-criteria mapping.
2. Add canonical token proposal and contract tests if new token domains are needed.
3. Add backend store/route extensions only after proving existing fields are insufficient.
4. Add Command Center read-only ledger/gate visibility.
5. Add controlled progression workflow only under a separate reviewed architecture task.

## Links

- [[ADR Index]]
- [[001-Queue-Based-Completion-Acceptance-Model|ADR-001 Queue-Based Completion Acceptance Model]]
- [[002-Dual-State-Machine-Model|ADR-002 Dual State Machine Model]]
- [[006-flow-builder-elicitation-lane|ADR-006 Flow Builder Elicitation Lane]]
- [[014-Flow-Builder-Thread-Draft-and-Receipts-Contract|ADR-014 Flow Builder Thread, Draft, and Receipts Contract]]
- [[020-Guardian-Mediated-Coding-Agent-Execution-Contract|ADR-020 Guardian Mediated Coding Agent Execution Contract]]
- [[022-Guardian-Intent-Spine-and-Cross-Surface-Control-Plane|ADR-022 Guardian Intent Spine and Cross-Surface Control Plane]]
- [[024-Context-Command-and-Active-Connector-Semantics|ADR-024 Context Command and Active Connector Semantics]]
- [[027-flow-builder-typed-surface-and-run-receipt-contract|ADR-027 Flow Builder Typed Surface and Run Receipt Contract]]
- [[runtime-protocol-token-contract|Runtime Protocol Token Contract]]
- [[chat-runtime-contract|Chat Runtime Contract]]
- [[account-export-restore-contract|Account Export + Restore Contract]]
- [[self-extending-agent-plugin-system|Self-Extending Agent Plugin System]]
- [[00-current-state]]
