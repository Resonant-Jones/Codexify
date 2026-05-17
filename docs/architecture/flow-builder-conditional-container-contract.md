# Flow Builder ConditionalContainer Contract

## Purpose

This document defines the future contract for Flow Builder conditional containers.

It is contract planning only and not UI, compiler, or runtime implementation. No condition evaluator, validation engine, compiler, schema migration, route, worker, or UI component exists as a result of this document.

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
- canonical-token-philosophy.md

## Interpretation Rules

- Conditional containers are structured control-flow nodes, not arbitrary graph splits.
- The default authoring model remains linear ordered steps.
- Nested substeps are contained by the conditional container.
- A conditional container must preserve readable execution receipts.
- Condition expressions must be based on typed values or explicit literals.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Conceptual Model

`FlowDraft` contains ordered authoring steps. `ActionStep` may include a `ConditionalContainer`. `VariableBinding` and `TypedStepOutput` provide typed inputs to the condition. `ValidationIssue` guards structure, ordering, and type compatibility. `CompiledPlan` is the future executable interpretation of the authored draft. `StepReceipt` records whether a step executed, skipped, or blocked. `RunReceipt` aggregates the execution evidence for the run.

Proposed relationship diagram:

`FlowDraft ordered steps -> ConditionalContainer -> condition expression -> nested substeps -> StepReceipt skipped/executed evidence -> RunReceipt`

This relationship is proposed only. It is not an implementation claim.

## ConditionalContainer Definition

A `ConditionalContainer` is an `ActionStep` whose `kind` is `conditional`.

It is:

- a structured container with condition expression(s) and nested substeps
- a bounded branch construct inside an otherwise ordered flow
- not an arbitrary DAG node
- not a recursive loop construct
- not an autonomous decision agent

## Proposed Shape: ConditionalContainer

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Identity for the container inside the flow draft. |
| `kind` | `action_step_kind` token | yes | flow-builder-token-domains.md | Must align with `action_step_kind=conditional`. |
| `label` | string | yes | proposed | Human-readable label for the container. |
| `position` | ordered step position token or integer | yes | proposed | Preserves the container's place in the linear flow. |
| `condition` | `ConditionExpression` object or array | yes | proposed | Must follow the proposed condition expression shape. |
| `substeps` | array of nested step declarations | yes | proposed | Must contain at least one nested step before TestRun or Activation eligibility. |
| `else_substeps` | array of nested step declarations | no | proposed | Optional else branch; may be empty in early implementation. |
| `validation_state` | validation state token or summary ref | yes | flow-builder-validation-issue-taxonomy.md | Captures whether the container is eligible. |
| `provenance` | nested provenance object | yes | flowdraft-schema-proposal.md | Preserves authoring and derived-lineage context. |

`kind` must align with `action_step_kind=conditional`.

`condition` must follow the proposed condition expression shape.

`substeps` must contain at least one nested step before TestRun or Activation eligibility.

`else_substeps` is optional and may be empty in early implementation.

## Proposed Shape: Condition Expression

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Identity for the expression or expression group. |
| `lhs` | `VariableBinding` or `TypedStepOutput` reference, or literal | yes | variable-chip-typed-output-contract.md, flow-builder-semantic-step-contract.md | Should generally reference a `VariableBinding` or `TypedStepOutput`. |
| `operator` | `conditional_operator` token | yes | flow-builder-token-domains.md | Must align with the canonical operator domain. |
| `rhs` | literal, variable-backed reference, or null | no | proposed | May be omitted for unary operators. |
| `conjunction` | `and` or `or` | no | proposed | Bounded to simple conjunctions when multiple conditions are allowed. |
| `negated` | boolean | no | proposed | Indicates the condition should be inverted. |
| `value_type` | `variable_value_type` token or typed literal descriptor | yes | flow-builder-token-domains.md | Declares the expected comparison type. |
| `source_refs` | array of binding or output refs | yes | proposed | Lists the typed sources used by the expression. |

`lhs` should generally reference a `VariableBinding` or `TypedStepOutput`.

`operator` must align with `conditional_operator`.

`rhs` may be literal, variable-backed, or omitted for unary operators.

`conjunction` must be bounded to simple `and` / `or` when multiple conditions are allowed.

Complex expression trees require future architecture work before implementation.

## Conditional Operators

Reference the `conditional_operator` domain from `flow-builder-token-domains.md`.

Candidate values:

- `is_true`
- `is_false`
- `equals`
- `not_equals`
- `contains`
- `not_contains`
- `greater_than`
- `less_than`
- `exists`
- `is_empty`

| Operator | Expected input type | Is `rhs` required | Common validation failures | Notes |
|---|---|---|---|---|
| `is_true` | boolean or boolean-like typed value | no | `missing_required_field`, `incompatible_variable_type` | Unary truth check. |
| `is_false` | boolean or boolean-like typed value | no | `missing_required_field`, `incompatible_variable_type` | Unary negated truth check. |
| `equals` | typed scalar or comparable structured value | yes | `missing_required_field`, `incompatible_variable_type` | Exact match comparison. |
| `not_equals` | typed scalar or comparable structured value | yes | `missing_required_field`, `incompatible_variable_type` | Exact mismatch comparison. |
| `contains` | text, list, or collection-like value | yes | `missing_required_field`, `incompatible_variable_type` | Membership or substring check. |
| `not_contains` | text, list, or collection-like value | yes | `missing_required_field`, `incompatible_variable_type` | Inverted membership or substring check. |
| `greater_than` | number, date, or datetime | yes | `missing_required_field`, `incompatible_variable_type` | Ordered comparison only. |
| `less_than` | number, date, or datetime | yes | `missing_required_field`, `incompatible_variable_type` | Ordered comparison only. |
| `exists` | any typed value or reference | no | `missing_required_field`, `deleted_or_unavailable_reference` | Presence check, not truth check. |
| `is_empty` | text, list, object, or nullable typed value | no | `missing_required_field`, `incompatible_variable_type` | Empty-check semantics must stay bounded. |

