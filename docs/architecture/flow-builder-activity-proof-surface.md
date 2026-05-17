# Flow Builder Activity and Proof Surface Design

## Purpose

This document defines the future activity/proof surface design for Flow Builder evidence.

It is design and contract planning only and not UI/runtime implementation. No UI component, route, persistence table, event stream, validation engine, receipt store, or runtime execution path exists as a result of this document.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- flow-builder-token-domains.md
- flowdraft-schema-proposal.md
- flow-builder-validation-issue-taxonomy.md
- flow-builder-testrun-activation-contract.md
- flow-builder-runreceipt-persistence-model.md
- runtime-protocol-token-contract.md
- canonical-token-philosophy.md
- ui-diagrams-v1.md
- runtime-diagrams-v1.md
- data-and-storage.md
- account-export-restore-contract.md
- config-and-ops.md

## Interpretation Rules

- Activity view is not durable receipt storage.
- UI receipt presentation is not task-event publication.
- Task-event visibility is not durable execution proof.
- Validation success is eligibility, not execution success.
- Activation status is not successful run proof.
- A green UI indicator must never collapse validation, activation, execution, and receipt evidence into one ambiguous state.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Conceptual Model

`FlowDraft` is the authored flow state. `ValidationSummary` establishes eligibility posture. `TestRun` and `Activation` are entry records for attempts and durable enablement. `RunReceipt` and `StepReceipt` are the proof surfaces behind the activity view. The activity timeline is the visible narrative layer; the proof detail panel is the selected-evidence inspector. Command bus, cron, and task events are adjacent possible substrates, but they are not the activity surface itself.

Proposed relationship diagram:

`FlowDraft -> Activity Timeline -> selected event -> Proof Detail Panel -> receipt/validation/permission/side-effect evidence refs`

This relationship is proposed only. It is not an implementation claim.

## Surface Goals

- make execution evidence inspectable
- keep authoring state separate from run evidence
- show validation and permission posture used for an attempt
- expose skipped/executed branch evidence
- expose semantic uncertainty without hidden chain-of-thought
- expose side-effect references and degraded states
- avoid treating task events as durable proof
- avoid noisy diagnostics in the primary authoring lane

## Surface Non-Goals

- not a diagnostics dump
- not raw chain-of-thought
- not raw prompt or hidden system-message display
- not a replacement for RunReceipt persistence
- not a replacement for audit logs
- not a replacement for task events
- not a release-readiness badge
- not a general observability deck for all Codexify subsystems

## Proposed Surface Regions

| Region | Purpose | Primary evidence source | Must display | Must not display |
|---|---|---|---|---|
| `ActivityTimeline` | Show the ordered history of draft, validation, activation, and run activity. | RunReceipt, TestRun, Activation, validation snapshots, task-event refs | event type, time, origin, state, and evidence links | raw logs, hidden prompts, or full debug payloads |
| `RunSummaryCard` | Provide a compact summary of one execution attempt or activation-linked run. | RunReceipt and receipt-linked refs | run id, origin, state, timestamps, counts, and major refs | full step payloads or raw event streams |
| `ValidationSnapshotPanel` | Inspect the validation posture used to authorize the attempt. | ValidationSummary refs | issue codes, severities, blocking state, validator version, target refs | chat content, prompt text, or unrelated diagnostics |
| `PermissionSnapshotPanel` | Inspect the effective permission posture used for the attempt. | Permission snapshot refs | posture, risk classes, boundary warnings, local-only posture | raw policy internals or hidden enforcement code |
| `StepReceiptList` | Provide a step-by-step receipt index for the run. | StepReceipt refs | step label, ref, state, timestamps, and evidence status | raw hidden prompts or unbounded trace dumps |
| `StepReceiptDetail` | Show one selected step receipt in bounded detail. | StepReceipt and linked refs | inputs, outputs, semantic metadata, condition metadata, side-effect refs | full chain-of-thought or unreduced prompt state |
| `SemanticMetadataPanel` | Present bounded semantic evidence for AI-assisted steps. | StepReceipt semantic metadata | kind, uncertainty, schema ref, redaction summary, failure reason | raw prompt or hidden message content |
| `ConditionalBranchPanel` | Show branch selection and skipped/evaluated steps. | StepReceipt condition metadata and branch refs | condition result, selected branch, skipped refs, executed refs | collapsing skipped branches into a generic success row |
| `SideEffectEvidencePanel` | Show external mutation evidence and risk posture. | Side-effect refs, audit refs, command run refs | risk class, target scope, refs, and result state | sensitive payload bodies that are not needed for audit |
| `FailureAndCancellationPanel` | Make degraded or failed proof states explicit. | RunReceipt and StepReceipt failure metadata | failure reason, cancellation reason, blocked/degraded state | rendering failures as ordinary success |
| `ExportLineagePanel` | Show how evidence would be reconstructed from export/restore lineage. | Exportable refs and provenance | artifact links, missing refs, export availability | pretending non-exported proof was preserved |

