# Flow Builder TestRun and Activation Contract

## Purpose

This document defines the future backend contract for Flow Builder TestRun and Activation records.

It is contract planning only and not backend/runtime implementation. No schema migration, route, worker, trigger registry, command-bus integration, cron integration, execution path, validation engine, or UI component exists as a result of this document.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- flow-builder-token-domains.md
- flowdraft-schema-proposal.md
- flow-builder-validation-issue-taxonomy.md
- flow-builder-semantic-step-contract.md
- flow-builder-conditional-container-contract.md
- runtime-protocol-token-contract.md
- canonical-token-philosophy.md
- agent-tool-loop-contract.md
- data-and-storage.md
- flows.md
- config-and-ops.md

## Interpretation Rules

- TestRun is not Activation.
- Activation is not successful execution.
- Validation success is eligibility, not execution proof.
- Route acceptance is not completion.
- Task-event publication is not UI receipt.
- Receipt evidence is the future proof surface for execution attempts.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Conceptual Model

`FlowDraft` is the authored flow state. `CompiledPlan` is the executable interpretation of that draft. `ValidationSummary` decides whether the draft or compiled plan is eligible for further action. `TestRun` is a bounded execution attempt against a draft or compiled plan. `Activation` is the durable enablement state for future starter-driven execution. `RunReceipt` is the proof surface for a particular execution attempt. Command bus and cron are adjacent possible implementation substrates, but they are not evidence that Flow Builder execution support exists.

Proposed relationship diagram:

`FlowDraft -> validate -> CompiledPlan -> TestRun OR Activation -> execution attempt -> RunReceipt`

This relationship is proposed only. It is not an implementation claim.

## TestRun Definition

A `TestRun` is:

- an explicit execution attempt against a `FlowDraft` or `CompiledPlan`
- primarily intended for validation and proof before activation
- not durable activation
- not release support by itself
- non-side-effecting by default unless a future explicit gate permits otherwise
- receipt-producing when implementation exists

## Activation Definition

An `Activation` is:

- a durable enablement or subscription state for a valid flow
- the record that permits future starter-driven execution
- stricter than `TestRun` eligibility
- separate from any one execution attempt
- not proof that execution has succeeded
- receipt-producing only when an activation triggers a run

## Proposed Shape: TestRun

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Identity for the execution attempt. |
| `flow_draft_id` | `FlowDraft` reference | yes | flowdraft-schema-proposal.md | Draft under test. |
| `compiled_plan_id` | `CompiledPlan` reference | no | proposed | May be present when a compiled interpretation is used. |
| `initiated_by_user_id` | user reference | yes | proposed | Who started the test run. |
| `state` | `test_run_state` token | yes | flow-builder-token-domains.md | Must align with the canonical state domain. |
| `validation_snapshot_ref` | validation snapshot reference | yes | flow-builder-validation-issue-taxonomy.md | Points to the validation state used to admit the run. |
| `input_overrides` | object or structured override payload | no | proposed | Optional run-specific overrides for non-destructive testing. |
| `side_effect_mode` | token or mode object | yes | proposed | Should default to non-side-effecting behavior. |
| `permission_snapshot` | object or reference | yes | proposed | Effective permission posture used for the run. |
| `run_receipt_ref` | receipt reference | no | data-and-storage.md, flows.md | Links to evidence but does not store full receipt evidence inside the TestRun. |
| `created_at` | timestamp | yes | proposed | When the test run record was created. |
| `started_at` | timestamp or null | no | proposed | When execution began, if it began. |
| `completed_at` | timestamp or null | no | proposed | When execution finished successfully or terminally. |
| `cancelled_at` | timestamp or null | no | proposed | When the run was cancelled. |
| `failure_reason` | string or structured reason | no | proposed | Human-readable or machine-readable failure context. |

`state` must align with `test_run_state`.

`side_effect_mode` should default to non-side-effecting behavior.

