# Campaign: Flow Builder Typed Surface Implementation

## Purpose

This campaign decomposes ADR-027 into an ordered set of atomic future implementation tasks for Flow Builder typed surfaces, validation, execution evidence, and release-safe proof.

This is sequencing guidance only. It does not implement Flow Builder runtime behavior, add schemas, add routes, add workers, add UI components, or expand the supported beta surface.

## Governing Sources

- [ADR-006: Flow Builder Elicitation Lane](../architecture/adr/006-flow-builder-elicitation-lane.md)
- [ADR-014: Flow Builder Thread, Draft, and Receipts Contract](../architecture/adr/014-flow-builder-thread-draft-and-receipts-contract.md)
- [ADR-027: Flow Builder Typed Surface and Run Receipt Contract](../architecture/adr/027-flow-builder-typed-surface-and-run-receipt-contract.md)
- [Flow Builder Surface Research Application](../architecture/flow-builder-surface-research-application.md)
- [Runtime Protocol Token Contract](../architecture/runtime-protocol-token-contract.md)
- [Canonical Token Philosophy](../architecture/canonical-token-philosophy.md)
- [Critical Flows](../architecture/flows.md)
- [Data and Storage](../architecture/data-and-storage.md)
- [Modules and Ownership](../architecture/modules-and-ownership.md)

## Current Truth

### Implemented / current

- Codexify is in local-first beta hardening.
- The supported runtime path remains the local Docker Compose stack.
- The current supported beta surface is anchored to chat, ingestion/readback, supported-profile health/catalog truth, and current local-only runtime proof.
- Existing architecture docs distinguish route acceptance from completion, task-event publication from UI receipt, and validation/proof from release support.
- ADR-006, ADR-014, and ADR-027 are accepted architecture contracts for future Flow Builder work.

### Adjacent but not sufficient

- Guardian threads provide the canonical conversation substrate, but they are not FlowDraft persistence.
- Command bus runs and cron runs provide adjacent execution and scheduling concepts, but they are not Flow Builder execution, TestRun, Activation, or FlowRunReceipt persistence.
- Runtime protocol tokens provide existing token discipline, but Flow Builder variable, validation, semantic-step, and receipt token domains are not yet defined.
- Existing export/restore doctrine provides lineage expectations, but Flow Builder artifact inclusion is not yet specified.

### Proposed / contract-only

- `FlowDraft`, `FlowBuilderView`, and `FlowRunReceipt` are canonical contract terms.
- `Starter`, `ActionStep`, `SemanticStep`, `VariableChip`, `TypedStepOutput`, `ConditionalContainer`, `ValidationIssue`, `TestRun`, and `Activation` are canonical ADR-027 terms.
- Validation eligibility, activation state, compiled execution plans, and receipt evidence are architectural contracts for future implementation.
- Workspace Studio research is planning input only. It is not Codexify runtime truth.

### Explicitly not assumed

- Do not assume production Flow Builder UI exists.
- Do not assume `VariableChip` implementation exists.
- Do not assume `SemanticStep` execution exists.
- Do not assume `TestRun`, `Activation`, or `RunReceipt` persistence is implemented.
- Do not assume workflow execution is part of the supported beta surface.
- Do not assume route acceptance, task enqueue, or task-event publication proves execution completion or UI receipt.

## Campaign Invariants

- Preserve the distinction between authoring conversation, `FlowDraft` artifact state, compiled execution plan, validation eligibility, activation state, and run receipt evidence.
- Preserve route acceptance versus completion semantics.
- Preserve task-event publication versus UI receipt semantics.
- Preserve canonical token discipline: contract-bearing literals must live in bounded registries before use.
- Preserve identity boundaries and provenance from Guardian thread/message scope into draft, activation, and receipt artifacts.
- Preserve bounded execution: no recursive agent loop, no hidden prompt-only workflow semantics, and no unreceipted side effects.
- Preserve release truth: no beta surface widening and no implementation claims without proof.
- Treat validation as eligibility, not execution success.
- Treat receipt evidence as the durable proof surface for runs once runtime execution exists.

## Ordered Task Chain

1. **Task id:** `FB-001`
   **Title:** Flow Builder canonical token domain inventory
   **Lane:** docs
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/runtime-protocol-token-contract.md`, `docs/architecture/canonical-token-philosophy.md`, `docs/architecture/adr/027-flow-builder-typed-surface-and-run-receipt-contract.md`, possible future `docs/architecture/flow-builder-token-domains.md`
   **Depends on:** ADR-006, ADR-014, ADR-027, this campaign
   **Proof artifact:** `docs/architecture/flow-builder-token-domains.md`
   **Proof surface:** docs validation, grep proof that candidate token domains are inventoried before code use, explicit no-runtime-change diff
   **Non-goals:** no code token registry, no schema, no UI, no route or worker changes

2. **Task id:** `FB-002`
   **Title:** FlowDraft schema proposal
   **Lane:** backend contract
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/adr/`, `docs/architecture/data-and-storage.md`, possible future schema proposal note under `docs/architecture/`
   **Depends on:** `FB-001`
   **Proof artifact:** `docs/architecture/flowdraft-schema-proposal.md`
   **Proof surface:** accepted or explicitly proposed contract note covering `FlowDraft`, `Starter`, ordered steps, validation state, and provenance fields
   **Non-goals:** no migration, no SQLAlchemy model, no persistence implementation, no frontend draft model changes

