---
tags:
  - architecture
  - adr
  - campaign-runner
  - pi-loop-manager
  - execution-ledger
  - proposed
aliases:
  - ADR-041
  - Pi Loop Manager Campaign Runner Gate Graph
---

# ADR-041: Pi Loop Manager Campaign Runner Gate Graph

## Status

Proposed

## Date

2026-07-03

## Context

Campaign Runner now has a bounded Pi Loop Manager v0 dry-run receipt spine. The implementation establishes local loop mechanics for a single task: task spec intake, gate sequencing, provider abstraction, policy checks, artifact emission, validation capture, and final receipt output.

This creates a new execution-adjacent seam that Codexify can eventually adopt as governed evidence for WorkOrder attempts. It must not be treated as a new canonical control plane, autonomous dispatcher, merge authority, or durable runtime truth source.

Codexify already has the Execution Ledger and Campaign Runner governance posture from ADR-028. ADR-028 keeps `campaign_goals`, `campaigns`, `coding_work_orders`, and `campaign_execution_attempts` as the durable planning and evidence surfaces, and explicitly rejects duplicate runtime truth planes, hidden autonomous dispatch, and acceptance/completion collapse.

ADR-036 and ADR-037 further establish that Campaign Runner should use provider adapters rather than hardcoded provider assumptions, and that Pi is a preferred lightweight provider-broker seam when available without becoming Campaign Runner core or a mandatory global runtime.

## Decision

Codexify may adopt Campaign Runner Pi Loop Manager receipts as bounded attempt evidence, not as durable control-plane truth.

The adoption boundary is:

1. Campaign Runner owns local loop mechanics for one bounded task attempt.
2. Pi Loop Manager owns gate sequencing inside that attempt.
3. Pi Loop Manager emits receipts, artifacts, validation logs, and handoffs.
4. Codexify remains the durable authority for WorkOrders, Execution Ledger identity, attempt records, review gates, lifecycle state, and operator-visible truth.
5. Whoosh'd remains substrate-only and may be used only through a provider adapter or OpenAI-compatible inference surface. It does not gain WorkOrder, ADR, receipt, dispatch, or documentation authority.
6. Receipts are evidence inputs. They do not directly mutate `coding_work_orders`, trigger dispatch, approve completion, create merge readiness, or bypass human/operator review.
7. Any future durable ingestion must be implemented as a separate reviewed task that maps receipt fields into Codexify-owned attempt evidence records with explicit lineage.

## Definitions

### Pi Loop Manager

A Campaign Runner-local bounded loop engine for one task attempt. It may plan, create execution packets, call a provider adapter, inspect declared changes, run or capture validation evidence, enforce policy gates, and emit receipts.

### Gate Graph

A sequence of typed gates such as context curation, architecture impact review, ADR policy review, planning, execution, inspection, validation, documentation review, and receipt writing. These gates are policy functions, not autonomous personas.

### Loop Receipt

A bounded artifact produced by Pi Loop Manager that summarizes attempt outcome, stop reason, validation evidence, proposed changed paths, ADR impact, documentation impact, and follow-up recommendations.

### Durable Attempt Evidence

Codexify-owned evidence linked to an Execution Ledger attempt or Guardian run/attempt record. A loop receipt can become part of durable attempt evidence only after explicit ingestion through a governed Codexify path.

## Receipt Trust Boundary

A Pi Loop Manager receipt may support claims about:

- task spec used for the attempt.
- loop gates that ran.
- provider adapter selected.
- stop reason declared by the loop.
- validation commands captured by the loop.
- artifacts emitted under the run directory.
- proposed or provider-declared changed paths.
- policy classifications made by the loop.

A Pi Loop Manager receipt must not independently prove:

- WorkOrder completion.
- merge readiness.
- production readiness.
- UI-visible completion.
- live runtime support.
- database state mutation.
- successful Codexify ingestion.
- accepted ADR status.
- provider truth beyond recorded adapter output.
- release-surface widening.

## Required Ingestion Fields

A future Codexify ingestion path must preserve, at minimum:

- `task_id`
- `work_order_id` when available
- `run_id`
- `attempt_id` or mapped Codexify attempt identity
- `loop_status`
- `stop_reason`
- `provider_kind`
- `provider_receipt_ref` when available
- `gate_receipts`
- `validation_commands`
- `validation_outputs` or artifact references
- `changed_paths`
- `evidence_refs`
- `adr_impact`
- `documentation_impact`
- `operator_review_required`
- `follow_up_recommendations`
- source artifact path or object reference
- ingestion timestamp
- ingestion actor or service identity

## Operator Review Gates

Operator review remains required before any Codexify durable or mutating adoption when a receipt indicates or implies:

- UI or UX changes.
- design token changes.
- architecture contract changes.
- runtime state-machine changes.
- provider or broker boundary changes.
- queue, worker, lease, or dispatch behavior changes.
- database/schema changes.
- identity, memory, persona, or privacy behavior changes.
- accepted ADR mutation.
- release-readiness claims.
- merge automation.
- autonomous progression.

## Deferred Behavior

This ADR does not approve:

- autonomous dispatch.
- WorkOrder lifecycle mutation from loop receipts.
- merge automation.
- automatic completion acceptance.
- Command Center mutation controls.
- Whoosh'd provider integration.
- patch-applying local execution as a Codexify-supported path.
- durable receipt ingestion.
- accepted ADR promotion by agents.

Each deferred behavior requires a separate reviewed task and, where architecture-impacting, ADR alignment.

## Documentation Authority

Campaign Runner may write local run artifacts and handoff documents for loop execution.

Codexify canonical architecture documents, accepted ADRs, current-state docs, design tokens, and operator truth surfaces remain read-only by default for agentic loop outputs unless an explicit task grants authority and review gates are satisfied.

Proposed ADRs and proposed specs may be created under proposal paths, but they are not accepted truth until reviewed and promoted by the operator or an approved governance path.

## Consequences

### Positive

- Keeps the Pi Loop Manager useful without granting it authority it should not hold.
- Gives Codexify a clean path to ingest loop evidence later.
- Preserves Campaign Runner as the loop mechanics home.
- Preserves Codexify as durable orchestration truth.
- Keeps Whoosh'd as runtime substrate rather than orchestration owner.
- Prevents receipt production from becoming completion theater.

### Tradeoffs

- Adds a documentation step before runtime integration.
- Slows mutating automation until receipt semantics are reviewed.
- Requires future mapping between Campaign Runner receipt shape and Codexify attempt evidence shape.
- Keeps v0 dry-run evidence useful but intentionally non-authoritative.

## Non-Goals

This ADR does not:

- implement migrations.
- add routes.
- add UI.
- modify Campaign Runner code.
- modify Whoosh'd code.
- ingest receipts into Codexify.
- create new runtime tokens.
- approve autonomous dispatch.
- approve merge automation.
- promote this proposed ADR to accepted status.

## Invariants

- Receipt is evidence, not truth.
- Acceptance is not completion.
- Validation output is scoped proof, not global release proof.
- File artifacts are not durable runtime truth when architecture assigns truth to Postgres-backed stores.
- Campaign Runner loop mechanics must not bypass Guardian or Execution Ledger boundaries.
- Provider adapters must remain replaceable.
- Whoosh'd must remain substrate-only.
- Operator review gates must remain explicit before mutating adoption.
- Accepted ADRs must not be mutated by loop output.

## Required Follow-Up Work

1. Add `docs/specs/campaign-runner/PI_LOOP_MANAGER_ADOPTION_CONTRACT.md`.
2. Review Campaign Runner loop receipt schema against this contract.
3. Add a future Codexify ingestion design only after field mapping is stable.
4. Add Command Center read-only visibility only after durable ingestion semantics are approved.
5. Add provider integrations only through adapter boundaries.

## Links

- ADR-028: Execution Ledger Campaign Runner Contract
- ADR-036: Campaign Runner Provider Adapter Contract
- ADR-037: Campaign Runner Pi Provider Broker
- `docs/specs/campaign-runner/PI_LOOP_MANAGER_ADOPTION_CONTRACT.md`
