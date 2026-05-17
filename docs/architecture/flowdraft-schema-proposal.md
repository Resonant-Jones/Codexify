# FlowDraft Schema Proposal

## Purpose

This document proposes the future durable shape of `FlowDraft` artifacts.

It is schema planning only. It does not implement runtime behavior, and it does not create a database migration or route.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- flow-builder-token-domains.md
- data-and-storage.md
- account-export-restore-contract.md
- canonical-token-philosophy.md

## Interpretation Rules

- Proposed fields are not implemented runtime fields.
- Token-bearing fields must use future canonical registries before code use.
- FlowDraft persistence must not be conflated with execution, activation, or receipt persistence.
- This document does not decide final database table names unless explicitly labeled proposed.
- If later implementation diverges from this proposal, update docs or ADRs before code lands.

## Conceptual Model

`GuardianThread` is the canonical conversation substrate. `FlowDraft` is the authored flow artifact that originates from that conversation and preserves its lineage. `FlowBuilderView` is a presentation over one `FlowDraft`, not a separate artifact. `CompiledPlan` is the executable interpretation of the draft. `TestRun` and `Activation` are distinct downstream states or records that may reference the draft or a compiled plan. `RunReceipt` is the durable proof surface for an execution attempt and remains separate from authoring state.

Proposed relationship diagram:

`GuardianThread -> FlowDraft -> CompiledPlan -> TestRun / Activation -> RunReceipt`

This relationship is proposed only. It is not an implementation claim.

## Proposed Entity: FlowDraft

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable UUID or equivalent durable identifier | yes | proposed | Immutable identity for the draft artifact. |
| `title` | string | yes | proposed | Human-facing name for the draft. |
| `description` | string or null | no | proposed | Optional summary of the draft's intent. |
| `project_id` | project UUID or null | no | proposed | Ownership boundary and project-scoping anchor. |
| `thread_id` | GuardianThread UUID | yes | ADR-014 | Canonical conversation anchor. |
| `source_message_id` | message UUID or bounded scope reference | yes | ADR-014 | Origin message lineage where applicable. |
| `created_by_user_id` | user UUID | yes | proposed | Authorship owner for the draft. |
| `status` | `flow_draft_lifecycle` token | yes | flow-builder-token-domains.md | Draft lifecycle state. |
| `version` | string or semver-like label | yes | proposed | Compatibility-oriented version marker. |
| `revision` | monotonically increasing integer | yes | proposed | Concurrency and edit history guard. |
| `starter` | nested Starter object | yes | ADR-006, ADR-027 | Single trigger entry point for the flow. |
| `steps` | ordered array of nested Step objects | yes | ADR-027 | Authoring sequence after the starter. |
| `variables` | array of Variable Binding objects | yes | ADR-027 | Canonical variable references for wiring and display. |
| `validation_summary` | nested Validation Summary object | yes | ADR-027 | Current validation state and issue list. |
| `compiled_plan_ref` | compiled-plan reference or null | no | proposed | Latest compiled interpretation, if any. |
| `last_test_run_ref` | test-run reference or null | no | proposed | Most recent test execution summary, if any. |
| `last_activation_ref` | activation reference or null | no | proposed | Most recent durable activation summary, if any. |
| `provenance` | nested provenance object | yes | ADR-014, account-export-restore-contract.md | Source lineage and derived-artifact origin. |
| `created_at` | timestamp | yes | proposed | Creation time. |
| `updated_at` | timestamp | yes | proposed | Last mutation time. |
| `archived_at` | timestamp or null | no | ADR-014 | Archive instead of hard delete by default. |

## Proposed Nested Shape: Starter

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable nested identifier | yes | proposed | Identity for the starter block. |
| `kind` | `starter_kind` token | yes | flow-builder-token-domains.md | Must align with the starter kind domain. |
| `label` | string | yes | proposed | Human-facing starter label. |
| `config` | object | yes | proposed | Mode-specific configuration payload. |
| `source_ref` | lineage reference or null | no | ADR-014 | Reference to origin material used to derive the starter. |
| `validation_state` | validation state object or token | yes | proposed | Starter-level validation visibility. |

## Proposed Nested Shape: Step

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable nested identifier | yes | proposed | Identity for the step. |
| `kind` | `action_step_kind` token | yes | flow-builder-token-domains.md | Must align with the action-step domain. |
| `label` | string | yes | proposed | Human-facing step label. |
| `position` | integer | yes | proposed | Ordered step position in the draft. |
| `config` | object | yes | proposed | Step-specific configuration payload. |
| `input_bindings` | array of Variable Binding objects | yes | proposed | Input wiring for the step. |
| `output_definitions` | array of output definitions | yes | proposed | Declared outputs produced by the step. |
| `validation_state` | validation state object or token | yes | proposed | Step-level validation visibility. |
| `provenance` | provenance object | yes | ADR-014, account-export-restore-contract.md | Source or derivation lineage for the step. |

Semantic steps must also carry a `semantic_step_kind` token in their `config` or a similarly explicit nested field. That token must align with the Flow Builder token-domain inventory.

## Proposed Nested Shape: Variable Binding

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `id` | stable nested identifier | yes | proposed | Identity for the variable binding record. |
| `scope` | `variable_binding_scope` token | yes | flow-builder-token-domains.md | Must align with the variable binding scope domain. |
| `source_ref` | step or starter reference | yes | proposed | Source artifact that produced the value. |
| `path` | string | yes | proposed | Named path into the source artifact. |
| `value_type` | `variable_value_type` token | yes | flow-builder-token-domains.md | Must align with the typed variable domain. |
| `display_label` | string | yes | proposed | Human-facing label for the bound value. |
| `required` | boolean | yes | proposed | Whether the binding is mandatory. |
| `compatibility` | object or token set | yes | proposed | Compatibility and acceptance constraints. |