3. **Task id:** `FB-003`
   **Title:** VariableChip and TypedStepOutput contract
   **Lane:** frontend contract
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/adr/`, `docs/architecture/runtime-protocol-token-contract.md`, `docs/architecture/canonical-token-philosophy.md`, possible future Flow Builder contract note, `docs/architecture/variable-chip-typed-output-contract.md`
   **Depends on:** `FB-001`, `FB-002`
   **Proof artifact:** `docs/architecture/variable-chip-typed-output-contract.md`
   **Proof surface:** contract tests or docs checks in the future implementation slice proving stable identity, source-step lineage, canonical type domains, and compatibility rules are specified before UI use
   **Non-goals:** no `VariableChip` component, no chip styling, no string interpolation runtime, no backend execution

4. **Task id:** `FB-004`
   **Title:** ValidationIssue taxonomy and token registry
   **Lane:** backend contract
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/runtime-protocol-token-contract.md`, `docs/architecture/canonical-token-philosophy.md`, possible future `guardian/flow_builder/` contract module and contract tests, `docs/architecture/flow-builder-validation-issue-taxonomy.md`
   **Depends on:** `FB-001`, `FB-002`, `FB-003`
   **Proof artifact:** `docs/architecture/flow-builder-validation-issue-taxonomy.md`
   **Proof surface:** bounded validation issue code registry, severity domain, field/step/flow scope rules, and tests that reject ad hoc validation codes when implementation begins
   **Non-goals:** no validation engine, no UI issue badges, no activation or execution gating implementation

5. **Task id:** `FB-005`
   **Title:** SemanticStep contract
   **Lane:** backend contract
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/adr/`, `docs/architecture/flows.md`, possible future `guardian/flow_builder/semantic_steps.py`
   **Depends on:** `FB-001`, `FB-003`, `FB-004`
   **Proof artifact:** `docs/architecture/flow-builder-semantic-step-contract.md`
   **Proof surface:** contract note defining semantic step kinds, input/output schemas, uncertainty behavior, receipt metadata, and explicit non-recursive execution boundaries
   **Non-goals:** no model calls, no prompt executor, no recursive agent loop, no tool-chain runtime

6. **Task id:** `FB-006`
   **Title:** ConditionalContainer contract and UI model
   **Lane:** frontend contract
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/adr/`, possible future `docs/architecture/flow-builder-conditional-container.md`, future frontend model docs
   **Depends on:** `FB-002`, `FB-003`, `FB-004`, `FB-005`
   **Proof artifact:** `docs/architecture/flow-builder-conditional-container-contract.md`
   **Proof surface:** contract note proving the default authoring model is linear steps with structured conditional containers, branch context, at least one nested substep, and no arbitrary DAG claim
   **Non-goals:** no canvas implementation, no drag/drop branch UI, no execution compiler

7. **Task id:** `FB-007`
   **Title:** TestRun and Activation backend contract
   **Lane:** backend contract
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/adr/`, `docs/architecture/flows.md`, `docs/architecture/data-and-storage.md`, possible future `guardian/flow_builder/` contract files
   **Depends on:** `FB-002`, `FB-004`, `FB-005`, `FB-006`
   **Proof surface:** contract note distinguishing isolated non-side-effecting TestRun from durable Activation, including validation gates, permission checks, trigger registration, and activation/deactivation semantics
   **Non-goals:** no trigger registration implementation, no cron reuse implementation, no command-bus execution wiring, no external side effects

8. **Task id:** `FB-008`
   **Title:** RunReceipt persistence model
   **Lane:** backend contract
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/data-and-storage.md`, `docs/architecture/adr/`, possible future migration plan docs
   **Depends on:** `FB-002`, `FB-007`
   **Proof artifact:** `docs/architecture/flow-builder-runreceipt-persistence-model.md`
   **Proof surface:** persistence proposal covering receipt immutability, run identity, step receipts, terminal state, failure reason, provenance links, command run references, retrieval posture, and semantic-step metadata
   **Non-goals:** no database migration, no model implementation, no receipt API, no activity UI