## Nested Substep Rules

- Conditional containers may contain nested `ActionStep`s.
- Nested substeps must preserve stable IDs and local ordering.
- Empty `substeps` should produce a blocking validation issue.
- Nested containers may be allowed only if the future implementation explicitly supports them.
- Early implementation should prefer shallow nesting for legibility.
- Nested substeps must not create arbitrary cross-branch jumps.
- Step reordering must preserve provenance and binding references.

## UI Model Constraints

- UI should present conditionals as readable containers in the ordered step list.
- UI must distinguish condition, then-substeps, and optional else-substeps.
- UI should avoid arbitrary node-canvas semantics unless a future ADR expands the model.
- UI should show validation issues at container, condition, and nested-step levels.
- UI should preserve chip-based variable selection rather than raw path-string authoring as the primary model.
- UI must not imply execution success from validation success.

## Validation Rules

Future validation should cover at least these conditions:

- missing condition
- missing lhs
- missing operator
- missing rhs for binary operator
- unsupported operator
- incompatible operand types
- missing substep
- invalid nested step order
- deleted or unavailable variable source
- semantic uncertainty outcome used without policy
- sensitive value used in external side-effect branch without approval

| Validation concern | Likely ValidationIssue code(s) | Notes |
|---|---|---|
| missing condition | `missing_required_field` | The container cannot be evaluated. |
| missing lhs | `missing_required_field` | No left-hand operand is available. |
| missing operator | `missing_required_field` | The comparison cannot be interpreted. |
| missing rhs for binary operator | `missing_required_field` | Binary operators require a right-hand operand. |
| unsupported operator | `invalid_token_value` | Operator falls outside the canonical registry. |
| incompatible operand types | `incompatible_variable_type` | Operand shapes cannot be compared safely. |
| missing substep | `missing_substep` | Structured branch is incomplete. |
| invalid nested step order | `invalid_step_order` | Nested execution order is invalid. |
| deleted or unavailable variable source | `deleted_or_unavailable_reference` | Condition source no longer resolves. |
| semantic uncertainty outcome used without policy | `unknown_semantic_output` or `missing_required_field` | Use the most specific code available for the missing policy. |
| sensitive value used in external side-effect branch without approval | `permission_risk` or `external_side_effect_requires_approval` | Use the approval-specific code when applicable. |

## SemanticStep Interactions

- Conditional containers may consume outputs from `SemanticStep` declarations.
- `decide` outputs may be used directly by boolean condition operators.
- `route` outputs may require explicit mapping before branch selection.
- `unknown`, `low_confidence`, or `insufficient_evidence` outcomes must be handled explicitly.
- Semantic uncertainty must not silently choose a branch unless the condition policy says so.

## Compilation and Execution Boundaries

- This contract does not implement a compiler.
- Future compilation must translate conditional containers into an executable plan without mutating the source `FlowDraft`.
- Compilation success does not prove execution success.
- Runtime branch evaluation must produce receipt evidence.
- Skipped branches must be represented as skipped or not-evaluated receipt evidence rather than disappearing.

## Receipt Expectations

Future receipt metadata candidates include:

- `condition_ref`
- `condition_result`
- `evaluated_inputs`
- `selected_branch`
- `skipped_step_refs`
- `executed_step_refs`
- `uncertainty_outcome`
- `failure_reason`

Receipt metadata must be safe and bounded, not raw chain-of-thought or hidden prompts.

## Export and Restore Implications

- ConditionalContainer declarations are part of `FlowDraft` artifacts.
- Export/restore must preserve condition expressions, nested substep IDs, ordering, variable refs, operator tokens, and provenance.
- Restore must report unresolved condition refs or missing nested step refs explicitly.
- Silent branch loss is not allowed.

## Non-Goals

- No condition evaluator.
- No compiler implementation.
- No validation engine.
- No UI component.
- No schema migration.
- No SQLAlchemy model.
- No Pydantic model.
- No TypeScript constants.
- No Python constants.
- No TestRun, Activation, or RunReceipt implementation.
- No arbitrary DAG model.
- No recursive loop construct.
- No autonomous recursive agent loop.
- No release-surface expansion.

## Implementation Follow-Through

- FB-007 should define TestRun and Activation gates for conditional containers.
- FB-008 should define how conditional branch receipts appear in RunReceipt.
- FB-011 should prototype conditional container UI only after contract fixtures exist.
- A future implementation task must add contract tests before a compiler or UI consumes conditional container shapes.
- Any expansion from structured containers to arbitrary DAGs requires a future ADR.

## Open Questions

- Should early implementation allow nested conditional containers?
- Should else branches be supported in the first implementation slice?
- Should semantic uncertainty default to block, fail closed, or route to review?
- Should condition expressions support grouped clauses beyond simple and/or?
- Should skipped substeps produce full StepReceipts or compact skipped references?
- Which conditional fields must be included in account export/restore v1?
