# Flow Builder RunReceipt Persistence Model

## Purpose

This document defines the future persistence model for Flow Builder RunReceipt and StepReceipt proof surfaces.

It is persistence planning only and not database/runtime implementation. No schema migration, model, route, worker, receipt table, execution path, validation engine, or UI component exists as a result of this document.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- flow-builder-token-domains.md
- flowdraft-schema-proposal.md
- variable-chip-typed-output-contract.md
- flow-builder-validation-issue-taxonomy.md
- flow-builder-semantic-step-contract.md
- flow-builder-conditional-container-contract.md
- flow-builder-testrun-activation-contract.md
- runtime-protocol-token-contract.md
- canonical-token-philosophy.md
- data-and-storage.md
- account-export-restore-contract.md
- flows.md
- config-and-ops.md

## Interpretation Rules

- RunReceipt is execution proof, not authoring state.
- StepReceipt is step-level proof, not step definition.
- A completed TestRun or active Activation is not full execution proof without receipt evidence once receipts exist.
- Receipt persistence must not silently mutate FlowDraft.
- Receipt event visibility is not the same as durable receipt persistence.
- Task-event publication is not UI receipt.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Conceptual Model

`FlowDraft` is the authored flow state. `CompiledPlan` is the executable interpretation of that draft. `ValidationSummary` decides whether the draft or compiled plan is eligible for further action. `TestRun` and `Activation` are entry records for execution attempts. `RunReceipt` is the durable proof surface for a specific attempt. `StepReceipt` records step-level evidence beneath that run. Command bus, cron, and task events are adjacent possible implementation substrates, but they are not proof that Flow Builder receipt persistence exists.

Proposed relationship diagram:

`FlowDraft -> CompiledPlan -> TestRun or Activation-triggered execution -> RunReceipt -> StepReceipts`

This relationship is proposed only. It is not an implementation claim.

## RunReceipt Definition

`RunReceipt` is:

- the durable proof surface for one Flow Builder execution attempt
- linked to a `FlowDraft` or `CompiledPlan`
- linked to `TestRun` or `Activation` where applicable
- containing summary metadata plus references to step-level evidence
- not a replacement for task events, audit logs, command runs, or chat messages
- not authoring state

## StepReceipt Definition

`StepReceipt` is:

- step-level execution evidence for a specific step attempt
- linked to a `RunReceipt`
- linked to the source step or conditional branch
- able to represent pending, running, skipped, completed, failed, and blocked states
- bounded and safe, not raw hidden prompts or chain-of-thought

## Proposed Shape: RunReceipt

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Identity for the run proof surface. |
| `flow_draft_id` | `FlowDraft` reference | yes | flowdraft-schema-proposal.md | Draft associated with the attempt. |
| `compiled_plan_id` | `CompiledPlan` reference | no | proposed | Present when the attempt used a compiled interpretation. |
| `test_run_id` | `TestRun` reference | no | flow-builder-testrun-activation-contract.md | Nullable depending on run origin. |
| `activation_id` | `Activation` reference | no | flow-builder-testrun-activation-contract.md | Nullable depending on run origin. |
| `initiator_ref` | user or system actor reference | yes | proposed | Who or what initiated the attempt. |
| `trigger_ref` | starter, event, or registration reference | no | proposed | Indicates which trigger path initiated the attempt. |
| `state` | `run_receipt_state` token | yes | flow-builder-token-domains.md | Must align with the canonical receipt state domain. |
| `validation_snapshot_ref` | validation snapshot reference | yes | flow-builder-validation-issue-taxonomy.md | Validation posture used to authorize the attempt. |
| `permission_snapshot_ref` | permission snapshot reference | yes | flow-builder-testrun-activation-contract.md | Permission posture used for the attempt. |
| `step_receipt_refs` | array of step receipt references or embedded summaries | yes | proposed | Step-level evidence for the run. |
| `command_run_refs` | array of command run references | no | data-and-storage.md, flows.md | Adjacent proof surface, not a replacement for the receipt. |
| `task_event_refs` | array of task event references | no | runtime-protocol-token-contract.md, flows.md | Live visibility references, not durable receipt persistence. |
| `audit_log_refs` | array of audit log references | no | data-and-storage.md, config-and-ops.md | Mutation evidence references. |
| `semantic_metadata_summary` | bounded object or summary payload | no | flow-builder-semantic-step-contract.md | Compact semantic evidence summary. |
| `side_effect_summary` | bounded object or summary payload | no | flow-builder-testrun-activation-contract.md | Bounded side-effect proof summary. |
| `provenance` | nested provenance object | yes | account-export-restore-contract.md | Lineage for the proof artifact. |
| `created_at` | timestamp | yes | proposed | When the receipt record was created. |
| `started_at` | timestamp or null | no | proposed | When execution began, if it began. |
| `completed_at` | timestamp or null | no | proposed | When the attempt reached a terminal success or failure state. |
| `cancelled_at` | timestamp or null | no | proposed | When the attempt was cancelled. |
| `failure_reason` | string or structured reason | no | proposed | Human-readable or machine-readable failure context. |

