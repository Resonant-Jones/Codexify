# Flow Builder SemanticStep Contract

## Purpose

This document defines the future contract for Flow Builder semantic AI steps.

It is contract planning only and not model/runtime implementation. No model-call path, prompt executor, validation engine, schema migration, route, worker, or UI component exists as a result of this document.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- flow-builder-token-domains.md
- flowdraft-schema-proposal.md
- variable-chip-typed-output-contract.md
- flow-builder-validation-issue-taxonomy.md
- agent-tool-loop-contract.md
- canonical-token-philosophy.md

## Interpretation Rules

- Semantic steps are bounded semantic primitives, not arbitrary hidden prompt blobs.
- Semantic step declarations are authoring contracts, not execution proof.
- Typed outputs must be declared before downstream binding.
- Uncertainty behavior must be explicit before implementation.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Conceptual Model

`FlowDraft` carries the authored flow state. `SemanticStep` is the bounded AI-assisted step contract inside that draft. `TypedStepOutput` declares what the semantic step can produce. `VariableBinding` connects downstream consumers to those declared outputs. `ValidationIssue` records compatibility, policy, or declaration failures before execution. `TestRun` is the non-durable execution attempt gate. `RunReceipt` is the later proof surface that may summarize the semantic step outcome.

Proposed relationship diagram:

`SemanticStep declaration -> typed output contract -> validation -> TestRun/execution -> semantic receipt metadata`

This relationship is proposed only. It is not an implementation claim.

## SemanticStep Definition

A `SemanticStep` is an `ActionStep` whose behavior is AI-assisted but bounded by an explicit semantic kind.

It is:

- a step with declared input shape, output shape, uncertainty policy, and receipt metadata
- not a general autonomous agent loop
- not a freeform prompt-only execution surface

## Supported Semantic Step Kinds

| Kind | Meaning | Required input pattern | Required output pattern | Typical uncertainty behavior | Notes |
|---|---|---|---|---|---|
| `extract` | Pull structured fields from source material | One or more source texts, documents, or structured inputs with explicit field targets | Typed fields or structured records matching declared outputs | Missing fields may surface as `unknown` or `insufficient_evidence` | Should not invent absent source facts. |
| `classify` | Assign labels or categories from evidence | Subject text plus label set or decision criteria | Single label, label set, or scored label output | Low confidence should remain explicit | Good candidate for warning-grade uncertainty metadata. |
| `summarize` | Condense source material into bounded summary output | Source text, document, or prior outputs with scope hints | Summary text or structured summary fields | Sparse source may yield `insufficient_evidence` | Must stay bounded to declared output shape. |
| `decide` | Choose a bounded outcome from declared options and evidence | Evidence bundle, policy, or candidate options | Decision token, route token, or boolean-like outcome | Ambiguity should usually fail closed or route to review | Should define fallback policy explicitly. |
| `transform` | Convert one typed representation into another | One or more typed source values plus transformation instruction | Transformed typed value or structured output | Missing source shape may produce `unknown` | Not a general code execution surface. |
| `route` | Select a downstream path or branch | Classification or decision evidence plus route candidates | Route token, branch token, or selected path reference | Uncertainty should fall back to review or a safe default | Must define fallback behavior in config. |

## Proposed Shape: SemanticStep Config

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `semantic_step_kind` | `semantic_step_kind` token | yes | flow-builder-token-domains.md | Must align with the candidate semantic step domain from FB-001. |
| `input_bindings` | array of `VariableBinding` references | yes | flowdraft-schema-proposal.md, variable-chip-typed-output-contract.md | Declares which draft inputs feed the semantic step. |
| `instruction` | string or bounded instruction object | yes | proposed | The authoring instruction for the semantic operation. |
| `output_definitions` | array of `TypedStepOutput` declarations | yes | variable-chip-typed-output-contract.md | Must align with the typed output contract from FB-003. |
| `uncertainty_policy` | object or token set | yes | proposed | Must explicitly define behavior for `known`, `unknown`, `low_confidence`, and `insufficient_evidence`. |
| `allowed_sources` | array of source policy tokens or refs | yes | proposed | Constrains where the semantic step may draw evidence from. |
| `model_policy` | object or token ref | yes | proposed | Declares the future model/provider governance expected for the step. |
| `safety_policy` | object or token ref | yes | proposed | Declares redaction, boundary, and refusal expectations. |
| `receipt_policy` | object or token ref | yes | proposed | Declares which semantic metadata should appear in receipt evidence. |

`semantic_step_kind` must align with the token domain from FB-001.

`output_definitions` must align with the `TypedStepOutput` contract from FB-003.

`uncertainty_policy` must explicitly define behavior for `known`, `unknown`, `low_confidence`, and `insufficient_evidence`.

## Input Contracts

- Semantic steps consume `VariableBinding` references or literal configuration values.
- Inputs must define expected value types.
- Sensitive inputs must preserve permission and trust-boundary metadata.
- Missing or incompatible inputs should produce `ValidationIssue` objects.
- Runtime materialization failures must be receipted or surfaced as validation or execution evidence.

