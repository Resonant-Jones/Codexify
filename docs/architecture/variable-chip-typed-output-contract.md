# VariableChip and TypedStepOutput Contract

## Purpose

This document defines the future contract for Flow Builder variable chips and typed step outputs.

It is contract planning only, not UI or runtime implementation. No `VariableChip` component, runtime binding engine, or schema migration exists as a result of this document.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- flow-builder-token-domains.md
- flowdraft-schema-proposal.md
- account-export-restore-contract.md
- canonical-token-philosophy.md

## Interpretation Rules

- Variable chips are not raw strings.
- Display labels are not canonical identity.
- Runtime values are not stored in display chips.
- Typed outputs must be declared before downstream binding.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Conceptual Model

`Starter`, `ActionStep`, and `SemanticStep` declare typed outputs. `TypedStepOutput` is the canonical output contract. `VariableChip` is the user-facing display affordance that lets a person select or insert that output. `VariableBinding` is the durable draft reference connecting a consumer field to a source output. `ValidationIssue` is the future check surface that should reject incompatible wiring. `RunReceipt` is the later proof surface that may summarize what actually happened when a flow was tested or executed.

Proposed relationship diagram:

`Starter / Step -> TypedStepOutput -> VariableChip display -> VariableBinding -> downstream Step input -> StepReceipt / RunReceipt`

This relationship is proposed only. It is not an implementation claim.

## Canonical Distinctions

- `TypedStepOutput`: declared output contract from a starter or step.
- `VariableChip`: user-facing display affordance for selecting or inserting a variable.
- `VariableBinding`: durable draft reference connecting a consumer field to a source output.
- `RuntimeValue`: materialized value during `TestRun` or execution.
- `ReceiptValueSummary`: safe, bounded evidence captured in receipts.

## Proposed Shape: TypedStepOutput

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Canonical identity for the declared output. |
| `source_ref` | starter or step reference | yes | ADR-027, flowdraft-schema-proposal.md | Must point to a starter or step. |
| `name` | machine-readable output name | yes | proposed | Stable local name used in authoring and export. |
| `display_label` | string | yes | proposed | May change without changing canonical identity. |
| `value_type` | `variable_value_type` token | yes | flow-builder-token-domains.md | Must align with the canonical variable type domain. |
| `cardinality` | shape descriptor | yes | proposed | Single, optional, or bounded collection shape. |
| `description` | string or null | no | proposed | Human-readable explanation of the output. |
| `schema` | object or schema fragment | no | proposed | Optional structural schema for complex outputs. |
| `nullable` | boolean | yes | proposed | Whether the output may be absent. |
| `sensitive` | boolean | yes | proposed | Marks outputs that need trust-boundary handling. |
| `provenance` | nested provenance object | yes | ADR-014, account-export-restore-contract.md | Lineage for how the output was derived. |
| `created_by` | user, system, or actor reference | yes | proposed | Who declared or generated the output contract. |

## Proposed Shape: VariableChip

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `output_id` | `TypedStepOutput` reference | yes | proposed | Resolves back to a `TypedStepOutput`. |
| `source_ref` | starter or step reference | yes | proposed | Mirrors the source output lineage. |
| `display_label` | string | yes | proposed | Presentation label for authoring UI. |
| `value_type` | `variable_value_type` token | yes | flow-builder-token-domains.md | Used for compatibility filtering and display grouping. |
| `icon_hint` | string or presentation token | no | proposed | Display-only hint for visual affordance. |
| `scope` | `variable_binding_scope` token | yes | flow-builder-token-domains.md | Bound scope for the chip's use context. |
| `compatibility_summary` | string or structured summary | yes | proposed | Derived summary of what the chip can bind to. |
| `sensitive` | boolean | yes | proposed | Must surface trust-boundary implications. |
| `preview_policy` | object or token | yes | proposed | Governs how much preview data may be shown. |

This is a view model and display affordance. It must not be the sole source of truth. It should resolve back to a `TypedStepOutput`.