`state` must align with `run_receipt_state`.

`test_run_id` and `activation_id` are nullable depending on run origin.

`step_receipt_refs` may be embedded summaries or references depending on later storage choice.

`command_run_refs`, `task_event_refs`, and `audit_log_refs` are references to adjacent proof surfaces, not replacements for the receipt.

## Proposed Shape: StepReceipt

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Identity for the step-level evidence record. |
| `run_receipt_id` | `RunReceipt` reference | yes | proposed | Parent run proof surface. |
| `source_step_ref` | step reference | yes | flowdraft-schema-proposal.md, flow-builder-semantic-step-contract.md | The authored step under evidence. |
| `source_branch_ref` | branch or nested container reference | no | flow-builder-conditional-container-contract.md | Required when the step is nested under a conditional branch. |
| `state` | `step_receipt_state` token | yes | flow-builder-token-domains.md | Must align with the canonical step receipt state domain. |
| `input_refs` | array of binding or source refs | no | variable-chip-typed-output-contract.md, flow-builder-semantic-step-contract.md | Inputs consumed by the step attempt. |
| `output_refs` | array of output refs | no | variable-chip-typed-output-contract.md, flow-builder-semantic-step-contract.md | Outputs produced by the step attempt. |
| `value_summary` | bounded summary, hash, reference, or redacted payload | yes | proposed | Must stay bounded for sensitive data. |
| `semantic_metadata` | bounded object or summary payload | no | flow-builder-semantic-step-contract.md | Semantic-step evidence when relevant. |
| `condition_metadata` | bounded object or summary payload | no | flow-builder-conditional-container-contract.md | Branch-evaluation evidence when relevant. |
| `side_effect_refs` | array of side-effect references | no | flow-builder-testrun-activation-contract.md, data-and-storage.md | External mutation references where applicable. |
| `started_at` | timestamp or null | no | proposed | When the step attempt began. |
| `completed_at` | timestamp or null | no | proposed | When the step attempt completed. |
| `skipped_at` | timestamp or null | no | proposed | When the step was skipped. |
| `failure_reason` | string or structured reason | no | proposed | Step-specific failure context. |

`state` must align with `step_receipt_state`.

`value_summary` must be bounded, redacted, hash-based, or reference-based for sensitive data.

`source_branch_ref` is required when the step is nested under a `ConditionalContainer` branch.

## State Taxonomy

### `run_receipt_state`

| State | Meaning | Terminal? | Transition notes |
|---|---|---|---|
| `queued` | The attempt is admitted but has not started. | no | May transition to `running` or `cancelled`. |
| `running` | The attempt is in progress. | no | May transition to `completed`, `failed`, `cancelled`, or `blocked`. |
| `completed` | The attempt finished with durable receipt evidence. | yes | Should not transition further. |
| `failed` | The attempt ended in failure. | yes | May be followed by a new attempt, not an in-place retry. |
| `cancelled` | The attempt was intentionally stopped. | yes | Cancellation may occur before or during execution. |
| `blocked` | The attempt was prevented from starting or completing due to policy or validation. | yes | May still emit receipt evidence for the block. |

### `step_receipt_state`

| State | Meaning | Terminal? | Transition notes |
|---|---|---|---|
| `pending` | The step is known in the plan but not yet evaluated. | no | May transition to `running`, `skipped`, `completed`, `failed`, or `blocked`. |
| `running` | The step is actively being evaluated. | no | May transition to `completed`, `failed`, `skipped`, or `blocked`. |
| `skipped` | The step was not executed because branch or plan logic bypassed it. | yes | Skipped steps should remain visible in proof. |
| `completed` | The step finished successfully. | yes | Should not transition further. |
| `failed` | The step ended in failure. | yes | May be followed by a new attempt, not an in-place retry. |
| `blocked` | The step could not proceed due to validation, policy, or dependency failure. | yes | Blocked evidence should remain explicit. |

## Validation and Permission Snapshots

- A `RunReceipt` should reference the `ValidationSummary` used to authorize the attempt.
- A `RunReceipt` should reference the permission snapshot used for the attempt.
- Snapshots must distinguish eligibility from execution success.
- Permission snapshots must capture external-recipient, third-party, local-only, and identity-sensitive posture where applicable.
- If validation or permission posture changes after execution begins, the receipt must preserve the posture used for that attempt.

