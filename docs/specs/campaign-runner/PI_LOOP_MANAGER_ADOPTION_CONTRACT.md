# Pi Loop Manager Adoption Contract

## Status

Draft contract for proposed ADR-041.

## Purpose

Define how Codexify may treat Campaign Runner Pi Loop Manager v0 outputs without confusing local loop receipts with durable Codexify control-plane truth.

This contract exists before any mutating runtime integration. It is intentionally conservative.

## Scope

This contract covers:

- Campaign Runner Pi Loop Manager receipts.
- Codexify receipt review and future ingestion boundaries.
- WorkOrder / Execution Ledger ownership.
- trust limits for dry-run and future execution receipts.
- operator review gates before durable or mutating adoption.
- explicit deferrals for dispatch, merge automation, and autonomous progression.

This contract does not implement runtime behavior.

## System Ownership

| Surface | Owner | Authority |
|---|---|---|
| Pi Loop Manager | Campaign Runner | Bounded local loop mechanics for one task attempt |
| Loop receipts | Campaign Runner output, Codexify evidence input | Evidence only until ingested through a governed Codexify path |
| WorkOrders | Codexify | Durable atomic task identity and lifecycle |
| Execution Ledger attempts | Codexify | Durable attempt evidence and review linkage |
| Guardian-mediated execution | Codexify | Governed execution boundary |
| Command Center | Codexify | Operator-visible truth surface |
| Whoosh'd | Whoosh'd | Optional inference/runtime substrate only |

## Adoption Rule

Codexify may reference Pi Loop Manager receipts as attempt evidence.

Codexify must not treat Pi Loop Manager receipts as direct authority to:

- mutate WorkOrder state.
- approve completion.
- mark work as merge-ready.
- dispatch downstream work.
- widen release claims.
- bypass Guardian mediation.
- bypass operator review.
- mutate accepted ADRs or canonical docs.

## Receipt-As-Evidence Semantics

A receipt can be used as evidence for a bounded attempt only when it preserves source lineage and artifact references.

A receipt can say:

- what task spec was used.
- what gates ran.
- what provider adapter was invoked.
- what status the loop returned.
- why the loop stopped.
- what validation commands were captured.
- what artifacts were emitted.
- what paths were provider-declared or proposed as changed.
- whether operator review is required.

A receipt cannot, by itself, say:

- the WorkOrder is complete.
- the code is merged.
- the product is release-ready.
- live runtime support is proven.
- a UI receipt was shown to the operator.
- accepted architecture changed.
- durable Codexify state changed.

## Receipt Classification

Codexify should classify incoming loop receipts using the following dimensions:

```text
receipt_mode:
  dry_run
  patch_producing
  local_execution
  durable_ingested
```

```text
receipt_trust_level:
  artifact_only
  validation_captured
  validation_passed
  operator_reviewed
  durable_evidence_ingested
```

```text
receipt_actionability:
  observe_only
  review_required
  follow_up_work_order_candidate
  ingestion_candidate
```

For Pi Loop Manager v0, the expected classification is:

```yaml
receipt_mode: dry_run
receipt_trust_level: validation_captured
receipt_actionability: review_required
```

## Required Receipt Fields

A Codexify-compatible loop receipt should include:

```yaml
task_id: string
work_order_id: string | null
run_id: string
attempt: integer | null
loop_status: string
stop_reason: string
provider_kind: string
provider_receipt_ref: string | null
gate_receipts: list
validation_commands: list
validation_outputs: list | artifact refs
changed_paths: list
evidence_refs: list
adr_impact: string
documentation_impact: string
operator_review_required: boolean
follow_up_recommendations: list
artifact_root: string
ingestion_timestamp: string | null
ingestion_actor: string | null
```

If fields are missing, the receipt may still be preserved as an artifact, but it should not be treated as durable attempt evidence without an explicit review decision.

## Gate Receipt Expectations

Each gate receipt should preserve:

```yaml
gate_id: string
gate_status: string
summary: string
evidence_refs: list
changed_paths: list
adr_impact: string
documentation_impact: string
next_gate: string | null
stop_reason: string | null
```

Gate failures or ambiguous gate state should fail closed to `review_required` or `blocked` at the Codexify adoption boundary.

## WorkOrder Mapping

A future ingestion path may map loop receipt fields to Codexify surfaces as follows:

| Loop receipt field | Codexify target | Notes |
|---|---|---|
| `work_order_id` | `coding_work_orders.id` | Must already exist or require operator mapping |
| `run_id` | Guardian / attempt lineage | Must not replace WorkOrder identity |
| `loop_status` | attempt evidence status | Must not directly mutate WorkOrder lifecycle |
| `stop_reason` | attempt evidence reason | Should use canonical token review before runtime visibility |
| `validation_outputs` | durable attempt evidence artifact refs | Preserve raw logs or stable artifact pointers |
| `operator_review_required` | review gate signal | Must not auto-resolve |
| `follow_up_recommendations` | follow-up WorkOrder candidates | Must remain candidates until accepted |

## Lifecycle Boundary

Pi Loop Manager output may support a future review decision, but it must not directly transition WorkOrders.

Allowed future interpretation:

```text
loop receipt passed
  -> proof review candidate
  -> operator or governed review evaluates evidence
  -> Codexify may record durable attempt evidence
```

Forbidden interpretation:

```text
loop receipt passed
  -> WorkOrder complete
  -> merge ready
  -> downstream dispatch
```

## Operator Review Gates

Operator review is required before Codexify accepts or acts on receipts involving:

- UI or UX changes.
- design token changes.
- public-facing copy changes.
- accepted ADR changes.
- architecture contract changes.
- runtime state-machine changes.
- database/schema changes.
- provider/broker boundary changes.
- queue, worker, lease, or dispatch behavior changes.
- identity, memory, persona, or privacy behavior changes.
- release-readiness claims.
- merge automation.
- autonomous progression.

## Documentation Authority

Receipts and handoffs may point to proposed documentation.

They may not promote proposed documentation to canonical truth.

Agent-generated docs should be classified as:

```text
operational artifact
handoff
proposal
canonical change request
```

Canonical docs remain read-only by default:

- accepted ADRs.
- `docs/architecture/00-current-state.md`.
- runtime contracts.
- design tokens.
- release-readiness docs.
- operator truth doctrine.

## Provider Boundary

Pi Loop Manager must call providers through adapters.

Codexify adoption must not assume a direct provider identity unless the receipt records it.

Whoosh'd may serve as an OpenAI-compatible inference substrate through an adapter, but Whoosh'd must not gain authority over:

- WorkOrders.
- Execution Ledger attempts.
- ADR policy.
- documentation authority.
- dispatch.
- merge readiness.
- completion review.

## Validation Boundary

Validation evidence proves only what was actually checked.

Dry-run validation proves the loop can produce and classify evidence. It does not prove applied code changes unless the loop actually applies patches and runs validation against the mutated workspace.

Validation outputs should record:

- command.
- exit code.
- stdout/stderr or artifact reference.
- run location.
- timestamp when available.
- whether the command was declared by the task spec or suggested by the loop.

Suggested commands may be useful, but only executed and recorded commands count as evidence.

## Deferrals

The following remain deferred until separate reviewed tasks exist:

1. Patch-applying local execution.
2. Real provider adapter beyond stub/manual handoff.
3. Whoosh'd/OpenAI-compatible provider adapter.
4. Codexify durable receipt ingestion.
5. WorkOrder lifecycle mutation from receipts.
6. Command Center read-only receipt visibility.
7. Command Center mutation controls.
8. autonomous dispatch.
9. merge automation.
10. accepted ADR promotion by agents.

## Minimal Future Ingestion Flow

A future ingestion path should follow this shape:

```text
Campaign Runner loop receipt
  -> Codexify ingestion endpoint or worker
  -> schema validation
  -> WorkOrder identity resolution
  -> artifact reference preservation
  -> attempt evidence record creation
  -> proof review state set to pending
  -> Command Center read-only visibility
```

The ingestion path should not perform completion acceptance, merge readiness, or dispatch.

## Acceptance Criteria For This Contract

This contract is sufficient for the next implementation slice when:

- the receipt-as-evidence rule is explicit.
- WorkOrder and Execution Ledger ownership remain in Codexify.
- required receipt fields are listed.
- trust limits are documented.
- operator review gates are listed.
- Whoosh'd remains substrate-only.
- dispatch, merge automation, and autonomous progression are explicitly deferred.
- no runtime behavior is implemented by this document.

## Recommended Next Tasks

1. Review the Campaign Runner Pi Loop Manager v0 receipt schema against Required Receipt Fields.
2. Add a Codexify proof-only fixture using a sample loop receipt.
3. Draft a future ingestion task that stores receipt artifacts as attempt evidence without mutating WorkOrder lifecycle.
4. Add Command Center read-only receipt visibility only after ingestion semantics are approved.