## Proposed Shape: VariableBinding

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable durable identifier | yes | proposed | Binding identity inside the draft. |
| `consumer_ref` | starter or step-field reference | yes | proposed | Points to the consumer field using the variable. |
| `consumer_field` | string | yes | proposed | Named field on the consumer step or starter. |
| `output_ref` | `TypedStepOutput` reference | yes | proposed | Points to the source output. |
| `scope` | `variable_binding_scope` token | yes | flow-builder-token-domains.md | Must align with the binding scope domain. |
| `path` | string | yes | proposed | Path into the source output, but not the only identity. |
| `value_type` | `variable_value_type` token | yes | flow-builder-token-domains.md | Must align with the source output type. |
| `required` | boolean | yes | proposed | Whether the downstream field requires this binding. |
| `fallback` | object, token, or null | no | proposed | Optional fallback value or fallback rule. |
| `compatibility` | object or token set | yes | proposed | Compatibility result or constraints. |
| `created_at` | timestamp | yes | proposed | When the binding was created. |
| `updated_at` | timestamp | yes | proposed | When the binding was last edited. |

`consumer_ref` points to the step or starter field consuming the variable.

`output_ref` points to the source output.

`path` must not become the only identity.

`scope` must align with `variable_binding_scope`.

## Compatibility Rules

Compatibility is a first-class validation concern.

Future implementation should recognize at least these cases:

- exact type match
- coercible type match
- incompatible type
- nullable output to required input
- list-to-single mismatch
- sensitive output into external side-effect field
- deleted or unavailable source output
- unknown semantic output

Incompatible bindings should produce `ValidationIssue` objects in future implementation.

## Type Domains

Typed outputs and bindings must reference the `variable_value_type` domain from `flow-builder-token-domains.md`.

Candidate values:

- `text`
- `number`
- `boolean`
- `date`
- `datetime`
- `email_address`
- `url`
- `document_ref`
- `file_ref`
- `person_ref`
- `json_object`
- `list`

Future implementation may add narrower subtypes only through canonical token discipline.

## Sensitive Outputs and Permission Boundaries

Outputs may carry user data.

Sensitive outputs must be marked before they can be bound into third-party or external-recipient fields.

Future UI should show trust-boundary warnings when binding sensitive outputs into external side effects.

Variable chips must not hide permission implications.

Identity-sensitive fields must not be inferred or promoted without explicit consent.

## Runtime Value Materialization

Variable bindings are authoring references.

Runtime values are materialized during `TestRun` or execution.

Runtime values should not mutate the source `FlowDraft`.

Receipts may include bounded summaries, hashes, references, or redacted values, but should not blindly store all raw sensitive content.

Runtime materialization failure should produce receipt evidence and/or validation evidence, not silent nulls.

## Semantic Step Outputs

Semantic steps must declare expected outputs before execution.

AI-generated outputs must preserve uncertainty metadata where applicable.

`unknown`, `low_confidence`, and `insufficient_evidence` outcomes must be representable.

Semantic output shape must be compatible with future validation and receipts.

Do not treat freeform prompt prose as a typed output contract.

## Export and Restore Implications

`TypedStepOutput` declarations and `VariableBinding`s are lineage-bearing parts of `FlowDraft` artifacts.

Export/restore must preserve canonical output IDs, binding IDs, source refs, display labels, value types, and compatibility metadata.

Display labels may be restored even if source refs require remapping.

Restore must report unresolved bindings explicitly.

Silent binding loss is not allowed.

## Non-Goals

- No VariableChip UI component.
- No runtime variable resolver.
- No schema migration.
- No SQLAlchemy model.
- No Pydantic model.
- No TypeScript constants.
- No Python constants.
- No validation engine.
- No TestRun or execution behavior.
- No release-surface expansion.

## Implementation Follow-Through

- FB-004 should convert compatibility failures into a validation issue taxonomy.
- FB-005 should refine semantic step output declarations and uncertainty metadata.
- FB-008 should define how bound values appear in RunReceipt evidence.
- Future implementation should add contract tests before UI components or runtime resolvers consume these shapes.

## Open Questions

- Should `TypedStepOutput.id` be globally unique or draft-local?
- Should list element types be represented as nested schema or separate value types?
- How much preview data can `VariableChip` safely show?
- Should sensitive outputs require explicit user approval before external binding?
- How should bindings survive source step deletion or step reordering?
- Which binding fields must be included in account export/restore v1?
