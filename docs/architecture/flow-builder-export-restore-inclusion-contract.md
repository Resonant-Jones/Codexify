# Flow Builder Export and Restore Inclusion Contract

## Purpose

This document defines future export/restore inclusion rules for Flow Builder artifacts.

It is contract planning only and not export/restore implementation. No archive writer, restore reader, schema migration, route, worker, UI component, persistence table, validation engine, compiler, or runtime execution path exists as a result of this document.

## Governing Sources

- ADR-006: Flow Builder Elicitation Lane
- ADR-014: Flow Builder Thread, Draft, and Receipts Contract
- ADR-027: Flow Builder Typed Surface and Run Receipt Contract
- CAMPAIGN_FLOW_BUILDER_TYPED_SURFACE.md
- account-export-restore-contract.md
- flow-builder-token-domains.md
- flowdraft-schema-proposal.md
- variable-chip-typed-output-contract.md
- flow-builder-validation-issue-taxonomy.md
- flow-builder-semantic-step-contract.md
- flow-builder-conditional-container-contract.md
- flow-builder-testrun-activation-contract.md
- flow-builder-runreceipt-persistence-model.md
- flow-builder-activity-proof-surface.md
- runtime-protocol-token-contract.md
- canonical-token-philosophy.md
- data-and-storage.md
- modules-and-ownership.md

## Interpretation Rules

- Exported workflow artifacts are portability records, not runtime proof by themselves.
- Restore success is not workflow execution success.
- Activity reconstruction is not receipt persistence.
- Task-event streams are not sufficient export artifacts.
- Flow Builder docs-only contracts are not shipped runtime support.
- Token-bearing fields must use future canonical registries before code use.
- This document does not decide final implementation file or module locations.

## Relationship to Account Export and Restore

This contract inherits the account export/restore guarantees and must preserve them for Flow Builder artifacts:

- single canonical archive
- `manifest.json` as archive source of truth
- explicit entity payloads
- explicit relationship payloads
- integrity metadata
- compatibility metadata
- fail-closed or explicit reporting for unsupported schema versions
- no silent lineage loss
- semantic equivalence across ID remapping

## Conceptual Model

`FlowDraft` is the authored flow state. `CompiledPlan` is the executable interpretation when it exists. `ValidationSnapshot` captures the eligibility posture. `TestRun` and `Activation` are execution-adjacent records. `RunReceipt` and `StepReceipt` are durable proof artifacts. `ActivityTimeline` is a reconstructable presentation of those artifacts. `manifest.json` declares what is included. The restore ID map reconciles exported IDs to restored local IDs.

Proposed relationship diagram:

`FlowDraft artifacts -> export manifest families -> restore ID map -> restored FlowDraft/proof refs -> reconstructed activity/proof surface`

This relationship is proposed only. It is not an implementation claim.

## Export Artifact Families

| Family | Purpose | Inclusion class | Restore expectation | Exclusion policy |
|---|---|---|---|---|
| `flow_drafts` | Preserve authored FlowDraft state and lineage. | required | Restore as editable draft state. | Must be explicit if absent. |
| `flow_compiled_plan_refs` | Preserve references to executable interpretations. | deferred | Restore as references unless compiler-compatible snapshots are included. | May be excluded if deterministically regenerable. |
| `flow_validation_snapshots` | Preserve validation eligibility evidence. | optional | Restore as historical validation evidence, not current validity. | May be excluded only if no downstream family depends on it. |
| `flow_test_runs` | Preserve execution attempt history. | optional | Restore as historical attempts, never active execution. | May be excluded in early formats if not yet persisted. |
| `flow_activations` | Preserve durable enablement/subscription records. | optional | Restore as historical or inactive records unless explicit policy says otherwise. | Must be explicit if omitted. |
| `flow_run_receipts` | Preserve durable execution proof. | optional | Restore as historical proof references. | Must be explicit if omitted. |
| `flow_step_receipts` | Preserve step-level proof and branch evidence. | optional | Restore as step evidence linked to receipt IDs or exported stable IDs. | Must be explicit if omitted. |
| `flow_activity_refs` | Preserve reconstructable activity/proof surface references. | optional | Restore as reconstructable presentation inputs. | May be excluded if activity history is not exported. |
| `flow_artifact_relationships` | Preserve explicit lineage and graph edges. | required | Restore through the ID map and explicit relationship reconciliation. | Silent omission is not allowed. |

## Proposed Manifest Entries