## Proposed Activity Event Types

| Event type | Meaning | Source evidence | Durable proof? | Notes |
|---|---|---|---|---|
| `draft_created` | A FlowDraft was created. | FlowDraft provenance | no | Candidate UI/activity label only until promoted into a canonical registry. |
| `draft_validated` | Validation completed for the draft. | ValidationSummary | no | Reflects eligibility, not execution. |
| `test_run_started` | A TestRun began. | TestRun | no | May later point to receipt refs. |
| `test_run_completed` | A TestRun finished successfully. | TestRun + RunReceipt | partial | Receipt-backed completion is durable, the event label itself is not. |
| `test_run_failed` | A TestRun failed. | TestRun + RunReceipt | partial | Failure must still be visible as proof. |
| `activation_created` | An Activation record was created. | Activation | no | Durable enablement evidence, not execution proof. |
| `activation_paused` | Activation was paused. | Activation | no | Prevents future starter-driven runs. |
| `activation_disabled` | Activation was disabled. | Activation | no | Durable shutdown state. |
| `run_started` | An execution attempt started. | RunReceipt / task-event ref | no | Activity visibility only until receipt exists. |
| `run_completed` | An execution attempt completed. | RunReceipt | yes | Durable only when backed by RunReceipt. |
| `run_failed` | An execution attempt failed. | RunReceipt | yes | Failure is proof, not absence of proof. |
| `run_cancelled` | An execution attempt was cancelled. | RunReceipt | yes | Cancellation evidence must remain visible. |
| `step_started` | A step attempt started. | StepReceipt | no | Step-level visibility. |
| `step_completed` | A step attempt completed. | StepReceipt | yes | Durable when receipt-backed. |
| `step_failed` | A step attempt failed. | StepReceipt | yes | Must keep failure distinct from skip. |
| `step_skipped` | A step was skipped by branch or plan logic. | StepReceipt | yes | Skipped steps must remain visible. |
| `permission_warning` | A permission or trust-boundary warning exists. | Permission snapshot / validation refs | no | Candidate label only until promoted into canonical registry. |
| `side_effect_recorded` | A side effect was attempted or recorded. | Side-effect refs | yes | Should surface target scope and risk class. |
| `receipt_persisted` | Receipt persistence succeeded. | RunReceipt / StepReceipt refs | yes | This is proof of persistence, not execution alone. |
| `receipt_degraded` | Receipt evidence exists but is partial or degraded. | RunReceipt / audit refs | yes | Must never read as clean success. |

These are candidate UI/activity labels only until promoted into canonical token registries.

## Evidence Hierarchy

From strongest to weakest:

1. durable RunReceipt / StepReceipt
1. durable Activation / TestRun record with receipt reference
1. durable validation snapshot
1. audit log reference
1. command run reference
1. task-event stream
1. transient UI state

Weaker surfaces may support live visibility but must not replace stronger durable proof.

## Run Summary Presentation

A `RunSummaryCard` should show:

- run id
- origin: TestRun or Activation
- state
- source FlowDraft / CompiledPlan refs
- validation snapshot ref
- permission snapshot ref
- started/completed/cancelled timestamps
- step counts by state
- side-effect count
- semantic uncertainty summary
- failure/cancellation reason when applicable

## Step Receipt Presentation

A `StepReceiptDetail` should show:

- step label and canonical step ref
- state
- input refs
- output refs
- bounded value summary or redaction notice
- semantic metadata when applicable
- condition metadata when applicable
- side-effect refs when applicable
- timestamps
- failure reason

Sensitive values should be redacted, hash-based, or reference-based.