## Semantic Metadata

Future semantic receipt metadata candidates:

- `semantic_step_kind`
- `uncertainty_outcome`
- `model_policy_ref`
- `allowed_sources_snapshot`
- `redaction_summary`
- `output_schema_ref`
- `failure_reason`

Semantic receipt metadata must not include raw chain-of-thought.

Hidden prompts and raw sensitive inputs should not be stored blindly.

Unknown, low-confidence, or insufficient-evidence outcomes must be visible in receipt evidence.

## Conditional Branch Evidence

- Conditional execution must preserve selected branch evidence.
- Skipped branches must not disappear.
- Skipped nested steps may produce compact skipped `StepReceipt` evidence or skipped refs, depending on later storage choice.
- Branch condition result, evaluated inputs, selected branch, skipped step refs, and executed step refs should be receipted.
- Semantic uncertainty must be represented when it affects branch choice.

## Side-Effect Evidence

- Side effects require receipt evidence.
- Command bus side effects must preserve command run IDs where used.
- External writes must preserve enough reference data for audit without leaking unnecessary sensitive content.
- Partial side-effect failure must be represented explicitly.
- Unreceipted side effects are forbidden.

## Storage Options

| Option | Benefits | Risks | Recommendation |
|---|---|---|---|
| Option A: Dedicated flow_run_receipts table with JSONB receipt body | Simplest first durable model; preserves receipt as a whole artifact; easy to evolve while contracts settle. | Step-level querying is less direct; later normalization may be needed for reporting. | Recommended conservative first step. |
| Option B: Dedicated run_receipts plus normalized step_receipts table | Better step-level queryability and future analytical use; clearer separation of run and step evidence. | Higher schema and migration complexity; more moving parts before contracts are stable. | Good later-stage option if step-level queries become primary. |
| Option C: Reuse existing task-event or command-run tables as receipt storage | Minimizes initial table count. | Conflates live visibility or command proof with durable workflow proof; weakens lineage and contract clarity. | Not recommended. |

Recommend a conservative path, likely Option A for first receipt persistence unless future proof requires normalized `StepReceipt` queries.

## Failure and Cancellation Evidence

- validation failure before execution
- permission snapshot failure
- trigger/activation failure
- execution cancellation before first step
- cancellation during step execution
- semantic step failure
- conditional evaluation failure
- side-effect failure
- receipt persistence failure

Receipt persistence failure must surface as audit/operator evidence and must not look like successful execution proof.

## Relationship to Existing Runtime Surfaces

- Task events may provide live visibility but are not durable `RunReceipt` persistence by themselves.
- Command runs may provide command-specific proof but are not whole-flow receipt proof.
- Audit logs may provide mutation evidence but are not a replacement for structured workflow receipts.
- Future implementation must preserve route acceptance versus completion semantics.
- Future workflow receipt states must not redefine chat request states, provider runtime states, or command bus run states.

## Export and Restore Implications

- `RunReceipt` and `StepReceipt` artifacts are lineage-bearing execution evidence when included in exports.
- Export/restore must preserve receipt IDs, FlowDraft links, compiled plan links, TestRun/Activation links, step refs, state, provenance, timestamps, and side-effect refs where applicable.
- If receipts are excluded from an early export format, the exclusion must be explicit.
- Restore must report unresolved receipt refs, command run refs, or side-effect refs explicitly.
- Silent receipt loss is not allowed if receipts are part of the exported artifact.

## Non-Goals

- No `RunReceipt` implementation.
- No `StepReceipt` implementation.
- No receipt table or migration.
- No SQLAlchemy model.
- No Pydantic model.
- No route implementation.
- No worker implementation.
- No task-event integration.
- No command-bus integration.
- No cron integration.
- No validation engine.
- No UI implementation.
- No TypeScript constants.
- No Python constants.
- No release-surface expansion.

## Implementation Follow-Through

- FB-009 should define the activity/proof surface that presents receipt evidence.
- FB-010 should decide export/restore inclusion for receipts and related workflow artifacts.
- FB-012 should build the first non-side-effecting TestRun proof harness only after receipt storage expectations are contract-backed.
- FB-013 should require durable receipt proof before side-effecting execution is considered complete.
- Future backend implementation must add contract tests before routes or workers persist receipts.

## Open Questions

- Should StepReceipts be embedded in RunReceipt JSONB first or normalized immediately?
- How much value summary can be stored safely for sensitive outputs?
- Should skipped substeps create full StepReceipt rows or compact skipped references?
- Should receipt persistence failure fail the whole run or create degraded execution evidence?
- Which receipt references should be exportable by default?
- How should receipts support replay or idempotency in later execution work?
