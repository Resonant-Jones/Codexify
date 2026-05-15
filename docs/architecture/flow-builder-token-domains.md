# Flow Builder Token Domain Inventory

## Purpose

This document inventories candidate canonical token domains for future Flow Builder implementation.

It is contract planning only. It does not implement runtime behavior, define storage, or widen the supported beta surface.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- runtime-protocol-token-contract.md
- canonical-token-philosophy.md
- flows.md
- data-and-storage.md

## Interpretation Rules

- Candidate tokens in this document are not implemented runtime values.
- Existing token domains remain governed by their current modules and contracts.
- Future code must not invent ad hoc literals for contract-bearing Flow Builder meanings.
- This document does not choose final file or module locations for code registries unless a registry location is explicitly stated as proposed.

## Token Domain Inventory

| Domain | Purpose | Candidate values | Owner layer | Source contract | Implementation status | Notes |
|---|---|---|---|---|---|---|
| `flow_draft_lifecycle` | Draft state progression from authored artifact to release-ready inventory state | `draft`, `validated`, `compiled`, `archived` | Shared Flow Builder contract | ADR-014, ADR-027 | inventory-only | Canonical lifecycle tokens for the draft artifact itself. |
| `flow_builder_view_mode` | Authoring surface mode for the Flow Builder shell | `authoring`, `review`, `test`, `activity` | Frontend/shared contract | ADR-014, ADR-027 | inventory-only | View modes are presentation tokens, not draft states. |
| `starter_kind` | Single trigger entry point for a flow draft | `manual`, `schedule`, `event` | Backend Flow Builder contract | ADR-006, ADR-027 | inventory-only | Exactly one starter kind may be active per draft in the contract model. |
| `action_step_kind` | Ordered step family after the starter | `command`, `semantic`, `conditional`, `transform`, `notification`, `document`, `task` | Shared Flow Builder contract | ADR-027 | inventory-only | Broad step family labels only; not a full execution taxonomy. |
| `semantic_step_kind` | Bounded AI-anchored step intent | `extract`, `classify`, `summarize`, `decide`, `transform`, `route` | Backend Flow Builder contract | ADR-027, flow-builder-surface-research-application.md | inventory-only | Semantic steps must stay typed and non-recursive. |
| `variable_value_type` | Canonical typing for variable chips and outputs | `text`, `number`, `boolean`, `date`, `datetime`, `email_address`, `url`, `document_ref`, `file_ref`, `person_ref`, `json_object`, `list` | Shared type contract | ADR-027, canonical-token-philosophy.md | inventory-only | Candidate typing set for compatibility checks and chip rendering. |
| `variable_binding_scope` | Where a variable may bind from in the authored flow | `starter`, `step_output`, `flow_input`, `system` | Shared Flow Builder contract | ADR-027 | inventory-only | Scope tokens distinguish source lineage from display labels. |
| `validation_issue_code` | Machine-readable validation findings for authored flows | `missing_required_field`, `incompatible_variable_type`, `missing_substep`, `inaccessible_resource`, `deleted_or_unavailable_reference`, `unsupported_manual_value`, `permission_risk`, `unknown_semantic_output`, `receipt_required` | Backend validation contract | ADR-027, runtime-protocol-token-contract.md, canonical-token-philosophy.md | inventory-only | Validation codes must be bounded before any runtime consumer relies on them. |
| `validation_severity` | Validation finding severity ladder | `info`, `warning`, `error`, `blocking` | Shared validation contract | ADR-027 | inventory-only | Severity is separate from the issue code. |
| `conditional_operator` | Branch predicate operators | `is_true`, `is_false`, `equals`, `not_equals`, `contains`, `not_contains`, `greater_than`, `less_than`, `exists`, `is_empty` | Shared Flow Builder contract | ADR-027, flow-builder-surface-research-application.md | inventory-only | Conservative operator set for structured conditionals. |
| `test_run_state` | Ephemeral isolated test execution state | `queued`, `running`, `completed`, `failed`, `cancelled` | Backend execution contract | ADR-027, ADR-014 | inventory-only | Test runs remain distinct from live activation. |
| `activation_state` | Durable enablement state for a flow draft | `inactive`, `active`, `paused`, `disabled`, `error` | Backend execution contract | ADR-027, ADR-014 | inventory-only | Activation state is not a run receipt state. |
| `run_receipt_state` | Terminal and intermediate receipt state for a flow run | `queued`, `running`, `completed`, `failed`, `cancelled`, `blocked` | Backend receipt contract | ADR-014, ADR-027, data-and-storage.md | inventory-only | Receipt state records evidence, not authoring status. |
| `step_receipt_state` | Per-step evidence state inside a run receipt | `pending`, `running`, `skipped`, `completed`, `failed`, `blocked` | Backend receipt contract | ADR-027, data-and-storage.md | inventory-only | Step receipts are nested under run receipts. |
| `semantic_uncertainty_outcome` | Explicit result of bounded semantic ambiguity handling | `known`, `unknown`, `low_confidence`, `insufficient_evidence` | Backend semantic-step contract | ADR-027, flow-builder-surface-research-application.md | inventory-only | Outcome vocabulary must be chosen before semantic execution exists. |
| `side_effect_risk_class` | Risk class for authored steps and run operations | `none`, `internal_write`, `external_write`, `third_party_share`, `identity_sensitive` | Backend policy contract | ADR-027, data-and-storage.md | inventory-only | Risk tokens support validation and receipt evidence. |
| `permission_boundary_class` | Trust boundary class crossed by a step or run | `local_only`, `workspace_internal`, `external_recipient`, `third_party_service`, `admin_required` | Backend policy contract | ADR-014, ADR-027, modules-and-ownership.md | inventory-only | Boundary tokens should map to policy checks, not UI decoration. |
| `proof_surface_kind` | Evidence surface that can prove a workflow state or run result | `validation_result`, `test_run_receipt`, `activation_record`, `run_receipt`, `step_receipt`, `task_event`, `audit_log`, `export_manifest` | Shared proof contract | ADR-014, ADR-027, flows.md, data-and-storage.md | inventory-only | Proof surfaces must stay distinct from authoring and chat transcripts. |