## Validation and Permission Presentation

- Validation snapshots should show issue codes, severities, blocking state, target refs, and validator version.
- Permission snapshots should show effective posture, risk classes, external-recipient or third-party boundaries, and local-only posture where relevant.
- UI copy must distinguish warnings from blockers.
- Permission warnings must not be hidden behind generic success states.

## Semantic Metadata Presentation

- Show semantic step kind, uncertainty outcome, output schema ref, allowed sources snapshot, redaction summary, and failure reason when applicable.
- Do not display raw chain-of-thought.
- Do not blindly display hidden prompts or raw sensitive inputs.
- `unknown`, `low_confidence`, and `insufficient_evidence` must be visible when they affect execution or branch choice.

## Conditional Branch Presentation

- Show condition ref, condition result, selected branch, skipped step refs, executed step refs, and uncertainty outcome where applicable.
- Skipped branches must not disappear.
- UI should make skipped versus failed visually and semantically distinct.
- Branch presentation must preserve nested step order.

## Side-Effect Evidence Presentation

- Show side-effect type, risk class, target service/scope, command run ref where applicable, audit ref where applicable, and result state.
- External writes and third-party sharing must be visible.
- Partial side-effect failures must be visible.
- Unreceipted side effects must surface as severe proof degradation.

## Failure and Degraded Proof States

Must cover:

- validation failure before run
- permission snapshot failure
- trigger registration failure
- execution failure
- semantic uncertainty block
- conditional evaluation failure
- side-effect failure
- receipt persistence failure
- task-event visibility loss

Degraded proof must be shown explicitly and must not be rendered as ordinary success.

## UI Placement and Interaction Model

- The activity/proof surface should be accessed from Flow Builder activity context, not injected into ordinary chat messages.
- Activity inspection should be opt-in.
- The authoring lane should remain clean.
- Diagnostic-level raw traces should remain in diagnostics or developer-mode surfaces.
- Future UI must follow Codexify token and layout discipline.
- The surface may later integrate with Workspace/Inspector only if it preserves the distinction between artifact inspection and runtime proof.

## Relationship to Existing Runtime Surfaces

- Task events provide live progress visibility, not durable proof by themselves.
- Command runs provide command-specific evidence, not whole-flow proof.
- Audit logs provide mutation evidence, not full workflow proof.
- Existing `/api/events` or `/api/tasks/*/events` surfaces must not be reinterpreted as Flow Builder receipt storage.
- Future activity UI may aggregate these references, but the RunReceipt remains the workflow proof anchor.

## Export and Restore Implications

- Activity/proof presentation should be reconstructable from exported FlowDraft, TestRun, Activation, RunReceipt, StepReceipt, and audit/reference artifacts when included.
- Export/restore must preserve enough references to reconstruct meaningful activity history.
- If activity history is not exported, the exclusion must be explicit.
- Restore must report unresolved receipt refs, side-effect refs, command run refs, or audit refs explicitly.
- Silent proof-history loss is not allowed when proof artifacts are included in export.

## Non-Goals

- No UI implementation.
- No route implementation.
- No receipt persistence implementation.
- No event-stream implementation.
- No schema migration.
- No SQLAlchemy model.
- No Pydantic model.
- No TypeScript constants.
- No Python constants.
- No validation engine.
- No TestRun, Activation, RunReceipt, or StepReceipt implementation.
- No release-surface expansion.

## Implementation Follow-Through

- FB-010 should decide export/restore inclusion for Flow Builder proof artifacts.
- FB-011 should prototype the frontend shell only after proof-surface fixtures exist.
- FB-012 should make the first non-side-effecting TestRun proof harness generate inspectable receipt evidence.
- FB-013 should require proof-surface visibility before side-effecting execution is considered complete.
- Future UI work must use fixtures that distinguish validation success, activation, execution success, skipped steps, failure, and degraded proof.

## Open Questions

- Should activity events become canonical backend tokens or remain UI labels derived from receipt state?
- Should StepReceipt details be expandable inline or only in a side inspector?
- Should degraded proof states block “successful” presentation even when execution completed?
- How much side-effect target detail can be shown safely?
- Should activity history be exportable in v1 or reconstructed only from receipts?
- Which proof-surface fields must be included in account export/restore v1?
