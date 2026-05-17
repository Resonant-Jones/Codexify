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

This contract sits underneath the canonical account export and restore doctrine and must preserve its guarantees:

- single canonical archive
- `manifest.json` as archive source of truth
- explicit entity payloads
- explicit relationship payloads
- integrity metadata
- compatibility metadata
- fail-closed or explicit reporting for unsupported schema versions
- no silent lineage loss
- semantic equivalence across ID remapping

The archive remains the canonical portability unit. Flow Builder inclusion rules are only a sub-contract inside that archive model.

## Conceptual Model

The planned relationship among Flow Builder artifacts is:

`FlowDraft -> CompiledPlan -> ValidationSnapshot -> TestRun / Activation -> RunReceipt -> StepReceipt -> ActivityTimeline -> manifest.json -> restore ID map`

This is a proposed model only. It does not claim any implementation exists.

The export path should treat `FlowDraft` as the authoring anchor and receipts as lineage-bearing evidence. The restore path should use the ID map and manifest to reconcile references, then reconstruct historical proof surfaces without re-running anything by default.

Diagram:

`FlowDraft artifacts -> export manifest families -> restore ID map -> restored FlowDraft/proof refs -> reconstructed activity/proof surface`

## Export Artifact Families

| Family | Purpose | Inclusion class | Restore expectation | Exclusion policy |
|---|---|---|---|---|
| `flow_drafts` | Canonical authoring artifact with lineage, validation, and draft structure. | Required once `FlowDraft` persistence exists. | Restore as editable draft state, not compiled execution truth. | May be absent only if the account has no persisted drafts or the format explicitly excludes them. |
| `flow_compiled_plan_refs` | Reference to deterministic compiled interpretation and its lineage. | Deferred or optional. | Restore as advisory reference only; never authoritative over the draft. | May be excluded early if the compiler version and plan hash make safe regeneration possible. |
| `flow_validation_snapshots` | Historical validation evidence and eligibility posture. | Optional, but required when referenced by TestRun, Activation, or RunReceipt records. | Restore as historical evidence, not current validity. | May be excluded if not implemented, not present, or intentionally deferred, but the manifest must say so. |
| `flow_test_runs` | Historical isolated execution-attempt records. | Optional or deferred until TestRun persistence exists. | Restore only as historical attempts; never as active executions. | May be excluded if not implemented or if the export policy intentionally omits them. |
| `flow_activations` | Durable enablement history and trigger-facing lineage. | Optional or deferred, but higher risk than drafts. | Restore as inactive or historical unless explicit future policy says otherwise. | May be excluded for privacy, policy, or unsupported restoration posture, but the manifest must say so. |
| `flow_run_receipts` | Run-level execution proof and lineage-bearing evidence. | Optional if the export format is proof-aware; required if run proof is included. | Restore as immutable historical evidence. | Silent loss is not allowed if the family is declared included. |
| `flow_step_receipts` | Step-level execution proof beneath a run receipt. | Optional if the export format is proof-aware; required if run proof is included. | Restore as immutable step evidence, including skips and branch decisions. | Silent loss is not allowed if the family is declared included. |
| `flow_activity_refs` | Reconstructable activity/proof surface references and labels. | Optional or deferred. | Restore as a visible history layer derived from included refs. | If activity history is excluded, the manifest must declare that exclusion explicitly. |
| `flow_artifact_relationships` | Explicit lineage edges between Flow Builder artifacts and adjacent proof surfaces. | Required for lineage-preserving export. | Restore through the ID map and surface any unresolved edges explicitly. | May be excluded only if the export intentionally omits the corresponding artifact families and states that exclusion explicitly. |

## Proposed Manifest Entries

The following fields are candidate manifest entries. They become mandatory only if later implementation promotes them.

| Manifest field | Type / shape | Required | Notes |
|---|---|---|---|
| `flow_builder_schema_version` | string or semver-like value | Candidate | Identifies the Flow Builder sub-schema version within the archive. |
| `flow_builder_export_mode` | token or string | Candidate | Declares whether the export is draft-only, proof-inclusive, historical-only, or another supported mode. |
| `flow_builder_entity_counts` | object keyed by family | Candidate | Count by included Flow Builder entity family. |
| `flow_builder_relationship_counts` | object keyed by relationship family | Candidate | Count by exported relationship family. |
| `flow_builder_feature_flags` | object or token set | Candidate | Declares which Flow Builder artifact capabilities are present. |
| `flow_builder_included_families` | array of family names | Candidate | Lists every included Flow Builder family explicitly. |
| `flow_builder_excluded_families` | array of family names plus reasons | Candidate | Lists every excluded family explicitly, with exclusion class. |
| `flow_builder_integrity` | checksum/hash metadata object | Candidate | Integrity metadata for Flow Builder payloads and proof surfaces. |
| `flow_builder_compatibility` | object or token set | Candidate | Compatibility posture for versioning, regen, and restore behavior. |
| `flow_builder_restore_requirements` | object or array | Candidate | Declares restore prerequisites, unresolved-reference policy, and gates. |

These are candidate fields unless later implementation promotes them.

## FlowDraft Export Requirements

FlowDraft exports must preserve stable draft IDs or exported stable IDs.

Draft title, description, starter refs, ordered ActionSteps, VariableBindings, TypedStepOutputs, ConditionalContainers, SemanticSteps, validation state refs, provenance, timestamps, project/thread refs, and owner/user refs must be preserved where applicable.

Authoring state must not be replaced by compiled execution state.

Missing project/thread refs must be reported explicitly on restore.

FlowDraft export is the primary required family once FlowDraft persistence exists.

## CompiledPlan Reference Policy