## Candidate Token Domains

### `flow_draft_lifecycle`

Meaning: the lifecycle of the authored flow artifact itself.

Candidate values: `draft`, `validated`, `compiled`, `archived`

Implementation status: `inventory-only`

Non-goals:

- Not a runtime execution state.
- Not a receipt state.
- Not a UI filter taxonomy.

Future registry owner: `proposed`

### `flow_builder_view_mode`

Meaning: the presentation mode of the Flow Builder surface.

Candidate values: `authoring`, `review`, `test`, `activity`

Implementation status: `inventory-only`

Non-goals:

- Not a draft lifecycle token.
- Not a backend execution state.
- Not a substitute for route state.

Future registry owner: `proposed`

### `starter_kind`

Meaning: the canonical trigger form for a flow draft.

Candidate values: `manual`, `schedule`, `event`

Implementation status: `inventory-only`

Non-goals:

- Not a multi-trigger model.
- Not a step kind.
- Not a receipt state.

Future registry owner: `proposed`

### `action_step_kind`

Meaning: the bounded family for authored steps after the starter.

Candidate values: `command`, `semantic`, `conditional`, `transform`, `notification`, `document`, `task`

Implementation status: `inventory-only`

Non-goals:

- Not a full execution opcode set.
- Not a UI card catalog.
- Not an open-ended graph node taxonomy.

Future registry owner: `proposed`

### `semantic_step_kind`

Meaning: the typed intent label for AI-anchored steps.

Candidate values: `extract`, `classify`, `summarize`, `decide`, `transform`, `route`

Implementation status: `inventory-only`

Non-goals:

- Not a generic planner.
- Not a recursive agent loop.
- Not unbounded prompt text.

Future registry owner: `proposed`

### `variable_value_type`

Meaning: the canonical type vocabulary for variable chips and typed outputs.

Candidate values: `text`, `number`, `boolean`, `date`, `datetime`, `email_address`, `url`, `document_ref`, `file_ref`, `person_ref`, `json_object`, `list`

Implementation status: `inventory-only`

Non-goals:

- Not raw display labels.
- Not storage column names.
- Not the final shape of every future typed output.

Future registry owner: `proposed`

### `variable_binding_scope`

Meaning: the source scope a variable may bind from inside a flow.

Candidate values: `starter`, `step_output`, `flow_input`, `system`

Implementation status: `inventory-only`

Non-goals:

- Not a permission boundary.
- Not a provenance replacement.
- Not a runtime request scope.

Future registry owner: `proposed`

### `validation_issue_code`

Meaning: the canonical machine-readable code attached to a validation finding.

Candidate values: `missing_required_field`, `incompatible_variable_type`, `missing_substep`, `inaccessible_resource`, `deleted_or_unavailable_reference`, `unsupported_manual_value`, `permission_risk`, `unknown_semantic_output`, `receipt_required`

Implementation status: `inventory-only`

Non-goals:

- Not freeform error text.
- Not a runtime exception taxonomy.
- Not a catch-all diagnostics bucket.

Future registry owner: `proposed`

### `validation_severity`

Meaning: the severity ladder for validation findings.

Candidate values: `info`, `warning`, `error`, `blocking`

Implementation status: `inventory-only`

Non-goals:

- Not execution outcome state.
- Not a receipt terminal state.
- Not a UI color token set.

Future registry owner: `proposed`

### `conditional_operator`

Meaning: the comparison and existence operators usable in structured conditionals.