`run_receipt_ref` links to evidence but does not store full receipt evidence inside the `TestRun`.

## Proposed Shape: Activation

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Identity for the durable enablement record. |
| `flow_draft_id` | `FlowDraft` reference | yes | flowdraft-schema-proposal.md | Draft being activated. |
| `compiled_plan_id` | `CompiledPlan` reference | yes | proposed | Executable interpretation associated with activation. |
| `activated_by_user_id` | user reference | yes | proposed | Who enabled the flow. |
| `state` | `activation_state` token | yes | flow-builder-token-domains.md | Must align with the canonical activation domain. |
| `starter_ref` | starter reference | yes | flowdraft-schema-proposal.md | Which starter this activation enables. |
| `validation_snapshot_ref` | validation snapshot reference | yes | flow-builder-validation-issue-taxonomy.md | Validation state used to admit activation. |
| `permission_snapshot` | object or reference | yes | proposed | Effective permission posture at activation time. |
| `trigger_registration_ref` | trigger registration reference | no | proposed | May point to a durable registration, but this document does not implement registration. |
| `last_run_receipt_ref` | receipt reference | no | data-and-storage.md, flows.md | Most recent run evidence linked to the activation. |
| `created_at` | timestamp | yes | proposed | When the activation record was created. |
| `activated_at` | timestamp or null | no | proposed | When the flow became active. |
| `paused_at` | timestamp or null | no | proposed | When the activation was paused. |
| `disabled_at` | timestamp or null | no | proposed | When the activation was disabled. |
| `failure_reason` | string or structured reason | no | proposed | Why activation failed or entered an error state. |

`state` must align with `activation_state`.

Activation may reference a trigger registration, but this document does not implement registration.

Activation is durable enablement, not execution success.

## Validation Gates

- Draft preview may exist with warnings or errors.
- `TestRun` requires no blocking validation issues.
- Activation requires stricter validation than `TestRun`.
- Activation must block on missing trigger configuration, inaccessible resources, unapproved external side effects, unresolved semantic uncertainty policy, and missing receipt requirements.
- Validation snapshot used for `TestRun` or Activation must be referenceable in future receipt evidence.
- Validation discovered during execution must appear in receipt evidence and must not silently mutate `FlowDraft`.

## Side-Effect Policy

- `TestRun` defaults to non-side-effecting execution.
- Any side-effecting `TestRun` requires explicit future gate and user approval.
- Activation may permit side effects only after permission checks and trust-boundary review.
- External writes, third-party sharing, identity-sensitive operations, and user-data movement require explicit risk classification.
- Unreceipted side effects are forbidden.
- Command bus side effects, if used later, must preserve command run IDs and idempotency evidence.

## Trigger Registration Policy

- Manual `TestRun` does not require durable trigger registration.
- Activation for schedule/event starters may require durable registration.
- Cron is an adjacent possible substrate for schedule starters, but this contract does not wire Flow Builder to cron.
- Event starters require explicit future architecture for event subscription, authorization, and deregistration.
- Disabling or pausing Activation must prevent future starter-driven runs.
- Trigger registration failure must not look like successful Activation.

## Permission and Trust Boundaries

- Permission snapshots must capture the effective permission posture used for `TestRun` or Activation.
- Sensitive variable bindings and semantic outputs must preserve permission metadata.
- External-recipient or third-party service flows require explicit trust-boundary warnings before Activation.
- Flow Builder must not mutate Identity Mirror, persona ownership rules, canonical tokens, message-versus-attempt identity, export/restore lineage, or queue/worker acceptance semantics.
- Local-only and supported-profile posture must remain respected.

## State Taxonomy

### `test_run_state`

| State | Meaning | Terminal? | Transition notes |
|---|---|---|---|
| `queued` | The test run is admitted but has not started. | no | May transition to `running` or `cancelled`. |
| `running` | The test run is in progress. | no | May transition to `completed`, `failed`, or `cancelled`. |
| `completed` | The test run finished successfully or terminally with receipt evidence. | yes | Should not transition further. |
| `failed` | The test run ended in failure. | yes | May be followed by a new run, not an in-place retry. |
| `cancelled` | The test run was intentionally stopped. | yes | Cancellation may occur before or during execution. |