9. **Task id:** `FB-009`
   **Title:** Flow activity/proof surface design
   **Lane:** frontend contract
   **Status:** complete
   **Architecture impact:** yes
   **Target files or likely target file families:** `docs/architecture/`, possible future `docs/architecture/flow-builder-activity-proof-surface.md`, future frontend contract docs
   **Depends on:** `FB-008`
   **Proof artifact:** `docs/architecture/flow-builder-activity-proof-surface.md`
   **Proof surface:** surface design that shows receipt streams as operational evidence distinct from chat messages and task events
   **Non-goals:** no UI component implementation, no SSE subscription, no receipt route, no live proof claim

10. **Task id:** `FB-010`
    **Title:** Export/restore workflow artifact inclusion
    **Lane:** backend contract
    **Architecture impact:** yes
    **Target files or likely target file families:** `docs/architecture/account-export-restore-contract.md`, `docs/architecture/data-and-storage.md`, possible future export manifest docs and tests
    **Depends on:** `FB-002`, `FB-007`, `FB-008`
    **Proof surface:** explicit decision on whether `FlowDraft`, `Activation`, and `FlowRunReceipt` enter export/restore first, including lineage preservation or explicit manifest exclusion
    **Non-goals:** no export code changes, no restore implementation, no data migration

11. **Task id:** `FB-011`
    **Title:** Frontend Flow Builder shell prototype
    **Lane:** frontend implementation
    **Architecture impact:** no
    **Target files or likely target file families:** `frontend/src/features/flowBuilder/`, `frontend/tests/` or colocated Vitest files, frontend route/shell files only if needed
    **Depends on:** `FB-002`, `FB-003`, `FB-004`, `FB-006`, `FB-009`
    **Proof surface:** targeted frontend tests showing one shared typed draft object, validation display from contract fixtures, no runtime execution, and no beta nav/supported-surface expansion unless separately approved
    **Non-goals:** no backend route, no persistence, no TestRun, no Activation, no live execution, no release-surface claim

12. **Task id:** `FB-012`
    **Title:** First non-side-effecting TestRun proof harness
    **Lane:** proof
    **Architecture impact:** yes
    **Target files or likely target file families:** future `guardian/flow_builder/`, future tests under `tests/`, possible scripts under `scripts/proofs/`
    **Depends on:** `FB-004`, `FB-005`, `FB-007`, `FB-008`
    **Proof surface:** isolated test harness that executes only non-side-effecting steps, emits ephemeral test evidence, proves validation gating, and proves no external writes
    **Non-goals:** no live Activation, no external connector writes, no scheduler registration, no supported beta claim

13. **Task id:** `FB-013`
    **Title:** First side-effecting workflow execution behind explicit gate
    **Lane:** backend implementation
    **Architecture impact:** yes
    **Target files or likely target file families:** future `guardian/flow_builder/`, command bus or cron integration files if selected by prior contracts, tests under `tests/`, operator proof docs
    **Depends on:** `FB-007`, `FB-008`, `FB-010`, `FB-012`
    **Proof surface:** explicit operator gate, validation pass, activation record, durable receipt, idempotency evidence, provenance links, and side-effect references for every external mutation
    **Non-goals:** no recursive agent loop, no hidden prompt-only workflow behavior, no unreceipted side effects, no beta surface widening without separate release decision

## Recommended First Implementation Slice

The first real implementation slice after this campaign should be `FB-001`: token/domain inventory plus contract tests.

That slice should define the bounded Flow Builder token domains that future code will need, identify which registry or registries own them, and add tests that prevent ad hoc use once implementation starts. It should not build UI, persistence, runtime execution, TestRun, Activation, or receipt storage.

This order keeps the durable vocabulary ahead of runtime code. It also prevents UI from depending on literals, states, or validation codes that have not been canonically accepted.

## Release Boundary

This campaign does not make Flow Builder part of the supported beta surface.

Each implementation task must define its own proof surface before it is started. Proof must distinguish contract acceptance, test-backed behavior, supported-path live proof, and release readiness.

Runtime execution cannot ship without receipts, validation, and operator evidence. Side-effecting execution additionally requires explicit gating, idempotency, provenance, and audit-ready receipt records.

## Open Questions

- Where should workflow token registries live?
- Should `FlowDraft` persistence reuse existing flow tables or introduce new contract-specific tables?
- What is the minimum `RunReceipt` for a non-side-effecting test run?
- How should `unknown` AI decisions be represented?
- Which workflow artifacts must enter export/restore first?

## Documentation Follow-Through

- Link this campaign from `/docs/architecture/README.md` near the Flow Builder cluster as implementation sequencing guidance, not runtime truth.
- Do not add task files under `/docs/tasks/` in this documentation-only campaign. Add them later, one atomic task at a time, when implementation begins.
- ADR-027 does not need amendment before `FB-001` begins. Later tasks that choose persistence shape, uncertainty behavior, activation semantics, or execution behavior may require ADR amendments or follow-on ADRs before implementation.