| Manifest field | Type / shape | Required | Notes |
|---|---|---|---|
| `flow_builder_schema_version` | string | yes | Version of the Flow Builder export sub-schema. |
| `flow_builder_export_mode` | string | yes | Declares whether the archive includes full state, references only, or a staged subset. |
| `flow_builder_entity_counts` | object | yes | Counts by Flow Builder artifact family. |
| `flow_builder_relationship_counts` | object | yes | Counts by explicit relationship family. |
| `flow_builder_feature_flags` | array or object | yes | Declares which Flow Builder families and capabilities are present. |
| `flow_builder_included_families` | array of strings | yes | Lists included Flow Builder families. |
| `flow_builder_excluded_families` | array of strings | yes | Lists excluded Flow Builder families and why they are excluded. |
| `flow_builder_integrity` | object | yes | Checksums, hashes, or integrity metadata for included payloads. |
| `flow_builder_compatibility` | object | yes | Restore compatibility posture, reader expectations, and version flags. |
| `flow_builder_restore_requirements` | object | yes | Declares prerequisites and failure behavior for restore. |

These are candidate fields unless later implementation promotes them.

## FlowDraft Export Requirements

- FlowDraft exports must preserve stable draft IDs or exported stable IDs.
- Draft title, description, starter refs, ordered ActionSteps, VariableBindings, TypedStepOutputs, ConditionalContainers, SemanticSteps, validation state refs, provenance, timestamps, project/thread refs, and owner/user refs must be preserved where applicable.
- Authoring state must not be replaced by compiled execution state.
- Missing project/thread refs must be reported explicitly on restore.
- FlowDraft export is the primary required family once FlowDraft persistence exists.

## CompiledPlan Reference Policy

- CompiledPlan artifacts may be excluded in early export if they are deterministic and safely regenerable from FlowDraft plus compiler version.
- If included, CompiledPlan exports must preserve source FlowDraft ref, compiler version, plan hash, generated-at timestamp, validation snapshot ref, and provenance.
- Restore must not treat a stale compiled plan as authoritative over the restored FlowDraft.
- If compiler versions differ, restore must report compatibility posture.

## ValidationSnapshot Export Requirements

- Validation snapshots may be required once TestRun, Activation, or RunReceipt records reference them.
- Exports should preserve issue codes, severities, target refs, blocking state, validator version, generated-at timestamp, and provenance.
- Restore must preserve the difference between historical validation evidence and current validation eligibility.
- Restoring a historical validation snapshot must not imply the restored flow is currently valid.

## TestRun Export Requirements

- TestRun exports are optional or deferred until TestRun persistence exists.
- If included, they must preserve state, FlowDraft ref, CompiledPlan ref, validation snapshot ref, permission snapshot ref, run receipt ref, timestamps, initiated-by ref, side-effect mode, cancellation/failure reason, and provenance.
- Restore must not turn historical TestRuns into active executions.
- Restore must report unresolved receipt refs or permission snapshot refs explicitly.

## Activation Export Requirements

- Activation records are higher risk than drafts because they imply durable enablement/subscription.
- Early export may include Activation records as historical records but restore them as inactive unless explicit future policy says otherwise.
- If included, Activation exports must preserve state, FlowDraft ref, CompiledPlan ref, starter ref, validation snapshot ref, permission snapshot ref, trigger registration ref, last run receipt ref, timestamps, activated-by ref, paused/disabled markers, failure reason, and provenance.
- Restore must not silently re-register triggers or resume side-effecting workflows.
- Trigger registration refs must be reported unresolved unless the restore environment can rebind them through an explicit future gate.

## RunReceipt and StepReceipt Export Requirements

- RunReceipt and StepReceipt artifacts are lineage-bearing execution evidence.
- If included, exports must preserve receipt IDs or exported stable IDs, source FlowDraft refs, CompiledPlan refs, TestRun/Activation refs, state, validation snapshot refs, permission snapshot refs, command run refs, task event refs, audit refs, side-effect refs, semantic metadata, condition metadata, timestamps, failure/cancellation reasons, and provenance.
- StepReceipt exports must preserve source step refs, branch refs, state, bounded value summaries or redaction references, and side-effect refs.
- Restore must report unresolved command run refs, task event refs, audit refs, or side-effect refs explicitly.
- Silent receipt loss is not allowed if receipts are declared included.

## Activity and Proof Surface Reconstruction

- Activity/proof surfaces should be reconstructable from restored FlowDraft, TestRun, Activation, RunReceipt, StepReceipt, validation, permission, audit, and side-effect references where included.
- Activity UI labels are not independently authoritative export records unless later promoted.
- If activity history is excluded, the exclusion must be declared in the manifest.
- Reconstructed activity must distinguish restored historical evidence from newly generated runtime evidence.

## ID Remapping and Reference Reconciliation

- exported stable ID: an ID included in the archive as emitted by the exporter
- restored local ID: the new ID used by the importing instance
- restore ID map: the explicit mapping from exported stable IDs to restored local IDs
- unresolved reference: a reference the restore reader cannot bind
- remapped reference: a reference rewritten through the restore ID map
- orphaned historical reference: a reference preserved as evidence but not rebound into active state

