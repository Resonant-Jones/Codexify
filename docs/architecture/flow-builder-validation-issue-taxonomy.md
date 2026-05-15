# Flow Builder ValidationIssue Taxonomy

## Purpose

This document defines the future taxonomy for Flow Builder validation issues.

It is taxonomy planning only, not validation-engine implementation. No token module, validation engine, schema migration, route, or UI component exists as a result of this document.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- flow-builder-token-domains.md
- flowdraft-schema-proposal.md
- variable-chip-typed-output-contract.md
- runtime-protocol-token-contract.md
- canonical-token-philosophy.md

## Interpretation Rules

- Validation success is eligibility, not execution success.
- Validation issues are contract objects, not just prose messages.
- User-facing messages are not canonical issue identity.
- Blocking validation issues must prevent TestRun or Activation eligibility when implementation exists.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Conceptual Model

`FlowDraft` contains the authored flow state. `Starter`, `Step`, `VariableBinding`, and `TypedStepOutput` are the authored elements that must be checked. `ValidationIssue` is the canonical contract object that records any problem found by validation. `ValidationSummary` aggregates those issues into eligibility signals for `TestRun` and `Activation`. `TestRun`, `Activation`, and `RunReceipt` remain downstream concepts: validation gates access to them, but they are not the same thing as validation.

Proposed relationship diagram:

`FlowDraft -> validate -> ValidationSummary -> eligibility for TestRun / Activation -> RunReceipt after execution`

This relationship is proposed only. It is not an implementation claim.

## Proposed Shape: ValidationIssue

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Identity for the issue record. |
| `code` | `validation_issue_code` token | yes | flow-builder-token-domains.md | Must align with the canonical issue-code registry. |
| `severity` | `validation_severity` token | yes | flow-builder-token-domains.md | Must align with the canonical severity registry. |
| `scope` | validation scope token | yes | proposed | Scope of the issue inside the draft. |
| `target_ref` | target reference object | yes | proposed | Points to the affected draft object. |
| `message` | string | yes | proposed | Display text, not identity. |
| `blocking` | boolean | yes | proposed | Whether the issue blocks eligibility. |
| `details` | object or structured payload | no | proposed | Machine-readable context for diagnostics or UI. |
| `source` | object, token, or string | yes | proposed | Indicates whether the issue came from validation, compatibility, policy, or review. |
| `created_at` | timestamp | yes | proposed | When the issue was produced. |

`code` must align with `validation_issue_code`.

`severity` must align with `validation_severity`.

`target_ref` must point to a draft, starter, step, variable binding, output declaration, or permission boundary.

`message` is display text, not identity.

## Proposed Shape: ValidationSummary

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `state` | summary state token | yes | proposed | Overall validation state for the draft. |
| `eligible_for_test_run` | boolean | yes | proposed | Derived eligibility for isolated test execution. |
| `eligible_for_activation` | boolean | yes | proposed | Derived eligibility for durable activation. |
| `issues` | array of `ValidationIssue` references or embedded issues | yes | proposed | Current issue set for the draft. |
| `blocking_count` | integer | yes | proposed | Count of blocking issues. |
| `warning_count` | integer | yes | proposed | Count of warning-level issues. |
| `validated_at` | timestamp or null | no | proposed | Most recent validation timestamp. |
| `validator_version` | string | yes | proposed | Version or hash of the validation logic. |

Eligibility flags are derived from issues.

Validation state must not be treated as execution state.

Validation summaries may be embedded in `FlowDraft`, but detailed execution evidence belongs in receipts.

## Issue Code Taxonomy

| Code | Meaning | Default severity | Default blocking | Typical scope | Notes |
|---|---|---|---|---|---|
| `missing_required_field` | A required authoring field is absent | `blocking` | yes | `flow`, `starter`, `step`, `variable_binding`, `typed_output` | Usually indicates the draft cannot be safely run or activated. |
| `incompatible_variable_type` | A bound value or output type cannot satisfy the consumer field | `error` | yes | `variable_binding`, `typed_output`, `step` | Covers hard mismatches and coercion failures. |
| `missing_substep` | A structured container or branch is missing required child structure | `error` | yes | `step`, `conditional_container` | Common for conditional branches and nested step groups. |
| `inaccessible_resource` | Required content or connector target cannot be reached | `error` | yes | `step`, `permission_boundary`, `system` | Often reflects reachability or policy enforcement. |
| `deleted_or_unavailable_reference` | A source ref or target ref points to missing or removed content | `error` | yes | `step`, `variable_binding`, `typed_output`, `receipt` | Must stay explicit instead of silently degrading. |
| `unsupported_manual_value` | A field expects structured selection but got an unsupported hand-entered value | `warning` | no | `step`, `variable_binding` | May still allow preview or limited test flows. |
| `permission_risk` | A binding or action crosses a trust boundary with elevated risk | `warning` | no | `variable_binding`, `step`, `permission_boundary` | May require user acknowledgment before activation. |
| `unknown_semantic_output` | A semantic step produced an unresolved or ambiguous output | `warning` | no | `step`, `typed_output` | Captures ambiguity without treating it as silent success. |
| `receipt_required` | A run or gate requires evidence that is not yet present | `error` | yes | `flow`, `receipt`, `system` | Used when proof is missing for a contract-bearing step. |
| `invalid_token_value` | A token-bearing field contains a value outside its canonical domain | `error` | yes | `flow`, `starter`, `step`, `variable_binding`, `typed_output` | Protects canonical token discipline. |
| `duplicate_step_id` | Two steps or nested items reuse the same identity | `error` | yes | `flow`, `step`, `conditional_container` | Identity collisions must fail closed. |
| `invalid_step_order` | Ordered steps or nested positions violate declared sequence rules | `error` | yes | `flow`, `step` | Applies to both ordered sequences and nested containers. |
| `missing_output_declaration` | A step consumes or exposes output without declaring it | `error` | yes | `step`, `typed_output` | Prevents hidden output assumptions. |
| `external_side_effect_requires_approval` | A binding or action would affect an external side effect without approval | `warning` | no | `step`, `permission_boundary`, `receipt` | Usually needs explicit approval before activation. |
| `activation_requires_clean_validation` | Activation was attempted while validation still has disqualifying issues | `blocking` | yes | `flow`, `system` | Guardrail code for durable enablement gates. |