## Output Contracts

- Semantic steps must declare `TypedStepOutput` objects before downstream binding.
- Outputs must include value type, cardinality, nullability, sensitivity, and provenance expectations.
- Freeform prose is allowed only when declared as a typed text output.
- AI output must not silently invent undeclared outputs.
- Output mismatch should produce validation or receipt evidence.

## Uncertainty Policy

Candidate uncertainty outcomes:

- `known`
- `unknown`
- `low_confidence`
- `insufficient_evidence`

Each semantic step kind must define how uncertainty affects output values.

`decide` must explicitly define whether uncertainty fails closed, blocks, or routes to review.

`route` must define fallback route behavior.

`extract` must define missing-field behavior.

Unknown semantic outputs must map to validation or receipt evidence.

## Validation Rules

Future validation should cover at least these conditions:

- missing semantic kind
- unsupported semantic kind
- missing input binding
- incompatible input type
- missing output declaration
- undeclared output requested downstream
- uncertainty policy missing
- sensitive input routed to external side effect without approval
- model policy unavailable
- allowed source unavailable

| Validation concern | Likely ValidationIssue code(s) | Notes |
|---|---|---|
| missing semantic kind | `missing_required_field` | Step contract is incomplete. |
| unsupported semantic kind | `invalid_token_value` | Semantic kind falls outside the canonical registry. |
| missing input binding | `missing_required_field` | The step cannot be evaluated safely. |
| incompatible input type | `incompatible_variable_type` | Input shape does not satisfy the step contract. |
| missing output declaration | `missing_output_declaration` | Prevents hidden output assumptions. |
| undeclared output requested downstream | `missing_output_declaration` or `unknown_semantic_output` | Use the most specific code available. |
| uncertainty policy missing | `missing_required_field` | Uncertainty behavior must be explicit. |
| sensitive input routed to external side effect without approval | `permission_risk` or `external_side_effect_requires_approval` | Use the approval-specific code when applicable. |
| model policy unavailable | `receipt_required` or `inaccessible_resource` | Choose based on whether the missing dependency is proof or reachability. |
| allowed source unavailable | `deleted_or_unavailable_reference` or `inaccessible_resource` | Use the more precise source-failure code. |

## Runtime and Model Policy Boundaries

- This contract does not select a provider or model.
- Future implementation must respect supported-profile, egress, local-only, and provider governance.
- Semantic steps must not bypass retrieval policy, command bus policy, or permission gates.
- Semantic steps must not mutate identity mirrors, persona ownership rules, canonical tokens, message-versus-attempt identity, export/restore lineage, or queue/worker acceptance semantics.

## Receipt Metadata Requirements

Future semantic receipt metadata candidates include:

- `semantic_step_kind`
- `input_refs`
- `output_refs`
- `uncertainty_outcome`
- `model_policy_ref`
- `allowed_sources_snapshot`
- `validation_snapshot_ref`
- `redaction_summary`
- `failure_reason`

Receipt metadata must be safe and bounded, not raw chain-of-thought or hidden prompts.

## Relationship to Existing Bounded Tool Loop

- SemanticStep is not the existing bounded tool-turn implementation.
- Future SemanticStep execution must remain bounded and non-recursive unless a future ADR changes the model.
- Tool calls inside semantic steps, if ever allowed, require explicit future architecture work.
- This contract must not be used to smuggle autonomous agent loops into Flow Builder.

## Export and Restore Implications

- SemanticStep declarations are part of FlowDraft artifacts.
- Export/restore must preserve semantic step kind, instruction, input bindings, output definitions, uncertainty policy, source policy, and provenance.
- Restore must report unsupported semantic kinds or unresolved bindings explicitly.
- Silent semantic-step degradation is not allowed.

## Non-Goals

- No model-call implementation.
- No prompt executor.
- No validation engine.
- No schema migration.
- No SQLAlchemy model.
- No Pydantic model.
- No TypeScript constants.
- No Python constants.
- No UI implementation.
- No TestRun, Activation, or RunReceipt implementation.
- No autonomous recursive agent loop.
- No release-surface expansion.

## Implementation Follow-Through

- FB-006 should define conditional-container behavior around semantic outputs.
- FB-007 should define TestRun and Activation gates for semantic steps.
- FB-008 should define how semantic receipt metadata appears in RunReceipt.
- A future implementation task must add contract tests before any model-call runtime consumes semantic step declarations.
- Any semantic step execution implementation must define provider, source, redaction, and receipt proof surfaces before shipping.

## Open Questions

- Should `decide` uncertainty fail closed, block execution, or route to review by default?
- Should `extract` missing fields produce null outputs, validation issues, or receipt warnings?
- Should semantic steps allow retrieval during execution, or only consume prior step outputs?
- Should model policy be draft-level, step-level, or activation-level?
- Which semantic metadata belongs in receipts versus validation summaries?
- Which semantic step fields must be included in account export/restore v1?