Candidate values: `is_true`, `is_false`, `equals`, `not_equals`, `contains`, `not_contains`, `greater_than`, `less_than`, `exists`, `is_empty`

Implementation status: `inventory-only`

Non-goals:

- Not arbitrary expression evaluation.
- Not a general scripting language.
- Not a DAG edge replacement.

Future registry owner: `proposed`

### `test_run_state`

Meaning: the lifecycle state of an isolated non-side-effecting test run.

Candidate values: `queued`, `running`, `completed`, `failed`, `cancelled`

Implementation status: `inventory-only`

Non-goals:

- Not a live activation state.
- Not a durable production receipt state.
- Not a chat request lifecycle state.

Future registry owner: `proposed`

### `activation_state`

Meaning: the durable enablement state for a flow draft.

Candidate values: `inactive`, `active`, `paused`, `disabled`, `error`

Implementation status: `inventory-only`

Non-goals:

- Not a test run state.
- Not a run receipt state.
- Not a release readiness label.

Future registry owner: `proposed`

### `run_receipt_state`

Meaning: the lifecycle state of a flow run receipt.

Candidate values: `queued`, `running`, `completed`, `failed`, `cancelled`, `blocked`

Implementation status: `inventory-only`

Non-goals:

- Not the same as activation.
- Not the same as chat request states.
- Not an authoring state.

Future registry owner: `proposed`

### `step_receipt_state`

Meaning: the per-step state nested inside a run receipt.

Candidate values: `pending`, `running`, `skipped`, `completed`, `failed`, `blocked`

Implementation status: `inventory-only`

Non-goals:

- Not a top-level run state.
- Not a validation severity.
- Not a step definition kind.

Future registry owner: `proposed`

### `semantic_uncertainty_outcome`

Meaning: the explicit output for unresolved semantic ambiguity.

Candidate values: `known`, `unknown`, `low_confidence`, `insufficient_evidence`

Implementation status: `inventory-only`

Non-goals:

- Not an untyped null.
- Not a hidden prompt-only fallback.
- Not a replacement for validation codes.

Future registry owner: `proposed`

### `side_effect_risk_class`

Meaning: the risk class for a step or execution path that can mutate state.

Candidate values: `none`, `internal_write`, `external_write`, `third_party_share`, `identity_sensitive`

Implementation status: `inventory-only`

Non-goals:

- Not a permission grant.
- Not a policy decision by itself.
- Not a final compliance classification.

Future registry owner: `proposed`

### `permission_boundary_class`

Meaning: the trust boundary a step or run crosses.

Candidate values: `local_only`, `workspace_internal`, `external_recipient`, `third_party_service`, `admin_required`

Implementation status: `inventory-only`

Non-goals:

- Not a user role system.
- Not a routing alias.
- Not a storage schema.

Future registry owner: `proposed`

### `proof_surface_kind`

Meaning: the evidence surface used to prove a workflow contract.

Candidate values: `validation_result`, `test_run_receipt`, `activation_record`, `run_receipt`, `step_receipt`, `task_event`, `audit_log`, `export_manifest`

Implementation status: `inventory-only`

Non-goals:

- Not the same as workflow state.
- Not an implementation module name.
- Not a proof claim by itself.

Future registry owner: `proposed`

## Proposed Registry Boundaries

Future implementation should avoid one giant enum. The bounded registry families should stay separate even if a later module layout groups them nearby.

Proposed families:

- flow lifecycle tokens
- flow step tokens
- variable and type tokens
- validation tokens
- execution and receipt tokens
- permission and risk tokens
- proof-surface tokens

This document does not choose the final file paths for those registries. It only proposes the semantic boundaries.

## Relationship to Existing Runtime Tokens

Existing chat and task protocol tokens remain governed by `runtime-protocol-token-contract.md`.

Flow Builder tokens must not redefine existing task event names, chat request states, or other current runtime truth tokens.

If future workflow execution emits task events, the mapping between workflow receipt states and task event types must be explicitly defined before implementation.

## Non-Goals

- No code token registry in this task.
- No TypeScript constants.
- No Python constants.
- No schema or migration.
- No runtime behavior change.
- No UI behavior change.
- No release-surface expansion.

## Implementation Follow-Through

- FB-004 should refine validation issue codes into an implementation registry.
- FB-005 should refine semantic step kinds and uncertainty outcomes.
- FB-007 and FB-008 should refine test run, activation, and receipt states.
- Future implementation tasks should add contract tests before runtime consumers rely on these tokens.

## Open Questions

- Which token domains belong in backend-only registries versus shared frontend/backend contracts?
- Should variable value types reuse existing document/media/entity type tokens where possible?
- Should receipt states reuse task states or remain workflow-specific?
- Should uncertainty outcomes be represented as semantic-step output metadata, validation issues, or both?
- Which domains must be included in export/restore manifests?