CompiledPlan artifacts may be excluded in early export if they are deterministic and safely regenerable from FlowDraft plus compiler version.

If included, CompiledPlan exports must preserve source FlowDraft ref, compiler version, plan hash, generated-at timestamp, validation snapshot ref, and provenance.

Restore must not treat a stale compiled plan as authoritative over the restored FlowDraft.

If compiler versions differ, restore must report compatibility posture.

## ValidationSnapshot Export Requirements

Validation snapshots may be required once TestRun, Activation, or RunReceipt records reference them.

Exports should preserve issue codes, severities, target refs, blocking state, validator version, generated-at timestamp, and provenance.

Restore must preserve the difference between historical validation evidence and current validation eligibility.

Restoring a historical validation snapshot must not imply the restored flow is currently valid.

## TestRun Export Requirements

TestRun exports are optional or deferred until TestRun persistence exists.

If included, they must preserve state, FlowDraft ref, CompiledPlan ref, validation snapshot ref, permission snapshot ref, run receipt ref, timestamps, initiated-by ref, side-effect mode, cancellation/failure reason, and provenance.

Restore must not turn historical TestRuns into active executions.

Restore must report unresolved receipt refs or permission snapshot refs explicitly.

## Activation Export Requirements

Activation records are higher risk than drafts because they imply durable enablement/subscription.

Early export may include Activation records as historical records but restore them as inactive unless explicit future policy says otherwise.

If included, Activation exports must preserve state, FlowDraft ref, CompiledPlan ref, starter ref, validation snapshot ref, permission snapshot ref, trigger registration ref, last run receipt ref, timestamps, activated-by ref, paused/disabled markers, failure reason, and provenance.

Restore must not silently re-register triggers or resume side-effecting workflows.

Trigger registration refs must be reported unresolved unless the restore environment can rebind them through an explicit future gate.

## RunReceipt and StepReceipt Export Requirements

RunReceipt and StepReceipt artifacts are lineage-bearing execution evidence.

If included, exports must preserve receipt IDs or exported stable IDs, source FlowDraft refs, CompiledPlan refs, TestRun/Activation refs, state, validation snapshot refs, permission snapshot refs, command run refs, task event refs, audit refs, side-effect refs, semantic metadata, condition metadata, timestamps, failure/cancellation reasons, and provenance.

StepReceipt exports must preserve source step refs, branch refs, state, bounded value summaries or redaction references, and side-effect refs.

Restore must report unresolved command run refs, task event refs, audit refs, or side-effect refs explicitly.

Silent receipt loss is not allowed if receipts are declared included.

## Activity and Proof Surface Reconstruction

Activity/proof surfaces should be reconstructable from restored FlowDraft, TestRun, Activation, RunReceipt, StepReceipt, validation, permission, audit, and side-effect references where included.

Activity UI labels are not independently authoritative export records unless later promoted.

If activity history is excluded, the exclusion must be declared in the manifest.

Reconstructed activity must distinguish restored historical evidence from newly generated runtime evidence.

## ID Remapping and Reference Reconciliation

Exported stable ID: the durable identifier written into the archive.

Restored local ID: the identifier assigned inside the target account during restore.

Restore ID map: the mapping between exported stable IDs and restored local IDs.

Unresolved reference: a reference that cannot be reconciled to a restored local ID.

Remapped reference: a reference rewritten through the restore ID map.

Orphaned historical reference: a preserved historical edge whose target is not restorable as an active object.

Restore must produce or maintain an ID map for all Flow Builder artifact families.

Relationship payloads must be reconciled through the ID map.

Restore must fail or explicitly report when required refs cannot be reconciled.

Restored IDs must not break VariableBinding refs, step refs, branch refs, receipt refs, or source thread/project refs silently.

## Relationship Payloads

Relationship payloads must be explicit and must not be inferred only from nested JSON.

Define relationship records for:

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

Each relationship record should preserve endpoint IDs, relationship type, directionality, and any metadata needed for deterministic restore.

## Exclusion Policy

Early export formats may exclude some Flow Builder families if they are not implemented or not safe to restore.

Exclusions must be explicit in `manifest.json`.

Exclusion must distinguish:

- not implemented
- intentionally deferred
- intentionally excluded for privacy/security
- not present in this account

Silent exclusion is not allowed.

## Privacy and Sensitive Data

Exported workflow artifacts may contain variable bindings, semantic metadata, external-recipient details, side-effect refs, and evidence summaries.

Sensitive values should be redacted, hash-based, reference-based, or excluded according to future policy.

Hidden prompts, raw chain-of-thought, raw secrets, and unnecessary sensitive inputs must not be exported blindly.

Third-party service references must preserve enough auditability without leaking unnecessary account data.

Restore must preserve privacy posture and not silently promote sensitive historical evidence into active runtime configuration.

## Compatibility and Versioning

Flow Builder export schema must be versioned independently or as a declared sub-schema of the account export schema.

Restore must fail closed or report incompatibility when schema versions are unsupported.

Feature flags must describe which Flow Builder artifact families are present.

Compiler, validator, and receipt-schema versions must be preserved where applicable.

Compatibility behavior must be tested before implementation claims support.

## Restore Safety Rules

Restored FlowDrafts may become editable drafts.

Restored Activations must not automatically become active unless a future explicit policy and user/operator approval gate exists.

Restored trigger registrations must not silently rebind.

Restored TestRuns must not replay automatically.

Restored RunReceipts must remain historical evidence.

Restored side-effect refs must not be re-executed.

Restore must not widen local-only or supported-profile posture.

## Failure and Reporting Policy

Restore must surface the following conditions explicitly:

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
- No TestRun, Activation, RunReceipt, or StepReceipt implementation.
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