- Restore must produce or maintain an ID map for all Flow Builder artifact families.
- Relationship payloads must be reconciled through the ID map.
- Restore must fail or explicitly report when required refs cannot be reconciled.
- Restored IDs must not break VariableBinding refs, step refs, branch refs, receipt refs, or source thread/project refs silently.

## Relationship Payloads

Relationship payloads must be explicit for:

- FlowDraft -> project
- FlowDraft -> thread
- FlowDraft -> source message
- FlowDraft -> ValidationSnapshot
- FlowDraft -> CompiledPlan
- TestRun -> FlowDraft
- TestRun -> RunReceipt
- Activation -> FlowDraft
- Activation -> RunReceipt
- RunReceipt -> StepReceipt
- StepReceipt -> source step
- Conditional branch -> skipped/executed StepReceipts
- Flow artifacts -> audit/command/task-event refs

Relationship payloads must be explicit and not inferred only from nested JSON.

## Exclusion Policy

- Early export formats may exclude some Flow Builder families if they are not implemented or not safe to restore.
- Exclusions must be explicit in `manifest.json`.
- Exclusion must distinguish:
  - not implemented
  - intentionally deferred
  - intentionally excluded for privacy/security
  - not present in this account
- Silent exclusion is not allowed.

## Privacy and Sensitive Data

- Exported workflow artifacts may contain variable bindings, semantic metadata, external-recipient details, side-effect refs, and evidence summaries.
- Sensitive values should be redacted, hash-based, reference-based, or excluded according to future policy.
- Hidden prompts, raw chain-of-thought, raw secrets, and unnecessary sensitive inputs must not be exported blindly.
- Third-party service references must preserve enough auditability without leaking unnecessary account data.
- Restore must preserve privacy posture and not silently promote sensitive historical evidence into active runtime configuration.

## Compatibility and Versioning

- Flow Builder export schema must be versioned independently or as a declared sub-schema of the account export schema.
- Restore must fail closed or report incompatibility when schema versions are unsupported.
- Feature flags must describe which Flow Builder artifact families are present.
- Compiler, validator, and receipt-schema versions must be preserved where applicable.
- Compatibility behavior must be tested before implementation claims support.

## Restore Safety Rules

- Restored FlowDrafts may become editable drafts.
- Restored Activations must not automatically become active unless a future explicit policy and user/operator approval gate exists.
- Restored trigger registrations must not silently rebind.
- Restored TestRuns must not replay automatically.
- Restored RunReceipts must remain historical evidence.
- Restored side-effect refs must not be re-executed.
- Restore must not widen local-only or supported-profile posture.

## Failure and Reporting Policy

Required failures include:

- unsupported Flow Builder export schema
- missing required family
- checksum/integrity failure
- unresolved FlowDraft refs
- unresolved source thread/project/message refs
- unresolved validation snapshot refs
- unresolved permission snapshot refs
- unresolved trigger registration refs
- unresolved command run/audit/task-event refs
- receipt family declared included but missing payloads
- relationship payload mismatch

Required failures must be surfaced as restore errors or explicit restore warnings according to severity, never hidden.

## Non-Goals

- No export implementation.
- No restore implementation.
- No manifest implementation.
- No archive writer.
- No restore reader.
- No schema migration.
- No SQLAlchemy model.
- No Pydantic model.
- No route implementation.
- No worker implementation.
- No UI implementation.
- No validation engine.
- No compiler.
- No `TestRun`, `Activation`, `RunReceipt`, or `StepReceipt` implementation.
- No trigger re-registration.
- No side-effect replay.
- No release-surface expansion.

## Implementation Follow-Through

- FB-011 should prototype frontend shell only with fixtures that respect export/restore lineage fields.
- FB-012 should avoid claiming TestRun portability until receipt and export fixtures exist.
- FB-013 should require export/restore posture to be explicit before side-effecting workflows ship.
- Future backend implementation must add contract tests for manifest fields, relationship payloads, ID remapping, exclusions, and unresolved-reference reporting.
- Future restore implementation must include fixtures that prove Activations do not silently reactivate.

## Open Questions

- Should FlowDraft export be required as soon as FlowDraft persistence exists?
- Should CompiledPlan exports be omitted if compiler determinism is proven?
- Should RunReceipt and StepReceipt exports be default-on or opt-in?
- Should Activation records restore as inactive, disabled, or archived?
- Which permission snapshot fields are safe to export?
- Should activity history be exported directly or reconstructed from receipts?
- What Flow Builder sub-schema version should appear in the first account export format?
- How should restore report unresolved external service refs without frightening ordinary users?