### `activation_state`

| State | Meaning | Terminal? | Transition notes |
|---|---|---|---|
| `inactive` | The flow is not currently enabled. | no | May transition to `active` or `disabled`. |
| `active` | The flow is enabled for starter-driven execution. | no | May transition to `paused`, `disabled`, or `error`. |
| `paused` | The flow is temporarily disabled without being fully retired. | no | Should block future starter-driven runs until resumed. |
| `disabled` | The flow has been explicitly turned off. | yes | May require reactivation to become active again. |
| `error` | Activation is in a failed or degraded durable state. | yes | Must surface failure reason and recovery path. |

## Relationship to RunReceipt

- RunReceipt is the durable proof surface for a specific execution attempt.
- `TestRun` and `Activation` may reference receipts but must not contain all receipt evidence.
- Receipts should capture validation snapshot, permission snapshot, selected plan, step evidence, skipped steps, side-effect references, command run IDs, semantic metadata, failure or cancellation reason, and timestamps where applicable.
- Receipt persistence is defined later by FB-008.
- A completed `TestRun` or active `Activation` without a receipt must not be treated as full execution proof once receipts exist.

## Failure and Cancellation Semantics

- cancellation before execution starts
- cancellation while running
- validation failure before run
- trigger registration failure
- permission snapshot failure
- execution failure
- receipt generation failure
- partial side-effect failure

Each failure mode must have receipt or audit evidence in future implementation.

## Relationship to Existing Runtime Surfaces

- Existing command bus, cron, queues, workers, and task events are adjacent implementation substrates, not proof of Flow Builder `TestRun` or Activation support.
- Future integration must preserve route acceptance versus completion semantics.
- Future task-event emission must remain governed by runtime protocol token contracts.
- Flow Builder execution states must not redefine chat request states, provider runtime states, or command bus run states.

## Export and Restore Implications

- `TestRun` and Activation records may become exportable workflow artifacts or references.
- Export/restore must preserve activation state, validation refs, permission snapshots, trigger registration refs, receipt refs, and source `FlowDraft` refs where applicable.
- Restore must report unresolved trigger registrations or inaccessible resources explicitly.
- Silent loss of activation lineage or test evidence is not allowed if those records are included in the export artifact.

## Non-Goals

- No `TestRun` implementation.
- No Activation implementation.
- No trigger registry.
- No cron integration.
- No command-bus integration.
- No execution route.
- No validation engine.
- No schema migration.
- No SQLAlchemy model.
- No Pydantic model.
- No TypeScript constants.
- No Python constants.
- No UI implementation.
- No RunReceipt implementation.
- No release-surface expansion.

## Implementation Follow-Through

- FB-008 should define RunReceipt persistence model.
- FB-009 should define activity/proof surfaces for `TestRun` and Activation evidence.
- FB-010 should decide export/restore inclusion for `FlowDraft`, `TestRun`, Activation, and receipts.
- FB-012 should build the first non-side-effecting `TestRun` proof harness only after contract tests and receipt model exist.
- FB-013 should gate the first side-effecting workflow execution behind explicit operator/user approval and durable receipts.
- Any backend implementation must add contract tests before routes or workers consume these shapes.

## Open Questions

- Should `TestRun` records be durable from the first implementation or ephemeral until RunReceipt exists?
- Should Activation require a compiled plan snapshot or always compile on activation?
- Should pausing Activation preserve trigger registration or deregister immediately?
- What side-effect modes are needed beyond non-side-effecting and explicitly approved?
- Should permission snapshots be stored as full structured objects or references to policy decisions?
- Which `TestRun` and Activation fields must be included in account export/restore v1?