## Severity Taxonomy

- `info`: advisory only; should not block TestRun or Activation by default.
- `warning`: known risk or ambiguity; should not block TestRun by default and should not block Activation by default unless policy adds an approval step.
- `error`: structural or contract problem; should not allow Activation by default and should usually block normal TestRun, while still allowing limited validation preview.
- `blocking`: hard stop; should prevent TestRun and Activation eligibility by default.

By default, `info` and `warning` should not affect TestRun eligibility. `error` and `blocking` should affect TestRun eligibility unless the implementation explicitly separates a limited validation preview from a full TestRun. `error` and `blocking` should prevent Activation eligibility by default.

## Scope and Target References

Allowed scopes:

- `flow`
- `starter`
- `step`
- `variable_binding`
- `typed_output`
- `conditional_container`
- `permission_boundary`
- `receipt`
- `system`

Target reference expectations:

- target kind
- target id
- optional field path
- optional source ref

The target reference should identify both the affected object and, when needed, the affected field path inside that object.

## Compatibility Failure Mapping

Compatibility failures from FB-003 should map to validation issues as follows:

| Failure | Validation issue code | Notes |
|---|---|---|
| exact type match | no issue | Exact matches are eligible without extra validation noise. |
| coercible type match | `incompatible_variable_type` with optional warning severity | May be surfaced as a warning when coercion is allowed but worth showing. |
| incompatible type | `incompatible_variable_type` | Hard mismatch between output and consumer field. |
| nullable output to required input | `missing_required_field` or `incompatible_variable_type` | Use `missing_required_field` if the value is absent; use `incompatible_variable_type` if the shape cannot satisfy the input contract. |
| list-to-single mismatch | `incompatible_variable_type` | Collection shape cannot satisfy scalar expectation. |
| sensitive output into external side-effect field | `permission_risk` or `external_side_effect_requires_approval` | Use the approval-specific code when the issue is policy approval rather than general risk. |
| deleted source output | `deleted_or_unavailable_reference` | Source lineage no longer resolves. |
| unknown semantic output | `unknown_semantic_output` | Ambiguous AI output must remain explicit. |

## Eligibility Rules

- Drafts with blocking issues are not eligible for TestRun.
- Drafts with errors may be eligible for limited validation preview but not Activation.
- Drafts with warnings may be eligible for TestRun but may require user acknowledgment for Activation.
- External side effects require explicit approval before Activation.
- Validation success does not prove successful execution.

## Relationship to TestRun, Activation, and RunReceipt

TestRun can only begin from an eligible draft or compiled plan.

Activation requires stricter validation than draft preview.

RunReceipt must record the validation snapshot or validation reference used for the run when implementation exists.

Validation issues discovered during execution should appear in receipt evidence, not silently mutate the draft.

## Relationship to Existing Runtime Tokens

ValidationIssue codes are Flow Builder contract tokens, not replacements for existing chat/task protocol tokens.

If validation events are emitted through task-event surfaces later, event names must remain governed by runtime protocol token contracts.

Workflow validation states must not redefine chat request states or provider runtime states.

## Export and Restore Implications

Validation summaries and unresolved issues should eventually be exportable with `FlowDraft` artifacts.

Export/restore must preserve issue codes, target refs, severity, blocking state, and validator version where applicable.

Restore must report unresolved target refs explicitly.

Silent loss of validation state is not allowed if validation state is part of the exported artifact.

## Non-Goals

- No validation engine.
- No code token registry.
- No TypeScript constants.
- No Python constants.
- No schema migration.
- No SQLAlchemy model.
- No Pydantic model.
- No UI badges or issue panels.
- No TestRun, Activation, or execution behavior.
- No release-surface expansion.

## Implementation Follow-Through

- FB-005 should refine SemanticStep validation and uncertainty behavior.
- FB-006 should define conditional-container validation behavior.
- FB-007 should define validation gates for TestRun and Activation.
- FB-008 should define how validation snapshots appear in RunReceipt evidence.
- Future implementation should add contract tests before runtime or UI consumers rely on validation codes.

## Open Questions

- Should warnings ever block Activation by policy?
- Should validation issue IDs be stable across edits or regenerated per validation pass?
- Should validation summaries store only current issues or validation history?
- How should validation distinguish user-correctable issues from system/operator issues?
- Should validation support acknowledgement states for known risks?
- Which validation fields must be included in account export/restore v1?