## Proposed Nested Shape: Validation Summary

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `state` | `validation_severity`-like state or validation status token | yes | proposed | Overall validation state for the draft. |
| `issues` | array of validation issue objects | yes | proposed | Ordered issue list for the draft. |
| `validated_at` | timestamp or null | no | proposed | Most recent validation timestamp. |
| `validator_version` | string | yes | proposed | Version of the validation logic or contract reader. |

Each issue should include:

| Field | Type / shape | Required | Source | Notes |
|---|---|---|---|---|
| `code` | validation issue code token | yes | flow-builder-token-domains.md | Must align with future validation-token registries. |
| `severity` | validation severity token | yes | flow-builder-token-domains.md | Must align with future validation-token registries. |
| `scope` | `starter` / `step` / `flow` / `variable` | yes | proposed | Scope of the issue. |
| `target_ref` | nested object reference | yes | proposed | The affected draft element. |
| `message` | string | yes | proposed | Human-readable explanation. |
| `blocking` | boolean | yes | proposed | Whether the issue blocks activation or testing. |

## Provenance and Lineage

`FlowDraft` must preserve source thread and message lineage where applicable.

`FlowDraft` must preserve project and user ownership boundaries.

`FlowDraft` must support export/restore lineage.

Generated or derived `FlowDraft` artifacts must record source artifact references when available.

Silent provenance loss is not allowed.

## Versioning and Revision Model

- `id` should remain immutable.
- `revision` should increase monotonically with each meaningful edit.
- `version` should capture a human-visible or compatibility-oriented version marker.
- `created_at`, `updated_at`, and `archived_at` should support auditability and lifecycle tracking.
- Archived state should be preferred over hard delete by default.
- Future implementation must define optimistic concurrency or revision guards before multi-client editing.

## Relationship to Compiled Plans

`FlowDraft` is authoring state.

`CompiledPlan` is executable interpretation.

`FlowDraft` may reference the latest compiled plan, but the draft and compiled plan must not be treated as identical.

Compilation success does not prove execution success.

Compiled plans must not silently mutate the source `FlowDraft`.

## Relationship to TestRun, Activation, and RunReceipt

`TestRun` executes against a draft or compiled plan without durable activation.

`Activation` is a durable enablement or subscription record.

`RunReceipt` is the durable proof surface for execution attempts.

`FlowDraft` may reference the latest `TestRun` or `Activation` summaries, but receipts remain separate evidence artifacts.

Do not store full run evidence only inside the `FlowDraft`.

## Storage Options

| Option | Benefits | Risks | Recommendation |
|---|---|---|---|
| Option A: Dedicated `flow_drafts` table with JSONB draft body | Small initial blast radius, straightforward ownership boundary, easy to version the draft body, and compatible with gradual normalization later | The JSONB body can become a dumping ground if contracts are not enforced; nested shape queries may be less efficient | Recommended conservative path for early implementation unless later code pressure clearly favors another layout |
| Option B: Reuse existing flow tables | Potentially fewer new tables, may align with eventual normalized execution tables, and could reduce initial migration count | High coupling to unrelated flow semantics, risk of conflating draft state with runtime state, and harder to preserve clean authoring boundaries | Not recommended unless current code already exposes a strong flow table shape that matches the contract |
| Option C: Split normalized tables for drafts, steps, variables, and validation issues | Strong relational integrity and query precision; easier to query individual nested entities | Higher migration and model complexity, more surface area for drift, and a larger implementation blast radius before contracts harden | Reasonable later-stage option, but too heavy for the first durable draft contract unless the domain proves it needs normalization immediately |

Option A is the preferred early implementation path because it preserves a single durable draft boundary while leaving room to normalize steps, variables, and validation records later if required.

## Export and Restore Implications

`FlowDraft` artifacts should eventually be exportable as lineage-bearing artifacts.

The export manifest should include draft IDs, source thread and message links, project links, revision and version values, and references to compiled plans, activations, and receipts when present.

If `FlowDraft`s are excluded from an early export format, the exclusion must be explicit.

Restore must not silently drop `FlowDraft` lineage.

## Non-Goals

- No database migration in this task.
- No SQLAlchemy model.
- No Pydantic model.
- No route implementation.
- No frontend state model.
- No compiler implementation.
- No TestRun, Activation, or RunReceipt implementation.
- No release-surface expansion.

## Implementation Follow-Through

- FB-003 should refine `VariableChip` and `TypedStepOutput` details.
- FB-004 should define `ValidationIssue` taxonomy and implementation registry.
- FB-007 should define `TestRun` and `Activation` backend contract.
- FB-008 should define `RunReceipt` persistence model.
- A future backend implementation task must add migrations and models only after contracts are accepted.

## Open Questions

- Should `FlowDraft` use JSONB first or normalized step tables first?
- Should compiled plans be stored durably before `TestRun` exists?
- Should `FlowDraft` revisions be full snapshots or patch-based?
- What is the minimum viable provenance payload for imported or generated drafts?
- How should multi-user edits or shared draft editing be guarded?
- Which `FlowDraft` fields must be included in account export/restore v1?
